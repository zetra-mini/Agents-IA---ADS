# Guia de Contribuição — AdSimples AI / Meta Ads Copilot

Bem-vindo(a) ao repositório open-source do **AdSimples AI** (Agents IA ADS)!

> ⚠️ **Aviso de Projeto em Desenvolvimento (WIP / Beta):**  
> Este sistema é um projeto de código aberto em construção ativa. Algumas funcionalidades estão em fase de protótipo, validação ou implementação assistida. A sua ajuda para testar, corrigir bugs, refatorar código e sugerir novas ferramentas é extremamente bem-vinda!

---

## 🔒 1. Política de Segurança & Privacidade (REGRA DE OURO)

Para proteger a integridade dos contribuidores e de quem utiliza o sistema, **esta regra é inegociável**:

1. **PROIBIDO comitar credenciais, tokens e chaves de API:**
   - Jamais submeta chaves como `OPENAI_API_KEY`, `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENCODE_API_KEY`.
   - Jamais submeta tokens da Meta Graph API (`EAAB...`, `EAA...`) ou segredos de aplicativo (`app_secret`).
2. **PROIBIDO comitar dados pessoais reais:**
   - Nunca insira CPFs, CNPJs, nomes de pessoas físicas reais, e-mails pessoais ou números de telefone no código ou histórico git.
   - Não submeta IDs de contas de anúncios reais (`act_...`), IDs de Páginas do Facebook ou contas do Instagram reais. Use sempre valores mockados/fictícios (ex.: `act_0000000000000000`, `page_demo_1`).
3. **Uso do `.env`:**
   - O arquivo `.env` e `.meta_session.json` são estritamente ignorados pelo `.gitignore`.
   - Sempre utilize o `.env.example` como modelo para novos parâmetros de ambiente, mantendo valores sensíveis vazios.
4. **Arquivos locais e criativos:**
   - Imagens ou vídeos pessoais colocados na pasta `criativos/` ou no perfil de automação `browser_profile/` não devem ser comitados.

---

## 🗺️ 2. Roadmap & Onde Você Pode Ajudar

Atualmente, estamos buscando contribuições nas seguintes frentes prioritárias:

- [ ] **Publicação Completa de Anúncios (Graph API):** Finalizar o fluxo de envio de `adcreative` + upload de imagem/vídeo para a biblioteca da Meta e criação do objeto `ad` vinculado ao conjunto de anúncios.
- [ ] **Módulo de Relatórios & Insights Históricos:** Criar gráficos temporais detalhados consumindo o endpoint `/insights` da Meta Graph API (com filtros por data: últimos 7 dias, 14 dias, 30 dias, mês atual).
- [ ] **Regras Avançadas do Robô Otimizador:** Desenvolver automações personalizáveis (ex.: pausar conjunto se CPA > R\$ X após Y impressões, aumentar orçamento em 20% se ROAS > 3x).
- [ ] **Mocks & Testes Automatizados:** Expandir a cobertura de testes no backend (`pytest`) simulando respostas da Graph API v22.0 sem requisições de rede externas.
- [ ] **Responsividade & Acessibilidade:** Melhorias contínuas na interface Svelte 5 para telas móveis ultra-compactas, tablets e navegação por teclado (a11y).
- [ ] **Suporte a Múltiplos Motores de IA:** Validação e aprimoramento de prompts para modelos locais via Ollama (`qwen2.5`, `deepseek-r1`, `llama3.2`) e gateways OpenCode.

---

## 🛠️ 3. Configuração do Ambiente de Desenvolvimento

### Pré-requisitos
- **Python 3.11+** com `uv` ou `pip`
- **Node.js 18+** e `npm`
- (Opcional) **Docker** e **Docker Compose**
- (Opcional) **Ollama** para processamento de IA 100% local

### Rodando Localmente

#### Backend (FastAPI):
```bash
# Copie as variáveis de exemplo
cp .env.example .env

# Inicie o servidor FastAPI via uv
uv run --python 3.11 --with-requirements requirements.txt uvicorn main:app --host 127.0.0.1 --port 8010 --reload
```
A documentação interativa Swagger estará disponível em: `http://127.0.0.1:8010/docs`

#### Frontend (Svelte 5 + Vite):
```bash
cd frontend
npm install
npm run dev
```
O painel estará disponível em: `http://127.0.0.1:5173`

#### Verificando Build do Frontend:
Antes de abrir qualquer Pull Request, certifique-se de que a build de produção compila sem erros:
```bash
cd frontend
npm run build
```

---

## 📐 4. Padrões de Código e Arquitetura

- **Backend (Python):**
  - Código limpo seguindo a PEP 8.
  - Tipagem estática com Pydantic v2 e Type Annotations.
  - Comunicação assíncrona (`async`/`await`) utilizando `httpx` para chamadas HTTP externas.
  - Tratamento resiliente de erros em endpoints do Graph API, garantindo fallbacks amigáveis para a interface.
- **Frontend (Svelte):**
  - Uso dos **Svelte 5 Runes** (`$state`, `$derived`, `$props`, `$effect`).
  - Interface no padrão Dark Mode SaaS moderno, mantendo consistência com as variáveis CSS de tema em `App.svelte`.
  - Navegação lateral em gaveta retrátil (menu hambúrguer) para manter a área de trabalho limpa e sem poluição visual no topo da tela.
- **Mensagens de Commit:**
  - Adotamos o padrão [Conventional Commits](https://www.conventionalcommits.org/):
    - `feat:` Nova funcionalidade
    - `fix:` Correção de bug
    - `docs:` Alterações em documentação
    - `style:` Formatação de código ou ajustes visuais de CSS
    - `refactor:` Refatoração de código sem alteração de funcionalidade
    - `test:` Adição ou modificação de testes

---

## 🚀 5. Como Enviar sua Contribuição (Pull Request)

1. Faça um **Fork** deste repositório.
2. Crie uma branch com um nome descritivo para a sua mudança:
   ```bash
   git checkout -b feature/minha-nova-funcionalidade
   # ou
   git checkout -b fix/correcao-bug-campanhas
   ```
3. Faça suas alterações, sempre auditando para não incluir dados pessoais ou segredos de API.
4. Execute os testes e verifique se o frontend constrói perfeitamente:
   ```bash
   pytest
   cd frontend && npm run build
   ```
5. Faça o commit e envie para o seu Fork:
   ```bash
   git commit -m "feat: descricao sucinta da melhoria"
   git push origin feature/minha-nova-funcionalidade
   ```
6. Abra um **Pull Request** detalhando:
   - Qual problema a mudança resolve ou qual funcionalidade adiciona.
   - Como testar a alteração.
   - Capturas de tela (se houver alteração de interface).

Muito obrigado por contribuir para tornar a gestão e automação de anúncios Meta Ads acessível, inteligente e aberta para todos!
