/**
 * Shared UI helpers — toasts, modal (focus-trapped + Esc), formatters,
 * loading helpers, badge factories.
 *
 * All HTML-bearing helpers escape their inputs. The `esc()` helper is
 * exported and re-exposed on window.UI for inline handlers.
 */

// ── HTML escape ──────────────────────────────────────────────────
export function esc(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

// ── Toasts ───────────────────────────────────────────────────────
const ICONS = { success: '✓', error: '✕', warning: '⚠', info: 'ℹ' };

export function toast(type, title, msg = '', ms = 4500) {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const el = document.createElement('div');
  el.className = `toast toast-${type}`;
  el.setAttribute('role', type === 'error' || type === 'warning' ? 'alert' : 'status');
  el.innerHTML = `
    <span class="toast-icon">${ICONS[type] || ICONS.info}</span>
    <div class="toast-body">
      <div class="toast-title">${esc(title)}</div>
      ${msg ? `<div class="toast-msg">${esc(msg)}</div>` : ''}
    </div>
    <button class="toast-close" type="button" aria-label="Dismiss notification">✕</button>`;
  container.appendChild(el);

  let dismissed = false;
  const dismiss = () => {
    if (dismissed) return;
    dismissed = true;
    el.classList.add('toast-out');
    setTimeout(() => el.remove(), 220);
  };

  let timer = setTimeout(dismiss, ms);
  el.addEventListener('mouseenter', () => clearTimeout(timer));
  el.addEventListener('mouseleave', () => { timer = setTimeout(dismiss, 2000); });
  el.querySelector('.toast-close').addEventListener('click', dismiss);

  return dismiss;
}

// ── Modal — focus-trapped, Esc-closable, optional Enter submit ──
let _lastFocus = null;
let _modalEnterHandler = null;
const FOCUSABLE = 'a[href], button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])';

export function showModal(title, bodyHtml, footerHtml = '', { size = 'md', onEnter = null } = {}) {
  const overlay = document.getElementById('modal-overlay');
  const box = document.getElementById('modal-box');
  if (!overlay || !box) return;

  _lastFocus = document.activeElement;

  // Reset size class (modal-sm | modal-md | modal-lg)
  box.classList.remove('modal-sm', 'modal-md', 'modal-lg', 'modal-xl');
  box.classList.add(`modal-${size}`);

  document.getElementById('modal-title').textContent = title;
  document.getElementById('modal-body').innerHTML = bodyHtml;
  document.getElementById('modal-footer').innerHTML = footerHtml;
  overlay.classList.remove('hidden');

  // Focus first focusable element inside modal
  requestAnimationFrame(() => {
    const first = box.querySelector('input:not([type="hidden"]), textarea, select') ||
                  box.querySelector(FOCUSABLE);
    first?.focus();
  });

  // Enter-to-submit: invoke onEnter (or default primary button) when Enter pressed
  if (onEnter || _modalEnterHandler == null) {
    _modalEnterHandler = (e) => {
      if (e.key !== 'Enter') return;
      // Ignore Enter inside textarea (multiline)
      if (e.target.tagName === 'TEXTAREA') return;
      const handler = onEnter || (() => {
        const primary = box.querySelector('.modal-footer .btn-primary, .modal-footer .btn-success, .modal-footer .btn-danger');
        primary?.click();
      });
      e.preventDefault();
      handler();
    };
    box.addEventListener('keydown', _modalEnterHandler);
  }
}

export function closeModal() {
  const overlay = document.getElementById('modal-overlay');
  const box = document.getElementById('modal-box');
  if (!overlay || overlay.classList.contains('hidden')) return;

  overlay.classList.add('hidden');
  document.getElementById('modal-body').innerHTML = '';
  document.getElementById('modal-footer').innerHTML = '';

  if (_modalEnterHandler) {
    box.removeEventListener('keydown', _modalEnterHandler);
    _modalEnterHandler = null;
  }
  // Restore focus to trigger
  _lastFocus?.focus?.();
  _lastFocus = null;
}

// Global key handlers — Escape closes modal, Tab is trapped inside it
document.addEventListener('keydown', (e) => {
  const overlay = document.getElementById('modal-overlay');
  if (!overlay || overlay.classList.contains('hidden')) return;

  if (e.key === 'Escape') {
    e.preventDefault();
    closeModal();
    return;
  }

  if (e.key === 'Tab') {
    const box = document.getElementById('modal-box');
    const focusables = Array.from(box.querySelectorAll(FOCUSABLE)).filter(el => !el.disabled && el.offsetParent !== null);
    if (focusables.length === 0) return;
    const first = focusables[0];
    const last = focusables[focusables.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  }
});

// ── Formatting ───────────────────────────────────────────────────
export function fmtDate(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  if (isNaN(d.getTime())) return '—';
  return d.toLocaleDateString('en-AU', { day: 'numeric', month: 'short', year: 'numeric' });
}

export function fmtDateTime(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  if (isNaN(d.getTime())) return '—';
  return d.toLocaleString('en-AU', {
    day: 'numeric', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

export function fmtRelative(iso) {
  if (!iso) return '—';
  const t = new Date(iso).getTime();
  if (isNaN(t)) return '—';
  const diff = Date.now() - t;
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
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// ── Badge helpers ────────────────────────────────────────────────
export function badge(value, extraClass = '') {
  if (!value) return '<span class="badge badge-muted">—</span>';
  const cls = extraClass || `badge-${String(value).toLowerCase().replace(/\s+/g, '_')}`;
  return `<span class="badge ${cls}">${esc(String(value).replace(/_/g, ' '))}</span>`;
}

export function tierBadge(tier) {
  if (!tier) return '<span class="badge badge-muted">None</span>';
  return `<span class="badge tier-${esc(tier)}">${esc(String(tier).replace(/_/g, ' '))}</span>`;
}

export function recBadge(type) {
  if (!type) return '';
  const icons = { add: '＋', increase: '↑', decrease: '↓', maintain: '→', retire: '✕' };
  return `<span class="badge rec-${esc(type)}">${icons[type] || ''} ${esc(type)}</span>`;
}

export function confBadge(level) {
  if (!level) return '';
  return `<span class="badge badge-${esc(String(level).toLowerCase())}">${esc(level)}</span>`;
}

export function posBadge(pos) {
  const cls = pos === 1 ? 'pos-1' : pos === 2 ? 'pos-2' : pos === 3 ? 'pos-3' : 'pos-n';
  return `<span class="pos-badge ${cls}">${esc(pos)}</span>`;
}

// ── Loading helpers ──────────────────────────────────────────────
export function setLoading(el) {
  if (!el) return;
  el.innerHTML = '<div class="loader-center"><div class="loader" role="status" aria-label="Loading"></div></div>';
}

/** Render a skeleton placeholder while data loads. */
export function setSkeleton(el, variant = 'card') {
  if (!el) return;
  if (variant === 'list') {
    el.innerHTML = `
      <div class="card">
        <div class="skel skel-row"></div>
        <div class="skel skel-row"></div>
        <div class="skel skel-row"></div>
        <div class="skel skel-row"></div>
        <div class="skel skel-row"></div>
      </div>`;
  } else if (variant === 'stats') {
    el.innerHTML = `
      <div class="stats-grid mb-5">
        <div class="skel skel-stat"></div>
        <div class="skel skel-stat"></div>
        <div class="skel skel-stat"></div>
        <div class="skel skel-stat"></div>
      </div>
      <div class="card">
        <div class="skel skel-row"></div>
        <div class="skel skel-row"></div>
        <div class="skel skel-row"></div>
      </div>`;
  } else {
    el.innerHTML = `
      <div class="card">
        <div class="skel skel-title"></div>
        <div class="skel skel-row"></div>
        <div class="skel skel-row"></div>
        <div class="skel skel-row"></div>
      </div>`;
  }
}

/** Toggle a button into / out of a loading state. */
export function setBtnLoading(btn, loading, loadingLabel = 'Working…') {
  if (!btn) return;
  if (loading) {
    btn.dataset.origLabel = btn.dataset.origLabel || btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = `<span class="btn-spinner" aria-hidden="true"></span>${esc(loadingLabel)}`;
  } else {
    btn.disabled = false;
    btn.innerHTML = btn.dataset.origLabel || btn.textContent;
    delete btn.dataset.origLabel;
  }
}

// ── Confirmation dialog convenience ──────────────────────────────
export function confirmModal({ title, message, confirmLabel = 'Confirm', cancelLabel = 'Cancel', danger = false }) {
  return new Promise((resolve) => {
    const cancelId = `cm-cancel-${Date.now()}`;
    const confirmId = `cm-confirm-${Date.now()}`;
    showModal(
      title,
      `<p class="text-2 text-sm" style="line-height:1.55">${esc(message)}</p>`,
      `<button class="btn btn-ghost" id="${cancelId}" type="button">${esc(cancelLabel)}</button>
       <button class="btn ${danger ? 'btn-danger' : 'btn-primary'}" id="${confirmId}" type="button">${esc(confirmLabel)}</button>`,
      { size: 'sm' }
    );
    document.getElementById(cancelId).addEventListener('click', () => { closeModal(); resolve(false); });
    document.getElementById(confirmId).addEventListener('click', () => { closeModal(); resolve(true); });
  });
}

// ── Pagination ───────────────────────────────────────────────────
/**
 * Render a pagination bar into `container`.
 *
 * @param {HTMLElement} container  - Element that receives the pagination bar.
 * @param {object} opts
 * @param {number} opts.total      - Total item count from X-Total-Count header.
 * @param {number} opts.limit      - Page size.
 * @param {number} opts.offset     - Current offset.
 * @param {function} opts.onNavigate - Called with new offset when user clicks.
 */
export function mountPagination(container, { total, limit, offset, onNavigate }) {
  if (!container) return;
  if (total <= limit) {
    container.innerHTML = '';
    return;
  }
  const currentPage = Math.floor(offset / limit) + 1;
  const totalPages  = Math.ceil(total / limit);
  const hasPrev = offset > 0;
  const hasNext = offset + limit < total;

  container.innerHTML = `
    <div class="pagination">
      <button class="btn btn-ghost btn-sm" id="pg-prev" ${hasPrev ? '' : 'disabled'}>← Prev</button>
      <span class="pagination-info">Page ${currentPage} of ${totalPages} &nbsp;·&nbsp; ${total.toLocaleString()} total</span>
      <button class="btn btn-ghost btn-sm" id="pg-next" ${hasNext ? '' : 'disabled'}>Next →</button>
    </div>`;

  if (hasPrev) {
    container.querySelector('#pg-prev').addEventListener('click', () =>
      onNavigate(Math.max(0, offset - limit))
    );
  }
  if (hasNext) {
    container.querySelector('#pg-next').addEventListener('click', () =>
      onNavigate(offset + limit)
    );
  }
}

// ── Expose on window for inline onclick handlers ─────────────────
window.UI = {
  toast, showModal, closeModal, fmtDate, fmtDateTime, fmtRelative,
  dlBlob, badge, tierBadge, recBadge, confBadge, posBadge, esc,
  setLoading, setSkeleton, setBtnLoading, confirmModal, mountPagination,
};
