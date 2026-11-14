# Regras do Projeto — AdSimples AI

Este documento estabelece as diretrizes arquiteturais, operacionais e de governança para qualquer desenvolvedor humano ou **Agente de IA** (Antigravity, OpenCode, Claude Code, Cursor, Codex) que trabalhe neste repositório.

---

## 1. Comunicação e Idioma
- **Idioma Padrão:** Toda a interface do usuário, documentação, comentários no código e mensagens de commit devem ser redigidos prioritariamente em **Português do Brasil (pt-BR)**.
- **Termos Técnicos:** Termos consolidados da computação e da Meta Ads API (ex.: *AdSet, CBO, ABO, Creative, Hook, ROAS, CPA, CTR, Runes, Endpoint*) podem ser mantidos no formato original.

---

## 2. Segurança Absoluta de Credenciais e Privacidade
- **Zero Segredos no Repositório:** Sob nenhuma hipótese adicione tokens de API (Meta Graph API, OpenAI, Google Gemini, Anthropic, OpenCode), credenciais, certificados ou senhas ao controle de versão.
- **Zero Dados Pessoais:** Nunca adicione CPFs, nomes de pessoas reais, números de telefone, endereços, IDs de contas de anúncios reais (`act_...`) ou nomes de páginas empresariais reais diretamente nos fontes. Use sempre dados genéricos ou mockados (`act_0000000000000000`, `Página Demo`).
- **Verificação Contínua do `.gitignore`:** Arquivos `.env`, `.meta_session.json`, `browser_profile/`, `*.log`, `*.token` e pastas de criativos do usuário devem permanecer estritamente fora do git.

---

## 3. Arquitetura de IA Híbrida & Prioridade de Motores
Ao implementar ou estender funcionalidades que consumam modelos de linguagem (LLM) no backend ou no frontend:
1. **Prioridade para Motores Locais e Abertos:** Estruture e mantenha sempre suporte padrão para:
   - **OpenCode CLI / OpenCode Server** (`opencode/mimo-v2.6-flash-free` ou compatível OpenAI).
   - **IA Local (Ollama)** (`http://127.0.0.1:11434`, ex.: `qwen2.5:0.5b`, `llama3.2`).
2. **Provedores Externos Opcionais:** Mantenha suporte integrado e alternável via interface e `.env` para:
   - Google Gemini (`gemini-2.5-flash` / `gemini-2.0-flash`).
   - OpenAI (`gpt-4o` / `gpt-4.1`).
   - Anthropic Claude (`claude-sonnet-4-6`).
3. **Não Dependência Exclusiva de APIs Pagas:** O sistema deve funcionar mesmo quando o usuário não possuir chaves de API pagas, utilizando Ollama local ou OpenCode.

---

## 4. Diretrizes de Interface e Experiência do Usuário (UI/UX)
- **Design SaaS Dark Mode:** Mantenha uma paleta visual profissional em tons de grafite escuro (`#0f172a`, `#1e293b`), com bordas sutis (`#334155`), azul de ação (`#2563eb`), verde de sucesso (`#10b981`) e tipografia legível (`Inter, system-ui`).
- **Sem Poluição no Topo da Dashboard:** A barra superior deve conter apenas os elementos essenciais de navegação (botão do menu hambúrguer, pílula de status da conta ativa, botão do Copiloto IA e botão de Configurações). Informações extensas e botões duplicados devem ser mantidos dentro da tela de Configurações ou no respectivo módulo.
- **Menu Lateral tipo Gaveta (Drawer):** O menu de navegação de funções deve abrir em formato de gaveta lateral deslizante ao clicar no botão hambúrguer (`☰` / `✕`), fechando-se ao clicar novamente ou ao selecionar uma opção.
- **Sem Duplicações:** Nunca duplique botões, cabeçalhos ou seletores de conta na mesma página.
- **Responsividade Obrigatória:** Todos os componentes novos devem ser adaptáveis para celulares (largura de 375px a 430px), tablets (768px a 1024px) e desktops amplos.

---

## 5. Operações com a Meta Ads API & Travas de Segurança
- **Modo Seguro por Padrão:** Qualquer ação que possa alterar ou gerar cobrança na conta de anúncios da Meta deve, por padrão:
  1. Criar campanhas, conjuntos e anúncios em status **PAUSED** (Pausado) ou como **Rascunho** antes da ativação.
  2. Fornecer feedback visual instantâneo do ID gerado na Meta Graph API.
  3. Permitir ligar/desligar com um clique através dos toggles de status.
- **Resiliência a Falhas de Conexão:** Endpoints devem sempre tratar respostas de erro da Graph API (ex.: token expirado, limite de taxa ou conta desativada) retornando mensagens descritivas para a interface, sem derrubar a API FastAPI.
