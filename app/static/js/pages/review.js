import { API } from '../api.js';
import { toast, showModal, closeModal, fmtRelative, fmtDateTime, badge, esc } from '../ui.js';

const STATUSES = ['all', 'pending', 'reviewed', 'dismissed', 'escalated'];

let _items    = [];
let _filter   = 'all';
let _container;

export async function init(container, actions) {
  _container = container;
  container.innerHTML = '<div class="loader-center"><div class="loader"></div></div>';
  await loadItems();
  render(actions);
}

async function loadItems() {
  try {
    _items = await API.reviewItems();
  } catch (err) {
    _items = [];
    toast('error', 'Failed to load review items', err.message);
  }
}

function counts() {
  const c = { all: _items.length };
  STATUSES.slice(1).forEach(s => { c[s] = _items.filter(i => i.status === s).length; });
  return c;
}

function filtered() {
  return _filter === 'all' ? _items : _items.filter(i => i.status === _filter);
}

function render(actions) {
  const c = counts();
  const visible = filtered();

  actions.innerHTML = `
    <button class="btn btn-ghost btn-sm" onclick="window._reviewPage.refresh()">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/>
        <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
      </svg>
      Refresh
    </button>`;

  _container.innerHTML = `
    <div class="filter-tabs">
      ${STATUSES.map(s => `
        <button class="filter-tab ${_filter === s ? 'active' : ''}"
                onclick="window._reviewPage.setFilter('${s}')">
          ${s === 'all' ? 'All' : s.charAt(0).toUpperCase() + s.slice(1)}
          <span class="tab-count">${c[s] || 0}</span>
        </button>`).join('')}
    </div>

    <div class="card">
      <div class="table-wrap">
        <table>
          <thead><tr>
            <th>Title</th><th>Type</th><th>Status</th>
            <th>Station</th><th>Age</th><th style="text-align:right">Actions</th>
          </tr></thead>
          <tbody>
            ${visible.length ? visible.map(item => `
              <tr>
                <td style="max-width:280px">
                  <div class="trunc font-500" title="${esc(item.title)}">${esc(item.title)}</div>
                  ${item.description ? `<div class="text-3 text-xs trunc" style="max-width:280px">${esc(item.description)}</div>` : ''}
                </td>
                <td>${badge(item.item_type)}</td>
                <td>${badge(item.status)}</td>
                <td class="text-3 text-xs mono">${item.station_id ? item.station_id.slice(0,8)+'…' : '—'}</td>
                <td class="text-3 text-sm" title="${fmtDateTime(item.created_at)}">${fmtRelative(item.created_at)}</td>
                <td style="text-align:right;white-space:nowrap">
                  ${item.status === 'pending' ? `
                    <button class="btn btn-success btn-xs" onclick="window._reviewPage.resolve('${item.id}')">Resolve</button>
                    <button class="btn btn-warning btn-xs" onclick="window._reviewPage.escalate('${item.id}')">Escalate</button>
                    <button class="btn btn-ghost btn-xs"   onclick="window._reviewPage.dismiss('${item.id}')">Dismiss</button>
                  ` : item.status === 'escalated' ? `
                    <button class="btn btn-success btn-xs" onclick="window._reviewPage.resolve('${item.id}')">Resolve</button>
                  ` : `
                    <span class="text-3 text-xs">${item.resolved_by ? `by ${esc(item.resolved_by)}` : ''}</span>
                  `}
                </td>
              </tr>`).join('') : `<tr><td colspan="6" class="td-empty">No items in this category</td></tr>`}
          </tbody>
        </table>
      </div>
    </div>`;
}

// ── Actions ──────────────────────────────────────────────────────
function resolve(id) {
  const item = _items.find(i => i.id === id);
  if (!item) return;

  showModal(
    'Resolve Review Item',
    `<p class="text-2 text-sm mb-4">${esc(item.title)}</p>
     <div class="form-group">
       <label>Resolved by</label>
       <input type="text" id="m-resolved-by" placeholder="operator@station.com">
     </div>
     <div class="form-group">
       <label>Notes (optional)</label>
       <textarea id="m-notes" rows="3" placeholder="What was confirmed or fixed…"></textarea>
     </div>`,
    `<button class="btn btn-ghost" onclick="UI.closeModal()">Cancel</button>
     <button class="btn btn-success" onclick="window._reviewPage._submitResolve('${id}')">Mark Resolved</button>`
  );
}

async function _submitResolve(id) {
  const resolvedBy = document.getElementById('m-resolved-by')?.value?.trim();
  const notes      = document.getElementById('m-notes')?.value?.trim();
  if (!resolvedBy) { toast('warning', 'Resolved by is required'); return; }

  try {
    await API.resolveItem(id, { resolved_by: resolvedBy, notes: notes || undefined });
    toast('success', 'Item resolved');
    closeModal();
    await loadItems();
    render(document.getElementById('page-actions'));
  } catch (err) {
    toast('error', 'Failed to resolve', err.message);
  }
}

async function escalate(id) {
  const item = _items.find(i => i.id === id);
  if (!item) return;

  showModal(
    'Escalate Review Item',
    `<p class="text-2 text-sm mb-4">${esc(item.title)}</p>
     <div class="form-group">
       <label>Escalated by</label>
       <input type="text" id="m-esc-by" placeholder="operator@station.com">
     </div>`,
    `<button class="btn btn-ghost" onclick="UI.closeModal()">Cancel</button>
     <button class="btn btn-warning" onclick="window._reviewPage._submitEscalate('${id}')">Escalate</button>`
  );
}

async function _submitEscalate(id) {
  const by = document.getElementById('m-esc-by')?.value?.trim();
  if (!by) { toast('warning', 'Operator name is required'); return; }

  try {
    await API.escalateItem(id, { resolved_by: by });
    toast('success', 'Item escalated');
    closeModal();
    await loadItems();
    render(document.getElementById('page-actions'));
  } catch (err) {
    toast('error', 'Failed to escalate', err.message);
  }
}

async function dismiss(id) {
  const item = _items.find(i => i.id === id);
  if (!item) return;

  showModal(
    'Dismiss Review Item',
    `<p class="text-2 text-sm mb-4">${esc(item.title)}</p>
     <div class="form-group">
       <label>Dismissed by</label>
       <input type="text" id="m-dis-by" placeholder="operator@station.com">
     </div>`,
    `<button class="btn btn-ghost" onclick="UI.closeModal()">Cancel</button>
     <button class="btn btn-ghost" onclick="window._reviewPage._submitDismiss('${id}')">Dismiss Item</button>`
  );
}

async function _submitDismiss(id) {
  const by = document.getElementById('m-dis-by')?.value?.trim();
  if (!by) { toast('warning', 'Operator name is required'); return; }

  try {
    await API.dismissItem(id, { resolved_by: by });
    toast('success', 'Item dismissed');
    closeModal();
    await loadItems();
    render(document.getElementById('page-actions'));
  } catch (err) {
    toast('error', 'Failed to dismiss', err.message);
  }
}

async function refresh() {
  _container.innerHTML = '<div class="loader-center"><div class="loader"></div></div>';
  await loadItems();
  render(document.getElementById('page-actions'));
}

function setFilter(f) {
  _filter = f;
  render(document.getElementById('page-actions'));
}

// Expose to global for inline onclick
window._reviewPage = { resolve, escalate, dismiss, refresh, setFilter, _submitResolve, _submitEscalate, _submitDismiss };
