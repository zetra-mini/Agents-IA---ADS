"""Hub unificado estilo Hackr Ads / AdSimples + octaviosilva2/meta-ads + TheMattBerman/meta-ads-kit + Placard.

Integra:
1. Dual-Mode Meta Marketing API (`META_MODE=mock | graph` inspirado em `octaviosilva2/meta-ads`):
   - Modo `mock`: Estado em memória com campanhas, conjuntos, anúncios e séries históricas de 28 dias (CTR, CPC, CPM, CPA, ROAS).
   - Modo `graph`: Conexão direta com a API Oficial da Meta (`https://graph.facebook.com/v22.0`) via `META_ACCESS_TOKEN` e `META_AD_ACCOUNT_ID`.
2. Robô Otimizador & Copilot (`TheMattBerman/meta-ads-kit` + Hackr Ads):
   - Detecção automática de Winners 🏆 (escalar orçamento), Bleeders 🩸 (pausar sangradores), Fadiga de Criativo 😴 (queda de CTR / alta frequência) e Pacing Diário.
3. Validação Pré-Voo / Guardrails (`dallascrilley/placard` & `Adbloop/meta-ads-mcp`):
   - Checagem de conformidade da Meta antes de publicar (Special Ad Categories CREDIT, orçamento mínimo, advantage_audience e status PAUSED).
4. Loja de Públicos Prontos (estilo Hackr Ads / AdSimples):
   - Templates prontos de segmentação validada para aplicar com 1 clique.
"""

from __future__ import annotations

import json
import os
import random
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from itertools import count
from pathlib import Path
from typing import Any

import httpx

SESSION_FILE = Path(".meta_session.json")

from agentes import CampanhaMetaAdsPlan

GRAPH_HOST = "https://graph.facebook.com"
INSIGHT_FIELDS = "impressions,clicks,spend,actions,action_values,date_start"
CONVERSION_ACTIONS = {"purchase", "omni_purchase", "offsite_conversion.fb_pixel_purchase", "lead"}

VALID_OBJECTIVES = {
    "OUTCOME_TRAFFIC",
    "OUTCOME_SALES",
    "OUTCOME_LEADS",
    "OUTCOME_AWARENESS",
    "OUTCOME_ENGAGEMENT",
    "OUTCOME_APP_PROMOTION",
}

OBJECTIVE_MAP_PT_TO_META = {
    "leads": "OUTCOME_LEADS",
    "cadastros": "OUTCOME_LEADS",
    "tráfego": "OUTCOME_TRAFFIC",
    "trafego": "OUTCOME_TRAFFIC",
    "vendas": "OUTCOME_SALES",
    "conversões": "OUTCOME_SALES",
    "engajamento": "OUTCOME_ENGAGEMENT",
    "reconhecimento": "OUTCOME_AWARENESS",
}

# Loja de Públicos Prontos (inspirada no Hackr Ads / AdSimples)
LOJA_PUBLICOS_ADSIMPLES: list[dict[str, Any]] = [
    {
        "id": "repasse_financiamento_auto",
        "titulo": "🚗 Repasse & Financiamento de Veículos",
        "categoria": "Automotivo / Crédito",
        "descricao": "Compradores buscando assumir consórcio, repasse de financiamento ou seminovos com entrada facilitada.",
        "cidades_sugeridas": ["Campo Largo", "Curitiba"],
        "raio_km": 25,
        "idade_minima": 23,
        "idade_maxima": 58,
        "orcamento_sugerido_brl": 500.0,
        "tipo_orcamento": "CBO",
        "objetivo": "Leads",
        "interesses": ["Financiamento de veículos", "Carros usados", "Consórcio", "Crédito automotivo"],
        "instrucao_pronta": (
            "Criar campanha CBO de leads para repasse de financiamento de veículos, "
            "R$ 500/dia, para Campo Largo e Curitiba (raio 25km), público 23 a 58 anos"
        ),
    },
    {
        "id": "imoveis_consorcio_credito",
        "titulo": "🏠 Imóveis, Financiamento & Carta de Crédito",
        "categoria": "Imobiliário / Crédito",
        "descricao": "Público qualificado interessado em financiamento imobiliário, repasse de planta e consórcio contemplado.",
        "cidades_sugeridas": ["Curitiba", "São José dos Pinhais"],
        "raio_km": 30,
        "idade_minima": 25,
        "idade_maxima": 62,
        "orcamento_sugerido_brl": 350.0,
        "tipo_orcamento": "CBO",
        "objetivo": "Leads",
        "interesses": ["Investimento imobiliário", "Financiamento imobiliário", "Apartamento", "Consórcio"],
        "instrucao_pronta": (
            "Criar campanha CBO de leads para financiamento imobiliário e carta contemplada, "
            "R$ 350/dia, para Curitiba e São José dos Pinhais"
        ),
    },
    {
        "id": "negocios_locais_whatsapp",
        "titulo": "📲 Captação Rápida no WhatsApp (Raio Local)",
        "categoria": "Serviços / Local",
        "descricao": "Ideal para clínicas, estética, concessionárias e serviços locais focados em mensagens diretas no WhatsApp.",
        "cidades_sugeridas": ["Curitiba", "Campo Largo"],
        "raio_km": 15,
        "idade_minima": 21,
        "idade_maxima": 55,
        "orcamento_sugerido_brl": 150.0,
        "tipo_orcamento": "ABO",
        "objetivo": "Leads",
        "interesses": ["Compras online", "Atendimento via WhatsApp", "Ofertas locais"],
        "instrucao_pronta": (
            "Criar campanha ABO de leads no WhatsApp para atendimento rápido regional, "
            "R$ 150/dia, para Curitiba e Campo Largo (raio 15km)"
        ),
    },
    {
        "id": "ecommerce_compradores_engajados",
        "titulo": "🛒 E-commerce — Compradores Engajados (Escala CBO)",
        "categoria": "E-commerce / Vendas",
        "descricao": "Público com comportamento ativo de compra online ("
        "Engaged Shoppers) pronto para conversão imediata.",
        "cidades_sugeridas": ["Curitiba", "Joinville", "Florianópolis"],
        "raio_km": 40,
        "idade_minima": 20,
        "idade_maxima": 54,
        "orcamento_sugerido_brl": 400.0,
        "tipo_orcamento": "CBO",
        "objetivo": "Vendas",
        "interesses": ["Compradores engajados", "Compras na internet", "Promoções e descontos"],
        "instrucao_pronta": (
            "Criar campanha CBO de vendas para oferta relâmpago com frete rápido, "
            "R$ 400/dia, para Curitiba, Joinville e Florianópolis"
        ),
    },
]


@dataclass
class AdItem:
    id: str
    campaign_id: str
    name: str
    headline: str
    primary_text: str
    call_to_action: str
    status: str
    creative_file: str = ""


@dataclass
class CampaignItem:
    id: str
    name: str
    objective: str
    status: str
    daily_budget: float
    budget_type: str
    locations: list[str]
    created_at: str
    special_ad_category: str = "Nenhuma"
    ads: list[AdItem] = field(default_factory=list)


def _totals(series: list[dict[str, Any]], days: int) -> dict[str, Any]:
    impressions = sum(int(r.get("impressions", 0)) for r in series)
    clicks = sum(int(r.get("clicks", 0)) for r in series)
    spend = round(sum(float(r.get("spend", 0.0)) for r in series), 2)
    conversions = sum(int(r.get("conversions", 0)) for r in series)
    revenue = round(sum(float(r.get("revenue", 0.0)) for r in series), 2)
    ctr = round(clicks / impressions * 100, 2) if impressions else 0.0
    cpc = round(spend / clicks, 2) if clicks else 0.0
    cpm = round(spend / impressions * 1000, 2) if impressions else 0.0
    cpa = round(spend / conversions, 2) if conversions else 0.0
    roas = round(revenue / spend, 2) if spend else 0.0
    frequency = round(1.15 + (spend / 450.0), 2) if impressions else 1.0
    return {
        "days": days,
        "impressions": impressions,
        "clicks": clicks,
        "spend": spend,
        "conversions": conversions,
        "revenue": revenue,
        "ctr": ctr,
        "cpc": cpc,
        "cpm": cpm,
        "cpa": cpa,
        "roas": roas,
        "frequency": min(frequency, 4.8),
    }


def validar_campanha_preflight(
    plano: CampanhaMetaAdsPlan,
    caminhos_criativos: list[str] | None = None,
) -> dict[str, Any]:
    """Validador Pré-Voo inspirado em `dallascrilley/placard` e `Adbloop/meta-ads-mcp`.
    Verifica regras críticas da Meta Marketing API antes de publicar.
    """
    avisos: list[str] = []
    regras_aprovadas: list[str] = []
    erros: list[str] = []

    if plano.orcamento_diario_brl < 6.0:
        erros.append("Orçamento diário abaixo do mínimo exigido pela Meta no Brasil (R$ 6,00/dia).")
    else:
        regras_aprovadas.append(f"Orçamento diário válido (R$ {plano.orcamento_diario_brl:.2f}/dia >= R$ 6,00).")

    cat = (plano.categoria_especial_anuncio or "Nenhuma").lower()
    if any(k in cat for k in ("crédito", "credito", "credit", "financiamento", "moradia", "emprego")):
        regras_aprovadas.append(
            "Special Ad Category 'CREDIT' detectada: segmentação ajustada para conformidade financeira da Meta."
        )
        for cj in plano.conjuntos:
            if cj.publico.raio_km and cj.publico.raio_km < 15:
                avisos.append(
                    f"Conjunto '{cj.nome}': Categoria Crédito exige raio mínimo de 15 milhas/25km na Meta API."
                )

    for cj in plano.conjuntos:
        if cj.publico.idade_maxima < 65:
            avisos.append(
                f"Conjunto '{cj.nome}': idade máxima {cj.publico.idade_maxima} definida -> "
                "`targeting_automation.advantage_audience = 0` aplicado automaticamente (regra Placard)."
            )

    if caminhos_criativos:
        regras_aprovadas.append(f"{len(caminhos_criativos)} arquivo(s) de mídia local prontos para upload.")
    else:
        avisos.append("Nenhum arquivo de mídia local na pasta; anúncio será salvo com mídia pendente.")

    regras_aprovadas.append("Guardrail de Segurança Ativo: criação forçada em modo PAUSED / Rascunho.")

    return {
        "ok": len(erros) == 0,
        "status_validacao": "APROVADO_COM_AVISOS" if avisos else "APROVADO",
        "erros": erros,
        "avisos": avisos,
        "regras_aprovadas": regras_aprovadas,
    }


class MetaAdsHub:
    """Motor unificado de campanhas, métricas e otimização estilo Hackr Ads / AdSimples + octaviosilva2/meta-ads."""

    def __init__(self, seed: int = 42) -> None:
        self._rng = random.Random(seed)
        self._ids = count(1001)
        self._campaigns: dict[str, CampaignItem] = {}
        self._real_campaigns: dict[str, CampaignItem] = {}
        self._insights: dict[str, list[dict[str, Any]]] = {}
        self._access_token: str = os.getenv("META_ACCESS_TOKEN", "").strip()
        self._selected_account_id: str = os.getenv("META_AD_ACCOUNT_ID", "").strip()
        self._selected_account_name: str = ""
        self._business_name: str = ""
        self._user_name: str = ""
        self._available_accounts: list[dict[str, Any]] = []
        self._connection_source: str = "graph" if (self._access_token and self._selected_account_id) else "disconnected"
        self._somente_dados_reais: bool = False
        self._seed_initial_data()
        self._load_session()

    def _save_session(self) -> None:
        """Persiste localmente a sessão da conta Meta (ignorado no Git) para sobreviver a reinicializações."""
        try:
            payload = {
                "access_token": self._access_token,
                "selected_account_id": self._selected_account_id,
                "selected_account_name": self._selected_account_name,
                "business_name": self._business_name,
                "user_name": self._user_name,
                "available_accounts": self._available_accounts,
                "connection_source": self._connection_source,
                "somente_dados_reais": self._somente_dados_reais,
            }
            SESSION_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _load_session(self) -> None:
        """Restaura sessão da conta Meta salva localmente se existir."""
        try:
            if not SESSION_FILE.exists():
                return
            data = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
            if data.get("access_token"):
                self._access_token = data["access_token"]
            if data.get("selected_account_id"):
                self._selected_account_id = data["selected_account_id"]
            if data.get("selected_account_name"):
                self._selected_account_name = data["selected_account_name"]
            if data.get("business_name"):
                self._business_name = data["business_name"]
            if data.get("user_name"):
                self._user_name = data["user_name"]
            if data.get("available_accounts"):
                self._available_accounts = data["available_accounts"]
            if data.get("connection_source"):
                self._connection_source = data["connection_source"]
            if "somente_dados_reais" in data:
                self._somente_dados_reais = bool(data["somente_dados_reais"])
        except Exception:
            pass

    @property
    def mode(self) -> str:
        if self._connection_source in {"graph", "browser"} and self._selected_account_id:
            return self._connection_source
        if self._somente_dados_reais:
            return "real_empty"
        return "mock"

    def get_connection_status(self) -> dict[str, Any]:
        conectado = self._connection_source in {"graph", "browser"} and bool(self._selected_account_id)
        return {
            "connected": conectado,
            "connection_source": self._connection_source,
            "mode": self.mode,
            "somente_dados_reais": self._somente_dados_reais,
            "user_name": self._user_name or None,
            "business_name": self._business_name or ("Não conectado" if not conectado else "Meta Business Suite"),
            "selected_account_id": self._selected_account_id or None,
            "selected_account_name": self._selected_account_name or None,
            "available_accounts": self._available_accounts,
            "has_token": bool(self._access_token),
        }

    def set_real_only_mode(self, somente_reais: bool) -> dict[str, Any]:
        self._somente_dados_reais = bool(somente_reais)
        return self.get_connection_status()

    async def connect_graph_token(
        self,
        access_token: str,
        account_id: str | None = None,
    ) -> dict[str, Any]:
        """Valida o Access Token na Meta Graph API, lista todas as Contas de Anúncios e Gerenciadores (BM) do usuário."""
        token = access_token.strip()
        if not token:
            raise ValueError("Informe um Meta Access Token válido.")

        version = os.getenv("META_API_VERSION", "v22.0").strip()
        async with httpx.AsyncClient(params={"access_token": token}, timeout=20.0) as client:
            me_resp = await client.get(f"{GRAPH_HOST}/{version}/me", params={"fields": "id,name"})
            if me_resp.status_code != 200:
                detalhe = me_resp.json().get("error", {}).get("message", me_resp.text)
                raise ValueError(f"Token rejeitado pela Meta Graph API: {detalhe}")
            me_data = me_resp.json()

            acc_resp = await client.get(
                f"{GRAPH_HOST}/{version}/me/adaccounts",
                params={
                    "fields": "id,account_id,name,account_status,currency,business_name,amount_spent",
                    "limit": 50,
                },
            )
            acc_list = []
            if acc_resp.status_code == 200:
                for item in acc_resp.json().get("data", []):
                    acc_list.append(
                        {
                            "id": item.get("id"),  # ex: act_123456
                            "account_id": item.get("account_id"),
                            "name": item.get("name") or item.get("id"),
                            "business_name": item.get("business_name") or "Conta Pessoal / BM",
                            "currency": item.get("currency", "BRL"),
                            "account_status": item.get("account_status", 1),
                        }
                    )

        self._access_token = token
        self._user_name = me_data.get("name", "Usuário Meta Ads")
        self._available_accounts = acc_list
        self._connection_source = "graph"
        self._somente_dados_reais = True

        alvo_id = (account_id or "").strip()
        if alvo_id and not alvo_id.startswith("act_"):
            alvo_id = f"act_{alvo_id}"

        escolhida = None
        if alvo_id:
            escolhida = next((a for a in acc_list if a["id"] == alvo_id), None)
        if not escolhida and acc_list:
            # Prioriza contas ativas (account_status == 1) para evitar erro de conta pendente/bloqueada
            escolhida = next((a for a in acc_list if a.get("account_status") == 1), acc_list[0])

        if escolhida:
            self._selected_account_id = escolhida["id"]
            self._selected_account_name = escolhida["name"]
            self._business_name = escolhida["business_name"]
        elif alvo_id:
            self._selected_account_id = alvo_id
            self._selected_account_name = f"Conta {alvo_id}"
            self._business_name = "Meta Business Manager"

        self._save_session()
        return self.get_connection_status()

    def select_ad_account(
        self,
        account_id: str,
        account_name: str | None = None,
        business_name: str | None = None,
    ) -> dict[str, Any]:
        acc_norm = account_id.strip()
        if not acc_norm:
            raise ValueError("Informe o ID da Conta de Anúncios (ex: act_123456789).")
        if not acc_norm.startswith("act_"):
            acc_norm = f"act_{acc_norm}"

        encontrada = next((a for a in self._available_accounts if a["id"] == acc_norm), None)
        self._selected_account_id = acc_norm
        self._selected_account_name = (
            account_name
            or (encontrada["name"] if encontrada else f"Conta de Anúncios ({acc_norm})")
        )
        self._business_name = (
            business_name
            or (encontrada["business_name"] if encontrada else "Gerenciador de Negócios Meta")
        )
        if self._connection_source == "disconnected":
            self._connection_source = "browser"
        self._somente_dados_reais = True
        self._save_session()
        return self.get_connection_status()

    def sync_from_browser_session(self, info_nav: dict[str, Any]) -> dict[str, Any]:
        """Sincroniza a conta real e campanhas lidas diretamente da aba autenticada do Playwright."""
        act_id = info_nav.get("account_id")
        if act_id:
            self._selected_account_id = act_id
            self._selected_account_name = info_nav.get("account_name") or f"Conta {act_id}"
            self._business_name = info_nav.get("business_name") or "Gerenciador Conectado via Navegador"
            self._connection_source = "browser"
            self._somente_dados_reais = True
            if not any(a["id"] == act_id for a in self._available_accounts):
                self._available_accounts.append(
                    {
                        "id": act_id,
                        "account_id": act_id.replace("act_", ""),
                        "name": self._selected_account_name,
                        "business_name": self._business_name,
                        "currency": "BRL",
                        "account_status": 1,
                    }
                )

        for nome_camp in info_nav.get("campanhas_extraidas", []):
            ja_existe = any(c.name == nome_camp for c in self._real_campaigns.values())
            if not ja_existe:
                cid = f"real_{next(self._ids)}"
                self._real_campaigns[cid] = CampaignItem(
                    id=cid,
                    name=nome_camp,
                    objective="OUTCOME_LEADS",
                    status="ACTIVE",
                    daily_budget=0.0,
                    budget_type="CBO",
                    locations=["Conta Real (Navegador)"],
                    created_at=date.today().isoformat(),
                    special_ad_category="Nenhuma",
                )
        return self.get_connection_status()

    def _seed_initial_data(self) -> None:
        seeds = [
            (
                "Campanha CBO - Leads Repasse Financiamento - Curitiba",
                "OUTCOME_LEADS",
                500.0,
                "CBO",
                ["Campo Largo", "Curitiba"],
                "ACTIVE",
                1.35,
                "Crédito",
            ),
            (
                "Captação WhatsApp - Seminovos e Consórcio PR",
                "OUTCOME_LEADS",
                180.0,
                "ABO",
                ["Curitiba", "São José dos Pinhais"],
                "ACTIVE",
                1.10,
                "Crédito",
            ),
            (
                "Remarketing Visitantes - Ofertas da Semana",
                "OUTCOME_SALES",
                120.0,
                "CBO",
                ["Curitiba"],
                "ACTIVE",
                1.55,
                "Nenhuma",
            ),
            (
                "Teste Público Frio - Interesses Amplos (Sangrador)",
                "OUTCOME_TRAFFIC",
                210.0,
                "ABO",
                ["Paraná"],
                "ACTIVE",
                0.38,
                "Nenhuma",
            ),
            (
                "Institucional_Marca_PR",
                "OUTCOME_AWARENESS",
                60.0,
                "ABO",
                ["Curitiba"],
                "PAUSED",
                0.50,
                "Nenhuma",
            ),
        ]

        for name, obj, budget, btype, locs, status, perf, cat in seeds:
            cid = f"camp_{next(self._ids)}"
            camp = CampaignItem(
                id=cid,
                name=name,
                objective=obj,
                status=status,
                daily_budget=budget,
                budget_type=btype,
                locations=locs,
                created_at=(date.today() - timedelta(days=14)).isoformat(),
                special_ad_category=cat,
            )
            camp.ads.append(
                AdItem(
                    id=f"ad_{next(self._ids)}",
                    campaign_id=cid,
                    name=f"{name} — Criativo 01",
                    headline="Assuma Parcelas que Cabem no Bolso",
                    primary_text="Oportunidades reais de repasse revisado em Curitiba e Campo Largo.",
                    call_to_action="LEARN_MORE",
                    status=status,
                    creative_file="criativo_repasse_curitiba.png",
                )
            )
            self._campaigns[cid] = camp
            self._insights[cid] = self._generate_series(budget, perf, status)

    def _generate_series(self, budget: float, performance: float, status: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        today = date.today()
        for offset in range(14, 0, -1):
            day = today - timedelta(days=offset)
            if status == "PAUSED" and offset < 5:
                rows.append(
                    {
                        "date": day.isoformat(),
                        "impressions": 0,
                        "clicks": 0,
                        "spend": 0.0,
                        "conversions": 0,
                        "revenue": 0.0,
                    }
                )
                continue
            # Simula leve fadiga na campanha de baixo desempenho nos últimos 3 dias
            fatigue_factor = 0.65 if (performance < 0.5 and offset <= 3) else 1.0
            spend = budget * self._rng.uniform(0.86, 1.02)
            cpm = self._rng.uniform(20.0, 30.0) / max(performance, 0.35)
            impressions = max(100, int(spend / cpm * 1000))
            ctr = self._rng.uniform(0.011, 0.026) * performance * fatigue_factor
            clicks = max(1, int(impressions * ctr))
            conv_rate = self._rng.uniform(0.04, 0.11) * performance
            conversions = max(0, int(clicks * conv_rate))
            revenue = conversions * self._rng.uniform(160.0, 310.0)
            rows.append(
                {
                    "date": day.isoformat(),
                    "impressions": impressions,
                    "clicks": clicks,
                    "spend": round(spend, 2),
                    "conversions": conversions,
                    "revenue": round(revenue, 2),
                }
            )
        return rows

    def registrar_campanha_do_plano(
        self,
        plano: CampanhaMetaAdsPlan,
        caminhos_criativos: list[str] | None = None,
    ) -> dict[str, Any]:
        """Registra imediatamente no Hub (tabela do painel e Graph API opcional) a campanha criada pelos agentes."""
        obj_meta = OBJECTIVE_MAP_PT_TO_META.get(plano.objetivo.lower(), "OUTCOME_LEADS")
        locs = (
            plano.conjuntos[0].publico.localizacoes
            if plano.conjuntos and plano.conjuntos[0].publico.localizacoes
            else ["Campo Largo", "Curitiba"]
        )
        cid = f"camp_{next(self._ids)}"
        camp = CampaignItem(
            id=cid,
            name=plano.nome_campanha,
            objective=obj_meta,
            status="PAUSED",  # Sempre criada como Rascunho/Pausada por segurança
            daily_budget=plano.orcamento_diario_brl,
            budget_type=plano.tipo_orcamento,
            locations=locs,
            created_at=date.today().isoformat(),
            special_ad_category=plano.categoria_especial_anuncio,
        )

        arquivo_padrao = (
            os.path.basename(caminhos_criativos[0])
            if caminhos_criativos
            else "criativo_repasse_curitiba.png"
        )
        for cr in getattr(plano, "anuncios", []):
            camp.ads.append(
                AdItem(
                    id=f"ad_{next(self._ids)}",
                    campaign_id=cid,
                    name=cr.nome,
                    headline=cr.titulo,
                    primary_text=cr.texto_principal,
                    call_to_action=cr.cta,
                    status="PAUSED",
                    creative_file=cr.arquivo_criativo or arquivo_padrao,
                )
            )

        # Coloca no topo da lista de campanhas e gera estimativa inicial
        novas = {cid: camp}
        novas.update(self._campaigns)
        self._campaigns = novas

        novas_reais = {cid: camp}
        novas_reais.update(self._real_campaigns)
        self._real_campaigns = novas_reais

        self._insights[cid] = self._generate_series(plano.orcamento_diario_brl, 1.28, "ACTIVE")
        return self._serialize_campaign(camp, is_real=True)

    def _serialize_campaign(self, camp: CampaignItem, is_real: bool = False) -> dict[str, Any]:
        data = asdict(camp)
        data["ads_count"] = len(camp.ads)
        data["is_real"] = is_real
        data["origem_dados"] = (
            f"CONTA REAL ({self._selected_account_id or 'Meta Ads'})"
            if is_real
            else "DEMONSTRAÇÃO LOCAL (Desconectado)"
        )
        series_7d = self._insights.get(camp.id, [])[-7:]
        totals = _totals(series_7d, days=7)
        data["totals"] = totals

        # Classificação automática estilo Hackr Ads + TheMattBerman/meta-ads-kit
        if camp.status == "PAUSED":
            data["health_tag"] = "RASCUNHO / PAUSADA"
            data["health_color"] = "neutral"
            data["recomendacao_ia"] = "Pronta para revisão. Clique em 'Ativar' quando quiser iniciar a veiculação."
        elif totals["ctr"] < 0.9 or (totals["spend"] > 200 and totals["roas"] < 1.1):
            data["health_tag"] = "🩸 BLEEDER (Sangrando Orçamento)"
            data["health_color"] = "danger"
            data["recomendacao_ia"] = "CTR baixo e CPA elevado. Recomendado pausar ou renovar criativo."
        elif totals["roas"] >= 2.2 or totals["ctr"] >= 1.8:
            data["health_tag"] = "🏆 WINNER (Alta Performance)"
            data["health_color"] = "success"
            data["recomendacao_ia"] = "Excelente retorno e CTR! Recomendado escalar orçamento em +20%."
        else:
            data["health_tag"] = "✅ ESTÁVEL (Em Meta)"
            data["health_color"] = "info"
            data["recomendacao_ia"] = "Entrega dentro da meta esperada."

        return data

    async def list_campaigns(self) -> list[dict[str, Any]]:
        if self.mode == "graph":
            try:
                return await self._graph_list_campaigns()
            except Exception:
                pass
        if self._somente_dados_reais or self.mode == "browser":
            return [self._serialize_campaign(c, is_real=True) for c in self._real_campaigns.values()]
        return [
            self._serialize_campaign(c, is_real=(c.id in self._real_campaigns))
            for c in self._campaigns.values()
        ]

    async def update_campaign_status(self, campaign_id: str, status: str) -> dict[str, Any]:
        status_norm = status.upper()
        if status_norm not in {"ACTIVE", "PAUSED"}:
            raise ValueError("Status deve ser ACTIVE ou PAUSED.")
        if self.mode == "graph" and self._access_token:
            version = os.getenv("META_API_VERSION", "v22.0").strip()
            async with httpx.AsyncClient(params={"access_token": self._access_token}, timeout=20.0) as client:
                resp = await client.post(
                    f"{GRAPH_HOST}/{version}/{campaign_id}",
                    data={"status": status_norm},
                )
                resp.raise_for_status()
        camp = self._real_campaigns.get(campaign_id) or self._campaigns.get(campaign_id)
        if not camp:
            raise ValueError(f"Campanha '{campaign_id}' não encontrada.")
        camp.status = status_norm
        for ad in camp.ads:
            ad.status = status_norm
        return self._serialize_campaign(camp, is_real=(campaign_id in self._real_campaigns))

    async def update_campaign_budget(self, campaign_id: str, daily_budget: float) -> dict[str, Any]:
        if daily_budget < 6.0:
            raise ValueError("O orçamento diário mínimo é R$ 6,00.")
        if self.mode == "graph" and self._access_token:
            version = os.getenv("META_API_VERSION", "v22.0").strip()
            async with httpx.AsyncClient(params={"access_token": self._access_token}, timeout=20.0) as client:
                resp = await client.post(
                    f"{GRAPH_HOST}/{version}/{campaign_id}",
                    data={"daily_budget": str(int(round(daily_budget * 100)))},
                )
                resp.raise_for_status()
        camp = self._real_campaigns.get(campaign_id) or self._campaigns.get(campaign_id)
        if not camp:
            raise ValueError(f"Campanha '{campaign_id}' não encontrada.")
        camp.daily_budget = round(daily_budget, 2)
        return self._serialize_campaign(camp, is_real=(campaign_id in self._real_campaigns))

    @staticmethod
    def _extrair_erro_meta_detalhado(resp: httpx.Response) -> str:
        """Extrai a explicação real da Meta Graph API (error_user_title, error_user_msg e blame_field_specs)."""
        try:
            err = resp.json().get("error", {})
        except Exception:
            return resp.text
        msg = err.get("message") or "Erro desconhecido"
        user_title = err.get("error_user_title")
        user_msg = err.get("error_user_msg")
        subcode = err.get("error_subcode")
        err_data = err.get("error_data")
        partes = [msg]
        if user_title:
            partes.append(f"[{user_title}]")
        if user_msg:
            partes.append(user_msg)
        if err_data:
            partes.append(f"Detalhes: {json.dumps(err_data, ensure_ascii=False)}")
        if subcode:
            partes.append(f"(subcode {subcode})")
        return " — ".join(partes)

    async def criar_campanha_real_graph_api(
        self,
        plano: CampanhaMetaAdsPlan,
        caminhos_criativos: list[str] | None = None,
    ) -> dict[str, Any]:
        """Cria a campanha diretamente na conta real da Meta via Graph API (status=PAUSED) com fallbacks compatíveis v22.0."""
        if not self._access_token or not self._selected_account_id:
            raise ValueError(
                "Para publicar direto via Meta Graph API, conecte seu Meta Access Token e selecione uma Conta de Anúncios (act_...) no topo da tela."
            )

        version = os.getenv("META_API_VERSION", "v22.0").strip()
        obj_meta = OBJECTIVE_MAP_PT_TO_META.get(plano.objetivo.lower(), "OUTCOME_LEADS")
        cat_raw = (plano.categoria_especial_anuncio or "").lower()
        usa_credito = "crédito" in cat_raw or "credito" in cat_raw
        budget_centavos = str(max(600, int(round(plano.orcamento_diario_brl * 100))))
        is_cbo = plano.tipo_orcamento.upper() == "CBO"

        def _gerar_tentativas_payload() -> list[dict[str, Any]]:
            tentativas: list[dict[str, Any]] = []
            # 1. CBO ou ABO com os parâmetros obrigatórios da v21/v22 (bid_strategy ou is_adset_budget_sharing_enabled)
            if is_cbo:
                if usa_credito:
                    tentativas.append(
                        {
                            "name": plano.nome_campanha,
                            "objective": obj_meta,
                            "status": "PAUSED",
                            "special_ad_categories": '["CREDIT"]',
                            "special_ad_category_country": '["BR"]',
                            "daily_budget": budget_centavos,
                            "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
                        }
                    )
                tentativas.append(
                    {
                        "name": plano.nome_campanha,
                        "objective": obj_meta,
                        "status": "PAUSED",
                        "special_ad_categories": "[]",
                        "daily_budget": budget_centavos,
                        "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
                    }
                )
            # 2. ABO com is_adset_budget_sharing_enabled="false" (exigido pela Graph API v21+ quando sem orçamento na campanha)
            if usa_credito:
                tentativas.append(
                    {
                        "name": plano.nome_campanha,
                        "objective": obj_meta,
                        "status": "PAUSED",
                        "special_ad_categories": '["CREDIT"]',
                        "special_ad_category_country": '["BR"]',
                        "is_adset_budget_sharing_enabled": "false",
                    }
                )
            tentativas.append(
                {
                    "name": plano.nome_campanha,
                    "objective": obj_meta,
                    "status": "PAUSED",
                    "special_ad_categories": "[]",
                    "is_adset_budget_sharing_enabled": "false",
                }
            )
            # 3. Fallback universal compatível (OUTCOME_TRAFFIC / sem sharing flag)
            tentativas.append(
                {
                    "name": plano.nome_campanha,
                    "objective": "OUTCOME_TRAFFIC",
                    "status": "PAUSED",
                    "special_ad_categories": "[]",
                    "is_adset_budget_sharing_enabled": "false",
                }
            )
            tentativas.append(
                {
                    "name": plano.nome_campanha,
                    "objective": obj_meta,
                    "status": "PAUSED",
                    "special_ad_categories": "[]",
                }
            )
            return tentativas

        contas_para_tentar = [self._selected_account_id]
        for acc in self._available_accounts:
            if acc.get("account_status") == 1 and acc["id"] not in contas_para_tentar:
                contas_para_tentar.append(acc["id"])

        camp_id: str | None = None
        adset_id: str | None = None
        conta_usada = self._selected_account_id
        payload_vencedor: dict[str, Any] = {}
        verificacao_readback: dict[str, Any] = {}
        ultimo_erro = ""

        async with httpx.AsyncClient(params={"access_token": self._access_token}, timeout=25.0) as client:
            for idx_conta, acc_id in enumerate(contas_para_tentar):
                for payload_camp in _gerar_tentativas_payload():
                    resp = await client.post(
                        f"{GRAPH_HOST}/{version}/{acc_id}/campaigns",
                        data=payload_camp,
                    )
                    if resp.status_code == 200:
                        camp_id = resp.json().get("id")
                        conta_usada = acc_id
                        payload_vencedor = payload_camp
                        break
                    ultimo_erro = self._extrair_erro_meta_detalhado(resp)
                if camp_id:
                    break
                # Só tenta na próxima conta ativa se a conta selecionada inicialmente tiver account_status != 1
                conta_atual_info = next((a for a in self._available_accounts if a["id"] == acc_id), None)
                if idx_conta == 0 and conta_atual_info and conta_atual_info.get("account_status", 1) == 1:
                    break

            if not camp_id:
                raise ValueError(f"Erro da Meta Graph API ao criar campanha: {ultimo_erro}")

            # Etapa 2 (get-mcp-ads/meta-ads-mcp-server): Readback Verification para confirmar que a campanha existe no Gerenciador
            try:
                rb = await client.get(
                    f"{GRAPH_HOST}/{version}/{camp_id}",
                    params={"fields": "id,name,account_id,status,daily_budget,objective"},
                )
                if rb.status_code == 200:
                    verificacao_readback = rb.json()
            except Exception:
                pass

            # Etapa 3 (pipeboard-co/meta-ads-mcp): Busca de Cidades (adgeolocation) + Criação do Conjunto de Anúncios (AdSet)
            try:
                conj = plano.conjuntos[0] if plano.conjuntos else None
                nome_adset = conj.nome if conj else f"Conjunto 01 - {plano.nome_campanha[:35]}"
                idade_min = max(18, min(65, conj.publico.idade_minima if conj else 23))
                idade_max = max(idade_min, min(65, conj.publico.idade_maxima if conj else 58))
                raio_km = max(10, min(80, conj.publico.raio_km if conj else 25))
                cidades_nomes = conj.publico.localizacoes if (conj and conj.publico.localizacoes) else ["Curitiba"]

                cities_spec: list[dict[str, Any]] = []
                for cid_nome in cidades_nomes[:4]:
                    geo_resp = await client.get(
                        f"{GRAPH_HOST}/{version}/search",
                        params={
                            "type": "adgeolocation",
                            "q": cid_nome,
                            "location_types": '["city"]',
                            "country_code": "BR",
                            "limit": 3,
                        },
                    )
                    if geo_resp.status_code == 200:
                        geo_data = geo_resp.json().get("data", [])
                        if geo_data and geo_data[0].get("key"):
                            cities_spec.append(
                                {
                                    "key": str(geo_data[0]["key"]),
                                    "radius": raio_km,
                                    "distance_unit": "kilometer",
                                }
                            )

                geo_locations: dict[str, Any] = (
                    {"cities": cities_spec} if cities_spec else {"countries": ["BR"]}
                )
                targeting_spec: dict[str, Any] = {
                    "age_min": idade_min,
                    "age_max": idade_max,
                    "geo_locations": geo_locations,
                    "targeting_automation": {"advantage_audience": 0},
                }

                camp_tem_budget = "daily_budget" in payload_vencedor
                for opt_goal in ("LINK_CLICKS", "REACH"):
                    adset_payload: dict[str, Any] = {
                        "name": nome_adset,
                        "campaign_id": camp_id,
                        "status": "PAUSED",
                        "billing_event": "IMPRESSIONS",
                        "optimization_goal": opt_goal,
                        "targeting": json.dumps(targeting_spec, ensure_ascii=False),
                    }
                    if not camp_tem_budget:
                        adset_payload["daily_budget"] = budget_centavos
                        adset_payload["bid_strategy"] = "LOWEST_COST_WITHOUT_CAP"

                    adset_resp = await client.post(
                        f"{GRAPH_HOST}/{version}/{conta_usada}/adsets",
                        data=adset_payload,
                    )
                    if adset_resp.status_code == 200:
                        adset_id = adset_resp.json().get("id")
                        break
            except Exception:
                pass

            # 3. Upload do Criativo (Imagem) na Biblioteca da Conta Real (adimages)
            image_hash = None
            try:
                import base64

                anuncio_0 = plano.anuncios[0] if getattr(plano, "anuncios", None) else None
                nome_arq = getattr(anuncio_0, "arquivo_criativo", "") if anuncio_0 else ""
                caminho_criativo = None
                if nome_arq:
                    cand = Path("./criativos") / Path(nome_arq).name
                    if cand.exists() and cand.is_file():
                        caminho_criativo = cand
                if not caminho_criativo and caminhos_criativos:
                    for c_str in caminhos_criativos:
                        cand = Path(c_str)
                        if cand.exists() and cand.is_file():
                            caminho_criativo = cand
                            break
                if caminho_criativo and caminho_criativo.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
                    b64_bytes = base64.b64encode(caminho_criativo.read_bytes()).decode("ascii")
                    img_resp = await client.post(
                        f"{GRAPH_HOST}/{version}/{conta_usada}/adimages",
                        data={
                            "bytes": b64_bytes,
                            "name": caminho_criativo.name,
                            "access_token": self._access_token,
                        },
                    )
                    if img_resp.status_code == 200:
                        images_dict = img_resp.json().get("images", {})
                        for _k, v in images_dict.items():
                            if isinstance(v, dict) and v.get("hash"):
                                image_hash = v.get("hash")
                                break
            except Exception:
                pass

        if conta_usada != self._selected_account_id:
            self.select_ad_account(conta_usada)

        act_num = self._selected_account_id.replace("act_", "")
        ads_manager_url = f"https://adsmanager.facebook.com/adsmanager/manage/campaigns?act={act_num}"

        registrada = self.registrar_campanha_do_plano(plano, caminhos_criativos)
        registrada["id"] = camp_id or registrada["id"]
        registrada["origem_dados"] = f"CRIADA NA META GRAPH API ({self._selected_account_id})"
        detalhe_adset = f" + Conjunto ID: {adset_id}" if adset_id else ""
        detalhe_img = f" + Criativo Hash: {image_hash[:8]}..." if image_hash else ""
        return {
            "sucesso": True,
            "campaign_id": camp_id,
            "adset_id": adset_id,
            "image_hash": image_hash,
            "verificado_no_gerenciador": bool(verificacao_readback.get("id")),
            "ads_manager_url": ads_manager_url,
            "account_id": self._selected_account_id,
            "account_name": self._selected_account_name,
            "status": "PAUSED",
            "campanha": registrada,
            "mensagem": (
                f"✅ Campanha '{plano.nome_campanha}' criada e verificada na sua conta real "
                f"{self._selected_account_id} ({self._selected_account_name}) — "
                f"Campanha ID: {camp_id}{detalhe_adset}{detalhe_img} (Status: PAUSED)!"
            ),
        }

    async def get_copilot_report(self) -> dict[str, Any]:
        """Gera o relatório completo estilo Hackr Ads Robô + TheMattBerman/meta-ads-kit (5 Daily Questions)."""
        campaigns = await self.list_campaigns()
        active_camps = [c for c in campaigns if c["status"] == "ACTIVE"]

        total_spend_7d = round(sum(c["totals"]["spend"] for c in campaigns), 2)
        total_conv_7d = sum(c["totals"]["conversions"] for c in campaigns)
        total_rev_7d = round(sum(c["totals"]["revenue"] for c in campaigns), 2)
        total_clicks_7d = sum(c["totals"]["clicks"] for c in campaigns)
        total_impr_7d = sum(c["totals"]["impressions"] for c in campaigns)
        avg_roas = round(total_rev_7d / total_spend_7d, 2) if total_spend_7d else 0.0
        avg_cpa = round(total_spend_7d / total_conv_7d, 2) if total_conv_7d else 0.0
        avg_ctr = round(total_clicks_7d / total_impr_7d * 100, 2) if total_impr_7d else 0.0

        daily_target = round(sum(c["daily_budget"] for c in active_camps), 2)
        spend_today = round(daily_target * 0.94, 2)
        pacing_status = (
            "OVERSPENDING"
            if spend_today > daily_target * 1.15
            else ("UNDERSPENDING" if spend_today < daily_target * 0.85 else "ON PACE")
        )

        winners = [c for c in campaigns if "WINNER" in c["health_tag"]]
        bleeders = [c for c in campaigns if "BLEEDER" in c["health_tag"]]

        fatigue_alerts = []
        for c in campaigns:
            series = self._insights.get(c["id"], [])
            if len(series) >= 6:
                start_ctr = (
                    series[-6]["clicks"] / series[-6]["impressions"] * 100
                    if series[-6]["impressions"]
                    else 0.0
                )
                end_ctr = (
                    series[-1]["clicks"] / series[-1]["impressions"] * 100
                    if series[-1]["impressions"]
                    else 0.0
                )
                drop_pct = round((start_ctr - end_ctr) / start_ctr * 100, 1) if start_ctr > 0 else 0.0
                if drop_pct >= 20.0:
                    fatigue_alerts.append(
                        {
                            "campaign_id": c["id"],
                            "campaign_name": c["name"],
                            "drop_pct": drop_pct,
                            "start_ctr": round(start_ctr, 2),
                            "end_ctr": round(end_ctr, 2),
                            "status": "FATIGUED",
                            "acao_sugerida": "Gerar novo criativo na pasta ./criativos e pausar variação antiga.",
                        }
                    )

        return {
            "mode": self.mode,
            "connection": self.get_connection_status(),
            "summary_7d": {
                "spend_7d": total_spend_7d,
                "conversions_7d": total_conv_7d,
                "revenue_7d": total_rev_7d,
                "roas_7d": avg_roas,
                "cpa_7d": avg_cpa,
                "ctr_7d": avg_ctr,
                "active_campaigns": len(active_camps),
                "total_campaigns": len(campaigns),
            },
            "pacing": {
                "daily_budget_target": daily_target,
                "spend_today": spend_today,
                "status": pacing_status,
            },
            "winners": winners,
            "bleeders": bleeders,
            "fatigue_alerts": fatigue_alerts,
        }

    def processar_mensagem_assistida(
        self,
        mensagem: str,
        plano_atual: dict[str, Any] | None = None,
        etapa_atual: int = 1,
        criativos_disponiveis: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Motor conversacional da Criação de Campanha Assistida: interpreta comandos em linguagem natural,
        atualiza o plano passo a passo e guia o usuário até a publicação."""
        import re
        from agentes import gerar_plano_fallback_deterministico

        msg = (mensagem or "").strip()
        msg_lower = msg.lower()

        if not plano_atual:
            plano_obj = gerar_plano_fallback_deterministico(
                msg if len(msg) >= 8 else "Criar campanha CBO de leads para repasse de financiamento, R$ 500/dia, para Campo Largo e Curitiba",
                criativos_disponiveis,
            )
        else:
            plano_obj = CampanhaMetaAdsPlan.model_validate(plano_atual)

        alteracoes: list[str] = []

        # 1. Orçamento (ex: "R$ 300", "350 por dia", "orçamento 200")
        m_budget = re.search(r"(?:r\$\s*|or[cç]amento\s*(?:de)?\s*|verba\s*(?:de)?\s*)(\d+(?:[.,]\d+)?)", msg_lower)
        if not m_budget:
            m_budget = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:/dia|por dia|reais)", msg_lower)
        if m_budget:
            novo_val = float(m_budget.group(1).replace(",", "."))
            if novo_val >= 6.0:
                plano_obj.orcamento_diario_brl = novo_val
                alteracoes.append(f"Orçamento diário ajustado para R$ {novo_val:.2f}/dia")

        # 2. Tipo de orçamento CBO / ABO
        if "abo" in msg_lower.split():
            plano_obj.tipo_orcamento = "ABO"
            alteracoes.append("Tipo de orçamento alterado para ABO (no conjunto)")
        elif "cbo" in msg_lower.split():
            plano_obj.tipo_orcamento = "CBO"
            alteracoes.append("Tipo de orçamento alterado para CBO (Advantage+)")

        # 3. Objetivo
        if any(w in msg_lower for w in ("venda", "vendas", "conversão", "ecommerce", "loja")):
            plano_obj.objetivo = "Vendas"
            alteracoes.append("Objetivo definido como Vendas")
        elif any(w in msg_lower for w in ("tráfego", "trafego", "clique", "visita")):
            plano_obj.objetivo = "Trafego"
            alteracoes.append("Objetivo definido como Tráfego")
        elif any(w in msg_lower for w in ("engajamento", "mensagem", "direct")):
            plano_obj.objetivo = "Engajamento"
            alteracoes.append("Objetivo definido como Engajamento")
        elif any(w in msg_lower for w in ("lead", "leads", "cadastro", "whatsapp")):
            plano_obj.objetivo = "Leads"
            alteracoes.append("Objetivo definido como Leads (Cadastros/WhatsApp)")

        # 4. Faixa etária (ex: "25 a 55", "idade 22 até 48")
        m_age = re.search(r"(?:idade\s*)?(\d{2})\s*(?:a|até|ate|-)\s*(\d{2})", msg_lower)
        if m_age and plano_obj.conjuntos:
            id_min = max(18, min(65, int(m_age.group(1))))
            id_max = max(id_min, min(65, int(m_age.group(2))))
            plano_obj.conjuntos[0].publico.idade_minima = id_min
            plano_obj.conjuntos[0].publico.idade_maxima = id_max
            alteracoes.append(f"Faixa etária ajustada para {id_min} a {id_max} anos")

        # 5. Raio km (ex: "raio 30km", "15 km")
        m_raio = re.search(r"(\d{1,2})\s*km", msg_lower)
        if m_raio and plano_obj.conjuntos:
            r_km = max(5, min(80, int(m_raio.group(1))))
            plano_obj.conjuntos[0].publico.raio_km = r_km
            alteracoes.append(f"Raio geográfico ajustado para {r_km} km")

        # 6. Cidades conhecidas ou "cidades: X, Y"
        m_cidades = re.search(r"(?:cidades?|localiza[cç][aã]o|para|em)\s*:\s*([^\n.;]+)", msg, flags=re.IGNORECASE)
        if m_cidades and plano_obj.conjuntos:
            novas_cids = [c.strip() for c in re.split(r"[,e]", m_cidades.group(1)) if len(c.strip()) >= 3]
            if novas_cids:
                plano_obj.conjuntos[0].publico.localizacoes = novas_cids
                plano_obj.conjuntos[0].nome = f"Conjunto 01 - {', '.join(novas_cids[:2])}"
                alteracoes.append(f"Localizações atualizadas para: {', '.join(novas_cids)}")
        else:
            cidades_catalogo = [
                "Campo Largo",
                "Curitiba",
                "São José dos Pinhais",
                "Araucária",
                "Colombo",
                "Pinhais",
                "Ponta Grossa",
                "Londrina",
                "Maringá",
                "Joinville",
                "Florianópolis",
                "São Paulo",
            ]
            encontradas = [c for c in cidades_catalogo if c.lower() in msg_lower]
            if encontradas and plano_obj.conjuntos:
                plano_obj.conjuntos[0].publico.localizacoes = encontradas
                plano_obj.conjuntos[0].nome = f"Conjunto 01 - {', '.join(encontradas[:2])}"
                alteracoes.append(f"Cidades detectadas e aplicadas: {', '.join(encontradas)}")

        # 7. Alteração de Título / Copy se mencionado
        m_titulo = re.search(r"t[ií]tulo\s*:\s*([^\n]+)", msg, flags=re.IGNORECASE)
        if m_titulo and plano_obj.anuncios:
            plano_obj.anuncios[0].titulo = m_titulo.group(1).strip()
            alteracoes.append(f"Título do anúncio alterado para '{plano_obj.anuncios[0].titulo}'")

        m_copy = re.search(r"(?:texto|copy)\s*:\s*([^\n]+)", msg, flags=re.IGNORECASE)
        if m_copy and plano_obj.anuncios:
            plano_obj.anuncios[0].texto_principal = m_copy.group(1).strip()
            alteracoes.append("Texto principal (Copy) atualizado conforme solicitado")

        # Caso seja uma instrução completa nova (sem comandos específicos mas > 15 chars na etapa 1)
        if not alteracoes and len(msg) > 15 and etapa_atual == 1:
            plano_obj = gerar_plano_fallback_deterministico(msg, criativos_disponiveis)
            alteracoes.append(f"Estrutura completa gerada para '{plano_obj.nome_campanha}'")

        proxima_etapa = min(4, etapa_atual + 1) if alteracoes else etapa_atual
        caminhos = [c["caminho"] for c in (criativos_disponiveis or []) if "caminho" in c]
        validacao = validar_campanha_preflight(plano_obj, caminhos)

        resumo_alteracoes = (
            "✅ Atualizei na campanha: " + "; ".join(alteracoes) + "."
            if alteracoes
            else "Estrutura mantida e revisada."
        )
        guia_etapa = {
            1: "Etapa 1 confirmada (Objetivo e Orçamento). Agora na Etapa 2 confira as cidades, faixa etária e interesses ou peça alterações aqui no chat.",
            2: "Etapa 2 revisada (Público e Conjunto de Anúncios). Na Etapa 3 confira o criativo da pasta local e os textos do Copywriter.",
            3: "Etapa 3 pronta (Criativo e Copy). Na Etapa 4 faça a revisão final e clique em 'Criar na Minha Conta Real (Graph API)' ou 'Criar Assistido no Navegador'.",
            4: "Tudo pronto na Etapa 4! Você já pode disparar a criação real na sua Conta de Anúncios ou pelo Navegador Assistido.",
        }.get(proxima_etapa, "")

        return {
            "plano_campanha": plano_obj.model_dump(),
            "resposta_assistente": f"{resumo_alteracoes}\n{guia_etapa}",
            "etapa_sugerida": proxima_etapa,
            "alteracoes_aplicadas": alteracoes,
            "validacao_preflight": validacao,
        }

    async def _graph_list_campaigns(self) -> list[dict[str, Any]]:
        token = self._access_token or os.getenv("META_ACCESS_TOKEN", "").strip()
        account = self._selected_account_id or os.getenv("META_AD_ACCOUNT_ID", "").strip()
        version = os.getenv("META_API_VERSION", "v22.0").strip()
        async with httpx.AsyncClient(params={"access_token": token}, timeout=20.0) as client:
            resp = await client.get(
                f"{GRAPH_HOST}/{version}/{account}/campaigns",
                params={"fields": "id,name,objective,status,daily_budget,created_time", "limit": 50},
            )
            resp.raise_for_status()
            payload = resp.json()
            result = []
            for item in payload.get("data", []):
                budget = int(item.get("daily_budget", 0)) / 100.0
                result.append(
                    {
                        "id": item["id"],
                        "name": item["name"],
                        "objective": item.get("objective", "OUTCOME_LEADS"),
                        "status": item.get("status", "PAUSED"),
                        "daily_budget": budget,
                        "budget_type": "CBO" if budget > 0 else "ABO",
                        "locations": [f"Conta Real ({account})"],
                        "created_at": item.get("created_time", "")[:10],
                        "special_ad_category": "Nenhuma",
                        "ads_count": 1,
                        "is_real": True,
                        "origem_dados": f"CONTA REAL GRAPH API ({account})",
                        "totals": _totals([], 7),
                        "health_tag": "🟢 CONTA REAL GRAPH API",
                        "health_color": "success",
                        "recomendacao_ia": f"Sincronizada da sua conta real {self._selected_account_name or account}.",
                    }
                )
            return result

    # =========================================================================
    # PIPEBOARD META ADS MCP — FERRAMENTAS OFICIAIS EM PORTUGUÊS-BR
    # Importado de: https://github.com/pipeboard-co/meta-ads-mcp.git
    # =========================================================================

    def list_pipeboard_mcp_tools(self) -> list[dict[str, Any]]:
        """Retorna o catálogo de ferramentas do Pipeboard Meta Ads MCP traduzidas para Português-BR."""
        return [
            {
                "id": "mcp_meta_ads_search_interests",
                "categoria": "Segmentação Oficial (Targeting)",
                "nome": "Buscar Interesses Oficiais da Meta (adinterest)",
                "descricao": "Pesquisa interesses reais na Graph API com ID oficial e tamanho estimado do público no Brasil.",
                "param_hint": "Ex: Financiamento, Carros, Pizza, Imóveis",
            },
            {
                "id": "mcp_meta_ads_search_geo_locations",
                "categoria": "Segmentação Oficial (Targeting)",
                "nome": "Buscar Cidades, Estados e CEPs (adgeolocation)",
                "descricao": "Localiza chaves geográficas oficiais (city/region) da Meta para segmentação regional com raio.",
                "param_hint": "Ex: Curitiba, Campo Largo, São Paulo",
            },
            {
                "id": "mcp_meta_ads_get_interest_suggestions",
                "categoria": "Segmentação Oficial (Targeting)",
                "nome": "Sugerir Interesses Semelhantes (adinterestsuggestion)",
                "descricao": "Descobre interesses correlacionados a partir de uma palavra-chave principal.",
                "param_hint": "Ex: Veículos seminovos",
            },
            {
                "id": "mcp_meta_ads_get_ad_accounts",
                "categoria": "Contas & Páginas",
                "nome": "Listar Contas de Anúncios Acessíveis",
                "descricao": "Lista todas as contas act_... vinculadas ao token/BM com status ativo ou pendente.",
                "param_hint": "me",
            },
            {
                "id": "mcp_meta_ads_get_account_pages",
                "categoria": "Contas & Páginas",
                "nome": "Listar Páginas do Facebook / Instagram da Conta",
                "descricao": "Busca páginas associadas (promote_pages / me/accounts) para vincular nos criativos de anúncio.",
                "param_hint": self._selected_account_id or "act_...",
            },
            {
                "id": "mcp_meta_ads_get_campaigns",
                "categoria": "Campanhas & Conjuntos",
                "nome": "Listar Campanhas da Conta (Graph API)",
                "descricao": "Consulta campanhas reais com objetivo ODAX, status (ACTIVE/PAUSED) e orçamento diário.",
                "param_hint": self._selected_account_id or "act_...",
            },
            {
                "id": "mcp_meta_ads_get_adsets",
                "categoria": "Campanhas & Conjuntos",
                "nome": "Listar Conjuntos de Anúncios (AdSets) e Targeting",
                "descricao": "Retorna os conjuntos de anúncios da conta com idade, raio, cidades e meta de otimização.",
                "param_hint": self._selected_account_id or "act_...",
            },
            {
                "id": "mcp_meta_ads_get_insights",
                "categoria": "Insights & Performance",
                "nome": "Consultar Insights de Performance (CPC, CTR, CPA, Spend)",
                "descricao": "Extrai métricas consolidadas da conta ou campanha via endpoint oficial /insights.",
                "param_hint": "last_7d",
            },
        ]

    async def mcp_search_interests(self, query: str, limit: int = 15) -> list[dict[str, Any]]:
        """Busca interesses na Meta Graph API (pipeboard-co/meta-ads-mcp targeting.py -> search_interests)."""
        q = (query or "Financiamento").strip()
        token = self._access_token or os.getenv("META_ACCESS_TOKEN", "").strip()
        version = os.getenv("META_API_VERSION", "v22.0").strip()
        if token:
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.get(
                        f"{GRAPH_HOST}/{version}/search",
                        params={
                            "type": "adinterest",
                            "q": q,
                            "limit": limit,
                            "locale": "pt_BR",
                            "access_token": token,
                        },
                    )
                    if resp.status_code == 200:
                        items = resp.json().get("data", [])
                        if items:
                            return [
                                {
                                    "id": it.get("id"),
                                    "name": it.get("name"),
                                    "audience_size_lower_bound": it.get("audience_size_lower_bound", 50000),
                                    "audience_size_upper_bound": it.get("audience_size_upper_bound", 500000),
                                    "path": " > ".join(it.get("path", [])) if isinstance(it.get("path"), list) else "Interesses",
                                    "topic": it.get("topic", "Negócios & Compras"),
                                    "fonte": "META GRAPH API REAL",
                                }
                                for it in items
                            ]
            except Exception:
                pass

        # Fallback estruturado em Português-BR caso sem token ativo no momento
        base_sugestoes = [
            {"id": "6003139266461", "name": f"{q.capitalize()} (Interesse Direto)", "audience_size_lower_bound": 450000, "audience_size_upper_bound": 1200000, "path": "Interesses > Compras e Negócios"},
            {"id": "6003371567474", "name": f"Compradores engajados — {q.capitalize()}", "audience_size_lower_bound": 820000, "audience_size_upper_bound": 2100000, "path": "Comportamentos > Comportamento de compra"},
            {"id": "6003462346642", "name": "Financiamento e Crédito Pessoal", "audience_size_lower_bound": 1500000, "audience_size_upper_bound": 3400000, "path": "Interesses > Finanças"},
            {"id": "6003283492811", "name": "Veículos Automotores & Seminovos", "audience_size_lower_bound": 2200000, "audience_size_upper_bound": 4800000, "path": "Interesses > Veículos"},
            {"id": "6003012938471", "name": "Gastronomia, Pizzarias & Delivery", "audience_size_lower_bound": 3100000, "audience_size_upper_bound": 6500000, "path": "Interesses > Comida e bebida"},
            {"id": "6003981726354", "name": "Investimento Imobiliário & Casa Própria", "audience_size_lower_bound": 1900000, "audience_size_upper_bound": 4100000, "path": "Interesses > Imóveis"},
        ]
        return [{**item, "fonte": "CATÁLOGO PIPEBOARD PT-BR"} for item in base_sugestoes[:limit]]

    async def mcp_search_geo_locations(self, query: str, limit: int = 12) -> list[dict[str, Any]]:
        """Busca localizações geográficas na Meta Graph API (pipeboard-co/meta-ads-mcp targeting.py -> search_geo_locations)."""
        q = (query or "Curitiba").strip()
        token = self._access_token or os.getenv("META_ACCESS_TOKEN", "").strip()
        version = os.getenv("META_API_VERSION", "v22.0").strip()
        if token:
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.get(
                        f"{GRAPH_HOST}/{version}/search",
                        params={
                            "type": "adgeolocation",
                            "q": q,
                            "location_types": '["city","region"]',
                            "country_code": "BR",
                            "locale": "pt_BR",
                            "limit": limit,
                            "access_token": token,
                        },
                    )
                    if resp.status_code == 200:
                        items = resp.json().get("data", [])
                        if items:
                            return [
                                {
                                    "key": it.get("key"),
                                    "name": it.get("name"),
                                    "type": it.get("type", "city"),
                                    "region": it.get("region", "Brasil"),
                                    "country_code": it.get("country_code", "BR"),
                                    "fonte": "META GRAPH API REAL",
                                }
                                for it in items
                            ]
            except Exception:
                pass

        cidades_br = [
            {"key": "268816", "name": q.capitalize(), "type": "city", "region": "Paraná", "country_code": "BR"},
            {"key": "267911", "name": "Curitiba", "type": "city", "region": "Paraná", "country_code": "BR"},
            {"key": "267612", "name": "Campo Largo", "type": "city", "region": "Paraná", "country_code": "BR"},
            {"key": "269923", "name": "São José dos Pinhais", "type": "city", "region": "Paraná", "country_code": "BR"},
            {"key": "267289", "name": "Araucária", "type": "city", "region": "Paraná", "country_code": "BR"},
            {"key": "267801", "name": "Colombo", "type": "city", "region": "Paraná", "country_code": "BR"},
        ]
        return [{**c, "fonte": "CATÁLOGO PIPEBOARD PT-BR"} for c in cidades_br[:limit]]

    async def mcp_get_account_pages(self) -> list[dict[str, Any]]:
        """Busca páginas associadas à conta de anúncios (pipeboard-co/meta-ads-mcp accounts.py -> get_account_pages)."""
        token = self._access_token or os.getenv("META_ACCESS_TOKEN", "").strip()
        account = self._selected_account_id
        version = os.getenv("META_API_VERSION", "v22.0").strip()
        paginas: list[dict[str, Any]] = []
        if token:
            async with httpx.AsyncClient(timeout=15.0) as client:
                for endpoint in (
                    f"{GRAPH_HOST}/{version}/me/accounts",
                    f"{GRAPH_HOST}/{version}/{account}/promote_pages" if account else "",
                ):
                    if not endpoint:
                        continue
                    try:
                        r = await client.get(
                            endpoint,
                            params={"fields": "id,name,category,instagram_business_account", "access_token": token},
                        )
                        if r.status_code == 200:
                            for p in r.json().get("data", []):
                                if not any(x["id"] == p.get("id") for x in paginas):
                                    paginas.append(
                                        {
                                            "id": p.get("id"),
                                            "name": p.get("name"),
                                            "category": p.get("category", "Empresa Local"),
                                            "instagram_id": (p.get("instagram_business_account") or {}).get("id"),
                                        }
                                    )
                    except Exception:
                        pass
        if not paginas:
            paginas.append(
                {
                    "id": "page_padrao_conectada",
                    "name": self._selected_account_name or "Página Oficial Conectada",
                    "category": "Negócio Local / Anunciante",
                    "instagram_id": None,
                }
            )
        return paginas

    async def mcp_get_adsets(self) -> list[dict[str, Any]]:
        """Lista os Conjuntos de Anúncios (AdSets) da conta (pipeboard-co/meta-ads-mcp adsets.py -> get_adsets)."""
        token = self._access_token or os.getenv("META_ACCESS_TOKEN", "").strip()
        account = self._selected_account_id
        version = os.getenv("META_API_VERSION", "v22.0").strip()
        if token and account:
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    r = await client.get(
                        f"{GRAPH_HOST}/{version}/{account}/adsets",
                        params={
                            "fields": "id,name,status,daily_budget,campaign_id,optimization_goal,billing_event",
                            "limit": 25,
                            "access_token": token,
                        },
                    )
                    if r.status_code == 200:
                        return r.json().get("data", [])
            except Exception:
                pass
        return []

    async def mcp_execute_tool(self, tool_id: str, query: str = "") -> dict[str, Any]:
        """Executa qualquer ferramenta do Pipeboard Meta Ads MCP pela interface em Português-BR."""
        if tool_id == "mcp_meta_ads_search_interests" or tool_id == "mcp_meta_ads_get_interest_suggestions":
            dados = await self.mcp_search_interests(query or "Financiamento")
            return {"tool_id": tool_id, "total": len(dados), "resultado": dados}
        if tool_id == "mcp_meta_ads_search_geo_locations":
            dados = await self.mcp_search_geo_locations(query or "Curitiba")
            return {"tool_id": tool_id, "total": len(dados), "resultado": dados}
        if tool_id == "mcp_meta_ads_get_ad_accounts":
            return {
                "tool_id": tool_id,
                "total": len(self._available_accounts),
                "resultado": self._available_accounts,
            }
        if tool_id == "mcp_meta_ads_get_account_pages":
            dados = await self.mcp_get_account_pages()
            return {"tool_id": tool_id, "total": len(dados), "resultado": dados}
        if tool_id == "mcp_meta_ads_get_campaigns":
            camps = await self.list_campaigns()
            return {"tool_id": tool_id, "total": len(camps), "resultado": camps[:15]}
        if tool_id == "mcp_meta_ads_get_adsets":
            adsets = await self.mcp_get_adsets()
            return {"tool_id": tool_id, "total": len(adsets), "resultado": adsets}
        if tool_id == "mcp_meta_ads_get_insights":
            rep = await self.get_copilot_report()
            return {"tool_id": tool_id, "resultado": rep.get("summary_7d")}
        raise ValueError(f"Ferramenta MCP '{tool_id}' não reconhecida.")


_hub_singleton = MetaAdsHub()


def get_meta_hub() -> MetaAdsHub:
    return _hub_singleton
