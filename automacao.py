"""Automação do Gerenciador de Anúncios da Meta utilizando `browser-use` (Playwright/CDP).

Recebe o JSON estruturado gerado pelo CrewAI, inicia uma sessão Chromium com perfil
persistente, libera os caminhos locais de criativos para upload (`available_file_paths`)
e preenche a campanha no `adsmanager.facebook.com`, salvando obrigatoriamente como Rascunho.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from agentes import CampanhaMetaAdsPlan, _endpoint_local_acessivel
from llm_config import Settings, build_browser_use_llm, get_settings, resolve_provider_config

logger = logging.getLogger("meta_ads_automacao")

# Mantém a instância do navegador persistente viva entre chamadas no modo desktop (headless=False)
_playwright_instance: Any = None
_persistent_context: Any = None


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

    profile_dir = Path(cfg.browser_user_data_dir)
    if not profile_dir.exists() and cfg.browser_user_data_dir.startswith("/app/"):
        profile_dir = Path(__file__).resolve().parent / "browser_profile"
    profile_dir.mkdir(parents=True, exist_ok=True)

    caminhos_validos = [str(Path(p).resolve()) for p in (caminhos_criativos or []) if Path(p).is_file()]

    # Se o motor local estiver offline ou for um modelo micro de CPU sem suporte a visão,
    # abre imediatamente a nova guia no Gerenciador de Anúncios sem travar a requisição.
    if resolved.provider in {"opencode", "ollama"}:
        modelo_micro_cpu = any(tag in resolved.model.lower() for tag in (":0.5b", ":1b"))
        if not _endpoint_local_acessivel(resolved.base_url) or modelo_micro_cpu:
            res_direto = await abrir_navegador_direto(
                url=cfg.meta_ads_url,
                headless=cfg.browser_headless,
                user_data_dir=str(profile_dir),
                motivo=f"Plano pronto ({plano.nome_campanha}). Guia aberta no Meta Ads Manager.",
            )
            res_direto["provider"] = resolved.provider
            res_direto["model"] = resolved.model
            res_direto["criativos_anexados"] = caminhos_validos
            return res_direto

    llm = build_browser_use_llm(provider_override, cfg)

    # Em containers Docker Linux (como root ou sem userns), o sandbox do Chromium precisa ficar desativado.
    in_docker = os.getenv("IN_DOCKER", "").lower() in {"1", "true", "yes"}
    browser = Browser(
        use_cloud=False,
        headless=cfg.browser_headless,
        chromium_sandbox=not in_docker,
        user_data_dir=str(profile_dir),
    )

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
    except Exception as exc:
        logger.warning(
            f"browser-use agent encontrou erro ao orquestrar via LLM ({exc}). "
            "Iniciando navegador Playwright diretamente no Meta Ads..."
        )
        return await abrir_navegador_direto(
            url=cfg.meta_ads_url,
            headless=cfg.browser_headless,
            user_data_dir=str(profile_dir),
            motivo=f"Agente IA encontrou erro ({exc}). Navegador aberto diretamente no Gerenciador de Anúncios.",
        )
    finally:
        try:
            await browser.stop()
        except Exception:
            pass


async def abrir_navegador_direto(
    url: str,
    headless: bool = False,
    user_data_dir: str | None = None,
    motivo: str | None = None,
) -> dict[str, Any]:
    """Abre uma nova guia no Chromium com perfil persistente direto na URL do Meta Ads e mantém a janela aberta."""
    global _playwright_instance, _persistent_context
    from playwright.async_api import async_playwright

    raw_dir = user_data_dir or "./browser_profile"
    profile = Path(raw_dir)
    if not profile.exists() and raw_dir.startswith("/app/"):
        profile = Path(__file__).resolve().parent / "browser_profile"
    profile = profile.resolve()
    profile.mkdir(parents=True, exist_ok=True)

    try:
        if headless:
            async with async_playwright() as p:
                context = await p.chromium.launch_persistent_context(
                    user_data_dir=str(profile),
                    headless=True,
                    args=["--no-sandbox", "--disable-dev-shm-usage"],
                )
                page = context.pages[0] if context.pages else await context.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=45000)
                url_atual = page.url
        else:
            # Modo visual desktop: mantém o navegador aberto e abre uma nova guia a cada chamada
            if _playwright_instance is None:
                _playwright_instance = await async_playwright().start()

            context_alive = False
            if _persistent_context is not None:
                try:
                    _ = _persistent_context.pages
                    context_alive = True
                except Exception:
                    context_alive = False

            if not context_alive:
                _persistent_context = await _playwright_instance.chromium.launch_persistent_context(
                    user_data_dir=str(profile),
                    headless=False,
                    args=["--no-sandbox", "--disable-dev-shm-usage"],
                )
                pages = _persistent_context.pages
                page = pages[0] if pages and pages[0].url == "about:blank" else await _persistent_context.new_page()
            else:
                page = await _persistent_context.new_page()

            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            try:
                await page.bring_to_front()
                await page.evaluate(
                    """() => {
                        if (document.getElementById('ia-playwright-cursor')) return;
                        const cursor = document.createElement('div');
                        cursor.id = 'ia-playwright-cursor';
                        cursor.style.cssText = 'position:fixed;top:20px;left:20px;width:22px;height:22px;border-radius:50%;background:rgba(56,189,248,0.85);border:2px solid #fff;box-shadow:0 0 14px rgba(56,189,248,0.9);pointer-events:none;z-index:2147483647;transition:transform 0.08s linear;';
                        const label = document.createElement('div');
                        label.textContent = '🤖 Agente IA Meta Ads';
                        label.style.cssText = 'position:absolute;left:26px;top:0;background:#0f172a;color:#38bdf8;padding:3px 8px;border-radius:6px;font-size:11px;font-family:sans-serif;font-weight:bold;white-space:nowrap;border:1px solid #38bdf8;';
                        cursor.appendChild(label);
                        document.body.appendChild(cursor);
                        document.addEventListener('mousemove', (e) => {
                            cursor.style.transform = `translate(${e.clientX}px, ${e.clientY}px)`;
                        });
                    }"""
                )
                for pos_x, pos_y in [(180, 140), (420, 260), (310, 340)]:
                    await page.mouse.move(pos_x, pos_y, steps=18)
            except Exception:
                pass
            url_atual = page.url

        precisa_login = "login" in url_atual.lower() or "checkpoint" in url_atual.lower()
        return {
            "status": "auth_required" if precisa_login else "navegador_aberto",
            "provider": "playwright_direto",
            "model": "chromium",
            "criativos_anexados": [],
            "steps_executados": 1,
            "sucesso": True,
            "resultado_navegador": (
                f"Nova guia aberta em '{url_atual}'. "
                + ("Atenção: Faça login na sua conta do Meta Ads no navegador." if precisa_login else "Gerenciador de Anúncios acessado com sucesso.")
                + (f" ({motivo})" if motivo else "")
            ),
            "erros": [],
        }
    except Exception as exc:
        return {
            "status": "erro_navegador",
            "provider": "playwright_direto",
            "model": "chromium",
            "criativos_anexados": [],
            "steps_executados": 0,
            "sucesso": False,
            "resultado_navegador": f"Falha ao abrir navegador: {exc}",
            "erros": [str(exc)],
        }
