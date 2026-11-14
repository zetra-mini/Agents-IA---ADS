# AdSimples AI — Meta Ads Copilot & Orchestrator 🚀

[![Status](https://img.shields.io/badge/Status-Beta%20%2F%20WIP-orange?style=flat-square)](https://github.com/zetra-mini/Agents-IA---ADS)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?style=flat-square&logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-green?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Svelte](https://img.shields.io/badge/Svelte-5%20Runes-ff3e00?style=flat-square&logo=svelte)](https://svelte.dev/)
[![Meta Graph API](https://img.shields.io/badge/Meta%20Graph%20API-v22.0-0866FF?style=flat-square&logo=meta)](https://developers.facebook.com/docs/graph-api)
[![License](https://img.shields.io/badge/License-MIT-lightgrey?style=flat-square)](LICENSE)

> 💡 **Projeto Open Source em Construção Ativa (Work In Progress - WIP):**  
> Este repositório é um projeto público e colaborativo para quem busca criar, planejar, orquestrar e otimizar campanhas no **Meta Ads** utilizando Inteligência Artificial (CrewAI, OpenAdKit, Ollama, OpenCode e modelos externos como Gemini, OpenAI e Claude).  
> **Toda ajuda é bem-vinda!** Veja nosso [Guia de Contribuição (CONTRIBUTING.md)](CONTRIBUTING.md) e as [Regras do Projeto (RULES.md)](RULES.md) para saber como participar.

---

## 🧭 Visão Geral

O **AdSimples AI** integra a **API Oficial da Meta (Graph API v22.0)** com agentes autônomos de IA para transformar a complexidade do Gerenciador de Anúncios em um fluxo intuitivo, seguro e rápido:

1. **Gerenciador de Anúncios Unificado:**
   - Visualização e alternância rápida entre **Campanhas**, **Conjuntos de Anúncios** e **Anúncios**.
   - Filtros inteligentes por status (*Todos, Ativos, Pausados*), objetivos e pesquisa em tempo real.
   - Ativação e desativação direta (`ACTIVE` / `PAUSED`) com um clique sincronizado com a Meta.
   - Ajuste rápido de orçamento diário (+20%, -20% ou edição inline).
   - Duplicação segura de campanhas e exclusão com confirmação.

2. **Criação Assistida Passo a Passo:**
   - Criação orientada em 3 etapas (Campanha CBO/ABO -> Conjunto com segmentação regional/interesses -> Anúncio com seleção de Página Facebook e Perfil Instagram).
   - Pré-visualização instantânea do criativo no formato feed com copy gerada por IA.
   - Modo seguro: criação com status **Pausado / Rascunho** por padrão para evitar gastos acidentais.

3. **Arquitetura de IA Híbrida & Flexível:**
   - **Local / Custo Zero (Prioritário):** Suporte nativo ao **OpenCode CLI** e ao **Ollama** (`http://127.0.0.1:11434`, ex.: `qwen2.5`, `llama3.2`).
   - **APIs Externas:** Integração direta com **Google Gemini** (`gemini-2.5-flash`), **OpenAI** (`gpt-4o`) e **Anthropic Claude** (`claude-sonnet-4-6`).

4. **Ferramentas de Tráfego & OpenAdKit:**
   - Cérebro da Marca (extração automática de proposta de valor).
   - Gerador de Copies com 3 ângulos de alta conversão.
   - Roteiros para Reels & Funil de WhatsApp.
   - Diagnóstico Creative Score (0 a 10) e espionagem estruturada de concorrentes.
   - Robô Otimizador com regras automáticas de escala e corte de custos.
   - Módulo dedicado de **Relatórios & Evolução Diária**.

---

## 🏗️ Estrutura do Repositório

```text
├── main.py                     # API FastAPI (Rotas, proxy Graph API e orquestração)
├── meta_hub.py                 # Conector Graph API v22.0 (Campanhas, AdSets, Ads, Páginas)
├── agentes.py                  # Agentes CrewAI (Gestor de Tráfego & Copywriter)
├── openadkit_agents.py         # Módulos especializados OpenAdKit (Creative Score, Roteiros, Espião)
├── llm_config.py               # Seletor unificado de IA (Ollama, OpenCode, Gemini, OpenAI, Claude)
├── automacao.py                # Automação browser-use para preenchimento de rascunhos
├── criativos.py                # Leitura e validação segura de imagens e vídeos locais
├── frontend/                   # Interface moderna em Svelte 5 + Vite (Dark Mode SaaS)
│   ├── src/
│   │   ├── App.svelte          # Shell do aplicativo, rotas internas e Gerenciador de Anúncios
│   │   ├── SimuladorMetaAds.svelte # Pré-visualização interativa de anúncios
│   │   └── PainelAdSimples.svelte  # Controles legados e integrações adicionais
│   └── package.json
├── docker-compose.yml          # Orquestração de containers Backend + Frontend
├── Dockerfile                  # Containerização do Backend FastAPI
├── CONTRIBUTING.md             # Guia de contribuição para a comunidade open-source
├── RULES.md                    # Regras arquiteturais para humanos e agentes de IA
└── .env.example                # Modelo de variáveis de ambiente sem segredos
```

---

## 🚀 Como Iniciar

### Opção 1: Via Docker (Recomendado para Produção/Ambiente Isolado)

```bash
# 1. Clone o repositório
git clone https://github.com/zetra-mini/Agents-IA---ADS.git
cd Agents-IA---ADS

# 2. Configure as variáveis de ambiente
cp .env.example .env

# 3. Suba os containers
docker compose up --build -d
```

Acesse:
- **Painel Web (Frontend):** `http://localhost:5173`
- **API Swagger (FastAPI):** `http://localhost:8010/docs`

---

### Opção 2: Rodando Localmente

#### 1. Backend (FastAPI):
Recomendamos o uso de [`uv`](https://github.com/astral-sh/uv) para inicialização ultra-rápida:
```bash
cp .env.example .env
uv run --python 3.11 --with-requirements requirements.txt uvicorn main:app --host 127.0.0.1 --port 8010 --reload
```
*(Ou via `pip install -r requirements.txt && uvicorn main:app --host 127.0.0.1 --port 8010 --reload`)*

#### 2. Frontend (Svelte 5):
```bash
cd frontend
npm install
npm run dev
```
O Vite iniciará em `http://127.0.0.1:5173`.

---

## 🔒 Segurança & Privacidade de Dados

Este repositório segue uma política rígida de **Zero Dados Sensíveis**:
- Nunca comite tokens de acesso (`EAAB...`), chaves de API (`AIzaSy...`, `sk-...`), senhas ou credenciais.
- Nunca comite nomes reais de pessoas físicas, CPFs ou IDs reais de contas de anúncio.
- O arquivo `.env` e `.meta_session.json` estão protegidos e ignorados pelo `.gitignore`.
- Antes de enviar Pull Requests, consulte o [CONTRIBUTING.md](CONTRIBUTING.md).

---

## 🤝 Como Contribuir

Se você deseja sugerir uma melhoria, corrigir um bug ou implementar novas integrações:
1. Abra uma **Issue** explicando a ideia ou o problema encontrado.
2. Veja as tarefas abertas no [Roadmap do CONTRIBUTING.md](CONTRIBUTING.md#2-roadmap--onde-você-pode-ajudar).
3. Leia as [Regras do Projeto em RULES.md](RULES.md).
4. Envie seu **Pull Request**!

---

## 📄 Licença

Distribuído sob a licença **MIT**. Veja `LICENSE` para mais detalhes.  
*Nota: Este projeto não é afiliado, endossado ou patrocinado pela Meta Platforms, Inc.*
