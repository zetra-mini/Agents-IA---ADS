"""Utilitários para descoberta e upload seguro de criativos (imagens e vídeos) locais."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

EXTENSOES_IMAGEM = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
EXTENSOES_VIDEO = {".mp4", ".mov", ".m4v", ".avi", ".webm"}
EXTENSOES_SUPORTADAS = EXTENSOES_IMAGEM | EXTENSOES_VIDEO


def resolver_pasta_criativos(pasta: str | None, default_dir: str) -> Path:
    """Resolve o caminho da pasta de criativos, com fallback seguro para execução local."""
    if pasta and pasta.strip():
        return Path(pasta.strip()).expanduser().resolve()

    candidato = Path(default_dir).expanduser()
    # Quando rodando fora do container Docker, `./criativos` evita falha caso `/app/criativos` não exista.
    if not candidato.exists() and default_dir.startswith("/app/"):
        local_fallback = Path(__file__).resolve().parent / "criativos"
        local_fallback.mkdir(parents=True, exist_ok=True)
        return local_fallback.resolve()

    candidato.mkdir(parents=True, exist_ok=True)
    return candidato.resolve()


def _classificar_arquivo(caminho: Path) -> Literal["imagem", "video"] | None:
    ext = caminho.suffix.lower()
    if ext in EXTENSOES_IMAGEM:
        return "imagem"
    if ext in EXTENSOES_VIDEO:
        return "video"
    return None


def listar_criativos(pasta: str | None, default_dir: str = "./criativos") -> dict[str, Any]:
    """Lista arquivos de imagem/vídeo suportados na pasta informada (ordenada por nome)."""
    diretorio = resolver_pasta_criativos(pasta, default_dir)
    if not diretorio.exists() or not diretorio.is_dir():
        raise ValueError(f"Pasta de criativos não encontrada: {diretorio}")

    arquivos: list[dict[str, Any]] = []
    for item in sorted(diretorio.iterdir(), key=lambda p: p.name.lower()):
        if not item.is_file():
            continue
        tipo = _classificar_arquivo(item)
        if not tipo:
            continue
        stat = item.stat()
        arquivos.append(
            {
                "nome": item.name,
                "caminho": str(item.resolve()),
                "tipo": tipo,
                "extensao": item.suffix.lower(),
                "tamanho_kb": round(stat.st_size / 1024, 1),
            }
        )

    return {
        "pasta": str(diretorio),
        "total": len(arquivos),
        "arquivos": arquivos,
    }


def validar_nome_arquivo_upload(filename: str) -> str:
    """Sanitiza o nome do arquivo enviado via upload e valida extensão de mídia."""
    nome_limpo = os.path.basename(filename or "").strip()
    if not nome_limpo:
        raise ValueError("Nome de arquivo inválido.")
    ext = Path(nome_limpo).suffix.lower()
    if ext not in EXTENSOES_SUPORTADAS:
        permitidas = ", ".join(sorted(EXTENSOES_SUPORTADAS))
        raise ValueError(f"Extensão '{ext}' não suportada. Use: {permitidas}.")
    return nome_limpo
