<script>
  import { onMount } from 'svelte';

  let {
    onAplicarPublico = (instrucao) => {},
    onExecutarAssistidoNoNavegador = (plano) => {},
    criativosDisponiveis = [],
    pastaCriativos = '',
    validacaoPreflight = null,
  } = $props();

  let abaAtiva = $state('assistida'); // 'assistida' | 'central' | 'robo' | 'publicos'
  let campanhas = $state([]);
  let copilot = $state(null);
  let publicos = $state([]);
  let connection = $state({
    connected: false,
    connection_source: 'disconnected',
    mode: 'mock',
    somente_dados_reais: false,
    user_name: null,
    business_name: 'Não conectado',
    selected_account_id: null,
    selected_account_name: null,
    available_accounts: [],
    has_token: false,
  });

  let mostrarModalConexao = $state(false);
  let tokenInput = $state('');
  let accountIdInput = $state('');
  let accountNameInput = $state('');
  let businessNameInput = $state('');
  let conectandoConta = $state(false);

  let carregando = $state(false);
  let mensagemAcao = $state('');
  let erroAcao = $state('');

  // Estado da Criação de Campanha Assistida (Passo a Passo + Chat)
  let etapaAssistida = $state(1);
  let chatInput = $state('');
  let enviandoChat = $state(false);
  let publicandoReal = $state(false);
  let historicoChat = $state([
    {
      autor: 'ia',
      texto:
        'Olá! Sou seu Assistente de Criação Guiada. Vamos montar sua campanha em 4 etapas (1. Objetivo/Orçamento → 2. Público/Cidades → 3. Criativo/Copy → 4. Publicação Real). Você pode editar os campos ao lado ou me pedir alterações aqui no chat!',
    },
  ]);

  let planoAssistido = $state({
    nome_campanha: 'Campanha CBO - Leads Repasse Financiamento - Curitiba',
    objetivo: 'Leads',
    tipo_orcamento: 'CBO',
    orcamento_diario_brl: 500.0,
    estrategia_lance: 'Volume mais alto',
    categoria_especial_anuncio: 'Crédito',
    conjuntos: [
      {
        nome: 'Conjunto 01 - Campo Largo, Curitiba (Raio 25km)',
        orcamento_diario_brl: null,
        otimizacao_veiculacao: 'Leads',
        evento_conversao: 'Formulario instantaneo ou WhatsApp',
        posicionamentos: ['Advantage+ (Automático)'],
        publico: {
          idade_minima: 23,
          idade_maxima: 58,
          genero: 'todos',
          localizacoes: ['Campo Largo', 'Curitiba'],
          raio_km: 25,
          interesses_sugeridos: ['Financiamento de veículos', 'Carros usados', 'Crédito'],
        },
      },
    ],
    anuncios: [
      {
        nome: 'Anúncio 01 - Repasse de Financiamento Sem Burocracia',
        formato: 'imagem_unica',
        arquivo_criativo: 'criativo_repasse_curitiba.png',
        texto_principal:
          'Procurando repasse de financiamento com parcelas acessíveis na sua região? Confira oportunidades reais revisadas em Campo Largo e Curitiba.',
        titulo: 'Repasse de Financiamento Facilitado',
        descricao: 'Simule agora pelo WhatsApp ou Formulário',
        cta: 'Saiba mais',
      },
    ],
    observacoes_compliance: ['Categoria Especial Crédito verificada.'],
  });

  let validacaoAssistida = $state(null);

  export async function recarregarHub() {
    carregando = true;
    try {
      const [resCon, resCamp, resCop, resPub] = await Promise.all([
        fetch('/api/meta/connection'),
        fetch('/api/meta/campaigns'),
        fetch('/api/meta/copilot'),
        fetch('/api/meta/audiences-store'),
      ]);
      if (resCon.ok) connection = await resCon.json();
      if (resCamp.ok) campanhas = await resCamp.json();
      if (resCop.ok) copilot = await resCop.json();
      if (resPub.ok) {
        const dataPub = await resPub.json();
        publicos = dataPub.publicos || [];
      }
    } catch (_) {
    } finally {
      carregando = false;
    }
  }

  async function conectarTokenGraph() {
    erroAcao = '';
    mensagemAcao = '';
    conectandoConta = true;
    try {
      if (tokenInput.trim()) {
        const res = await fetch('/api/meta/connect-token', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            access_token: tokenInput.trim(),
            account_id: accountIdInput.trim() || null,
          }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Falha ao validar token na Meta Graph API.');
        connection = data;
        mensagemAcao = `Conectado com sucesso à Meta Graph API! Conta ativa: ${data.selected_account_name || data.selected_account_id}`;
        mostrarModalConexao = false;
      } else if (accountIdInput.trim()) {
        const res = await fetch('/api/meta/select-account', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            account_id: accountIdInput.trim(),
            account_name: accountNameInput.trim() || null,
            business_name: businessNameInput.trim() || null,
          }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Erro ao vincular conta.');
        connection = data;
        mensagemAcao = `Conta ${data.selected_account_name} (${data.selected_account_id}) vinculada no modo Somente Dados Reais!`;
        mostrarModalConexao = false;
      } else {
        throw new Error('Informe seu Meta Access Token ou o ID da Conta de Anúncios (ex: act_123456789).');
      }
      await recarregarHub();
    } catch (err) {
      erroAcao = err.message;
    } finally {
      conectandoConta = false;
    }
  }

  async function sincronizarDoNavegadorPlaywright() {
    erroAcao = '';
    mensagemAcao = '';
    conectandoConta = true;
    try {
      const res = await fetch('/api/meta/sync-browser', { method: 'POST' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Erro ao ler navegador.');
      connection = data.connection;
      if (data.navegador?.account_id) {
        mensagemAcao = `Conta real sincronizada do navegador: ${data.navegador.account_name} (${data.navegador.account_id})!`;
      } else {
        mensagemAcao = data.navegador?.mensagem || 'Abra o Gerenciador no navegador e faça login para importar seu act_... automaticamente.';
      }
      await recarregarHub();
    } catch (err) {
      erroAcao = err.message;
    } finally {
      conectandoConta = false;
    }
  }

  async function trocarContaDropdown(e) {
    const novoId = e.target.value;
    if (!novoId) return;
    try {
      const res = await fetch('/api/meta/select-account', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ account_id: novoId }),
      });
      if (res.ok) {
        connection = await res.json();
        mensagemAcao = `Conta alterada para ${connection.selected_account_name} (${connection.selected_account_id}).`;
        await recarregarHub();
      }
    } catch (_) {}
  }

  async function alternarSomenteReais() {
    const novoValor = !connection.somente_dados_reais;
    try {
      const res = await fetch('/api/meta/real-mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ somente_dados_reais: novoValor }),
      });
      if (res.ok) {
        connection = await res.json();
        mensagemAcao = novoValor
          ? 'Modo Somente Dados Reais ativado: campanhas de demonstração foram ocultadas!'
          : 'Modo Demonstração ativado: exibindo campanhas de exemplo.';
        await recarregarHub();
      }
    } catch (_) {}
  }

  async function enviarMensagemAssistente(msgCustom = null) {
    const texto = (msgCustom ?? chatInput).trim();
    if (!texto) return;
    historicoChat = [...historicoChat, { autor: 'user', texto }];
    if (!msgCustom) chatInput = '';
    enviandoChat = true;
    erroAcao = '';
    try {
      const res = await fetch('/api/campanhas/assistida/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mensagem: texto,
          plano_atual: planoAssistido,
          etapa_atual: etapaAssistida,
          pasta_criativos: pastaCriativos || null,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Erro no assistente.');
      planoAssistido = data.plano_campanha;
      etapaAssistida = data.etapa_sugerida || etapaAssistida;
      validacaoAssistida = data.validacao_preflight;
      historicoChat = [...historicoChat, { autor: 'ia', texto: data.resposta_assistente }];
    } catch (err) {
      historicoChat = [...historicoChat, { autor: 'ia', texto: '⚠️ ' + err.message }];
    } finally {
      enviandoChat = false;
    }
  }

  async function publicarAssistidoViaGraphApi() {
    publicandoReal = true;
    erroAcao = '';
    mensagemAcao = '';
    try {
      const res = await fetch('/api/campanhas/assistida/publicar-graph', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          plano_campanha: planoAssistido,
          pasta_criativos: pastaCriativos || null,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Falha ao publicar na Meta Graph API.');
      mensagemAcao = data.mensagem;
      historicoChat = [...historicoChat, { autor: 'ia', texto: '🎉 ' + data.mensagem }];
      await recarregarHub();
    } catch (err) {
      erroAcao = err.message;
      historicoChat = [...historicoChat, { autor: 'ia', texto: '⚠️ ' + err.message }];
    } finally {
      publicandoReal = false;
    }
  }

  async function dispararAssistidoNoNavegador() {
    mensagemAcao = 'Iniciando criação assistida passo a passo no Gerenciador de Anúncios...';
    historicoChat = [
      ...historicoChat,
      {
        autor: 'ia',
        texto: `🖱️ Iniciando preenchimento assistido de "${planoAssistido.nome_campanha}" no Gerenciador de Anúncios (R$ ${planoAssistido.orcamento_diario_brl}/dia · ${planoAssistido.tipo_orcamento})!`,
      },
    ];
    onExecutarAssistidoNoNavegador(planoAssistido);
    await recarregarHub();
  }

  async function alternarStatus(camp) {
    const novoStatus = camp.status === 'ACTIVE' ? 'PAUSED' : 'ACTIVE';
    try {
      const res = await fetch(`/api/meta/campaigns/${camp.id}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: novoStatus }),
      });
      if (res.ok) {
        mensagemAcao = `Campanha "${camp.name}" alterada para ${novoStatus === 'ACTIVE' ? 'ATIVA' : 'PAUSADA'}!`;
        await recarregarHub();
      }
    } catch (_) {}
  }

  async function ajustarOrcamento(camp, fator) {
    const novoValor = Math.max(10, Math.round(camp.daily_budget * fator));
    try {
      const res = await fetch(`/api/meta/campaigns/${camp.id}/budget`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ daily_budget: novoValor }),
      });
      if (res.ok) {
        mensagemAcao = `Orçamento de "${camp.name}" ajustado para R$ ${novoValor.toFixed(2)}/dia!`;
        await recarregarHub();
      }
    } catch (_) {}
  }

  function escolherPublico(pub) {
    onAplicarPublico(pub.instrucao_pronta);
    enviarMensagemAssistente(pub.instrucao_pronta);
    abaAtiva = 'assistida';
    mensagemAcao = `Público "${pub.titulo}" carregado na Criação Assistida!`;
  }

  onMount(recarregarHub);
</script>

<section class="adsimples-card">
  <!-- 1. BARRA DE IDENTIFICAÇÃO DA CONTA DE ANÚNCIOS REAL & GERENCIADOR (BM) -->
  <div class="connection-banner" class:connected={connection.connected}>
    <div class="conn-left">
      <span class="conn-dot" class:on={connection.connected}></span>
      <div>
        <div class="conn-title">
          {#if connection.connected}
            🟢 CONECTADO AO GERENCIADOR REAL: <strong>{connection.business_name}</strong>
          {:else}
            🔴 GERENCIADOR DESCONECTADO — Nenhuma Conta de Anúncios Real vinculada ainda
          {/if}
        </div>
        <div class="conn-sub">
          {#if connection.selected_account_id}
            💳 Conta de Anúncios Ativa: <strong>{connection.selected_account_name || 'Conta Meta'}</strong>
            <code class="act-code">{connection.selected_account_id}</code>
            · Fonte: <strong>{connection.connection_source === 'graph' ? 'Meta Graph API Oficial' : 'Sessão do Navegador'}</strong>
          {:else}
            Conecte seu Token da Meta API ou sincronize a janela do navegador para carregar seu <code>act_...</code> e suas campanhas reais.
          {/if}
        </div>
      </div>
    </div>

    <div class="conn-actions">
      {#if connection.available_accounts?.length > 0}
        <select class="acc-select" value={connection.selected_account_id} onchange={trocarContaDropdown}>
          {#each connection.available_accounts as acc}
            <option value={acc.id}>{acc.name} ({acc.id}) — {acc.business_name}</option>
          {/each}
        </select>
      {/if}

      <button
        type="button"
        class="btn-conn primary"
        onclick={() => (mostrarModalConexao = !mostrarModalConexao)}
      >
        🔗 {connection.connected ? 'Trocar Conta / Token' : 'Conectar Minha Conta Meta Ads Real'}
      </button>

      <button
        type="button"
        class="btn-conn"
        onclick={sincronizarDoNavegadorPlaywright}
        disabled={conectandoConta}
      >
        🌐 Sincronizar do Navegador
      </button>

      <button
        type="button"
        class="btn-conn"
        class:active-real={connection.somente_dados_reais}
        onclick={alternarSomenteReais}
        title="Oculta os dados simulados e exibe apenas campanhas reais da sua conta"
      >
        {connection.somente_dados_reais ? '🔒 Somente Dados Reais (Ativo)' : '🧪 Exibindo Demo (Clique p/ Só Reais)'}
      </button>
    </div>
  </div>

  <!-- MODAL / DRAWER DE CONEXÃO REAL COM A CONTA DE ANÚNCIOS -->
  {#if mostrarModalConexao}
    <div class="conn-drawer">
      <div class="conn-drawer-head">
        <h3>🔐 Conectar Gerenciador de Negócios (BM) e Conta de Anúncios Real (Meta Marketing API)</h3>
        <button type="button" class="close-x" onclick={() => (mostrarModalConexao = false)}>✕</button>
      </div>
      <p class="conn-help">
        Você pode conectar colando seu <strong>Meta Access Token</strong> (que puxa automaticamente todas as suas Contas <code>act_...</code> e Campanhas Reais via <code>graph.facebook.com</code>) ou informando o <strong>ID da sua Conta de Anúncios</strong> para uso com o navegador Playwright.
      </p>
      <div class="conn-form-grid">
        <div>
          <label for="meta-token-inp">Meta Access Token (ads_read, ads_management)</label>
          <input
            id="meta-token-inp"
            type="password"
            placeholder="EAABwzLixnjYBO..."
            bind:value={tokenInput}
          />
          <small>
            Gere em 1 clique no
            <a href="https://developers.facebook.com/tools/explorer/" target="_blank" rel="noopener noreferrer">
              Graph API Explorer da Meta
            </a>
            ou em Usuários do Sistema no BM.
          </small>
        </div>
        <div>
          <label for="meta-act-inp">ID da Conta de Anúncios (ex: act_1049283741)</label>
          <input
            id="meta-act-inp"
            type="text"
            placeholder="act_1234567890"
            bind:value={accountIdInput}
          />
        </div>
        <div>
          <label for="meta-acc-name">Nome da Conta / Gerenciador (Opcional)</label>
          <input
            id="meta-acc-name"
            type="text"
            placeholder="Ex: Conta Principal - Repasse Curitiba"
            bind:value={accountNameInput}
          />
        </div>
      </div>
      <div class="conn-drawer-foot">
        <button type="button" class="btn-conn primary" onclick={conectarTokenGraph} disabled={conectandoConta}>
          {conectandoConta ? 'Conectando...' : '✅ Salvar e Conectar Conta Real'}
        </button>
      </div>
    </div>
  {/if}

  <div class="adsimples-header">
    <div>
      <div class="adsimples-badge-row">
        <span class="badge-hackr">⚡ CENTRAL ADSIMPLES / HACKR ADS</span>
        <span class="badge-repo">Criação Assistida · Meta Graph API · Robô Otimizador</span>
      </div>
      <h2>Criação de Campanha Assistida & Gestão Unificada</h2>
    </div>
    <div class="tabs-bar">
      <button
        type="button"
        class="tab-btn"
        class:active={abaAtiva === 'assistida'}
        onclick={() => (abaAtiva = 'assistida')}
      >
        🪄 Criação de Campanha Assistida (Passo a Passo)
      </button>
      <button
        type="button"
        class="tab-btn"
        class:active={abaAtiva === 'central'}
        onclick={() => (abaAtiva = 'central')}
      >
        📊 Campanhas da Conta ({campanhas.length})
      </button>
      <button
        type="button"
        class="tab-btn"
        class:active={abaAtiva === 'robo'}
        onclick={() => (abaAtiva = 'robo')}
      >
        🤖 Robô Otimizador
      </button>
      <button
        type="button"
        class="tab-btn"
        class:active={abaAtiva === 'publicos'}
        onclick={() => (abaAtiva = 'publicos')}
      >
        🎯 Loja de Públicos ({publicos.length})
      </button>
    </div>
  </div>

  {#if mensagemAcao}
    <div class="toast-msg">
      <span>✅ {mensagemAcao}</span>
      <button type="button" onclick={() => (mensagemAcao = '')}>✕</button>
    </div>
  {/if}

  {#if erroAcao}
    <div class="toast-msg error">
      <span>⚠️ {erroAcao}</span>
      <button type="button" onclick={() => (erroAcao = '')}>✕</button>
    </div>
  {/if}

  <!-- ABA 1: CRIAÇÃO DE CAMPANHA ASSISTIDA (WIZARD 4 ETAPAS + CHAT ASSISTIDO) -->
  {#if abaAtiva === 'assistida'}
    <div class="assisted-layout">
      <!-- Coluna Esquerda do Assistente: Etapas Visuais Editáveis -->
      <div class="wizard-panel">
        <div class="stepper">
          <button type="button" class="step-pill" class:active={etapaAssistida === 1} onclick={() => (etapaAssistida = 1)}>
            1. Conta & Objetivo
          </button>
          <button type="button" class="step-pill" class:active={etapaAssistida === 2} onclick={() => (etapaAssistida = 2)}>
            2. Público & Cidades
          </button>
          <button type="button" class="step-pill" class:active={etapaAssistida === 3} onclick={() => (etapaAssistida = 3)}>
            3. Criativo & Copy
          </button>
          <button type="button" class="step-pill" class:active={etapaAssistida === 4} onclick={() => (etapaAssistida = 4)}>
            4. Revisão & Criar Real
          </button>
        </div>

        {#if etapaAssistida === 1}
          <div class="step-box">
            <h3>Etapa 1/4 — Conta de Destino, Objetivo e Orçamento</h3>
            <div class="wiz-grid">
              <div class="wiz-field">
                <label for="w-camp-name">Nome da Campanha</label>
                <input id="w-camp-name" type="text" bind:value={planoAssistido.nome_campanha} />
              </div>
              <div class="wiz-field">
                <label for="w-obj">Objetivo no Meta Ads</label>
                <select id="w-obj" bind:value={planoAssistido.objetivo}>
                  <option value="Leads">Cadastros / Leads (Formulário ou WhatsApp)</option>
                  <option value="Vendas">Vendas / Conversões</option>
                  <option value="Trafego">Tráfego (Cliques no Link)</option>
                  <option value="Engajamento">Engajamento / Mensagens Direct</option>
                </select>
              </div>
              <div class="wiz-field">
                <label for="w-btype">Tipo de Orçamento</label>
                <select id="w-btype" bind:value={planoAssistido.tipo_orcamento}>
                  <option value="CBO">CBO — Orçamento Advantage+ na Campanha</option>
                  <option value="ABO">ABO — Orçamento no Conjunto de Anúncios</option>
                </select>
              </div>
              <div class="wiz-field">
                <label for="w-budget">Orçamento Diário (R$)</label>
                <input id="w-budget" type="number" min="6" step="10" bind:value={planoAssistido.orcamento_diario_brl} />
              </div>
              <div class="wiz-field full">
                <label for="w-cat">Categoria de Anúncio Especial (Compliance Meta)</label>
                <input id="w-cat" type="text" bind:value={planoAssistido.categoria_especial_anuncio} />
              </div>
            </div>
            <div class="step-nav">
              <span>Conta selecionada: <strong>{connection.selected_account_id || 'Modo Guiado / Navegador'}</strong></span>
              <button type="button" class="btn-wiz-next" onclick={() => (etapaAssistida = 2)}>
                Confirmar Etapa 1 e Avançar para Público →
              </button>
            </div>
          </div>
        {:else if etapaAssistida === 2}
          <div class="step-box">
            <h3>Etapa 2/4 — Conjunto de Anúncios e Segmentação Regional</h3>
            {#if planoAssistido.conjuntos?.[0]}
              <div class="wiz-grid">
                <div class="wiz-field full">
                  <label for="w-adset-name">Nome do Conjunto de Anúncios</label>
                  <input id="w-adset-name" type="text" bind:value={planoAssistido.conjuntos[0].nome} />
                </div>
                <div class="wiz-field">
                  <label for="w-locs">Cidades / Regiões (separadas por vírgula)</label>
                  <input
                    id="w-locs"
                    type="text"
                    value={planoAssistido.conjuntos[0].publico.localizacoes.join(', ')}
                    oninput={(e) => {
                      planoAssistido.conjuntos[0].publico.localizacoes = e.target.value
                        .split(',')
                        .map((s) => s.trim())
                        .filter(Boolean);
                    }}
                  />
                </div>
                <div class="wiz-field">
                  <label for="w-raio">Raio Geográfico (km)</label>
                  <input id="w-raio" type="number" min="5" max="80" bind:value={planoAssistido.conjuntos[0].publico.raio_km} />
                </div>
                <div class="wiz-field">
                  <label for="w-age-min">Idade Mínima</label>
                  <input id="w-age-min" type="number" min="18" max="65" bind:value={planoAssistido.conjuntos[0].publico.idade_minima} />
                </div>
                <div class="wiz-field">
                  <label for="w-age-max">Idade Máxima</label>
                  <input id="w-age-max" type="number" min="18" max="65" bind:value={planoAssistido.conjuntos[0].publico.idade_maxima} />
                </div>
                <div class="wiz-field full">
                  <label for="w-int">Interesses Direcionados</label>
                  <input
                    id="w-int"
                    type="text"
                    value={planoAssistido.conjuntos[0].publico.interesses_sugeridos.join(', ')}
                    oninput={(e) => {
                      planoAssistido.conjuntos[0].publico.interesses_sugeridos = e.target.value
                        .split(',')
                        .map((s) => s.trim())
                        .filter(Boolean);
                    }}
                  />
                </div>
              </div>
            {/if}
            <div class="step-nav">
              <button type="button" class="btn-wiz-back" onclick={() => (etapaAssistida = 1)}>← Voltar</button>
              <button type="button" class="btn-wiz-next" onclick={() => (etapaAssistida = 3)}>
                Confirmar Público e Avançar para Criativo & Copy →
              </button>
            </div>
          </div>
        {:else if etapaAssistida === 3}
          <div class="step-box">
            <h3>Etapa 3/4 — Criativo da Pasta Local & Copywriter</h3>
            {#if planoAssistido.anuncios?.[0]}
              <div class="wiz-grid">
                <div class="wiz-field">
                  <label for="w-ad-name">Nome do Anúncio</label>
                  <input id="w-ad-name" type="text" bind:value={planoAssistido.anuncios[0].nome} />
                </div>
                <div class="wiz-field">
                  <label for="w-media">Arquivo da Pasta de Criativos</label>
                  <select id="w-media" bind:value={planoAssistido.anuncios[0].arquivo_criativo}>
                    {#if criativosDisponiveis.length === 0}
                      <option value="criativo_repasse_curitiba.png">criativo_repasse_curitiba.png</option>
                    {:else}
                      {#each criativosDisponiveis as arq}
                        <option value={arq.nome}>{arq.nome} ({arq.tamanho_kb} KB)</option>
                      {/each}
                    {/if}
                  </select>
                </div>
                <div class="wiz-field full">
                  <label for="w-copy">Texto Principal (Copywriter)</label>
                  <textarea id="w-copy" rows="3" bind:value={planoAssistido.anuncios[0].texto_principal}></textarea>
                </div>
                <div class="wiz-field">
                  <label for="w-head">Título (Headline)</label>
                  <input id="w-head" type="text" bind:value={planoAssistido.anuncios[0].titulo} />
                </div>
                <div class="wiz-field">
                  <label for="w-cta">Botão de Chamada para Ação (CTA)</label>
                  <select id="w-cta" bind:value={planoAssistido.anuncios[0].cta}>
                    <option value="Saiba mais">Saiba mais</option>
                    <option value="Enviar mensagem">Enviar mensagem (WhatsApp)</option>
                    <option value="Cadastre-se">Cadastre-se</option>
                    <option value="Solicitar agora">Solicitar agora</option>
                  </select>
                </div>
              </div>
            {/if}
            <div class="step-nav">
              <button type="button" class="btn-wiz-back" onclick={() => (etapaAssistida = 2)}>← Voltar</button>
              <button type="button" class="btn-wiz-next" onclick={() => (etapaAssistida = 4)}>
                Avançar para Revisão e Criação Real →
              </button>
            </div>
          </div>
        {:else if etapaAssistida === 4}
          <div class="step-box">
            <h3>Etapa 4/4 — Revisão Final & Disparo Assistido</h3>
            <div class="review-summary">
              <div><strong>Campanha:</strong> {planoAssistido.nome_campanha}</div>
              <div><strong>Objetivo / Verba:</strong> {planoAssistido.objetivo} · {planoAssistido.tipo_orcamento} · R$ {Number(planoAssistido.orcamento_diario_brl).toFixed(2)}/dia</div>
              <div><strong>Público Regional:</strong> {planoAssistido.conjuntos?.[0]?.publico?.localizacoes?.join(', ')} (Raio {planoAssistido.conjuntos?.[0]?.publico?.raio_km}km · {planoAssistido.conjuntos?.[0]?.publico?.idade_minima}–{planoAssistido.conjuntos?.[0]?.publico?.idade_maxima} anos)</div>
              <div><strong>Criativo & Copy:</strong> 🖼️ {planoAssistido.anuncios?.[0]?.arquivo_criativo} · "{planoAssistido.anuncios?.[0]?.titulo}" ({planoAssistido.anuncios?.[0]?.cta})</div>
              <div><strong>Conta de Destino:</strong> {connection.selected_account_id ? `${connection.selected_account_name} (${connection.selected_account_id})` : 'Gerenciador no Navegador (Playwright)'}</div>
            </div>

            <div class="publish-actions">
              <button
                type="button"
                class="btn-launch-browser"
                onclick={dispararAssistidoNoNavegador}
              >
                🖱️ Criar de Forma Assistida no Navegador (Ver Mouse Preenchendo Passo a Passo)
              </button>

              <button
                type="button"
                class="btn-launch-graph"
                onclick={publicarAssistidoViaGraphApi}
                disabled={publicandoReal}
              >
                {publicandoReal ? 'Publicando na Meta API...' : '🚀 Criar Direto na Minha Conta Real via Meta Graph API (PAUSED)'}
              </button>
            </div>

            <div class="step-nav" style="margin-top: 12px;">
              <button type="button" class="btn-wiz-back" onclick={() => (etapaAssistida = 3)}>← Voltar e Editar</button>
            </div>
          </div>
        {/if}
      </div>

      <!-- Coluna Direita do Assistente: Chat Interativo de Criação Assistida -->
      <div class="chat-panel">
        <div class="chat-head">
          <strong>💬 Chat da Criação Assistida</strong>
          <span>Peça alterações em linguagem natural</span>
        </div>
        <div class="chat-messages">
          {#each historicoChat as msg}
            <div class="chat-bubble {msg.autor}">
              <small>{msg.autor === 'ia' ? '🤖 Assistente Meta Ads' : '👤 Você'}</small>
              <p>{msg.texto}</p>
            </div>
          {/each}
        </div>
        <div class="quick-chips">
          <button type="button" onclick={() => enviarMensagemAssistente('Muda o orçamento para R$ 300 por dia')}>
            💰 R$ 300/dia
          </button>
          <button type="button" onclick={() => enviarMensagemAssistente('Cidades: Curitiba, Campo Largo, São José dos Pinhais')}>
            📍 + São José dos Pinhais
          </button>
          <button type="button" onclick={() => enviarMensagemAssistente('Idade 25 a 52 anos e raio 30km')}>
            🎂 25–52 anos (30km)
          </button>
        </div>
        <form
          class="chat-input-row"
          onsubmit={(e) => {
            e.preventDefault();
            enviarMensagemAssistente();
          }}
        >
          <input
            type="text"
            placeholder="Ex: Muda para R$ 350/dia em Curitiba e foca no WhatsApp..."
            bind:value={chatInput}
          />
          <button type="submit" disabled={enviandoChat}>
            {enviandoChat ? '...' : 'Enviar'}
          </button>
        </form>
      </div>
    </div>
  {:else if abaAtiva === 'central'}
    {#if campanhas.length === 0}
      <div class="empty-real-box">
        <h3>🔒 Modo Somente Dados Reais Ativo — Nenhuma campanha carregada ainda</h3>
        <p>
          Você ocultou os dados simulados de demonstração. Para ver ou criar campanhas reais aqui:
          <strong>1)</strong> Conecte seu Token da Meta API no botão <em>"Conectar Minha Conta Meta Ads Real"</em> acima,
          <strong>2)</strong> Clique em <em>"Sincronizar do Navegador"</em> após fazer login no Facebook, ou
          <strong>3)</strong> Use a aba <em>"🪄 Criação de Campanha Assistida"</em> para criar sua primeira campanha!
        </p>
      </div>
    {:else}
      <div class="table-wrap">
        <table class="camp-table">
          <thead>
            <tr>
              <th>On/Off</th>
              <th>Campanha / Origem dos Dados</th>
              <th>Orçamento</th>
              <th>Métricas (7d)</th>
              <th>Diagnóstico IA (Robô)</th>
              <th>Ações Rápidas (1-Clique)</th>
            </tr>
          </thead>
          <tbody>
            {#each campanhas as camp}
              <tr>
                <td>
                  <button
                    type="button"
                    class="switch-btn"
                    class:on={camp.status === 'ACTIVE'}
                    onclick={() => alternarStatus(camp)}
                    title="Clique para Ativar ou Pausar"
                  >
                    <span class="knob"></span>
                  </button>
                </td>
                <td>
                  <div class="camp-name">{camp.name}</div>
                  <div class="camp-meta">
                    <span class="origin-pill" class:real={camp.is_real}>
                      {camp.origem_dados || (camp.is_real ? '🟢 CONTA REAL' : '🧪 DEMO LOCAL')}
                    </span>
                    · {camp.objective} · 📍 {(camp.locations || []).join(', ')}
                  </div>
                </td>
                <td>
                  <div class="budget-val">R$ {camp.daily_budget.toFixed(2)}/dia</div>
                  <span class="budget-tag">{camp.budget_type}</span>
                </td>
                <td>
                  <div class="metrics-line">
                    <span>CTR: <strong>{camp.totals.ctr}%</strong></span>
                    <span>CPA: <strong>R$ {camp.totals.cpa}</strong></span>
                    <span>ROAS: <strong>{camp.totals.roas}x</strong></span>
                  </div>
                  <div class="camp-meta">
                    Gasto 7d: R$ {camp.totals.spend.toFixed(2)} · {camp.totals.conversions} conv.
                  </div>
                </td>
                <td>
                  <span class="health-badge {camp.health_color}">{camp.health_tag}</span>
                  <div class="rec-text">{camp.recomendacao_ia}</div>
                </td>
                <td>
                  <div class="action-btns">
                    <button
                      type="button"
                      class="act-btn scale"
                      onclick={() => ajustarOrcamento(camp, 1.2)}
                    >
                      📈 +20% Verba
                    </button>
                    <button
                      type="button"
                      class="act-btn cut"
                      onclick={() => ajustarOrcamento(camp, 0.8)}
                    >
                      📉 -20%
                    </button>
                    <button
                      type="button"
                      class="act-btn toggle"
                      onclick={() => alternarStatus(camp)}
                    >
                      {camp.status === 'ACTIVE' ? '⏸️ Pausar' : '▶️ Ativar'}
                    </button>
                  </div>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  {:else if abaAtiva === 'robo'}
    <div class="robo-grid">
      <div class="robo-col winner-col">
        <h3>🏆 Campanhas Vencedoras (Winners — Escalar)</h3>
        {#if !copilot || copilot.winners.length === 0}
          <p class="empty-note">Nenhuma campanha acima do limiar de Winner no momento.</p>
        {:else}
          {#each copilot.winners as w}
            <div class="robo-item">
              <div>
                <strong>{w.name}</strong>
                <p>ROAS {w.totals.roas}x · CTR {w.totals.ctr}% · CPA R$ {w.totals.cpa}</p>
              </div>
              <button type="button" class="act-btn scale" onclick={() => ajustarOrcamento(w, 1.2)}>
                ⚡ Escalar +20% (R$ {(w.daily_budget * 1.2).toFixed(0)}/dia)
              </button>
            </div>
          {/each}
        {/if}
      </div>

      <div class="robo-col bleeder-col">
        <h3>🩸 Campanhas Sangrando Orçamento (Bleeders & Fadiga)</h3>
        {#if !copilot || (copilot.bleeders.length === 0 && copilot.fatigue_alerts.length === 0)}
          <p class="empty-note">Nenhum sangrador ou fadiga crítica detectada!</p>
        {:else}
          {#each copilot.bleeders as b}
            <div class="robo-item danger">
              <div>
                <strong>{b.name}</strong>
                <p>CTR {b.totals.ctr}% · Gasto 7d: R$ {b.totals.spend.toFixed(2)} · Frequência {b.totals.frequency}</p>
              </div>
              <button type="button" class="act-btn cut" onclick={() => alternarStatus(b)}>
                ⏸️ Pausar Sangrador Agora
              </button>
            </div>
          {/each}
          {#each copilot.fatigue_alerts as f}
            <div class="robo-item warn">
              <div>
                <strong>😴 Fadiga Detectada: {f.campaign_name}</strong>
                <p>Queda de CTR de {f.drop_pct}% ({f.start_ctr}% → {f.end_ctr}%). {f.acao_sugerida}</p>
              </div>
            </div>
          {/each}
        {/if}
      </div>
    </div>
  {:else if abaAtiva === 'publicos'}
    <div class="publicos-grid">
      {#each publicos as pub}
        <div class="pub-card">
          <div class="pub-top">
            <span class="pub-cat">{pub.categoria}</span>
            <span class="pub-budget">{pub.tipo_orcamento} · R$ {pub.orcamento_sugerido_brl}/dia</span>
          </div>
          <h3>{pub.titulo}</h3>
          <p>{pub.descricao}</p>
          <div class="pub-tags">
            <span>📍 {pub.cidades_sugeridas.join(', ')} (+{pub.raio_km}km)</span>
            <span>🎂 {pub.idade_minima}–{pub.idade_maxima} anos</span>
          </div>
          <div class="pub-interests">
            Interesses: {pub.interesses.join(' · ')}
          </div>
          <button type="button" class="btn-apply-pub" onclick={() => escolherPublico(pub)}>
            ⚡ Usar Este Público na Criação Assistida
          </button>
        </div>
      {/each}
    </div>
  {/if}
</section>

<style>
  .adsimples-card {
    background: linear-gradient(180deg, #111927 0%, #0d1420 100%);
    border: 1px solid #1e2d45;
    border-radius: 16px;
    padding: 18px 20px;
    margin-bottom: 24px;
    box-shadow: 0 14px 34px rgba(0, 0, 0, 0.35);
  }

  .connection-banner {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 14px;
    flex-wrap: wrap;
    background: rgba(239, 68, 68, 0.09);
    border: 1px solid rgba(239, 68, 68, 0.35);
    border-radius: 12px;
    padding: 12px 16px;
    margin-bottom: 16px;
  }

  .connection-banner.connected {
    background: rgba(16, 185, 129, 0.1);
    border-color: rgba(16, 185, 129, 0.4);
  }

  .conn-left {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .conn-dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: #ef4444;
    box-shadow: 0 0 10px #ef4444;
    flex-shrink: 0;
  }

  .conn-dot.on {
    background: #10b981;
    box-shadow: 0 0 10px #10b981;
  }

  .conn-title {
    font-size: 0.86rem;
    color: #f8fafc;
  }

  .conn-sub {
    font-size: 0.77rem;
    color: #94a3b8;
    margin-top: 2px;
  }

  .act-code {
    background: #0f172a;
    color: #38bdf8;
    padding: 1px 6px;
    border-radius: 4px;
    font-weight: 700;
  }

  .conn-actions {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    align-items: center;
  }

  .acc-select {
    background: #0f172a;
    color: #f8fafc;
    border: 1px solid #38bdf8;
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 0.78rem;
    font-weight: 700;
  }

  .btn-conn {
    background: #1e293b;
    color: #e2e8f0;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 7px 11px;
    font-size: 0.76rem;
    font-weight: 700;
    cursor: pointer;
  }

  .btn-conn.primary {
    background: #1877f2;
    color: #fff;
    border-color: #38bdf8;
  }

  .btn-conn.active-real {
    background: rgba(16, 185, 129, 0.2);
    color: #34d399;
    border-color: #10b981;
  }

  .conn-drawer {
    background: #090e17;
    border: 1px solid #0284c7;
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 16px;
  }

  .conn-drawer-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 6px;
  }

  .conn-drawer-head h3 {
    margin: 0;
    font-size: 0.95rem;
    color: #38bdf8;
  }

  .close-x {
    background: transparent;
    border: none;
    color: #94a3b8;
    font-size: 1rem;
    cursor: pointer;
  }

  .conn-help {
    font-size: 0.8rem;
    color: #94a3b8;
    margin: 0 0 12px;
  }

  .conn-form-grid {
    display: grid;
    grid-template-columns: 1.4fr 1fr 1fr;
    gap: 12px;
    margin-bottom: 12px;
  }

  @media (max-width: 900px) {
    .conn-form-grid {
      grid-template-columns: 1fr;
    }
  }

  .conn-form-grid label {
    display: block;
    font-size: 0.75rem;
    font-weight: 700;
    color: #cbd5e1;
    margin-bottom: 4px;
  }

  .conn-form-grid input {
    width: 100%;
    box-sizing: border-box;
    background: #111927;
    border: 1px solid #2b3b55;
    color: #f8fafc;
    border-radius: 7px;
    padding: 8px 10px;
    font-size: 0.82rem;
  }

  .conn-form-grid small {
    display: block;
    margin-top: 4px;
    font-size: 0.72rem;
    color: #64748b;
  }

  .conn-form-grid small a {
    color: #38bdf8;
  }

  .adsimples-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 16px;
    flex-wrap: wrap;
    margin-bottom: 14px;
  }

  .adsimples-badge-row {
    display: flex;
    gap: 8px;
    align-items: center;
    flex-wrap: wrap;
    margin-bottom: 4px;
  }

  .badge-hackr {
    background: rgba(16, 185, 129, 0.16);
    color: #34d399;
    border: 1px solid rgba(16, 185, 129, 0.35);
    font-size: 11px;
    font-weight: 800;
    padding: 3px 9px;
    border-radius: 999px;
  }

  .badge-repo {
    background: rgba(56, 189, 248, 0.12);
    color: #38bdf8;
    border: 1px solid rgba(56, 189, 248, 0.3);
    font-size: 11px;
    font-weight: 700;
    padding: 3px 9px;
    border-radius: 999px;
  }

  .adsimples-header h2 {
    margin: 0;
    font-size: 1.15rem;
    color: #f8fafc;
  }

  .tabs-bar {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }

  .tab-btn {
    background: #172235;
    color: #cbd5e1;
    border: 1px solid #283854;
    border-radius: 9px;
    padding: 8px 13px;
    font-size: 0.8rem;
    font-weight: 700;
    cursor: pointer;
  }

  .tab-btn.active {
    background: #0284c7;
    color: #ffffff;
    border-color: #38bdf8;
  }

  .toast-msg {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: rgba(22, 163, 74, 0.18);
    border: 1px solid rgba(34, 197, 94, 0.45);
    color: #bbf7d0;
    padding: 8px 14px;
    border-radius: 9px;
    font-size: 0.82rem;
    font-weight: 600;
    margin-bottom: 12px;
  }

  .toast-msg.error {
    background: rgba(239, 68, 68, 0.18);
    border-color: rgba(239, 68, 68, 0.45);
    color: #fecaca;
  }

  .toast-msg button {
    background: transparent;
    border: none;
    color: inherit;
    cursor: pointer;
    font-weight: 800;
  }

  /* CRIAÇÃO ASSISTIDA */
  .assisted-layout {
    display: grid;
    grid-template-columns: 1.35fr 1fr;
    gap: 16px;
  }

  @media (max-width: 960px) {
    .assisted-layout {
      grid-template-columns: 1fr;
    }
  }

  .wizard-panel {
    background: #0b111c;
    border: 1px solid #1e2b40;
    border-radius: 12px;
    padding: 14px 16px;
  }

  .stepper {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 6px;
    margin-bottom: 14px;
  }

  .step-pill {
    background: #131d2e;
    color: #94a3b8;
    border: 1px solid #24344d;
    border-radius: 8px;
    padding: 7px 8px;
    font-size: 0.75rem;
    font-weight: 700;
    cursor: pointer;
  }

  .step-pill.active {
    background: rgba(2, 132, 199, 0.25);
    color: #38bdf8;
    border-color: #38bdf8;
  }

  .step-box h3 {
    margin: 0 0 12px;
    font-size: 0.95rem;
    color: #f8fafc;
  }

  .wiz-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
  }

  .wiz-field.full {
    grid-column: 1 / -1;
  }

  .wiz-field label {
    display: block;
    font-size: 0.74rem;
    font-weight: 700;
    color: #94a3b8;
    margin-bottom: 4px;
  }

  .wiz-field input,
  .wiz-field select,
  .wiz-field textarea {
    width: 100%;
    box-sizing: border-box;
    background: #131d2e;
    border: 1px solid #2b3c57;
    color: #f8fafc;
    border-radius: 7px;
    padding: 8px 10px;
    font-size: 0.82rem;
  }

  .step-nav {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 14px;
    font-size: 0.78rem;
    color: #94a3b8;
  }

  .btn-wiz-next {
    background: #0284c7;
    color: #fff;
    border: none;
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 0.8rem;
    font-weight: 700;
    cursor: pointer;
  }

  .btn-wiz-back {
    background: #1e293b;
    color: #cbd5e1;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 7px 12px;
    font-size: 0.78rem;
    font-weight: 700;
    cursor: pointer;
  }

  .review-summary {
    background: #111a2b;
    border: 1px solid #263854;
    border-radius: 10px;
    padding: 12px 14px;
    font-size: 0.82rem;
    color: #cbd5e1;
    line-height: 1.65;
    margin-bottom: 14px;
  }

  .publish-actions {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .btn-launch-browser {
    background: #1877f2;
    color: #fff;
    border: none;
    border-radius: 9px;
    padding: 11px 16px;
    font-size: 0.86rem;
    font-weight: 800;
    cursor: pointer;
  }

  .btn-launch-graph {
    background: #16a34a;
    color: #fff;
    border: none;
    border-radius: 9px;
    padding: 11px 16px;
    font-size: 0.86rem;
    font-weight: 800;
    cursor: pointer;
  }

  .chat-panel {
    background: #0b111c;
    border: 1px solid #1e2b40;
    border-radius: 12px;
    padding: 12px 14px;
    display: flex;
    flex-direction: column;
    max-height: 390px;
  }

  .chat-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #1e2b40;
    padding-bottom: 8px;
    margin-bottom: 8px;
    font-size: 0.82rem;
  }

  .chat-head strong {
    color: #38bdf8;
  }

  .chat-head span {
    font-size: 0.72rem;
    color: #64748b;
  }

  .chat-messages {
    flex: 1;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding-right: 4px;
    margin-bottom: 8px;
  }

  .chat-bubble {
    padding: 8px 10px;
    border-radius: 9px;
    font-size: 0.79rem;
    line-height: 1.4;
  }

  .chat-bubble.ia {
    background: #131f33;
    border: 1px solid #233858;
    color: #e2e8f0;
  }

  .chat-bubble.user {
    background: rgba(2, 132, 199, 0.22);
    border: 1px solid rgba(56, 189, 248, 0.4);
    color: #f8fafc;
    align-self: flex-end;
  }

  .chat-bubble small {
    display: block;
    font-size: 0.68rem;
    color: #38bdf8;
    font-weight: 700;
    margin-bottom: 2px;
  }

  .chat-bubble p {
    margin: 0;
    white-space: pre-line;
  }

  .quick-chips {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    margin-bottom: 8px;
  }

  .quick-chips button {
    background: #162236;
    color: #93c5fd;
    border: 1px solid #283c5c;
    border-radius: 999px;
    padding: 4px 9px;
    font-size: 0.71rem;
    font-weight: 600;
    cursor: pointer;
  }

  .chat-input-row {
    display: flex;
    gap: 6px;
  }

  .chat-input-row input {
    flex: 1;
    background: #131d2e;
    border: 1px solid #2b3c57;
    color: #f8fafc;
    border-radius: 8px;
    padding: 8px 10px;
    font-size: 0.8rem;
  }

  .chat-input-row button {
    background: #0284c7;
    color: #fff;
    border: none;
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 0.8rem;
    font-weight: 700;
    cursor: pointer;
  }

  .empty-real-box {
    background: #0b111c;
    border: 1px dashed #38bdf8;
    border-radius: 12px;
    padding: 20px;
    text-align: center;
  }

  .empty-real-box h3 {
    margin: 0 0 8px;
    color: #38bdf8;
    font-size: 0.98rem;
  }

  .empty-real-box p {
    margin: 0 auto;
    max-width: 720px;
    font-size: 0.83rem;
    color: #94a3b8;
    line-height: 1.5;
  }

  .origin-pill {
    display: inline-block;
    padding: 1px 6px;
    border-radius: 4px;
    font-size: 0.68rem;
    font-weight: 800;
    background: rgba(245, 158, 11, 0.16);
    color: #fcd34d;
  }

  .origin-pill.real {
    background: rgba(16, 185, 129, 0.2);
    color: #34d399;
  }

  .table-wrap {
    overflow-x: auto;
  }

  .camp-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.83rem;
  }

  .camp-table th {
    text-align: left;
    padding: 10px 12px;
    color: #94a3b8;
    font-size: 0.74rem;
    text-transform: uppercase;
    border-bottom: 1px solid #1e2d45;
  }

  .camp-table td {
    padding: 12px;
    border-bottom: 1px solid #172234;
    vertical-align: middle;
  }

  .switch-btn {
    width: 40px;
    height: 22px;
    border-radius: 999px;
    background: #334155;
    border: none;
    position: relative;
    cursor: pointer;
  }

  .switch-btn.on {
    background: #1877f2;
  }

  .switch-btn .knob {
    position: absolute;
    top: 3px;
    left: 3px;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: #ffffff;
    transition: transform 0.2s;
  }

  .switch-btn.on .knob {
    transform: translateX(18px);
  }

  .camp-name {
    font-weight: 700;
    color: #f1f5f9;
    margin-bottom: 2px;
  }

  .camp-meta {
    font-size: 0.74rem;
    color: #64748b;
  }

  .budget-val {
    font-weight: 700;
    color: #e2e8f0;
  }

  .budget-tag {
    display: inline-block;
    font-size: 0.7rem;
    font-weight: 800;
    padding: 1px 6px;
    border-radius: 4px;
    background: rgba(56, 189, 248, 0.15);
    color: #38bdf8;
  }

  .metrics-line {
    display: flex;
    gap: 10px;
    color: #cbd5e1;
    margin-bottom: 2px;
  }

  .health-badge {
    display: inline-block;
    font-size: 0.72rem;
    font-weight: 800;
    padding: 2px 8px;
    border-radius: 999px;
    margin-bottom: 3px;
  }

  .health-badge.success {
    background: rgba(16, 185, 129, 0.18);
    color: #34d399;
  }

  .health-badge.danger {
    background: rgba(239, 68, 68, 0.2);
    color: #f87171;
  }

  .health-badge.neutral {
    background: rgba(148, 163, 184, 0.18);
    color: #cbd5e1;
  }

  .health-badge.info {
    background: rgba(56, 189, 248, 0.16);
    color: #38bdf8;
  }

  .rec-text {
    font-size: 0.73rem;
    color: #94a3b8;
    max-width: 240px;
  }

  .action-btns {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
  }

  .act-btn {
    border: 1px solid #2b3b55;
    background: #162133;
    color: #e2e8f0;
    font-size: 0.74rem;
    font-weight: 700;
    padding: 5px 9px;
    border-radius: 6px;
    cursor: pointer;
  }

  .act-btn.scale {
    border-color: rgba(16, 185, 129, 0.45);
    color: #34d399;
  }

  .act-btn.cut {
    border-color: rgba(239, 68, 68, 0.45);
    color: #f87171;
  }

  .robo-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px;
  }

  .robo-col {
    background: #0b111c;
    border: 1px solid #1e2b40;
    border-radius: 12px;
    padding: 14px;
  }

  .robo-col h3 {
    margin: 0 0 10px;
    font-size: 0.92rem;
    color: #f8fafc;
  }

  .robo-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 10px;
    padding: 10px 12px;
    border-radius: 8px;
    background: rgba(16, 185, 129, 0.08);
    border: 1px solid rgba(16, 185, 129, 0.25);
    margin-bottom: 8px;
  }

  .robo-item.danger {
    background: rgba(239, 68, 68, 0.08);
    border-color: rgba(239, 68, 68, 0.28);
  }

  .robo-item.warn {
    background: rgba(245, 158, 11, 0.08);
    border-color: rgba(245, 158, 11, 0.28);
  }

  .publicos-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }

  .pub-card {
    background: #0b111c;
    border: 1px solid #1e2c42;
    border-radius: 12px;
    padding: 14px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .pub-top {
    display: flex;
    justify-content: space-between;
    font-size: 0.74rem;
    font-weight: 700;
  }

  .pub-cat {
    color: #38bdf8;
  }

  .pub-budget {
    color: #34d399;
  }

  .pub-card h3 {
    margin: 0;
    font-size: 0.95rem;
    color: #f8fafc;
  }

  .pub-card p {
    margin: 0;
    font-size: 0.8rem;
    color: #94a3b8;
  }

  .pub-tags {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    font-size: 0.75rem;
    color: #cbd5e1;
  }

  .pub-interests {
    font-size: 0.74rem;
    color: #64748b;
  }

  .btn-apply-pub {
    margin-top: 4px;
    background: #1877f2;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 0.8rem;
    font-weight: 700;
    cursor: pointer;
  }

  .empty-note {
    font-size: 0.82rem;
    color: #64748b;
  }
</style>
