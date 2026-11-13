"""Testes unitários e de contrato da API para o backend Meta Ads."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import agentes  # noqa: E402
import automacao  # noqa: E402
import criativos  # noqa: E402
import llm_config  # noqa: E402
import main  # noqa: E402


def _sample_plan() -> agentes.CampanhaMetaAdsPlan:
    return agentes.CampanhaMetaAdsPlan(
        nome_campanha="CBO_LEADS_REPASSE_CWB_CL",
        objetivo="Leads",
        tipo_orcamento="CBO",
        orcamento_diario_brl=500.0,
        estrategia_lance="Volume mais alto",
        categoria_especial_anuncio="Crédito",
        conjuntos=[
            agentes.ConjuntoAnuncios(
                nome="CJ01_Curitiba_CampoLargo",
                orcamento_diario_brl=None,
                publico=agentes.PublicoAlvo(
                    idade_minima=23,
                    idade_maxima=55,
                    localizacoes=["Curitiba, PR", "Campo Largo, PR"],
                    raio_km=25,
                    interesses_sugeridos=["Financiamento de veículos", "Automóveis"],
                ),
            )
        ],
        anuncios=[
            agentes.CriativoAnuncio(
                nome="AD01_Repasse_Sem_Burocracia",
                arquivo_criativo="banner_repasse.png",
                texto_principal="Quer transferir ou assumir financiamento de veículo em Curitiba e Campo Largo? Fale com nossa equipe.",
                titulo="Repasse de Financiamento",
                descricao="Atendimento rápido na região.",
                cta="Saiba mais",
            )
        ],
        observacoes_compliance=["Avaliar Categoria Especial: Crédito antes da publicação."],
    )


def test_provider_priority_and_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    cfg = llm_config.Settings(_env_file=None)

    providers = llm_config.list_providers(cfg)
    ids = [p["id"] for p in providers["providers"]]
    assert ids == ["opencode", "ollama", "anthropic", "openai", "google"]
    assert providers["active_provider"] == "ollama"

    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        llm_config.resolve_provider_config("anthropic", cfg)

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    cfg_with_key = llm_config.Settings(_env_file=None)
    resolved = llm_config.resolve_provider_config("anthropic", cfg_with_key)
    assert resolved.provider == "anthropic"
    assert resolved.model == "claude-sonnet-4-6"


def test_criativos_discovery_and_validation(tmp_path: Path) -> None:
    (tmp_path / "criativo_01.png").write_bytes(b"fake-png")
    (tmp_path / "video_02.mp4").write_bytes(b"fake-mp4")
    (tmp_path / "notas.txt").write_text("ignorar", encoding="utf-8")

    inventario = criativos.listar_criativos(str(tmp_path))
    assert inventario["total"] == 2
    assert [a["nome"] for a in inventario["arquivos"]] == ["criativo_01.png", "video_02.mp4"]
    assert [a["tipo"] for a in inventario["arquivos"]] == ["imagem", "video"]

    with pytest.raises(ValueError, match="não suportada"):
        criativos.validar_nome_arquivo_upload("malware.exe")


def test_extrair_plano_estruturado_fallback_markdown_json() -> None:
    plan = _sample_plan()
    fake_result = SimpleNamespace(
        pydantic=None,
        json_dict=None,
        raw=f"Aqui está o JSON solicitado:\n```json\n{json.dumps(plan.model_dump())}\n```",
    )
    parsed = agentes.extrair_plano_estruturado(fake_result)
    assert parsed.nome_campanha == plan.nome_campanha
    assert parsed.orcamento_diario_brl == 500.0
    assert parsed.anuncios[0].arquivo_criativo == "banner_repasse.png"


def test_prompt_navegador_enforces_draft_and_media_paths(tmp_path: Path) -> None:
    plan = _sample_plan()
    img = tmp_path / "banner_repasse.png"
    img.write_bytes(b"fake")
    prompt = automacao.construir_prompt_navegador(
        plan,
        "https://adsmanager.facebook.com/adsmanager/manage/campaigns",
        [str(img)],
    )
    assert "NUNCA clique em \"Publicar\"" in prompt
    assert "Salvar como rascunho" in prompt
    assert "AUTH_REQUIRED" in prompt
    assert "upload_file" in prompt
    assert str(img) in prompt


def test_fastapi_endpoints_with_mocks(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    (tmp_path / "oferta.jpg").write_bytes(b"img-bytes")
    plan = _sample_plan()

    async def fake_planejar(
        instrucao: str,
        provider_override: str | None = None,
        criativos_disponiveis=None,
    ):
        assert "Campo Largo" in instrucao
        nomes = {c["nome"] for c in (criativos_disponiveis or [])}
        assert nomes == {"novo_banner.png", "oferta.jpg"}
        return plan

    async def fake_executar(plano, provider_override: str | None = None, caminhos_criativos=None):
        assert caminhos_criativos
        assert any(p.endswith("oferta.jpg") for p in caminhos_criativos)
        assert any(p.endswith("novo_banner.png") for p in caminhos_criativos)
        return {
            "status": "rascunho_criado",
            "provider": provider_override or "ollama",
            "model": "qwen2.5:7b",
            "criativos_anexados": caminhos_criativos,
            "steps_executados": 6,
            "sucesso": True,
            "resultado_navegador": "Campanha salva como Rascunho.",
            "erros": [],
        }

    monkeypatch.setattr(main, "planejar_campanha", fake_planejar)
    monkeypatch.setattr(main, "executar_rascunho_meta_ads", fake_executar)

    client = TestClient(main.app)

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    res_list = client.get("/criativos", params={"pasta": str(tmp_path)})
    assert res_list.status_code == 200
    assert res_list.json()["total"] == 1

    res_upload = client.post(
        "/criativos/upload",
        data={"pasta": str(tmp_path)},
        files={"files": ("novo_banner.png", b"png-data", "image/png")},
    )
    assert res_upload.status_code == 200
    assert res_upload.json()["salvos"] == ["novo_banner.png"]

    res_create = client.post(
        "/campanhas/criar",
        json={
            "instrucao": "Criar campanha CBO de leads para repasse de financiamento, R$ 500/dia, para Campo Largo e Curitiba",
            "pasta_criativos": str(tmp_path),
            "executar_navegador": True,
            "provider": "anthropic",
        },
    )
    assert res_create.status_code == 200
    body = res_create.json()
    assert body["criativos_encontrados"]["total"] == 2
    assert body["automacao"]["status"] == "rascunho_criado"
    assert body["automacao"]["provider"] == "anthropic"


def test_fallback_deterministico_when_llm_offline() -> None:
    plan = agentes.gerar_plano_fallback_deterministico(
        "Criar campanha CBO de leads para repasse de financiamento, R$ 500/dia, para Campo Largo e Curitiba"
    )
    assert plan.orcamento_diario_brl == 500.0
    assert plan.tipo_orcamento == "CBO"
    assert any("Curitiba" in cid for cid in plan.conjuntos[0].publico.localizacoes)
