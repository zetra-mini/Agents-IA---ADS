"""API FastAPI para orquestração de campanhas Meta Ads com CrewAI + browser-use."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agentes import CampanhaMetaAdsPlan, planejar_campanha
from automacao import executar_rascunho_meta_ads
from criativos import (
    listar_criativos,
    resolver_pasta_criativos,
    validar_nome_arquivo_upload,
)
from llm_config import get_settings, list_providers

logger = logging.getLogger("meta_ads_api")
settings = get_settings()

app = FastAPI(
    title="Meta Ads Autonomous Orchestrator API",
    description=(
        "Backend Dockerizado com FastAPI + CrewAI + browser-use para planejar e "
        "montar rascunhos de campanhas no Meta Ads Manager a partir de comandos e pastas de criativos."
    ),
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ComandoCampanhaRequest(BaseModel):
    """Payload de entrada enviado por Astro, Svelte ou clientes HTTP."""

    instrucao: str = Field(
        ...,
        min_length=5,
        examples=[
            "Criar campanha CBO de leads para repasse de financiamento, R$ 500/dia, para Campo Largo e Curitiba"
        ],
    )
    pasta_criativos: str | None = Field(
        default=None,
        description=(
            "Caminho da pasta onde estão os criativos (imagens/vídeos). "
            "Se omitido, usa CREATIVES_DIR configurado no .env."
        ),
    )
    executar_navegador: bool = Field(
        default=True,
        description="Se false, executa somente os agentes CrewAI e retorna o JSON estruturado.",
    )
    provider: str | None = Field(
        default=None,
        description="Override opcional: opencode, ollama, anthropic, openai ou google.",
    )


class CampanhaResposta(BaseModel):
    """Resposta unificada com o plano do CrewAI, criativos encontrados e resultado do browser-use."""

    plano_campanha: CampanhaMetaAdsPlan
    criativos_encontrados: dict[str, Any]
    automacao: dict[str, Any] | None = None


def _carregar_criativos(pasta_criativos: str | None) -> dict[str, Any]:
    cfg = get_settings()
    return listar_criativos(pasta_criativos, default_dir=cfg.creatives_dir)


@app.get("/health")
async def healthcheck() -> dict[str, Any]:
    """Verifica disponibilidade da API, provedor LLM ativo e pasta de criativos padrão."""
    cfg = get_settings()
    pasta_resolvida = resolver_pasta_criativos(None, cfg.creatives_dir)
    return {
        "status": "ok",
        "active_provider": cfg.llm_provider,
        "headless": cfg.browser_headless,
        "creatives_dir": str(pasta_resolvida),
    }


@app.get("/providers")
async def get_providers() -> dict[str, Any]:
    """Expõe provedores locais e externos configuráveis para o seletor do frontend."""
    return list_providers()


@app.get("/criativos")
async def get_criativos(
    pasta: str | None = Query(default=None, description="Caminho da pasta local ou montada no Docker"),
) -> dict[str, Any]:
    """Lista os criativos (imagens/vídeos) encontrados na pasta informada."""
    try:
        return _carregar_criativos(pasta)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/criativos/upload")
async def upload_criativos(
    files: list[UploadFile] = File(...),
    pasta: str | None = Form(default=None),
) -> dict[str, Any]:
    """Envia imagens/vídeos diretamente pelo frontend para a pasta de criativos."""
    cfg = get_settings()
    destino_dir = resolver_pasta_criativos(pasta, cfg.creatives_dir)
    destino_dir.mkdir(parents=True, exist_ok=True)

    salvos: list[str] = []
    for upload in files:
        try:
            nome = validar_nome_arquivo_upload(upload.filename or "")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        destino_arquivo = (destino_dir / nome).resolve()
        conteudo = await upload.read()
        destino_arquivo.write_bytes(conteudo)
        salvos.append(nome)

    return {
        "salvos": salvos,
        "inventario": listar_criativos(str(destino_dir), default_dir=cfg.creatives_dir),
    }


@app.post("/campanhas/planejar", response_model=CampanhaMetaAdsPlan)
async def planejar_somente(payload: ComandoCampanhaRequest) -> CampanhaMetaAdsPlan:
    """Executa apenas o CrewAI (Gestor de Tráfego + Copywriter) e devolve o JSON."""
    try:
        criativos_info = _carregar_criativos(payload.pasta_criativos)
        return await planejar_campanha(
            instrucao=payload.instrucao,
            provider_override=payload.provider,
            criativos_disponiveis=criativos_info["arquivos"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Erro ao planejar campanha via CrewAI")
        raise HTTPException(
            status_code=500,
            detail=f"Falha ao executar agentes CrewAI: {exc}",
        ) from exc


@app.post("/campanhas/criar", response_model=CampanhaResposta)
async def criar_campanha(payload: ComandoCampanhaRequest) -> CampanhaResposta:
    """Orquestra Pasta de Criativos -> CrewAI -> JSON estruturado -> browser-use (Rascunho)."""
    try:
        criativos_info = _carregar_criativos(payload.pasta_criativos)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        plano = await planejar_campanha(
            instrucao=payload.instrucao,
            provider_override=payload.provider,
            criativos_disponiveis=criativos_info["arquivos"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Erro na etapa CrewAI")
        raise HTTPException(
            status_code=500,
            detail=f"Falha na etapa de planejamento CrewAI: {exc}",
        ) from exc

    if not payload.executar_navegador:
        return CampanhaResposta(
            plano_campanha=plano,
            criativos_encontrados=criativos_info,
            automacao=None,
        )

    caminhos = [item["caminho"] for item in criativos_info["arquivos"]]
    try:
        automacao_res = await executar_rascunho_meta_ads(
            plano=plano,
            provider_override=payload.provider,
            caminhos_criativos=caminhos,
        )
        return CampanhaResposta(
            plano_campanha=plano,
            criativos_encontrados=criativos_info,
            automacao=automacao_res,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Erro na etapa browser-use")
        raise HTTPException(
            status_code=500,
            detail=f"Plano criado, mas falhou a automação browser-use: {exc}",
        ) from exc
