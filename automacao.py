"""Automação do Gerenciador de Anúncios da Meta utilizando `browser-use` (Playwright/CDP).

Recebe o JSON estruturado gerado pelo CrewAI, inicia uma sessão Chromium com perfil
persistente, libera os caminhos locais de criativos para upload (`available_file_paths`)
e preenche a campanha no `adsmanager.facebook.com`, salvando obrigatoriamente como Rascunho.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from agentes import CampanhaMetaAdsPlan
from llm_config import Settings, build_browser_use_llm, get_settings, resolve_provider_config


def construir_prompt_navegador(
    plano: CampanhaMetaAdsPlan,
    meta_ads_url: str,
    caminhos_criativos: list[str] | None = None,
) -> str:
    """Monta a instrução detalhada e segura para o agente `browser-use`."""
    plano_json = plano.model_dump_json(indent=2)
    bloco_midia = (
        "ARQUIVOS LOCAIS AUTORIZADOS PARA UPLOAD DE CRIATIVO (use upload_file com o caminho exato):\n"
        + "\n".join(f"- {caminho}" for caminho in caminhos_criativos)
        if caminhos_criativos
        else "Nenhum arquivo local de mídia foi fornecido; deixe a mídia padrão para revisão posterior no rascunho."
    )

    passo_midia = (
        "   - Na etapa de Anúncio, clique em Adicionar mídia (Imagem ou Vídeo) e utilize `upload_file` "
        "enviando um dos caminhos exatos listados abaixo."
        if caminhos_criativos
        else "   - Na etapa de Anúncio, mantenha a mídia pendente se não houver arquivo na pasta."
    )

    return f"""
Você é um operador especialista no Meta Ads Manager. Execute os passos abaixo com cautela:

1. Acesse a URL: {meta_ads_url}
2. Verifique se a conta está autenticada no Gerenciador de Anúncios.
   - SE aparecer tela de login, senha, checkpoint ou verificação em duas etapas (2FA),
     PARE IMEDIATAMENTE e retorne exatamente:
     "AUTH_REQUIRED: Faça login manualmente no perfil persistente antes de criar rascunhos."
3. Caso esteja autenticado:
   - Clique no botão "Criar" (ou "+ Create") para iniciar uma nova campanha.
   - Selecione o objetivo equivalente a "{plano.objetivo}".
   - Caso aplicável e indicado no JSON, observe a Categoria Especial de Anúncio: "{plano.categoria_especial_anuncio}".
   - Configure o nome da campanha como "{plano.nome_campanha}".
   - Configure o tipo de orçamento "{plano.tipo_orcamento}" com orçamento diário de R$ {plano.orcamento_diario_brl:.2f}.
   - Avance para o(s) Conjunto(s) de Anúncios e preencha as localizações geográficas, faixa etária e posicionamentos conforme o JSON abaixo.
   - Avance para o Anúncio e preencha texto principal, título, descrição e CTA do primeiro criativo do JSON abaixo.
{passo_midia}
4. REGRA CRÍTICA DE SEGURANÇA:
   - NUNCA clique em "Publicar" ou "Publish".
   - Ao concluir o preenchimento, clique em "Fechar" / "Salvar como rascunho" (Close / Save as draft) e confirme que a campanha aparece na tabela com status "Em rascunho" ou "Rascunho".
   - Retorne um resumo objetivo do que foi preenchido e salvo como rascunho.

{bloco_midia}

JSON ESTRUTURADO DA CAMPANHA:
{plano_json}
""".strip()


async def executar_rascunho_meta_ads(
    plano: CampanhaMetaAdsPlan,
    provider_override: str | None = None,
    caminhos_criativos: list[str] | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Dispara o agente `browser-use` para montar o rascunho no Meta Ads Manager."""
    from browser_use import Agent, Browser

    cfg = settings or get_settings()
    resolved = resolve_provider_config(provider_override, cfg)
    llm = build_browser_use_llm(provider_override, cfg)

    profile_dir = Path(cfg.browser_user_data_dir)
    if not profile_dir.exists() and cfg.browser_user_data_dir.startswith("/app/"):
        profile_dir = Path(__file__).resolve().parent / "browser_profile"
    profile_dir.mkdir(parents=True, exist_ok=True)

    # Em containers Docker Linux (como root ou sem userns), o sandbox do Chromium precisa ficar desativado.
    in_docker = os.getenv("IN_DOCKER", "").lower() in {"1", "true", "yes"}
    browser = Browser(
        use_cloud=False,
        headless=cfg.browser_headless,
        chromium_sandbox=not in_docker,
        user_data_dir=str(profile_dir),
    )

    caminhos_validos = [str(Path(p).resolve()) for p in (caminhos_criativos or []) if Path(p).is_file()]
    task_prompt = construir_prompt_navegador(plano, cfg.meta_ads_url, caminhos_validos)

    agent = Agent(
        task=task_prompt,
        llm=llm,
        browser=browser,
        available_file_paths=caminhos_validos,
        use_vision=True,
        max_failures=3,
    )

    try:
        history = await agent.run(max_steps=cfg.browser_max_steps)
        final_text = history.final_result() or ""
        auth_required = "AUTH_REQUIRED" in final_text

        return {
            "status": "auth_required" if auth_required else ("rascunho_criado" if history.is_done() else "incompleto"),
            "provider": resolved.provider,
            "model": resolved.model,
            "criativos_anexados": caminhos_validos,
            "steps_executados": history.number_of_steps(),
            "sucesso": False if auth_required else bool(history.is_done() and not history.has_errors()),
            "resultado_navegador": final_text,
            "erros": [err for err in history.errors() if err],
        }
    finally:
        await browser.stop()
