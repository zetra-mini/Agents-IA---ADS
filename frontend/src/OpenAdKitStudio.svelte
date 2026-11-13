<script>
  import { onMount } from 'svelte';

  let {
    secao = 'oak_anuncios', // 'oak_brain' | 'oak_anuncios' | 'oak_reels' | 'oak_score' | 'oak_espiao' | 'oak_mcp' | 'oak_benchmarks'
    planoAssistido = $bindable(),
    onAplicarNaCampanha = () => {},
    onIrParaSecao = () => {},
    onNotificar = () => {},
  } = $props();

  let carregando = $state(false);

  // Estado do Hub OpenAdKit + Pipeboard MCP
  let activeBrain = $state({
    business_name: 'AutoPrime Curitiba & Região',
    industry: 'Automotivo / Financiamento e Seminovos',
    niche: 'Veículos revisados e repasse de financiamento com aprovação rápida',
    service_area: 'Curitiba, Campo Largo',
    tone: 'Direto, confiável e transparente',
    usp: 'Simulação em 2 minutos pelo WhatsApp e veículos periciados com garantia',
  });
  let templates = $state([]);
  let benchmarks = $state([]);
  let frameworks = $state([]);
  let mcpTools = $state([]);

  // 1. Extrator de URL (Brand Brain)
  let urlExtracao = $state('');
  let extraindoUrl = $state(false);

  // 2. Gerador de Anúncios & Reels
  let genId = $state('meta_ads_3_angulos');
  let genProduto = $state('Repasse de Financiamento e Seminovos Revisados');
  let genPromocao = $state('Simulação em 2 minutos pelo WhatsApp + 1ª parcela para 60 dias');
  let genCidades = $state('Curitiba, Campo Largo');
  let genCta = $state('Enviar mensagem');
  let resultadoGeracao = $state(null);

  // 3. Creative Score (5 Alavancas)
  let scoreTexto = $state('');
  let scoreTitulo = $state('');
  let scoreCta = $state('Enviar mensagem');
  let resultadoScore = $state(null);

  // 4. Espionagem Steal & Beat
  let concNome = $state('Concorrente Tradicional');
  let concAnuncio = $state(
    'Venha conferir nosso estoque de veículos com ótimas taxas de financiamento. Faça uma visita em nossa loja!'
  );
  let concDiferencial = $state('Pré-aprovação em 2 minutos direto no WhatsApp e laudo cautelar 100% aprovado');
  let resultadoSteal = $state(null);

  // 5. Pipeboard Meta Ads MCP
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
        templates = data.templates || [];
        benchmarks = data.benchmarks || [];
        frameworks = data.frameworks_copy || [];
        mcpTools = data.pipeboard_mcp_tools || [];
        genProduto = activeBrain.niche || genProduto;
        genPromocao = activeBrain.usp || genPromocao;
        genCidades = activeBrain.service_area || genCidades;
      }
      scoreTexto =
        planoAssistido?.anuncios?.[0]?.texto_principal ||
        'Procurando repasse de financiamento com parcelas acessíveis em Curitiba e Campo Largo? Simule em 2 minutos no WhatsApp!';
      scoreTitulo = planoAssistido?.anuncios?.[0]?.titulo || 'Repasse Facilitado Curitiba';
      await Promise.all([
        executarGerador(),
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
        genProduto = activeBrain.niche || '';
        genPromocao = activeBrain.usp || '';
        genCidades = activeBrain.service_area || 'Curitiba';
        onNotificar(`Perfil "${activeBrain.business_name}" ativado com sucesso!`);
        await executarGerador();
      }
    } finally {
      carregando = false;
    }
  }

  async function extrairMarcaDeUrl() {
    if (!urlExtracao.trim()) {
      onNotificar('Digite a URL do site (ex: https://seusite.com.br).', 'error');
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
        onNotificar('Cérebro da Marca salvo com sucesso!');
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
      onNotificar(`Ferramenta "${mcpToolSelecionada}" executada!`);
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
    onNotificar(`Copy "${v.label}" aplicada na Criação de Campanha Assistida!`);
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

<div class="clean-section">
  {#if secao === 'oak_brain'}
    <!-- SEÇÃO DEDICADA 1: CÉREBRO DA MARCA (BRAND BRAIN) -->
    <div class="sec-header">
      <div>
        <h1>🧠 Cérebro da Marca (Brand Brain)</h1>
        <p>Configure os dados estratégicos da sua empresa ou extraia automaticamente pela URL do site.</p>
      </div>
      <div class="active-brand-tag">
        Marca Ativa: <strong>{activeBrain.business_name}</strong>
      </div>
    </div>

    <div class="clean-grid-2">
      <section class="clean-card">
        <h2>🌐 Auto-Extrator pela URL do Site</h2>
        <p class="card-desc">
          Informe o site ou landing page da empresa para preencher automaticamente posicionamento, oferta e público.
        </p>
        <div class="inline-search">
          <input
            type="text"
            placeholder="Ex: https://seusite.com.br"
            bind:value={urlExtracao}
          />
          <button type="button" class="btn-primary" onclick={extrairMarcaDeUrl} disabled={extraindoUrl}>
            {extraindoUrl ? 'Extraindo...' : '⚡ Extrair Site'}
          </button>
        </div>

        <div class="divider"></div>

        <h2>📝 Dados do Perfil Ativo</h2>
        <div class="form-stack">
          <div class="field-row">
            <label for="bb-name">Nome da Empresa</label>
            <input id="bb-name" type="text" bind:value={activeBrain.business_name} />
          </div>
          <div class="field-row">
            <label for="bb-area">Cidades / Região de Atendimento</label>
            <input id="bb-area" type="text" bind:value={activeBrain.service_area} />
          </div>
          <div class="field-row">
            <label for="bb-niche">Nicho & Produto Principal</label>
            <input id="bb-niche" type="text" bind:value={activeBrain.niche} />
          </div>
          <div class="field-row">
            <label for="bb-usp">Diferencial Único (USP / Oferta)</label>
            <input id="bb-usp" type="text" bind:value={activeBrain.usp} />
          </div>
          <button type="button" class="btn-primary" onclick={salvarBrainAtual}>
            💾 Salvar Cérebro da Marca
          </button>
        </div>
      </section>

      <section class="clean-card">
        <h2>⚡ Templates de Nicho Prontos (Brasil)</h2>
        <p class="card-desc">Clique em um modelo para carregar todas as configurações do setor em 1 clique.</p>
        <div class="tpl-list">
          {#each templates as tpl}
            <div class="tpl-row">
              <div>
                <strong>{tpl.emoji} {tpl.nome}</strong>
                <p>{tpl.descricao}</p>
              </div>
              <button type="button" class="btn-ghost-sm" onclick={() => aplicarTemplateIndustria(tpl.slug)}>
                Usar Modelo
              </button>
            </div>
          {/each}
        </div>
      </section>
    </div>

  {:else if secao === 'oak_anuncios'}
    <!-- SEÇÃO DEDICADA 2: GERADOR DE ANÚNCIOS META ADS (3 ÂNGULOS) -->
    <div class="sec-header">
      <div>
        <h1>✍️ Gerador de Copy Meta Ads (3 Ângulos)</h1>
        <p>Gere 3 variantes prontas (Dor/PAS, Desejo/BAB e Prova Social/AIDA) dentro do limite mobile da Meta.</p>
      </div>
      <button type="button" class="btn-ghost-sm" onclick={() => onIrParaSecao('oak_brain')}>
        🧠 Marca: <strong>{activeBrain.business_name}</strong> (Trocar)
      </button>
    </div>

    <section class="clean-card">
      <div class="form-row-4">
        <div class="field-row">
          <label for="oak-gen-prod">Produto / Oferta Principal</label>
          <input id="oak-gen-prod" type="text" bind:value={genProduto} />
        </div>
        <div class="field-row">
          <label for="oak-gen-usp">Diferencial / Promoção</label>
          <input id="oak-gen-usp" type="text" bind:value={genPromocao} />
        </div>
        <div class="field-row">
          <label for="oak-gen-cid">Cidades Alvo</label>
          <input id="oak-gen-cid" type="text" bind:value={genCidades} />
        </div>
        <div class="field-row">
          <label for="oak-gen-cta">Botão CTA</label>
          <select id="oak-gen-cta" bind:value={genCta}>
            <option value="Enviar mensagem">Enviar mensagem (WhatsApp)</option>
            <option value="Saiba mais">Saiba mais</option>
            <option value="Cadastre-se">Cadastre-se</option>
            <option value="Solicitar agora">Solicitar agora</option>
          </select>
        </div>
      </div>
      <div class="form-actions-bar">
        <span class="rule-hint">📏 Limite Mobile aplicado: Título ≤ 27 caracteres · Acima da dobra ≤ 125 caracteres</span>
        <button type="button" class="btn-primary" onclick={executarGerador} disabled={carregando}>
          {carregando ? '⏳ Gerando...' : '🚀 Gerar 3 Variantes de Anúncio'}
        </button>
      </div>
    </section>

    {#if resultadoGeracao}
      <div class="cards-grid-3">
        {#each resultadoGeracao.variantes_meta as v}
          <div class="clean-card variant-item">
            <div class="item-top">
              <span class="badge-blue">{v.label}</span>
              <span class="muted-label">{v.angulo}</span>
            </div>
            <p class="copy-body">{v.primary_text}</p>
            <div class="meta-summary">
              <div><strong>Título ({v.char_counts.headline}/27):</strong> {v.headline}</div>
              <div><strong>Descrição ({v.char_counts.description}/27):</strong> {v.description}</div>
              <div><strong>CTA:</strong> {v.cta_button} · <span class="text-green">{v.status_validacao}</span></div>
            </div>
            <button type="button" class="btn-apply" onclick={() => usarVarianteNaCampanha(v)}>
              🪄 Usar na Criação Assistida
            </button>
          </div>
        {/each}
      </div>
    {/if}

  {:else if secao === 'oak_reels'}
    <!-- SEÇÃO DEDICADA 3: ROTEIROS DE REELS, TIKTOK & SHORTS + SEQUÊNCIA WHATSAPP -->
    <div class="sec-header">
      <div>
        <h1>🎬 Roteiros de Reels & Funil WhatsApp</h1>
        <p>6 roteiros de vídeo curto com ganchos de 3 segundos validados + sequência de fechamento no WhatsApp.</p>
      </div>
      <button type="button" class="btn-primary" onclick={executarGerador} disabled={carregando}>
        🔄 Atualizar Roteiros para {activeBrain.business_name}
      </button>
    </div>

    {#if resultadoGeracao}
      <div class="cards-grid-3">
        {#each resultadoGeracao.ideias_reels as r}
          <div class="clean-card variant-item">
            <div class="item-top">
              <span class="badge-purple">Reels #{r.id} · {r.duracao_segundos}s</span>
              <span class="muted-label">{r.hook_formula}</span>
            </div>
            <div class="script-block">🎤 <strong>Gancho (0–3s):</strong> "{r.hook_0_3s}"</div>
            <div class="script-block">🎥 <strong>Cena Visual:</strong> {r.visual_brief}</div>
            <div class="script-block">📝 <strong>Locução:</strong> {r.script_locucao}</div>
            <div class="item-foot">
              <span>⏰ {r.melhor_horario}</span>
              <button
                type="button"
                class="btn-ghost-sm"
                onclick={() =>
                  usarVarianteNaCampanha({
                    label: `Reels #${r.id}`,
                    primary_text: `${r.hook_0_3s}\n\n${r.script_locucao}`,
                    headline: r.cta.slice(0, 27),
                    description: 'Assista e chame no WhatsApp',
                    cta_button: genCta,
                  })}
              >
                🪄 Usar na Campanha
              </button>
            </div>
          </div>
        {/each}
      </div>

      <section class="clean-card">
        <h2>💬 Sequência de 3 Mensagens para Fechamento no WhatsApp</h2>
        <div class="cards-grid-3">
          {#each resultadoGeracao.kit_lancamento.sequencia_whatsapp_3_etapas as zap}
            <div class="sub-box">
              <strong>{zap.etapa}</strong>
              <p>{zap.texto}</p>
            </div>
          {/each}
        </div>
      </section>
    {/if}

  {:else if secao === 'oak_score'}
    <!-- SEÇÃO DEDICADA 4: AVALIADOR CREATIVE SCORE (5 ALAVANCAS) -->
    <div class="sec-header">
      <div>
        <h1>🎯 Avaliador de Criativo (Creative Score — 5 Alavancas)</h1>
        <p>Auditoria de 0 a 10 para prever o CTR e corrigir pontos fracos antes de gastar orçamento.</p>
      </div>
    </div>

    <div class="clean-grid-2">
      <section class="clean-card">
        <h2>📝 Texto do Anúncio para Avaliar</h2>
        <div class="form-stack">
          <div class="field-row">
            <label for="sc-txt">Texto Principal (Copy)</label>
            <textarea id="sc-txt" rows="5" bind:value={scoreTexto}></textarea>
          </div>
          <div class="field-row">
            <label for="sc-tit">Título Mobile (Headline ≤ 27 caracteres)</label>
            <input id="sc-tit" type="text" bind:value={scoreTitulo} />
          </div>
          <button type="button" class="btn-primary" onclick={executarCreativeScore}>
            🎯 Calcular Nota (0 a 10) & Gerar Correções
          </button>
        </div>
      </section>

      {#if resultadoScore}
        <section class="clean-card">
          <div class="score-banner">
            <div class="score-circle">{resultadoScore.overall_score}<span>/10</span></div>
            <div>
              <div class="score-verdict">{resultadoScore.tier_label}</div>
              <div class="card-desc">CTR Estimado: <strong>{resultadoScore.predicted_ctr_band}</strong></div>
            </div>
          </div>

          <div class="levers-stack">
            {#each Object.values(resultadoScore.scores) as lev}
              <div class="lever-line">
                <div class="lever-top">
                  <strong>{lev.label}</strong>
                  <span class="badge-blue">{lev.score}/10</span>
                </div>
                <div class="card-desc">{lev.reason}</div>
              </div>
            {/each}
          </div>

          <div class="divider"></div>
          <h3>🔧 3 Ajustes Recomendados:</h3>
          {#each resultadoScore.top_3_fixes as fix}
            <div class="fix-box">
              <div><strong>{fix.alavanca}:</strong> <span class="text-green">{fix.ganho_esperado}</span></div>
              <div class="card-desc">➡️ "{fix.substituir_por}"</div>
            </div>
          {/each}

          <button
            type="button"
            class="btn-apply"
            onclick={() =>
              usarVarianteNaCampanha({
                label: 'Copy Otimizada (Creative Score)',
                primary_text: resultadoScore.copy_otimizada_pronta.texto_principal,
                headline: resultadoScore.copy_otimizada_pronta.titulo,
                description: 'Simule em 2 min no WhatsApp',
                cta_button: resultadoScore.copy_otimizada_pronta.cta,
              })}
          >
            ✨ Aplicar Copy Otimizada na Criação Assistida
          </button>
        </section>
      {/if}
    </div>

  {:else if secao === 'oak_espiao'}
    <!-- SEÇÃO DEDICADA 5: ESPIONAGEM DE CONCORRENTES (STEAL & BEAT) -->
    <div class="sec-header">
      <div>
        <h1>🕵️ Espionagem de Concorrentes (Steal & Beat)</h1>
        <p>Analise o anúncio de qualquer concorrente, identifique o ponto cego e gere 3 anúncios superiores.</p>
      </div>
      {#if resultadoSteal?.bibliotecas_oficiais}
        <div class="ext-links">
          {#each resultadoSteal.bibliotecas_oficiais as lib}
            <a href={lib.url} target="_blank" rel="noopener noreferrer" class="btn-ghost-sm">
              🔎 {lib.nome} ↗
            </a>
          {/each}
        </div>
      {/if}
    </div>

    <section class="clean-card">
      <div class="clean-grid-2">
        <div class="field-row">
          <label for="st-conc">Texto do Anúncio do Concorrente (Cole da Biblioteca de Anúncios)</label>
          <textarea id="st-conc" rows="3" bind:value={concAnuncio}></textarea>
        </div>
        <div class="form-stack">
          <div class="field-row">
            <label for="st-usp">Nosso Diferencial para Superar o Concorrente</label>
            <input id="st-usp" type="text" bind:value={concDiferencial} />
          </div>
          <button type="button" class="btn-primary" onclick={executarStealAndBeat}>
            🕵️ Desmontar Concorrente & Gerar 3 Variantes Superiores
          </button>
        </div>
      </div>
    </section>

    {#if resultadoSteal}
      <section class="clean-card">
        <div class="clean-grid-2">
          <div class="sub-box">
            <strong>⚠️ Ponto Fraco Detectado no Concorrente</strong>
            <p>{resultadoSteal.teardown.ponto_fraco_exploravel}</p>
          </div>
          <div class="sub-box">
            <strong>🚀 Nosso Plano de Ataque</strong>
            <p>{resultadoSteal.plano_ataque.angulo_para_dominar}</p>
          </div>
        </div>
      </section>

      <div class="cards-grid-3">
        {#each resultadoSteal.beat_variants as bv}
          <div class="clean-card variant-item">
            <div class="item-top">
              <span class="badge-blue">{bv.label}</span>
              <span class="text-green">{bv.estrategia}</span>
            </div>
            <p class="copy-body">{bv.primary_text}</p>
            <div class="card-desc">💡 <strong>Por que vence:</strong> {bv.por_que_vence}</div>
            <button
              type="button"
              class="btn-apply"
              onclick={() =>
                usarVarianteNaCampanha({
                  label: bv.label,
                  primary_text: bv.primary_text,
                  headline: bv.headline,
                  description: 'Atendimento em 2 min',
                  cta_button: bv.cta,
                })}
            >
              🪄 Usar na Criação Assistida
            </button>
          </div>
        {/each}
      </div>
    {/if}

  {:else if secao === 'oak_mcp'}
    <!-- SEÇÃO DEDICADA 6: PIPEBOARD META ADS MCP (INTERESSES & CIDADES GRAPH API) -->
    <div class="sec-header">
      <div>
        <h1>🔌 Segmentação Oficial Meta Graph API (Pipeboard MCP)</h1>
        <p>Consulte interesses oficiais (IDs reais) e cidades diretamente na API da Meta e adicione à sua campanha.</p>
      </div>
    </div>

    <div class="clean-grid-2">
      <section class="clean-card">
        <h2>🎯 Buscar Interesses Oficiais (`adinterest`)</h2>
        <div class="inline-search">
          <input
            type="text"
            placeholder="Ex: Financiamento, Veículos, Pizzaria..."
            bind:value={buscaInteresseQuery}
          />
          <button type="button" class="btn-primary" onclick={buscarInteressesMcp}>
            🔍 Buscar
          </button>
        </div>

        <div class="result-list">
          {#each interessesEncontrados as it}
            <div class="result-row">
              <div>
                <strong>{it.name}</strong>
                <div class="card-desc">
                  ID: <code>{it.id}</code> · Audiência: {(it.audience_size_lower_bound || 50000).toLocaleString('pt-BR')}–{(it.audience_size_upper_bound || 500000).toLocaleString('pt-BR')}
                </div>
              </div>
              <button type="button" class="btn-ghost-sm" onclick={() => adicionarInteresseNaCampanha(it.name)}>
                ➕ Adicionar
              </button>
            </div>
          {/each}
        </div>
      </section>

      <section class="clean-card">
        <h2>📍 Buscar Cidades e Regiões (`adgeolocation`)</h2>
        <div class="inline-search">
          <input
            type="text"
            placeholder="Ex: Curitiba, Campo Largo..."
            bind:value={buscaCidadeQuery}
          />
          <button type="button" class="btn-primary" onclick={buscarCidadesMcp}>
            📍 Buscar
          </button>
        </div>

        <div class="result-list">
          {#each cidadesEncontradas as cid}
            <div class="result-row">
              <div>
                <strong>{cid.name} ({cid.region})</strong>
                <div class="card-desc">Key Meta: <code>{cid.key}</code> · Tipo: {cid.type}</div>
              </div>
              <button type="button" class="btn-ghost-sm" onclick={() => adicionarCidadeNaCampanha(cid.name)}>
                ➕ Adicionar
              </button>
            </div>
          {/each}
        </div>
      </section>
    </div>

    <section class="clean-card">
      <h2>🛠️ Executor Direto de Ferramentas Pipeboard MCP</h2>
      <div class="inline-search">
        <select bind:value={mcpToolSelecionada}>
          {#each mcpTools as t}
            <option value={t.id}>{t.categoria} — {t.nome}</option>
          {/each}
        </select>
        <input type="text" placeholder="Parâmetro opcional..." bind:value={mcpToolQuery} />
        <button type="button" class="btn-primary" onclick={rodarFerramentaMcpDireta}>
          ▶️ Executar
        </button>
      </div>
      {#if mcpToolOutput}
        <pre class="json-viewer">{JSON.stringify(mcpToolOutput, null, 2)}</pre>
      {/if}
    </section>

  {:else if secao === 'oak_benchmarks'}
    <!-- SEÇÃO DEDICADA 7: BENCHMARKS BRASIL & FRAMEWORKS DE COPY -->
    <div class="sec-header">
      <div>
        <h1>📚 Benchmarks Brasil 2025/2026 & Frameworks de Copy</h1>
        <p>Métricas de referência no mercado brasileiro e estruturas clássicas de persuasão.</p>
      </div>
    </div>

    <section class="clean-card">
      <h2>📊 Tabela de Benchmarks por Plataforma (Brasil)</h2>
      <div class="table-wrap">
        <table class="clean-table">
          <thead>
            <tr>
              <th>Métrica</th>
              <th>Plataforma</th>
              <th>Nicho</th>
              <th>Faixa Saudável</th>
              <th>Diagnóstico</th>
            </tr>
          </thead>
          <tbody>
            {#each benchmarks as b}
              <tr>
                <td><strong>{b.metrica}</strong></td>
                <td>{b.plataforma}</td>
                <td>{b.nicho}</td>
                <td><span class="badge-blue">{b.min} – {b.max} {b.unidade}</span></td>
                <td class="card-desc">{b.nota}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </section>

    <div class="cards-grid-3">
      {#each frameworks as fw}
        <div class="clean-card variant-item">
          <div class="item-top">
            <span class="badge-blue">{fw.sigla}</span>
            <strong>{fw.nome}</strong>
          </div>
          <div class="card-desc">📌 Ideal para: {fw.melhor_para}</div>
          <ul class="clean-list">
            {#each fw.estrutura as passo}
              <li>{passo}</li>
            {/each}
          </ul>
          <div class="sub-box">
            <strong>Exemplo em Português:</strong>
            <p>"{fw.exemplo_pratico}"</p>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  .clean-section {
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .sec-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 16px;
    padding-bottom: 14px;
    border-bottom: 1px solid var(--border);
    flex-wrap: wrap;
  }

  .sec-header h1 {
    margin: 0;
    font-size: 1.28rem;
    font-weight: 700;
    letter-spacing: -0.02em;
  }

  .sec-header p {
    margin: 4px 0 0;
    font-size: 0.83rem;
    color: var(--muted);
  }

  .active-brand-tag {
    background: rgba(16, 185, 129, 0.12);
    border: 1px solid rgba(16, 185, 129, 0.3);
    color: #6ee7b7;
    padding: 7px 13px;
    border-radius: 8px;
    font-size: 0.78rem;
  }

  .clean-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 14px;
  }

  .clean-card h2 {
    margin: 0;
    font-size: 0.96rem;
    font-weight: 700;
  }

  .clean-card h3 {
    margin: 0;
    font-size: 0.86rem;
    font-weight: 700;
  }

  .card-desc {
    margin: 0;
    font-size: 0.78rem;
    color: var(--muted);
    line-height: 1.45;
  }

  .clean-grid-2 {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
  }

  .cards-grid-3 {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 18px;
  }

  .form-row-4 {
    display: grid;
    grid-template-columns: 1.3fr 1.3fr 1fr 0.9fr;
    gap: 12px;
  }

  @media (max-width: 1100px) {
    .clean-grid-2,
    .cards-grid-3,
    .form-row-4 {
      grid-template-columns: 1fr;
    }
  }

  .form-stack {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .field-row {
    display: flex;
    flex-direction: column;
    gap: 5px;
  }

  .field-row label {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--text-secondary);
  }

  .field-row input,
  .field-row select,
  .field-row textarea,
  .inline-search input,
  .inline-search select {
    background: #0b0e14;
    border: 1px solid var(--border-strong);
    color: #fff;
    border-radius: 8px;
    padding: 9px 12px;
    font-size: 0.82rem;
    font-family: inherit;
  }

  .inline-search {
    display: flex;
    gap: 10px;
  }

  .inline-search input {
    flex: 1;
  }

  .form-actions-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    padding-top: 8px;
    border-top: 1px solid var(--border);
    flex-wrap: wrap;
  }

  .rule-hint {
    font-size: 0.76rem;
    color: var(--muted);
  }

  .btn-primary {
    background: var(--primary);
    color: #fff;
    border: none;
    border-radius: 8px;
    padding: 9px 16px;
    font-size: 0.82rem;
    font-weight: 700;
    cursor: pointer;
    white-space: nowrap;
  }

  .btn-primary:hover {
    background: #1d4ed8;
  }

  .btn-ghost-sm {
    background: rgba(255, 255, 255, 0.04);
    color: var(--text-secondary);
    border: 1px solid var(--border-strong);
    border-radius: 7px;
    padding: 6px 12px;
    font-size: 0.76rem;
    font-weight: 600;
    cursor: pointer;
    text-decoration: none;
    white-space: nowrap;
  }

  .btn-ghost-sm:hover {
    border-color: var(--primary-light);
    color: #fff;
  }

  .btn-apply {
    margin-top: auto;
    background: rgba(16, 185, 129, 0.16);
    color: #6ee7b7;
    border: 1px solid rgba(16, 185, 129, 0.38);
    border-radius: 8px;
    padding: 9px 14px;
    font-size: 0.8rem;
    font-weight: 700;
    cursor: pointer;
  }

  .btn-apply:hover {
    background: #059669;
    color: #fff;
  }

  .variant-item {
    justify-content: flex-start;
  }

  .item-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
    font-size: 0.76rem;
  }

  .badge-blue {
    background: rgba(37, 99, 235, 0.2);
    color: #93c5fd;
    padding: 3px 9px;
    border-radius: 6px;
    font-size: 0.72rem;
    font-weight: 700;
  }

  .badge-purple {
    background: rgba(139, 92, 246, 0.2);
    color: #c4b5fd;
    padding: 3px 9px;
    border-radius: 6px;
    font-size: 0.72rem;
    font-weight: 700;
  }

  .muted-label {
    color: var(--muted);
    font-size: 0.74rem;
  }

  .copy-body {
    margin: 0;
    font-size: 0.83rem;
    line-height: 1.5;
    color: #e2e8f0;
    white-space: pre-line;
  }

  .meta-summary {
    background: #0b0e14;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 10px 12px;
    font-size: 0.76rem;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .text-green {
    color: #34d399;
    font-weight: 700;
  }

  .tpl-list,
  .result-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
    max-height: 380px;
    overflow-y: auto;
  }

  .tpl-row,
  .result-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    padding: 10px 12px;
    background: #0b0e14;
    border: 1px solid var(--border);
    border-radius: 8px;
  }

  .tpl-row p {
    margin: 2px 0 0;
    font-size: 0.74rem;
    color: var(--muted);
  }

  .divider {
    height: 1px;
    background: var(--border);
    margin: 4px 0;
  }

  .script-block {
    font-size: 0.79rem;
    line-height: 1.45;
  }

  .item-foot {
    margin-top: auto;
    padding-top: 10px;
    border-top: 1px solid var(--border);
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.73rem;
    color: var(--muted);
  }

  .sub-box {
    background: #0b0e14;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px;
    font-size: 0.8rem;
  }

  .sub-box p {
    margin: 6px 0 0;
    color: var(--text-secondary);
    line-height: 1.45;
  }

  .score-banner {
    display: flex;
    align-items: center;
    gap: 14px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--border);
  }

  .score-circle {
    font-size: 1.8rem;
    font-weight: 900;
    color: #34d399;
    background: rgba(16, 185, 129, 0.12);
    border: 1px solid rgba(16, 185, 129, 0.35);
    padding: 8px 14px;
    border-radius: 10px;
  }

  .score-circle span {
    font-size: 0.85rem;
    color: var(--muted);
  }

  .score-verdict {
    font-size: 0.95rem;
    font-weight: 800;
  }

  .levers-stack {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .lever-line {
    background: #0b0e14;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 8px 12px;
  }

  .lever-top {
    display: flex;
    justify-content: space-between;
    font-size: 0.78rem;
    margin-bottom: 2px;
  }

  .fix-box {
    background: rgba(37, 99, 235, 0.08);
    border-left: 3px solid #3b82f6;
    padding: 8px 10px;
    border-radius: 6px;
    font-size: 0.78rem;
  }

  .ext-links {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }

  .json-viewer {
    background: #070a0f;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px;
    font-size: 0.74rem;
    color: #93c5fd;
    max-height: 240px;
    overflow: auto;
  }

  .table-wrap {
    overflow-x: auto;
  }

  .clean-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.8rem;
  }

  .clean-table th,
  .clean-table td {
    padding: 10px 12px;
    border-bottom: 1px solid var(--border);
    text-align: left;
  }

  .clean-table th {
    font-size: 0.72rem;
    text-transform: uppercase;
    color: var(--muted);
  }

  .clean-list {
    margin: 0;
    padding-left: 18px;
    font-size: 0.78rem;
    color: var(--text-secondary);
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
</style>
