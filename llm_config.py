"""Seletor unificado de provedores de LLM para CrewAI e browser-use.

Prioriza execução local/OpenCode (opencode e ollama) e mantém provedores externos
(Anthropic Claude, OpenAI GPT-4o, Google Gemini) selecionáveis via `.env` ou override por requisição.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

ProviderName = Literal["opencode", "ollama", "anthropic", "openai", "google"]

PROVIDER_ORDER: tuple[ProviderName, ...] = (
    "opencode",
    "ollama",
    "anthropic",
    "openai",
    "google",
)


@dataclass(frozen=True)
class ProviderMetadata:
    """Metadados descritivos e chaves de configuração de um provedor LLM."""

    id: ProviderName
    label: str
    locality: Literal["local", "external"]
    crewai_prefix: str
    requires_api_key: bool


PROVIDER_REGISTRY: dict[ProviderName, ProviderMetadata] = {
    "opencode": ProviderMetadata(
        id="opencode",
        label="OpenCode (Prioritário / Endpoint Compatível)",
        locality="local",
        crewai_prefix="openai",
        requires_api_key=False,
    ),
    "ollama": ProviderMetadata(
        id="ollama",
        label="Ollama (100% Localhost)",
        locality="local",
        crewai_prefix="ollama",
        requires_api_key=False,
    ),
    "anthropic": ProviderMetadata(
        id="anthropic",
        label="Anthropic Claude",
        locality="external",
        crewai_prefix="anthropic",
        requires_api_key=True,
    ),
    "openai": ProviderMetadata(
        id="openai",
        label="OpenAI (GPT-4o / GPT-4.1)",
        locality="external",
        crewai_prefix="openai",
        requires_api_key=True,
    ),
    "google": ProviderMetadata(
        id="google",
        label="Google Gemini",
        locality="external",
        crewai_prefix="gemini",
        requires_api_key=True,
    ),
}


class Settings(BaseSettings):
    """Configurações centralizadas lidas do ambiente ou arquivo `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_provider: ProviderName = "opencode"

    # 1. OpenCode (prioritário local/gateway - modelos 100% grátis)
    opencode_model: str = "opencode/mimo-v2.6-flash-free"
    opencode_base_url: str = "http://127.0.0.1:4096/v1"
    opencode_api_key: str = "opencode"

    # 2. Ollama (100% Localhost)
    ollama_model: str = "qwen2.5:0.5b"
    ollama_base_url: str = "http://127.0.0.1:11434"

    # 3. Opções Externas
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    # Automação browser-use & Meta Ads
    meta_ads_url: str = "https://adsmanager.facebook.com/adsmanager/manage/campaigns"
    browser_headless: bool = False
    browser_user_data_dir: str = "/app/browser_profile"
    browser_max_steps: int = 40
    creatives_dir: str = "./criativos"

    # API FastAPI & Dashboards Astro/Svelte
    app_host: str = "0.0.0.0"
    app_port: int = 8010
    cors_origins: str = (
        "http://localhost:4321,http://localhost:5173,"
        "http://127.0.0.1:4321,http://127.0.0.1:5173,"
        "http://127.0.0.1:4173,http://localhost:4173"
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """Converte a string de origens separadas por vírgula em lista limpa."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


def get_settings() -> Settings:
    """Retorna instância atualizada das configurações."""
    return Settings()


@dataclass(frozen=True)
class ResolvedProviderConfig:
    """Credenciais e parâmetros resolvidos para instanciar clientes LLM."""

    provider: ProviderName
    model: str
    api_key: str | None
    base_url: str | None


def resolve_provider_config(
    provider_override: str | None = None,
    settings: Settings | None = None,
) -> ResolvedProviderConfig:
    """Resolve e valida o provedor selecionado sem instanciar SDKs pesados."""
    cfg = settings or get_settings()
    raw_provider = (provider_override or cfg.llm_provider).strip().lower()

    if raw_provider not in PROVIDER_REGISTRY:
        valid = ", ".join(PROVIDER_ORDER)
        raise ValueError(f"Provedor inválido '{raw_provider}'. Opções válidas: {valid}.")

    provider: ProviderName = raw_provider  # type: ignore[assignment]
    meta = PROVIDER_REGISTRY[provider]

    table: dict[ProviderName, tuple[str, str | None, str | None]] = {
        "opencode": (cfg.opencode_model, cfg.opencode_api_key or "opencode", cfg.opencode_base_url),
        "ollama": (cfg.ollama_model, None, cfg.ollama_base_url),
        "anthropic": (cfg.anthropic_model, cfg.anthropic_api_key.strip() or None, None),
        "openai": (cfg.openai_model, cfg.openai_api_key.strip() or None, None),
        "google": (cfg.gemini_model, cfg.gemini_api_key.strip() or None, None),
    }

    model, api_key, base_url = table[provider]
    if meta.requires_api_key and not api_key:
        env_var = {
            "anthropic": "ANTHROPIC_API_KEY",
            "openai": "OPENAI_API_KEY",
            "google": "GEMINI_API_KEY",
        }[provider]
        raise ValueError(
            f"Provedor '{provider}' selecionado, mas '{env_var}' não está configurado no .env."
        )

    return ResolvedProviderConfig(
        provider=provider,
        model=model,
        api_key=api_key,
        base_url=base_url,
    )


def _mask_key(raw: str | None) -> str | None:
    """Retorna versão mascarada da chave de API (ex: sk-p...9a1b) para exibição segura na UI."""
    if not raw or not raw.strip():
        return None
    clean = raw.strip()
    if len(clean) <= 8:
        return "****" + clean[-2:]
    return f"{clean[:4]}...{clean[-4:]}"


def list_providers(settings: Settings | None = None) -> dict[str, Any]:
    """Lista os provedores na ordem prioritária para consumo pelos dashboards."""
    cfg = settings or get_settings()
    key_map: dict[ProviderName, str] = {
        "opencode": cfg.opencode_api_key,
        "ollama": "",
        "anthropic": cfg.anthropic_api_key,
        "openai": cfg.openai_api_key,
        "google": cfg.gemini_api_key,
    }
    url_map: dict[ProviderName, str | None] = {
        "opencode": cfg.opencode_base_url,
        "ollama": cfg.ollama_base_url,
        "anthropic": None,
        "openai": None,
        "google": None,
    }
    items = []
    for name in PROVIDER_ORDER:
        meta = PROVIDER_REGISTRY[name]
        try:
            resolved = resolve_provider_config(name, cfg)
            configured = True
            model = resolved.model
        except ValueError:
            configured = False
            model = getattr(cfg, f"{'gemini' if name == 'google' else name}_model")
        raw_key = key_map[name]
        items.append(
            {
                "id": meta.id,
                "label": meta.label,
                "locality": meta.locality,
                "model": model,
                "configured": configured,
                "requires_api_key": meta.requires_api_key,
                "has_key": bool(raw_key and raw_key.strip()),
                "masked_key": _mask_key(raw_key) if meta.requires_api_key else None,
                "base_url": url_map[name],
                "active": name == cfg.llm_provider,
            }
        )
    return {"active_provider": cfg.llm_provider, "providers": items}


def update_provider_credentials(
    *,
    active_provider: str | None = None,
    openai_api_key: str | None = None,
    openai_model: str | None = None,
    anthropic_api_key: str | None = None,
    anthropic_model: str | None = None,
    gemini_api_key: str | None = None,
    gemini_model: str | None = None,
    ollama_model: str | None = None,
    ollama_base_url: str | None = None,
    opencode_model: str | None = None,
    opencode_base_url: str | None = None,
    opencode_api_key: str | None = None,
    env_path: Path | None = None,
) -> dict[str, Any]:
    """Atualiza chaves de API e modelos em tempo de execução (os.environ) e persiste no `.env`."""
    updates: dict[str, str] = {}

    if active_provider and active_provider.strip().lower() in PROVIDER_REGISTRY:
        updates["LLM_PROVIDER"] = active_provider.strip().lower()

    field_to_env = {
        "OPENAI_API_KEY": openai_api_key,
        "OPENAI_MODEL": openai_model,
        "ANTHROPIC_API_KEY": anthropic_api_key,
        "ANTHROPIC_MODEL": anthropic_model,
        "GEMINI_API_KEY": gemini_api_key,
        "GEMINI_MODEL": gemini_model,
        "OLLAMA_MODEL": ollama_model,
        "OLLAMA_BASE_URL": ollama_base_url,
        "OPENCODE_MODEL": opencode_model,
        "OPENCODE_BASE_URL": opencode_base_url,
        "OPENCODE_API_KEY": opencode_api_key,
    }

    for env_key, val in field_to_env.items():
        if val is not None:
            clean_val = val.strip()
            updates[env_key] = clean_val
            os.environ[env_key] = clean_val

    if "LLM_PROVIDER" in updates:
        os.environ["LLM_PROVIDER"] = updates["LLM_PROVIDER"]

    target_env = env_path or Path(".env")
    existing_lines: list[str] = []
    if target_env.exists():
        existing_lines = target_env.read_text(encoding="utf-8").splitlines()

    updated_keys: set[str] = set()
    new_lines: list[str] = []
    for line in existing_lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            new_lines.append(line)
            continue
        k = stripped.split("=", 1)[0].strip()
        if k in updates:
            new_lines.append(f"{k}={updates[k]}")
            updated_keys.add(k)
        else:
            new_lines.append(line)

    for k, v in updates.items():
        if k not in updated_keys:
            new_lines.append(f"{k}={v}")

    target_env.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    return list_providers(get_settings())


def build_crewai_llm(
    provider_override: str | None = None,
    settings: Settings | None = None,
) -> Any:
    """Instancia `crewai.LLM` para o provedor escolhido."""
    from crewai import LLM

    resolved = resolve_provider_config(provider_override, settings)
    prefix = PROVIDER_REGISTRY[resolved.provider].crewai_prefix
    model_id = (
        resolved.model
        if resolved.provider != "opencode" and resolved.model.startswith(f"{prefix}/")
        else f"{prefix}/{resolved.model}"
    )

    kwargs: dict[str, Any] = {"model": model_id, "temperature": 0.2}
    if resolved.api_key:
        kwargs["api_key"] = resolved.api_key
    if resolved.base_url:
        kwargs["base_url"] = resolved.base_url

    return LLM(**kwargs)


def build_browser_use_llm(
    provider_override: str | None = None,
    settings: Settings | None = None,
) -> Any:
    """Instancia o wrapper de LLM nativo do `browser-use` (0.11.x)."""
    from browser_use import ChatAnthropic, ChatGoogle, ChatOllama, ChatOpenAI

    resolved = resolve_provider_config(provider_override, settings)

    if resolved.provider == "opencode":
        return ChatOpenAI(
            model=resolved.model,
            api_key=resolved.api_key or "opencode",
            base_url=resolved.base_url,
        )
    if resolved.provider == "ollama":
        return ChatOllama(model=resolved.model, host=resolved.base_url)
    if resolved.provider == "anthropic":
        return ChatAnthropic(model=resolved.model, api_key=resolved.api_key)
    if resolved.provider == "openai":
        return ChatOpenAI(model=resolved.model, api_key=resolved.api_key)
    return ChatGoogle(model=resolved.model, api_key=resolved.api_key)
