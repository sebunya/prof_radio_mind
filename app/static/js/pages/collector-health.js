/**
 * Collector Health page — summary cards + paginated run log.
 *
 * Summary cards: Last Run, Runs Today, 24h Success Rate, Currently Running
 * Run log table: status, station, started, duration, row counts, error
 */

import { API } from '../api.js';
import { badge, esc, fmtDateTime, fmtRelative, mountPagination, setSkeleton, toast } from '../ui.js';

const PAGE_SIZE = 25;

let _stationMap = {};   // uuid → call_sign
let _offset     = 0;
let _statusFilter = '';

export async function init(container, actions) {
  setSkeleton(container, 'stats');

  // Filter + refresh button in page-actions bar
  actions.innerHTML = `
    <select id="ch-status-filter" class="form-select form-select-sm" style="width:160px">
      <option value="">All statuses</option>
      <option value="completed">Completed</option>
      <option value="failed">Failed</option>
      <option value="started">Running</option>
      <option value="scheduled">Scheduled</option>
    </select>
    <button class="btn btn-ghost btn-sm" id="ch-refresh">↺ Refresh</button>`;

  document.getElementById('ch-refresh').addEventListener('click', () => _load(container));
  document.getElementById('ch-status-filter').addEventListener('change', (e) => {
    _statusFilter = e.target.value;
    _offset = 0;
    _loadTable(container);
  });

  await _load(container);
}

async function _load(container) {
  // Fetch summary + first run page + stations concurrently
  const [summaryRes, stationsRes] = await Promise.allSettled([
    API.collectorSummary(),
    API.stations(),
  ]);

  const summary  = summaryRes.status  === 'fulfilled' ? summaryRes.value  : null;
  const stations = stationsRes.status === 'fulfilled' ? stationsRes.value : [];

  _stationMap = Object.fromEntries(stations.map(s => [s.id, s.call_sign]));

  container.innerHTML = `
    <!-- Summary cards -->
    <div class="stats-grid mb-5" id="ch-summary">
      ${_summaryCards(summary)}
    </div>

    <!-- Run log -->
    <div class="card">
      <div class="card-header">
        <span class="card-title">Collector Runs</span>
        <span class="text-3 text-sm" id="ch-run-count"></span>
      </div>
      <div id="ch-table-wrap"></div>
      <div id="ch-pagination" style="padding:12px 16px"></div>
    </div>`;

  await _loadTable(container);
}

async function _loadTable() {
  const wrap    = document.getElementById('ch-table-wrap');
  const pgWrap  = document.getElementById('ch-pagination');
  const countEl = document.getElementById('ch-run-count');
  if (!wrap) return;

  wrap.innerHTML = '<div class="loader-center" style="padding:24px"><div class="loader"></div></div>';

  let result;
  try {
    result = await API.collectorRuns({ status: _statusFilter || null, limit: PAGE_SIZE, offset: _offset });
  } catch (err) {
    wrap.innerHTML = `<div class="alert alert-danger" style="margin:16px">${esc(err.message)}</div>`;
    return;
  }

  const { items, total } = result;
  if (countEl) countEl.textContent = `${total.toLocaleString()} runs`;

  if (!items.length) {
    wrap.innerHTML = `<div class="td-empty" style="padding:24px;text-align:center">No collector runs found.</div>`;
    if (pgWrap) pgWrap.innerHTML = '';
    return;
  }

  wrap.innerHTML = `
    <div class="table-wrap">
      <table>
        <thead><tr>
          <th>Status</th>
          <th>Station</th>
          <th>Started</th>
          <th>Duration</th>
          <th>Rows</th>
          <th>Error</th>
        </tr></thead>
        <tbody>
          ${items.map(_runRow).join('')}
        </tbody>
      </table>
    </div>`;

  if (pgWrap) {
    mountPagination(pgWrap, {
      total,
      limit: PAGE_SIZE,
      offset: _offset,
      onNavigate: (newOffset) => { _offset = newOffset; _loadTable(); },
    });
  }
}

function _summaryCards(s) {
  if (!s) {
    return `<div class="stat-card"><div class="stat-label">Status</div>
      <div class="stat-value danger">Unavailable</div>
      <div class="stat-meta">Could not reach /collector-runs/summary</div></div>`;
  }

  const lastRun = s.last_completed_at
    ? `<div class="stat-meta">${esc(fmtRelative(s.last_completed_at))}</div>`
    : `<div class="stat-meta text-3">Never</div>`;

  const rateColour = s.success_rate_24h === null ? '' :
    s.success_rate_24h >= 90 ? 'success' :
    s.success_rate_24h >= 70 ? 'warning' : 'danger';

  const lastFail = s.last_failed_at
    ? `<div class="stat-meta text-sm">${esc(fmtRelative(s.last_failed_at))}</div>`
    : `<div class="stat-meta">No failures recorded</div>`;

  return `
    <div class="stat-card">
      <div class="stat-label">Last Successful Run</div>
      <div class="stat-value ${s.last_completed_at ? 'success' : 'text-3'}" style="font-size:16px;padding-top:4px">
        ${s.last_completed_at ? esc(fmtDateTime(s.last_completed_at)) : '—'}
      </div>
      ${lastRun}
    </div>
    <div class="stat-card">
      <div class="stat-label">Runs Today</div>
      <div class="stat-value accent">${s.runs_today}</div>
      <div class="stat-meta">${s.running_count} currently active</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Success Rate (24 h)</div>
      <div class="stat-value ${rateColour}">
        ${s.success_rate_24h !== null ? `${s.success_rate_24h}%` : '—'}
      </div>
      <div class="stat-meta">Based on last 24 hours</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Last Failure</div>
      <div class="stat-value ${s.last_failed_at ? 'danger' : 'success'}" style="font-size:16px;padding-top:4px">
        ${s.last_failed_at ? esc(fmtDateTime(s.last_failed_at)) : 'None'}
      </div>
      ${lastFail}
    </div>`;
}

function _runRow(run) {
  const station  = _stationMap[run.station_id] || run.station_id.slice(0, 8) + '…';
  const duration = _duration(run.started_at, run.completed_at);
  const rows     = run.rows_persisted !== null
    ? `<span title="fetched/parsed/persisted">${run.rows_fetched ?? '?'} / ${run.rows_parsed ?? '?'} / ${run.rows_persisted}</span>`
    : '—';
  const errCell  = run.error_message
    ? `<span class="text-danger text-sm trunc" style="max-width:200px;display:inline-block" title="${esc(run.error_message)}">${esc(run.error_message)}</span>`
    : '<span class="text-3">—</span>';

  return `<tr>
    <td>${badge(run.status)}</td>
    <td><span class="badge badge-accent">${esc(station)}</span></td>
    <td class="text-sm text-2">${run.started_at ? esc(fmtRelative(run.started_at)) : '—'}</td>
    <td class="text-sm text-3">${duration}</td>
    <td class="text-sm text-2">${rows}</td>
    <td>${errCell}</td>
  </tr>`;
}

function _duration(startedAt, completedAt) {
  if (!startedAt || !completedAt) return '—';
  const ms = new Date(completedAt) - new Date(startedAt);
  if (ms < 0)    return '—';
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.floor(ms / 60000)}m ${Math.round((ms % 60000) / 1000)}s`;
}
