<script>
  import { onMount } from 'svelte';

  let { plano = null, criativos = [], autoStart = true } = $props();

  let stageEl = $state(null);
  let cursorX = $state(80);
  let cursorY = $state(60);
  let clicking = $state(false);
  let cursorLabel = $state('Agente browser-use pronto');
  let stepIndex = $state(0);
  let running = $state(false);

  // Estado visual do Gerenciador de Anúncios Meta Ads
  let viewMode = $state('table'); // 'table' | 'modal_objetivo' | 'editor_campanha' | 'editor_conjunto' | 'editor_anuncio'
  let selectedObjective = $state('');
  let typedCampaignName = $state('');
  let specialCategory = $state('Nenhuma');
  let cboEnabled = $state(false);
  let typedBudget = $state('');
  let typedAdsetName = $state('');
  let addedLocations = $state([]);
  let typedAgeRange = $state('18 - 65+');
  let addedInterests = $state([]);
  let typedAdName = $state('');
  let attachedMedia = $state('');
  let typedPrimaryText = $state('');
  let typedHeadline = $state('');
  let selectedCta = $state('Saiba mais');
  let activeField = $state('');

  let savedCampaigns = $state([
    {
      id: 'camp-0',
      active: false,
      nome: ' Institucional_Marca_PR',
      veiculacao: 'Desativada',
      estrategia: 'Orçamento do conjunto (ABO)',
      orcamento: 'R$ 80,00/dia',
      resultados: '142 cadastros',
    },
  ]);

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  function moveToPercent(xPct, yPct, label) {
    cursorX = xPct;
    cursorY = yPct;
    if (label) cursorLabel = label;
  }

  async function clickAt(xPct, yPct, label, fieldId = '') {
    activeField = fieldId;
    moveToPercent(xPct, yPct, label);
    await sleep(520);
    clicking = true;
    await sleep(220);
    clicking = false;
    await sleep(140);
  }

  async function typeText(setter, fullText, speed = 22) {
    setter('');
    let current = '';
    for (let i = 0; i < fullText.length; i++) {
      current += fullText[i];
      setter(current);
      await sleep(speed);
    }
  }

  export async function iniciarDemonstracaoVisual() {
    if (running) return;
    running = true;

    const nomeCampanha =
      plano?.nome_campanha || 'Campanha CBO - Leads Repasse Financiamento - Campo Largo';
    const orcamentoNum = plano?.orcamento_diario_brl || 500;
    const orcamentoFmt = `R$ ${orcamentoNum.toFixed(2).replace('.', ',')}`;
    const conjunto = plano?.conjuntos?.[0] || {
      nome: 'Conjunto 01 - Campo Largo, Curitiba (Raio 25km)',
      publico: {
        idade_minima: 23,
        idade_maxima: 58,
        localizacoes: ['Campo Largo, PR (+25 km)', 'Curitiba, PR (+25 km)'],
        interesses_sugeridos: ['Financiamento de veículos', 'Carros usados', 'Crédito'],
      },
    };
    const anuncio = plano?.anuncios?.[0] || {
      nome: 'Anúncio 01 - Repasse de Financiamento Sem Burocracia',
      titulo: 'Repasse de Financiamento Facilitado',
      texto_principal:
        'Procurando repasse de financiamento com parcelas acessíveis na sua região? Confira veículos selecionados em Campo Largo e Curitiba.',
      cta: 'Saiba mais',
      arquivo_criativo: criativos?.[0]?.nome || 'criativo_repasse_oferta.png',
    };

    // Reset inicial
    viewMode = 'table';
    selectedObjective = '';
    typedCampaignName = '';
    specialCategory = 'Nenhuma';
    cboEnabled = false;
    typedBudget = '';
    typedAdsetName = '';
    addedLocations = [];
    typedAgeRange = '18 - 65+';
    addedInterests = [];
    typedAdName = '';
    attachedMedia = '';
    typedPrimaryText = '';
    typedHeadline = '';
    selectedCta = 'Saiba mais';
    stepIndex = 1;

    await sleep(350);

    // PASSO 1: Clicar no botão verde "+ Criar"
    await clickAt(11, 25, 'Passo 1/7: Clicando em "+ Criar" no Gerenciador de Anúncios', 'btn-criar');
    viewMode = 'modal_objetivo';
    await sleep(400);

    // PASSO 2: Selecionar objetivo "Cadastros (Leads)" e clicar em Continuar
    stepIndex = 2;
    await clickAt(38, 52, 'Passo 2/7: Selecionando objetivo "Cadastros (Leads)"', 'obj-leads');
    selectedObjective = 'Leads';
    await sleep(350);
    await clickAt(66, 78, 'Passo 2/7: Clicando em "Continuar"', 'btn-continuar');
    viewMode = 'editor_campanha';
    await sleep(400);

    // PASSO 3: Configurar Campanha (Nome, Categoria Crédito, CBO e Orçamento R$ 500/dia)
    stepIndex = 3;
    await clickAt(42, 34, 'Passo 3/7: Digitando Nome da Campanha', 'input-camp-nome');
    await typeText((v) => (typedCampaignName = v), nomeCampanha, 18);

    await clickAt(42, 49, 'Passo 3/7: Marcando Categoria de Anúncio Especial: Crédito', 'select-cat');
    specialCategory = 'Crédito (Financiamento / Repasse)';
    await sleep(300);

    await clickAt(36, 63, 'Passo 3/7: Ativando Orçamento da Campanha Advantage+ (CBO)', 'toggle-cbo');
    cboEnabled = true;
    await sleep(300);

    await clickAt(46, 74, `Passo 3/7: Definindo orçamento diário (${orcamentoFmt})`, 'input-budget');
    await typeText((v) => (typedBudget = v), orcamentoFmt, 38);
    await sleep(300);

    await clickAt(86, 88, 'Passo 3/7: Avançando para o Conjunto de Anúncios', 'btn-avancar-1');
    viewMode = 'editor_conjunto';
    await sleep(400);

    // PASSO 4: Configurar Conjunto de Anúncios (Cidades, Idade, Interesses)
    stepIndex = 4;
    await clickAt(42, 33, 'Passo 4/7: Digitando Nome do Conjunto de Anúncios', 'input-adset-nome');
    await typeText((v) => (typedAdsetName = v), conjunto.nome, 18);

    await clickAt(44, 50, 'Passo 4/7: Adicionando localização Campo Largo e Curitiba (Raio 25km)', 'input-loc');
    for (const loc of conjunto.publico.localizacoes) {
      addedLocations = [...addedLocations, loc];
      await sleep(320);
    }

    await clickAt(44, 65, 'Passo 4/7: Ajustando faixa etária e interesses de financiamento', 'input-idade');
    typedAgeRange = `${conjunto.publico.idade_minima} a ${conjunto.publico.idade_maxima} anos`;
    addedInterests = conjunto.publico.interesses_sugeridos?.length
      ? conjunto.publico.interesses_sugeridos
      : ['Financiamento de veículos', 'Carros usados', 'Crédito'];
    await sleep(400);

    await clickAt(86, 88, 'Passo 4/7: Avançando para o Anúncio (Copy + Criativo)', 'btn-avancar-2');
    viewMode = 'editor_anuncio';
    await sleep(400);

    // PASSO 5: Configurar Anúncio (Upload de Criativo da Pasta + Copywriter)
    stepIndex = 5;
    await clickAt(36, 32, 'Passo 5/7: Preenchendo Nome do Anúncio', 'input-ad-nome');
    await typeText((v) => (typedAdName = v), anuncio.nome, 18);

    stepIndex = 6;
    const nomeArquivo =
      anuncio.arquivo_criativo || criativos?.[0]?.nome || 'criativo_repasse_curitiba.png';
    await clickAt(36, 46, `Passo 6/7: Anexando criativo da pasta (${nomeArquivo})`, 'btn-upload-media');
    attachedMedia = nomeArquivo;
    await sleep(380);

    await clickAt(38, 61, 'Passo 6/7: Redigindo Texto Principal (Copywriter)', 'input-primary-text');
    await typeText((v) => (typedPrimaryText = v), anuncio.texto_principal, 12);

    await clickAt(38, 76, 'Passo 6/7: Preenchendo Título e CTA', 'input-headline');
    await typeText((v) => (typedHeadline = v), anuncio.titulo, 22);
    selectedCta = anuncio.cta || 'Saiba mais';
    await sleep(400);

    // PASSO 7: Salvar como Rascunho (NUNCA clicar em Publicar)
    stepIndex = 7;
    await clickAt(68, 88, 'Passo 7/7: Clicando em "Salvar como Rascunho" (bloqueio de publicação ativo)', 'btn-rascunho');

    savedCampaigns = [
      {
        id: 'camp-' + Date.now(),
        active: false,
        isNewDraft: true,
        nome: nomeCampanha,
        veiculacao: 'Em rascunho',
        estrategia: `CBO (${plano?.tipo_orcamento || 'CBO'})`,
        orcamento: `${orcamentoFmt}/dia`,
        resultados: `${conjunto.publico.localizacoes.join(' + ')} · ${nomeArquivo}`,
      },
      ...savedCampaigns.filter((c) => !c.isNewDraft),
    ];

    viewMode = 'table';
    activeField = 'row-new-draft';
    moveToPercent(34, 42, 'Concluído! Campanha salva como "Em rascunho" no Gerenciador de Anúncios.');
    running = false;
  }

  onMount(() => {
    if (autoStart) {
      iniciarDemonstracaoVisual();
    }
  });
</script>

<div class="sim-wrapper" bind:this={stageEl}>
  <!-- Barra de controle da automação visual -->
  <div class="sim-HUD">
    <div class="hud-left">
      <span class="live-dot" class:pulsing={running}></span>
      <strong>Execução Visual no Gerenciador de Anúncios (Playwright / browser-use)</strong>
      <span class="step-pill">Passo {stepIndex}/7</span>
    </div>
    <div class="hud-actions">
      <button class="hud-btn" type="button" onclick={iniciarDemonstracaoVisual} disabled={running}>
        {running ? '🖱️ Agente operando o mouse...' : '🔁 Ver Mouse Criando Novamente'}
      </button>
    </div>
  </div>

  <!-- Palco do Gerenciador de Anúncios da Meta -->
  <div class="ads-stage">
    <!-- Barra de endereço estilo navegador -->
    <div class="browser-chrome">
      <div class="dots">
        <span class="d red"></span>
        <span class="d yellow"></span>
        <span class="d green"></span>
      </div>
      <div class="url-bar">
        🔒 <span>https://adsmanager.facebook.com/adsmanager/manage/campaigns?act=1049283741</span>
      </div>
      <div class="profile-tag">Perfil Persistente Ativo</div>
    </div>

    <!-- Topbar oficial estilo Meta Ads Manager -->
    <div class="meta-topbar">
      <div class="meta-brand">
        <span class="meta-logo">∞ Meta</span>
        <span class="meta-title">Gerenciador de Anúncios</span>
      </div>
      <div class="meta-tabs">
        <span class="m-tab" class:active={viewMode === 'table' || viewMode === 'editor_campanha'}>
          📊 Campanhas
        </span>
        <span class="m-tab" class:active={viewMode === 'editor_conjunto'}>
          🎯 Conjuntos de anúncios
        </span>
        <span class="m-tab" class:active={viewMode === 'editor_anuncio'}>
          🖼️ Anúncios
        </span>
      </div>
    </div>

    {#if viewMode === 'table'}
      <!-- Toolbar da tabela de campanhas -->
      <div class="meta-toolbar">
        <button
          class="meta-create-btn"
          class:highlight-target={activeField === 'btn-criar'}
          type="button"
          onclick={iniciarDemonstracaoVisual}
        >
          + Criar
        </button>
        <button class="meta-tool-btn" type="button">Duplicar</button>
        <button class="meta-tool-btn" type="button">Editar</button>
        <span class="meta-draft-badge">Rascunhos salvos: {savedCampaigns.filter((c) => c.isNewDraft).length}</span>
      </div>

      <!-- Tabela de campanhas -->
      <table class="meta-table">
        <thead>
          <tr>
            <th>Off/On</th>
            <th>Campanha</th>
            <th>Veiculação</th>
            <th>Estratégia de orçamento</th>
            <th>Orçamento</th>
            <th>Segmentação / Criativo</th>
          </tr>
        </thead>
        <tbody>
          {#each savedCampaigns as camp (camp.id)}
            <tr class:new-draft-row={camp.isNewDraft} class:highlight-target={camp.isNewDraft && activeField === 'row-new-draft'}>
              <td>
                <div class="fake-toggle"></div>
              </td>
              <td>
                <strong>{camp.nome}</strong>
                {#if camp.isNewDraft}
                  <div class="row-sub">Criado pelo Agente IA · Pronto para revisão</div>
                {/if}
              </td>
              <td>
                <span class="status-badge" class:draft={camp.isNewDraft}>
                  ● {camp.veiculacao}
                </span>
              </td>
              <td>{camp.estrategia}</td>
              <td><strong>{camp.orcamento}</strong></td>
              <td>{camp.resultados}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    {:else if viewMode === 'modal_objetivo'}
      <!-- Modal de escolha de objetivo da campanha -->
      <div class="meta-modal-backdrop">
        <div class="meta-modal">
          <div class="meta-modal-header">Criar nova campanha · Escolha um objetivo de campanha</div>
          <div class="obj-list">
            <div class="obj-item">📢 Reconhecimento</div>
            <div class="obj-item">🔗 Tráfego</div>
            <div class="obj-item">💬 Engajamento</div>
            <div
              class="obj-item"
              class:selected={selectedObjective === 'Leads'}
              class:highlight-target={activeField === 'obj-leads'}
            >
              🧲 <strong>Cadastros (Leads)</strong>
              <small>Ideal para formulários instantâneos, WhatsApp e repasse de financiamento</small>
            </div>
            <div class="obj-item">🛒 Vendas</div>
          </div>
          <div class="meta-modal-footer">
            <span class="meta-btn-cancel">Cancelar</span>
            <span
              class="meta-btn-primary"
              class:highlight-target={activeField === 'btn-continuar'}
            >
              Continuar
            </span>
          </div>
        </div>
      </div>
    {:else if viewMode === 'editor_campanha'}
      <!-- Editor Nível 1: Campanha (CBO + Orçamento) -->
      <div class="editor-layout">
        <div class="editor-form">
          <div class="step-header">Nível 1 de 3 · Configuração da Campanha</div>

          <div class="form-group" class:highlight-target={activeField === 'input-camp-nome'}>
            <label>Nome da campanha</label>
            <div class="fake-input">{typedCampaignName}<span class="caret">|</span></div>
          </div>

          <div class="form-group" class:highlight-target={activeField === 'select-cat'}>
            <label>Categorias de Anúncio Especial</label>
            <div class="fake-input">{specialCategory}</div>
          </div>

          <div class="form-group" class:highlight-target={activeField === 'toggle-cbo'}>
            <label>Orçamento da campanha Advantage+ (CBO)</label>
            <div class="cbo-row">
              <div class="fake-toggle" class:on={cboEnabled}></div>
              <span>{cboEnabled ? 'Ativado (Distribuição automática entre conjuntos)' : 'Desativado'}</span>
            </div>
          </div>

          <div class="form-group" class:highlight-target={activeField === 'input-budget'}>
            <label>Orçamento diário</label>
            <div class="fake-input strong">{typedBudget || 'R$ 0,00'}</div>
          </div>

          <div class="editor-footer">
            <span class="meta-btn-primary" class:highlight-target={activeField === 'btn-avancar-1'}>
              Avançar →
            </span>
          </div>
        </div>
      </div>
    {:else if viewMode === 'editor_conjunto'}
      <!-- Editor Nível 2: Conjunto de Anúncios (Localização + Público) -->
      <div class="editor-layout">
        <div class="editor-form">
          <div class="step-header">Nível 2 de 3 · Conjunto de Anúncios e Segmentação Regional</div>

          <div class="form-group" class:highlight-target={activeField === 'input-adset-nome'}>
            <label>Nome do conjunto de anúncios</label>
            <div class="fake-input">{typedAdsetName}<span class="caret">|</span></div>
          </div>

          <div class="form-group" class:highlight-target={activeField === 'input-loc'}>
            <label>Localizações (Público Regional)</label>
            <div class="tags-box">
              {#if addedLocations.length === 0}
                <span class="muted">Pesquisando cidades no mapa...</span>
              {:else}
                {#each addedLocations as loc}
                  <span class="loc-pin">📍 {loc}</span>
                {/each}
              {/if}
            </div>
          </div>

          <div class="form-group" class:highlight-target={activeField === 'input-idade'}>
            <label>Idade e Direcionamento Detalhado</label>
            <div class="fake-input">Idade: {typedAgeRange} · Gênero: Todos</div>
            {#if addedInterests.length > 0}
              <div class="tags-box" style="margin-top: 6px;">
                {#each addedInterests as intItem}
                  <span class="interest-chip">🎯 {intItem}</span>
                {/each}
              </div>
            {/if}
          </div>

          <div class="editor-footer">
            <span class="meta-btn-primary" class:highlight-target={activeField === 'btn-avancar-2'}>
              Avançar →
            </span>
          </div>
        </div>
      </div>
    {:else if viewMode === 'editor_anuncio'}
      <!-- Editor Nível 3: Anúncio (Upload de Criativo + Copywriter + Preview) -->
      <div class="editor-layout two-cols">
        <div class="editor-form">
          <div class="step-header">Nível 3 de 3 · Criativo e Copywriting do Anúncio</div>

          <div class="form-group" class:highlight-target={activeField === 'input-ad-nome'}>
            <label>Nome do anúncio</label>
            <div class="fake-input">{typedAdName}</div>
          </div>

          <div class="form-group" class:highlight-target={activeField === 'btn-upload-media'}>
            <label>Mídia do Anúncio (Pasta de Criativos)</label>
            <div class="fake-input media-box">
              {#if attachedMedia}
                ✅ Arquivo carregado via <code>upload_file</code>: <strong>{attachedMedia}</strong>
              {:else}
                + Adicionar imagem ou vídeo da pasta local...
              {/if}
            </div>
          </div>

          <div class="form-group" class:highlight-target={activeField === 'input-primary-text'}>
            <label>Texto principal (Copywriter)</label>
            <div class="fake-input multiline">{typedPrimaryText}<span class="caret">|</span></div>
          </div>

          <div class="form-group" class:highlight-target={activeField === 'input-headline'}>
            <label>Título e CTA</label>
            <div class="fake-input">{typedHeadline} · Botão: <strong>{selectedCta}</strong></div>
          </div>

          <div class="editor-footer">
            <span
              class="meta-btn-draft"
              class:highlight-target={activeField === 'btn-rascunho'}
            >
              💾 Fechar e Salvar como Rascunho
            </span>
            <span class="meta-btn-disabled" title="Bloqueado por segurança: revisão humana obrigatória">
              🔒 Publicar (Bloqueado)
            </span>
          </div>
        </div>

        <!-- Prévia em tempo real do Anúncio -->
        <div class="ad-preview-card">
          <div class="preview-header">Prévia do Anúncio · Feed Instagram / Facebook</div>
          <div class="preview-post">
            <div class="post-user">🚘 <strong>Repasse & Financiamento PR</strong> · Patrocinado</div>
            <p class="post-copy">{typedPrimaryText || 'O texto principal aparecerá aqui...'}</p>
            <div class="post-media">
              {#if attachedMedia}
                <div class="media-thumb">
                  🖼️ <span>{attachedMedia}</span>
                  <small>500/dia · Campo Largo & Curitiba</small>
                </div>
              {:else}
                <div class="media-placeholder">Aguardando upload da pasta de criativos...</div>
              {/if}
            </div>
            <div class="post-cta-bar">
              <div>
                <strong>{typedHeadline || 'Título do Anúncio'}</strong>
                <small>Formulário Instantâneo / WhatsApp</small>
              </div>
              <span class="post-cta-btn">{selectedCta}</span>
            </div>
          </div>
        </div>
      </div>
    {/if}

    <!-- CURSOR VISUAL ANIMADO DO AGENTE -->
    <div
      class="ai-cursor"
      class:is-clicking={clicking}
      style="left: {cursorX}%; top: {cursorY}%;"
    >
      <div class="cursor-ring"></div>
      <svg class="cursor-arrow" viewBox="0 0 24 24" width="26" height="26">
        <path
          d="M4 2L20 11L13 13L16 21L13 22L10 14L4 19V2Z"
          fill="#38bdf8"
          stroke="#0f172a"
          stroke-width="2"
        />
      </svg>
      <div class="cursor-tooltip">{cursorLabel}</div>
    </div>
  </div>
</div>

<style>
  .sim-wrapper {
    margin-top: 18px;
    border: 1px solid rgba(56, 189, 248, 0.35);
    border-radius: 14px;
    overflow: hidden;
    background: #0b1220;
    box-shadow: 0 16px 40px rgba(0, 0, 0, 0.45);
  }

  .sim-HUD {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 16px;
    background: rgba(15, 23, 42, 0.95);
    border-bottom: 1px solid rgba(148, 163, 184, 0.16);
    flex-wrap: wrap;
    gap: 10px;
  }

  .hud-left {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 13px;
  }

  .live-dot {
    width: 10px;
    height: 10px;
    border-radius: 999px;
    background: #22c55e;
  }

  .live-dot.pulsing {
    box-shadow: 0 0 0 6px rgba(34, 197, 94, 0.25);
    animation: pulse 1s infinite;
  }

  @keyframes pulse {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.25); }
  }

  .step-pill {
    background: rgba(56, 189, 248, 0.16);
    color: #38bdf8;
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 700;
  }

  .hud-btn {
    background: rgba(56, 189, 248, 0.15);
    color: #38bdf8;
    border: 1px solid rgba(56, 189, 248, 0.4);
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
  }

  .hud-btn:disabled {
    opacity: 0.65;
    cursor: default;
  }

  .ads-stage {
    position: relative;
    min-height: 430px;
    background: #f0f2f5;
    color: #1c1e21;
    font-family: system-ui, -apple-system, sans-serif;
    user-select: none;
    overflow: hidden;
  }

  .browser-chrome {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 7px 12px;
    background: #1e293b;
    color: #cbd5e1;
    font-size: 12px;
  }

  .dots {
    display: flex;
    gap: 5px;
  }

  .d {
    width: 10px;
    height: 10px;
    border-radius: 999px;
    display: inline-block;
  }
  .d.red { background: #ef4444; }
  .d.yellow { background: #f59e0b; }
  .d.green { background: #22c55e; }

  .url-bar {
    flex: 1;
    background: #0f172a;
    padding: 4px 10px;
    border-radius: 6px;
    color: #94a3b8;
    font-family: monospace;
    font-size: 11px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .profile-tag {
    background: rgba(34, 197, 94, 0.2);
    color: #4ade80;
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 11px;
  }

  .meta-topbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 16px;
    background: #ffffff;
    border-bottom: 1px solid #dddfe2;
  }

  .meta-brand {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .meta-logo {
    color: #0866ff;
    font-weight: 800;
    font-size: 15px;
  }

  .meta-title {
    font-weight: 700;
    font-size: 14px;
    color: #1c1e21;
  }

  .meta-tabs {
    display: flex;
    gap: 8px;
  }

  .m-tab {
    font-size: 12px;
    padding: 6px 12px;
    border-radius: 6px;
    background: #f0f2f5;
    color: #4b4f56;
    font-weight: 600;
  }

  .m-tab.active {
    background: #e7f3ff;
    color: #0866ff;
    border-bottom: 2px solid #0866ff;
  }

  .meta-toolbar {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px 16px;
    background: #ffffff;
    border-bottom: 1px solid #dddfe2;
  }

  .meta-create-btn {
    background: #1877f2;
    color: #fff;
    border: none;
    border-radius: 6px;
    padding: 7px 14px;
    font-weight: 700;
    font-size: 13px;
    cursor: pointer;
  }

  .meta-tool-btn {
    background: #e4e6eb;
    color: #1c1e21;
    border: none;
    border-radius: 6px;
    padding: 7px 12px;
    font-size: 12px;
    font-weight: 600;
  }

  .meta-draft-badge {
    margin-left: auto;
    font-size: 12px;
    font-weight: 700;
    color: #0866ff;
    background: #e7f3ff;
    padding: 4px 10px;
    border-radius: 999px;
  }

  .meta-table {
    width: 100%;
    border-collapse: collapse;
    background: #fff;
    font-size: 12px;
  }

  .meta-table th,
  .meta-table td {
    padding: 10px 12px;
    border-bottom: 1px solid #e4e6eb;
    text-align: left;
  }

  .meta-table th {
    background: #f5f6f7;
    color: #4b4f56;
    font-weight: 700;
  }

  .new-draft-row {
    background: #f0fdf4;
  }

  .row-sub {
    font-size: 11px;
    color: #15803d;
    margin-top: 2px;
  }

  .status-badge {
    display: inline-block;
    padding: 3px 8px;
    border-radius: 999px;
    font-weight: 700;
    font-size: 11px;
    background: #e4e6eb;
    color: #4b4f56;
  }

  .status-badge.draft {
    background: #dbeafe;
    color: #1d4ed8;
  }

  .meta-modal-backdrop {
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 22px;
  }

  .meta-modal {
    width: 100%;
    max-width: 520px;
    background: #fff;
    border-radius: 10px;
    box-shadow: 0 12px 32px rgba(0, 0, 0, 0.18);
    overflow: hidden;
  }

  .meta-modal-header {
    padding: 12px 16px;
    font-weight: 700;
    border-bottom: 1px solid #e4e6eb;
    font-size: 14px;
  }

  .obj-list {
    padding: 12px 16px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .obj-item {
    padding: 10px 12px;
    border: 1px solid #dddfe2;
    border-radius: 8px;
    font-size: 13px;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .obj-item.selected {
    border-color: #0866ff;
    background: #e7f3ff;
  }

  .obj-item small {
    color: #606770;
    font-size: 11px;
  }

  .meta-modal-footer {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    padding: 10px 16px;
    background: #f5f6f7;
    border-top: 1px solid #e4e6eb;
  }

  .meta-btn-cancel {
    padding: 6px 12px;
    background: #e4e6eb;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 600;
  }

  .meta-btn-primary {
    padding: 7px 14px;
    background: #0866ff;
    color: #fff;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 700;
  }

  .meta-btn-draft {
    padding: 8px 14px;
    background: #0866ff;
    color: #fff;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 700;
  }

  .meta-btn-disabled {
    padding: 8px 12px;
    background: #e4e6eb;
    color: #8a8d91;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 600;
  }

  .editor-layout {
    padding: 16px;
  }

  .editor-layout.two-cols {
    display: grid;
    grid-template-columns: 1.35fr 1fr;
    gap: 14px;
  }

  .editor-form {
    background: #fff;
    border: 1px solid #dddfe2;
    border-radius: 10px;
    padding: 14px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .step-header {
    font-weight: 800;
    font-size: 13px;
    color: #0866ff;
    border-bottom: 1px solid #e4e6eb;
    padding-bottom: 6px;
  }

  .form-group {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 6px;
    border-radius: 8px;
    transition: box-shadow 0.2s, background 0.2s;
  }

  .form-group label {
    font-size: 11px;
    font-weight: 700;
    color: #4b4f56;
  }

  .fake-input {
    background: #f5f6f7;
    border: 1px solid #ccd0d5;
    border-radius: 6px;
    padding: 7px 10px;
    font-size: 12px;
    min-height: 31px;
    color: #1c1e21;
  }

  .fake-input.strong {
    font-weight: 800;
    color: #0866ff;
    font-size: 14px;
  }

  .fake-input.multiline {
    min-height: 54px;
    line-height: 1.35;
  }

  .cbo-row {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;
  }

  .fake-toggle {
    width: 34px;
    height: 18px;
    border-radius: 999px;
    background: #ccd0d5;
    position: relative;
  }

  .fake-toggle::after {
    content: '';
    position: absolute;
    top: 2px;
    left: 2px;
    width: 14px;
    height: 14px;
    border-radius: 50%;
    background: #fff;
    transition: transform 0.2s;
  }

  .fake-toggle.on {
    background: #0866ff;
  }

  .fake-toggle.on::after {
    transform: translateX(16px);
  }

  .tags-box {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    background: #f5f6f7;
    border: 1px solid #ccd0d5;
    border-radius: 6px;
    padding: 7px;
  }

  .loc-pin {
    background: #dbeafe;
    color: #1e40af;
    padding: 3px 8px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 700;
  }

  .interest-chip {
    background: #dcfce7;
    color: #166534;
    padding: 3px 8px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 600;
  }

  .editor-footer {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    margin-top: 4px;
  }

  .ad-preview-card {
    background: #fff;
    border: 1px solid #dddfe2;
    border-radius: 10px;
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .preview-header {
    font-size: 11px;
    font-weight: 700;
    color: #606770;
  }

  .preview-post {
    border: 1px solid #e4e6eb;
    border-radius: 8px;
    padding: 10px;
    background: #fafafa;
    font-size: 12px;
  }

  .post-copy {
    margin: 6px 0;
    color: #1c1e21;
    font-size: 11px;
  }

  .post-media {
    background: linear-gradient(135deg, #0f172a, #1d4ed8);
    color: #fff;
    border-radius: 6px;
    padding: 18px 10px;
    text-align: center;
    margin-bottom: 8px;
  }

  .media-thumb {
    display: flex;
    flex-direction: column;
    gap: 4px;
    font-size: 12px;
  }

  .post-cta-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 6px;
    background: #f0f2f5;
    padding: 6px 8px;
    border-radius: 6px;
  }

  .post-cta-bar small {
    display: block;
    font-size: 10px;
    color: #606770;
  }

  .post-cta-btn {
    background: #e4e6eb;
    padding: 4px 8px;
    border-radius: 4px;
    font-weight: 700;
    font-size: 11px;
  }

  .highlight-target {
    box-shadow: 0 0 0 3px rgba(8, 102, 255, 0.45) !important;
    background: #e7f3ff !important;
  }

  .caret {
    color: #0866ff;
    font-weight: 900;
    animation: blink 0.8s infinite;
  }

  @keyframes blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0; }
  }

  /* CURSOR ANIMADO */
  .ai-cursor {
    position: absolute;
    z-index: 50;
    pointer-events: none;
    transition: left 0.48s cubic-bezier(0.22, 1, 0.36, 1), top 0.48s cubic-bezier(0.22, 1, 0.36, 1);
  }

  .cursor-arrow {
    filter: drop-shadow(0 4px 8px rgba(0, 0, 0, 0.45));
    transform-origin: top left;
    transition: transform 0.15s ease;
  }

  .ai-cursor.is-clicking .cursor-arrow {
    transform: scale(0.82);
  }

  .cursor-ring {
    position: absolute;
    top: -10px;
    left: -10px;
    width: 34px;
    height: 34px;
    border-radius: 50%;
    border: 3px solid #38bdf8;
    opacity: 0;
    transform: scale(0.4);
  }

  .ai-cursor.is-clicking .cursor-ring {
    animation: click-ripple 0.38s ease-out;
  }

  @keyframes click-ripple {
    0% { opacity: 1; transform: scale(0.4); }
    100% { opacity: 0; transform: scale(1.9); }
  }

  .cursor-tooltip {
    position: absolute;
    left: 24px;
    top: 14px;
    background: #0f172a;
    color: #f8fafc;
    border: 1px solid #38bdf8;
    border-radius: 8px;
    padding: 5px 10px;
    font-size: 11px;
    font-weight: 600;
    white-space: nowrap;
    box-shadow: 0 8px 20px rgba(0, 0, 0, 0.4);
  }

  @media (max-width: 900px) {
    .editor-layout.two-cols {
      grid-template-columns: 1fr;
    }
  }
</style>
