<script>
  import { onMount } from 'svelte';
  import SimuladorMetaAds from './SimuladorMetaAds.svelte';
  import OpenAdKitStudio from './OpenAdKitStudio.svelte';

  // Navegação principal do SaaS Premium (exibe apenas 1 visão limpa por vez)
  let activeNav = $state(
    typeof window !== 'undefined' && window.location.search.includes('view=adsmanager')
      ? 'automacao'
      : 'dashboard'
  ); // 'dashboard' | 'assistida' | 'robo' | 'automacao'

  let apiOnline = $state(false);
  let providers = $state([]);
  let selectedProvider = $state('opencode');
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
  let adsets = $state([]);
  let ads = $state([]);
  let activeLevelTab = $state('campaigns'); // 'campaigns' | 'adsets' | 'ads'
  let copilot = $state(null);
  let publicos = $state([]);
  let chartMetric = $state('spend'); // 'spend' | 'conversions' | 'roas'

  // Modal de Conexão da Conta Real
  let showConnectModal = $state(false);
  let showChatDrawer = $state(false);
  let buscaCampanha = $state('');
  let filtroStatus = $state('TODAS'); // 'TODAS' | 'ACTIVE' | 'PAUSED'
  let buscaAdset = $state('');
  let filtroStatusAdset = $state('TODAS'); // 'TODAS' | 'ACTIVE' | 'PAUSED'
  let buscaAd = $state('');
  let filtroStatusAd = $state('TODAS'); // 'TODAS' | 'ACTIVE' | 'PAUSED'
  let adModalPreview = $state(null); // Prévia de Anúncio / Criativo estilo Feed
  let tokenInput = $state('');
  let accountIdInput = $state('');
  let accountNameInput = $state('');
  let conectandoConta = $state(false);

  // Filtros Avançados estilo Gerenciador de Anúncios Meta
  let filtroObjetivo = $state('TODOS'); // 'TODOS' | 'LEADS' | 'SALES' | 'TRAFFIC' | 'ENGAGEMENT' | 'AWARENESS'
  let filtroTipoOrcamento = $state('TODOS'); // 'TODOS' | 'CBO' | 'ABO'
  let filtroSaude = $state('TODOS'); // 'TODOS' | 'WINNER' | 'BLEEDER' | 'REAL'
  let filtroPeriodo = $state('7d'); // 'hoje' | 'ontem' | '7d' | '14d' | '30d'

  function limparFiltrosGerenciador() {
    filtroStatus = 'TODAS';
    filtroStatusAdset = 'TODAS';
    filtroStatusAd = 'TODAS';
    filtroObjetivo = 'TODOS';
    filtroTipoOrcamento = 'TODOS';
    filtroSaude = 'TODOS';
    filtroPeriodo = '7d';
    buscaCampanha = '';
    buscaAdset = '';
    buscaAd = '';
  }

  // Modal de Chaves de API Externa & Motores de IA
  let showApiKeysModal = $state(false);
  let salvandoKeys = $state(false);
  let openaiKeyInput = $state('');
  let openaiModelInput = $state('gpt-4o');
  let anthropicKeyInput = $state('');
  let anthropicModelInput = $state('claude-sonnet-4-6');
  let geminiKeyInput = $state('');
  let geminiModelInput = $state('gemini-2.5-flash');
  let ollamaModelInput = $state('qwen2.5:0.5b');
  let ollamaUrlInput = $state('http://127.0.0.1:11434');
  let opencodeModelInput = $state('opencode/mimo-v2.6-flash-free');

  const activeProviderMeta = $derived(
    providers.find((p) => p.id === selectedProvider) || {
      id: selectedProvider,
      configured: selectedProvider === 'ollama' || selectedProvider === 'opencode',
      requires_api_key: ['openai', 'anthropic', 'google'].includes(selectedProvider),
    }
  );

  const campanhasFiltradas = $derived.by(() => {
    let lista = campanhas;
    if (filtroStatus === 'ACTIVE') {
      lista = lista.filter((c) => c.status === 'ACTIVE');
    } else if (filtroStatus === 'PAUSED') {
      lista = lista.filter((c) => c.status === 'PAUSED');
    }
    if (filtroObjetivo !== 'TODOS') {
      lista = lista.filter((c) => (c.objective || '').toUpperCase().includes(filtroObjetivo.toUpperCase()));
    }
    if (filtroTipoOrcamento !== 'TODOS') {
      lista = lista.filter((c) => (c.budget_type || '').toUpperCase() === filtroTipoOrcamento.toUpperCase());
    }
    if (filtroSaude === 'WINNER') {
      lista = lista.filter((c) => (c.health_tag || '').includes('WINNER'));
    } else if (filtroSaude === 'BLEEDER') {
      lista = lista.filter((c) => (c.health_tag || '').includes('BLEEDER'));
    } else if (filtroSaude === 'REAL') {
      lista = lista.filter((c) => c.is_real);
    }
    if (buscaCampanha.trim()) {
      const termo = buscaCampanha.trim().toLowerCase();
      lista = lista.filter(
        (c) =>
          (c.name || '').toLowerCase().includes(termo) ||
          (c.id || '').toLowerCase().includes(termo) ||
          (c.objective || '').toLowerCase().includes(termo) ||
          (c.locations || []).some((l) => l.toLowerCase().includes(termo))
      );
    }
    return lista;
  });

  const adsetsFiltrados = $derived.by(() => {
    let lista = adsets;
    if (filtroStatusAdset === 'ACTIVE') {
      lista = lista.filter((a) => a.status === 'ACTIVE');
    } else if (filtroStatusAdset === 'PAUSED') {
      lista = lista.filter((a) => a.status === 'PAUSED');
    }
    if (filtroObjetivo !== 'TODOS') {
      lista = lista.filter((a) => (a.optimization_goal || '').toUpperCase().includes(filtroObjetivo.toUpperCase()));
    }
    if (buscaAdset.trim()) {
      const termo = buscaAdset.trim().toLowerCase();
      lista = lista.filter(
        (a) =>
          (a.name || '').toLowerCase().includes(termo) ||
          (a.campaign_name || '').toLowerCase().includes(termo) ||
          (a.id || '').toLowerCase().includes(termo) ||
          (a.locations || []).some((l) => l.toLowerCase().includes(termo))
      );
    }
    return lista;
  });

  const adsFiltrados = $derived.by(() => {
    let lista = ads;
    if (filtroStatusAd === 'ACTIVE') {
      lista = lista.filter((a) => a.status === 'ACTIVE');
    } else if (filtroStatusAd === 'PAUSED') {
      lista = lista.filter((a) => a.status === 'PAUSED');
    }
    if (buscaAd.trim()) {
      const termo = buscaAd.trim().toLowerCase();
      lista = lista.filter(
        (a) =>
          (a.name || '').toLowerCase().includes(termo) ||
          (a.headline || '').toLowerCase().includes(termo) ||
          (a.primary_text || '').toLowerCase().includes(termo) ||
          (a.campaign_name || '').toLowerCase().includes(termo) ||
          (a.adset_name || '').toLowerCase().includes(termo) ||
          (a.id || '').toLowerCase().includes(termo)
      );
    }
    return lista;
  });

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
  let subindoCriativo = $state(false);
  let ultimaCampanhaRealCriada = $state(null);
  let simuladorRef = $state(null);
  let validacaoPreflight = $state(null);

  function ehVideoCriativo(nome) {
    if (!nome) return false;
    return /\.(mp4|mov|webm)$/i.test(nome);
  }

  function temArquivoRealNaPasta(nome) {
    if (!nome) return false;
    return criativosLista.some((a) => a.nome === nome);
  }

  async function uploadArquivoCriativo(event) {
    const files = event.target?.files;
    if (!files || files.length === 0) return;
    subindoCriativo = true;
    try {
      const formData = new FormData();
      for (const f of files) {
        formData.append('files', f);
      }
      const res = await fetch('/api/criativos/upload', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Falha ao enviar arquivo de criativo.');
      criativosLista = data.inventario?.arquivos || criativosLista;
      const primeiroSalvo = data.salvos?.[0];
      if (primeiroSalvo && planoAssistido.anuncios?.[0]) {
        planoAssistido.anuncios[0].arquivo_criativo = primeiroSalvo;
        planoAssistido.anuncios[0].formato = ehVideoCriativo(primeiroSalvo) ? 'video' : 'imagem_unica';
      }
      notify(`Criativo "${primeiroSalvo}" enviado com sucesso e aplicado no anúncio!`);
    } catch (err) {
      notify(err.message, 'error');
    } finally {
      subindoCriativo = false;
      if (event.target) event.target.value = '';
    }
  }

  let planoAssistido = $state({
    nome_campanha: 'Campanha CBO - Leads Repasse Financiamento - Curitiba',
    objetivo: 'Leads',
    tipo_orcamento: 'CBO',
    orcamento_diario_brl: 500.0,
    estrategia_lance: 'Volume mais alto',
    categoria_especial_anuncio: 'Nenhuma',
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
      const [resHealth, resProv, resCon, resCamp, resAdsets, resAds, resCop, resPub, resCri] = await Promise.all([
        fetch('/api/health'),
        fetch('/api/providers'),
        fetch('/api/meta/connection'),
        fetch('/api/meta/campaigns'),
        fetch('/api/meta/adsets'),
        fetch('/api/meta/ads'),
        fetch('/api/meta/copilot'),
        fetch('/api/meta/audiences-store'),
        fetch('/api/criativos'),
      ]);

      apiOnline = resHealth.ok;
      if (resProv.ok) {
        const p = await resProv.json();
        providers = p.providers || [];
        selectedProvider = p.active_provider || 'opencode';
        const pOpenai = providers.find((x) => x.id === 'openai');
        const pAnthropic = providers.find((x) => x.id === 'anthropic');
        const pGoogle = providers.find((x) => x.id === 'google');
        const pOllama = providers.find((x) => x.id === 'ollama');
        const pOpencode = providers.find((x) => x.id === 'opencode');
        if (pOpenai?.model) openaiModelInput = pOpenai.model;
        if (pAnthropic?.model) anthropicModelInput = pAnthropic.model;
        if (pGoogle?.model) geminiModelInput = pGoogle.model;
        if (pOllama?.model) ollamaModelInput = pOllama.model;
        if (pOllama?.base_url) ollamaUrlInput = pOllama.base_url;
        if (pOpencode?.model) opencodeModelInput = pOpencode.model;
      }
      if (resCon.ok) {
        connection = await resCon.json();
        const savedToken =
          tokenInput.trim() ||
          (typeof localStorage !== 'undefined' ? localStorage.getItem('meta_ads_saved_token') || '' : '');
        if (!connection.connected && savedToken) {
          const recon = await fetch('/api/meta/connect-token', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ access_token: savedToken }),
          });
          if (recon.ok) connection = await recon.json();
        }
      }
      if (resCamp.ok) campanhas = await resCamp.json();
      if (resAdsets.ok) adsets = await resAdsets.json();
      if (resAds.ok) ads = await resAds.json();
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
        if (typeof localStorage !== 'undefined') {
          localStorage.setItem('meta_ads_saved_token', tokenInput.trim());
        }
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

  async function aoSelecionarMotorIA(e) {
    const novo = e.target.value;
    selectedProvider = novo;
    const info = providers.find((p) => p.id === novo);
    if (info && info.requires_api_key && !info.configured) {
      showApiKeysModal = true;
      notify(`Informe a API Key para ativar o motor ${info.label}.`);
      return;
    }
    try {
      const res = await fetch('/api/providers/configure', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ active_provider: novo }),
      });
      if (res.ok) {
        const data = await res.json();
        providers = data.providers || [];
        selectedProvider = data.active_provider || novo;
        notify(`Motor de IA ativo alterado para: ${info?.label || novo}`);
      }
    } catch (_) {}
  }

  async function salvarChavesApi() {
    salvandoKeys = true;
    try {
      const payload = {
        active_provider: selectedProvider,
        openai_model: openaiModelInput.trim() || undefined,
        anthropic_model: anthropicModelInput.trim() || undefined,
        gemini_model: geminiModelInput.trim() || undefined,
        ollama_model: ollamaModelInput.trim() || undefined,
        ollama_base_url: ollamaUrlInput.trim() || undefined,
        opencode_model: opencodeModelInput.trim() || undefined,
      };
      if (openaiKeyInput.trim()) payload.openai_api_key = openaiKeyInput.trim();
      if (anthropicKeyInput.trim()) payload.anthropic_api_key = anthropicKeyInput.trim();
      if (geminiKeyInput.trim()) payload.gemini_api_key = geminiKeyInput.trim();

      const res = await fetch('/api/providers/configure', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Erro ao salvar chaves de API.');
      providers = data.providers || [];
      selectedProvider = data.active_provider || selectedProvider;
      openaiKeyInput = '';
      anthropicKeyInput = '';
      geminiKeyInput = '';
      showApiKeysModal = false;
      notify('Chaves de API e configurações de IA salvas no .env com sucesso!');
    } catch (err) {
      notify(err.message, 'error');
    } finally {
      salvandoKeys = false;
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
    const statusAnterior = camp.status;
    const novo = statusAnterior === 'ACTIVE' ? 'PAUSED' : 'ACTIVE';
    camp.status = novo; // Atualização otimista imediata na interface
    try {
      const res = await fetch(`/api/meta/campaigns/${camp.id}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: novo }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'A Meta recusou a alteração de status.');
      }
      notify(`Campanha "${camp.name}" ${novo === 'ACTIVE' ? 'ativada' : 'pausada'} com sucesso!`);
      await carregarTudo();
    } catch (err) {
      camp.status = statusAnterior; // Reverte em caso de recusa
      notify(`Erro ao alterar status: ${err.message}`, 'error');
    }
  }

  async function duplicarCampanha(camp) {
    try {
      notify(`Duplicando campanha "${camp.name}"...`);
      const res = await fetch(`/api/meta/campaigns/${camp.id}/duplicate`, {
        method: 'POST',
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Falha ao duplicar campanha.');
      notify(`Campanha "${camp.name}" duplicada como PAUSADA.`);
      await carregarTudo();
    } catch (err) {
      notify(err.message, 'error');
    }
  }

  async function excluirCampanha(camp) {
    const confirmou = window.confirm(`Deseja realmente excluir a campanha "${camp.name}"?`);
    if (!confirmou) return;
    try {
      notify(`Excluindo campanha "${camp.name}"...`);
      const res = await fetch(`/api/meta/campaigns/${camp.id}`, {
        method: 'DELETE',
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Falha ao excluir campanha.');
      campanhas = campanhas.filter((c) => c.id !== camp.id);
      notify(`Campanha "${camp.name}" excluída.`);
      await carregarTudo();
    } catch (err) {
      notify(err.message, 'error');
    }
  }

  async function alternarStatusAdset(adset) {
    const statusAnterior = adset.status;
    const novo = statusAnterior === 'ACTIVE' ? 'PAUSED' : 'ACTIVE';
    adset.status = novo;
    try {
      const res = await fetch(`/api/meta/adsets/${adset.id}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: novo }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'A Meta recusou a alteração de status do conjunto.');
      notify(`Conjunto "${adset.name}" ${novo === 'ACTIVE' ? 'ativado' : 'pausado'}!`);
      await carregarTudo();
    } catch (err) {
      adset.status = statusAnterior;
      notify(`Erro: ${err.message}`, 'error');
    }
  }

  async function alternarStatusAd(ad) {
    const statusAnterior = ad.status;
    const novo = statusAnterior === 'ACTIVE' ? 'PAUSED' : 'ACTIVE';
    ad.status = novo;
    try {
      const res = await fetch(`/api/meta/ads/${ad.id}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: novo }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'A Meta recusou a alteração de status do anúncio.');
      notify(`Anúncio "${ad.name}" ${novo === 'ACTIVE' ? 'ativado' : 'pausado'}!`);
      await carregarTudo();
    } catch (err) {
      ad.status = statusAnterior;
      notify(`Erro: ${err.message}`, 'error');
    }
  }

  async function excluirAdset(adset) {
    if (!window.confirm(`Excluir o conjunto de anúncios "${adset.name}"?`)) return;
    try {
      const res = await fetch(`/api/meta/adsets/${adset.id}`, { method: 'DELETE' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Falha ao excluir conjunto.');
      adsets = adsets.filter((a) => a.id !== adset.id);
      notify(`Conjunto "${adset.name}" excluído.`);
      await carregarTudo();
    } catch (err) {
      notify(err.message, 'error');
    }
  }

  async function excluirAd(ad) {
    if (!window.confirm(`Excluir o anúncio "${ad.name}"?`)) return;
    try {
      const res = await fetch(`/api/meta/ads/${ad.id}`, { method: 'DELETE' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Falha ao excluir anúncio.');
      ads = ads.filter((a) => a.id !== ad.id);
      notify(`Anúncio "${ad.name}" excluído.`);
      await carregarTudo();
    } catch (err) {
      notify(err.message, 'error');
    }
  }

  function abrirModalCriativo(ad) {
    adModalPreview = ad;
  }

  async function editarOrcamentoPrompt(camp) {
    const entrada = window.prompt(
      `Definir novo orçamento diário para "${camp.name}" (mínimo R$ 6,00):`,
      camp.daily_budget.toFixed(2)
    );
    if (!entrada) return;
    const valorLimpo = parseFloat(entrada.replace(',', '.'));
    if (isNaN(valorLimpo) || valorLimpo < 6.0) {
      notify('Orçamento inválido. O valor diário mínimo é R$ 6,00.', 'error');
      return;
    }
    try {
      const res = await fetch(`/api/meta/campaigns/${camp.id}/budget`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ daily_budget: valorLimpo }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Falha ao atualizar orçamento.');
      camp.daily_budget = valorLimpo;
      notify(`Orçamento atualizado para R$ ${valorLimpo.toFixed(2)}/dia.`);
      await carregarTudo();
    } catch (err) {
      notify(err.message, 'error');
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
    toolActivities = ['Criando campanha real na Meta Graph API', 'Iniciando demonstração visual no Gerenciador'];
    try {
      let msgReal = '';
      if (connection.has_token) {
        const resGraph = await fetch('/api/campanhas/assistida/publicar-graph', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ plano_campanha: planoAssistido }),
        });
        const dataGraph = await resGraph.json();
        if (!resGraph.ok) {
          throw new Error(dataGraph.detail || 'Falha ao criar campanha na Meta Graph API.');
        }
        ultimaCampanhaRealCriada = dataGraph;
        msgReal = dataGraph.mensagem;
        chatHistory = [...chatHistory, { autor: 'ia', texto: `🎉 ${dataGraph.mensagem}` }];
      }

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
      notify(
        msgReal ||
          'Campanha registrada e automação visual iniciada no Gerenciador de Anúncios!'
      );
      await carregarTudo();
    } catch (err) {
      notify(err.message, 'error');
    } finally {
      toolActivities = [];
      abrindoNavegador = false;
    }
  }

  async function criarCampanhaDiretoGraphApi() {
    if (!connection.has_token) {
      showConnectModal = true;
      notify('Confirme seu Meta Access Token uma última vez para gravar na sessão persistente e criar a campanha.', 'error');
      return;
    }
    publicandoReal = true;
    try {
      const res = await fetch('/api/campanhas/assistida/publicar-graph', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ plano_campanha: planoAssistido }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Erro na Meta Graph API.');
      ultimaCampanhaRealCriada = data;
      notify(data.mensagem);
      chatHistory = [...chatHistory, { autor: 'ia', texto: `🎉 ${data.mensagem}` }];
      await carregarTudo();
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
  <!-- 1. SIDEBAR DE NAVEGAÇÃO LIMPA (CADA SEÇÃO NO SEU LUGAR, SEM FUNÇÃO DENTRO DE FUNÇÃO) -->
  <aside class="sidebar">
    <div class="brand">
      <div class="brand-logo">∞</div>
      <div class="brand-titles">
        <div class="brand-name">AdSimples AI</div>
        <div class="brand-sub">Meta Ads Copilot</div>
      </div>
    </div>

    <!-- CONTA META ATIVA NA SIDEBAR -->
    <div class="sidebar-account-box" class:connected={connection.connected}>
      <span class="conn-dot" class:connected={connection.connected}></span>
      <div class="sidebar-acc-info">
        <strong>{connection.selected_account_name || 'Conta dos anúncios'}</strong>
        <code>{connection.selected_account_id || 'act_3339104319737592'}</code>
      </div>
    </div>

    <nav class="nav-list">
      <div class="nav-group-label">Campanhas & Operação</div>

      <button
        type="button"
        class="nav-item"
        class:active={activeNav === 'dashboard'}
        onclick={() => (activeNav = 'dashboard')}
      >
        <span class="nav-icon">📊</span>
        <span>Gerenciador & Campanhas</span>
        <span class="nav-count">{campanhas.length}</span>
      </button>

      <button
        type="button"
        class="nav-item"
        class:active={activeNav === 'relatorios'}
        onclick={() => (activeNav = 'relatorios')}
      >
        <span class="nav-icon">📈</span>
        <span>Relatórios & Evolução</span>
      </button>

      <button
        type="button"
        class="nav-item"
        class:active={activeNav === 'assistida'}
        onclick={() => (activeNav = 'assistida')}
      >
        <span class="nav-icon">🪄</span>
        <span>Criação Assistida</span>
      </button>

      <button
        type="button"
        class="nav-item"
        class:active={activeNav === 'publicos'}
        onclick={() => (activeNav = 'publicos')}
      >
        <span class="nav-icon">👥</span>
        <span>Loja de Públicos</span>
      </button>

      <button
        type="button"
        class="nav-item"
        class:active={activeNav === 'robo'}
        onclick={() => (activeNav = 'robo')}
      >
        <span class="nav-icon">🤖</span>
        <span>Robô Otimizador</span>
      </button>

      <div class="nav-group-label">OpenAdKit & Meta MCP</div>

      <button
        type="button"
        class="nav-item"
        class:active={activeNav === 'oak_brain'}
        onclick={() => (activeNav = 'oak_brain')}
      >
        <span class="nav-icon">🧠</span>
        <span>Cérebro da Marca</span>
      </button>

      <button
        type="button"
        class="nav-item"
        class:active={activeNav === 'oak_anuncios'}
        onclick={() => (activeNav = 'oak_anuncios')}
      >
        <span class="nav-icon">✍️</span>
        <span>Copy Meta Ads</span>
      </button>

      <button
        type="button"
        class="nav-item"
        class:active={activeNav === 'oak_reels'}
        onclick={() => (activeNav = 'oak_reels')}
      >
        <span class="nav-icon">🎬</span>
        <span>Roteiros Reels & Zap</span>
      </button>

      <button
        type="button"
        class="nav-item"
        class:active={activeNav === 'oak_score'}
        onclick={() => (activeNav = 'oak_score')}
      >
        <span class="nav-icon">🎯</span>
        <span>Creative Score (0–10)</span>
      </button>

      <button
        type="button"
        class="nav-item"
        class:active={activeNav === 'oak_espiao'}
        onclick={() => (activeNav = 'oak_espiao')}
      >
        <span class="nav-icon">🕵️</span>
        <span>Espiar Concorrentes</span>
      </button>

      <button
        type="button"
        class="nav-item"
        class:active={activeNav === 'oak_mcp'}
        onclick={() => (activeNav = 'oak_mcp')}
      >
        <span class="nav-icon">🔌</span>
        <span>Segmentação Meta MCP</span>
      </button>

      <button
        type="button"
        class="nav-item"
        class:active={activeNav === 'oak_benchmarks'}
        onclick={() => (activeNav = 'oak_benchmarks')}
      >
        <span class="nav-icon">📚</span>
        <span>Benchmarks & Copy</span>
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
        <span>Simulador Visual IA</span>
      </button>

      <div class="nav-group-label">Copiloto & Sistema</div>

      <button
        type="button"
        class="nav-item"
        class:active={showChatDrawer}
        onclick={() => (showChatDrawer = !showChatDrawer)}
        title="Abrir Assistente Copiloto IA (Gaveta Lateral)"
      >
        <span class="nav-icon">💬</span>
        <span>Assistente IA Copilot</span>
      </button>

      <button
        type="button"
        class="nav-item"
        class:active={activeNav === 'configuracoes'}
        onclick={() => (activeNav = 'configuracoes')}
      >
        <span class="nav-icon">⚙️</span>
        <span>Configurações & Contas</span>
      </button>
    </nav>

    <!-- RODAPÉ DA SIDEBAR: MOTOR OPENCODE GRÁTIS + BACKEND -->
    <div class="sidebar-footer-minimal">
      <div class="status-dot-row">
        <span class="engine-dot-status ready"></span>
        <span class="foot-text">⚡ OpenCode (Modelos Grátis)</span>
      </div>
      <div class="status-dot-row sub-status">
        <span class="engine-dot-status" class:ready={apiOnline}></span>
        <span class="foot-text">Backend 8010 {apiOnline ? 'Online' : 'Offline'}</span>
      </div>
    </div>
  </aside>

  <!-- 2. ÁREA CENTRAL DE TRABALHO: 100% LIMPA, ZERO POLUIÇÃO NO TOPO -->
  <div class="workspace">
    {#if toastMessage}
      <div class="toast-bar" class:error={toastType === 'error'}>
        <span>{toastType === 'error' ? '⚠️' : '✅'} {toastMessage}</span>
        <button type="button" onclick={() => (toastMessage = '')}>✕</button>
      </div>
    {/if}

    <!-- CONTEÚDO PRINCIPAL (1 VISÃO LIMPA POR VEZ) -->
    <main class="canvas">
      {#if activeNav === 'dashboard'}
        <!-- VISÃO 1: GERENCIADOR DE ANÚNCIOS (TABELA OFICIAL EM 3 NÍVEIS + FILTROS META ADS) -->
        <div class="view-header">
          <div>
            <h1>Gerenciador de Anúncios</h1>
            <p>Controle oficial de Campanhas, Conjuntos e Anúncios com filtros avançados e sincronização Graph API.</p>
          </div>
          <div class="view-header-right">
            <button type="button" class="btn-cta" onclick={() => (activeNav = 'assistida')}>
              🪄 + Nova Campanha
            </button>
          </div>
        </div>

        <!-- BARRA DOS 3 NÍVEIS OFICIAIS DO GERENCIADOR DE ANÚNCIOS (CAMPANHAS / CONJUNTOS / ANÚNCIOS) -->
        <div class="meta-manager-level-tabs">
          <button
            type="button"
            class="level-tab-btn"
            class:active={activeLevelTab === 'campaigns'}
            onclick={() => (activeLevelTab = 'campaigns')}
          >
            <span class="tab-level-icon">📊</span>
            <span class="tab-level-text">Campanhas</span>
            <span class="tab-level-badge">{campanhas.length}</span>
          </button>
          <button
            type="button"
            class="level-tab-btn"
            class:active={activeLevelTab === 'adsets'}
            onclick={() => (activeLevelTab = 'adsets')}
          >
            <span class="tab-level-icon">📁</span>
            <span class="tab-level-text">Conjuntos de Anúncios</span>
            <span class="tab-level-badge">{adsets.length}</span>
          </button>
          <button
            type="button"
            class="level-tab-btn"
            class:active={activeLevelTab === 'ads'}
            onclick={() => (activeLevelTab = 'ads')}
          >
            <span class="tab-level-icon">📢</span>
            <span class="tab-level-text">Anúncios</span>
            <span class="tab-level-badge">{ads.length}</span>
          </button>
        </div>

        <!-- PAINEL PRINCIPAL DO GERENCIADOR DE ANÚNCIOS -->
        <section class="panel-card">
          <div class="panel-head">
            <div>
              {#if activeLevelTab === 'campaigns'}
                <h2>Campanhas Meta Ads ({campanhasFiltradas.length} de {campanhas.length})</h2>
              {:else if activeLevelTab === 'adsets'}
                <h2>Conjuntos de Anúncios ({adsetsFiltrados.length} de {adsets.length})</h2>
              {:else}
                <h2>Anúncios ({adsFiltrados.length} de {ads.length})</h2>
              {/if}
              <span class="panel-sub">
                {connection.somente_dados_reais ? 'Exibindo dados reais da Conta Meta' : 'Sincronizado com Meta Graph API & Sistema'}
              </span>
            </div>
            <div class="adsmanager-head-actions">
              <a
                href={connection.selected_account_id ? `https://adsmanager.facebook.com/adsmanager/manage/${activeLevelTab}?act=${connection.selected_account_id.replace('act_', '')}` : 'https://adsmanager.facebook.com/'}
                target="_blank"
                rel="noopener noreferrer"
                class="btn-top ghost"
                title="Abrir no Gerenciador de Anúncios oficial"
              >
                ↗️ Abrir Gerenciador Meta
              </a>
              <button type="button" class="btn-top ghost" onclick={carregarTudo} title="Atualizar dados e métricas agora">
                🔄 Atualizar
              </button>
              <button type="button" class="btn-cta" onclick={() => (activeNav = 'assistida')}>
                🪄 + Nova Campanha
              </button>
            </div>
          </div>

          <!-- BARRA DE FERRAMENTAS DO GERENCIADOR (FILTROS COMPLETOS DO GERENCIADOR DE ANÚNCIOS) -->
          <div class="adsmanager-toolbar">
            <div class="adsmanager-toolbar-filters">
              <!-- Filtro 1: Status da Veiculação (Todas, Ativas, Pausadas) -->
              <div class="status-filter-pills">
                <button
                  type="button"
                  class="filter-pill"
                  class:active={(activeLevelTab === 'campaigns' ? filtroStatus : (activeLevelTab === 'adsets' ? filtroStatusAdset : filtroStatusAd)) === 'TODAS'}
                  onclick={() => {
                    if (activeLevelTab === 'campaigns') filtroStatus = 'TODAS';
                    else if (activeLevelTab === 'adsets') filtroStatusAdset = 'TODAS';
                    else filtroStatusAd = 'TODAS';
                  }}
                >
                  Todos ({activeLevelTab === 'campaigns' ? campanhas.length : (activeLevelTab === 'adsets' ? adsets.length : ads.length)})
                </button>
                <button
                  type="button"
                  class="filter-pill"
                  class:active={(activeLevelTab === 'campaigns' ? filtroStatus : (activeLevelTab === 'adsets' ? filtroStatusAdset : filtroStatusAd)) === 'ACTIVE'}
                  onclick={() => {
                    if (activeLevelTab === 'campaigns') filtroStatus = 'ACTIVE';
                    else if (activeLevelTab === 'adsets') filtroStatusAdset = 'ACTIVE';
                    else filtroStatusAd = 'ACTIVE';
                  }}
                >
                  🟢 Ativos
                </button>
                <button
                  type="button"
                  class="filter-pill"
                  class:active={(activeLevelTab === 'campaigns' ? filtroStatus : (activeLevelTab === 'adsets' ? filtroStatusAdset : filtroStatusAd)) === 'PAUSED'}
                  onclick={() => {
                    if (activeLevelTab === 'campaigns') filtroStatus = 'PAUSED';
                    else if (activeLevelTab === 'adsets') filtroStatusAdset = 'PAUSED';
                    else filtroStatusAd = 'PAUSED';
                  }}
                >
                  ⏸️ Pausados
                </button>
              </div>

              <!-- Filtro 2: Objetivo da Campanha -->
              <select bind:value={filtroObjetivo} class="filter-select" title="Filtrar por objetivo de veiculação da Meta">
                <option value="TODOS">🎯 Objetivo: Todos</option>
                <option value="LEAD">🎯 Cadastros / Leads</option>
                <option value="SALE">🛒 Vendas / Conversões</option>
                <option value="TRAFFIC">🌐 Tráfego no Site</option>
                <option value="ENGAGEMENT">💬 Engajamento / WhatsApp</option>
                <option value="AWARENESS">📣 Reconhecimento de Marca</option>
              </select>

              <!-- Filtro 3: Tipo de Orçamento (Advantage+ CBO vs ABO) -->
              <select bind:value={filtroTipoOrcamento} class="filter-select" title="Estratégia de orçamento">
                <option value="TODOS">💰 Orçamento: Todos</option>
                <option value="CBO">Advantage+ (CBO)</option>
                <option value="ABO">Por Conjunto (ABO)</option>
              </select>

              <!-- Filtro 4: Desempenho / Saúde da IA -->
              <select bind:value={filtroSaude} class="filter-select" title="Classificação de saúde da IA">
                <option value="TODOS">🏷️ Desempenho: Todos</option>
                <option value="WINNER">🏆 Winners (Escalar)</option>
                <option value="BLEEDER">🩸 Bleeders (Sangradores)</option>
                <option value="REAL">🟢 Conta Real</option>
              </select>

              <!-- Filtro 5: Janela de Atribuição -->
              <select bind:value={filtroPeriodo} class="filter-select" title="Janela de atribuição">
                <option value="7d">📅 Últimos 7 dias</option>
                <option value="14d">📅 Últimos 14 dias</option>
                <option value="30d">📅 Últimos 30 dias</option>
                <option value="hoje">📅 Hoje</option>
                <option value="max">📅 Todo o Período</option>
              </select>

              {#if filtroStatus !== 'TODAS' || filtroStatusAdset !== 'TODAS' || filtroStatusAd !== 'TODAS' || filtroObjetivo !== 'TODOS' || filtroTipoOrcamento !== 'TODOS' || filtroSaude !== 'TODOS' || buscaCampanha || buscaAdset || buscaAd}
                <button type="button" class="btn-clear-filters" onclick={limparFiltrosGerenciador} title="Limpar todos os filtros">
                  ✕ Limpar Filtros
                </button>
              {/if}
            </div>

            <div class="search-box">
              {#if activeLevelTab === 'campaigns'}
                <input
                  type="text"
                  placeholder="🔍 Pesquisar campanha por nome, ID ou cidade..."
                  bind:value={buscaCampanha}
                />
                {#if buscaCampanha}
                  <button type="button" class="search-clear" onclick={() => (buscaCampanha = '')}>✕</button>
                {/if}
              {:else if activeLevelTab === 'adsets'}
                <input
                  type="text"
                  placeholder="🔍 Pesquisar conjunto por nome, cidade ou ID..."
                  bind:value={buscaAdset}
                />
                {#if buscaAdset}
                  <button type="button" class="search-clear" onclick={() => (buscaAdset = '')}>✕</button>
                {/if}
              {:else}
                <input
                  type="text"
                  placeholder="🔍 Pesquisar anúncio por título, copy ou ID..."
                  bind:value={buscaAd}
                />
                {#if buscaAd}
                  <button type="button" class="search-clear" onclick={() => (buscaAd = '')}>✕</button>
                {/if}
              {/if}
            </div>
          </div>

          <!-- NÍVEL 1: TABELA DE CAMPANHAS -->
          {#if activeLevelTab === 'campaigns'}
            {#if campanhasFiltradas.length === 0}
              <div class="empty-state">
                {#if campanhas.length === 0}
                  <h3>Nenhuma campanha carregada neste momento</h3>
                  <p>Crie uma campanha em <strong>🪄 Criação Assistida</strong> ou conecte sua Conta Meta.</p>
                  <div class="empty-actions">
                    <button type="button" class="btn-cta" onclick={() => (activeNav = 'assistida')}>
                      🪄 Criar Campanha Assistida Agora
                    </button>
                  </div>
                {:else}
                  <h3>Nenhuma campanha encontrada com o filtro atual</h3>
                  <p>Altere o filtro de status ou limpe o termo pesquisado.</p>
                  <div class="empty-actions">
                    <button type="button" class="btn-top ghost" onclick={() => { filtroStatus = 'TODAS'; buscaCampanha = ''; }}>
                      Limpar Filtros
                    </button>
                  </div>
                {/if}
              </div>
            {:else}
              <div class="table-scroll">
                <table class="clean-table ads-manager-table">
                  <thead>
                    <tr>
                      <th style="width: 70px;">Status</th>
                      <th>Campanha</th>
                      <th>Orçamento</th>
                      <th class="num">Gasto 7d</th>
                      <th class="num">CTR</th>
                      <th class="num">CPA</th>
                      <th class="num">ROAS</th>
                      <th>Diagnóstico IA</th>
                      <th class="right">Ações</th>
                    </tr>
                  </thead>
                  <tbody>
                    {#each campanhasFiltradas as camp}
                      <tr class:row-paused={camp.status === 'PAUSED'}>
                        <td>
                          <button
                            type="button"
                            class="toggle-switch"
                            class:on={camp.status === 'ACTIVE'}
                            onclick={() => alternarStatusCampanha(camp)}
                            title={camp.status === 'ACTIVE' ? 'Clique para PAUSAR a veiculação' : 'Clique para ATIVAR a veiculação'}
                            aria-label={`Status da campanha: ${camp.status}`}
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
                            {#if camp.id}
                              <code class="camp-id-code">ID: {camp.id}</code>
                            {/if}
                          </div>
                        </td>
                        <td>
                          <div class="budget-cell">
                            <strong>R$ {camp.daily_budget.toFixed(2)}</strong><span class="c-sub">/dia</span>
                            <button
                              type="button"
                              class="btn-edit-budget"
                              onclick={() => editarOrcamentoPrompt(camp)}
                              title="Editar orçamento diário da campanha"
                            >
                              ✏️
                            </button>
                          </div>
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
                            <button
                              type="button"
                              class="mini-btn"
                              onclick={() => alternarStatusCampanha(camp)}
                              title={camp.status === 'ACTIVE' ? 'Pausar campanha' : 'Ativar campanha'}
                            >
                              {camp.status === 'ACTIVE' ? '⏸️ Pausar' : '▶️ Ativar'}
                            </button>
                            <button
                              type="button"
                              class="mini-btn up"
                              onclick={() => escalarOrcamento(camp, 1.2)}
                              title="Aumentar orçamento em +20%"
                            >
                              +20%
                            </button>
                            <button
                              type="button"
                              class="mini-btn down"
                              onclick={() => escalarOrcamento(camp, 0.8)}
                              title="Reduzir orçamento em -20%"
                            >
                              -20%
                            </button>
                            <button
                              type="button"
                              class="mini-btn dup"
                              onclick={() => duplicarCampanha(camp)}
                              title="Duplicar esta campanha"
                            >
                              📋 Duplicar
                            </button>
                            <button
                              type="button"
                              class="mini-btn del"
                              onclick={() => excluirCampanha(camp)}
                              title="Excluir campanha da conta"
                            >
                              🗑️
                            </button>
                          </div>
                        </td>
                      </tr>
                    {/each}
                  </tbody>
                </table>
              </div>
            {/if}

          <!-- NÍVEL 2: TABELA DE CONJUNTOS DE ANÚNCIOS (ADSETS) -->
          {:else if activeLevelTab === 'adsets'}
            {#if adsetsFiltrados.length === 0}
              <div class="empty-state">
                <h3>Nenhum conjunto de anúncios encontrado</h3>
                <p>Crie uma campanha na <strong>🪄 Criação Assistida</strong> ou ajuste o filtro.</p>
                <div class="empty-actions">
                  <button type="button" class="btn-top ghost" onclick={() => { filtroStatusAdset = 'TODAS'; buscaAdset = ''; }}>
                    Limpar Filtros
                  </button>
                </div>
              </div>
            {:else}
              <div class="table-scroll">
                <table class="clean-table ads-manager-table">
                  <thead>
                    <tr>
                      <th style="width: 70px;">Status</th>
                      <th>Conjunto de Anúncios</th>
                      <th>Campanha Pai</th>
                      <th>Orçamento</th>
                      <th>Otimização</th>
                      <th>Segmentação</th>
                      <th class="num">Gasto</th>
                      <th class="num">Resultados</th>
                      <th class="right">Ações</th>
                    </tr>
                  </thead>
                  <tbody>
                    {#each adsetsFiltrados as adset}
                      <tr class:row-paused={adset.status === 'PAUSED'}>
                        <td>
                          <button
                            type="button"
                            class="toggle-switch"
                            class:on={adset.status === 'ACTIVE'}
                            onclick={() => alternarStatusAdset(adset)}
                            title={adset.status === 'ACTIVE' ? 'Clique para PAUSAR o conjunto' : 'Clique para ATIVAR o conjunto'}
                            aria-label={`Status do conjunto: ${adset.status}`}
                          >
                            <span class="knob"></span>
                          </button>
                        </td>
                        <td>
                          <div class="c-name">{adset.name}</div>
                          <div class="c-sub">
                            <span class="origin-tag" class:real={adset.is_real}>
                              {adset.is_real ? 'CONTA REAL' : 'SISTEMA'}
                            </span>
                            {#if adset.id}
                              <code class="camp-id-code">ID: {adset.id}</code>
                            {/if}
                          </div>
                        </td>
                        <td>
                          <div class="c-sub" style="font-weight: 550; color: #cbd5e1;">{adset.campaign_name || '—'}</div>
                        </td>
                        <td>
                          {#if adset.daily_budget > 0}
                            <div class="budget-cell">
                              <strong>R$ {adset.daily_budget.toFixed(2)}</strong><span class="c-sub">/dia</span>
                            </div>
                          {:else}
                            <span class="btype-pill">CBO (Campanha)</span>
                          {/if}
                        </td>
                        <td>
                          <span class="opt-goal-badge">{adset.optimization_goal}</span>
                          <div class="c-sub">Cobrança: {adset.billing_event}</div>
                        </td>
                        <td>
                          <div class="c-sub">📍 {(adset.locations || []).join(', ')}</div>
                          <div class="c-sub">🎂 {adset.min_age} - {adset.max_age} anos</div>
                        </td>
                        <td class="num">R$ {adset.spend.toFixed(2)}</td>
                        <td class="num">
                          <strong>{adset.conversions}</strong>
                          <div class="c-sub">CPA: R$ {adset.cpa.toFixed(2)}</div>
                        </td>
                        <td class="right">
                          <div class="row-actions">
                            <button
                              type="button"
                              class="mini-btn"
                              onclick={() => alternarStatusAdset(adset)}
                              title={adset.status === 'ACTIVE' ? 'Pausar conjunto' : 'Ativar conjunto'}
                            >
                              {adset.status === 'ACTIVE' ? '⏸️ Pausar' : '▶️ Ativar'}
                            </button>
                            <button
                              type="button"
                              class="mini-btn del"
                              onclick={() => excluirAdset(adset)}
                              title="Excluir conjunto"
                            >
                              🗑️
                            </button>
                          </div>
                        </td>
                      </tr>
                    {/each}
                  </tbody>
                </table>
              </div>
            {/if}

          <!-- NÍVEL 3: TABELA DE ANÚNCIOS (ADS COM PRÉVIA VISUAL DO CRIATIVO) -->
          {:else}
            {#if adsFiltrados.length === 0}
              <div class="empty-state">
                <h3>Nenhum anúncio encontrado</h3>
                <p>Crie uma campanha na <strong>🪄 Criação Assistida</strong> para gerar os criativos e anúncios.</p>
                <div class="empty-actions">
                  <button type="button" class="btn-cta" onclick={() => (activeNav = 'assistida')}>
                    🪄 Criar Anúncios Assistidos
                  </button>
                </div>
              </div>
            {:else}
              <div class="table-scroll">
                <table class="clean-table ads-manager-table">
                  <thead>
                    <tr>
                      <th style="width: 70px;">Status</th>
                      <th style="width: 54px;">Criativo</th>
                      <th>Anúncio</th>
                      <th>Título & Copy</th>
                      <th>CTA</th>
                      <th class="num">Gasto</th>
                      <th class="num">CTR</th>
                      <th class="num">Conversões</th>
                      <th class="right">Ações</th>
                    </tr>
                  </thead>
                  <tbody>
                    {#each adsFiltrados as ad}
                      <tr class:row-paused={ad.status === 'PAUSED'}>
                        <td>
                          <button
                            type="button"
                            class="toggle-switch"
                            class:on={ad.status === 'ACTIVE'}
                            onclick={() => alternarStatusAd(ad)}
                            title={ad.status === 'ACTIVE' ? 'Clique para PAUSAR o anúncio' : 'Clique para ATIVAR o anúncio'}
                            aria-label={`Status do anúncio: ${ad.status}`}
                          >
                            <span class="knob"></span>
                          </button>
                        </td>
                        <td>
                          <div
                            class="ad-thumb-box"
                            onclick={() => abrirModalCriativo(ad)}
                            title="Clique para ver a prévia completa deste criativo"
                            role="button"
                            tabindex="0"
                            onkeydown={(e) => { if (e.key === 'Enter') abrirModalCriativo(ad); }}
                          >
                            {#if ad.image_url}
                              <img src={ad.image_url} alt={ad.name} class="ad-thumb-img" />
                            {:else if ad.creative_file}
                              <img
                                src={`/api/criativos/arquivo/${ad.creative_file}`}
                                alt={ad.name}
                                class="ad-thumb-img"
                                onerror={(e) => { e.currentTarget.style.display = 'none'; e.currentTarget.nextElementSibling.style.display = 'flex'; }}
                              />
                              <div class="ad-thumb-fallback" style="display: none;">🎨</div>
                            {:else}
                              <div class="ad-thumb-fallback">🖼️</div>
                            {/if}
                          </div>
                        </td>
                        <td>
                          <div class="c-name">{ad.name}</div>
                          <div class="c-sub">
                            <span class="origin-tag" class:real={ad.is_real}>
                              {ad.is_real ? 'CONTA REAL' : 'SISTEMA'}
                            </span>
                            · 📁 {ad.adset_name || 'Conjunto'}
                            {#if ad.id}
                              <code class="camp-id-code">ID: {ad.id}</code>
                            {/if}
                          </div>
                        </td>
                        <td class="ad-copy-cell">
                          <div class="ad-copy-title" title={ad.headline}>{ad.headline}</div>
                          <div class="ad-copy-snippet" title={ad.primary_text}>{ad.primary_text}</div>
                        </td>
                        <td>
                          <span class="cta-badge">{ad.call_to_action === 'LEARN_MORE' ? 'Saiba Mais' : ad.call_to_action}</span>
                        </td>
                        <td class="num">R$ {ad.spend.toFixed(2)}</td>
                        <td class="num">{ad.ctr}%</td>
                        <td class="num">
                          <strong>{ad.conversions}</strong>
                          <div class="c-sub">CPA: R$ {ad.cpa.toFixed(2)}</div>
                        </td>
                        <td class="right">
                          <div class="row-actions">
                            <button
                              type="button"
                              class="mini-btn preview"
                              onclick={() => abrirModalCriativo(ad)}
                              title="Visualizar criativo e texto no formato de anúncio"
                            >
                              👁️ Prévia
                            </button>
                            <button
                              type="button"
                              class="mini-btn"
                              onclick={() => alternarStatusAd(ad)}
                              title={ad.status === 'ACTIVE' ? 'Pausar anúncio' : 'Ativar anúncio'}
                            >
                              {ad.status === 'ACTIVE' ? '⏸️' : '▶️'}
                            </button>
                            <button
                              type="button"
                              class="mini-btn del"
                              onclick={() => excluirAd(ad)}
                              title="Excluir anúncio"
                            >
                              🗑️
                            </button>
                          </div>
                        </td>
                      </tr>
                    {/each}
                  </tbody>
                </table>
              </div>
            {/if}
          {/if}
        </section>

      {:else if activeNav === 'relatorios'}
        <!-- VISÃO DEDICADA: RELATÓRIOS & EVOLUÇÃO DIÁRIA (Extraído da Dashboard) -->
        <div class="view-header">
          <div>
            <h1>📈 Relatórios & Performance Diária</h1>
            <p>Análise consolidada de investimento, pacing diário, conversões, ROAS e curva de evolução dos últimos 14 dias.</p>
          </div>
          <div class="view-header-right">
            <button type="button" class="btn-top ghost" onclick={carregarTudo} title="Atualizar dados analíticos">
              🔄 Atualizar Dados
            </button>
          </div>
        </div>

        {#if copilot}
          <!-- CARDS DE MÉTRICAS CONSOLIDADAS -->
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

        <!-- GRÁFICO DE EVOLUÇÃO DIÁRIA -->
        <section class="panel-card">
          <div class="panel-head">
            <div>
              <h2>Evolução Diária (Últimos 14 dias)</h2>
              <span class="panel-sub">Curva diária de desempenho com base nos dados sincronizados da conta.</span>
            </div>
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

        <!-- TABELA ANALÍTICA DIA A DIA -->
        <section class="panel-card">
          <div class="panel-head">
            <div>
              <h2>Detalhamento Diário Analítico</h2>
              <span class="panel-sub">Registro histórico de cada dia com valor investido, conversões apuradas e retorno.</span>
            </div>
          </div>

          <div class="table-scroll">
            <table class="clean-table ads-manager-table">
              <thead>
                <tr>
                  <th>Dia / Janela</th>
                  <th class="num">Investimento</th>
                  <th class="num">Conversões</th>
                  <th class="num">CPA Estimado</th>
                  <th class="num">ROAS</th>
                  <th>Status do Ritmo (Pacing)</th>
                </tr>
              </thead>
              <tbody>
                {#each serieGrafico as item}
                  {@const cpaDia = item.conversions ? (item.spend / item.conversions).toFixed(2) : '0.00'}
                  <tr>
                    <td>
                      <strong>{item.label}</strong>
                      <div class="c-sub">Janela de atribuição 7d clique / 1d visualização</div>
                    </td>
                    <td class="num"><strong>R$ {item.spend.toFixed(2)}</strong></td>
                    <td class="num">{item.conversions}</td>
                    <td class="num">R$ {cpaDia}</td>
                    <td class="num strong-roas">{item.roas}x</td>
                    <td>
                      <span class="health-pill success">🟢 Em conformidade</span>
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        </section>

        <!-- ALERTAS DE FADIGA E RECOMENDAÇÕES DE OTIMIZAÇÃO -->
        {#if copilot && copilot.fatigue_alerts && copilot.fatigue_alerts.length > 0}
          <section class="panel-card" style="margin-top: 20px;">
            <div class="panel-head">
              <div>
                <h2>⚠️ Alertas de Fadiga Criativa Detectados</h2>
                <span class="panel-sub">Campanhas com queda de CTR superior a 20% nos últimos 7 dias.</span>
              </div>
            </div>
            <div class="fatigue-list">
              {#each copilot.fatigue_alerts as fat}
                <div class="fatigue-card">
                  <div class="fatigue-head">
                    <strong>{fat.campaign_name}</strong>
                    <span class="fatigue-tag">Queda de CTR: -{fat.drop_pct}%</span>
                  </div>
                  <div class="c-sub" style="margin-top: 4px;">
                    CTR Inicial: {fat.start_ctr}% → CTR Atual: {fat.end_ctr}%
                  </div>
                  <div class="c-sub" style="color: #38bdf8; margin-top: 6px;">
                    💡 Ação recomendada: {fat.acao_sugerida}
                  </div>
                </div>
              {/each}
            </div>
          </section>
        {/if}

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
                {#if planoAssistido.anuncios?.[0]}
                  <div class="field full">
                    <label for="f-upload-step1">📤 Criativo do Anúncio (Subir Imagem ou Vídeo)</label>
                    <div class="creative-upload-row">
                      <label class="btn-upload-creative" for="f-upload-step1">
                        {subindoCriativo
                          ? '⏳ Enviando arquivo...'
                          : '📤 Subir Imagem ou Vídeo (.png, .jpg, .mp4, .mov)'}
                      </label>
                      <input
                        id="f-upload-step1"
                        type="file"
                        accept=".png,.jpg,.jpeg,.webp,.mp4,.mov,.webm"
                        multiple
                        onchange={uploadArquivoCriativo}
                        hidden
                      />
                      <select class="creative-select-inline" bind:value={planoAssistido.anuncios[0].arquivo_criativo}>
                        {#if criativosLista.length === 0}
                          <option value="criativo_repasse_curitiba.png">criativo_repasse_curitiba.png</option>
                        {:else}
                          {#each criativosLista as arq}
                            <option value={arq.nome}>
                              {ehVideoCriativo(arq.nome) ? '🎬' : '🖼️'} {arq.nome}
                            </option>
                          {/each}
                        {/if}
                      </select>
                    </div>
                  </div>
                {/if}
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
              <h2>Etapa 3 de 4 — Copywriter & Mídia do Anúncio (Imagem ou Vídeo)</h2>
              {#if planoAssistido.anuncios?.[0]}
                <div class="form-grid">
                  <div class="field full">
                    <label for="f-upload-step3">📤 Enviar Criativo do Computador (Imagem ou Vídeo)</label>
                    <div class="creative-upload-dropzone">
                      <label class="btn-upload-creative primary-upload" for="f-upload-step3">
                        {subindoCriativo
                          ? '⏳ Enviando Criativo...'
                          : '📤 Escolher Arquivo de Vídeo ou Imagem (.mp4, .mov, .png, .jpg, .webp)'}
                      </label>
                      <input
                        id="f-upload-step3"
                        type="file"
                        accept=".png,.jpg,.jpeg,.webp,.mp4,.mov,.webm"
                        multiple
                        onchange={uploadArquivoCriativo}
                        hidden
                      />
                      <span class="upload-sub-hint">
                        Selecionado: <strong>{planoAssistido.anuncios[0].arquivo_criativo}</strong>
                        ({ehVideoCriativo(planoAssistido.anuncios[0].arquivo_criativo) ? 'Vídeo' : 'Imagem'})
                      </span>
                    </div>
                  </div>
                  <div class="field">
                    <label for="f-adname">Nome do Anúncio</label>
                    <input id="f-adname" type="text" bind:value={planoAssistido.anuncios[0].nome} />
                  </div>
                  <div class="field">
                    <label for="f-media">Criativo Selecionado na Biblioteca</label>
                    <select
                      id="f-media"
                      bind:value={planoAssistido.anuncios[0].arquivo_criativo}
                      onchange={(e) => {
                        planoAssistido.anuncios[0].formato = ehVideoCriativo(e.target.value)
                          ? 'video'
                          : 'imagem_unica';
                      }}
                    >
                      {#if criativosLista.length === 0}
                        <option value="criativo_repasse_curitiba.png">criativo_repasse_curitiba.png</option>
                      {:else}
                        {#each criativosLista as arq}
                          <option value={arq.nome}>
                            {ehVideoCriativo(arq.nome) ? '🎬 Vídeo:' : '🖼️ Imagem:'} {arq.nome}
                          </option>
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
                  <span>Criativo (Mídia)</span>
                  <strong>
                    {ehVideoCriativo(planoAssistido.anuncios?.[0]?.arquivo_criativo) ? '🎬 Vídeo' : '🖼️ Imagem'}:
                    {planoAssistido.anuncios?.[0]?.arquivo_criativo}
                  </strong>
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

              {#if ultimaCampanhaRealCriada}
                <div class="real-created-banner">
                  <div>
                    <strong>✅ Criada no Gerenciador Real:</strong>
                    ID Campanha <code>{ultimaCampanhaRealCriada.campaign_id}</code>
                    {#if ultimaCampanhaRealCriada.adset_id}
                      · Conjunto <code>{ultimaCampanhaRealCriada.adset_id}</code>
                    {/if}
                    em <strong>{ultimaCampanhaRealCriada.account_name} ({ultimaCampanhaRealCriada.account_id})</strong>
                  </div>
                  {#if ultimaCampanhaRealCriada.ads_manager_url}
                    <a
                      class="btn-open-real-ads"
                      href={ultimaCampanhaRealCriada.ads_manager_url}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      🌐 Abrir Campanha no Meu Gerenciador Real ↗
                    </a>
                  {/if}
                </div>
              {/if}

              <div class="launch-stack">
                <button
                  type="button"
                  class="btn-launch primary"
                  onclick={criarCampanhaAssistidaNavegador}
                  disabled={abrindoNavegador}
                >
                  {abrindoNavegador
                    ? '🖱️ Criando na Conta Real + Iniciando Agente...'
                    : '🖱️ Criar de Forma Assistida no Gerenciador (Cria Real + Ver Mouse)'}
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
            <div class="preview-head-row">
              <h2>Prévia em Tempo Real (Feed Instagram / Facebook)</h2>
              <label class="btn-quick-upload" for="f-upload-preview">
                {subindoCriativo ? '⏳ Subindo...' : '📤 Subir Vídeo / Imagem'}
              </label>
              <input
                id="f-upload-preview"
                type="file"
                accept=".png,.jpg,.jpeg,.webp,.mp4,.mov,.webm"
                multiple
                onchange={uploadArquivoCriativo}
                hidden
              />
            </div>
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
                {#if temArquivoRealNaPasta(planoAssistido.anuncios?.[0]?.arquivo_criativo)}
                  {#if ehVideoCriativo(planoAssistido.anuncios?.[0]?.arquivo_criativo)}
                    <video
                      class="ig-media-real"
                      src={`/api/criativos/arquivo/${encodeURIComponent(planoAssistido.anuncios[0].arquivo_criativo)}`}
                      controls
                      muted
                      autoplay
                      loop
                      playsinline
                    ></video>
                  {:else}
                    <img
                      class="ig-media-real"
                      src={`/api/criativos/arquivo/${encodeURIComponent(planoAssistido.anuncios[0].arquivo_criativo)}`}
                      alt={planoAssistido.anuncios[0].arquivo_criativo}
                    />
                  {/if}
                {/if}
                <div class="ig-media-badge">
                  {ehVideoCriativo(planoAssistido.anuncios?.[0]?.arquivo_criativo) ? '🎬' : '🖼️'}
                  {planoAssistido.anuncios?.[0]?.arquivo_criativo || 'criativo.png'}
                </div>
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
        <!-- SEÇÃO DEDICADA: ROBÔ OTIMIZADOR (WINNERS VS BLEEDERS) -->
        <div class="view-header">
          <div>
            <h1>🤖 Robô Otimizador (Scale & Kill)</h1>
            <p>Diagnóstico automático de campanhas para escalar campeãs e pausar desperdício de orçamento.</p>
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

      {:else if activeNav === 'publicos'}
        <!-- SEÇÃO DEDICADA: LOJA DE PÚBLICOS PRONTOS -->
        <div class="view-header">
          <div>
            <h1>👥 Loja de Públicos Prontos</h1>
            <p>Catálogo de públicos validados para aplicar em 1 clique na Criação de Campanha Assistida.</p>
          </div>
        </div>

        <section class="panel-card">
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

      {:else if activeNav.startsWith('oak_')}
        <!-- SEÇÕES DEDICADAS DO OPENADKIT & PIPEBOARD MCP (1 FUNÇÃO POR PÁGINA, SEM SUB-ABAS) -->
        <OpenAdKitStudio
          secao={activeNav}
          bind:planoAssistido
          onIrParaSecao={(novaSecao) => (activeNav = novaSecao)}
          onAplicarNaCampanha={() => {
            activeNav = 'assistida';
            etapaAssistida = 3;
          }}
          onNotificar={notify}
        />

      {:else if activeNav === 'automacao'}
        <!-- SEÇÃO DEDICADA: SIMULADOR VISUAL NO GERENCIADOR DE ANÚNCIOS -->
        <div class="view-header">
          <div>
            <h1>🖱️ Simulador Visual no Gerenciador de Anúncios</h1>
            <p>Acompanhe o cursor da IA clicando e preenchendo cada etapa da campanha em tempo real.</p>
          </div>
        </div>

        <SimuladorMetaAds
          bind:this={simuladorRef}
          plano={planoAssistido}
          criativos={criativosLista}
          autoStart={true}
        />

      {:else if activeNav === 'configuracoes'}
        <!-- SEÇÃO DEDICADA: CONFIGURAÇÕES & CONTAS & MOTOR DE IA -->
        <div class="view-header">
          <div>
            <h1>⚙️ Configurações & Contas</h1>
            <p>Gerencie sua Business Manager (BM), contas de anúncios Meta, tokens de acesso e motor de IA ativo.</p>
          </div>
          <div class="header-actions-right">
            <button
              type="button"
              class="btn-cta"
              onclick={() => (activeNav = 'dashboard')}
            >
              📊 Voltar à Dashboard
            </button>
          </div>
        </div>

        <div class="settings-view">
          <!-- CARD 1: CONTAS META ADS & BUSINESS MANAGER -->
          <section class="panel-card settings-card">
            <div class="panel-head">
              <div>
                <h2>🏢 Gerenciador de Negócios & Contas Meta Ads</h2>
                <span class="panel-sub">Sincronização oficial com a Meta Graph API v22.0</span>
              </div>
              <span class="conn-badge" class:connected={connection.connected}>
                {connection.connected ? '🟢 Conectado' : '🟡 Modo Demonstração'}
              </span>
            </div>

            <div class="settings-content-grid">
              <div class="info-block">
                <span class="info-label">Business Manager (BM):</span>
                <span class="info-val strong">{connection.business_name || 'Não identificado'}</span>
              </div>

              <div class="info-block">
                <span class="info-label">Conta Selecionada:</span>
                <span class="info-val">
                  <strong>{connection.selected_account_name || 'Conta dos anúncios'}</strong>
                  <code class="act-pill">{connection.selected_account_id || 'act_3339104319737592'}</code>
                </span>
              </div>

              {#if connection.available_accounts?.length > 0}
                <div class="info-block">
                  <label for="cfg-select-acc" class="info-label">Trocar Conta Ativa:</label>
                  <select id="cfg-select-acc" class="settings-select" value={connection.selected_account_id} onchange={trocarContaAtiva}>
                    {#each connection.available_accounts as acc}
                      <option value={acc.id}>
                        {acc.account_status === 1 ? '🟢' : '⚠️'} {acc.name} ({acc.id})
                      </option>
                    {/each}
                  </select>
                </div>
              {/if}

              <div class="info-block">
                <span class="info-label">Modo de Exibição dos Dados:</span>
                <div class="segmented-mode">
                  <button
                    type="button"
                    class:selected={!connection.somente_dados_reais}
                    onclick={() => definirModoDadosReais(false)}
                  >
                    Demo (Demonstração)
                  </button>
                  <button
                    type="button"
                    class:selected={connection.somente_dados_reais}
                    onclick={() => definirModoDadosReais(true)}
                  >
                    🔒 Só Reais (Ocultar Demo)
                  </button>
                </div>
              </div>
            </div>

            <div class="settings-actions-row">
              <button
                type="button"
                class="btn-top ghost"
                onclick={sincronizarDoNavegador}
                disabled={conectandoConta}
              >
                🌐 Sincronizar Sessão do Navegador
              </button>

              <button
                type="button"
                class="btn-top primary"
                onclick={() => (showConnectModal = true)}
              >
                🔗 {connection.connected ? 'Alterar Token Meta API' : 'Conectar Token Meta API'}
              </button>

              <a
                href={connection.selected_account_id ? `https://adsmanager.facebook.com/adsmanager/manage/campaigns?act=${connection.selected_account_id.replace('act_', '')}` : 'https://adsmanager.facebook.com/'}
                target="_blank"
                rel="noopener noreferrer"
                class="btn-top ghost"
              >
                ↗️ Abrir no Gerenciador Meta Oficial
              </a>
            </div>
          </section>

          <!-- CARD 2: MOTOR DE INTELIGÊNCIA ARTIFICIAL -->
          <section class="panel-card settings-card">
            <div class="panel-head">
              <div>
                <h2>🤖 Motor de Inteligência Artificial & Automação</h2>
                <span class="panel-sub">Escolha qual modelo gera copies, audiências e orquestra a criação</span>
              </div>
              <span class="engine-tag" class:ready={activeProviderMeta?.configured}>
                {activeProviderMeta?.configured ? '🟢 Motor Pronto' : '🔒 Requer Chave'}
              </span>
            </div>

            <div class="settings-engine-body">
              <div class="field">
                <label for="cfg-engine-active">Motor de IA Ativo no Sistema</label>
                <select id="cfg-engine-active" class="settings-select-large" value={selectedProvider} onchange={aoSelecionarMotorIA}>
                  {#if providers.length === 0}
                    <option value="opencode">OpenCode CLI (Prioritário / Sem Custo)</option>
                    <option value="ollama">IA Local (Ollama - 100% Localhost)</option>
                    <option value="anthropic">Anthropic Claude (Sonnet 4 / 3.5)</option>
                    <option value="openai">OpenAI (GPT-4o / GPT-4.1)</option>
                    <option value="google">Google Gemini (2.5 Flash / Pro)</option>
                  {:else}
                    {#each providers as p}
                      <option value={p.id}>
                        {p.label} {p.requires_api_key ? (p.configured ? '✓ (Chave salva)' : '🔒 (Sem chave)') : '⚡ (Local)'}
                      </option>
                    {/each}
                  {/if}
                </select>
                <small class="hint-small">
                  {#if selectedProvider === 'opencode'}
                    ⚡ <strong>OpenCode CLI:</strong> Execução nativa de alta velocidade e raciocínio de código sem custos de API.
                  {:else if selectedProvider === 'ollama'}
                    🏠 <strong>IA Local Ollama:</strong> Processamento 100% no seu computador (porta 11434). Zero envio de dados para fora.
                  {:else if selectedProvider === 'anthropic'}
                    🧠 <strong>Anthropic Claude:</strong> Máxima persuasão para redação de copies de alta conversão.
                  {:else if selectedProvider === 'openai'}
                    🤖 <strong>OpenAI GPT-4o:</strong> Modelo multimodal para análise rápida de criativos e campanhas.
                  {:else if selectedProvider === 'google'}
                    ✨ <strong>Google Gemini:</strong> Respostas rápidas e janela de contexto estendida.
                  {/if}
                </small>
              </div>

              <div class="engine-buttons-row">
                <button
                  type="button"
                  class="btn-cta"
                  onclick={() => (showApiKeysModal = true)}
                >
                  🔑 Configurar Chaves de API & Modelos (.env)
                </button>
              </div>
            </div>
          </section>

          <!-- CARD 3: STATUS DO SISTEMA E INTEGRAÇÕES -->
          <section class="panel-card settings-card">
            <div class="panel-head">
              <h2>🛠️ Status das Ferramentas & MCP Integrados</h2>
            </div>
            <div class="integrations-list">
              <div class="integ-item">
                <span class="integ-icon">🔌</span>
                <div class="integ-info">
                  <strong>Pipeboard Meta Ads MCP (42 Tools)</strong>
                  <span>Ferramentas oficiais: `adinterest`, `adgeolocation`, `create_campaign`, `update_budget`, `insights`.</span>
                </div>
                <span class="integ-status ok">Ativo</span>
              </div>
              <div class="integ-item">
                <span class="integ-icon">🧰</span>
                <div class="integ-info">
                  <strong>OpenAdKit v1.1 PT-BR</strong>
                  <span>18 geradores, Brand Brain, Creative Score 5 alavancas e espionagem Steal & Beat.</span>
                </div>
                <span class="integ-status ok">Carregado</span>
              </div>
              <div class="integ-item">
                <span class="integ-icon">🚀</span>
                <div class="integ-info">
                  <strong>Backend FastAPI (Porta 8010)</strong>
                  <span>API REST de orquestração com suporte a Graph API v22.0.</span>
                </div>
                <span class="integ-status" class:ok={apiOnline}>{apiOnline ? 'Online' : 'Offline'}</span>
              </div>
            </div>
          </section>
        </div>
      {/if}
    </main>
  </div>
</div>

<!-- GAVETA LATERAL DIREITA (SOB DEMANDA): ASSISTENTE DE CAMPANHAS IA -->
{#if showChatDrawer}
  <div class="modal-backdrop drawer-backdrop" role="presentation" onclick={() => (showChatDrawer = false)}>
    <div
      class="chat-drawer"
      role="dialog"
      tabindex="-1"
      onclick={(e) => e.stopPropagation()}
      onkeydown={(e) => e.key === 'Escape' && (showChatDrawer = false)}
    >
      <div class="dock-header">
        <div>
          <strong>💬 Assistente de Campanhas IA</strong>
          <div class="dock-sub">Criação assistida & análise em tempo real</div>
        </div>
        <button type="button" class="modal-close" onclick={() => (showChatDrawer = false)}>✕</button>
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
          {enviandoChat ? 'Processando...' : 'Enviar para o Assistente'}
        </button>
      </form>
    </div>
  </div>
{/if}

<!-- MODAL DE PRÉVIA DO ANÚNCIO (FORMATO FEED DO FACEBOOK / INSTAGRAM) -->
{#if adModalPreview}
  <div class="modal-backdrop" onclick={() => (adModalPreview = null)} role="presentation">
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <div
      class="modal-card ad-preview-modal-card"
      onclick={(e) => e.stopPropagation()}
      role="dialog"
      aria-modal="true"
      tabindex="-1"
    >
      <div class="modal-head">
        <h3>📱 Prévia do Anúncio (Feed Facebook & Instagram)</h3>
        <button type="button" class="modal-close" onclick={() => (adModalPreview = null)} aria-label="Fechar">✕</button>
      </div>

      <div class="feed-mockup-wrapper">
        <div class="fb-feed-card">
          <!-- Topo do post com página oficial -->
          <div class="fb-post-header">
            <div class="fb-avatar">
              <span class="avatar-letter">{(connection.selected_account_name || 'Tv')[0]}</span>
            </div>
            <div class="fb-post-meta">
              <div class="fb-page-name">{connection.selected_account_name || 'Tvshopdigital — Página Oficial'}</div>
              <div class="fb-post-sub">Patrocinado · 🌐</div>
            </div>
          </div>

          <!-- Texto principal / Copy -->
          <div class="fb-post-body">
            {adModalPreview.primary_text || 'Oportunidades exclusivas de repasse e financiamento com entrada facilitada.'}
          </div>

          <!-- Imagem / Criativo -->
          <div class="fb-media-container">
            {#if adModalPreview.image_url}
              <img src={adModalPreview.image_url} alt={adModalPreview.name} class="fb-creative-img" />
            {:else if adModalPreview.creative_file}
              <img
                src={`/api/criativos/arquivo/${adModalPreview.creative_file}`}
                alt={adModalPreview.name}
                class="fb-creative-img"
                onerror={(e) => {
                  e.currentTarget.style.display = 'none';
                  e.currentTarget.nextElementSibling.style.display = 'flex';
                }}
              />
              <div class="fb-placeholder-media" style="display: none;">
                <span>🎨 {adModalPreview.creative_file}</span>
              </div>
            {:else}
              <div class="fb-placeholder-media">
                <span>🎨 Criativo em Alta Resolução</span>
              </div>
            {/if}
          </div>

          <!-- Barra de Chamada para Ação / Link -->
          <div class="fb-cta-bar">
            <div class="fb-cta-info">
              <span class="fb-domain">WHATSAPP.COM · OFERTA LIMITADA</span>
              <strong class="fb-headline">{adModalPreview.headline || 'Assuma Parcelas que Cabem no Bolso'}</strong>
            </div>
            <button type="button" class="btn-meta-cta">
              {adModalPreview.call_to_action === 'LEARN_MORE' ? 'Saiba Mais' : (adModalPreview.call_to_action || 'Saiba Mais')}
            </button>
          </div>
        </div>

        <!-- Painel lateral de detalhes técnicos do anúncio -->
        <div class="ad-preview-details">
          <h4>Detalhes do Anúncio</h4>
          <div class="preview-detail-row">
            <span class="detail-label">Nome:</span>
            <strong>{adModalPreview.name}</strong>
          </div>
          <div class="preview-detail-row">
            <span class="detail-label">ID do Anúncio:</span>
            <code class="camp-id-code">{adModalPreview.id}</code>
          </div>
          <div class="preview-detail-row">
            <span class="detail-label">Campanha Vinculada:</span>
            <span style="color: #cbd5e1;">{adModalPreview.campaign_name || '—'}</span>
          </div>
          <div class="preview-detail-row">
            <span class="detail-label">Conjunto de Anúncios:</span>
            <span style="color: #cbd5e1;">{adModalPreview.adset_name || '—'}</span>
          </div>
          <div class="preview-detail-row">
            <span class="detail-label">Status Atual:</span>
            <span class="origin-tag" class:real={adModalPreview.status === 'ACTIVE'}>
              {adModalPreview.status === 'ACTIVE' ? '🟢 ATIVO (Veiculando)' : '⏸️ PAUSADO (Rascunho)'}
            </span>
          </div>
          <div class="preview-detail-row">
            <span class="detail-label">Origem:</span>
            <span class="origin-tag" class:real={adModalPreview.is_real}>{adModalPreview.origem_dados}</span>
          </div>
          <div class="preview-detail-row">
            <span class="detail-label">Métricas Acumuladas:</span>
            <span style="color: #94a3b8; font-size: 0.76rem;">
              Gasto: R$ {adModalPreview.spend?.toFixed(2) || '0.00'} · {adModalPreview.clicks || 0} cliques · CTR {adModalPreview.ctr || 0}% · {adModalPreview.conversions || 0} conversões
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
{/if}

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

<!-- MODAL DE CHAVES DE API EXTERNA & MOTORES DE IA -->
{#if showApiKeysModal}
  {@const pOpenai = providers.find((x) => x.id === 'openai')}
  {@const pAnthropic = providers.find((x) => x.id === 'anthropic')}
  {@const pGoogle = providers.find((x) => x.id === 'google')}
  <div class="modal-backdrop">
    <div class="modal-card modal-wide">
      <div class="modal-head">
        <h3>🔑 Configurar Chaves de API Externa & Motores de IA</h3>
        <button type="button" class="modal-close" onclick={() => (showApiKeysModal = false)}>✕</button>
      </div>
      <p class="modal-desc">
        Insira as chaves de API dos provedores externos (OpenAI, Anthropic Claude, Google Gemini) ou ajuste os modelos locais (Ollama / OpenCode). As credenciais são salvas automaticamente no arquivo <code>.env</code> do servidor.
      </p>

      <div class="modal-fields">
        <div class="field">
          <label for="m-active-prov">Motor Principal Selecionado</label>
          <select id="m-active-prov" bind:value={selectedProvider}>
            {#each providers as p}
              <option value={p.id}>{p.label}</option>
            {/each}
          </select>
        </div>

        <!-- 1. OpenAI -->
        <div class="provider-config-card" class:selected={selectedProvider === 'openai'}>
          <div class="prov-card-head">
            <strong>🤖 OpenAI (GPT-4o / GPT-4.1)</strong>
            <span class="prov-key-badge" class:ok={pOpenai?.has_key}>
              {pOpenai?.has_key ? `✅ Salva (${pOpenai.masked_key})` : '⚠️ Sem API Key'}
            </span>
          </div>
          <div class="form-grid-2">
            <div class="field">
              <label for="k-openai">OpenAI API Key (OPENAI_API_KEY)</label>
              <input
                id="k-openai"
                type="password"
                placeholder={pOpenai?.has_key ? `Manter atual (${pOpenai.masked_key}) ou digitar nova...` : 'sk-proj-...'}
                bind:value={openaiKeyInput}
              />
            </div>
            <div class="field">
              <label for="m-openai">Modelo OpenAI</label>
              <input id="m-openai" type="text" placeholder="gpt-4o" bind:value={openaiModelInput} />
            </div>
          </div>
        </div>

        <!-- 2. Anthropic Claude -->
        <div class="provider-config-card" class:selected={selectedProvider === 'anthropic'}>
          <div class="prov-card-head">
            <strong>🧠 Anthropic Claude (Sonnet 4 / 3.5)</strong>
            <span class="prov-key-badge" class:ok={pAnthropic?.has_key}>
              {pAnthropic?.has_key ? `✅ Salva (${pAnthropic.masked_key})` : '⚠️ Sem API Key'}
            </span>
          </div>
          <div class="form-grid-2">
            <div class="field">
              <label for="k-anthropic">Anthropic API Key (ANTHROPIC_API_KEY)</label>
              <input
                id="k-anthropic"
                type="password"
                placeholder={pAnthropic?.has_key ? `Manter atual (${pAnthropic.masked_key}) ou digitar nova...` : 'sk-ant-api03-...'}
                bind:value={anthropicKeyInput}
              />
            </div>
            <div class="field">
              <label for="m-anthropic">Modelo Anthropic</label>
              <input id="m-anthropic" type="text" placeholder="claude-sonnet-4-6" bind:value={anthropicModelInput} />
            </div>
          </div>
        </div>

        <!-- 3. Google Gemini -->
        <div class="provider-config-card" class:selected={selectedProvider === 'google'}>
          <div class="prov-card-head">
            <strong>✨ Google Gemini (2.5 Flash / Pro)</strong>
            <span class="prov-key-badge" class:ok={pGoogle?.has_key}>
              {pGoogle?.has_key ? `✅ Salva (${pGoogle.masked_key})` : '⚠️ Sem API Key'}
            </span>
          </div>
          <div class="form-grid-2">
            <div class="field">
              <label for="k-gemini">Gemini API Key (GEMINI_API_KEY)</label>
              <input
                id="k-gemini"
                type="password"
                placeholder={pGoogle?.has_key ? `Manter atual (${pGoogle.masked_key}) ou digitar nova...` : 'AIzaSy...'}
                bind:value={geminiKeyInput}
              />
            </div>
            <div class="field">
              <label for="m-gemini">Modelo Gemini</label>
              <input id="m-gemini" type="text" placeholder="gemini-2.5-flash" bind:value={geminiModelInput} />
            </div>
          </div>
        </div>

        <!-- 4. Motores Locais (Ollama & OpenCode) -->
        <div class="provider-config-card" class:selected={selectedProvider === 'ollama' || selectedProvider === 'opencode'}>
          <div class="prov-card-head">
            <strong>🏠 Motores Locais (Ollama & OpenCode — Sem Custo de API)</strong>
            <span class="prov-key-badge ok">✅ Prontos Localmente</span>
          </div>
          <div class="form-grid-3">
            <div class="field">
              <label for="m-ollama">Modelo Ollama</label>
              <input id="m-ollama" type="text" bind:value={ollamaModelInput} />
            </div>
            <div class="field">
              <label for="u-ollama">URL Ollama</label>
              <input id="u-ollama" type="text" bind:value={ollamaUrlInput} />
            </div>
            <div class="field">
              <label for="m-opencode">Modelo OpenCode</label>
              <input id="m-opencode" type="text" bind:value={opencodeModelInput} />
            </div>
          </div>
        </div>
      </div>

      <div class="modal-foot">
        <button type="button" class="btn-top ghost" onclick={() => (showApiKeysModal = false)}>Cancelar</button>
        <button type="button" class="btn-cta" onclick={salvarChavesApi} disabled={salvandoKeys}>
          {salvandoKeys ? 'Salvando...' : '💾 Salvar Chaves API & Ativar Motor'}
        </button>
      </div>
    </div>
  </div>
{/if}



<style>
  .app-shell {
    display: grid;
    grid-template-columns: 232px minmax(0, 1fr);
    height: 100vh;
    max-height: 100vh;
    overflow: hidden;
    background: var(--bg-app);
  }

  /* SIDEBAR */
  .sidebar {
    background: var(--bg-sidebar);
    border-right: 1px solid var(--border);
    padding: 14px 12px 12px;
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
    gap: 8px;
    height: 100vh;
    overflow-y: auto;
  }

  .brand {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 2px 6px 12px;
    border-bottom: 1px solid var(--border);
  }

  .brand-titles {
    flex: 1;
    min-width: 0;
  }



  .brand-logo {
    width: 30px;
    height: 30px;
    border-radius: 8px;
    background: linear-gradient(135deg, #2563eb, #06b6d4);
    display: grid;
    place-items: center;
    font-weight: 900;
    font-size: 16px;
    color: #fff;
    flex-shrink: 0;
  }

  .brand-name {
    font-weight: 800;
    font-size: 0.92rem;
    letter-spacing: -0.01em;
  }

  .brand-sub {
    font-size: 0.68rem;
    color: var(--muted);
  }

  .nav-list {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .nav-group-label {
    font-size: 0.64rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--muted);
    padding: 8px 8px 3px;
  }

  .nav-item {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    padding: 7px 10px;
    border-radius: 7px;
    border: 1px solid transparent;
    background: transparent;
    color: var(--text-secondary);
    font-size: 0.78rem;
    font-weight: 600;
    cursor: pointer;
    text-align: left;
    transition: all 0.12s;
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
    font-size: 0.9rem;
  }

  .nav-count {
    margin-left: auto;
    font-size: 0.64rem;
    font-weight: 700;
    padding: 1px 6px;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.07);
    color: var(--text-secondary);
  }

  .ham-cat-title {
    font-size: 0.72rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #60a5fa;
    margin-top: 8px;
  }

  .chat-drawer {
    position: fixed;
    top: 0;
    right: 0;
    width: 360px;
    max-width: 92vw;
    height: 100vh;
    background: var(--bg-sidebar);
    border-left: 1px solid var(--border-strong);
    display: flex;
    flex-direction: column;
    z-index: 250;
    box-shadow: -16px 0 48px rgba(0, 0, 0, 0.65);
  }

  /* RODAPÉ MINIMALISTA DA SIDEBAR */
  .sidebar-footer-minimal {
    margin-top: auto;
    padding-top: 10px;
    border-top: 1px solid var(--border);
  }

  .status-dot-row {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 8px;
    border-radius: 6px;
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid var(--border);
  }

  .engine-dot-status {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #f59e0b;
  }

  .engine-dot-status.ready {
    background: #10b981;
    box-shadow: 0 0 6px #10b981;
  }

  .foot-text {
    font-size: 0.7rem;
    font-weight: 700;
    color: var(--text-secondary);
  }

  /* CONTA ATIVA NA SIDEBAR */
  .sidebar-account-box {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 10px;
    margin: 4px 0 6px;
    border-radius: 8px;
    background: rgba(15, 23, 42, 0.75);
    border: 1px solid var(--border);
  }

  .sidebar-account-box.connected {
    border-color: rgba(16, 185, 129, 0.3);
    background: rgba(16, 185, 129, 0.06);
  }

  .conn-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #f59e0b;
    flex-shrink: 0;
  }

  .conn-dot.connected {
    background: #10b981;
    box-shadow: 0 0 8px #10b981;
  }

  .sidebar-acc-info {
    display: flex;
    flex-direction: column;
    min-width: 0;
    gap: 1px;
  }

  .sidebar-acc-info strong {
    font-size: 0.74rem;
    color: #fff;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .sidebar-acc-info code {
    font-size: 0.65rem;
    color: #38bdf8;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  /* WORKSPACE CENTRAL - 100% LIMPO E ESPAÇOSO (ZERO POLUIÇÃO NO TOPO) */
  .workspace {
    display: flex;
    flex-direction: column;
    min-width: 0;
    height: 100vh;
    overflow-y: auto;
    background: var(--bg-app);
  }

  .sub-status {
    margin-top: 4px;
    opacity: 0.85;
  }

  /* TOOLBAR E RECURSOS DO GERENCIADOR DE ANÚNCIOS (META ADS) */
  .adsmanager-head-actions {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }

  .adsmanager-toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    margin: 14px 0 16px;
    padding: 10px 14px;
    background: #0b0f19;
    border: 1px solid var(--border);
    border-radius: 10px;
    flex-wrap: wrap;
  }

  .status-filter-pills {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
  }

  .filter-pill {
    background: var(--surface);
    border: 1px solid var(--border);
    color: var(--text-secondary);
    border-radius: 7px;
    padding: 5px 11px;
    font-size: 0.76rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.13s;
  }

  .filter-pill:hover {
    color: #fff;
    border-color: var(--border-strong);
  }

  .filter-pill.active {
    background: rgba(37, 99, 235, 0.2);
    border-color: #3b82f6;
    color: #93c5fd;
  }

  .search-box {
    display: flex;
    align-items: center;
    position: relative;
    min-width: 260px;
  }

  .search-box input {
    width: 100%;
    background: var(--surface);
    border: 1px solid var(--border-strong);
    color: #fff;
    border-radius: 8px;
    padding: 6px 28px 6px 10px;
    font-size: 0.77rem;
  }

  .search-clear {
    position: absolute;
    right: 8px;
    background: transparent;
    border: none;
    color: var(--muted);
    cursor: pointer;
    font-size: 0.75rem;
  }

  .budget-cell {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .btn-edit-budget {
    background: transparent;
    border: none;
    cursor: pointer;
    font-size: 0.75rem;
    padding: 2px 4px;
    border-radius: 4px;
    opacity: 0.7;
    transition: opacity 0.15s;
  }

  .btn-edit-budget:hover {
    opacity: 1;
    background: rgba(255, 255, 255, 0.1);
  }

  .camp-id-code {
    background: rgba(255, 255, 255, 0.06);
    color: #94a3b8;
    padding: 1px 5px;
    border-radius: 4px;
    font-size: 0.68rem;
    margin-left: 4px;
  }

  .row-paused {
    opacity: 0.72;
  }

  .mini-btn.dup {
    background: rgba(59, 130, 246, 0.14);
    border: 1px solid rgba(59, 130, 246, 0.35);
    color: #93c5fd;
  }

  .mini-btn.dup:hover {
    background: #2563eb;
    color: #fff;
  }

  .mini-btn.del {
    background: rgba(239, 68, 68, 0.12);
    border: 1px solid rgba(239, 68, 68, 0.3);
    color: #fca5a5;
  }

  .mini-btn.del:hover {
    background: #dc2626;
    color: #fff;
  }

  /* VIEW DE CONFIGURAÇÕES */
  .settings-view {
    display: flex;
    flex-direction: column;
    gap: 20px;
    margin-top: 10px;
  }

  .settings-card {
    padding: 22px;
  }

  .settings-content-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 16px;
    margin: 16px 0;
  }

  .info-block {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .info-label {
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--muted);
  }

  .info-val {
    font-size: 0.88rem;
    color: var(--text);
  }

  .info-val.strong {
    font-weight: 700;
    color: #fff;
    font-size: 0.95rem;
  }

  .settings-select {
    background: var(--surface);
    color: #fff;
    border: 1px solid var(--border-strong);
    border-radius: 8px;
    padding: 7px 10px;
    font-size: 0.8rem;
    font-weight: 600;
    width: 100%;
  }

  .settings-select-large {
    background: var(--surface);
    color: #fff;
    border: 1px solid var(--border-strong);
    border-radius: 9px;
    padding: 10px 12px;
    font-size: 0.88rem;
    font-weight: 700;
    width: 100%;
  }

  .settings-actions-row {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-top: 16px;
    padding-top: 14px;
    border-top: 1px solid var(--border);
  }

  .settings-engine-body {
    display: flex;
    flex-direction: column;
    gap: 14px;
    margin-top: 14px;
  }

  .engine-buttons-row {
    display: flex;
    gap: 10px;
  }

  .hint-small {
    display: block;
    font-size: 0.76rem;
    color: var(--muted);
    margin-top: 6px;
    line-height: 1.4;
  }

  .integrations-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin-top: 14px;
  }

  .integ-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 14px;
    border-radius: 9px;
    background: #0b0f19;
    border: 1px solid var(--border);
  }

  .integ-icon {
    font-size: 1.3rem;
  }

  .integ-info {
    flex: 1;
    min-width: 0;
  }

  .integ-info strong {
    display: block;
    font-size: 0.84rem;
    color: #fff;
  }

  .integ-info span {
    font-size: 0.74rem;
    color: var(--muted);
  }

  .integ-status {
    font-size: 0.72rem;
    font-weight: 700;
    padding: 3px 8px;
    border-radius: 999px;
    background: rgba(239, 68, 68, 0.16);
    color: #fca5a5;
  }

  .integ-status.ok {
    background: rgba(16, 185, 129, 0.16);
    color: #6ee7b7;
  }

  .conn-badge {
    font-size: 0.75rem;
    font-weight: 700;
    padding: 3px 9px;
    border-radius: 999px;
    background: rgba(245, 158, 11, 0.16);
    color: #f59e0b;
  }

  .conn-badge.connected {
    background: rgba(16, 185, 129, 0.16);
    color: #10b981;
  }

  .engine-tag {
    font-size: 0.75rem;
    font-weight: 700;
    padding: 3px 9px;
    border-radius: 999px;
    background: rgba(245, 158, 11, 0.16);
    color: #f59e0b;
  }

  .engine-tag.ready {
    background: rgba(16, 185, 129, 0.16);
    color: #10b981;
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
    flex: 1;
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
    position: relative;
    height: 210px;
    background: linear-gradient(135deg, #172554 0%, #0f172a 100%);
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    padding: 14px;
    border-top: 1px solid var(--border);
    border-bottom: 1px solid var(--border);
    overflow: hidden;
  }

  .ig-media-real {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
    z-index: 0;
  }

  .ig-media-badge {
    position: relative;
    z-index: 1;
    align-self: flex-start;
    background: rgba(0, 0, 0, 0.72);
    padding: 4px 9px;
    border-radius: 6px;
    font-size: 0.72rem;
    color: #93c5fd;
  }

  .ig-media-overlay {
    position: relative;
    z-index: 1;
    font-size: 0.96rem;
    font-weight: 800;
    color: #fff;
    text-shadow: 0 2px 6px rgba(0, 0, 0, 0.85);
  }

  .creative-upload-row {
    display: flex;
    gap: 10px;
    align-items: center;
    flex-wrap: wrap;
  }

  .creative-upload-dropzone {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 12px;
    border-radius: 10px;
    border: 1px dashed rgba(59, 130, 246, 0.45);
    background: rgba(37, 99, 235, 0.08);
  }

  .btn-upload-creative {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 9px 14px;
    border-radius: 8px;
    border: 1px solid rgba(59, 130, 246, 0.5);
    background: rgba(37, 99, 235, 0.2);
    color: #bfdbfe;
    font-size: 0.8rem;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.15s;
  }

  .btn-upload-creative:hover {
    background: var(--primary);
    color: #fff;
  }

  .creative-select-inline {
    flex: 1;
    min-width: 180px;
  }

  .upload-sub-hint {
    font-size: 0.75rem;
    color: var(--muted);
  }

  .preview-head-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
    margin-bottom: 12px;
    flex-wrap: wrap;
  }

  .preview-head-row h2 {
    margin: 0;
  }

  .btn-quick-upload {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 5px 10px;
    border-radius: 7px;
    border: 1px solid rgba(59, 130, 246, 0.45);
    background: rgba(37, 99, 235, 0.16);
    color: #93c5fd;
    font-size: 0.74rem;
    font-weight: 700;
    cursor: pointer;
  }

  .btn-quick-upload:hover {
    background: var(--primary);
    color: #fff;
  }

  .real-created-banner {
    background: rgba(16, 185, 129, 0.14);
    border: 1px solid rgba(16, 185, 129, 0.4);
    border-radius: 10px;
    padding: 12px 14px;
    margin-bottom: 14px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
    font-size: 0.8rem;
    color: #d1fae5;
  }

  .btn-open-real-ads {
    background: #059669;
    color: #fff;
    text-decoration: none;
    padding: 7px 12px;
    border-radius: 7px;
    font-size: 0.76rem;
    font-weight: 700;
    white-space: nowrap;
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
    max-height: 90vh;
    overflow-y: auto;
    padding: 20px 22px;
    box-shadow: 0 24px 60px rgba(0, 0, 0, 0.6);
  }

  .modal-card.modal-wide {
    max-width: 680px;
  }

  .provider-config-card {
    background: var(--surface-alt);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 12px 14px;
  }

  .provider-config-card.selected {
    border-color: rgba(59, 130, 246, 0.55);
    background: rgba(37, 99, 235, 0.08);
  }

  .prov-card-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
    font-size: 0.84rem;
  }

  .prov-key-badge {
    font-size: 0.7rem;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 999px;
    background: rgba(245, 158, 11, 0.16);
    color: #fbbf24;
  }

  .prov-key-badge.ok {
    background: rgba(16, 185, 129, 0.16);
    color: #34d399;
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

  /* ABAS DOS 3 NÍVEIS HIERÁRQUICOS DO GERENCIADOR DE ANÚNCIOS */
  .meta-manager-level-tabs {
    display: flex;
    gap: 8px;
    margin: 18px 0 12px;
    border-bottom: 1px solid var(--border);
    padding-bottom: 2px;
  }

  .level-tab-btn {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 10px 18px;
    border: 1px solid transparent;
    border-bottom: none;
    border-radius: 8px 8px 0 0;
    background: transparent;
    color: var(--muted);
    font-size: 0.88rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .level-tab-btn:hover {
    color: #fff;
    background: rgba(255, 255, 255, 0.04);
  }

  .level-tab-btn.active {
    color: #fff;
    background: #111827;
    border-color: var(--border);
    border-bottom: 2px solid var(--primary);
  }

  .tab-level-icon {
    font-size: 1rem;
  }

  .tab-level-badge {
    background: #1f2937;
    color: #94a3b8;
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 700;
  }

  .level-tab-btn.active .tab-level-badge {
    background: var(--primary);
    color: #fff;
  }

  .opt-goal-badge {
    display: inline-block;
    padding: 2px 7px;
    border-radius: 4px;
    background: #1e293b;
    color: #38bdf8;
    border: 1px solid #334155;
    font-size: 0.7rem;
    font-weight: 600;
    margin-bottom: 2px;
  }

  .ad-thumb-box {
    width: 44px;
    height: 44px;
    border-radius: 6px;
    overflow: hidden;
    position: relative;
    background: #1e293b;
    border: 1px solid var(--border);
    flex-shrink: 0;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .ad-thumb-img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .ad-thumb-fallback {
    font-size: 1.2rem;
  }

  .ad-copy-cell {
    max-width: 280px;
  }

  .ad-copy-title {
    font-weight: 650;
    color: #f1f5f9;
    font-size: 0.82rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .ad-copy-snippet {
    font-size: 0.72rem;
    color: var(--muted);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-top: 2px;
  }

  .cta-badge {
    display: inline-block;
    padding: 2px 7px;
    border-radius: 4px;
    background: #1e293b;
    color: #38bdf8;
    border: 1px solid #334155;
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
  }

  /* MODAL DE PRÉVIA DO ANÚNCIO (FEED MOCKUP) */
  .ad-preview-modal-card {
    max-width: 820px;
    width: 95%;
  }

  .feed-mockup-wrapper {
    display: grid;
    grid-template-columns: 360px 1fr;
    gap: 20px;
    margin-top: 14px;
  }

  @media (max-width: 768px) {
    .feed-mockup-wrapper {
      grid-template-columns: 1fr;
    }
  }

  .fb-feed-card {
    background: #0f172a;
    border: 1px solid #334155;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4);
  }

  .fb-post-header {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 12px 14px;
  }

  .fb-avatar {
    width: 38px;
    height: 38px;
    border-radius: 50%;
    background: linear-gradient(135deg, #2563eb, #38bdf8);
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    color: #fff;
    flex-shrink: 0;
  }

  .fb-page-name {
    font-weight: 600;
    font-size: 0.86rem;
    color: #fff;
  }

  .fb-post-sub {
    font-size: 0.68rem;
    color: #94a3b8;
  }

  .fb-post-body {
    padding: 4px 14px 12px;
    font-size: 0.82rem;
    color: #e2e8f0;
    line-height: 1.45;
  }

  .fb-media-container {
    width: 100%;
    aspect-ratio: 1;
    background: #1e293b;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
  }

  .fb-creative-img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .fb-placeholder-media {
    color: var(--muted);
    font-size: 0.84rem;
  }

  .fb-cta-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 14px;
    background: #1e293b;
    border-top: 1px solid #334155;
    gap: 8px;
  }

  .fb-cta-info {
    overflow: hidden;
  }

  .fb-domain {
    display: block;
    font-size: 0.64rem;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .fb-headline {
    display: block;
    font-size: 0.82rem;
    color: #fff;
    margin-top: 2px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 200px;
  }

  .btn-meta-cta {
    padding: 6px 12px;
    background: #3b82f6;
    color: #fff;
    font-weight: 600;
    font-size: 0.78rem;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    flex-shrink: 0;
  }

  .ad-preview-details {
    display: flex;
    flex-direction: column;
    gap: 12px;
    background: #0b0f19;
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px;
  }

  .ad-preview-details h4 {
    margin: 0;
    font-size: 0.92rem;
    color: #fff;
    border-bottom: 1px solid var(--border);
    padding-bottom: 8px;
  }

  .preview-detail-row {
    display: flex;
    flex-direction: column;
    gap: 3px;
    font-size: 0.8rem;
  }

  .detail-label {
    color: var(--muted);
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.4px;
  }

  /* FILTROS AVANÇADOS DO GERENCIADOR DE ANÚNCIOS */
  .adsmanager-toolbar-filters {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
    flex: 1;
  }

  .filter-select {
    padding: 7px 11px;
    background: #0f172a;
    border: 1px solid var(--border);
    border-radius: 8px;
    color: #cbd5e1;
    font-size: 0.79rem;
    font-weight: 550;
    cursor: pointer;
    outline: none;
    transition: all 0.15s ease;
  }

  .filter-select:hover,
  .filter-select:focus {
    border-color: var(--primary);
    color: #fff;
    background: #1e293b;
  }

  .btn-clear-filters {
    padding: 6px 12px;
    background: rgba(239, 68, 68, 0.12);
    border: 1px solid rgba(239, 68, 68, 0.35);
    border-radius: 8px;
    color: #f87171;
    font-size: 0.76rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .btn-clear-filters:hover {
    background: rgba(239, 68, 68, 0.25);
    color: #fff;
  }

  /* LISTA DE ALERTAS DE FADIGA CRIATIVA */
  .fatigue-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin-top: 10px;
  }

  .fatigue-card {
    background: #0f172a;
    border: 1px solid #334155;
    border-left: 4px solid #f59e0b;
    border-radius: 8px;
    padding: 12px 16px;
  }

  .fatigue-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
  }

  .fatigue-head strong {
    color: #fff;
    font-size: 0.88rem;
  }

  .fatigue-tag {
    padding: 2px 8px;
    background: rgba(245, 158, 11, 0.15);
    border: 1px solid rgba(245, 158, 11, 0.4);
    color: #fbbf24;
    border-radius: 4px;
    font-size: 0.72rem;
    font-weight: 700;
  }
</style>
