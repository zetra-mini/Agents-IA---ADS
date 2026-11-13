<script>
  import { onMount } from 'svelte';

  let {
    planoAssistido = $bindable(),
    onAplicarNaCampanha = () => {},
    onNotificar = () => {},
  } = $props();

  let subTab = $state('geradores'); // 'brain' | 'geradores' | 'score_steal' | 'pipeboard_mcp' | 'benchmarks'
  let showHamburgerModal = $state(false);
  let carregando = $state(false);

  const MODULOS_OAK = [
    {
      id: 'geradores',
      icone: '✍️',
      curto: 'Geradores & Reels',
      titulo: '18 Geradores & Wizard 10-Min',
      desc: '3 variantes Meta Ads (Dor, Desejo, Prova Social), 6 roteiros de Reels (10 ganchos) e Kit WhatsApp + Google.',
      badge: '18 Tools',
    },
    {
      id: 'brain',
      icone: '🧠',
      curto: 'Cérebro da Marca',
      titulo: 'Cérebro da Marca (Brand Brain & URL)',
      desc: 'Auto-extrator de site por URL e 8 templates brasileiros prontos para calibrar toda a IA.',
      badge: 'Auto-URL',
    },
    {
      id: 'score_steal',
      icone: '🎯',
      curto: 'Score & Espionagem',
      titulo: 'Creative Score (5 Alavancas) & Steal & Beat',
      desc: 'Nota de 0 a 10 para seu anúncio + engenharia reversa para superar anúncios de concorrentes.',
      badge: '11 Otimizadores',
    },
    {
      id: 'pipeboard_mcp',
      icone: '🔌',
      curto: 'Pipeboard MCP',
      titulo: 'Pipeboard Meta Ads MCP (Graph API)',
      desc: 'Busca oficial de interesses (IDs reais), cidades/regiões e páginas via Meta Graph API.',
      badge: '42 MCP Tools',
    },
    {
      id: 'benchmarks',
      icone: '📚',
      curto: 'Benchmarks & Copy',
      titulo: 'Benchmarks Brasil & Escola de Copy',
      desc: 'Métricas de CTR/CPC/CPM/ROAS 2025/2026 no Brasil e frameworks PAS, AIDA, BAB, 4 U’s e Schwartz.',
      badge: 'Guia PT-BR',
    },
  ];

  let moduloAtivoInfo = $derived(MODULOS_OAK.find((m) => m.id === subTab) || MODULOS_OAK[0]);

  // Estado do Hub OpenAdKit + Pipeboard MCP
  let activeBrain = $state({
    business_name: 'AutoPrime Curitiba & Região',
    industry: 'Automotivo / Financiamento e Seminovos',
    niche: 'Veículos revisados e repasse de financiamento com aprovação rápida',
    service_area: 'Curitiba, Campo Largo',
    tone: 'Direto, confiável e transparente',
    usp: 'Simulação em 2 minutos pelo WhatsApp e veículos periciados com garantia',
    audience_who: 'Homens e mulheres de 23 a 58 anos buscando trocar de carro ou financiamento',
    audience_pain_points: ['Juros altos', 'Burocracia bancária'],
    audience_desires: ['Sair de carro novo com parcela acessível', 'Simular rápido no WhatsApp'],
    key_benefits: ['Aprovação rápida no WhatsApp', 'Estoque revisado com laudo'],
    words_to_use: ['Simule no WhatsApp', 'Parcelas acessíveis', 'Laudo aprovado'],
  });
  let brainsList = $state([]);
  let templates = $state([]);
  let benchmarks = $state([]);
  let frameworks = $state([]);
  let mcpTools = $state([]);

  // Extrator de URL (Brand Brain)
  let urlExtracao = $state('');
  let extraindoUrl = $state(false);

  // Inputs do Gerador Multiplataforma
  let genId = $state('meta_ads_3_angulos');
  let genProduto = $state('Repasse de Financiamento e Seminovos Revisados');
  let genPromocao = $state('Simulação em 2 minutos pelo WhatsApp + 1ª parcela para 60 dias');
  let genCidades = $state('Curitiba, Campo Largo');
  let genCta = $state('Enviar mensagem');
  let resultadoGeracao = $state(null);

  // Creative Score (5 Alavancas)
  let scoreTexto = $state('');
  let scoreTitulo = $state('');
  let scoreCta = $state('Enviar mensagem');
  let resultadoScore = $state(null);

  // Espionagem Steal & Beat
  let concNome = $state('Concorrente Tradicional');
  let concAnuncio = $state(
    'Venha conferir nosso estoque de veículos com ótimas taxas de financiamento. Faça uma visita em nossa loja!'
  );
  let concDiferencial = $state('Pré-aprovação em 2 minutos direto no WhatsApp e laudo cautelar 100% aprovado');
  let resultadoSteal = $state(null);

  // Pipeboard Meta Ads MCP
  let buscaInteresseQuery = $state('Financiamento');
  let interessesEncontrados = $state([]);
  let buscaCidadeQuery = $state('Curitiba');
  let cidadesEncontradas = $state([]);
  let mcpToolSelecionada = $state('mcp_meta_ads_get_ad_accounts');
  let mcpToolQuery = $state('');
  let mcpToolOutput = $state(null);

  async function carregarHub() {
    try {
      const res = await fetch('/api/openadkit/hub');
      if (res.ok) {
        const data = await res.json();
        if (data.active_brain) activeBrain = data.active_brain;
        brainsList = data.brains || [];
        templates = data.templates || [];
        benchmarks = data.benchmarks || [];
        frameworks = data.frameworks_copy || [];
        mcpTools = data.pipeboard_mcp_tools || [];
        genProduto = activeBrain.niche || genProduto;
        genPromocao = activeBrain.usp || genPromocao;
        genCidades = activeBrain.service_area || genCidades;
      }
      // Já dispara uma geração inicial e score inicial para a tela ficar rica imediatamente
      await executarGerador();
      scoreTexto =
        planoAssistido?.anuncios?.[0]?.texto_principal ||
        'Procurando repasse de financiamento com parcelas acessíveis em Curitiba e Campo Largo? Simule em 2 minutos no WhatsApp!';
      scoreTitulo = planoAssistido?.anuncios?.[0]?.titulo || 'Repasse Facilitado Curitiba';
      await Promise.all([
        executarCreativeScore(),
        executarStealAndBeat(),
        buscarInteressesMcp(),
        buscarCidadesMcp(),
      ]);
    } catch (_) {}
  }

  async function aplicarTemplateIndustria(slug) {
    carregando = true;
    try {
      const res = await fetch('/api/openadkit/brand-brain', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ apply_template_slug: slug }),
      });
      if (res.ok) {
        const data = await res.json();
        activeBrain = data.active_brain;
        brainsList = data.brains || [];
        genProduto = activeBrain.niche || '';
        genPromocao = activeBrain.usp || '';
        genCidades = activeBrain.service_area || 'Curitiba';
        onNotificar(`Template "${activeBrain.business_name}" carregado no Cérebro da Marca!`);
        await executarGerador();
      }
    } finally {
      carregando = false;
    }
  }

  async function extrairMarcaDeUrl() {
    if (!urlExtracao.trim()) {
      onNotificar('Digite a URL do site do cliente (ex: https://seusite.com.br).', 'error');
      return;
    }
    extraindoUrl = true;
    try {
      const res = await fetch('/api/openadkit/brand-brain/extract-url', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: urlExtracao.trim(),
          service_area: genCidades,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Erro ao extrair URL.');
      activeBrain = data.active_brain;
      brainsList = data.brains || [];
      genProduto = activeBrain.niche || '';
      genPromocao = activeBrain.usp || '';
      onNotificar(data.mensagem);
      await executarGerador();
    } catch (err) {
      onNotificar(err.message, 'error');
    } finally {
      extraindoUrl = false;
    }
  }

  async function salvarBrainAtual() {
    carregando = true;
    try {
      const res = await fetch('/api/openadkit/brand-brain', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(activeBrain),
      });
      if (res.ok) {
        const data = await res.json();
        activeBrain = data.active_brain;
        brainsList = data.brains || [];
        onNotificar('Cérebro da Marca salvo e sincronizado!');
      }
    } finally {
      carregando = false;
    }
  }

  async function executarGerador() {
    carregando = true;
    try {
      const res = await fetch('/api/openadkit/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          generator_id: genId,
          produto_oferta: genProduto,
          promocao: genPromocao,
          cidades: genCidades,
          cta_preferido: genCta,
        }),
      });
      if (res.ok) {
        resultadoGeracao = await res.json();
      }
    } finally {
      carregando = false;
    }
  }

  async function executarCreativeScore() {
    const res = await fetch('/api/openadkit/creative-score', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        texto_principal: scoreTexto,
        titulo: scoreTitulo,
        cta: scoreCta,
      }),
    });
    if (res.ok) {
      resultadoScore = await res.json();
    }
  }

  async function executarStealAndBeat() {
    const res = await fetch('/api/openadkit/steal-beat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        anuncio_concorrente: concAnuncio,
        nome_concorrente: concNome,
        nosso_diferencial: concDiferencial,
      }),
    });
    if (res.ok) {
      resultadoSteal = await res.json();
    }
  }

  async function buscarInteressesMcp() {
    const res = await fetch('/api/meta/mcp/execute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        tool_id: 'mcp_meta_ads_search_interests',
        query: buscaInteresseQuery,
      }),
    });
    if (res.ok) {
      const d = await res.json();
      interessesEncontrados = d.resultado || [];
    }
  }

  async function buscarCidadesMcp() {
    const res = await fetch('/api/meta/mcp/execute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        tool_id: 'mcp_meta_ads_search_geo_locations',
        query: buscaCidadeQuery,
      }),
    });
    if (res.ok) {
      const d = await res.json();
      cidadesEncontradas = d.resultado || [];
    }
  }

  async function rodarFerramentaMcpDireta() {
    const res = await fetch('/api/meta/mcp/execute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        tool_id: mcpToolSelecionada,
        query: mcpToolQuery,
      }),
    });
    if (res.ok) {
      mcpToolOutput = await res.json();
      onNotificar(`Ferramenta Pipeboard "${mcpToolSelecionada}" executada com sucesso!`);
    }
  }

  function usarVarianteNaCampanha(v) {
    if (!planoAssistido) return;
    planoAssistido.nome_campanha = `Campanha CBO - ${activeBrain.business_name} - ${genCidades.split(',')[0]}`;
    if (planoAssistido.conjuntos?.[0]) {
      const locs = genCidades
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean);
      if (locs.length > 0) planoAssistido.conjuntos[0].publico.localizacoes = locs;
    }
    if (planoAssistido.anuncios?.[0]) {
      planoAssistido.anuncios[0].texto_principal = v.primary_text;
      planoAssistido.anuncios[0].titulo = v.headline;
      planoAssistido.anuncios[0].descricao = v.description || 'Simule agora pelo WhatsApp';
      planoAssistido.anuncios[0].cta = v.cta_button || v.cta || 'Enviar mensagem';
    }
    onAplicarNaCampanha();
    onNotificar(`Variante "${v.label}" aplicada na Criação de Campanha Assistida!`);
  }

  function adicionarInteresseNaCampanha(nomeInteresse) {
    if (!planoAssistido?.conjuntos?.[0]) return;
    const atuais = planoAssistido.conjuntos[0].publico.interesses_sugeridos || [];
    if (!atuais.includes(nomeInteresse)) {
      planoAssistido.conjuntos[0].publico.interesses_sugeridos = [...atuais, nomeInteresse];
    }
    onNotificar(`Interesse "${nomeInteresse}" adicionado ao Conjunto de Anúncios!`);
  }

  function adicionarCidadeNaCampanha(nomeCidade) {
    if (!planoAssistido?.conjuntos?.[0]) return;
    const atuais = planoAssistido.conjuntos[0].publico.localizacoes || [];
    if (!atuais.includes(nomeCidade)) {
      planoAssistido.conjuntos[0].publico.localizacoes = [...atuais, nomeCidade];
      planoAssistido.conjuntos[0].nome = `Conjunto 01 - ${planoAssistido.conjuntos[0].publico.localizacoes.join(', ')}`;
    }
    onNotificar(`Cidade "${nomeCidade}" adicionada à segmentação geográfica!`);
  }

  onMount(carregarHub);
</script>

<div class="oak-wrap">
  <!-- BARRA SUPERIOR COMPACTA + BOTÃO DE MODAL HAMBÚRGUER (☰) -->
  <div class="oak-compact-header">
    <div class="oak-compact-left">
      <button
        type="button"
        class="btn-hamburger-oak"
        onclick={() => (showHamburgerModal = true)}
        title="Abrir Catálogo Completo OpenAdKit & Pipeboard MCP"
      >
        <span class="ham-lines">☰</span>
        <span>Menu & Ferramentas</span>
        <span class="ham-count">5 Suítes</span>
      </button>

      <div class="oak-active-title">
        <span class="oak-mod-icon">{moduloAtivoInfo.icone}</span>
        <div>
          <div class="oak-mod-name">
            {moduloAtivoInfo.titulo}
            <span class="oak-mini-badge">{moduloAtivoInfo.badge}</span>
          </div>
          <div class="oak-mod-sub">{moduloAtivoInfo.desc}</div>
        </div>
      </div>
    </div>

    <div class="oak-compact-right">
      <!-- NAVEGAÇÃO RÁPIDA EM 1 LINHA -->
      <div class="oak-inline-pills">
        {#each MODULOS_OAK as m}
          <button
            type="button"
            class:active={subTab === m.id}
            onclick={() => (subTab = m.id)}
            title={m.titulo}
          >
            <span>{m.icone}</span>
            <span>{m.curto}</span>
          </button>
        {/each}
      </div>

      <button
        type="button"
        class="brand-compact-btn"
        onclick={() => (subTab = 'brain')}
        title="Clique para trocar ou editar o Cérebro da Marca"
      >
        <span>🧠</span>
        <span class="brand-compact-name">{activeBrain.business_name}</span>
      </button>
    </div>
  </div>

  <!-- MODAL HAMBÚRGUER: CENTRAL OPENADKIT v1.1 PT-BR & PIPEBOARD META ADS MCP -->
  {#if showHamburgerModal}
    <div class="oak-modal-backdrop" role="presentation" onclick={() => (showHamburgerModal = false)}>
      <div class="oak-modal-drawer" role="dialog" tabindex="-1" onclick={(e) => e.stopPropagation()} onkeydown={(e) => e.key === 'Escape' && (showHamburgerModal = false)}>
        <div class="oak-modal-head">
          <div>
            <div class="oak-badges">
              <span class="badge-pill gold">🧰 OpenAdKit v1.1 PT-BR</span>
              <span class="badge-pill blue">🔌 Pipeboard Meta Ads MCP (42 Tools)</span>
              <span class="badge-pill green">100% Português do Brasil</span>
            </div>
            <h3>Central OpenAdKit & Pipeboard Meta Ads MCP</h3>
            <p>
              18 Geradores de Anúncios · 11 Otimizadores · Cérebro da Marca (Brand Brain) · Creative Score 5 Alavancas · Espionagem Steal & Beat · Segmentação Oficial da Meta Graph API.
            </p>
          </div>
          <button type="button" class="oak-modal-close" onclick={() => (showHamburgerModal = false)}>✕</button>
        </div>

        <div class="oak-modal-section-title">Selecione a Ferramenta / Módulo</div>
        <div class="oak-modal-grid">
          {#each MODULOS_OAK as m}
            <button
              type="button"
              class="oak-modal-item"
              class:selected={subTab === m.id}
              onclick={() => {
                subTab = m.id;
                showHamburgerModal = false;
              }}
            >
              <div class="oak-mi-top">
                <span class="oak-mi-icon">{m.icone}</span>
                <strong>{m.titulo}</strong>
                <span class="oak-mi-badge">{m.badge}</span>
              </div>
              <p>{m.desc}</p>
            </button>
          {/each}
        </div>

        <div class="oak-modal-brand-bar">
          <div>
            <span>🧠 Marca Ativa no Cérebro:</span>
            <strong>{activeBrain.business_name}</strong>
            <small>({activeBrain.service_area || 'Brasil'})</small>
          </div>
          <div class="oak-modal-tpl-chips">
            {#each templates.slice(0, 4) as tpl}
              <button
                type="button"
                class="tpl-quick-chip"
                onclick={() => {
                  aplicarTemplateIndustria(tpl.slug);
                  showHamburgerModal = false;
                }}
              >
                {tpl.emoji} {tpl.nome}
              </button>
            {/each}
          </div>
        </div>
      </div>
    </div>
  {/if}

  {#if subTab === 'geradores'}
    <!-- ABA 1: 18 GERADORES DE ANÚNCIOS, REELS (10 HOOKS) & WIZARD 10 MINUTOS -->
    <div class="oak-grid-2">
      <section class="oak-card">
        <h2>⚡ Configurar Geração de Alta Conversão</h2>
        <div class="oak-form">
          <div class="f-row">
            <label for="oak-gen-prod">Produto / Oferta Principal</label>
            <input id="oak-gen-prod" type="text" bind:value={genProduto} />
          </div>
          <div class="f-row">
            <label for="oak-gen-usp">Diferencial / Promoção (USP)</label>
            <input id="oak-gen-usp" type="text" bind:value={genPromocao} />
          </div>
          <div class="f-grid-2">
            <div class="f-row">
              <label for="oak-gen-cid">Cidades / Região Alvo</label>
              <input id="oak-gen-cid" type="text" bind:value={genCidades} />
            </div>
            <div class="f-row">
              <label for="oak-gen-cta">Botão CTA</label>
              <select id="oak-gen-cta" bind:value={genCta}>
                <option value="Enviar mensagem">Enviar mensagem (WhatsApp)</option>
                <option value="Saiba mais">Saiba mais</option>
                <option value="Cadastre-se">Cadastre-se</option>
                <option value="Solicitar agora">Solicitar agora</option>
              </select>
            </div>
          </div>
          <button type="button" class="btn-oak-primary" onclick={executarGerador} disabled={carregando}>
            {carregando ? '⏳ Gerando 3 Variantes + Reels + Kit...' : '🚀 Gerar 3 Variantes Meta Ads + 6 Roteiros Reels + Kit 10-Min'}
          </button>
        </div>
      </section>

      <section class="oak-card">
        <h2>📌 Regras Oficiais Meta Ads (OpenAdKit Enforcer)</h2>
        <div class="limits-list">
          <div class="limit-item">
            <span>Texto Principal (Acima da Dobra)</span>
            <strong>Máx. 125 caracteres sem truncar ("...ver mais")</strong>
          </div>
          <div class="limit-item">
            <span>Título Mobile (Headline)</span>
            <strong>Máx. 27 caracteres no celular (40 no desktop)</strong>
          </div>
          <div class="limit-item">
            <span>Descrição do Link</span>
            <strong>Máx. 27 caracteres</strong>
          </div>
          <div class="limit-item">
            <span>Gancho de Vídeo (Reels / Stories)</span>
            <strong>Primeiros 3 segundos com quebra de padrão visual + texto em tela</strong>
          </div>
        </div>
      </section>
    </div>

    {#if resultadoGeracao}
      <!-- 3 VARIANTES META ADS (DOR, DESEJO, PROVA SOCIAL) -->
      <section class="oak-card">
        <div class="card-head-flex">
          <h2>📱 3 Variantes Meta Ads (Facebook + Instagram) — Prontas para Publicar</h2>
          <span class="sub-pill">{resultadoGeracao.recomendacao_publico}</span>
        </div>

        <div class="variants-grid">
          {#each resultadoGeracao.variantes_meta as v}
            <div class="variant-card">
              <div class="var-top">
                <span class="var-badge">{v.label}</span>
                <span class="var-angle">{v.angulo}</span>
              </div>
              <p class="var-copy">{v.primary_text}</p>
              <div class="var-meta-box">
                <div><strong>Título ({v.char_counts.headline}/27):</strong> {v.headline}</div>
                <div><strong>Descrição ({v.char_counts.description}/27):</strong> {v.description}</div>
                <div><strong>CTA:</strong> {v.cta_button} · <span class="ok-green">{v.status_validacao}</span></div>
              </div>
              <button type="button" class="btn-apply-var" onclick={() => usarVarianteNaCampanha(v)}>
                🪄 Aplicar {v.label} na Criação Assistida
              </button>
            </div>
          {/each}
        </div>
      </section>

      <!-- 6 IDEIAS DE REELS / TIKTOK / SHORTS COM AS 10 FÓRMULAS DE GANCHO -->
      <section class="oak-card">
        <h2>🎬 Gerador de Ideias de Reels & TikTok (10 Fórmulas de Gancho Validado)</h2>
        <div class="reels-grid">
          {#each resultadoGeracao.ideias_reels as r}
            <div class="reel-card">
              <div class="var-top">
                <span class="var-badge purple">Reels #{r.id} · {r.duracao_segundos}s</span>
                <span class="var-angle">{r.hook_formula}</span>
              </div>
              <div class="reel-hook">🎤 <strong>Gancho (0–3s):</strong> "{r.hook_0_3s}"</div>
              <div class="reel-brief">🎥 <strong>Cena / B-Roll:</strong> {r.visual_brief}</div>
              <div class="reel-script">📝 <strong>Locução:</strong> {r.script_locucao}</div>
              <div class="reel-foot">
                <span>⏰ {r.melhor_horario}</span>
                <button
                  type="button"
                  class="btn-mini-apply"
                  onclick={() =>
                    usarVarianteNaCampanha({
                      label: `Reels #${r.id}`,
                      primary_text: `${r.hook_0_3s}\n\n${r.script_locucao}`,
                      headline: r.cta.slice(0, 27),
                      description: 'Assista e chame no WhatsApp',
                      cta_button: genCta,
                    })}
                >
                  🪄 Usar Roteiro no Anúncio
                </button>
              </div>
            </div>
          {/each}
        </div>
      </section>

      <!-- WIZARD DE LANÇAMENTO EM 10 MINUTOS (WHATSAPP + GOOGLE RSA + CALENDÁRIO 7D) -->
      <div class="oak-grid-2">
        <section class="oak-card">
          <h2>💬 Sequência de 3 Mensagens de Fechamento no WhatsApp</h2>
          {#each resultadoGeracao.kit_lancamento.sequencia_whatsapp_3_etapas as zap}
            <div class="zap-step">
              <strong>{zap.etapa}</strong>
              <p>{zap.texto}</p>
            </div>
          {/each}
        </section>

        <section class="oak-card">
          <h2>📅 Calendário Editorial de 7 Dias + Google Search RSA</h2>
          <div class="cal-list">
            {#each resultadoGeracao.kit_lancamento.calendario_7_dias as d}
              <div class="cal-row">
                <span class="cal-day">{d.dia}</span>
                <span class="cal-fmt">{d.formato}</span>
                <span class="cal-theme">{d.tema}</span>
              </div>
            {/each}
          </div>
        </section>
      </div>
    {/if}

  {:else if subTab === 'brain'}
    <!-- ABA 2: CÉREBRO DA MARCA (BRAND BRAIN) + EXTRATOR DE URL + 8 TEMPLATES -->
    <section class="oak-card">
      <h2>🌐 Extrair Cérebro da Marca Automaticamente pela URL do Site</h2>
      <p class="muted-sub">
        Cole o site do seu negócio ou cliente: o OpenAdKit lê o título, meta tags, oferta e constrói o perfil estratégico em português.
      </p>
      <div class="url-extract-bar">
        <input
          type="text"
          placeholder="Ex: https://panificadorabompao.com.br ou https://autoprimecuritiba.com.br"
          bind:value={urlExtracao}
        />
        <button type="button" class="btn-oak-primary" onclick={extrairMarcaDeUrl} disabled={extraindoUrl}>
          {extraindoUrl ? '⏳ Extraindo Marca...' : '⚡ Extrair Cérebro da Marca pela URL'}
        </button>
      </div>
    </section>

    <section class="oak-card">
      <h2>⚡ Ou Escolha um Template de Nicho Pronto (100% Português-BR)</h2>
      <div class="tpl-grid">
        {#each templates as tpl}
          <div class="tpl-card">
            <div class="tpl-top">
              <span class="tpl-emoji">{tpl.emoji}</span>
              <strong>{tpl.nome}</strong>
            </div>
            <p>{tpl.descricao}</p>
            <button type="button" class="btn-apply-var" onclick={() => aplicarTemplateIndustria(tpl.slug)}>
              ✅ Ativar Este Perfil de Marca
            </button>
          </div>
        {/each}
      </div>
    </section>

    <section class="oak-card">
      <h2>🧠 Perfil Estratégico Ativo: {activeBrain.business_name}</h2>
      <div class="f-grid-2">
        <div class="f-row">
          <label for="bb-name">Nome da Empresa</label>
          <input id="bb-name" type="text" bind:value={activeBrain.business_name} />
        </div>
        <div class="f-row">
          <label for="bb-area">Área de Atendimento (Cidades)</label>
          <input id="bb-area" type="text" bind:value={activeBrain.service_area} />
        </div>
        <div class="f-row">
          <label for="bb-niche">Nicho & Posicionamento</label>
          <input id="bb-niche" type="text" bind:value={activeBrain.niche} />
        </div>
        <div class="f-row">
          <label for="bb-usp">Proposta Única de Valor (USP)</label>
          <input id="bb-usp" type="text" bind:value={activeBrain.usp} />
        </div>
      </div>
      <div class="wiz-actions-row">
        <button type="button" class="btn-oak-primary" onclick={salvarBrainAtual}>
          💾 Salvar Cérebro da Marca
        </button>
      </div>
    </section>

  {:else if subTab === 'score_steal'}
    <!-- ABA 3: CREATIVE SCORE (5 ALAVANCAS) & ESPIONAGEM STEAL & BEAT -->
    <div class="oak-grid-2">
      <!-- CREATIVE SCORE -->
      <section class="oak-card">
        <h2>🎯 Avaliador Brutal de Criativo (Creative Score — 5 Alavancas)</h2>
        <div class="oak-form">
          <div class="f-row">
            <label for="sc-txt">Texto Principal do Anúncio</label>
            <textarea id="sc-txt" rows="3" bind:value={scoreTexto}></textarea>
          </div>
          <div class="f-row">
            <label for="sc-tit">Título (Headline Mobile ≤27 chars)</label>
            <input id="sc-tit" type="text" bind:value={scoreTitulo} />
          </div>
          <button type="button" class="btn-oak-primary" onclick={executarCreativeScore}>
            🎯 Calcular Nota do Anúncio (0 a 10) + 3 Correções
          </button>
        </div>

        {#if resultadoScore}
          <div class="score-result-box">
            <div class="score-header">
              <div class="big-score">{resultadoScore.overall_score}<span>/10</span></div>
              <div>
                <div class="tier-verdict">{resultadoScore.tier_label}</div>
                <div class="ctr-pred">CTR Estimado: <strong>{resultadoScore.predicted_ctr_band}</strong></div>
              </div>
            </div>

            <div class="levers-list">
              {#each Object.values(resultadoScore.scores) as lev}
                <div class="lever-row">
                  <div class="lever-head">
                    <strong>{lev.label}</strong>
                    <span class="lever-num">{lev.score}/10</span>
                  </div>
                  <div class="lever-reason">{lev.reason}</div>
                </div>
              {/each}
            </div>

            <h3 class="fixes-title">🔧 3 Correções Exatas Recomendadas pela IA:</h3>
            {#each resultadoScore.top_3_fixes as fix}
              <div class="fix-item">
                <div><strong>{fix.alavanca}:</strong> <span class="gain-tag">{fix.ganho_esperado}</span></div>
                <div class="fix-replace">➡️ <em>"{fix.substituir_por}"</em></div>
              </div>
            {/each}

            <button
              type="button"
              class="btn-apply-var"
              onclick={() =>
                usarVarianteNaCampanha({
                  label: 'Copy Otimizada (Creative Score)',
                  primary_text: resultadoScore.copy_otimizada_pronta.texto_principal,
                  headline: resultadoScore.copy_otimizada_pronta.titulo,
                  description: 'Simule em 2 min no WhatsApp',
                  cta_button: resultadoScore.copy_otimizada_pronta.cta,
                })}
            >
              ✨ Aplicar Copy Otimizada na Campanha Assistida
            </button>
          </div>
        {/if}
      </section>

      <!-- ESPIONAGEM STEAL & BEAT -->
      <section class="oak-card">
        <h2>🕵️ Espionagem Competitiva: "Roube a Estrutura e Supere" (Steal & Beat)</h2>
        {#if resultadoSteal?.bibliotecas_oficiais}
          <div class="lib-links">
            {#each resultadoSteal.bibliotecas_oficiais as lib}
              <a href={lib.url} target="_blank" rel="noopener noreferrer" class="lib-chip">
                🔎 {lib.nome} ↗
              </a>
            {/each}
          </div>
        {/if}

        <div class="oak-form">
          <div class="f-row">
            <label for="st-conc">Texto do Anúncio do Concorrente (Cole da Biblioteca da Meta)</label>
            <textarea id="st-conc" rows="3" bind:value={concAnuncio}></textarea>
          </div>
          <div class="f-row">
            <label for="st-usp">Nosso Diferencial para Superar</label>
            <input id="st-usp" type="text" bind:value={concDiferencial} />
          </div>
          <button type="button" class="btn-oak-primary" onclick={executarStealAndBeat}>
            🕵️ Desmontar Concorrente & Gerar 3 Anúncios Superiores
          </button>
        </div>

        {#if resultadoSteal}
          <div class="teardown-box">
            <div><strong>Ponto Fraco Detectado no Concorrente:</strong> {resultadoSteal.teardown.ponto_fraco_exploravel}</div>
            <div><strong>Nosso Plano de Ataque:</strong> {resultadoSteal.plano_ataque.angulo_para_dominar}</div>
          </div>

          {#each resultadoSteal.beat_variants as bv}
            <div class="beat-card">
              <div class="var-top">
                <strong>{bv.label}</strong>
                <span class="gain-tag">{bv.estrategia}</span>
              </div>
              <p class="var-copy">{bv.primary_text}</p>
              <div class="why-wins">💡 <strong>Por que vence:</strong> {bv.por_que_vence}</div>
              <button
                type="button"
                class="btn-mini-apply"
                onclick={() =>
                  usarVarianteNaCampanha({
                    label: bv.label,
                    primary_text: bv.primary_text,
                    headline: bv.headline,
                    description: 'Atendimento em 2 min',
                    cta_button: bv.cta,
                  })}
              >
                🪄 Usar Este Anúncio na Campanha Assistida
              </button>
            </div>
          {/each}
        {/if}
      </section>
    </div>

  {:else if subTab === 'pipeboard_mcp'}
    <!-- ABA 4: PIPEBOARD META ADS MCP (SEGMENTAÇÃO OFICIAL & EXECUTOR GRAPH API) -->
    <div class="oak-grid-2">
      <!-- BUSCADOR DE INTERESSES OFICIAIS DA META (adinterest) -->
      <section class="oak-card">
        <h2>🎯 Buscar Interesses Oficiais na Meta Graph API (Pipeboard MCP)</h2>
        <div class="url-extract-bar">
          <input
            type="text"
            placeholder="Ex: Financiamento, Carros, Pizza, Imóveis..."
            bind:value={buscaInteresseQuery}
          />
          <button type="button" class="btn-oak-primary" onclick={buscarInteressesMcp}>
            🔍 Buscar Interesses
          </button>
        </div>

        <div class="mcp-results-list">
          {#each interessesEncontrados as it}
            <div class="mcp-item-row">
              <div>
                <strong>{it.name}</strong>
                <div class="mcp-sub">
                  ID: <code>{it.id}</code> · Público: {(it.audience_size_lower_bound || 50000).toLocaleString('pt-BR')} a {(it.audience_size_upper_bound || 500000).toLocaleString('pt-BR')} pessoas · <span class="src-tag">{it.fonte}</span>
                </div>
              </div>
              <button type="button" class="btn-mini-apply" onclick={() => adicionarInteresseNaCampanha(it.name)}>
                ➕ Adicionar na Campanha
              </button>
            </div>
          {/each}
        </div>
      </section>

      <!-- BUSCADOR DE CIDADES E REGIÕES OFICIAIS DA META (adgeolocation) -->
      <section class="oak-card">
        <h2>📍 Buscar Cidades e Regiões Oficiais da Meta (`adgeolocation`)</h2>
        <div class="url-extract-bar">
          <input
            type="text"
            placeholder="Ex: Curitiba, Campo Largo, São José dos Pinhais..."
            bind:value={buscaCidadeQuery}
          />
          <button type="button" class="btn-oak-primary" onclick={buscarCidadesMcp}>
            📍 Buscar Cidades
          </button>
        </div>

        <div class="mcp-results-list">
          {#each cidadesEncontradas as cid}
            <div class="mcp-item-row">
              <div>
                <strong>{cid.name} ({cid.region})</strong>
                <div class="mcp-sub">
                  Key Oficial Meta: <code>{cid.key}</code> · Tipo: {cid.type} · <span class="src-tag">{cid.fonte}</span>
                </div>
              </div>
              <button type="button" class="btn-mini-apply" onclick={() => adicionarCidadeNaCampanha(cid.name)}>
                ➕ Adicionar Cidade
              </button>
            </div>
          {/each}
        </div>
      </section>
    </div>

    <!-- EXECUTOR INTERATIVO DE TODAS AS FERRAMENTAS PIPEBOARD META ADS MCP -->
    <section class="oak-card">
      <h2>🔌 Console de Ferramentas Pipeboard Meta Ads MCP (`co.pipeboard/meta-ads-mcp`)</h2>
      <div class="mcp-console-bar">
        <select bind:value={mcpToolSelecionada}>
          {#each mcpTools as t}
            <option value={t.id}>{t.categoria} — {t.nome}</option>
          {/each}
        </select>
        <input type="text" placeholder="Parâmetro opcional (ex: Curitiba, Financiamento)..." bind:value={mcpToolQuery} />
        <button type="button" class="btn-oak-primary" onclick={rodarFerramentaMcpDireta}>
          ▶️ Executar Ferramenta MCP
        </button>
      </div>

      {#if mcpToolOutput}
        <pre class="mcp-json-out">{JSON.stringify(mcpToolOutput, null, 2)}</pre>
      {/if}
    </section>

  {:else if subTab === 'benchmarks'}
    <!-- ABA 5: BENCHMARKS DE MERCADO 2025/2026 & ESCOLA DE COPYWRITING (PAS, AIDA, BAB, 4 U's, SCHWARTZ) -->
    <section class="oak-card">
      <h2>📊 Benchmarks Reais de Tráfego Pago 2025/2026 (OpenAdKit Brasil)</h2>
      <div class="table-scroll">
        <table class="oak-table">
          <thead>
            <tr>
              <th>Métrica</th>
              <th>Plataforma</th>
              <th>Nicho / Referência</th>
              <th>Faixa Saudável</th>
              <th>Diagnóstico Prático</th>
            </tr>
          </thead>
          <tbody>
            {#each benchmarks as b}
              <tr>
                <td><strong>{b.metrica}</strong></td>
                <td>{b.plataforma}</td>
                <td>{b.nicho}</td>
                <td><span class="range-pill">{b.min} – {b.max} {b.unidade}</span></td>
                <td class="muted-sub">{b.nota}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </section>

    <section class="oak-card">
      <h2>🎓 Escola Interativa de Copywriting (PAS · AIDA · BAB · 4 U's · Escada de Schwartz)</h2>
      <div class="fw-grid">
        {#each frameworks as fw}
          <div class="fw-card">
            <div class="var-top">
              <span class="var-badge">{fw.sigla}</span>
              <strong>{fw.nome}</strong>
            </div>
            <div class="fw-best">📌 Ideal para: {fw.melhor_para}</div>
            <ul class="fw-steps">
              {#each fw.estrutura as passo}
                <li>{passo}</li>
              {/each}
            </ul>
            <div class="fw-example">
              <strong>Exemplo Pronto em Português:</strong>
              <p>"{fw.exemplo_pratico}"</p>
            </div>
          </div>
        {/each}
      </div>
    </section>
  {/if}
</div>

<style>
  .oak-wrap {
    display: flex;
    flex-direction: column;
    gap: 14px;
  }

  .oak-compact-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    padding: 10px 14px;
    background: var(--surface);
    border: 1px solid var(--border-strong);
    border-radius: 10px;
    flex-wrap: wrap;
  }

  .oak-compact-left {
    display: flex;
    align-items: center;
    gap: 12px;
    min-width: 0;
  }

  .btn-hamburger-oak {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: linear-gradient(135deg, #2563eb, #1d4ed8);
    color: #fff;
    border: 1px solid rgba(96, 165, 250, 0.45);
    border-radius: 8px;
    padding: 7px 12px;
    font-size: 0.78rem;
    font-weight: 800;
    cursor: pointer;
    white-space: nowrap;
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.25);
    transition: all 0.15s;
  }

  .btn-hamburger-oak:hover {
    transform: translateY(-1px);
    background: linear-gradient(135deg, #3b82f6, #2563eb);
  }

  .ham-lines {
    font-size: 0.95rem;
    line-height: 1;
  }

  .ham-count {
    background: rgba(255, 255, 255, 0.18);
    padding: 1px 6px;
    border-radius: 999px;
    font-size: 0.67rem;
  }

  .oak-active-title {
    display: flex;
    align-items: center;
    gap: 9px;
    min-width: 0;
  }

  .oak-mod-icon {
    font-size: 1.15rem;
  }

  .oak-mod-name {
    font-size: 0.88rem;
    font-weight: 800;
    color: #fff;
    display: flex;
    align-items: center;
    gap: 7px;
  }

  .oak-mini-badge {
    font-size: 0.65rem;
    font-weight: 700;
    padding: 1px 7px;
    border-radius: 999px;
    background: rgba(59, 130, 246, 0.18);
    color: #93c5fd;
    border: 1px solid rgba(59, 130, 246, 0.35);
  }

  .oak-mod-sub {
    font-size: 0.72rem;
    color: var(--muted);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 390px;
  }

  .oak-compact-right {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }

  .oak-inline-pills {
    display: inline-flex;
    background: #0b0e14;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 3px;
    gap: 2px;
    flex-wrap: wrap;
  }

  .oak-inline-pills button {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    background: transparent;
    color: var(--text-secondary);
    border: none;
    border-radius: 6px;
    padding: 5px 9px;
    font-size: 0.73rem;
    font-weight: 700;
    cursor: pointer;
    white-space: nowrap;
    transition: all 0.12s;
  }

  .oak-inline-pills button:hover {
    color: #fff;
    background: rgba(255, 255, 255, 0.05);
  }

  .oak-inline-pills button.active {
    background: var(--primary);
    color: #fff;
  }

  .brand-compact-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(16, 185, 129, 0.12);
    border: 1px solid rgba(16, 185, 129, 0.35);
    color: #6ee7b7;
    padding: 6px 10px;
    border-radius: 8px;
    font-size: 0.74rem;
    font-weight: 700;
    cursor: pointer;
    white-space: nowrap;
  }

  .brand-compact-name {
    max-width: 140px;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  /* MODAL HAMBÚRGUER */
  .oak-modal-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(3, 7, 18, 0.78);
    backdrop-filter: blur(5px);
    z-index: 200;
    display: grid;
    place-items: center;
    padding: 20px;
  }

  .oak-modal-drawer {
    width: 100%;
    max-width: 720px;
    background: #0f1420;
    border: 1px solid var(--border-strong);
    border-radius: 14px;
    padding: 22px;
    box-shadow: 0 24px 60px rgba(0, 0, 0, 0.65);
    display: flex;
    flex-direction: column;
    gap: 14px;
  }

  .oak-modal-head {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 12px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--border);
  }

  .oak-modal-head h3 {
    margin: 4px 0 4px;
    font-size: 1.1rem;
    font-weight: 800;
  }

  .oak-modal-head p {
    margin: 0;
    font-size: 0.78rem;
    color: var(--muted);
  }

  .oak-modal-close {
    background: var(--surface);
    border: 1px solid var(--border);
    color: var(--text-secondary);
    width: 30px;
    height: 30px;
    border-radius: 7px;
    cursor: pointer;
    font-weight: 700;
  }

  .oak-modal-section-title {
    font-size: 0.72rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--muted);
  }

  .oak-modal-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 10px;
  }

  @media (max-width: 680px) {
    .oak-modal-grid {
      grid-template-columns: 1fr;
    }
  }

  .oak-modal-item {
    background: #0b0e14;
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 12px 14px;
    text-align: left;
    color: var(--text);
    cursor: pointer;
    display: flex;
    flex-direction: column;
    gap: 5px;
    transition: all 0.14s;
  }

  .oak-modal-item:hover {
    border-color: var(--primary-light);
    background: rgba(37, 99, 235, 0.08);
  }

  .oak-modal-item.selected {
    border-color: #3b82f6;
    background: rgba(37, 99, 235, 0.16);
  }

  .oak-mi-top {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.83rem;
  }

  .oak-mi-icon {
    font-size: 1rem;
  }

  .oak-mi-badge {
    margin-left: auto;
    font-size: 0.65rem;
    font-weight: 700;
    padding: 2px 7px;
    border-radius: 999px;
    background: rgba(59, 130, 246, 0.2);
    color: #93c5fd;
  }

  .oak-modal-item p {
    margin: 0;
    font-size: 0.74rem;
    color: var(--muted);
    line-height: 1.35;
  }

  .oak-modal-brand-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 10px;
    padding-top: 12px;
    border-top: 1px solid var(--border);
    font-size: 0.76rem;
    flex-wrap: wrap;
  }

  .oak-modal-tpl-chips {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
  }

  .tpl-quick-chip {
    background: var(--surface);
    border: 1px solid var(--border);
    color: var(--text-secondary);
    border-radius: 999px;
    padding: 4px 9px;
    font-size: 0.7rem;
    font-weight: 600;
    cursor: pointer;
  }

  .tpl-quick-chip:hover {
    border-color: #3b82f6;
    color: #fff;
  }

  .oak-badges {
    display: flex;
    gap: 8px;
    margin-bottom: 4px;
    flex-wrap: wrap;
  }

  .badge-pill {
    font-size: 0.68rem;
    font-weight: 800;
    padding: 2px 8px;
    border-radius: 999px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  .badge-pill.gold {
    background: rgba(245, 158, 11, 0.2);
    color: #fbbf24;
    border: 1px solid rgba(245, 158, 11, 0.4);
  }

  .badge-pill.blue {
    background: rgba(59, 130, 246, 0.2);
    color: #93c5fd;
    border: 1px solid rgba(59, 130, 246, 0.4);
  }

  .badge-pill.green {
    background: rgba(16, 185, 129, 0.2);
    color: #6ee7b7;
    border: 1px solid rgba(16, 185, 129, 0.4);
  }

  .oak-grid-2 {
    display: grid;
    grid-template-columns: 1.15fr 0.85fr;
    gap: 16px;
  }

  @media (max-width: 980px) {
    .oak-grid-2 {
      grid-template-columns: 1fr;
    }
  }

  .oak-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 18px 20px;
  }

  .oak-card h2 {
    margin: 0 0 12px;
    font-size: 0.96rem;
    font-weight: 750;
  }

  .oak-form {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .f-row {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .f-row label {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--text-secondary);
  }

  .f-row input,
  .f-row select,
  .f-row textarea,
  .url-extract-bar input,
  .mcp-console-bar select,
  .mcp-console-bar input {
    background: #0b0e14;
    border: 1px solid var(--border-strong);
    color: #fff;
    border-radius: 8px;
    padding: 8px 11px;
    font-size: 0.82rem;
    font-family: inherit;
  }

  .f-grid-2 {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
  }

  .btn-oak-primary {
    background: linear-gradient(135deg, #2563eb, #1d4ed8);
    color: #fff;
    border: none;
    border-radius: 8px;
    padding: 10px 16px;
    font-size: 0.82rem;
    font-weight: 700;
    cursor: pointer;
  }

  .limits-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .limit-item {
    display: flex;
    flex-direction: column;
    gap: 2px;
    padding: 9px 11px;
    background: rgba(255, 255, 255, 0.03);
    border-radius: 8px;
    border-left: 3px solid #3b82f6;
    font-size: 0.78rem;
  }

  .limit-item span {
    color: var(--muted);
    font-size: 0.72rem;
  }

  .card-head-flex {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    margin-bottom: 12px;
    flex-wrap: wrap;
  }

  .card-head-flex h2 {
    margin: 0;
  }

  .sub-pill {
    font-size: 0.74rem;
    color: #93c5fd;
    background: rgba(37, 99, 235, 0.15);
    padding: 4px 10px;
    border-radius: 999px;
  }

  .variants-grid,
  .reels-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 14px;
  }

  @media (max-width: 1100px) {
    .variants-grid,
    .reels-grid {
      grid-template-columns: 1fr;
    }
  }

  .variant-card,
  .reel-card,
  .tpl-card,
  .fw-card,
  .beat-card {
    background: #0d111a;
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 14px;
    display: flex;
    flex-direction: column;
    gap: 9px;
  }

  .var-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
    font-size: 0.74rem;
  }

  .var-badge {
    background: rgba(37, 99, 235, 0.22);
    color: #60a5fa;
    padding: 2px 8px;
    border-radius: 6px;
    font-weight: 800;
  }

  .var-badge.purple {
    background: rgba(139, 92, 246, 0.22);
    color: #c4b5fd;
  }

  .var-angle {
    color: var(--muted);
    font-weight: 600;
  }

  .var-copy {
    margin: 0;
    font-size: 0.81rem;
    line-height: 1.45;
    color: #e2e8f0;
  }

  .var-meta-box {
    background: rgba(255, 255, 255, 0.03);
    padding: 8px 10px;
    border-radius: 7px;
    font-size: 0.74rem;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .ok-green {
    color: #34d399;
    font-weight: 700;
  }

  .btn-apply-var {
    margin-top: auto;
    background: rgba(16, 185, 129, 0.18);
    color: #6ee7b7;
    border: 1px solid rgba(16, 185, 129, 0.4);
    border-radius: 7px;
    padding: 8px 12px;
    font-size: 0.78rem;
    font-weight: 700;
    cursor: pointer;
  }

  .btn-apply-var:hover {
    background: #059669;
    color: #fff;
  }

  .reel-hook,
  .reel-brief,
  .reel-script {
    font-size: 0.77rem;
    line-height: 1.4;
  }

  .reel-foot {
    margin-top: auto;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
    font-size: 0.71rem;
    color: var(--muted);
    padding-top: 8px;
    border-top: 1px solid rgba(255, 255, 255, 0.06);
  }

  .btn-mini-apply {
    background: rgba(37, 99, 235, 0.2);
    color: #93c5fd;
    border: 1px solid rgba(59, 130, 246, 0.4);
    border-radius: 6px;
    padding: 5px 10px;
    font-size: 0.73rem;
    font-weight: 700;
    cursor: pointer;
    white-space: nowrap;
  }

  .btn-mini-apply:hover {
    background: var(--primary);
    color: #fff;
  }

  .zap-step {
    background: #0d111a;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 10px 12px;
    margin-bottom: 8px;
    font-size: 0.79rem;
  }

  .zap-step p {
    margin: 4px 0 0;
    color: var(--text-secondary);
  }

  .cal-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .cal-row {
    display: grid;
    grid-template-columns: 90px 135px 1fr;
    gap: 8px;
    padding: 7px 10px;
    background: #0d111a;
    border-radius: 7px;
    font-size: 0.76rem;
  }

  .cal-day {
    font-weight: 700;
    color: #60a5fa;
  }

  .cal-fmt {
    color: #34d399;
  }

  .url-extract-bar,
  .mcp-console-bar {
    display: flex;
    gap: 10px;
    margin-top: 10px;
    flex-wrap: wrap;
  }

  .url-extract-bar input,
  .mcp-console-bar input {
    flex: 1;
    min-width: 220px;
  }

  .tpl-grid,
  .fw-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }

  @media (max-width: 900px) {
    .tpl-grid,
    .fw-grid {
      grid-template-columns: 1fr;
    }
  }

  .tpl-top {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.9rem;
  }

  .tpl-emoji {
    font-size: 1.25rem;
  }

  .tpl-card p {
    margin: 0;
    font-size: 0.78rem;
    color: var(--muted);
  }

  .wiz-actions-row {
    margin-top: 12px;
    display: flex;
    justify-content: flex-end;
  }

  .score-result-box {
    margin-top: 14px;
    padding-top: 14px;
    border-top: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .score-header {
    display: flex;
    align-items: center;
    gap: 14px;
    background: #0d111a;
    padding: 12px;
    border-radius: 10px;
    border: 1px solid rgba(16, 185, 129, 0.35);
  }

  .big-score {
    font-size: 2rem;
    font-weight: 900;
    color: #34d399;
  }

  .big-score span {
    font-size: 0.9rem;
    color: var(--muted);
  }

  .tier-verdict {
    font-size: 0.84rem;
    font-weight: 800;
    color: #fff;
  }

  .ctr-pred {
    font-size: 0.76rem;
    color: var(--muted);
  }

  .lever-row,
  .fix-item,
  .teardown-box {
    background: #0d111a;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 9px 11px;
    font-size: 0.77rem;
  }

  .lever-head {
    display: flex;
    justify-content: space-between;
    margin-bottom: 3px;
  }

  .lever-num {
    color: #60a5fa;
    font-weight: 800;
  }

  .lever-reason {
    color: var(--muted);
  }

  .fixes-title {
    margin: 4px 0 0;
    font-size: 0.84rem;
  }

  .gain-tag {
    color: #34d399;
    font-size: 0.72rem;
    font-weight: 700;
  }

  .fix-replace {
    margin-top: 4px;
    color: #bfdbfe;
  }

  .lib-links {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    margin-bottom: 10px;
  }

  .lib-chip {
    background: rgba(37, 99, 235, 0.14);
    border: 1px solid rgba(59, 130, 246, 0.35);
    color: #93c5fd;
    text-decoration: none;
    padding: 5px 9px;
    border-radius: 6px;
    font-size: 0.72rem;
    font-weight: 600;
  }

  .why-wins {
    font-size: 0.74rem;
    color: #a7f3d0;
  }

  .mcp-results-list {
    margin-top: 12px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    max-height: 310px;
    overflow-y: auto;
  }

  .mcp-item-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 10px;
    padding: 9px 11px;
    background: #0d111a;
    border: 1px solid var(--border);
    border-radius: 8px;
    font-size: 0.79rem;
  }

  .mcp-sub {
    font-size: 0.71rem;
    color: var(--muted);
    margin-top: 2px;
  }

  .src-tag {
    color: #34d399;
    font-weight: 700;
  }

  .mcp-json-out {
    margin-top: 12px;
    background: #080b10;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px;
    font-size: 0.74rem;
    max-height: 260px;
    overflow: auto;
    color: #93c5fd;
  }

  .oak-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.8rem;
  }

  .oak-table th,
  .oak-table td {
    padding: 10px;
    border-bottom: 1px solid var(--border);
    text-align: left;
  }

  .range-pill {
    background: rgba(16, 185, 129, 0.16);
    color: #34d399;
    padding: 3px 8px;
    border-radius: 6px;
    font-weight: 700;
  }

  .muted-sub {
    color: var(--muted);
    font-size: 0.78rem;
  }

  .fw-best {
    font-size: 0.75rem;
    color: #93c5fd;
  }

  .fw-steps {
    margin: 4px 0;
    padding-left: 18px;
    font-size: 0.77rem;
    color: var(--text-secondary);
  }

  .fw-example {
    background: rgba(255, 255, 255, 0.03);
    padding: 8px 10px;
    border-radius: 7px;
    font-size: 0.75rem;
  }

  .fw-example p {
    margin: 4px 0 0;
    color: #d1fae5;
  }
</style>
