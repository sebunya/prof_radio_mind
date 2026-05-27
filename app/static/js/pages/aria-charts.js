import { API } from '../api.js';
import { toast, fmtDate, posBadge, esc, setBtnLoading } from '../ui.js';

let _chart = null;
let _container;

export async function init(container, actions) {
  _container = container;
  container.innerHTML = '<div class="loader-center"><div class="loader"></div></div>';
  actions.innerHTML = '';

  // Try to load the latest cached chart first
  let latest = null;
  try { latest = await API.latestAria(); } catch { /* not yet ingested */ }

  renderPage(latest);
}

function today() {
  return new Date().toISOString().split('T')[0];
}

function renderPage(chartData) {
  _container.innerHTML = `
    <!-- ── Ingest form ── -->
    <div class="card mb-5">
      <div class="card-header"><span class="card-title">Ingest ARIA Singles Chart</span></div>
      <div class="alert alert-warning mb-4" style="font-size:12px">
        ⚠ VAL-ARIA-001: Live fetching makes a request to aria.com.au. Only use when the ARIA website
        is reachable and the selector has been validated. The parser raises 422 if the HTML structure changes.
      </div>
      <div class="form-row" style="align-items:flex-end;flex-wrap:wrap">
        <div class="form-group" style="flex:1;min-width:160px">
          <label>Chart Week-Ending Date</label>
          <input type="date" id="aria-date" value="${today()}">
          <div class="form-hint">Leave blank to fetch the current week</div>
        </div>
        <div class="form-group" style="flex:0;margin-bottom:14px">
          <button class="btn btn-secondary" id="aria-btn" onclick="window._ariaPage.ingest()">
            Fetch ARIA Chart
          </button>
        </div>
        <div class="form-group" style="flex:0;margin-bottom:14px">
          <button class="btn btn-ghost" onclick="window._ariaPage.loadLatest()">
            ↻ Reload Latest
          </button>
        </div>
      </div>
    </div>

    <!-- ── Chart display ── -->
    <div id="aria-display">
      ${chartData ? buildChartHtml(chartData) : `
        <div class="empty-state">
          <div class="empty-icon">🏆</div>
          <div class="empty-title">No chart ingested yet</div>
          <div class="empty-desc">Click "Fetch ARIA Chart" to ingest this week's ARIA Singles chart.</div>
        </div>`}
    </div>`;

  if (chartData?.entries?.length) {
    requestAnimationFrame(() => renderPositionsChart(chartData.entries));
  }
}

function buildChartHtml(data) {
  const entries = data.entries || [];
  if (!entries.length) return '<div class="alert alert-warning">Chart was ingested but returned 0 entries.</div>';

  const top10 = entries.slice(0, 10);
  const rest  = entries.slice(10);

  return `
    <!-- ── Meta ── -->
    <div class="flex items-c j-between mb-4">
      <div>
        <span class="badge badge-accent" style="font-size:13px">${esc(data.chart_name)}</span>
        <span class="text-2 text-sm" style="margin-left:10px">Week ending ${fmtDate(data.chart_date)}</span>
      </div>
      <span class="text-3 text-sm">${data.entry_count} entries · Cached ${fmtDate(data.fetched_at)}</span>
    </div>

    <!-- ── Top 10 visual ── -->
    <div class="card mb-5">
      <div class="card-header"><span class="card-title">Top 10 This Week</span></div>
      <div style="display:flex;flex-direction:column;gap:6px">
        ${top10.map(e => buildEntryRow(e)).join('')}
      </div>
    </div>

    <!-- ── Full chart table ── -->
    ${rest.length ? `
    <div class="card">
      <div class="card-header">
        <span class="card-title">Full Chart — ${entries.length} Entries</span>
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr>
            <th style="width:50px">#</th>
            <th>Artist</th><th>Title</th>
            <th>Previous</th><th>Peak</th><th>Weeks</th>
          </tr></thead>
          <tbody>
            ${entries.map(e => `
              <tr>
                <td>${posBadge(e.position)}</td>
                <td class="font-500">${esc(e.artist)}</td>
                <td class="text-2">${esc(e.title)}</td>
                <td class="text-3 text-sm">${e.previous_position ? `#${e.previous_position}` : '—'}</td>
                <td class="text-3 text-sm">${e.peak_position ? `#${e.peak_position}` : '—'}</td>
                <td class="text-3 text-sm">${e.weeks_on_chart || '—'}</td>
              </tr>`).join('')}
          </tbody>
        </table>
      </div>
    </div>` : ''}

    <!-- ── Bar chart ── -->
    <div class="card mt-4">
      <div class="card-header">
        <span class="card-title">Positions 1–20</span>
        <span class="text-3 text-xs">Bar height = chart rank (taller = higher)</span>
      </div>
      <div class="chart-wrap" style="height:160px"><canvas id="ch-aria"></canvas></div>
    </div>`;
}

function buildEntryRow(e) {
  const arrow = e.previous_position == null ? '' :
    e.position < e.previous_position ? '<span style="color:var(--success)">↑</span>' :
    e.position > e.previous_position ? '<span style="color:var(--danger)">↓</span>' :
    '<span style="color:var(--text3)">→</span>';

  const bg = e.position === 1 ? 'rgba(251,191,36,.08)' :
             e.position === 2 ? 'rgba(156,163,175,.06)' :
             e.position === 3 ? 'rgba(146,64,14,.06)'  : 'transparent';

  return `<div style="display:flex;align-items:center;gap:12px;padding:8px 10px;border-radius:6px;background:${bg}">
    ${posBadge(e.position)}
    <div style="flex:1;min-width:0">
      <div style="font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(e.artist)}</div>
      <div style="font-size:12px;color:var(--text2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(e.title)}</div>
    </div>
    <div style="font-size:13px;color:var(--text3)">${arrow}</div>
    ${e.weeks_on_chart ? `<div style="font-size:11px;color:var(--text3)">${e.weeks_on_chart}wk</div>` : ''}
  </div>`;
}

async function ingest() {
  const date = document.getElementById('aria-date')?.value || null;
  const btn  = document.getElementById('aria-btn');
  setBtnLoading(btn, true, 'Fetching…');

  try {
    const data = await API.ingestAria(date || undefined);
    document.getElementById('aria-display').innerHTML = buildChartHtml(data);
    requestAnimationFrame(() => renderPositionsChart(data.entries || []));
    toast('success', 'ARIA chart ingested', `${data.entry_count} entries for ${fmtDate(data.chart_date)}`);
  } catch (err) {
    toast('error', 'Ingest failed', err.message);
  } finally {
    setBtnLoading(btn, false);
  }
}

async function loadLatest() {
  try {
    const data = await API.latestAria();
    document.getElementById('aria-display').innerHTML = buildChartHtml(data);
    requestAnimationFrame(() => renderPositionsChart(data.entries || []));
    toast('info', 'Reloaded latest chart');
  } catch (err) {
    toast('error', 'No chart available', err.message);
  }
}

function renderPositionsChart(entries) {
  const ctx = document.getElementById('ch-aria');
  if (!ctx || !window.Chart) return;
  if (_chart) _chart.destroy();

  const top20 = entries.slice(0, 20);
  _chart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: top20.map(e => `#${e.position}`),
      datasets: [{
        label: 'Position',
        // Invert so #1 is tallest bar. Values are bounded to top20 so never negative.
        data: top20.map(e => 21 - e.position),
        backgroundColor: top20.map((e, i) => {
          if (e.position === 1) return 'rgba(251,191,36,.8)';
          if (e.position === 2) return 'rgba(156,163,175,.7)';
          if (e.position === 3) return 'rgba(146,64,14,.7)';
          return `rgba(14,165,233,${0.6 - i * 0.02})`;
        }),
        borderRadius: 3, borderWidth: 0,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: {
          title: (items) => top20[items[0].dataIndex]?.artist || '',
          label: (item) => top20[item.dataIndex]?.title || '',
        }},
      },
      scales: {
        x: { ticks: { color:'#94a3b8', font:{size:9} }, grid: { display: false } },
        y: { display: false, beginAtZero: true },
      },
    },
  });
}

window._ariaPage = { ingest, loadLatest };
