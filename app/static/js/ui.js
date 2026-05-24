/**
 * Shared UI helpers: toasts, modals, formatting utilities.
 * Exported as named functions AND exposed on window.UI for inline onclick handlers.
 */

// ── Toasts ──────────────────────────────────────────────────────
const ICONS = { success: '✓', error: '✕', warning: '⚠', info: 'ℹ' };

export function toast(type, title, msg = '', ms = 4500) {
  const el = Object.assign(document.createElement('div'), { className: `toast ${type}` });
  el.innerHTML = `
    <span class="toast-icon">${ICONS[type] || ICONS.info}</span>
    <div class="toast-body">
      <div class="toast-title">${esc(title)}</div>
      ${msg ? `<div class="toast-msg">${esc(msg)}</div>` : ''}
    </div>`;
  document.getElementById('toast-container').appendChild(el);
  setTimeout(() => {
    el.style.transition = 'opacity .3s';
    el.style.opacity = '0';
    setTimeout(() => el.remove(), 320);
  }, ms);
}

// ── Modal ────────────────────────────────────────────────────────
export function showModal(title, bodyHtml, footerHtml = '') {
  document.getElementById('modal-title').textContent = title;
  document.getElementById('modal-body').innerHTML = bodyHtml;
  document.getElementById('modal-footer').innerHTML = footerHtml;
  document.getElementById('modal-overlay').classList.remove('hidden');
}

export function closeModal() {
  document.getElementById('modal-overlay').classList.add('hidden');
  document.getElementById('modal-body').innerHTML = '';
  document.getElementById('modal-footer').innerHTML = '';
}

// ── Formatting ───────────────────────────────────────────────────
export function fmtDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-AU', { day: 'numeric', month: 'short', year: 'numeric' });
}

export function fmtDateTime(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('en-AU', {
    day: 'numeric', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

export function fmtRelative(iso) {
  if (!iso) return '—';
  const diff = Date.now() - new Date(iso).getTime();
  const mins  = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days  = Math.floor(diff / 86400000);
  if (mins  < 1)  return 'Just now';
  if (mins  < 60) return `${mins}m ago`;
  if (hours < 24) return `${hours}h ago`;
  if (days  <  7) return `${days}d ago`;
  return fmtDate(iso);
}

// ── Blob download ────────────────────────────────────────────────
export function dlBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// ── Badge helpers ────────────────────────────────────────────────
export function badge(value, extraClass = '') {
  if (!value) return '<span class="badge badge-muted">—</span>';
  const cls = extraClass || `badge-${value.toLowerCase().replace(/\s+/g, '_')}`;
  return `<span class="badge ${cls}">${esc(value.replace(/_/g, ' '))}</span>`;
}

export function tierBadge(tier) {
  if (!tier) return '<span class="badge badge-muted">None</span>';
  return `<span class="badge tier-${tier}">${tier.replace('_', ' ')}</span>`;
}

export function recBadge(type) {
  if (!type) return '';
  const icons = { add:'＋', increase:'↑', decrease:'↓', maintain:'→', retire:'✕' };
  return `<span class="badge rec-${type}">${icons[type] || ''} ${type}</span>`;
}

export function confBadge(level) {
  if (!level) return '';
  return `<span class="badge badge-${level.toLowerCase()}">${level}</span>`;
}

export function posBadge(pos) {
  const cls = pos === 1 ? 'pos-1' : pos === 2 ? 'pos-2' : pos === 3 ? 'pos-3' : 'pos-n';
  return `<span class="pos-badge ${cls}">${pos}</span>`;
}

// ── HTML escape ──────────────────────────────────────────────────
export function esc(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ── Loading skeleton ─────────────────────────────────────────────
export function setLoading(el) {
  el.innerHTML = '<div class="loader-center"><div class="loader"></div></div>';
}

// ── Expose on window for inline onclick ──────────────────────────
window.UI = { toast, showModal, closeModal, fmtDate, fmtDateTime, dlBlob, badge, esc };
