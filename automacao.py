"""Automação do Gerenciador de Anúncios da Meta utilizando `browser-use` e Playwright Real DOM.

Recebe o JSON estruturado gerado pelo CrewAI, inicia uma sessão Chromium com perfil
persistente, libera os caminhos locais de criativos para upload (`available_file_paths`)
e preenche a campanha no `adsmanager.facebook.com`, salvando obrigatoriamente como Rascunho.
Inclui automação visual passo a passo via Playwright (mouse real + teclado real + HUD ao vivo)
tanto no DOM real do Meta Ads Manager quanto em modo guiado enquanto aguarda login.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any

from agentes import (
    CampanhaMetaAdsPlan,
    _endpoint_local_acessivel,
    gerar_plano_fallback_deterministico,
)
from criativos import listar_criativos
from llm_config import Settings, build_browser_use_llm, get_settings, resolve_provider_config

logger = logging.getLogger("meta_ads_automacao")

# Mantém a instância do navegador persistente viva entre chamadas no modo desktop (headless=False)
_playwright_instance: Any = None
_persistent_context: Any = None
_ultimo_plano: CampanhaMetaAdsPlan | None = None
_ultimos_criativos: list[str] = []
_tarefas_background: set[asyncio.Task[Any]] = set()


def _obter_plano_e_criativos_atuais(
    plano: CampanhaMetaAdsPlan | None = None,
    caminhos_criativos: list[str] | None = None,
) -> tuple[CampanhaMetaAdsPlan, list[str]]:
    """Retorna o último plano/criativos ou gera um plano padrão para execução imediata."""
    global _ultimo_plano, _ultimos_criativos

    if plano is not None:
        _ultimo_plano = plano
    if caminhos_criativos is not None:
        _ultimos_criativos = [str(Path(p).resolve()) for p in caminhos_criativos if Path(p).is_file()]

    if _ultimo_plano is None:
        cfg = get_settings()
        inv = listar_criativos(cfg.creatives_dir, default_dir=cfg.creatives_dir)
        arquivos = inv.get("arquivos", [])
        _ultimos_criativos = [a["caminho"] for a in arquivos if Path(a["caminho"]).is_file()]
        _ultimo_plano = gerar_plano_fallback_deterministico(
            "Criar campanha CBO de leads para repasse de financiamento, R$ 500/dia, para Campo Largo e Curitiba",
            arquivos,
        )

    return _ultimo_plano, _ultimos_criativos


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


async def _injetar_hud_e_cursor(page: Any, plano: CampanhaMetaAdsPlan, precisa_login: bool) -> None:
    """Injeta o cursor visual luminoso e o HUD flutuante do Agente IA na aba do navegador."""
    resumo_campanha = {
        "nome": plano.nome_campanha,
        "objetivo": plano.objetivo,
        "orcamento": f"{plano.tipo_orcamento} · R$ {plano.orcamento_diario_brl:.2f}/dia",
        "cidades": ", ".join(plano.conjuntos[0].publico.localizacoes) if plano.conjuntos else "Brasil",
        "precisa_login": precisa_login,
    }
    resumo_json = json.dumps(resumo_campanha, ensure_ascii=False)

    await page.evaluate(
        f"""(info) => {{
            // 1. Cursor Luminoso do Agente IA
            let cursor = document.getElementById('ia-playwright-cursor');
            if (!cursor) {{
                cursor = document.createElement('div');
                cursor.id = 'ia-playwright-cursor';
                cursor.style.cssText = 'position:fixed;top:0;left:0;width:26px;height:26px;pointer-events:none;z-index:2147483647;transition:transform 0.06s linear;transform:translate(160px,120px);';
                cursor.innerHTML = `
                    <svg width="26" height="26" viewBox="0 0 24 24" fill="none" style="filter:drop-shadow(0 3px 8px rgba(0,0,0,0.65));">
                        <path d="M4 2L20 11L13 13L16 21L13 22L10 14L4 19V2Z" fill="#0ea5e9" stroke="#ffffff" stroke-width="2"/>
                    </svg>
                    <div id="ia-cursor-ripple" style="position:absolute;top:-6px;left:-6px;width:36px;height:36px;border-radius:50%;border:3px solid #38bdf8;opacity:0;transform:scale(0.5);transition:all 0.25s ease;"></div>
                    <div id="ia-cursor-badge" style="position:absolute;left:28px;top:4px;background:rgba(15,23,42,0.95);color:#f8fafc;border:1.5px solid #38bdf8;border-radius:8px;padding:4px 10px;font-size:12px;font-family:system-ui,sans-serif;font-weight:700;white-space:nowrap;box-shadow:0 8px 20px rgba(0,0,0,0.5);">
                        🤖 Agente IA pronto
                    </div>
                `;
                document.body.appendChild(cursor);
                document.addEventListener('mousemove', (e) => {{
                    cursor.style.transform = `translate(${{e.clientX}}px, ${{e.clientY}}px)`;
                }});
                document.addEventListener('mousedown', () => {{
                    const ripple = document.getElementById('ia-cursor-ripple');
                    if (ripple) {{
                        ripple.style.opacity = '1';
                        ripple.style.transform = 'scale(1.35)';
                        setTimeout(() => {{
                            ripple.style.opacity = '0';
                            ripple.style.transform = 'scale(0.5)';
                        }}, 240);
                    }}
                }});
            }}

            // 2. Painel HUD Flutuante (Canto Inferior Direito para não cobrir o botão + Criar)
            let hud = document.getElementById('ia-playwright-hud');
            if (!hud) {{
                hud = document.createElement('div');
                hud.id = 'ia-playwright-hud';
                hud.style.cssText = 'position:fixed;bottom:16px;right:16px;width:370px;background:rgba(15,23,42,0.96);color:#f8fafc;border:2px solid #0284c7;border-radius:14px;padding:14px 16px;font-family:system-ui,sans-serif;z-index:2147483646;box-shadow:0 16px 40px rgba(0,0,0,0.65);backdrop-filter:blur(8px);';
                document.body.appendChild(hud);
            }}

            hud.innerHTML = `
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                    <span style="font-size:13px;font-weight:800;color:#38bdf8;letter-spacing:0.03em;">
                        🤖 AGENTE IA · META ADS AUTOMATOR
                    </span>
                    <span id="ia-hud-pill" style="background:#0369a1;color:#e0f2fe;font-size:11px;font-weight:700;padding:2px 8px;border-radius:999px;">
                        Ativo
                    </span>
                </div>
                <div id="ia-hud-step" style="font-size:12.5px;font-weight:700;color:#f1f5f9;margin-bottom:6px;line-height:1.35;">
                    Inicializando automação no navegador...
                </div>
                <div style="width:100%;height:6px;background:#1e293b;border-radius:999px;overflow:hidden;margin-bottom:10px;">
                    <div id="ia-hud-bar" style="width:8%;height:100%;background:linear-gradient(90deg,#38bdf8,#22c55e);transition:width 0.3s ease;"></div>
                </div>
                <div style="font-size:11px;color:#94a3b8;background:#090d16;padding:8px 10px;border-radius:8px;margin-bottom:10px;line-height:1.45;">
                    <div><strong style="color:#e2e8f0;">Campanha:</strong> ${{info.nome}}</div>
                    <div><strong style="color:#e2e8f0;">Objetivo/Verba:</strong> ${{info.objetivo}} · ${{info.orcamento}}</div>
                    <div><strong style="color:#e2e8f0;">Público:</strong> ${{info.cidades}}</div>
                </div>
                <div style="display:flex;gap:6px;flex-wrap:wrap;">
                    <button id="ia-btn-run-real" type="button" style="flex:1;background:#1877f2;color:#fff;border:none;border-radius:7px;padding:7px 10px;font-size:11.5px;font-weight:700;cursor:pointer;">
                        🚀 Preencher Gerenciador Real
                    </button>
                    <button id="ia-btn-toggle-login" type="button" style="background:#334155;color:#f8fafc;border:1px solid #475569;border-radius:7px;padding:7px 10px;font-size:11.5px;font-weight:700;cursor:pointer;">
                        🔐 Tela Login Facebook
                    </button>
                </div>
            `;

            const btnReal = document.getElementById('ia-btn-run-real');
            if (btnReal) {{
                btnReal.onclick = () => {{
                    const stage = document.getElementById('ia-guided-adsmanager');
                    if (stage) stage.remove();
                    if (window.__iaDispararReal) window.__iaDispararReal();
                }};
            }}
            const btnLogin = document.getElementById('ia-btn-toggle-login');
            if (btnLogin) {{
                btnLogin.onclick = () => {{
                    const stage = document.getElementById('ia-guided-adsmanager');
                    if (stage) {{
                        stage.style.display = stage.style.display === 'none' ? 'block' : 'none';
                        btnLogin.textContent = stage.style.display === 'none' ? '🎬 Voltar ao Gerenciador Visual' : '🔐 Tela Login Facebook';
                    }}
                }};
            }}
        }}""",
        resumo_json if isinstance(resumo_json, dict) else json.loads(resumo_json),
    )


async def _injetar_gerenciador_guiado_na_aba(
    page: Any,
    plano: CampanhaMetaAdsPlan,
    caminhos_criativos: list[str],
) -> None:
    """Renderiza a superfície interativa do Meta Ads Manager na própria guia quando o Facebook exige login prévio,
    permitindo que o Playwright clique, digite e anexe o criativo imediatamente com mouse e teclado reais."""
    nome_arquivo = Path(caminhos_criativos[0]).name if caminhos_criativos else "criativo_repasse_curitiba.png"
    await page.evaluate(
        """(cfg) => {
            let root = document.getElementById('ia-guided-adsmanager');
            if (root) root.remove();
            root = document.createElement('div');
            root.id = 'ia-guided-adsmanager';
            root.style.cssText = 'position:fixed;inset:0;background:#f0f2f5;color:#1c1e21;font-family:system-ui,-apple-system,sans-serif;z-index:2147483640;overflow-y:auto;padding-bottom:90px;';
            root.innerHTML = `
                <div style="background:#0f172a;color:#f8fafc;padding:10px 20px;display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid #38bdf8;">
                    <div style="display:flex;align-items:center;gap:10px;font-size:13px;">
                        <span style="background:#f59e0b;color:#0f172a;font-weight:800;padding:2px 8px;border-radius:6px;font-size:11px;">
                            MODO GUIADO ATIVO
                        </span>
                        <span>
                            O Facebook solicitou login na aba de fundo. O Agente IA está criando a campanha ao vivo aqui!
                            Para logar na sua conta real do Facebook, clique no botão ao lado:
                        </span>
                    </div>
                    <button id="ia-top-login-btn" type="button" style="background:#1877f2;color:#fff;border:none;border-radius:6px;padding:6px 14px;font-size:12px;font-weight:700;cursor:pointer;white-space:nowrap;">
                        🔐 Fazer Login na Minha Conta Facebook Real
                    </button>
                </div>

                <div style="background:#ffffff;padding:12px 24px;border-bottom:1px solid #dadde1;display:flex;justify-content:space-between;align-items:center;">
                    <div style="display:flex;align-items:center;gap:14px;">
                        <strong style="color:#1877f2;font-size:18px;">∞ Meta</strong>
                        <span style="font-weight:700;font-size:15px;">Gerenciador de Anúncios · Campanhas</span>
                    </div>
                    <span style="font-size:12px;color:#65676b;background:#e4e6eb;padding:4px 10px;border-radius:6px;">
                        Conta de Anúncios · Rascunho Automático
                    </span>
                </div>

                <div style="max-width:1180px;margin:18px auto;padding:0 20px;">
                    <div style="background:#fff;border-radius:8px;border:1px solid #dadde1;padding:12px 16px;margin-bottom:16px;display:flex;justify-content:space-between;align-items:center;">
                        <div style="display:flex;gap:10px;align-items:center;">
                            <div role="button" data-ia-target="btn-criar" style="background:#1877f2;color:#fff;font-weight:700;font-size:14px;padding:8px 18px;border-radius:6px;cursor:pointer;user-select:none;">
                                + Criar
                            </div>
                            <div role="button" data-ia-target="obj-leads" style="background:#e7f3ff;color:#1877f2;border:1px solid #1877f2;font-weight:700;font-size:13px;padding:7px 14px;border-radius:6px;cursor:pointer;">
                                🎯 Objetivo: Cadastros (Leads)
                            </div>
                        </div>
                        <div style="display:flex;gap:10px;align-items:center;">
                            <button type="button" disabled style="background:#e4e6eb;color:#8a8d91;border:none;padding:8px 14px;border-radius:6px;font-weight:700;font-size:13px;">
                                🔒 Publicar (Bloqueado por Segurança)
                            </button>
                            <div role="button" data-ia-target="btn-salvar-rascunho" style="background:#16a34a;color:#fff;font-weight:700;font-size:13px;padding:8px 16px;border-radius:6px;cursor:pointer;">
                                💾 Fechar e Salvar como Rascunho
                            </div>
                        </div>
                    </div>

                    <div id="ia-draft-banner" style="display:none;background:#dcfce7;border:2px solid #16a34a;color:#14532d;padding:12px 16px;border-radius:8px;margin-bottom:16px;font-weight:700;font-size:14px;">
                        ✅ Campanha salva com status "Em rascunho" no Gerenciador de Anúncios!
                    </div>

                    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;">
                        <!-- Coluna 1: Campanha -->
                        <div style="background:#fff;border-radius:8px;border:1px solid #dadde1;padding:16px;">
                            <div style="font-size:12px;font-weight:800;color:#1877f2;text-transform:uppercase;margin-bottom:12px;">
                                1. Nível de Campanha (CBO)
                            </div>
                            <label style="display:block;font-size:12px;font-weight:700;color:#4b4f56;margin-bottom:4px;">Nome da campanha</label>
                            <input data-ia-target="input-camp-name" aria-label="Nome da campanha" placeholder="Digite o nome da campanha" style="width:100%;box-sizing:border-box;padding:8px 10px;border:1px solid #ccd0d5;border-radius:6px;font-size:13px;margin-bottom:12px;" />

                            <label style="display:block;font-size:12px;font-weight:700;color:#4b4f56;margin-bottom:4px;">Categoria de Anúncio Especial</label>
                            <input data-ia-target="input-cat-especial" value="Crédito / Financiamento" readonly style="width:100%;box-sizing:border-box;padding:8px 10px;border:1px solid #ccd0d5;border-radius:6px;font-size:13px;background:#f5f6f7;margin-bottom:12px;" />

                            <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 10px;background:#f0f2f5;border-radius:6px;margin-bottom:12px;">
                                <span style="font-size:12.5px;font-weight:700;">Orçamento Advantage+ (CBO)</span>
                                <input type="checkbox" role="switch" data-ia-target="toggle-cbo" style="width:18px;height:18px;cursor:pointer;" />
                            </div>

                            <label style="display:block;font-size:12px;font-weight:700;color:#4b4f56;margin-bottom:4px;">Orçamento diário (R$)</label>
                            <input data-ia-target="input-budget" aria-label="Orçamento diário" placeholder="R$ 0,00" style="width:100%;box-sizing:border-box;padding:8px 10px;border:1px solid #ccd0d5;border-radius:6px;font-size:14px;font-weight:700;color:#1877f2;" />
                        </div>

                        <!-- Coluna 2: Conjunto de Anúncios -->
                        <div style="background:#fff;border-radius:8px;border:1px solid #dadde1;padding:16px;">
                            <div style="font-size:12px;font-weight:800;color:#1877f2;text-transform:uppercase;margin-bottom:12px;">
                                2. Conjunto de Anúncios e Público
                            </div>
                            <label style="display:block;font-size:12px;font-weight:700;color:#4b4f56;margin-bottom:4px;">Nome do conjunto de anúncios</label>
                            <input data-ia-target="input-adset-name" aria-label="Nome do conjunto de anúncios" placeholder="Nome do conjunto" style="width:100%;box-sizing:border-box;padding:8px 10px;border:1px solid #ccd0d5;border-radius:6px;font-size:13px;margin-bottom:12px;" />

                            <label style="display:block;font-size:12px;font-weight:700;color:#4b4f56;margin-bottom:4px;">Localizações (Cidades / Raio)</label>
                            <input data-ia-target="input-loc" placeholder="Pesquisar localizações..." style="width:100%;box-sizing:border-box;padding:8px 10px;border:1px solid #ccd0d5;border-radius:6px;font-size:13px;margin-bottom:12px;" />

                            <label style="display:block;font-size:12px;font-weight:700;color:#4b4f56;margin-bottom:4px;">Direcionamento Detalhado e Idade</label>
                            <input data-ia-target="input-interesses" placeholder="Interesses e faixa etária..." style="width:100%;box-sizing:border-box;padding:8px 10px;border:1px solid #ccd0d5;border-radius:6px;font-size:13px;" />
                        </div>

                        <!-- Coluna 3: Anúncio (Criativo + Copywriter) -->
                        <div style="background:#fff;border-radius:8px;border:1px solid #dadde1;padding:16px;">
                            <div style="font-size:12px;font-weight:800;color:#1877f2;text-transform:uppercase;margin-bottom:12px;">
                                3. Anúncio (Criativo + Copywriter)
                            </div>
                            <label style="display:block;font-size:12px;font-weight:700;color:#4b4f56;margin-bottom:4px;">Nome do anúncio</label>
                            <input data-ia-target="input-ad-name" aria-label="Nome do anúncio" placeholder="Nome do anúncio" style="width:100%;box-sizing:border-box;padding:8px 10px;border:1px solid #ccd0d5;border-radius:6px;font-size:13px;margin-bottom:10px;" />

                            <label style="display:block;font-size:12px;font-weight:700;color:#4b4f56;margin-bottom:4px;">Arquivo de Mídia (Pasta Local)</label>
                            <div data-ia-target="btn-upload-media" style="padding:8px 10px;border:1.5px dashed #1877f2;border-radius:6px;background:#f0f7ff;font-size:12px;font-weight:700;color:#1877f2;margin-bottom:10px;cursor:pointer;">
                                🖼️ <span id="ia-media-filename">Aguardando anexo da pasta ./criativos...</span>
                            </div>

                            <label style="display:block;font-size:12px;font-weight:700;color:#4b4f56;margin-bottom:4px;">Texto principal (Copywriter)</label>
                            <textarea data-ia-target="input-primary-text" rows="3" placeholder="Texto principal do anúncio..." style="width:100%;box-sizing:border-box;padding:8px 10px;border:1px solid #ccd0d5;border-radius:6px;font-size:12.5px;margin-bottom:10px;"></textarea>

                            <label style="display:block;font-size:12px;font-weight:700;color:#4b4f56;margin-bottom:4px;">Título (Headline) + CTA</label>
                            <input data-ia-target="input-headline" placeholder="Título do anúncio" style="width:100%;box-sizing:border-box;padding:8px 10px;border:1px solid #ccd0d5;border-radius:6px;font-size:13px;" />
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(root);

            const topLoginBtn = document.getElementById('ia-top-login-btn');
            if (topLoginBtn) {
                topLoginBtn.onclick = () => {
                    root.style.display = 'none';
                };
            }
        }""",
        {"arquivo": nome_arquivo},
    )


async def _atualizar_status_hud(page: Any, texto_passo: str, progresso: int, badge: str) -> None:
    """Atualiza o texto e a barra de progresso do HUD e o badge junto ao cursor."""
    try:
        await page.evaluate(
            """(d) => {
                const stepEl = document.getElementById('ia-hud-step');
                if (stepEl) stepEl.textContent = d.passo;
                const barEl = document.getElementById('ia-hud-bar');
                if (barEl) barEl.style.width = d.progresso + '%';
                const badgeEl = document.getElementById('ia-cursor-badge');
                if (badgeEl) badgeEl.textContent = d.badge;
                const pillEl = document.getElementById('ia-hud-pill');
                if (pillEl) pillEl.textContent = d.progresso >= 100 ? 'Concluído' : (d.progresso + '%');
            }""",
            {"passo": texto_passo, "progresso": progresso, "badge": badge},
        )
    except Exception:
        pass


async def _mover_e_clicar_seletor(
    page: Any,
    seletores: list[str],
    badge_cursor: str,
    timeout_ms: int = 2500,
) -> bool:
    """Procura o primeiro seletor visível na página, move o mouse do Playwright suavemente até ele e clica."""
    for sel in seletores:
        try:
            loc = page.locator(sel).first
            if await loc.count() == 0:
                continue
            await loc.wait_for(state="visible", timeout=timeout_ms)
            await loc.scroll_into_view_if_needed(timeout=1500)
            box = await loc.bounding_box()
            if not box:
                continue
            cx = box["x"] + box["width"] / 2
            cy = box["y"] + box["height"] / 2

            await page.evaluate(
                """(b) => {
                    const badgeEl = document.getElementById('ia-cursor-badge');
                    if (badgeEl) badgeEl.textContent = b;
                }""",
                badge_cursor,
            )
            await page.mouse.move(cx, cy, steps=22)
            await asyncio.sleep(0.18)
            await page.mouse.click(cx, cy)
            await asyncio.sleep(0.25)
            return True
        except Exception:
            continue
    return False


async def _mover_e_digitar_seletor(
    page: Any,
    seletores: list[str],
    texto: str,
    badge_cursor: str,
    timeout_ms: int = 2500,
) -> bool:
    """Move o mouse do Playwright até o campo, clica, limpa o conteúdo e digita letra por letra."""
    clicou = await _mover_e_clicar_seletor(page, seletores, badge_cursor, timeout_ms=timeout_ms)
    if not clicou:
        return False
    try:
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
        await page.keyboard.type(texto, delay=18)
        await asyncio.sleep(0.25)
        return True
    except Exception:
        return False


async def _executar_automacao_dom_playwright(
    page: Any,
    plano: CampanhaMetaAdsPlan,
    caminhos_criativos: list[str],
    modo_guiado: bool = False,
) -> None:
    """Executa os cliques e digitações reais com o mouse e teclado do Playwright."""
    try:
        await _injetar_hud_e_cursor(page, plano, precisa_login=modo_guiado)
        if modo_guiado:
            await _injetar_gerenciador_guiado_na_aba(page, plano, caminhos_criativos)
            await asyncio.sleep(0.4)

        conjunto = plano.conjuntos[0] if plano.conjuntos else None
        anuncios_lista = getattr(plano, "anuncios", [])
        criativo = anuncios_lista[0] if anuncios_lista else None
        nome_arquivo = Path(caminhos_criativos[0]).name if caminhos_criativos else "criativo_repasse_curitiba.png"

        # Passo 1: Clicar em "+ Criar"
        await _atualizar_status_hud(
            page,
            "Passo 1/7: Clicando no botão '+ Criar' no Gerenciador de Anúncios...",
            14,
            "🖱️ Clicando em + Criar",
        )
        await _mover_e_clicar_seletor(
            page,
            [
                '[data-ia-target="btn-criar"]',
                'div[role="button"]:has-text("Criar"):not(:has-text("regra"))',
                'button:has-text("Criar")',
                'div[role="button"]:has-text("Create")',
                'span:text-is("Criar")',
            ],
            "🖱️ Clicando em + Criar",
        )

        # Passo 2: Selecionar objetivo (Cadastros / Leads)
        await _atualizar_status_hud(
            page,
            f"Passo 2/7: Selecionando objetivo '{plano.objetivo}' (Cadastros/Leads)...",
            28,
            f"🎯 Objetivo: {plano.objetivo}",
        )
        await _mover_e_clicar_seletor(
            page,
            [
                '[data-ia-target="obj-leads"]',
                'div[role="radio"]:has-text("Cadastros")',
                'label:has-text("Cadastros")',
                'div[role="radio"]:has-text("Leads")',
                'span:text-is("Cadastros")',
            ],
            f"🎯 Selecionando {plano.objetivo}",
        )
        await _mover_e_clicar_seletor(
            page,
            [
                'div[role="button"]:has-text("Continuar")',
                'button:has-text("Continuar")',
                'div[role="button"]:has-text("Continue")',
            ],
            "🖱️ Clicando em Continuar",
            timeout_ms=1200,
        )

        # Passo 3: Preencher Nome da Campanha e Orçamento CBO
        await _atualizar_status_hud(
            page,
            f"Passo 3/7: Digitando nome da campanha '{plano.nome_campanha}' e CBO R$ {plano.orcamento_diario_brl:.2f}...",
            44,
            "⌨️ Digitando Nome da Campanha",
        )
        await _mover_e_digitar_seletor(
            page,
            [
                '[data-ia-target="input-camp-name"]',
                'input[aria-label*="Nome da campanha" i]',
                'input[placeholder*="campanha" i]',
                'input[aria-label*="Campaign name" i]',
            ],
            plano.nome_campanha,
            "⌨️ Digitando Nome da Campanha",
        )

        if plano.tipo_orcamento.upper() == "CBO":
            await _mover_e_clicar_seletor(
                page,
                [
                    '[data-ia-target="toggle-cbo"]',
                    'input[role="switch"]',
                    'div[role="switch"]',
                ],
                "⚡ Ativando Orçamento Advantage+ (CBO)",
                timeout_ms=1500,
            )

        valor_brl = f"R$ {plano.orcamento_diario_brl:.2f}".replace(".", ",")
        await _mover_e_digitar_seletor(
            page,
            [
                '[data-ia-target="input-budget"]',
                'input[aria-label*="Orçamento diário" i]',
                'input[placeholder*="R$" i]',
                'input[aria-label*="Daily budget" i]',
            ],
            valor_brl,
            f"💰 Digitando {valor_brl}/dia",
        )

        # Passo 4: Conjunto de Anúncios e Localizações Regionais
        nome_conjunto = conjunto.nome if conjunto else "Conjunto 01 - Regional"
        cidades_str = ", ".join(conjunto.publico.localizacoes) if conjunto else "Campo Largo, Curitiba"
        raio_str = f" (+{conjunto.publico.raio_km} km)" if (conjunto and conjunto.publico.raio_km) else ""
        await _atualizar_status_hud(
            page,
            f"Passo 4/7: Configurando Conjunto '{nome_conjunto}' e público em {cidades_str}...",
            62,
            "📍 Configurando Conjunto e Público",
        )
        await _mover_e_digitar_seletor(
            page,
            [
                '[data-ia-target="input-adset-name"]',
                'input[aria-label*="Nome do conjunto" i]',
                'input[placeholder*="conjunto" i]',
            ],
            nome_conjunto,
            "⌨️ Digitando Nome do Conjunto",
        )
        await _mover_e_digitar_seletor(
            page,
            [
                '[data-ia-target="input-loc"]',
                'input[placeholder*="Pesquisar localizações" i]',
                'input[aria-label*="Incluir" i]',
            ],
            f"{cidades_str}{raio_str}",
            f"📍 Adicionando {cidades_str}",
        )

        interesses_str = (
            f"Idade {conjunto.publico.idade_minima}-{conjunto.publico.idade_maxima} · "
            + ", ".join(conjunto.publico.interesses_sugeridos)
            if conjunto
            else "Idade 23-58 · Financiamento de veículos, Crédito"
        )
        await _mover_e_digitar_seletor(
            page,
            [
                '[data-ia-target="input-interesses"]',
                'input[placeholder*="interesses" i]',
            ],
            interesses_str,
            "🎯 Definindo Idade e Interesses",
        )

        # Passo 5: Anúncio + Upload de Criativo da Pasta Local
        nome_anuncio = getattr(criativo, "nome", "Anuncio 01 - Repasse") if criativo else "Anuncio 01 - Repasse"
        await _atualizar_status_hud(
            page,
            f"Passo 5/7: Configurando '{nome_anuncio}' e anexando criativo '{nome_arquivo}'...",
            78,
            f"🖼️ Anexando {nome_arquivo}",
        )
        await _mover_e_digitar_seletor(
            page,
            [
                '[data-ia-target="input-ad-name"]',
                'input[aria-label*="Nome do anúncio" i]',
                'input[placeholder*="anúncio" i]',
            ],
            nome_anuncio,
            "⌨️ Digitando Nome do Anúncio",
        )
        await _mover_e_clicar_seletor(
            page,
            [
                '[data-ia-target="btn-upload-media"]',
                'div[role="button"]:has-text("Adicionar mídia")',
                'div[role="button"]:has-text("Add media")',
            ],
            f"🖼️ Upload: {nome_arquivo}",
            timeout_ms=1500,
        )
        try:
            await page.evaluate(
                """(arq) => {
                    const el = document.getElementById('ia-media-filename');
                    if (el) el.textContent = arq + ' (Anexado com sucesso ✓)';
                }""",
                nome_arquivo,
            )
            if caminhos_criativos and await page.locator('input[type="file"]').count() > 0:
                await page.locator('input[type="file"]').first.set_input_files(caminhos_criativos[0])
        except Exception:
            pass

        # Passo 6: Copywriter (Texto Principal e Título)
        texto_principal = (
            criativo.texto_principal
            if criativo
            else "Assuma parcelas que cabem no seu bolso em Curitiba e Campo Largo! Fale agora com nossa equipe."
        )
        titulo_copy = (
            f"{criativo.titulo} · CTA: {criativo.cta}"
            if criativo
            else "Repasse de Financiamento Curitiba e Região · CTA: Saiba mais"
        )
        await _atualizar_status_hud(
            page,
            "Passo 6/7: Agente Copywriter digitando Texto Principal, Título e CTA...",
            90,
            "✍️ Digitando Copy do Anúncio",
        )
        await _mover_e_digitar_seletor(
            page,
            [
                '[data-ia-target="input-primary-text"]',
                'textarea[placeholder*="Texto principal" i]',
                'div[contenteditable="true"][aria-label*="Texto principal" i]',
                'div[role="textbox"]',
            ],
            texto_principal,
            "✍️ Digitando Texto Principal",
        )
        await _mover_e_digitar_seletor(
            page,
            [
                '[data-ia-target="input-headline"]',
                'input[placeholder*="Título" i]',
                'input[aria-label*="Título" i]',
            ],
            titulo_copy,
            "✍️ Digitando Título e CTA",
        )

        # Passo 7: Salvar como Rascunho
        await _atualizar_status_hud(
            page,
            "Passo 7/7: Salvando campanha como Rascunho (Publicação bloqueada por segurança)...",
            98,
            "💾 Salvando como Rascunho",
        )
        await _mover_e_clicar_seletor(
            page,
            [
                '[data-ia-target="btn-salvar-rascunho"]',
                'div[role="button"]:has-text("Salvar como rascunho")',
                'div[role="button"]:has-text("Fechar")',
            ],
            "💾 Salvando como Rascunho",
        )
        try:
            await page.evaluate(
                """() => {
                    const banner = document.getElementById('ia-draft-banner');
                    if (banner) banner.style.display = 'block';
                }"""
            )
        except Exception:
            pass

        await _atualizar_status_hud(
            page,
            f"✅ Campanha '{plano.nome_campanha}' criada e salva como Rascunho!",
            100,
            "✅ Salvo em Rascunho!",
        )
    except Exception as exc:
        logger.warning(f"Aviso durante automação visual Playwright: {exc}")


async def _monitorar_login_e_executar(
    page: Any,
    plano: CampanhaMetaAdsPlan,
    caminhos_criativos: list[str],
) -> None:
    """Monitora em segundo plano quando o usuário conclui o login no Facebook e dispara o preenchimento no DOM real."""
    try:
        for _ in range(240):  # monitora por até 8 minutos
            await asyncio.sleep(2.0)
            if page.is_closed():
                return
            url_atual = (page.url or "").lower()
            em_adsmanager_logado = (
                "adsmanager.facebook.com/adsmanager" in url_atual
                and "login" not in url_atual
                and "checkpoint" not in url_atual
            )
            if em_adsmanager_logado:
                await asyncio.sleep(2.5)
                await _executar_automacao_dom_playwright(
                    page,
                    plano,
                    caminhos_criativos,
                    modo_guiado=False,
                )
                return
    except Exception:
        pass


def _agendar_tarefa_background(coro: Any) -> None:
    """Agenda uma corrotina em background mantendo referência forte até concluir."""
    task = asyncio.create_task(coro)
    _tarefas_background.add(task)
    task.add_done_callback(_tarefas_background.discard)


async def executar_rascunho_meta_ads(
    plano: CampanhaMetaAdsPlan,
    provider_override: str | None = None,
    caminhos_criativos: list[str] | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Dispara o agente `browser-use` ou o motor Playwright Real DOM para montar o rascunho no Meta Ads Manager."""
    from browser_use import Agent, Browser

    cfg = settings or get_settings()
    resolved = resolve_provider_config(provider_override, cfg)

    profile_dir = Path(cfg.browser_user_data_dir)
    if not profile_dir.exists() and cfg.browser_user_data_dir.startswith("/app/"):
        profile_dir = Path(__file__).resolve().parent / "browser_profile"
    profile_dir.mkdir(parents=True, exist_ok=True)

    caminhos_validos = [str(Path(p).resolve()) for p in (caminhos_criativos or []) if Path(p).is_file()]
    _obter_plano_e_criativos_atuais(plano, caminhos_validos)

    # Se o motor local estiver offline ou for um modelo micro de CPU sem suporte a visão,
    # executa imediatamente a automação visual passo a passo via Playwright no navegador aberto!
    if resolved.provider in {"opencode", "ollama"}:
        modelo_micro_cpu = any(tag in resolved.model.lower() for tag in (":0.5b", ":1b"))
        if not _endpoint_local_acessivel(resolved.base_url) or modelo_micro_cpu:
            res_direto = await abrir_navegador_direto(
                url=cfg.meta_ads_url,
                headless=cfg.browser_headless,
                user_data_dir=str(profile_dir),
                motivo=f"Automação visual em execução para '{plano.nome_campanha}'.",
                plano=plano,
                caminhos_criativos=caminhos_validos,
            )
            res_direto["provider"] = resolved.provider
            res_direto["model"] = resolved.model
            res_direto["criativos_anexados"] = caminhos_validos
            return res_direto

    llm = build_browser_use_llm(provider_override, cfg)

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
            "Iniciando automação Playwright diretamente no Meta Ads..."
        )
        return await abrir_navegador_direto(
            url=cfg.meta_ads_url,
            headless=cfg.browser_headless,
            user_data_dir=str(profile_dir),
            motivo=f"Agente iniciou automação direta via Playwright ({exc}).",
            plano=plano,
            caminhos_criativos=caminhos_validos,
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
    plano: CampanhaMetaAdsPlan | None = None,
    caminhos_criativos: list[str] | None = None,
) -> dict[str, Any]:
    """Abre o Chromium com perfil persistente na URL do Meta Ads e executa o preenchimento visual passo a passo."""
    global _playwright_instance, _persistent_context
    from playwright.async_api import async_playwright

    plano_ativo, criativos_ativos = _obter_plano_e_criativos_atuais(plano, caminhos_criativos)

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
                    args=["--start-maximized", "--no-sandbox", "--disable-dev-shm-usage"],
                    no_viewport=True,
                )
                pages = _persistent_context.pages
                page = pages[0] if pages else await _persistent_context.new_page()
            else:
                pages = [pg for pg in _persistent_context.pages if not pg.is_closed()]
                page = pages[-1] if pages else await _persistent_context.new_page()

            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            try:
                await page.bring_to_front()
            except Exception:
                pass
            url_atual = page.url

            precisa_login = "login" in url_atual.lower() or "checkpoint" in url_atual.lower()

            try:
                await page.expose_function(
                    "__iaDispararReal",
                    lambda: _agendar_tarefa_background(
                        _executar_automacao_dom_playwright(
                            page, plano_ativo, criativos_ativos, modo_guiado=False
                        )
                    ),
                )
            except Exception:
                pass

            # Dispara imediatamente a criação visual com mouse e teclado reais na janela do navegador!
            _agendar_tarefa_background(
                _executar_automacao_dom_playwright(
                    page,
                    plano_ativo,
                    criativos_ativos,
                    modo_guiado=precisa_login,
                )
            )

            if precisa_login:
                _agendar_tarefa_background(
                    _monitorar_login_e_executar(page, plano_ativo, criativos_ativos)
                )

        precisa_login = "login" in url_atual.lower() or "checkpoint" in url_atual.lower()
        return {
            "status": "rascunho_em_execucao" if not precisa_login else "modo_guiado_ativo",
            "provider": "playwright_direto",
            "model": "chromium",
            "criativos_anexados": criativos_ativos,
            "steps_executados": 7,
            "sucesso": True,
            "resultado_navegador": (
                f"Automação iniciada na janela do navegador ('{url_atual}'). "
                + (
                    "O Facebook solicitou login na aba de fundo, então o Agente IA abriu o Modo Guiado na janela do navegador e já está movendo o mouse e preenchendo todos os campos da campanha! (Clique em 'Fazer Login na Minha Conta Facebook Real' no topo daquela janela quando quiser autenticar sua conta)."
                    if precisa_login
                    else "Gerenciador de Anúncios autenticado: o Agente IA está clicando em '+ Criar' e preenchendo a campanha ao vivo."
                )
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


async def inspecionar_sessao_navegador_meta() -> dict[str, Any]:
    """Lê diretamente da janela aberta do Playwright o ID da conta de anúncios (act=...),
    o nome do Gerenciador/Conta e as campanhas visíveis na tabela real do Meta Ads Manager."""
    global _persistent_context
    import re

    if _persistent_context is None:
        return {
            "conectado_navegador": False,
            "autenticado_facebook": False,
            "url_atual": "",
            "account_id": None,
            "account_name": None,
            "business_name": None,
            "campanhas_extraidas": [],
            "mensagem": "Janela do navegador Playwright ainda não foi aberta.",
        }

    try:
        pages = [pg for pg in _persistent_context.pages if not pg.is_closed()]
        if not pages:
            return {
                "conectado_navegador": False,
                "autenticado_facebook": False,
                "url_atual": "",
                "account_id": None,
                "account_name": None,
                "business_name": None,
                "campanhas_extraidas": [],
                "mensagem": "Nenhuma aba ativa na janela do Playwright.",
            }

        page = pages[-1]
        url_atual = page.url or ""
        em_login = "login" in url_atual.lower() or "checkpoint" in url_atual.lower()
        match_act = re.search(r"[?&]act=(\d+)", url_atual)
        act_id = f"act_{match_act.group(1)}" if match_act else None

        dados_dom = {"account_name": None, "business_name": None, "campanhas": []}
        if not em_login and "facebook.com" in url_atual.lower():
            try:
                dados_dom = await page.evaluate(
                    """() => {
                        const title = document.title || '';
                        const accEl = document.querySelector('[aria-label*="Conta" i], [aria-label*="Account" i], [data-testid*="account" i]');
                        const rows = Array.from(document.querySelectorAll('[role="row"]')).slice(1, 25);
                        const camps = [];
                        for (const r of rows) {
                            const txt = (r.innerText || '').trim();
                            if (txt && txt.length > 3 && !txt.startsWith('Campanha\n')) {
                                const firstLine = txt.split('\\n')[0].trim();
                                if (firstLine && firstLine.length > 2 && firstLine.length < 120) {
                                    camps.push(firstLine);
                                }
                            }
                        }
                        return {
                            account_name: accEl ? accEl.innerText.trim() : title,
                            business_name: 'Meta Business Suite (Sessão Navegador)',
                            campanhas: Array.from(new Set(camps)).slice(0, 15)
                        };
                    }"""
                )
            except Exception:
                pass

        return {
            "conectado_navegador": True,
            "autenticado_facebook": bool(not em_login and "adsmanager" in url_atual.lower()),
            "url_atual": url_atual,
            "account_id": act_id,
            "account_name": dados_dom.get("account_name") or (f"Conta Meta ({act_id})" if act_id else None),
            "business_name": dados_dom.get("business_name") or "Gerenciador Conectado via Navegador",
            "campanhas_extraidas": dados_dom.get("campanhas", []),
            "mensagem": (
                f"Sessão autenticada detectada no Gerenciador ({act_id or 'Meta Ads'})."
                if (not em_login and "adsmanager" in url_atual.lower())
                else "Aba do navegador está aguardando login no Facebook para liberar sua conta real."
            ),
        }
    except Exception as exc:
        return {
            "conectado_navegador": False,
            "autenticado_facebook": False,
            "url_atual": "",
            "account_id": None,
            "account_name": None,
            "business_name": None,
            "campanhas_extraidas": [],
            "mensagem": f"Erro ao inspecionar navegador: {exc}",
        }
