<script>
  import { onMount } from 'svelte';

  let {
    onAplicarPublico = (instrucao) => {},
    validacaoPreflight = null,
  } = $props();

  let abaAtiva = $state('central'); // 'central' | 'publicos' | 'robo'
  let campanhas = $state([]);
  let copilot = $state(null);
  let publicos = $state([]);
  let carregando = $state(false);
  let mensagemAcao = $state('');

  export async function recarregarHub() {
    carregando = true;
    try {
      const [resCamp, resCop, resPub] = await Promise.all([
        fetch('/api/meta/campaigns'),
        fetch('/api/meta/copilot'),
        fetch('/api/meta/audiences-store'),
      ]);
      if (resCamp.ok) campanhas = await resCamp.json();
      if (resCop.ok) copilot = await resCop.json();
      if (resPub.ok) {
        const dataPub = await resPub.json();
        publicos = dataPub.publicos || [];
      }
    } catch (_) {
      // Silencioso caso backend esteja reiniciando
    } finally {
      carregando = false;
    }
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
    mensagemAcao = `Público "${pub.titulo}" aplicado no gerador de campanha!`;
  }

  onMount(recarregarHub);
</script>

<section class="adsimples-card">
  <div class="adsimples-header">
    <div>
      <div class="adsimples-badge-row">
        <span class="badge-hackr">⚡ MODO ADSIMPLES / HACKR ADS</span>
        <span class="badge-repo">octaviosilva2/meta-ads · meta-ads-kit · placard</span>
      </div>
      <h2>Central Simplificada de Gestão, Loja de Públicos & Robô Otimizador</h2>
      <p>
        Gerencie campanhas, aplique públicos validados em 1 clique e escale vencedores sem precisar navegar pelas dezenas de abas do Gerenciador tradicional.
      </p>
    </div>
    <div class="tabs-bar">
      <button
        type="button"
        class="tab-btn"
        class:active={abaAtiva === 'central'}
        onclick={() => (abaAtiva = 'central')}
      >
        📊 Campanhas & 1-Clique ({campanhas.length})
      </button>
      <button
        type="button"
        class="tab-btn"
        class:active={abaAtiva === 'robo'}
        onclick={() => (abaAtiva = 'robo')}
      >
        🤖 Robô Otimizador (Winners / Bleeders)
      </button>
      <button
        type="button"
        class="tab-btn"
        class:active={abaAtiva === 'publicos'}
        onclick={() => (abaAtiva = 'publicos')}
      >
        🎯 Loja de Públicos ({publicos.length})
      </button>
      <button type="button" class="tab-btn ghost" onclick={recarregarHub}>
        {carregando ? '...' : '↻'}
      </button>
    </div>
  </div>

  {#if mensagemAcao}
    <div class="toast-msg">
      <span>✅ {mensagemAcao}</span>
      <button type="button" onclick={() => (mensagemAcao = '')}>✕</button>
    </div>
  {/if}

  {#if validacaoPreflight}
    <div class="preflight-box">
      <div class="preflight-title">
        🛡️ Validação Pré-Voo Placard / Adbloop ({validacaoPreflight.status_validacao})
      </div>
      <div class="preflight-items">
        {#each validacaoPreflight.regras_aprovadas || [] as regra}
          <span class="pf-pill ok">✓ {regra}</span>
        {/each}
        {#each validacaoPreflight.avisos || [] as aviso}
          <span class="pf-pill warn">⚠️ {aviso}</span>
        {/each}
      </div>
    </div>
  {/if}

  {#if copilot}
    <div class="kpi-strip">
      <div class="kpi-box">
        <small>Investimento (7 dias)</small>
        <strong>R$ {copilot.summary_7d.spend_7d.toFixed(2)}</strong>
        <span class="sub">Meta hoje: R$ {copilot.pacing.daily_budget_target.toFixed(2)} ({copilot.pacing.status})</span>
      </div>
      <div class="kpi-box">
        <small>Leads / Conversões (7d)</small>
        <strong>{copilot.summary_7d.conversions_7d}</strong>
        <span class="sub">CPA Médio: R$ {copilot.summary_7d.cpa_7d.toFixed(2)}</span>
      </div>
      <div class="kpi-box">
        <small>ROAS Médio (7d)</small>
        <strong class="hi">{copilot.summary_7d.roas_7d.toFixed(2)}x</strong>
        <span class="sub">CTR Médio: {copilot.summary_7d.ctr_7d.toFixed(2)}%</span>
      </div>
      <div class="kpi-box">
        <small>Diagnóstico da Conta</small>
        <strong>🏆 {copilot.winners.length} Winners · 🩸 {copilot.bleeders.length} Bleeders</strong>
        <span class="sub">Modo API: {copilot.mode === 'graph' ? 'Meta Graph API Real' : 'Simulação Sincronizada'}</span>
      </div>
    </div>
  {/if}

  {#if abaAtiva === 'central'}
    <div class="table-wrap">
      <table class="camp-table">
        <thead>
          <tr>
            <th>On/Off</th>
            <th>Campanha / Público</th>
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
                  {camp.objective} · 📍 {(camp.locations || []).join(', ')} · {camp.ads_count} anúncio(s)
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
            ⚡ Carregar Este Público no Criador de Campanhas
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
    padding: 20px;
    margin-bottom: 24px;
    box-shadow: 0 14px 34px rgba(0, 0, 0, 0.35);
  }

  .adsimples-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 16px;
    flex-wrap: wrap;
    margin-bottom: 16px;
  }

  .adsimples-badge-row {
    display: flex;
    gap: 8px;
    align-items: center;
    flex-wrap: wrap;
    margin-bottom: 6px;
  }

  .badge-hackr {
    background: rgba(16, 185, 129, 0.16);
    color: #34d399;
    border: 1px solid rgba(16, 185, 129, 0.35);
    font-size: 11px;
    font-weight: 800;
    padding: 3px 9px;
    border-radius: 999px;
    letter-spacing: 0.04em;
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
    margin: 0 0 4px;
    font-size: 1.2rem;
    color: #f8fafc;
  }

  .adsimples-header p {
    margin: 0;
    font-size: 0.86rem;
    color: #94a3b8;
    max-width: 680px;
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
    font-size: 0.82rem;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.15s;
  }

  .tab-btn.active {
    background: #0284c7;
    color: #ffffff;
    border-color: #38bdf8;
  }

  .tab-btn.ghost {
    padding: 8px 10px;
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
    font-size: 0.84rem;
    font-weight: 600;
    margin-bottom: 12px;
  }

  .toast-msg button {
    background: transparent;
    border: none;
    color: #bbf7d0;
    cursor: pointer;
    font-weight: 800;
  }

  .preflight-box {
    background: rgba(15, 23, 42, 0.8);
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 10px 14px;
    margin-bottom: 14px;
  }

  .preflight-title {
    font-size: 0.8rem;
    font-weight: 800;
    color: #38bdf8;
    margin-bottom: 6px;
  }

  .preflight-items {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .pf-pill {
    font-size: 0.74rem;
    padding: 3px 8px;
    border-radius: 6px;
    font-weight: 600;
  }

  .pf-pill.ok {
    background: rgba(22, 163, 74, 0.16);
    color: #86efac;
  }

  .pf-pill.warn {
    background: rgba(245, 158, 11, 0.16);
    color: #fde68a;
  }

  .kpi-strip {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-bottom: 16px;
  }

  @media (max-width: 900px) {
    .kpi-strip {
      grid-template-columns: 1fr 1fr;
    }
  }

  .kpi-box {
    background: #0b111c;
    border: 1px solid #1e2b40;
    border-radius: 10px;
    padding: 12px 14px;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .kpi-box small {
    font-size: 0.74rem;
    color: #94a3b8;
    text-transform: uppercase;
  }

  .kpi-box strong {
    font-size: 1.15rem;
    color: #f8fafc;
  }

  .kpi-box strong.hi {
    color: #34d399;
  }

  .kpi-box .sub {
    font-size: 0.74rem;
    color: #64748b;
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
    transition: background 0.2s;
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

  @media (max-width: 900px) {
    .robo-grid {
      grid-template-columns: 1fr;
    }
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

  .robo-item strong {
    font-size: 0.84rem;
    color: #f1f5f9;
  }

  .robo-item p {
    margin: 2px 0 0;
    font-size: 0.76rem;
    color: #94a3b8;
  }

  .publicos-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }

  @media (max-width: 850px) {
    .publicos-grid {
      grid-template-columns: 1fr;
    }
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

  .btn-apply-pub:hover {
    background: #166fe5;
  }

  .empty-note {
    font-size: 0.82rem;
    color: #64748b;
  }
</style>
