"""API FastAPI para orquestração de campanhas Meta Ads com CrewAI + browser-use."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agentes import CampanhaMetaAdsPlan, planejar_campanha
from automacao import (
    abrir_navegador_direto,
    executar_rascunho_meta_ads,
    inspecionar_sessao_navegador_meta,
)
from criativos import (
    listar_criativos,
    resolver_pasta_criativos,
    validar_nome_arquivo_upload,
)
from llm_config import get_settings, list_providers
from meta_hub import LOJA_PUBLICOS_ADSIMPLES, get_meta_hub, validar_campanha_preflight

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
    validacao_preflight: dict[str, Any] | None = None
    campanha_registrada: dict[str, Any] | None = None


class StatusCampanhaPatch(BaseModel):
    status: str


class OrcamentoCampanhaPatch(BaseModel):
    daily_budget: float


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

    caminhos = [item["caminho"] for item in criativos_info["arquivos"]]
    validacao = validar_campanha_preflight(plano, caminhos)
    campanha_hub = get_meta_hub().registrar_campanha_do_plano(plano, caminhos)

    if not payload.executar_navegador:
        return CampanhaResposta(
            plano_campanha=plano,
            criativos_encontrados=criativos_info,
            automacao=None,
            validacao_preflight=validacao,
            campanha_registrada=campanha_hub,
        )

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
            validacao_preflight=validacao,
            campanha_registrada=campanha_hub,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Erro na etapa browser-use")
        raise HTTPException(
            status_code=500,
            detail=f"Plano criado, mas falhou a automação browser-use: {exc}",
        ) from exc


@app.post("/campanhas/abrir-navegador")
async def abrir_navegador_meta_ads(url: str | None = None) -> dict[str, Any]:
    """Abre uma instância do navegador diretamente no Gerenciador de Anúncios."""
    cfg = get_settings()
    alvo = url or cfg.meta_ads_url
    return await abrir_navegador_direto(
        url=alvo,
        headless=cfg.browser_headless,
        user_data_dir=cfg.browser_user_data_dir,
    )


@app.get("/meta/campaigns")
async def listar_campanhas_hub() -> list[dict[str, Any]]:
    """Lista campanhas da conta (Mock/Graph API de octaviosilva2/meta-ads) com diagnóstico de performance."""
    return await get_meta_hub().list_campaigns()


@app.get("/meta/copilot")
async def obter_relatorio_copilot() -> dict[str, Any]:
    """Retorna o relatório do Robô Otimizador estilo Hackr Ads / AdSimples + TheMattBerman/meta-ads-kit."""
    return await get_meta_hub().get_copilot_report()


@app.get("/meta/audiences-store")
async def obter_loja_publicos() -> dict[str, Any]:
    """Retorna a Loja de Públicos Prontos inspirada no Hackr Ads / AdSimples."""
    return {"publicos": LOJA_PUBLICOS_ADSIMPLES}


@app.patch("/meta/campaigns/{campaign_id}/status")
async def alterar_status_campanha(campaign_id: str, body: StatusCampanhaPatch) -> dict[str, Any]:
    """Ativa (ACTIVE) ou pausa (PAUSED) uma campanha em 1 clique."""
    try:
        return await get_meta_hub().update_campaign_status(campaign_id, body.status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.patch("/meta/campaigns/{campaign_id}/budget")
async def alterar_orcamento_campanha(campaign_id: str, body: OrcamentoCampanhaPatch) -> dict[str, Any]:
    """Escala ou reduz o orçamento diário de uma campanha em 1 clique."""
    try:
        return await get_meta_hub().update_campaign_budget(campaign_id, body.daily_budget)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


class ConectarTokenRequest(BaseModel):
    access_token: str
    account_id: str | None = None


class SelecionarContaRequest(BaseModel):
    account_id: str
    account_name: str | None = None
    business_name: str | None = None


class ModoRealRequest(BaseModel):
    somente_dados_reais: bool


class ChatAssistidoRequest(BaseModel):
    mensagem: str
    plano_atual: dict[str, Any] | None = None
    etapa_atual: int = 1
    pasta_criativos: str | None = None


class PublicarAssistidoRequest(BaseModel):
    plano_campanha: CampanhaMetaAdsPlan
    pasta_criativos: str | None = None


@app.get("/meta/connection")
async def obter_status_conexao_meta() -> dict[str, Any]:
    """Retorna qual Gerenciador de Negócios (BM) e Conta de Anúncios (act_...) estão conectados."""
    return get_meta_hub().get_connection_status()


@app.post("/meta/connect-token")
async def conectar_token_meta_api(body: ConectarTokenRequest) -> dict[str, Any]:
    """Conecta o Access Token real da Meta Marketing API e descobre todas as Contas de Anúncios (act_...)."""
    try:
        return await get_meta_hub().connect_graph_token(body.access_token, body.account_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Falha ao conectar na Meta Graph API: {exc}") from exc


@app.post("/meta/select-account")
async def selecionar_conta_meta(body: SelecionarContaRequest) -> dict[str, Any]:
    """Define qual Conta de Anúncios (act_...) e Gerenciador estão ativos no painel."""
    try:
        return get_meta_hub().select_ad_account(
            body.account_id, body.account_name, body.business_name
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/meta/sync-browser")
async def sincronizar_conta_do_navegador() -> dict[str, Any]:
    """Inspeciona a aba aberta do Playwright no Meta Ads Manager e importa o act_... e campanhas reais."""
    info_nav = await inspecionar_sessao_navegador_meta()
    status_con = get_meta_hub().sync_from_browser_session(info_nav)
    return {"navegador": info_nav, "connection": status_con}


@app.post("/meta/real-mode")
async def alternar_modo_somente_real(body: ModoRealRequest) -> dict[str, Any]:
    """Ativa ou desativa a exibição exclusiva de dados reais (ocultando campanhas de demonstração)."""
    return get_meta_hub().set_real_only_mode(body.somente_dados_reais)


@app.post("/campanhas/assistida/chat")
async def chat_criacao_assistida(body: ChatAssistidoRequest) -> dict[str, Any]:
    """Processa instruções no Assistente de Criação de Campanha Passo a Passo."""
    try:
        criativos_info = _carregar_criativos(body.pasta_criativos)
        return get_meta_hub().processar_mensagem_assistida(
            mensagem=body.mensagem,
            plano_atual=body.plano_atual,
            etapa_atual=body.etapa_atual,
            criativos_disponiveis=criativos_info["arquivos"],
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/campanhas/assistida/publicar-graph")
async def publicar_campanha_assistida_graph(body: PublicarAssistidoRequest) -> dict[str, Any]:
    """Cria a campanha revisada diretamente na Conta de Anúncios Real via Meta Graph API (PAUSED)."""
    try:
        criativos_info = _carregar_criativos(body.pasta_criativos)
        caminhos = [item["caminho"] for item in criativos_info["arquivos"]]
        return await get_meta_hub().criar_campanha_real_graph_api(body.plano_campanha, caminhos)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro ao criar na Graph API: {exc}") from exc
