/**
 * Main application entry point — hash router, nav active state,
 * API status polling, pending-review badge refresh, mobile sidebar toggle.
 */

import { API } from './api.js';
import { toast, closeModal } from './ui.js';

// ── Page registry ────────────────────────────────────────────────
const PAGES = {
  dashboard:  () => import('./pages/dashboard.js'),
  stations:   () => import('./pages/stations.js'),
  review:     () => import('./pages/review.js'),
  reports:    () => import('./pages/reports.js'),
  playlist:   () => import('./pages/playlist.js'),
  charts:     () => import('./pages/aria-charts.js'),
  webhooks:   () => import('./pages/webhooks.js'),
  backfill:   () => import('./pages/backfill.js'),
  operations: () => import('./pages/operations.js'),
};

const TITLES = {
  dashboard:  'Dashboard',
  stations:   'Radio Stations',
  review:     'Review Queue',
  reports:    'Reports',
  playlist:   'Playlist Automation',
  charts:     'ARIA Charts',
  webhooks:   'Webhooks',
  backfill:   'Historical Backfill',
  operations: 'Operations',
};

// ── Router ───────────────────────────────────────────────────────
function getRoute() {
  return window.location.hash.replace(/^#\//, '').split('?')[0] || 'dashboard';
}

let _navToken = 0;

async function navigate(route) {
  const token = ++_navToken;
  const content = document.getElementById('page-content');
  const titleEl = document.getElementById('page-title');
  const actions  = document.getElementById('page-actions');

  // Sync nav active state
  document.querySelectorAll('.nav-item').forEach(el => {
    el.classList.toggle('active', el.dataset.page === route);
  });

  titleEl.textContent = TITLES[route] || route;
  actions.innerHTML   = '';
  content.innerHTML   = '<div class="loader-center"><div class="loader" role="status" aria-label="Loading"></div></div>';

  // Close mobile sidebar after navigation
  closeSidebar();

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
    if (token !== _navToken) return; // stale navigation
    await mod.init(content, actions);
  } catch (err) {
    if (token !== _navToken) return;
    console.error('[router]', err);
    content.innerHTML = `<div class="alert alert-danger">
      <strong>Failed to load page.</strong> Please refresh and try again.
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

// ── Environment badge ────────────────────────────────────────────
async function refreshEnvBadge() {
  try {
    const data  = await API.adminOverview();
    const badge = document.getElementById('env-badge');
    const env   = data.environment || 'unknown';
    badge.textContent = env.toUpperCase();
    badge.className   = `env-badge ${
      env === 'production' ? 'env-prod' :
      env === 'staging'    ? 'env-staging' : 'env-dev'
    }`;
    badge.hidden = (env === 'development'); // hide dev badge to reduce noise
  } catch {
    // non-critical — badge stays hidden
  }
}

// ── Pending review badge ─────────────────────────────────────────
async function refreshPendingBadge() {
  try {
    const items = await API.reviewItems('pending');
    const badge = document.getElementById('nav-pending-badge');
    const n = items.length;
    if (n > 0) {
      badge.textContent = n > 99 ? '99+' : String(n);
      badge.hidden = false;
    } else {
      badge.hidden = true;
    }
  } catch { /* swallow — badge is optional */ }
}

// ── Mobile sidebar toggle ────────────────────────────────────────
function closeSidebar() {
  const sidebar = document.getElementById('sidebar');
  const scrim   = document.getElementById('sidebar-scrim');
  const toggle  = document.getElementById('sidebar-toggle');
  sidebar.classList.remove('open');
  if (scrim)  scrim.hidden = true;
  if (toggle) toggle.setAttribute('aria-expanded', 'false');
}

document.getElementById('sidebar-toggle')?.addEventListener('click', () => {
  const sidebar = document.getElementById('sidebar');
  const scrim   = document.getElementById('sidebar-scrim');
  const toggle  = document.getElementById('sidebar-toggle');
  const isOpen  = sidebar.classList.toggle('open');
  if (scrim)  scrim.hidden = !isOpen;
  if (toggle) toggle.setAttribute('aria-expanded', String(isOpen));
});

document.getElementById('sidebar-scrim')?.addEventListener('click', closeSidebar);

// ── Modal close wiring ───────────────────────────────────────────
document.getElementById('modal-close-btn').addEventListener('click', closeModal);
document.getElementById('modal-overlay').addEventListener('click', (e) => {
  if (e.target === e.currentTarget) closeModal();
});

// ── Boot ─────────────────────────────────────────────────────────
window.addEventListener('hashchange', () => navigate(getRoute()));

navigate(getRoute());
refreshApiStatus();
refreshPendingBadge();
refreshEnvBadge();

// Soft refresh every 30 s
setInterval(refreshApiStatus,    30_000);
setInterval(refreshPendingBadge, 30_000);
