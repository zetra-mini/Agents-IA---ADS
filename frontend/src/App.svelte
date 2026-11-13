<script>
  import { onMount } from 'svelte';
  import SimuladorMetaAds from './SimuladorMetaAds.svelte';

  // Navegação principal do SaaS Premium (exibe apenas 1 visão limpa por vez)
  let activeNav = $state(
    typeof window !== 'undefined' && window.location.search.includes('view=adsmanager')
      ? 'automacao'
      : 'dashboard'
  ); // 'dashboard' | 'assistida' | 'robo' | 'automacao'

  let apiOnline = $state(false);
  let providers = $state([]);
  let selectedProvider = $state('ollama');
  let criativosLista = $state([]);

  // Estado da Conta Real & Hub (octaviosilva2/meta-ads + AdSimples)
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

  let campanhas = $state([]);
  let copilot = $state(null);
  let publicos = $state([]);
  let chartMetric = $state('spend'); // 'spend' | 'conversions' | 'roas'

  // Modal de Conexão da Conta Real
  let showConnectModal = $state(false);
  let tokenInput = $state('');
  let accountIdInput = $state('');
  let accountNameInput = $state('');
  let conectandoConta = $state(false);

  // Toast / Notificações discretas
  let toastMessage = $state('');
  let toastType = $state('ok'); // 'ok' | 'error'

  function notify(msg, type = 'ok') {
    toastMessage = msg;
    toastType = type;
    setTimeout(() => {
      if (toastMessage === msg) toastMessage = '';
    }, 5500);
  }

  // Estado da Criação de Campanha Assistida (4 Etapas)
  let etapaAssistida = $state(1);
  let publicandoReal = $state(false);
  let abrindoNavegador = $state(false);
  let simuladorRef = $state(null);
  let validacaoPreflight = $state(null);

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
          'Procurando repasse de financiamento com parcelas acessíveis na sua região? Confira veículos revisados em Campo Largo e Curitiba.',
        titulo: 'Repasse de Financiamento Facilitado',
        descricao: 'Simule agora pelo WhatsApp ou Formulário',
        cta: 'Saiba mais',
      },
    ],
    observacoes_compliance: ['Categoria Especial Crédito verificada.'],
  });

  // Chat Lateral Assistido (estilo octaviosilva2/meta-ads ChatPanel)
  const SUGESTOES_CHAT = [
    'Criar campanha CBO R$ 500/dia para Curitiba e Campo Largo',
    'Muda o orçamento para R$ 300 por dia e foca em WhatsApp',
    'Adiciona São José dos Pinhais e idade 25 a 52 anos',
    'Qual campanha está com o melhor ROAS na conta?',
  ];

  let chatInput = $state('');
  let enviandoChat = $state(false);
  let toolActivities = $state([]);
  let chatHistory = $state([
    {
      autor: 'ia',
      texto:
        'Olá! Sou seu Copiloto Meta Ads. Posso analisar suas campanhas ou montar uma campanha assistida passo a passo com você.',
    },
  ]);

  // Dados para o Gráfico de Performance (14 dias)
  const serieGrafico = $derived.by(() => {
    const baseSpend = copilot?.pacing?.daily_budget_target || 500;
    const dias = [];
    const multiplicadores = [0.82, 0.91, 0.88, 0.96, 1.04, 0.92, 0.99, 1.08, 0.95, 1.02, 1.12, 0.97, 1.05, 1.0];
    for (let i = 0; i < 14; i++) {
      const m = multiplicadores[i];
      const spend = Math.round(baseSpend * m);
      const conv = Math.max(1, Math.round((spend / 11.5) * (0.9 + (i % 3) * 0.12)));
      const roas = Number((2.8 + (i % 4) * 0.45).toFixed(2));
      dias.push({
        label: `D-${14 - i}`,
        spend,
        conversions: conv,
        roas,
      });
    }
    return dias;
  });

  async function carregarTudo() {
    try {
      const [resHealth, resProv, resCon, resCamp, resCop, resPub, resCri] = await Promise.all([
        fetch('/api/health'),
        fetch('/api/providers'),
        fetch('/api/meta/connection'),
        fetch('/api/meta/campaigns'),
        fetch('/api/meta/copilot'),
        fetch('/api/meta/audiences-store'),
        fetch('/api/criativos'),
      ]);

      apiOnline = resHealth.ok;
      if (resProv.ok) {
        const p = await resProv.json();
        providers = p.providers || [];
        selectedProvider = p.active_provider || 'ollama';
      }
      if (resCon.ok) connection = await resCon.json();
      if (resCamp.ok) campanhas = await resCamp.json();
      if (resCop.ok) copilot = await resCop.json();
      if (resPub.ok) {
        const pubData = await resPub.json();
        publicos = pubData.publicos || [];
      }
      if (resCri.ok) {
        const criData = await resCri.json();
        criativosLista = criData.arquivos || [];
      }
    } catch (_) {
      apiOnline = false;
    }
  }

  async function conectarContaReal() {
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
        if (!res.ok) throw new Error(data.detail || 'Erro ao conectar token.');
        connection = data;
        showConnectModal = false;
        notify(`Conectado ao Gerenciador Real: ${data.selected_account_name || data.selected_account_id}`);
      } else if (accountIdInput.trim()) {
        const res = await fetch('/api/meta/select-account', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            account_id: accountIdInput.trim(),
            account_name: accountNameInput.trim() || null,
          }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Erro ao vincular conta.');
        connection = data;
        showConnectModal = false;
        notify(`Conta ${data.selected_account_id} vinculada em Modo Somente Dados Reais!`);
      } else {
        throw new Error('Informe o Meta Access Token ou o ID da Conta (act_...).');
      }
      await carregarTudo();
    } catch (err) {
      notify(err.message, 'error');
    } finally {
      conectandoConta = false;
    }
  }

  async function sincronizarDoNavegador() {
    conectandoConta = true;
    try {
      const res = await fetch('/api/meta/sync-browser', { method: 'POST' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Falha ao sincronizar navegador.');
      connection = data.connection;
      notify(
        data.navegador?.account_id
          ? `Conta ${data.navegador.account_id} sincronizada do navegador!`
          : data.navegador?.mensagem || 'Sessão do navegador verificada.'
      );
      await carregarTudo();
    } catch (err) {
      notify(err.message, 'error');
    } finally {
      conectandoConta = false;
    }
  }

  async function definirModoDadosReais(somenteReais) {
    try {
      const res = await fetch('/api/meta/real-mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ somente_dados_reais: somenteReais }),
      });
      if (res.ok) {
        connection = await res.json();
        notify(
          somenteReais
            ? 'Modo Somente Dados Reais ativado (dados de demonstração ocultados).'
            : 'Modo Demonstração ativado.'
        );
        await carregarTudo();
      }
    } catch (_) {}
  }

  async function trocarContaAtiva(e) {
    const id = e.target.value;
    if (!id) return;
    const res = await fetch('/api/meta/select-account', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ account_id: id }),
    });
    if (res.ok) {
      connection = await res.json();
      notify(`Conta ativa alterada para ${connection.selected_account_id}`);
      await carregarTudo();
    }
  }

  async function alternarStatusCampanha(camp) {
    const novo = camp.status === 'ACTIVE' ? 'PAUSED' : 'ACTIVE';
    const res = await fetch(`/api/meta/campaigns/${camp.id}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: novo }),
    });
    if (res.ok) {
      notify(`Campanha "${camp.name}" ${novo === 'ACTIVE' ? 'ativada' : 'pausada'}.`);
      await carregarTudo();
    }
  }

  async function escalarOrcamento(camp, fator) {
    const novoValor = Math.max(10, Math.round(camp.daily_budget * fator));
    const res = await fetch(`/api/meta/campaigns/${camp.id}/budget`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ daily_budget: novoValor }),
    });
    if (res.ok) {
      notify(`Orçamento de "${camp.name}" atualizado para R$ ${novoValor.toFixed(2)}/dia.`);
      await carregarTudo();
    }
  }

  async function enviarMensagemChat(textoCustom = null) {
    const msg = (textoCustom ?? chatInput).trim();
    if (!msg || enviandoChat) return;

    chatHistory = [...chatHistory, { autor: 'user', texto: msg }];
    if (!textoCustom) chatInput = '';
    enviandoChat = true;

    if (msg.toLowerCase().includes('roas') || msg.toLowerCase().includes('como estão')) {
      toolActivities = ['Consultando métricas da conta (7d)', 'Analisando Winners e Bleeders'];
      await new Promise((r) => setTimeout(r, 450));
      const topWinner = copilot?.winners?.[0];
      const resumo = topWinner
        ? `A campanha com melhor desempenho é "${topWinner.name}" (ROAS ${topWinner.totals.roas}x, CTR ${topWinner.totals.ctr}%, CPA R$ ${topWinner.totals.cpa}). Você pode escalar +20% em 1 clique na tabela!`
        : `Nos últimos 7 dias a conta investiu R$ ${copilot?.summary_7d?.spend_7d?.toFixed(2) || '0.00'} com ${copilot?.summary_7d?.conversions_7d || 0} conversões.`;
      toolActivities = [];
      chatHistory = [...chatHistory, { autor: 'ia', texto: resumo }];
      enviandoChat = false;
      return;
    }

    toolActivities = ['Estruturando campanha assistida', 'Validando regras Placard / Meta API'];
    try {
      const res = await fetch('/api/campanhas/assistida/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mensagem: msg,
          plano_atual: planoAssistido,
          etapa_atual: etapaAssistida,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Erro ao processar comando.');
      planoAssistido = data.plano_campanha;
      etapaAssistida = data.etapa_sugerida || etapaAssistida;
      validacaoPreflight = data.validacao_preflight;
      chatHistory = [...chatHistory, { autor: 'ia', texto: data.resposta_assistente }];
      if (activeNav !== 'assistida') {
        activeNav = 'assistida';
      }
    } catch (err) {
      chatHistory = [...chatHistory, { autor: 'ia', texto: `⚠️ ${err.message}` }];
    } finally {
      toolActivities = [];
      enviandoChat = false;
    }
  }

  async function criarCampanhaAssistidaNavegador() {
    abrindoNavegador = true;
    toolActivities = ['Orquestrando CrewAI + Playwright', 'Movendo mouse no Gerenciador de Anúncios'];
    try {
      const res = await fetch('/api/campanhas/criar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          instrucao: `${planoAssistido.nome_campanha} - ${planoAssistido.tipo_orcamento} R$ ${planoAssistido.orcamento_diario_brl}/dia para ${planoAssistido.conjuntos?.[0]?.publico?.localizacoes?.join(', ')}`,
          executar_navegador: true,
          provider: selectedProvider,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Erro ao criar campanha.');
      validacaoPreflight = data.validacao_preflight;
      activeNav = 'automacao';
      setTimeout(() => {
        simuladorRef?.iniciarDemonstracaoVisual();
      }, 100);
      notify('Campanha registrada e automação visual iniciada no Gerenciador de Anúncios!');
      await carregarTudo();
    } catch (err) {
      notify(err.message, 'error');
    } finally {
      toolActivities = [];
      abrindoNavegador = false;
    }
  }

  async function criarCampanhaDiretoGraphApi() {
    publicandoReal = true;
    try {
      const res = await fetch('/api/campanhas/assistida/publicar-graph', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ plano_campanha: planoAssistido }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Erro na Meta Graph API.');
      notify(data.mensagem);
      chatHistory = [...chatHistory, { autor: 'ia', texto: `🎉 ${data.mensagem}` }];
      await carregarTudo();
      activeNav = 'dashboard';
    } catch (err) {
      notify(err.message, 'error');
      chatHistory = [...chatHistory, { autor: 'ia', texto: `⚠️ ${err.message}` }];
    } finally {
      publicandoReal = false;
    }
  }

  function usarPublicoDaLoja(pub) {
    enviarMensagemChat(pub.instrucao_pronta);
    activeNav = 'assistida';
    notify(`Público "${pub.titulo}" carregado na Criação Assistida!`);
  }

  onMount(carregarTudo);
</script>

<div class="app-shell">
  <!-- 1. SIDEBAR DE NAVEGAÇÃO PREMIUM -->
  <aside class="sidebar">
    <div class="brand">
      <div class="brand-logo">∞</div>
      <div>
        <div class="brand-name">AdSimples AI</div>
        <div class="brand-sub">Meta Ads Copilot</div>
      </div>
    </div>

    <nav class="nav-list">
      <button
        type="button"
        class="nav-item"
        class:active={activeNav === 'dashboard'}
        onclick={() => (activeNav = 'dashboard')}
      >
        <span class="nav-icon">📊</span>
        <span>Dashboard & Campanhas</span>
        <span class="nav-count">{campanhas.length}</span>
      </button>

      <button
        type="button"
        class="nav-item"
        class:active={activeNav === 'assistida'}
        onclick={() => (activeNav = 'assistida')}
      >
        <span class="nav-icon">🪄</span>
        <span>Criação Assistida</span>
        <span class="nav-badge">4 Etapas</span>
      </button>

      <button
        type="button"
        class="nav-item"
        class:active={activeNav === 'robo'}
        onclick={() => (activeNav = 'robo')}
      >
        <span class="nav-icon">🤖</span>
        <span>Robô & Loja Públicos</span>
      </button>

      <button
        type="button"
        class="nav-item"
        class:active={activeNav === 'automacao'}
        onclick={() => {
          activeNav = 'automacao';
          setTimeout(() => simuladorRef?.iniciarDemonstracaoVisual(), 80);
        }}
      >
        <span class="nav-icon">🖱️</span>
        <span>Automação Visual IA</span>
      </button>
    </nav>

    <div class="sidebar-footer">
      <div class="engine-box">
        <label for="ai-engine-sel">Motor de IA Ativo</label>
        <select id="ai-engine-sel" bind:value={selectedProvider}>
          {#if providers.length === 0}
            <option value="ollama">Ollama Local (qwen2.5)</option>
            <option value="opencode">OpenCode CLI</option>
            <option value="anthropic">Anthropic Claude</option>
            <option value="openai">OpenAI GPT-4o</option>
          {:else}
            {#each providers as p}
              <option value={p.id}>{p.label}</option>
            {/each}
          {/if}
        </select>
      </div>

      <div class="api-status">
        <span class="status-dot" class:online={apiOnline}></span>
        <span>{apiOnline ? 'Backend Online · 8010' : 'Backend Offline'}</span>
      </div>
    </div>
  </aside>

  <!-- 2. ÁREA CENTRAL DE TRABALHO -->
  <div class="workspace">
    <!-- BARRA SUPERIOR: CONTA DE ANÚNCIOS REAL & GERENCIADOR -->
    <header class="topbar">
      <div class="account-status">
        <span class="conn-indicator" class:connected={connection.connected}></span>
        <div>
          <div class="acc-headline">
            {#if connection.connected}
              Gerenciador: <strong>{connection.business_name}</strong>
              <span class="sep">·</span>
              Conta: <strong>{connection.selected_account_name || 'Meta Ads'}</strong>
              <code class="act-pill">{connection.selected_account_id}</code>
            {:else}
              Gerenciador: <strong>Não conectado</strong>
              <span class="muted-hint">(Sem Conta Real vinculada)</span>
            {/if}
          </div>
        </div>
      </div>

      <div class="topbar-actions">
        {#if connection.available_accounts?.length > 0}
          <select class="top-select" value={connection.selected_account_id} onchange={trocarContaAtiva}>
            {#each connection.available_accounts as acc}
              <option value={acc.id}>{acc.name} ({acc.id})</option>
            {/each}
          </select>
        {/if}

        <div class="segmented-mode">
          <button
            type="button"
            class:selected={!connection.somente_dados_reais}
            onclick={() => definirModoDadosReais(false)}
          >
            Demo
          </button>
          <button
            type="button"
            class:selected={connection.somente_dados_reais}
            onclick={() => definirModoDadosReais(true)}
          >
            🔒 Só Reais
          </button>
        </div>

        <button type="button" class="btn-top ghost" onclick={sincronizarDoNavegador} disabled={conectandoConta}>
          🌐 Sincronizar Navegador
        </button>

        <button type="button" class="btn-top primary" onclick={() => (showConnectModal = true)}>
          🔗 {connection.connected ? 'Conta / Token' : 'Conectar Conta Meta'}
        </button>
      </div>
    </header>

    {#if toastMessage}
      <div class="toast-bar" class:error={toastType === 'error'}>
        <span>{toastType === 'error' ? '⚠️' : '✅'} {toastMessage}</span>
        <button type="button" onclick={() => (toastMessage = '')}>✕</button>
      </div>
    {/if}

    <!-- CONTEÚDO PRINCIPAL (1 VISÃO LIMPA POR VEZ) -->
    <main class="canvas">
      {#if activeNav === 'dashboard'}
        <!-- VISÃO 1: DASHBOARD & CAMPANHAS (Estilo octaviosilva2/meta-ads + AdSimples) -->
        <div class="view-header">
          <div>
            <h1>Visão Geral & Campanhas</h1>
            <p>Métricas consolidadas dos últimos 7 dias e controle rápido de orçamento e veiculação.</p>
          </div>
          <button type="button" class="btn-cta" onclick={() => (activeNav = 'assistida')}>
            🪄 + Nova Campanha Assistida
          </button>
        </div>

        {#if copilot}
          <div class="stats-grid">
            <div class="stat-card">
              <div class="stat-label">Investimento (7 dias)</div>
              <div class="stat-value">R$ {copilot.summary_7d.spend_7d.toFixed(2)}</div>
              <div class="stat-foot">
                Meta diária: R$ {copilot.pacing.daily_budget_target.toFixed(2)} ·
                <span class="pace-tag">{copilot.pacing.status}</span>
              </div>
            </div>

            <div class="stat-card">
              <div class="stat-label">Conversões / Leads</div>
              <div class="stat-value">{copilot.summary_7d.conversions_7d}</div>
              <div class="stat-foot">CPA Médio: R$ {copilot.summary_7d.cpa_7d.toFixed(2)}</div>
            </div>

            <div class="stat-card">
              <div class="stat-label">ROAS Médio</div>
              <div class="stat-value accent">{copilot.summary_7d.roas_7d.toFixed(2)}x</div>
              <div class="stat-foot">CTR Médio: {copilot.summary_7d.ctr_7d.toFixed(2)}%</div>
            </div>

            <div class="stat-card">
              <div class="stat-label">Saúde da Conta (IA)</div>
              <div class="stat-value">
                🏆 {copilot.winners.length} <span class="stat-sep">/</span> 🩸 {copilot.bleeders.length}
              </div>
              <div class="stat-foot">Winners p/ escalar vs. Bleeders</div>
            </div>
          </div>
        {/if}

        <!-- GRÁFICO DE PERFORMANCE LIMPO (Inspirado em octaviosilva2/meta-ads PerformanceChart) -->
        <section class="panel-card">
          <div class="panel-head">
            <h2>Evolução Diária (Últimos 14 dias)</h2>
            <div class="segmented-mode">
              <button type="button" class:selected={chartMetric === 'spend'} onclick={() => (chartMetric = 'spend')}>
                Investimento (R$)
              </button>
              <button
                type="button"
                class:selected={chartMetric === 'conversions'}
                onclick={() => (chartMetric = 'conversions')}
              >
                Conversões
              </button>
              <button type="button" class:selected={chartMetric === 'roas'} onclick={() => (chartMetric = 'roas')}>
                ROAS
              </button>
            </div>
          </div>

          <div class="chart-bars">
            {#each serieGrafico as item}
              {@const val = item[chartMetric]}
              {@const maxVal = Math.max(...serieGrafico.map((d) => d[chartMetric]), 1)}
              {@const pct = Math.max(12, Math.round((val / maxVal) * 100))}
              <div class="bar-col" title={`${item.label}: ${val}`}>
                <div class="bar-val">
                  {chartMetric === 'spend' ? `R$${val}` : chartMetric === 'roas' ? `${val}x` : val}
                </div>
                <div class="bar-track">
                  <div class="bar-fill" style="height: {pct}%"></div>
                </div>
                <div class="bar-label">{item.label}</div>
              </div>
            {/each}
          </div>
        </section>

        <!-- TABELA DE CAMPANHAS -->
        <section class="panel-card">
          <div class="panel-head">
            <h2>Campanhas da Conta ({campanhas.length})</h2>
            <span class="panel-sub">
              {connection.somente_dados_reais ? 'Exibindo exclusivamente dados reais' : 'Modo demonstração sincronizado'}
            </span>
          </div>

          {#if campanhas.length === 0}
            <div class="empty-state">
              <h3>Nenhuma campanha real carregada neste momento</h3>
              <p>
                Você está no modo <strong>Somente Dados Reais</strong>. Conecte seu Token da Meta API no topo, sincronize do navegador ou crie uma campanha em <strong>🪄 Criação Assistida</strong>.
              </p>
              <div class="empty-actions">
                <button type="button" class="btn-cta" onclick={() => (activeNav = 'assistida')}>
                  🪄 Criar Campanha Assistida Agora
                </button>
                <button type="button" class="btn-top ghost" onclick={() => definirModoDadosReais(false)}>
                  Ver Campanhas de Demonstração
                </button>
              </div>
            </div>
          {:else}
            <div class="table-scroll">
              <table class="clean-table">
                <thead>
                  <tr>
                    <th>Status</th>
                    <th>Campanha</th>
                    <th>Orçamento</th>
                    <th class="num">Gasto 7d</th>
                    <th class="num">CTR</th>
                    <th class="num">CPA</th>
                    <th class="num">ROAS</th>
                    <th>Diagnóstico IA</th>
                    <th class="right">Ações 1-Clique</th>
                  </tr>
                </thead>
                <tbody>
                  {#each campanhas as camp}
                    <tr>
                      <td>
                        <button
                          type="button"
                          class="toggle-switch"
                          class:on={camp.status === 'ACTIVE'}
                          onclick={() => alternarStatusCampanha(camp)}
                          aria-label="Alternar status da campanha"
                        >
                          <span class="knob"></span>
                        </button>
                      </td>
                      <td>
                        <div class="c-name">{camp.name}</div>
                        <div class="c-sub">
                          <span class="origin-tag" class:real={camp.is_real}>
                            {camp.is_real ? 'CONTA REAL' : 'DEMO'}
                          </span>
                          · {camp.objective.replace('OUTCOME_', '')} · 📍 {(camp.locations || []).join(', ')}
                        </div>
                      </td>
                      <td>
                        <strong>R$ {camp.daily_budget.toFixed(2)}</strong><span class="c-sub">/dia</span>
                        <span class="btype-pill">{camp.budget_type}</span>
                      </td>
                      <td class="num">R$ {camp.totals.spend.toFixed(2)}</td>
                      <td class="num">{camp.totals.ctr}%</td>
                      <td class="num">R$ {camp.totals.cpa}</td>
                      <td class="num strong-roas">{camp.totals.roas}x</td>
                      <td>
                        <span class="health-pill {camp.health_color}">{camp.health_tag}</span>
                      </td>
                      <td class="right">
                        <div class="row-actions">
                          <button type="button" class="mini-btn up" onclick={() => escalarOrcamento(camp, 1.2)}>
                            +20%
                          </button>
                          <button type="button" class="mini-btn down" onclick={() => escalarOrcamento(camp, 0.8)}>
                            -20%
                          </button>
                          <button type="button" class="mini-btn" onclick={() => alternarStatusCampanha(camp)}>
                            {camp.status === 'ACTIVE' ? 'Pausar' : 'Ativar'}
                          </button>
                        </div>
                      </td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
          {/if}
        </section>

      {:else if activeNav === 'assistida'}
        <!-- VISÃO 2: CRIAÇÃO DE CAMPANHA ASSISTIDA (4 Etapas + Preview Ao Vivo do Anúncio) -->
        <div class="view-header">
          <div>
            <h1>🪄 Criação de Campanha Assistida</h1>
            <p>Configure passo a passo ou peça alterações no Assistente IA à direita.</p>
          </div>
          <div class="stepper-pills">
            {#each [1, 2, 3, 4] as num}
              <button
                type="button"
                class="step-tab"
                class:active={etapaAssistida === num}
                onclick={() => (etapaAssistida = num)}
              >
                Etapa {num}
              </button>
            {/each}
          </div>
        </div>

        <div class="assisted-grid">
          <!-- Formulário Guiado da Etapa Atual -->
          <section class="panel-card">
            {#if etapaAssistida === 1}
              <h2>Etapa 1 de 4 — Estrutura da Campanha & Orçamento</h2>
              <div class="form-grid">
                <div class="field full">
                  <label for="f-camp-name">Nome da Campanha</label>
                  <input id="f-camp-name" type="text" bind:value={planoAssistido.nome_campanha} />
                </div>
                <div class="field">
                  <label for="f-obj">Objetivo Principal</label>
                  <select id="f-obj" bind:value={planoAssistido.objetivo}>
                    <option value="Leads">Cadastros / Leads (Formulário ou WhatsApp)</option>
                    <option value="Vendas">Vendas / Conversões</option>
                    <option value="Trafego">Tráfego no Link</option>
                    <option value="Engajamento">Engajamento / Mensagens</option>
                  </select>
                </div>
                <div class="field">
                  <label for="f-btype">Estratégia de Orçamento</label>
                  <select id="f-btype" bind:value={planoAssistido.tipo_orcamento}>
                    <option value="CBO">CBO — Orçamento Advantage+ na Campanha</option>
                    <option value="ABO">ABO — Orçamento por Conjunto</option>
                  </select>
                </div>
                <div class="field">
                  <label for="f-budget">Orçamento Diário (R$)</label>
                  <input id="f-budget" type="number" min="6" step="10" bind:value={planoAssistido.orcamento_diario_brl} />
                </div>
                <div class="field">
                  <label for="f-cat">Categoria de Anúncio Especial</label>
                  <input id="f-cat" type="text" bind:value={planoAssistido.categoria_especial_anuncio} />
                </div>
              </div>
              <div class="wiz-footer">
                <span class="wiz-hint">Destino: {connection.selected_account_id || 'Gerenciador Conectado'}</span>
                <button type="button" class="btn-cta" onclick={() => (etapaAssistida = 2)}>
                  Avançar para Público & Cidades →
                </button>
              </div>

            {:else if etapaAssistida === 2}
              <h2>Etapa 2 de 4 — Público-Alvo & Localização Regional</h2>
              {#if planoAssistido.conjuntos?.[0]}
                <div class="form-grid">
                  <div class="field full">
                    <label for="f-adset">Nome do Conjunto de Anúncios</label>
                    <input id="f-adset" type="text" bind:value={planoAssistido.conjuntos[0].nome} />
                  </div>
                  <div class="field">
                    <label for="f-locs">Cidades / Regiões (separadas por vírgula)</label>
                    <input
                      id="f-locs"
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
                  <div class="field">
                    <label for="f-raio">Raio Geográfico (km)</label>
                    <input id="f-raio" type="number" min="5" max="80" bind:value={planoAssistido.conjuntos[0].publico.raio_km} />
                  </div>
                  <div class="field">
                    <label for="f-amin">Idade Mínima</label>
                    <input id="f-amin" type="number" min="18" max="65" bind:value={planoAssistido.conjuntos[0].publico.idade_minima} />
                  </div>
                  <div class="field">
                    <label for="f-amax">Idade Máxima</label>
                    <input id="f-amax" type="number" min="18" max="65" bind:value={planoAssistido.conjuntos[0].publico.idade_maxima} />
                  </div>
                  <div class="field full">
                    <label for="f-int">Interesses Sugeridos pelo Agente</label>
                    <input
                      id="f-int"
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
              <div class="wiz-footer">
                <button type="button" class="btn-top ghost" onclick={() => (etapaAssistida = 1)}>← Etapa 1</button>
                <button type="button" class="btn-cta" onclick={() => (etapaAssistida = 3)}>
                  Avançar para Criativo & Copywriter →
                </button>
              </div>

            {:else if etapaAssistida === 3}
              <h2>Etapa 3 de 4 — Copywriter & Mídia do Anúncio</h2>
              {#if planoAssistido.anuncios?.[0]}
                <div class="form-grid">
                  <div class="field">
                    <label for="f-adname">Nome do Anúncio</label>
                    <input id="f-adname" type="text" bind:value={planoAssistido.anuncios[0].nome} />
                  </div>
                  <div class="field">
                    <label for="f-media">Mídia Selecionada</label>
                    <select id="f-media" bind:value={planoAssistido.anuncios[0].arquivo_criativo}>
                      {#if criativosLista.length === 0}
                        <option value="criativo_repasse_curitiba.png">criativo_repasse_curitiba.png</option>
                      {:else}
                        {#each criativosLista as arq}
                          <option value={arq.nome}>{arq.nome}</option>
                        {/each}
                      {/if}
                    </select>
                  </div>
                  <div class="field full">
                    <label for="f-copy">Texto Principal (Copy de Conversão)</label>
                    <textarea id="f-copy" rows="4" bind:value={planoAssistido.anuncios[0].texto_principal}></textarea>
                  </div>
                  <div class="field">
                    <label for="f-head">Título (Headline)</label>
                    <input id="f-head" type="text" bind:value={planoAssistido.anuncios[0].titulo} />
                  </div>
                  <div class="field">
                    <label for="f-cta">Chamada para Ação (CTA)</label>
                    <select id="f-cta" bind:value={planoAssistido.anuncios[0].cta}>
                      <option value="Saiba mais">Saiba mais</option>
                      <option value="Enviar mensagem">Enviar mensagem (WhatsApp)</option>
                      <option value="Cadastre-se">Cadastre-se</option>
                      <option value="Solicitar agora">Solicitar agora</option>
                    </select>
                  </div>
                </div>
              {/if}
              <div class="wiz-footer">
                <button type="button" class="btn-top ghost" onclick={() => (etapaAssistida = 2)}>← Etapa 2</button>
                <button type="button" class="btn-cta" onclick={() => (etapaAssistida = 4)}>
                  Revisar e Criar Campanha →
                </button>
              </div>

            {:else}
              <h2>Etapa 4 de 4 — Revisão Pré-Voo & Criação Real</h2>
              <div class="review-box">
                <div class="rev-item">
                  <span>Campanha</span>
                  <strong>{planoAssistido.nome_campanha}</strong>
                </div>
                <div class="rev-item">
                  <span>Objetivo & Verba</span>
                  <strong>{planoAssistido.objetivo} · {planoAssistido.tipo_orcamento} · R$ {Number(planoAssistido.orcamento_diario_brl).toFixed(2)}/dia</strong>
                </div>
                <div class="rev-item">
                  <span>Segmentação</span>
                  <strong>
                    {planoAssistido.conjuntos?.[0]?.publico?.localizacoes?.join(', ')} (+{planoAssistido.conjuntos?.[0]?.publico?.raio_km}km) ·
                    {planoAssistido.conjuntos?.[0]?.publico?.idade_minima} a {planoAssistido.conjuntos?.[0]?.publico?.idade_maxima} anos
                  </strong>
                </div>
                <div class="rev-item">
                  <span>Segurança</span>
                  <strong class="ok-txt">🔒 Status inicial PAUSED / Rascunho (Nenhum valor gasto sem sua ativação)</strong>
                </div>
              </div>

              <div class="launch-stack">
                <button
                  type="button"
                  class="btn-launch primary"
                  onclick={criarCampanhaAssistidaNavegador}
                  disabled={abrindoNavegador}
                >
                  {abrindoNavegador
                    ? '🖱️ Iniciando Agente no Gerenciador...'
                    : '🖱️ Criar de Forma Assistida no Gerenciador (Ver Mouse Preenchendo)'}
                </button>

                <button
                  type="button"
                  class="btn-launch graph"
                  onclick={criarCampanhaDiretoGraphApi}
                  disabled={publicandoReal}
                >
                  {publicandoReal
                    ? 'Publicando na Meta API...'
                    : '🚀 Publicar Direto na Minha Conta Real via Meta Graph API (PAUSED)'}
                </button>
              </div>

              <div class="wiz-footer">
                <button type="button" class="btn-top ghost" onclick={() => (etapaAssistida = 3)}>← Voltar e Editar</button>
              </div>
            {/if}
          </section>

          <!-- Card de Prévia Ao Vivo do Anúncio (Feed Instagram / Facebook) -->
          <section class="panel-card preview-card">
            <h2>Prévia em Tempo Real (Feed Instagram / Facebook)</h2>
            <div class="ig-mockup">
              <div class="ig-head">
                <div class="ig-avatar">∞</div>
                <div>
                  <div class="ig-author">{connection.selected_account_name || 'Sua Empresa · Meta Ads'}</div>
                  <div class="ig-spons">Patrocinado · 🌍 {planoAssistido.conjuntos?.[0]?.publico?.localizacoes?.[0] || 'Brasil'}</div>
                </div>
              </div>
              <div class="ig-copy">
                {planoAssistido.anuncios?.[0]?.texto_principal || ''}
              </div>
              <div class="ig-media">
                <div class="ig-media-badge">🖼️ {planoAssistido.anuncios?.[0]?.arquivo_criativo || 'criativo.png'}</div>
                <div class="ig-media-overlay">{planoAssistido.anuncios?.[0]?.titulo || ''}</div>
              </div>
              <div class="ig-cta-bar">
                <div>
                  <div class="ig-cta-title">{planoAssistido.anuncios?.[0]?.titulo || ''}</div>
                  <div class="ig-cta-sub">{planoAssistido.anuncios?.[0]?.descricao || 'Simule pelo WhatsApp'}</div>
                </div>
                <span class="ig-cta-btn">{planoAssistido.anuncios?.[0]?.cta || 'Saiba mais'}</span>
              </div>
            </div>
          </section>
        </div>

      {:else if activeNav === 'robo'}
        <!-- VISÃO 3: ROBÔ OTIMIZADOR & LOJA DE PÚBLICOS (Hackr Ads + meta-ads-kit) -->
        <div class="view-header">
          <div>
            <h1>🤖 Robô Otimizador & Loja de Públicos</h1>
            <p>Diagnóstico automático de campanhas (Winners vs. Bleeders) e públicos validados em 1 clique.</p>
          </div>
        </div>

        <div class="two-col-grid">
          <section class="panel-card">
            <h2>🏆 Winners — Prontas para Escalar Orçamento</h2>
            {#if !copilot || copilot.winners.length === 0}
              <p class="muted-p">Nenhuma campanha classificada como Winner no momento.</p>
            {:else}
              {#each copilot.winners as w}
                <div class="opt-row win">
                  <div>
                    <strong>{w.name}</strong>
                    <div class="c-sub">ROAS {w.totals.roas}x · CTR {w.totals.ctr}% · CPA R$ {w.totals.cpa}</div>
                  </div>
                  <button type="button" class="mini-btn up" onclick={() => escalarOrcamento(w, 1.2)}>
                    ⚡ Escalar +20%
                  </button>
                </div>
              {/each}
            {/if}
          </section>

          <section class="panel-card">
            <h2>🩸 Bleeders & Alertas de Fadiga</h2>
            {#if !copilot || (copilot.bleeders.length === 0 && copilot.fatigue_alerts.length === 0)}
              <p class="muted-p">Nenhum desperdício de orçamento ou fadiga detectada.</p>
            {:else}
              {#each copilot.bleeders as b}
                <div class="opt-row bleed">
                  <div>
                    <strong>{b.name}</strong>
                    <div class="c-sub">CTR {b.totals.ctr}% · Gasto 7d: R$ {b.totals.spend.toFixed(2)}</div>
                  </div>
                  <button type="button" class="mini-btn down" onclick={() => alternarStatusCampanha(b)}>
                    ⏸️ Pausar Agora
                  </button>
                </div>
              {/each}
              {#each copilot.fatigue_alerts as f}
                <div class="opt-row warn">
                  <div>
                    <strong>😴 Fadiga de Criativo: {f.campaign_name}</strong>
                    <div class="c-sub">Queda de CTR de {f.drop_pct}% ({f.start_ctr}% → {f.end_ctr}%).</div>
                  </div>
                </div>
              {/each}
            {/if}
          </section>
        </div>

        <section class="panel-card">
          <div class="panel-head">
            <h2>🎯 Loja de Públicos Prontos (Estilo AdSimples / Hackr Ads)</h2>
            <span class="panel-sub">Clique em qualquer público para carregar na Criação Assistida</span>
          </div>
          <div class="audiences-grid">
            {#each publicos as pub}
              <div class="aud-card">
                <div class="aud-top">
                  <span class="aud-cat">{pub.categoria}</span>
                  <span class="aud-bud">{pub.tipo_orcamento} · R$ {pub.orcamento_sugerido_brl}/dia</span>
                </div>
                <h3>{pub.titulo}</h3>
                <p>{pub.descricao}</p>
                <div class="aud-meta">
                  📍 {pub.cidades_sugeridas.join(', ')} (+{pub.raio_km}km) · 🎂 {pub.idade_minima}–{pub.idade_maxima} anos
                </div>
                <button type="button" class="btn-use-aud" onclick={() => usarPublicoDaLoja(pub)}>
                  ⚡ Usar Este Público na Criação Assistida
                </button>
              </div>
            {/each}
          </div>
        </section>

      {:else if activeNav === 'automacao'}
        <!-- VISÃO 4: AUTOMAÇÃO VISUAL NO GERENCIADOR DE ANÚNCIOS (Mouse IA em Tempo Real) -->
        <div class="view-header">
          <div>
            <h1>🖱️ Automação Visual no Gerenciador de Anúncios</h1>
            <p>Acompanhe o cursor da IA clicando e preenchendo cada etapa da campanha em tempo real.</p>
          </div>
        </div>

        <SimuladorMetaAds
          bind:this={simuladorRef}
          plano={planoAssistido}
          criativos={criativosLista}
          autoStart={true}
        />
      {/if}
    </main>
  </div>

  <!-- 3. DOCK LATERAL DIREITO: ASSISTENTE DE CAMPANHAS IA (Estilo octaviosilva2/meta-ads ChatPanel) -->
  <aside class="chat-dock">
    <div class="dock-header">
      <div>
        <strong>💬 Assistente de Campanhas</strong>
        <div class="dock-sub">Criação assistida & análise em tempo real</div>
      </div>
    </div>

    <div class="dock-messages">
      <div class="suggestions-box">
        <div class="sug-title">Ações Rápidas Assistidas:</div>
        {#each SUGESTOES_CHAT as sug}
          <button type="button" class="sug-chip" onclick={() => enviarMensagemChat(sug)}>
            {sug}
          </button>
        {/each}
      </div>

      {#each chatHistory as item}
        <div class="msg-bubble {item.autor}">
          <div class="msg-role">{item.autor === 'ia' ? '🤖 Copiloto IA' : '👤 Você'}</div>
          <div class="msg-text">{item.texto}</div>
        </div>
      {/each}

      {#each toolActivities as act}
        <div class="tool-pill">🔧 {act}...</div>
      {/each}
    </div>

    <form
      class="dock-form"
      onsubmit={(e) => {
        e.preventDefault();
        enviarMensagemChat();
      }}
    >
      <textarea
        rows="2"
        placeholder="Peça para criar ou ajustar campanha (ex: R$ 350/dia em Curitiba)..."
        bind:value={chatInput}
        onkeydown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            enviarMensagemChat();
          }
        }}
      ></textarea>
      <button type="submit" disabled={enviandoChat}>
        {enviandoChat ? ' Processando...' : 'Enviar para o Assistente'}
      </button>
    </form>
  </aside>
</div>

<!-- MODAL DE CONEXÃO REAL COM A CONTA META ADS -->
{#if showConnectModal}
  <div class="modal-backdrop">
    <div class="modal-card">
      <div class="modal-head">
        <h3>🔐 Conectar Gerenciador (BM) & Conta de Anúncios Real</h3>
        <button type="button" class="modal-close" onclick={() => (showConnectModal = false)}>✕</button>
      </div>
      <p class="modal-desc">
        Conecte seu <strong>Meta Access Token</strong> para sincronizar automaticamente todas as suas Contas de Anúncios (<code>act_...</code>) e campanhas reais via <code>graph.facebook.com</code>, ou informe diretamente o ID da sua conta.
      </p>

      <div class="modal-fields">
        <div class="field">
          <label for="m-token">Meta Access Token (ads_read, ads_management)</label>
          <input id="m-token" type="password" placeholder="EAABwzLixnjYBO..." bind:value={tokenInput} />
          <small>
            Obtenha no
            <a href="https://developers.facebook.com/tools/explorer/" target="_blank" rel="noopener noreferrer">
              Graph API Explorer
            </a>
            ou em Usuários do Sistema no Business Manager.
          </small>
        </div>

        <div class="field">
          <label for="m-act">ID da Conta de Anúncios (ex: act_1049283741)</label>
          <input id="m-act" type="text" placeholder="act_1234567890" bind:value={accountIdInput} />
        </div>

        <div class="field">
          <label for="m-name">Nome da Conta / BM (Opcional)</label>
          <input id="m-name" type="text" placeholder="Ex: Conta Principal Curitiba" bind:value={accountNameInput} />
        </div>
      </div>

      <div class="modal-foot">
        <button type="button" class="btn-top ghost" onclick={() => (showConnectModal = false)}>Cancelar</button>
        <button type="button" class="btn-cta" onclick={conectarContaReal} disabled={conectandoConta}>
          {conectandoConta ? 'Conectando...' : '✅ Conectar Conta Real'}
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  .app-shell {
    display: grid;
    grid-template-columns: 236px minmax(0, 1fr) 340px;
    min-height: 100vh;
    background: var(--bg-app);
  }

  @media (max-width: 1180px) {
    .app-shell {
      grid-template-columns: 210px minmax(0, 1fr);
    }
    .chat-dock {
      display: none;
    }
  }

  /* SIDEBAR */
  .sidebar {
    background: var(--bg-sidebar);
    border-right: 1px solid var(--border);
    padding: 20px 14px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }

  .brand {
    display: flex;
    align-items: center;
    gap: 11px;
    padding: 4px 8px 20px;
    border-bottom: 1px solid var(--border);
  }

  .brand-logo {
    width: 34px;
    height: 34px;
    border-radius: 9px;
    background: linear-gradient(135deg, #2563eb, #06b6d4);
    display: grid;
    place-items: center;
    font-weight: 900;
    font-size: 18px;
    color: #fff;
  }

  .brand-name {
    font-weight: 800;
    font-size: 0.96rem;
    letter-spacing: -0.01em;
  }

  .brand-sub {
    font-size: 0.72rem;
    color: var(--muted);
  }

  .nav-list {
    display: flex;
    flex-direction: column;
    gap: 5px;
    margin-top: 16px;
    flex: 1;
  }

  .nav-item {
    display: flex;
    align-items: center;
    gap: 10px;
    width: 100%;
    padding: 10px 12px;
    border-radius: 9px;
    border: 1px solid transparent;
    background: transparent;
    color: var(--text-secondary);
    font-size: 0.84rem;
    font-weight: 600;
    cursor: pointer;
    text-align: left;
    transition: all 0.15s;
  }

  .nav-item:hover {
    background: var(--surface);
    color: #fff;
  }

  .nav-item.active {
    background: rgba(37, 99, 235, 0.16);
    color: #60a5fa;
    border-color: rgba(59, 130, 246, 0.32);
  }

  .nav-icon {
    font-size: 1rem;
  }

  .nav-count,
  .nav-badge {
    margin-left: auto;
    font-size: 0.68rem;
    font-weight: 700;
    padding: 2px 7px;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.07);
    color: var(--text-secondary);
  }

  .sidebar-footer {
    border-top: 1px solid var(--border);
    padding-top: 14px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .engine-box label {
    display: block;
    font-size: 0.7rem;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-bottom: 4px;
  }

  .engine-box select {
    width: 100%;
    background: var(--surface);
    color: var(--text);
    border: 1px solid var(--border-strong);
    border-radius: 7px;
    padding: 6px 8px;
    font-size: 0.78rem;
  }

  .api-status {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.74rem;
    color: var(--muted);
  }

  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--danger);
  }

  .status-dot.online {
    background: var(--accent);
    box-shadow: 0 0 8px var(--accent);
  }

  /* WORKSPACE CENTRAL */
  .workspace {
    display: flex;
    flex-direction: column;
    min-width: 0;
  }

  .topbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    padding: 12px 24px;
    background: var(--bg-sidebar);
    border-bottom: 1px solid var(--border);
    flex-wrap: wrap;
  }

  .account-status {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .conn-indicator {
    width: 9px;
    height: 9px;
    border-radius: 50%;
    background: #f59e0b;
  }

  .conn-indicator.connected {
    background: #10b981;
    box-shadow: 0 0 8px #10b981;
  }

  .acc-headline {
    font-size: 0.82rem;
    color: var(--text-secondary);
  }

  .acc-headline strong {
    color: #fff;
  }

  .sep {
    margin: 0 6px;
    color: var(--muted);
  }

  .muted-hint {
    color: var(--muted);
    font-size: 0.76rem;
    margin-left: 4px;
  }

  .act-pill {
    background: var(--surface-elevated);
    color: #38bdf8;
    padding: 2px 6px;
    border-radius: 5px;
    font-size: 0.74rem;
    margin-left: 4px;
  }

  .topbar-actions {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }

  .top-select {
    background: var(--surface);
    color: #fff;
    border: 1px solid var(--border-strong);
    border-radius: 7px;
    padding: 6px 10px;
    font-size: 0.78rem;
  }

  .segmented-mode {
    display: inline-flex;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 7px;
    padding: 2px;
  }

  .segmented-mode button {
    background: transparent;
    border: none;
    color: var(--muted);
    padding: 4px 10px;
    font-size: 0.75rem;
    font-weight: 600;
    border-radius: 5px;
    cursor: pointer;
  }

  .segmented-mode button.selected {
    background: var(--surface-elevated);
    color: #fff;
  }

  .btn-top {
    border-radius: 7px;
    padding: 6px 12px;
    font-size: 0.78rem;
    font-weight: 600;
    cursor: pointer;
    border: 1px solid var(--border-strong);
  }

  .btn-top.ghost {
    background: var(--surface);
    color: var(--text-secondary);
  }

  .btn-top.primary {
    background: var(--primary);
    color: #fff;
    border-color: var(--primary-light);
  }

  .toast-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 9px 24px;
    background: rgba(16, 185, 129, 0.15);
    border-bottom: 1px solid rgba(16, 185, 129, 0.35);
    color: #a7f3d0;
    font-size: 0.82rem;
    font-weight: 600;
  }

  .toast-bar.error {
    background: rgba(239, 68, 68, 0.16);
    border-bottom-color: rgba(239, 68, 68, 0.35);
    color: #fecaca;
  }

  .toast-bar button {
    background: transparent;
    border: none;
    color: inherit;
    cursor: pointer;
  }

  .canvas {
    padding: 24px;
    display: flex;
    flex-direction: column;
    gap: 20px;
    overflow-y: auto;
  }

  .view-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 16px;
    flex-wrap: wrap;
  }

  .view-header h1 {
    margin: 0;
    font-size: 1.35rem;
    font-weight: 700;
    letter-spacing: -0.02em;
  }

  .view-header p {
    margin: 2px 0 0;
    font-size: 0.84rem;
    color: var(--muted);
  }

  .btn-cta {
    background: var(--primary);
    color: #fff;
    border: none;
    border-radius: 8px;
    padding: 9px 16px;
    font-size: 0.82rem;
    font-weight: 700;
    cursor: pointer;
  }

  .btn-cta:hover {
    background: var(--primary-light);
  }

  /* STAT CARDS */
  .stats-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 14px;
  }

  @media (max-width: 920px) {
    .stats-grid {
      grid-template-columns: 1fr 1fr;
    }
  }

  .stat-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 16px;
  }

  .stat-label {
    font-size: 0.74rem;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-bottom: 6px;
  }

  .stat-value {
    font-size: 1.5rem;
    font-weight: 750;
    letter-spacing: -0.02em;
  }

  .stat-value.accent {
    color: #34d399;
  }

  .stat-sep {
    color: var(--muted);
    font-weight: 400;
  }

  .stat-foot {
    margin-top: 6px;
    font-size: 0.75rem;
    color: var(--muted);
  }

  .pace-tag {
    color: #38bdf8;
    font-weight: 700;
  }

  /* PANELS */
  .panel-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 18px 20px;
  }

  .panel-card h2 {
    margin: 0 0 12px;
    font-size: 0.92rem;
    font-weight: 700;
    color: var(--text);
  }

  .panel-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    margin-bottom: 14px;
    flex-wrap: wrap;
  }

  .panel-head h2 {
    margin: 0;
  }

  .panel-sub {
    font-size: 0.76rem;
    color: var(--muted);
  }

  /* CHART BARS */
  .chart-bars {
    display: grid;
    grid-template-columns: repeat(14, 1fr);
    gap: 8px;
    height: 150px;
    align-items: end;
    padding-top: 16px;
  }

  .bar-col {
    display: flex;
    flex-direction: column;
    align-items: center;
    height: 100%;
    gap: 4px;
  }

  .bar-val {
    font-size: 0.66rem;
    color: var(--muted);
  }

  .bar-track {
    flex: 1;
    width: 100%;
    max-width: 28px;
    background: rgba(255, 255, 255, 0.03);
    border-radius: 6px;
    display: flex;
    align-items: flex-end;
    overflow: hidden;
  }

  .bar-fill {
    width: 100%;
    background: linear-gradient(180deg, #3b82f6 0%, #1d4ed8 100%);
    border-radius: 6px 6px 0 0;
    transition: height 0.25s ease;
  }

  .bar-label {
    font-size: 0.68rem;
    color: var(--muted);
  }

  /* CLEAN TABLE */
  .table-scroll {
    overflow-x: auto;
  }

  .clean-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.83rem;
  }

  .clean-table th {
    text-align: left;
    padding: 10px 12px;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--muted);
    border-bottom: 1px solid var(--border);
  }

  .clean-table td {
    padding: 12px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    vertical-align: middle;
  }

  .clean-table .num {
    text-align: right;
    font-variant-numeric: tabular-nums;
  }

  .clean-table .right {
    text-align: right;
  }

  .strong-roas {
    font-weight: 700;
    color: #34d399;
  }

  .toggle-switch {
    width: 36px;
    height: 20px;
    border-radius: 999px;
    background: #334155;
    border: none;
    position: relative;
    cursor: pointer;
  }

  .toggle-switch.on {
    background: var(--primary);
  }

  .toggle-switch .knob {
    position: absolute;
    top: 2px;
    left: 2px;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: #fff;
    transition: transform 0.18s;
  }

  .toggle-switch.on .knob {
    transform: translateX(16px);
  }

  .c-name {
    font-weight: 650;
    color: #fff;
  }

  .c-sub {
    font-size: 0.73rem;
    color: var(--muted);
    margin-top: 2px;
  }

  .origin-tag {
    display: inline-block;
    padding: 1px 5px;
    border-radius: 4px;
    font-size: 0.65rem;
    font-weight: 700;
    background: rgba(245, 158, 11, 0.14);
    color: #fcd34d;
  }

  .origin-tag.real {
    background: rgba(16, 185, 129, 0.18);
    color: #34d399;
  }

  .btype-pill {
    font-size: 0.68rem;
    font-weight: 700;
    padding: 1px 6px;
    border-radius: 4px;
    background: rgba(59, 130, 246, 0.15);
    color: #60a5fa;
    margin-left: 4px;
  }

  .health-pill {
    display: inline-block;
    font-size: 0.71rem;
    font-weight: 700;
    padding: 3px 8px;
    border-radius: 999px;
  }

  .health-pill.success {
    background: rgba(16, 185, 129, 0.15);
    color: #34d399;
  }

  .health-pill.danger {
    background: rgba(239, 68, 68, 0.16);
    color: #f87171;
  }

  .health-pill.neutral {
    background: rgba(148, 163, 184, 0.14);
    color: #cbd5e1;
  }

  .health-pill.info {
    background: rgba(59, 130, 246, 0.15);
    color: #60a5fa;
  }

  .row-actions {
    display: inline-flex;
    gap: 5px;
  }

  .mini-btn {
    background: var(--surface-elevated);
    border: 1px solid var(--border-strong);
    color: var(--text-secondary);
    border-radius: 6px;
    padding: 4px 8px;
    font-size: 0.73rem;
    font-weight: 600;
    cursor: pointer;
  }

  .mini-btn.up {
    color: #34d399;
    border-color: rgba(16, 185, 129, 0.35);
  }

  .mini-btn.down {
    color: #f87171;
    border-color: rgba(239, 68, 68, 0.35);
  }

  /* CRIAÇÃO ASSISTIDA */
  .stepper-pills {
    display: flex;
    gap: 6px;
  }

  .step-tab {
    background: var(--surface);
    border: 1px solid var(--border);
    color: var(--muted);
    padding: 6px 13px;
    border-radius: 7px;
    font-size: 0.78rem;
    font-weight: 700;
    cursor: pointer;
  }

  .step-tab.active {
    background: var(--primary);
    color: #fff;
    border-color: var(--primary-light);
  }

  .assisted-grid {
    display: grid;
    grid-template-columns: 1.35fr 1fr;
    gap: 18px;
    align-items: start;
  }

  @media (max-width: 960px) {
    .assisted-grid {
      grid-template-columns: 1fr;
    }
  }

  .form-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
  }

  .field.full {
    grid-column: 1 / -1;
  }

  .field label {
    display: block;
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--text-secondary);
    margin-bottom: 5px;
  }

  .field input,
  .field select,
  .field textarea {
    width: 100%;
    background: var(--bg-sidebar);
    border: 1px solid var(--border-strong);
    color: #fff;
    border-radius: 8px;
    padding: 9px 11px;
    font-size: 0.84rem;
  }

  .field small {
    display: block;
    margin-top: 4px;
    font-size: 0.72rem;
    color: var(--muted);
  }

  .field small a {
    color: #60a5fa;
  }

  .wiz-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 18px;
    padding-top: 14px;
    border-top: 1px solid var(--border);
  }

  .wiz-hint {
    font-size: 0.76rem;
    color: var(--muted);
  }

  .review-box {
    background: var(--bg-sidebar);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 14px;
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin-bottom: 16px;
  }

  .rev-item {
    display: flex;
    justify-content: space-between;
    font-size: 0.82rem;
    gap: 12px;
  }

  .rev-item span {
    color: var(--muted);
  }

  .ok-txt {
    color: #34d399;
  }

  .launch-stack {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .btn-launch {
    width: 100%;
    padding: 12px 16px;
    border-radius: 9px;
    border: none;
    font-size: 0.86rem;
    font-weight: 700;
    cursor: pointer;
    color: #fff;
  }

  .btn-launch.primary {
    background: var(--primary);
  }

  .btn-launch.graph {
    background: #059669;
  }

  /* INSTAGRAM / FB AD PREVIEW MOCKUP */
  .ig-mockup {
    background: #0d1017;
    border: 1px solid var(--border-strong);
    border-radius: 12px;
    overflow: hidden;
  }

  .ig-head {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 12px;
  }

  .ig-avatar {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: var(--primary);
    display: grid;
    place-items: center;
    font-weight: 800;
  }

  .ig-author {
    font-size: 0.82rem;
    font-weight: 700;
  }

  .ig-spons {
    font-size: 0.7rem;
    color: var(--muted);
  }

  .ig-copy {
    padding: 0 12px 12px;
    font-size: 0.81rem;
    color: var(--text-secondary);
    white-space: pre-line;
  }

  .ig-media {
    height: 170px;
    background: linear-gradient(135deg, #172554 0%, #0f172a 100%);
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    padding: 14px;
    border-top: 1px solid var(--border);
    border-bottom: 1px solid var(--border);
  }

  .ig-media-badge {
    align-self: flex-start;
    background: rgba(0, 0, 0, 0.55);
    padding: 4px 9px;
    border-radius: 6px;
    font-size: 0.72rem;
    color: #93c5fd;
  }

  .ig-media-overlay {
    font-size: 1rem;
    font-weight: 800;
    color: #fff;
  }

  .ig-cta-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 12px;
    background: #131824;
  }

  .ig-cta-title {
    font-size: 0.8rem;
    font-weight: 700;
  }

  .ig-cta-sub {
    font-size: 0.7rem;
    color: var(--muted);
  }

  .ig-cta-btn {
    background: var(--surface-elevated);
    border: 1px solid var(--border-strong);
    padding: 6px 11px;
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: 700;
  }

  /* ROBÔ & PÚBLICOS */
  .two-col-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }

  @media (max-width: 900px) {
    .two-col-grid {
      grid-template-columns: 1fr;
    }
  }

  .opt-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    padding: 11px 12px;
    border-radius: 9px;
    margin-bottom: 8px;
    background: var(--bg-sidebar);
    border: 1px solid var(--border);
  }

  .audiences-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 14px;
  }

  @media (max-width: 900px) {
    .audiences-grid {
      grid-template-columns: 1fr;
    }
  }

  .aud-card {
    background: var(--bg-sidebar);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 15px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .aud-top {
    display: flex;
    justify-content: space-between;
    font-size: 0.73rem;
    font-weight: 700;
  }

  .aud-cat {
    color: #60a5fa;
  }

  .aud-bud {
    color: #34d399;
  }

  .aud-card h3 {
    margin: 0;
    font-size: 0.94rem;
  }

  .aud-card p {
    margin: 0;
    font-size: 0.8rem;
    color: var(--muted);
  }

  .aud-meta {
    font-size: 0.75rem;
    color: var(--text-secondary);
  }

  .btn-use-aud {
    margin-top: 4px;
    background: var(--surface-elevated);
    color: #fff;
    border: 1px solid var(--border-strong);
    border-radius: 7px;
    padding: 8px 12px;
    font-size: 0.78rem;
    font-weight: 700;
    cursor: pointer;
  }

  .btn-use-aud:hover {
    background: var(--primary);
    border-color: var(--primary-light);
  }

  /* CHAT DOCK LATERAL */
  .chat-dock {
    background: var(--bg-sidebar);
    border-left: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    height: 100vh;
    position: sticky;
    top: 0;
  }

  .dock-header {
    padding: 14px 16px;
    border-bottom: 1px solid var(--border);
  }

  .dock-sub {
    font-size: 0.72rem;
    color: var(--muted);
  }

  .dock-messages {
    flex: 1;
    overflow-y: auto;
    padding: 14px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .suggestions-box {
    display: flex;
    flex-direction: column;
    gap: 6px;
    margin-bottom: 6px;
  }

  .sug-title {
    font-size: 0.7rem;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  .sug-chip {
    background: var(--surface);
    border: 1px solid var(--border);
    color: var(--text-secondary);
    border-radius: 8px;
    padding: 7px 10px;
    font-size: 0.76rem;
    text-align: left;
    cursor: pointer;
    transition: border-color 0.15s;
  }

  .sug-chip:hover {
    border-color: var(--primary-light);
    color: #fff;
  }

  .msg-bubble {
    padding: 10px 12px;
    border-radius: 10px;
    font-size: 0.8rem;
    line-height: 1.45;
  }

  .msg-bubble.ia {
    background: var(--surface);
    border: 1px solid var(--border);
  }

  .msg-bubble.user {
    background: rgba(37, 99, 235, 0.2);
    border: 1px solid rgba(59, 130, 246, 0.35);
    align-self: flex-end;
  }

  .msg-role {
    font-size: 0.68rem;
    font-weight: 700;
    color: #60a5fa;
    margin-bottom: 3px;
  }

  .msg-text {
    white-space: pre-line;
  }

  .tool-pill {
    font-size: 0.74rem;
    color: #93c5fd;
    background: rgba(37, 99, 235, 0.12);
    border: 1px dashed rgba(59, 130, 246, 0.35);
    padding: 6px 10px;
    border-radius: 7px;
  }

  .dock-form {
    padding: 12px 14px;
    border-top: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .dock-form textarea {
    width: 100%;
    background: var(--surface);
    border: 1px solid var(--border-strong);
    color: #fff;
    border-radius: 8px;
    padding: 8px 10px;
    font-size: 0.8rem;
    resize: none;
  }

  .dock-form button {
    background: var(--primary);
    color: #fff;
    border: none;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 0.8rem;
    font-weight: 700;
    cursor: pointer;
  }

  /* EMPTY & MODAL */
  .empty-state {
    text-align: center;
    padding: 28px 16px;
  }

  .empty-state h3 {
    margin: 0 0 6px;
    font-size: 1rem;
  }

  .empty-state p {
    margin: 0 auto 16px;
    max-width: 540px;
    color: var(--muted);
    font-size: 0.84rem;
  }

  .empty-actions {
    display: flex;
    justify-content: center;
    gap: 10px;
  }

  .modal-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.7);
    backdrop-filter: blur(4px);
    display: grid;
    place-items: center;
    z-index: 1000;
    padding: 16px;
  }

  .modal-card {
    background: var(--surface);
    border: 1px solid var(--border-strong);
    border-radius: 14px;
    width: 100%;
    max-width: 520px;
    padding: 20px 22px;
    box-shadow: 0 24px 60px rgba(0, 0, 0, 0.6);
  }

  .modal-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
  }

  .modal-head h3 {
    margin: 0;
    font-size: 1rem;
  }

  .modal-close {
    background: transparent;
    border: none;
    color: var(--muted);
    font-size: 1rem;
    cursor: pointer;
  }

  .modal-desc {
    font-size: 0.82rem;
    color: var(--muted);
    margin: 0 0 16px;
  }

  .modal-fields {
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin-bottom: 18px;
  }

  .modal-foot {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
  }

  .muted-p {
    color: var(--muted);
    font-size: 0.82rem;
  }
</style>
