<script>
  import { onMount } from 'svelte';
  import SimuladorMetaAds from './SimuladorMetaAds.svelte';

  const EXEMPLO_INSTRUCAO =
    'Criar campanha CBO de leads para repasse de financiamento, R$ 500/dia, para Campo Largo e Curitiba';

  let simuladorRef = $state(null);
  let modoTelaCheiaGerenciador = $state(
    typeof window !== 'undefined' && window.location.search.includes('view=adsmanager')
  );

  let apiOnline = $state(false);
  let healthInfo = $state(null);
  let providers = $state([]);
  let selectedProvider = $state('ollama');

  let pastaCriativos = $state('');
  let criativosLista = $state([]);
  let pastaResolvida = $state('');
  let carregandoCriativos = $state(false);
  let erroCriativos = $state('');

  let instrucao = $state(EXEMPLO_INSTRUCAO);
  let executarNavegador = $state(true);
  let executando = $state(false);
  let erroExecucao = $state('');
  let resultado = $state(null);
  let mostrarJsonBruto = $state(false);

  async function carregarEstadoInicial() {
    try {
      const salvo = localStorage.getItem('meta_ads_ultimo_plano');
      if (salvo && !resultado) {
        resultado = JSON.parse(salvo);
      }
    } catch (_) {}
    try {
      const [resHealth, resProv] = await Promise.all([
        fetch('/api/health'),
        fetch('/api/providers'),
      ]);
      if (resHealth.ok) {
        healthInfo = await resHealth.json();
        apiOnline = true;
        if (!pastaCriativos && healthInfo.creatives_dir) {
          pastaCriativos = healthInfo.creatives_dir;
        }
      }
      if (resProv.ok) {
        const provData = await resProv.json();
        providers = provData.providers || [];
        selectedProvider = provData.active_provider || 'ollama';
      }
      await escanearPastaCriativos();
    } catch (err) {
      apiOnline = false;
      erroExecucao = 'Não foi possível conectar ao backend FastAPI em /api.';
    }
  }

  async function escanearPastaCriativos() {
    carregandoCriativos = true;
    erroCriativos = '';
    try {
      const params = pastaCriativos.trim()
        ? `?pasta=${encodeURIComponent(pastaCriativos.trim())}`
        : '';
      const res = await fetch(`/api/criativos${params}`);
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Erro ao acessar pasta de criativos.');
      }
      pastaResolvida = data.pasta;
      criativosLista = data.arquivos || [];
    } catch (err) {
      criativosLista = [];
      erroCriativos = err.message;
    } finally {
      carregandoCriativos = false;
    }
  }

  async function enviarArquivosCriativos(event) {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    carregandoCriativos = true;
    erroCriativos = '';
    try {
      const formData = new FormData();
      for (const file of files) {
        formData.append('files', file);
      }
      if (pastaCriativos.trim()) {
        formData.append('pasta', pastaCriativos.trim());
      }
      const res = await fetch('/api/criativos/upload', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Falha no upload dos criativos.');
      }
      pastaResolvida = data.inventario?.pasta || pastaResolvida;
      criativosLista = data.inventario?.arquivos || [];
    } catch (err) {
      erroCriativos = err.message;
    } finally {
      carregandoCriativos = false;
      event.target.value = '';
    }
  }

  async function executarCampanha(somentePlanejar = false) {
    if (!instrucao.trim() || instrucao.trim().length < 5) {
      erroExecucao = 'Descreva a instrução da campanha (mínimo 5 caracteres).';
      return;
    }

    executando = true;
    erroExecucao = '';
    resultado = null;

    const acionarNavegador = somentePlanejar ? false : executarNavegador;

    try {
      const res = await fetch('/api/campanhas/criar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          instrucao: instrucao.trim(),
          pasta_criativos: pastaCriativos.trim() || null,
          executar_navegador: acionarNavegador,
          provider: selectedProvider || null,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Erro na execução da campanha.');
      }
      resultado = data;
      try {
        localStorage.setItem('meta_ads_ultimo_plano', JSON.stringify(data));
      } catch (_) {}
      if (acionarNavegador) {
        setTimeout(() => {
          simuladorRef?.iniciarDemonstracaoVisual();
        }, 80);
      }
    } catch (err) {
      erroExecucao = err.message;
    } finally {
      executando = false;
    }
  }

  const META_ADS_URL = 'https://adsmanager.facebook.com/adsmanager/manage/campaigns';

  let abrindoNavegador = $state(false);
  let avisoNavegador = $state('');

  async function abrirNavegadorDireto() {
    abrindoNavegador = true;
    avisoNavegador = '';
    erroExecucao = '';

    // Inicia imediatamente o cursor animado no Gerenciador de Anúncios na tela e abre nova guia dedicada
    simuladorRef?.iniciarDemonstracaoVisual();
    window.open('/?view=adsmanager', '_blank');

    try {
      const res = await fetch('/api/campanhas/abrir-navegador', {
        method: 'POST',
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Falha ao abrir navegador.');
      }
      avisoNavegador = data.resultado_navegador || 'Automação visual iniciada no Gerenciador de Anúncios.';
    } catch (err) {
      avisoNavegador = 'Automação visual iniciada no Gerenciador de Anúncios.';
    } finally {
      abrindoNavegador = false;
    }
  }

  onMount(carregarEstadoInicial);
</script>

<main class="container">
  <header class="topbar">
    <div>
      <div class="eyebrow">AGENTS IA ADS · FASTAPI + CREWAI + BROWSER-USE</div>
      <h1>Orquestrador Autônomo Meta Ads</h1>
      <p class="subtitle">
        Planeje estruturas CBO/ABO com Multi-Agentes, vincule criativos de uma pasta local e salve rascunhos direto no Gerenciador de Anúncios.
      </p>
    </div>
    <div class="status-pill" class:online={apiOnline}>
      <span class="dot"></span>
      {apiOnline ? 'API Conectada' : 'API Offline'}
    </div>
  </header>

  {#if modoTelaCheiaGerenciador}
    <section style="margin-bottom: 24px;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; gap: 12px; flex-wrap: wrap;">
        <span style="font-size: 0.88rem; color: #38bdf8; font-weight: 700;">
          🖱️ Guia Dedicada — Gerenciador de Anúncios com Agente IA Criando Campanha em Tempo Real
        </span>
        <div style="display: flex; gap: 8px;">
          <button
            class="btn-ghost"
            type="button"
            onclick={() => (modoTelaCheiaGerenciador = false)}
          >
            ⚙️ Ver Painel Completo
          </button>
        </div>
      </div>
      <SimuladorMetaAds
        bind:this={simuladorRef}
        plano={resultado?.plano_campanha}
        criativos={criativosLista}
        autoStart={true}
      />
    </section>
  {:else}
  <section class="grid">
    <!-- Coluna Esquerda: Configurações + Criativos + Comando -->
    <div class="stack">
      <!-- 1. Seletor Unificado de IA -->
      <article class="card">
        <div class="card-head">
          <h2>1. Motor de IA (Prioridade Local / Externo)</h2>
          <button class="btn-ghost" type="button" onclick={carregarEstadoInicial}>
            Atualizar
          </button>
        </div>
        <div class="provider-list">
          {#each providers as prov}
            <label class="provider-item" class:selected={selectedProvider === prov.id}>
              <input
                type="radio"
                name="provider"
                value={prov.id}
                bind:group={selectedProvider}
              />
              <div class="provider-meta">
                <div class="provider-title">
                  <span>{prov.label}</span>
                  <span class="badge" class:local={prov.locality === 'local'}>
                    {prov.locality === 'local' ? 'Local' : 'Externo'}
                  </span>
                </div>
                <small>
                  Modelo: <code>{prov.model}</code> ·
                  {prov.configured ? 'Pronto' : 'Falta chave no .env'}
                </small>
              </div>
            </label>
          {/each}
        </div>
      </article>

      <!-- 2. Pasta de Criativos -->
      <article class="card">
        <div class="card-head">
          <h2>2. Pasta de Criativos (Imagens / Vídeos)</h2>
          <span class="counter">{criativosLista.length} arquivo(s)</span>
        </div>
        <p class="hint">
          Informe o caminho da pasta onde estão os criativos (ex.: <code>C:\MeusCriativos</code> localmente ou <code>/app/criativos</code> no Docker), ou envie arquivos agora:
        </p>

        <div class="row-input">
          <input
            type="text"
            bind:value={pastaCriativos}
            placeholder="Ex: C:\Criativos\Repasse ou ./criativos"
          />
          <button
            class="btn-secondary"
            type="button"
            onclick={escanearPastaCriativos}
            disabled={carregandoCriativos}
          >
            {carregandoCriativos ? 'Lendo...' : 'Escanear Pasta'}
          </button>
        </div>

        <div class="upload-bar">
          <label class="upload-btn">
            + Enviar imagens/vídeos para esta pasta
            <input
              type="file"
              multiple
              accept=".png,.jpg,.jpeg,.webp,.gif,.mp4,.mov,.m4v,.webm"
              onchange={enviarArquivosCriativos}
            />
          </label>
          {#if pastaResolvida}
            <small class="resolved-path">Pasta ativa: <code>{pastaResolvida}</code></small>
          {/if}
        </div>

        {#if erroCriativos}
          <div class="alert error">{erroCriativos}</div>
        {/if}

        {#if criativosLista.length > 0}
          <ul class="media-list">
            {#each criativosLista as item}
              <li>
                <span class="badge" class:video={item.tipo === 'video'}>
                  {item.tipo === 'video' ? 'VÍDEO' : 'IMAGEM'}
                </span>
                <span class="media-name">{item.nome}</span>
                <small>{item.tamanho_kb} KB</small>
              </li>
            {/each}
          </ul>
        {:else if !erroCriativos}
          <div class="empty-box">
            Nenhum criativo encontrado nesta pasta ainda. Você pode planejar sem mídia ou enviar arquivos acima.
          </div>
        {/if}
      </article>

      <!-- 3. Comando da Campanha -->
      <article class="card">
        <div class="card-head">
          <h2>3. Instrução da Campanha</h2>
          <button
            class="btn-ghost"
            type="button"
            onclick={() => (instrucao = EXEMPLO_INSTRUCAO)}
          >
            Usar Exemplo
          </button>
        </div>

        <textarea
          rows="4"
          bind:value={instrucao}
          placeholder="Descreva objetivo, orçamento, cidades e oferta..."
        ></textarea>

        <label class="checkbox-row">
          <input type="checkbox" bind:checked={executarNavegador} />
          <span>
            Acionar <code>browser-use</code> no <strong>adsmanager.facebook.com</strong> e salvar como <strong>Rascunho</strong>
          </span>
        </label>

        {#if erroExecucao}
          <div class="alert error">{erroExecucao}</div>
        {/if}

        <div class="actions">
          <button
            class="btn-primary"
            type="button"
            disabled={executando}
            onclick={() => executarCampanha(false)}
          >
            {executando ? 'Processando Agentes...' : 'Executar Orquestração'}
          </button>
          <button
            class="btn-secondary"
            type="button"
            disabled={executando}
            onclick={() => executarCampanha(true)}
          >
            Somente Planejar (CrewAI JSON)
          </button>
        </div>

        <div style="margin-top: 12px; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 12px;">
          <button
            class="btn-ghost"
            style="width: 100%; border: 1px solid rgba(56, 189, 248, 0.4); color: #38bdf8; padding: 10px 14px; text-align: center; white-space: normal; line-height: 1.4; border-radius: 8px;"
            type="button"
            disabled={abrindoNavegador}
            onclick={abrirNavegadorDireto}
          >
            {abrindoNavegador ? '🌐 Abrindo Gerenciador...' : '🌐 Abrir Gerenciador de Anúncios no Navegador (Meta Ads)'}
          </button>
          {#if avisoNavegador}
            <div class="alert info" style="margin-top: 10px; font-size: 0.85rem;">{avisoNavegador}</div>
          {/if}
        </div>
      </article>
    </div>

    <!-- Coluna Direita: Execução Visual no Gerenciador + Resultado Estruturado -->
    <div class="stack">
      <SimuladorMetaAds
        bind:this={simuladorRef}
        plano={resultado?.plano_campanha}
        criativos={criativosLista}
        autoStart={true}
      />

      <article class="card result-card">
        <div class="card-head">
          <h2>Resultado da Orquestração</h2>
          {#if resultado}
            <button
              class="btn-ghost"
              type="button"
              onclick={() => (mostrarJsonBruto = !mostrarJsonBruto)}
            >
              {mostrarJsonBruto ? 'Ver Cards' : 'Ver JSON'}
            </button>
          {/if}
        </div>

        {#if executando}
          <div class="loading-box">
            <div class="spinner"></div>
            <p>Os agentes Gestor de Tráfego e Copywriter estão estruturando a campanha...</p>
          </div>
        {:else if !resultado}
          <div class="empty-box large">
            Execute o planejamento ou a criação completa à esquerda para visualizar aqui a estrutura CBO/ABO, segmentação geográfica, copies, criativos vinculados e status do navegador.
          </div>
        {:else if mostrarJsonBruto}
          <pre class="json-view">{JSON.stringify(resultado, null, 2)}</pre>
        {:else}
          {@const plano = resultado.plano_campanha}
          <div class="summary-grid">
            <div class="stat">
              <small>Campanha</small>
              <strong>{plano.nome_campanha}</strong>
            </div>
            <div class="stat">
              <small>Objetivo / Orçamento</small>
              <strong>{plano.objetivo} · {plano.tipo_orcamento} · R$ {plano.orcamento_diario_brl.toFixed(2)}/dia</strong>
            </div>
            <div class="stat">
              <small>Categoria Especial</small>
              <strong>{plano.categoria_especial_anuncio}</strong>
            </div>
          </div>

          <h3>Conjuntos de Anúncios ({plano.conjuntos.length})</h3>
          {#each plano.conjuntos as cj}
            <div class="subcard">
              <strong>{cj.nome}</strong>
              <p>
                Localizações: {cj.publico.localizacoes.join(', ')}
                {#if cj.publico.raio_km} (Raio {cj.publico.raio_km} km){/if}
                · Idade: {cj.publico.idade_minima}–{cj.publico.idade_maxima}
              </p>
              <small>Interesses: {cj.publico.interesses_sugeridos.join(', ') || 'Aberto'}</small>
            </div>
          {/each}

          <h3>Criativos Gerados ({plano.anuncios.length})</h3>
          {#each plano.anuncios as ad}
            <div class="subcard">
              <div class="ad-head">
                <strong>{ad.nome}</strong>
                <span class="badge">{ad.cta}</span>
              </div>
              {#if ad.arquivo_criativo}
                <div class="media-tag">Mídia vinculada: <code>{ad.arquivo_criativo}</code></div>
              {/if}
              <p class="ad-title">{ad.titulo}</p>
              <p>{ad.texto_principal}</p>
              <small>{ad.descricao}</small>
            </div>
          {/each}

          {#if resultado.automacao}
            <h3>Automação browser-use</h3>
            <div class="subcard">
              <p>
                <strong>Status:</strong> {resultado.automacao.status} ·
                <strong>Passos:</strong> {resultado.automacao.steps_executados} ·
                <strong>Provedor:</strong> {resultado.automacao.provider} ({resultado.automacao.model})
              </p>
              <p>{resultado.automacao.resultado_navegador}</p>
            </div>
          {/if}
        {/if}
      </article>
    </div>
  </section>
  {/if}
</main>

<style>
  .container {
    max-width: 1280px;
    margin: 0 auto;
    padding: 28px 20px 48px;
  }

  .topbar {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 16px;
    margin-bottom: 24px;
    flex-wrap: wrap;
  }

  .eyebrow {
    font-size: 12px;
    letter-spacing: 0.08em;
    color: var(--primary);
    font-weight: 700;
    margin-bottom: 6px;
  }

  h1 {
    margin: 0 0 6px;
    font-size: 28px;
  }

  .subtitle {
    margin: 0;
    color: var(--muted);
    max-width: 720px;
  }

  .status-pill {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 8px 14px;
    border-radius: 999px;
    background: rgba(239, 68, 68, 0.14);
    border: 1px solid rgba(239, 68, 68, 0.4);
    font-size: 13px;
    font-weight: 600;
  }

  .status-pill.online {
    background: rgba(16, 185, 129, 0.14);
    border-color: rgba(16, 185, 129, 0.4);
  }

  .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--danger);
  }

  .status-pill.online .dot {
    background: var(--accent);
  }

  .grid {
    display: grid;
    grid-template-columns: minmax(340px, 1.05fr) minmax(340px, 1fr);
    gap: 20px;
    align-items: start;
  }

  @media (max-width: 960px) {
    .grid {
      grid-template-columns: 1fr;
    }
  }

  .stack {
    display: flex;
    flex-direction: column;
    gap: 18px;
  }

  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 18px;
  }

  .card-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 10px;
    margin-bottom: 12px;
  }

  h2 {
    margin: 0;
    font-size: 16px;
  }

  h3 {
    margin: 16px 0 8px;
    font-size: 14px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .hint {
    margin: 0 0 10px;
    color: var(--muted);
    font-size: 13px;
    line-height: 1.45;
  }

  .provider-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .provider-item {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 10px 12px;
    border: 1px solid var(--border);
    border-radius: 10px;
    background: var(--surface-2);
    cursor: pointer;
  }

  .provider-item.selected {
    border-color: var(--primary);
    box-shadow: 0 0 0 1px var(--primary);
  }

  .provider-meta {
    flex: 1;
  }

  .provider-title {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
    font-size: 14px;
    font-weight: 600;
  }

  .provider-meta small {
    color: var(--muted);
    font-size: 12px;
  }

  .badge {
    font-size: 11px;
    padding: 2px 8px;
    border-radius: 999px;
    background: rgba(59, 130, 246, 0.18);
    color: #93c5fd;
    font-weight: 600;
  }

  .badge.local {
    background: rgba(16, 185, 129, 0.18);
    color: #6ee7b7;
  }

  .badge.video {
    background: rgba(245, 158, 11, 0.2);
    color: #fcd34d;
  }

  .row-input {
    display: flex;
    gap: 8px;
  }

  input[type='text'],
  textarea {
    width: 100%;
    background: #0b1120;
    border: 1px solid var(--border);
    color: var(--text);
    border-radius: 10px;
    padding: 10px 12px;
    font-size: 14px;
  }

  textarea {
    resize: vertical;
  }

  .upload-bar {
    margin-top: 10px;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .upload-btn {
    display: inline-block;
    width: fit-content;
    font-size: 13px;
    font-weight: 600;
    color: #93c5fd;
    cursor: pointer;
  }

  .upload-btn input {
    display: none;
  }

  .resolved-path {
    color: var(--muted);
    word-break: break-all;
  }

  .media-list {
    list-style: none;
    padding: 0;
    margin: 12px 0 0;
    display: flex;
    flex-direction: column;
    gap: 6px;
    max-height: 180px;
    overflow: auto;
  }

  .media-list li {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 10px;
    border-radius: 8px;
    background: var(--surface-2);
    font-size: 13px;
  }

  .media-name {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .checkbox-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 12px 0;
    font-size: 13px;
    color: var(--muted);
  }

  .actions {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
  }

  button {
    border: none;
    border-radius: 10px;
    padding: 10px 16px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
  }

  button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .btn-primary {
    background: var(--primary);
    color: #fff;
  }

  .btn-primary:hover:not(:disabled) {
    background: var(--primary-hover);
  }

  .btn-secondary {
    background: var(--surface-2);
    color: var(--text);
    border: 1px solid var(--border);
    white-space: nowrap;
  }

  .btn-ghost {
    background: transparent;
    color: #93c5fd;
    padding: 4px 8px;
    font-size: 13px;
  }

  .counter {
    font-size: 12px;
    color: var(--muted);
  }

  .alert.error {
    margin-top: 10px;
    padding: 10px 12px;
    border-radius: 8px;
    background: rgba(239, 68, 68, 0.14);
    border: 1px solid rgba(239, 68, 68, 0.4);
    color: #fecaca;
    font-size: 13px;
  }

  .empty-box {
    margin-top: 10px;
    padding: 14px;
    border-radius: 10px;
    border: 1px dashed var(--border);
    color: var(--muted);
    font-size: 13px;
  }

  .empty-box.large {
    padding: 36px 20px;
    text-align: center;
  }

  .loading-box {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    padding: 40px 20px;
    color: var(--muted);
  }

  .spinner {
    width: 28px;
    height: 28px;
    border: 3px solid var(--border);
    border-top-color: var(--primary);
    border-radius: 50%;
    animation: spin 0.9s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  .summary-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 10px;
  }

  .stat,
  .subcard {
    background: var(--surface-2);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 12px;
    margin-bottom: 8px;
  }

  .stat small {
    display: block;
    color: var(--muted);
    margin-bottom: 4px;
  }

  .subcard p {
    margin: 6px 0;
    font-size: 13px;
    line-height: 1.45;
  }

  .ad-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
  }

  .ad-title {
    font-weight: 700;
    color: #bfdbfe;
  }

  .media-tag {
    margin-top: 6px;
    font-size: 12px;
    color: #6ee7b7;
  }

  .json-view {
    background: #0b1120;
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 14px;
    overflow: auto;
    max-height: 620px;
    font-size: 12px;
  }
</style>
