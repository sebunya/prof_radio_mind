import { API } from '../api.js';
import { esc, fmtDateTime, badge, toast } from '../ui.js';

const PAGE_SIZE = 50;

let _stations   = [];
let _page       = null; // PlayEventsPageResponse
let _offset     = 0;
let _container;
let _actions;

export async function init(container, actions) {
  _container = container;
  _actions   = actions;
  _offset    = 0;

  container.innerHTML = '<div class="loader-center"><div class="loader"></div></div>';
  actions.innerHTML   = '';

  try {
    _stations = await API.stations();
  } catch {
    _stations = [];
  }

  renderShell();
  await loadPage(0);
}

function renderShell() {
  _actions.innerHTML = `
    <button class="btn btn-ghost btn-sm" onclick="window._playEventsPage.refresh()">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/>
        <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
      </svg>
      Refresh
    </button>`;

  _container.innerHTML = `
    <!-- ── Filters ── -->
    <div class="card mb-4">
      <div class="form-row" style="align-items:flex-end;flex-wrap:wrap;gap:12px">
        <div class="form-group" style="flex:2;min-width:180px">
          <label>Station</label>
          <select id="pe-station">
            <option value="">All stations</option>
            ${_stations.map(s => `<option value="${esc(s.id)}">${esc(s.call_sign)} — ${esc(s.name)}</option>`).join('')}
          </select>
        </div>
        <div class="form-group" style="flex:1;min-width:140px">
          <label>Date from</label>
          <input type="date" id="pe-date-from">
        </div>
        <div class="form-group" style="flex:1;min-width:140px">
          <label>Date to</label>
          <input type="date" id="pe-date-to">
        </div>
        <div class="form-group" style="flex:0;margin-bottom:14px">
          <button class="btn btn-primary btn-sm" onclick="window._playEventsPage.applyFilters()">Apply</button>
          <button class="btn btn-ghost btn-sm" onclick="window._playEventsPage.clearFilters()" style="margin-left:4px">Clear</button>
        </div>
      </div>
    </div>

    <!-- ── Table ── -->
    <div class="card">
      <div class="card-header" id="pe-header">
        <span class="card-title">Play Events</span>
        <span class="text-3 text-sm" id="pe-count"></span>
      </div>
      <div id="pe-body">
        <div class="loader-center"><div class="loader"></div></div>
      </div>
      <div id="pe-pagination" style="padding:16px 20px;display:flex;justify-content:space-between;align-items:center;border-top:1px solid var(--border)">
      </div>
    </div>`;
}

async function loadPage(offset) {
  _offset = offset;
  const body = document.getElementById('pe-body');
  if (body) body.innerHTML = '<div class="loader-center"><div class="loader"></div></div>';

  const params = getFilters();
  params.limit  = PAGE_SIZE;
  params.offset = offset;

  try {
    _page = await API.playEvents(params);
    renderTable();
  } catch (err) {
    if (body) {
      body.innerHTML = `<div class="alert alert-danger" style="margin:16px">${esc(err.message)}</div>`;
    }
    toast('error', 'Failed to load play events', err.message);
  }
}

function getFilters() {
  const stationEl  = document.getElementById('pe-station');
  const fromEl     = document.getElementById('pe-date-from');
  const toEl       = document.getElementById('pe-date-to');
  const params = {};
  if (stationEl?.value)  params.station_id = stationEl.value;
  if (fromEl?.value)     params.date_from  = fromEl.value;
  if (toEl?.value)       params.date_to    = toEl.value;
  return params;
}

function renderTable() {
  if (!_page) return;

  const countEl = document.getElementById('pe-count');
  if (countEl) {
    countEl.textContent = `${_page.total.toLocaleString()} total · showing ${_page.offset + 1}–${Math.min(_page.offset + _page.items.length, _page.total)}`;
  }

  const body = document.getElementById('pe-body');
  if (!body) return;

  if (!_page.items.length) {
    body.innerHTML = `
      <div class="empty-state" style="padding:40px 20px">
        <div class="empty-icon">📻</div>
        <div class="empty-title">No play events found</div>
        <div class="empty-desc">
          ${_page.total === 0
            ? 'The database is empty. Use Backfill to import historical tracks, or enable collectors to start automatic ingestion.'
            : 'No events match the current filters.'}
        </div>
      </div>`;
    renderPagination();
    return;
  }

  body.innerHTML = `
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Station</th>
            <th>Played At (UTC)</th>
            <th>Artist</th>
            <th>Title</th>
            <th>Deduplication</th>
            <th>Source</th>
            <th>Fingerprint</th>
          </tr>
        </thead>
        <tbody>
          ${_page.items.map(e => `
            <tr>
              <td><span class="badge badge-accent">${esc(e.station_call_sign)}</span></td>
              <td class="text-2" style="white-space:nowrap">${fmtDateTime(e.played_at)}</td>
              <td style="font-weight:500;max-width:160px" class="trunc" title="${esc(e.raw_artist)}">${esc(e.raw_artist)}</td>
              <td style="max-width:200px" class="trunc" title="${esc(e.raw_title)}">${esc(e.raw_title)}</td>
              <td>${e.is_duplicate
                ? '<span class="badge badge-warning">Duplicate</span>'
                : '<span class="badge badge-success">Unique</span>'}</td>
              <td class="text-3 text-xs">${e.attribution ? badge(e.attribution) : '<span class="text-3">—</span>'}</td>
              <td>
                <code class="mono" style="font-size:10px" title="${esc(e.fingerprint || '')}">
                  ${e.fingerprint ? esc(e.fingerprint.slice(0, 10)) + '…' : '—'}
                </code>
              </td>
            </tr>`).join('')}
        </tbody>
      </table>
    </div>`;

  renderPagination();
}

function renderPagination() {
  const el = document.getElementById('pe-pagination');
  if (!el || !_page) return;

  const totalPages = Math.ceil(_page.total / PAGE_SIZE);
  const currentPage = Math.floor(_page.offset / PAGE_SIZE) + 1;
  const hasPrev = _page.offset > 0;
  const hasNext = _page.offset + PAGE_SIZE < _page.total;

  el.innerHTML = `
    <div class="text-3 text-sm">
      Page ${currentPage} of ${totalPages || 1}
    </div>
    <div style="display:flex;gap:8px">
      <button class="btn btn-ghost btn-sm" ${hasPrev ? '' : 'disabled'}
              onclick="window._playEventsPage.prevPage()">← Previous</button>
      <button class="btn btn-ghost btn-sm" ${hasNext ? '' : 'disabled'}
              onclick="window._playEventsPage.nextPage()">Next →</button>
    </div>`;
}

function applyFilters() {
  loadPage(0);
}

function clearFilters() {
  const stationEl = document.getElementById('pe-station');
  const fromEl    = document.getElementById('pe-date-from');
  const toEl      = document.getElementById('pe-date-to');
  if (stationEl) stationEl.value = '';
  if (fromEl)    fromEl.value    = '';
  if (toEl)      toEl.value      = '';
  loadPage(0);
}

function prevPage() {
  if (_offset >= PAGE_SIZE) loadPage(_offset - PAGE_SIZE);
}

function nextPage() {
  if (_page && _offset + PAGE_SIZE < _page.total) loadPage(_offset + PAGE_SIZE);
}

async function refresh() {
  await loadPage(_offset);
}

window._playEventsPage = { applyFilters, clearFilters, prevPage, nextPage, refresh };
