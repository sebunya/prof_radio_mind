import { API } from '../api.js';
import { toast, showModal, closeModal, fmtDateTime, tierBadge, recBadge, esc, setBtnLoading } from '../ui.js';

let _stations     = [];
let _recs         = [];
let _chart        = null;
let _recTypeChart = null;
let _lastDays     = 7;
let _container;

export async function init(container, actions) {
  _container = container;
  container.innerHTML = '<div class="loader-center"><div class="loader"></div></div>';

  try { _stations = await API.stations(); } catch { _stations = []; }
  renderForm(actions);
}

function renderForm(actions) {
  actions.innerHTML = '';
  _container.innerHTML = `
    <!-- ── Controls ── -->
    <div class="card mb-5">
      <div class="card-header"><span class="card-title">Analyse Rotation</span></div>
      <div class="form-row" style="align-items:flex-end;flex-wrap:wrap">
        <div class="form-group" style="flex:3;min-width:200px">
          <label for="pl-station">Station</label>
          <select id="pl-station">
            <option value="">— Select station —</option>
            ${_stations.map(s => `<option value="${s.id}">${esc(s.call_sign)} — ${esc(s.name)}</option>`).join('')}
          </select>
        </div>
        <div class="form-group" style="flex:1;min-width:120px">
          <label for="pl-days">Lookback (days)</label>
          <input type="number" id="pl-days" value="7" min="1" max="90">
        </div>
        <div class="form-group" style="flex:0;margin-bottom:14px">
          <button class="btn btn-primary" id="pl-btn" onclick="window._playlistPage.analyse()">
            Analyse Rotation
          </button>
        </div>
      </div>
    </div>

    <!-- ── Results ── -->
    <div id="pl-results"></div>`;
}

async function analyse() {
  const stationId = document.getElementById('pl-station')?.value;
  const days      = parseInt(document.getElementById('pl-days')?.value, 10) || 7;
  if (!stationId) { toast('warning', 'Select a station first'); return; }

  const btn = document.getElementById('pl-btn');
  setBtnLoading(btn, true, 'Analysing…');

  try {
    _recs = await API.analyseRotation(stationId, days);
    _lastDays = days;
    renderResults(stationId, days);
    toast('success', `${_recs.length} recommendations generated`);
  } catch (err) {
    toast('error', 'Analysis failed', err.message);
    document.getElementById('pl-results').innerHTML = `<div class="alert alert-danger">${esc(err.message)}</div>`;
  } finally {
    setBtnLoading(btn, false);
  }
}

function renderResults(stationId, days) {
  const wrap = document.getElementById('pl-results');
  if (!wrap) return;

  const safeDays = days || _lastDays;

  if (!_recs.length) {
    wrap.innerHTML = `<div class="empty-state">
      <div class="empty-icon">🎵</div>
      <div class="empty-title">No recommendations</div>
      <div class="empty-desc">No play events found in the last ${safeDays} days for this station.</div>
    </div>`;
    return;
  }

  // Tier distribution counts
  const tierCounts = { A: 0, B: 0, C: 0, new_entry: 0, retired: 0 };
  const recTypeCounts = {};
  _recs.forEach(r => {
    tierCounts[r.recommended_tier] = (tierCounts[r.recommended_tier] || 0) + 1;
    recTypeCounts[r.recommendation_type] = (recTypeCounts[r.recommendation_type] || 0) + 1;
  });

  const pendingApproval = _recs.filter(r => !r.approved).length;

  wrap.innerHTML = `
    <!-- ── Summary stats ── -->
    <div class="stats-grid mb-5" style="grid-template-columns:repeat(5,1fr)">
      ${[['A', '#34d399'], ['B', '#38bdf8'], ['C', '#fbbf24'], ['new_entry', '#a5b4fc'], ['retired', '#64748b']].map(([t, c]) => `
        <div class="stat-card" style="padding:14px">
          <div class="stat-label" style="color:${c}">Tier ${t.replace('_', ' ')}</div>
          <div class="stat-value" style="font-size:26px;color:${c}">${tierCounts[t] || 0}</div>
        </div>`).join('')}
    </div>

    <!-- ── Charts ── -->
    <div class="charts-grid mb-5">
      <div class="card">
        <div class="card-header"><span class="card-title">Tier Distribution</span></div>
        <div class="chart-wrap"><canvas id="ch-tier"></canvas></div>
      </div>
      <div class="card">
        <div class="card-header"><span class="card-title">Recommendation Types</span></div>
        <div class="chart-wrap"><canvas id="ch-rec-type"></canvas></div>
      </div>
    </div>

    <!-- ── Recommendations table ── -->
    <div class="card">
      <div class="card-header">
        <span class="card-title">${_recs.length} Recommendations</span>
        <div class="flex gap-2">
          ${pendingApproval > 0 ? `<span class="badge badge-warning">${pendingApproval} pending approval</span>` : ''}
          <button class="btn btn-success btn-sm" onclick="window._playlistPage.approveAll()">✓ Approve All</button>
        </div>
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr>
            <th>Artist</th><th>Title</th><th>Spins</th>
            <th>Current Tier</th><th>Recommended</th><th>Change</th>
            <th>Status</th><th style="text-align:right">Action</th>
          </tr></thead>
          <tbody>
            ${_recs.map(r => `
              <tr id="rec-row-${r.id}">
                <td class="font-500 trunc" style="max-width:140px" title="${esc(r.artist)}">${esc(r.artist)}</td>
                <td class="trunc text-2" style="max-width:140px" title="${esc(r.title)}">${esc(r.title)}</td>
                <td style="font-weight:600;color:var(--accent)">${r.weekly_spins}</td>
                <td>${tierBadge(r.current_tier)}</td>
                <td>${tierBadge(r.recommended_tier)}</td>
                <td>${recBadge(r.recommendation_type)}</td>
                <td>${r.approved
                  ? `<span class="badge badge-success">Approved</span><div class="text-xs text-3 mt-2">by ${esc(r.approved_by || '')}</div>`
                  : '<span class="badge badge-muted">Pending</span>'}</td>
                <td style="text-align:right">
                  ${r.approved ? '' : `<button class="btn btn-success btn-xs" onclick="window._playlistPage.approve('${r.id}')">Approve</button>`}
                  <button class="btn btn-ghost btn-xs" onclick="window._playlistPage.showDetail('${r.id}')" title="View reason">ℹ</button>
                </td>
              </tr>`).join('')}
          </tbody>
        </table>
      </div>
    </div>`;

  requestAnimationFrame(() => {
    renderTierChart(tierCounts);
    renderRecTypeChart(recTypeCounts);
  });
}

function renderTierChart(d) {
  const ctx = document.getElementById('ch-tier');
  if (!ctx || !window.Chart) return;
  if (_chart) _chart.destroy();
  _chart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['A', 'B', 'C', 'New Entry', 'Retired'],
      datasets: [{
        data: [d.A||0, d.B||0, d.C||0, d.new_entry||0, d.retired||0],
        backgroundColor: ['rgba(52,211,153,.75)','rgba(56,189,248,.75)','rgba(251,191,36,.75)','rgba(165,180,252,.75)','rgba(100,116,139,.75)'],
        borderColor: '#1e293b', borderWidth: 2,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false, cutout: '65%',
      plugins: { legend: { position: 'right', labels: { color: '#94a3b8', boxWidth: 10, padding: 8, font:{size:11} } } },
    },
  });
}

function renderRecTypeChart(d) {
  const ctx = document.getElementById('ch-rec-type');
  if (!ctx || !window.Chart) return;
  if (_recTypeChart) { _recTypeChart.destroy(); _recTypeChart = null; }
  const colors = { add:'rgba(52,211,153,.6)', increase:'rgba(56,189,248,.6)', maintain:'rgba(100,116,139,.6)', decrease:'rgba(251,191,36,.6)', retire:'rgba(239,68,68,.6)' };
  _recTypeChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: Object.keys(d),
      datasets: [{ data: Object.values(d), backgroundColor: Object.keys(d).map(k => colors[k] || 'rgba(14,165,233,.6)'), borderRadius: 4, borderWidth: 0 }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color:'#94a3b8', font:{size:10} }, grid: { color:'rgba(255,255,255,.04)' } },
        y: { ticks: { color:'#94a3b8', font:{size:10}, stepSize:1 }, grid: { color:'rgba(255,255,255,.04)' }, beginAtZero:true },
      },
    },
  });
}

function showDetail(id) {
  const r = _recs.find(r => r.id === id);
  if (!r) return;
  showModal(
    `${esc(r.artist)} — ${esc(r.title)}`,
    `<div class="mb-4">
       <div class="flex gap-2 mb-4">${tierBadge(r.current_tier)} → ${tierBadge(r.recommended_tier)} &nbsp;${recBadge(r.recommendation_type)}</div>
       <p class="text-2 text-sm">${esc(r.reason)}</p>
     </div>
     <div class="text-3 text-xs">Weekly spins: <strong class="text-2">${r.weekly_spins}</strong></div>
     ${r.approved ? `<div class="text-3 text-xs mt-2">Approved by ${esc(r.approved_by)} on ${fmtDateTime(r.approved_at)}</div>` : ''}`,
    `<button class="btn btn-ghost" onclick="UI.closeModal()">Close</button>
     ${!r.approved ? `<button class="btn btn-success" onclick="window._playlistPage.approve('${id}');UI.closeModal()">Approve</button>` : ''}`
  );
}

async function approve(id) {
  showModal(
    'Approve Recommendation',
    `<div class="form-group">
       <label>Approved by</label>
       <input type="text" id="m-approve-by" placeholder="e.g. Music Director">
     </div>`,
    `<button class="btn btn-ghost" onclick="UI.closeModal()">Cancel</button>
     <button class="btn btn-success" onclick="window._playlistPage._submitApprove('${id}')">Approve</button>`
  );
}

async function _submitApprove(id) {
  const by = document.getElementById('m-approve-by')?.value?.trim();
  if (!by) { toast('warning', 'Enter who is approving'); return; }

  try {
    const updated = await API.approveRec(id, { approved_by: by });
    const idx = _recs.findIndex(r => r.id === id);
    if (idx !== -1) _recs[idx] = updated;

    // Update row in-place
    const row = document.getElementById(`rec-row-${id}`);
    if (row) {
      const cells = row.querySelectorAll('td');
      cells[6].innerHTML = `<span class="badge badge-success">Approved</span><div class="text-xs text-3 mt-2">by ${esc(by)}</div>`;
      cells[7].innerHTML = `<button class="btn btn-ghost btn-xs" onclick="window._playlistPage.showDetail('${id}')" title="View reason">ℹ</button>`;
    }

    closeModal();
    toast('success', 'Recommendation approved');
  } catch (err) {
    toast('error', 'Approval failed', err.message);
  }
}

async function approveAll() {
  const pending = _recs.filter(r => !r.approved);
  if (!pending.length) { toast('info', 'All recommendations already approved'); return; }

  showModal(
    'Approve All Recommendations',
    `<p class="text-2 text-sm mb-4">Approve all ${pending.length} pending recommendations?</p>
     <div class="form-group">
       <label>Approved by</label>
       <input type="text" id="m-all-by" placeholder="Music Director">
     </div>`,
    `<button class="btn btn-ghost" onclick="UI.closeModal()">Cancel</button>
     <button class="btn btn-success" onclick="window._playlistPage._submitApproveAll()">Approve All</button>`
  );
}

async function _submitApproveAll() {
  const by = document.getElementById('m-all-by')?.value?.trim();
  if (!by) { toast('warning', 'Enter approver name'); return; }

  closeModal();
  let ok = 0, fail = 0;
  for (const r of _recs.filter(r => !r.approved)) {
    try {
      const updated = await API.approveRec(r.id, { approved_by: by });
      const idx = _recs.findIndex(x => x.id === r.id);
      if (idx !== -1) _recs[idx] = updated;
      ok++;
    } catch { fail++; }
  }
  toast('success', `${ok} approved${fail ? `, ${fail} failed` : ''}`);
  renderResults(null, null);
}

window._playlistPage = { analyse, approve, approveAll, showDetail, _submitApprove, _submitApproveAll };
