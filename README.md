# Agents IA ADS — Orquestrador Meta Ads (FastAPI + CrewAI + browser-use + Svelte)

Sistema full-stack Dockerizado para planejar campanhas Meta Ads com agentes **CrewAI** (*Gestor de Tráfego* + *Copywriter*), selecionar criativos a partir de uma **pasta local**, preencher rascunhos no Gerenciador de Anúncios via **browser-use** e operar tudo por um dashboard em **Svelte**.

## Estrutura do Projeto

- `main.py`: API FastAPI (`/health`, `/providers`, `/criativos`, `/criativos/upload`, `/campanhas/planejar`, `/campanhas/criar`).
- `agentes.py`: Agentes CrewAI e esquema Pydantic (`CampanhaMetaAdsPlan`).
- `automacao.py`: Automação `browser-use` com `available_file_paths` para upload de criativos e trava para salvar apenas como **Rascunho**.
- `criativos.py`: Descoberta e validação segura de imagens (`.png`, `.jpg`, `.jpeg`, `.webp`, `.gif`) e vídeos (`.mp4`, `.mov`, `.m4v`, `.avi`, `.webm`) na pasta configurada.
- `llm_config.py`: Seletor unificado de IA priorizando `opencode` e `ollama` local, com suporte a `anthropic`, `openai` e `google`.
- `frontend/`: Painel Svelte 5 + Vite para testar instruções, trocar provedores, escanear/enviar criativos e visualizar os planos.
- `Dockerfile`, `frontend/Dockerfile` e `docker-compose.yml`: Stack completa isolada em Docker.

## Onde Informar a Pasta de Criativos

1. **Via Interface Web (Frontend):** No bloco **2. Pasta de Criativos**, informe o caminho completo da pasta local (ex.: `C:\MeusCriativos\Repasse` rodando localmente ou `/app/criativos` no Docker) e clique em **Escanear Pasta**, ou envie arquivos diretamente pelo botão de upload.
2. **Via `.env` / Docker Volume:** Defina `HOST_CREATIVES_DIR` no `.env` apontando para qualquer pasta do seu computador; o `docker-compose.yml` monta essa pasta automaticamente em `/app/criativos` dentro do container.
3. **Via API:** Envie `"pasta_criativos": "/app/criativos"` no JSON de `POST /campanhas/criar`.

## Como Rodar via Docker

```bash
cp .env.example .env
docker compose up --build -d
```

Acesse:
- Frontend Svelte: `http://localhost:5173`
- API FastAPI (Swagger): `http://localhost:8000/docs`

## Como Rodar Localmente (Sem Docker)

Backend:
```bash
uv run --python 3.11 --with-requirements requirements.txt uvicorn main:app --host 127.0.0.1 --port 8000
```

Frontend:
```bash
cd frontend
npm install
npm run dev
```
