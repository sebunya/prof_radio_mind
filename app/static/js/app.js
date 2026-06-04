/**
 * Main application entry point — hash router, nav active state,
 * API status polling, pending-review badge refresh.
 */

import { API } from './api.js';
import { toast, closeModal } from './ui.js';

// ── Page registry ────────────────────────────────────────────────
const PAGES = {
  dashboard: () => import('./pages/dashboard.js'),
  stations:  () => import('./pages/stations.js'),
  'play-events': () => import('./pages/play-events.js'),
  review:    () => import('./pages/review.js'),
  'spotify-metadata': () => import('./pages/spotify-metadata.js'),
  reports:   () => import('./pages/reports.js'),
  playlist:  () => import('./pages/playlist.js'),
  charts:    () => import('./pages/aria-charts.js'),
  webhooks:  () => import('./pages/webhooks.js'),
  backfill:  () => import('./pages/backfill.js'),
  'operations-guardrails': () => import('./pages/operations-guardrails.js'),
};

const TITLES = {
  dashboard: 'Dashboard',
  stations:  'Stations & Sources Health',
  'play-events': 'Play Events Stream',
  review:    'Review Queue',
  'spotify-metadata': 'Spotify Metadata Readiness',
  reports:   'Reports',
  playlist:  'Playlist Automation',
  charts:    'ARIA Charts',
  webhooks:  'Webhooks',
  backfill:  'Historical Backfill',
  'operations-guardrails': 'Operations & Safety Guardrails',
};

// ── Router ───────────────────────────────────────────────────────
function getRoute() {
  return window.location.hash.replace(/^#\//, '').split('?')[0] || 'dashboard';
}

async function navigate(route) {
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
    await mod.init(content, actions);
  } catch (err) {
    console.error('[router]', err);
    content.innerHTML = `<div class="alert alert-danger">
      <strong>Failed to load page:</strong> ${err.message}
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
    const items = await API.reviewItems('pending');
    const badge = document.getElementById('nav-pending-badge');
    const n = items.length;
    if (n > 0) {
      badge.textContent = n > 99 ? '99+' : n;
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

// ── Boot ─────────────────────────────────────────────────────────
window.addEventListener('hashchange', () => navigate(getRoute()));

navigate(getRoute());
refreshApiStatus();
refreshPendingBadge();

// Soft refresh every 30 s
setInterval(refreshApiStatus,   30_000);
setInterval(refreshPendingBadge, 30_000);
