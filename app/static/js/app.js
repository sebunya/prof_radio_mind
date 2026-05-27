/**
 * Main application entry point — hash router, nav active state,
 * API status polling, pending-review badge refresh.
 */

import { API, apiCallPaged } from './api.js';
import { toast, closeModal, esc } from './ui.js';

// ── Page registry ────────────────────────────────────────────────
const PAGES = {
  dashboard:          () => import('./pages/dashboard.js'),
  stations:           () => import('./pages/stations.js'),
  review:             () => import('./pages/review.js'),
  reports:            () => import('./pages/reports.js'),
  playlist:           () => import('./pages/playlist.js'),
  charts:             () => import('./pages/aria-charts.js'),
  webhooks:           () => import('./pages/webhooks.js'),
  backfill:           () => import('./pages/backfill.js'),
  'email-reports':    () => import('./pages/email-reports.js'),
  'collector-health': () => import('./pages/collector-health.js'),
};

const TITLES = {
  dashboard:          'Dashboard',
  stations:           'Radio Stations',
  review:             'Review Queue',
  reports:            'Reports',
  playlist:           'Playlist Automation',
  charts:             'ARIA Charts',
  webhooks:           'Webhooks',
  backfill:           'Historical Backfill',
  'email-reports':    'Email Reports',
  'collector-health': 'Collector Health',
};

// ── Router ───────────────────────────────────────────────────────
let _navToken = 0;

function getRoute() {
  return window.location.hash.replace(/^#\//, '').split('?')[0] || 'dashboard';
}

async function navigate(route) {
  const token   = ++_navToken;
  const content = document.getElementById('page-content');
  const titleEl = document.getElementById('page-title');
  const actions = document.getElementById('page-actions');

  // Sync nav active state
  document.querySelectorAll('.nav-item').forEach(el => {
    el.classList.toggle('active', el.dataset.page === route);
  });

  titleEl.textContent = TITLES[route] || route;
  actions.innerHTML = '';
  content.innerHTML = '<div class="loader-center"><div class="loader"></div></div>';

  const loader = PAGES[route];
  if (!loader) {
    content.innerHTML = `<div class="empty-state">
      <div class="empty-icon">🔍</div>
      <div class="empty-title">Page not found</div>
      <div class="empty-desc">Route "/${route}" doesn't exist.</div>
    </div>`;
    return;
  }

  try {
    const mod = await loader();
    if (token !== _navToken) return; // stale navigation, bail
    await mod.init(content, actions);
  } catch (err) {
    console.error('[router]', err);
    content.innerHTML = `<div class="alert alert-danger">
      <strong>Failed to load page:</strong> ${esc(err.message)}
    </div>`;
  }
}

// ── API status indicator ─────────────────────────────────────────
async function refreshApiStatus() {
  const el = document.getElementById('api-status');
  try {
    const h = await API.health();
    el.textContent = h.status === 'ok' ? '● API OK' : '◐ Degraded';
    el.className   = `api-status ${h.status === 'ok' ? 'ok' : 'checking'}`;
  } catch {
    el.textContent = '● API Down';
    el.className   = 'api-status error';
  }
}

// ── Pending review badge ─────────────────────────────────────────
async function refreshPendingBadge() {
  try {
    // Fetch just 1 item to get the total from X-Total-Count; avoids loading all items.
    const { total } = await apiCallPaged('GET', '/review-items?status=pending&limit=1&offset=0');
    const badge = document.getElementById('nav-pending-badge');
    if (total > 0) {
      badge.textContent = total > 99 ? '99+' : total;
      badge.hidden = false;
    } else {
      badge.hidden = true;
    }
  } catch { /* swallow — badge is optional */ }
}

// ── Modal close wiring ───────────────────────────────────────────
document.getElementById('modal-close-btn').addEventListener('click', closeModal);
document.getElementById('modal-overlay').addEventListener('click', (e) => {
  if (e.target === e.currentTarget) closeModal();
});

// ── Tab visibility: pause polling when hidden ────────────────────
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible') {
    refreshApiStatus();
    refreshPendingBadge();
  }
});

// ── Mobile sidebar toggle ────────────────────────────────────────
const sidebarToggle = document.getElementById('sidebar-toggle');
const sidebar       = document.getElementById('sidebar');
const scrim         = document.getElementById('sidebar-scrim');

if (sidebarToggle) {
  sidebarToggle.addEventListener('click', () => {
    const isOpen = sidebar.classList.toggle('open');
    sidebarToggle.setAttribute('aria-expanded', isOpen);
    if (scrim) scrim.hidden = !isOpen;
  });
}
if (scrim) {
  scrim.addEventListener('click', () => {
    sidebar.classList.remove('open');
    if (sidebarToggle) sidebarToggle.setAttribute('aria-expanded', 'false');
    scrim.hidden = true;
  });
}
// Close sidebar on nav (mobile)
document.querySelectorAll('.nav-item').forEach(el => {
  el.addEventListener('click', () => {
    if (window.innerWidth < 640) {
      sidebar.classList.remove('open');
      if (sidebarToggle) sidebarToggle.setAttribute('aria-expanded', 'false');
      if (scrim) scrim.hidden = true;
    }
  });
});

// ── Boot ─────────────────────────────────────────────────────────
window.addEventListener('hashchange', () => navigate(getRoute()));

navigate(getRoute());
refreshApiStatus();
refreshPendingBadge();

// Soft refresh every 30 s — store IDs so we can clear on unload
const _statusInterval  = setInterval(refreshApiStatus,    30_000);
const _badgeInterval   = setInterval(refreshPendingBadge, 30_000);

window.addEventListener('beforeunload', () => {
  clearInterval(_statusInterval);
  clearInterval(_badgeInterval);
});
