"""Orquestração multi-agentes com CrewAI para planejamento de campanhas Meta Ads."""

from __future__ import annotations

import json
import re
from typing import Any, Literal

from pydantic import BaseModel, Field

from llm_config import build_crewai_llm


class PublicoAlvo(BaseModel):
    """Definição de segmentação demográfica, geográfica e comportamental."""

    idade_minima: int = Field(default=21, ge=18, le=65)
    idade_maxima: int = Field(default=55, ge=18, le=65)
    genero: Literal["todos", "masculino", "feminino"] = "todos"
    localizacoes: list[str] = Field(..., min_length=1)
    raio_km: int | None = Field(default=25, ge=5, le=80)
    interesses_sugeridos: list[str] = Field(default_factory=list)


class ConjuntoAnuncios(BaseModel):
    """Estrutura de um Conjunto de Anúncios (Ad Set) no Gerenciador de Anúncios."""

    nome: str
    orcamento_diario_brl: float | None = Field(
        default=None,
        description="Preencher somente quando tipo_orcamento for ABO; manter nulo em CBO.",
    )
    otimizacao_veiculacao: str = "Leads"
    evento_conversao: str = "Formulario instantaneo ou WhatsApp"
    posicionamentos: list[str] = Field(
        default_factory=lambda: ["Advantage+ (Automático)"]
    )
    publico: PublicoAlvo


class CriativoAnuncio(BaseModel):
    """Variação de anúncio com textos de conversão e arquivo de mídia opcional."""

    nome: str
    formato: Literal["imagem_unica", "carrossel", "video_curto"] = "imagem_unica"
    arquivo_criativo: str | None = Field(
        default=None,
        description="Nome ou caminho do arquivo de mídia selecionado da pasta de criativos.",
    )
    texto_principal: str
    titulo: str
    descricao: str
    cta: Literal["Saiba mais", "Cadastre-se", "Enviar mensagem", "Solicitar agora"] = (
        "Saiba mais"
    )


class CampanhaMetaAdsPlan(BaseModel):
    """JSON estruturado final consumido pela automação browser-use e pelo frontend."""

    nome_campanha: str
    objetivo: Literal["Leads", "Trafego", "Vendas", "Engajamento"] = "Leads"
    tipo_orcamento: Literal["CBO", "ABO"] = "CBO"
    orcamento_diario_brl: float = Field(..., gt=0)
    estrategia_lance: str = "Volume mais alto"
    categoria_especial_anuncio: str = Field(
        default="Nenhuma (avaliar Crédito se aplicável ao anúncio)",
        description="Informar 'Crédito' caso a oferta envolva financiamento direto.",
    )
    conjuntos: list[ConjuntoAnuncios] = Field(..., min_length=1)
    anuncios: list[CriativoAnuncio] = Field(..., min_length=1)
    observacoes_compliance: list[str] = Field(default_factory=list)


def _limpar_json_bruto(texto: str) -> dict[str, Any]:
    """Extrai objeto JSON válido de respostas em texto livre ou blocos markdown."""
    bloco = re.search(r"```(?:json)?\s*(\{.*\})\s*```", texto, flags=re.DOTALL)
    candidato = bloco.group(1) if bloco else texto.strip()
    inicio = candidato.find("{")
    fim = candidato.rfind("}")
    if inicio == -1 or fim == -1 or fim <= inicio:
        raise ValueError("A resposta do CrewAI não contém um JSON válido.")
    return json.loads(candidato[inicio : fim + 1])


def extrair_plano_estruturado(result: Any) -> CampanhaMetaAdsPlan:
    """Converte o `CrewOutput` no modelo Pydantic `CampanhaMetaAdsPlan`."""
    pydantic_obj = getattr(result, "pydantic", None)
    if isinstance(pydantic_obj, CampanhaMetaAdsPlan):
        return pydantic_obj
    if isinstance(pydantic_obj, BaseModel):
        return CampanhaMetaAdsPlan.model_validate(pydantic_obj.model_dump())

    json_dict = getattr(result, "json_dict", None)
    if isinstance(json_dict, dict) and json_dict:
        return CampanhaMetaAdsPlan.model_validate(json_dict)

    raw_text = getattr(result, "raw", "") or str(result)
    return CampanhaMetaAdsPlan.model_validate(_limpar_json_bruto(raw_text))


def _formatar_lista_criativos(criativos_disponiveis: list[dict[str, Any]] | None) -> str:
    if not criativos_disponiveis:
        return "Nenhum arquivo de mídia local informado (preencher arquivo_criativo como null)."
    linhas = [
        f"- {item['nome']} ({item['tipo']}, {item['tamanho_kb']} KB)"
        for item in criativos_disponiveis
    ]
    return "Arquivos de mídia disponíveis na pasta de criativos:\n" + "\n".join(linhas)


def criar_crew_meta_ads(provider_override: str | None = None):
    """Monta os dois agentes (Gestor de Tráfego e Copywriter) e suas tasks sequenciais."""
    from crewai import Agent, Crew, Process, Task

    llm = build_crewai_llm(provider_override)

    gestor_trafego = Agent(
        role="Gestor de Tráfego Pago Especialista em Meta Ads",
        goal=(
            "Traduzir comandos de campanha em uma estrutura técnica completa para o "
            "Gerenciador de Anúncios (CBO/ABO, orçamento em BRL, segmentação geográfica "
            "precisa, conjuntos de anúncios e alertas de Categoria Especial de Anúncio)."
        ),
        backstory=(
            "Você atua há anos gerindo contas de performance no Brasil, especialmente "
            "campanhas locais de geração de leads (como repasse de financiamento veicular "
            "e serviços regionais). Você domina CBO, ABO, segmentação por cidade/raio "
            "e regras da Meta para anúncios de crédito/financiamento."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    copywriter = Agent(
        role="Copywriter de Performance para Meta Ads",
        goal=(
            "Redigir textos principais, títulos, descrições e CTAs altamente persuasivos "
            "em Português do Brasil, em total conformidade com as políticas da Meta, e "
            "consolidar toda a campanha no esquema JSON estruturado."
        ),
        backstory=(
            "Você escreve anúncios diretos e claros focados em geração de leads qualificados, "
            "evitando promessas enganosas ou termos que gerem reprovação automática na Meta "
            "(como afirmações de aprovação garantida de crédito). Você sempre entrega dados "
            "prontos para preenchimento automatizado."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    task_estrutura = Task(
        description=(
            "Analise a seguinte instrução de campanha:\n"
            "\"{instrucao}\"\n\n"
            "{criativos_contexto}\n\n"
            "Defina com precisão:\n"
            "1. Nome da campanha, objetivo (Leads, Trafego, Vendas ou Engajamento), "
            "tipo de orçamento (CBO ou ABO) e orçamento diário em BRL.\n"
            "2. Conjuntos de anúncios com segmentação geográfica exata para todas as "
            "cidades citadas na instrução, faixa etária recomendada e interesses.\n"
            "3. Caso o tema envolva financiamento ou crédito, sinalize a avaliação da "
            "Categoria Especial de Anúncio ('Crédito') e cuidados de segmentação."
        ),
        expected_output=(
            "Especificação técnica detalhada da campanha, conjuntos de anúncios, "
            "orçamento, cidades/raios e regras de conformidade."
        ),
        agent=gestor_trafego,
    )

    task_copy_e_json = Task(
        description=(
            "Com base na estrutura definida pelo Gestor de Tráfego e na instrução original:\n"
            "\"{instrucao}\"\n\n"
            "{criativos_contexto}\n\n"
            "1. Redija de 2 a 3 variações de anúncios em pt-BR (texto_principal, titulo curto "
            "com até 40 caracteres, descricao curta e cta).\n"
            "2. Quando houver arquivos listados acima, associe o nome do arquivo em "
            "`arquivo_criativo` e ajuste `formato` ('imagem_unica' ou 'video_curto').\n"
            "3. Consolide a estrutura completa da campanha e os criativos no formato JSON "
            "exigido pelo esquema CampanhaMetaAdsPlan.\n"
            "4. Nunca invente estatísticas falsas nem prometa aprovação automática de crédito."
        ),
        expected_output=(
            "Objeto JSON estruturado válido no padrão CampanhaMetaAdsPlan contendo "
            "campanha, conjuntos, anúncios e observações de compliance."
        ),
        agent=copywriter,
        context=[task_estrutura],
        output_pydantic=CampanhaMetaAdsPlan,
    )

    return Crew(
        agents=[gestor_trafego, copywriter],
        tasks=[task_estrutura, task_copy_e_json],
        process=Process.sequential,
        verbose=True,
    )


async def planejar_campanha(
    instrucao: str,
    provider_override: str | None = None,
    criativos_disponiveis: list[dict[str, Any]] | None = None,
) -> CampanhaMetaAdsPlan:
    """Executa a Crew de forma assíncrona e retorna o plano validado em Pydantic."""
    crew = criar_crew_meta_ads(provider_override=provider_override)
    result = await crew.akickoff(
        inputs={
            "instrucao": instrucao,
            "criativos_contexto": _formatar_lista_criativos(criativos_disponiveis),
        }
    )
    return extrair_plano_estruturado(result)
