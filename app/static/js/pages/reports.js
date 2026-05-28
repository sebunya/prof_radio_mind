import { API } from '../api.js';
import { toast, dlBlob, fmtDateTime, confBadge, esc, setBtnLoading } from '../ui.js';

let _stations = [];
let _summary  = null;
let _container;

export async function init(container, actions) {
  _container = container;
  container.innerHTML = '<div class="loader-center"><div class="loader"></div></div>';

  try { _stations = await API.stations(); } catch { _stations = []; }

  renderPage(actions);
}

function today() {
  return new Date().toISOString().split('T')[0];
}

function renderPage(actions) {
  actions.innerHTML = `
    <button class="btn btn-secondary btn-sm" onclick="window._reportsPage.masterDownload()">
      ↓ Master CSV
    </button>`;

  _container.innerHTML = `
    <!-- ── Generate form ── -->
    <div class="card mb-5">
      <div class="card-header"><span class="card-title">Generate Daily Report</span></div>
      <div class="form-row" style="align-items:flex-end;gap:12px;flex-wrap:wrap">
        <div class="form-group" style="min-width:180px;flex:2">
          <label for="rpt-station">Station</label>
          <select id="rpt-station">
            <option value="">— Select station —</option>
            ${_stations.map(s => `<option value="${s.id}">${esc(s.call_sign)} — ${esc(s.name)}</option>`).join('')}
          </select>
        </div>
        <div class="form-group" style="min-width:150px;flex:1">
          <label for="rpt-date">Report Date</label>
          <input type="date" id="rpt-date" value="${today()}">
        </div>
        <div class="form-group" style="min-width:100px;width:100px;flex:0">
          <label for="rpt-topn">Top N</label>
          <input type="number" id="rpt-topn" value="40" min="1" max="200">
        </div>
        <div class="form-group" style="flex:0;margin-bottom:14px">
          <button class="btn btn-primary" id="rpt-gen-btn" onclick="window._reportsPage.generate()">
            Generate Report
          </button>
        </div>
      </div>
    </div>

    <!-- ── Summary (shown after generation) ── -->
    <div id="rpt-summary-wrap" class="hidden"></div>

    <!-- ── Download section ── -->
    <div class="card mb-5">
      <div class="card-header"><span class="card-title">Download Report CSV</span></div>
      <div class="form-row" style="align-items:flex-end;flex-wrap:wrap">
        <div class="form-group" style="flex:2;min-width:180px">
          <label for="dl-station">Station</label>
          <select id="dl-station">
            <option value="">— Select station —</option>
            ${_stations.map(s => `<option value="${s.id}">${esc(s.call_sign)} — ${esc(s.name)}</option>`).join('')}
          </select>
        </div>
        <div class="form-group" style="flex:1;min-width:150px">
          <label for="dl-date">Date</label>
          <input type="date" id="dl-date" value="${today()}">
        </div>
        <div class="form-group" style="flex:0;margin-bottom:14px">
          <button class="btn btn-secondary" id="dl-btn" onclick="window._reportsPage.download()">↓ Download CSV</button>
        </div>
      </div>
    </div>

    <!-- ── Master report ── -->
    <div class="card">
      <div class="card-header">
        <span class="card-title">Master Cross-Station Report</span>
      </div>
      <p class="text-2 text-sm mb-4">
        Downloads a combined CSV of all active stations for the selected date.
      </p>
      <div class="form-row" style="align-items:flex-end;flex-wrap:wrap">
        <div class="form-group" style="flex:1;min-width:150px">
          <label for="master-date">Date</label>
          <input type="date" id="master-date" value="${today()}">
        </div>
        <div class="form-group" style="flex:0;margin-bottom:14px">
          <button class="btn btn-secondary" onclick="window._reportsPage.masterDownload()">↓ Master CSV</button>
        </div>
      </div>
    </div>`;
}

async function generate() {
  const stationId = document.getElementById('rpt-station')?.value;
  const date      = document.getElementById('rpt-date')?.value;
  const topN      = parseInt(document.getElementById('rpt-topn')?.value, 10) || 40;

  if (!stationId) { toast('warning', 'Select a station first'); return; }
  if (!date)      { toast('warning', 'Select a report date');   return; }

  const btn = document.getElementById('rpt-gen-btn');
  setBtnLoading(btn, true, 'Generating…');

  try {
    _summary = await API.generateReport(stationId, { report_date: date, top_n: topN });
    renderSummary();
    toast('success', 'Report generated', `v${_summary.version} · ${_summary.confidence_level} confidence`);
  } catch (err) {
    toast('error', 'Generation failed', err.message);
  } finally {
    setBtnLoading(btn, false);
  }
}

function renderSummary() {
  if (!_summary) return;
  const wrap = document.getElementById('rpt-summary-wrap');
  if (!wrap) return;
  wrap.classList.remove('hidden');

  const score    = Math.round((_summary.confidence_score || 0) * 100);
  const lvl      = (_summary.confidence_level || 'low').toLowerCase();
  const barClass = lvl === 'high' ? 'conf-high' : lvl === 'medium' ? 'conf-medium' : 'conf-low';

  // Look up station name from loaded list
  const station = _stations.find(s => s.id === _summary.station_id);
  const stationLabel = station
    ? `${esc(station.call_sign)} — ${esc(station.name)}`
    : esc(_summary.station_id);

  wrap.innerHTML = `
    <div class="card mb-5" style="border-left:3px solid var(--accent)">
      <div class="card-header">
        <span class="card-title">Report Summary — v${_summary.version}</span>
        <span>${confBadge(_summary.confidence_level)}</span>
      </div>

      <div class="report-summary-grid">
        <div class="report-metric">
          <div class="report-metric-label">Total Plays</div>
          <div class="report-metric-value accent">${_summary.total_plays}</div>
        </div>
        <div class="report-metric">
          <div class="report-metric-label">Unique Songs</div>
          <div class="report-metric-value">${_summary.entry_count}</div>
        </div>
        <div class="report-metric">
          <div class="report-metric-label">Confidence</div>
          <div class="report-metric-value" style="font-size:20px">${score}%</div>
          <div class="conf-wrap" style="margin-top:8px">
            <div class="conf-bar ${barClass}" style="width:${score}%;transition:width .6s ease"></div>
          </div>
        </div>
      </div>

      <div class="mt-4" style="padding-top:12px;border-top:1px solid var(--border2)">
        <div class="text-3 text-xs">
          Station: <strong class="text-2">${stationLabel}</strong>
          &nbsp;·&nbsp; Date: <strong class="text-2">${esc(_summary.report_date)}</strong>
          &nbsp;·&nbsp; Generated: ${fmtDateTime(_summary.generated_at)}
        </div>
      </div>
      <div class="mt-4">
        <button class="btn btn-secondary btn-sm" id="dl-summary-btn"
                onclick="window._reportsPage.downloadSummaryReport()">
          ↓ Download this report
        </button>
      </div>
    </div>`;
}

async function download() {
  const stationId = document.getElementById('dl-station')?.value;
  const date      = document.getElementById('dl-date')?.value;
  if (!stationId) { toast('warning', 'Select a station'); return; }
  if (!date)      { toast('warning', 'Select a date'); return; }

  const btn = document.getElementById('dl-btn');
  setBtnLoading(btn, true, 'Downloading…');
  try {
    const blob = await API.downloadReport(stationId, date);
    dlBlob(blob, `rmias_report_${stationId.slice(0, 8)}_${date}.csv`);
    toast('success', 'Download started');
  } catch (err) {
    toast('error', 'Download failed', err.message);
  } finally {
    setBtnLoading(btn, false);
  }
}

async function masterDownload() {
  const date = document.getElementById('master-date')?.value || today();
  try {
    const blob = await API.masterReport(date);
    dlBlob(blob, `rmias_master_${date}.csv`);
    toast('success', 'Master report downloading');
  } catch (err) {
    toast('error', 'Master download failed', err.message);
  }
}

async function downloadSummaryReport() {
  if (!_summary) return;
  const btn = document.getElementById('dl-summary-btn');
  setBtnLoading(btn, true, 'Downloading…');
  try {
    const blob = await API.downloadReport(_summary.station_id, _summary.report_date);
    dlBlob(blob, `rmias_report_${_summary.station_id.slice(0, 8)}_${_summary.report_date}.csv`);
    toast('success', 'Download started');
  } catch (err) {
    toast('error', 'Download failed', err.message);
  } finally {
    setBtnLoading(btn, false);
  }
}

window._reportsPage = { generate, download, masterDownload, downloadSummaryReport };
