import { API } from '../api.js';
import { toast, showModal, closeModal, fmtDateTime, esc, badge } from '../ui.js';

const VALID_EVENTS = ['play.detected', 'no_track.detected', 'reconciliation.completed'];

let _subs = [];
let _container;

export async function init(container, actions) {
  _container = container;
  actions.innerHTML = '';
  container.innerHTML = '<div class="loader-center"><div class="loader"></div></div>';
  await load();
  render(actions);
}

async function load() {
  try { _subs = await API.webhooks(); }
  catch { _subs = []; }
}

function render(actions) {
  actions.innerHTML = `
    <button class="btn btn-primary btn-sm" onclick="window._webhooksPage.openRegisterModal()">
      + New Subscription
    </button>`;

  _container.innerHTML = `
    <!-- ── Overview ── -->
    <div class="stats-grid mb-5" style="grid-template-columns:repeat(3,1fr)">
      <div class="stat-card">
        <div class="stat-label">Active Subscriptions</div>
        <div class="stat-value accent">${_subs.length}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Supported Events</div>
        <div class="stat-value">${VALID_EVENTS.length}</div>
        <div class="stat-meta">${VALID_EVENTS.join(', ')}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">HMAC Signing</div>
        <div class="stat-value" style="font-size:14px;padding-top:6px">
          <span class="dot dot-ok"></span> SHA-256
        </div>
        <div class="stat-meta">Set secret on registration</div>
      </div>
    </div>

    <!-- ── Subscriptions ── -->
    <div class="card">
      <div class="card-header">
        <span class="card-title">Subscriptions</span>
        <span class="text-3 text-sm">${_subs.length} registered</span>
      </div>

      ${_subs.length ? `
        <div id="subs-list">
          ${_subs.map(s => buildSubCard(s)).join('')}
        </div>
      ` : `
        <div class="empty-state">
          <div class="empty-icon">🔗</div>
          <div class="empty-title">No subscriptions yet</div>
          <div class="empty-desc">Register a webhook URL to receive real-time push notifications for play events.</div>
        </div>`}
    </div>

    <!-- ── Event reference ── -->
    <div class="card mt-4">
      <div class="card-header"><span class="card-title">Event Reference</span></div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Event</th><th>When it fires</th><th>Payload keys</th></tr></thead>
          <tbody>
            <tr>
              <td><code class="mono">play.detected</code></td>
              <td class="text-2 text-sm">After each successful collector run with a play event</td>
              <td class="text-3 text-xs mono">station_id, artist, title, played_at, attribution</td>
            </tr>
            <tr>
              <td><code class="mono">no_track.detected</code></td>
              <td class="text-2 text-sm">When collector returns no play (commercial break / parse fail)</td>
              <td class="text-3 text-xs mono">station_id, reason, raw_http_status</td>
            </tr>
            <tr>
              <td><code class="mono">reconciliation.completed</code></td>
              <td class="text-2 text-sm">After nightly deduplication job runs (00:30 AEST)</td>
              <td class="text-3 text-xs mono">stations_checked, duplicates_found, review_items_created</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="alert alert-info mt-4" style="font-size:12px">
        <strong>HMAC Verification:</strong> If a secret is set, each request includes an
        <code class="mono">X-RMIAS-Signature: sha256=&lt;hex&gt;</code> header. Compute
        <code class="mono">HMAC-SHA256(secret, body)</code> to verify authenticity.
      </div>
    </div>`;
}

function buildSubCard(s) {
  return `
    <div class="webhook-card" id="sub-${s.id}">
      <div style="margin-top:2px">
        <span class="dot ${s.is_active ? 'dot-ok' : 'dot-error'}"></span>
      </div>
      <div class="webhook-info">
        <div class="webhook-url">${esc(s.url)}</div>
        <div class="webhook-meta" style="display:flex;gap:8px;flex-wrap:wrap;margin-top:6px">
          ${s.event_types.map(e => `<span class="badge badge-info">${esc(e)}</span>`).join('')}
          <span class="text-3" style="font-size:11px">Registered ${fmtDateTime(s.created_at)}</span>
          ${s.secret ? '<span class="badge badge-accent" style="font-size:9px">HMAC ✓</span>' : ''}
        </div>
      </div>
      <button class="btn btn-danger btn-xs btn-icon" title="Delete subscription"
              onclick="window._webhooksPage.deleteSub('${s.id}')">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/>
          <path d="M10 11v6M14 11v6M9 6V4h6v2"/>
        </svg>
      </button>
    </div>`;
}

function openRegisterModal() {
  showModal(
    'Register Webhook',
    `<div class="form-group">
       <label for="m-wh-url">Endpoint URL</label>
       <input type="url" id="m-wh-url" placeholder="https://yourdomain.com/webhook">
     </div>
     <div class="form-group">
       <label>Event Types</label>
       <div class="checkbox-group">
         ${VALID_EVENTS.map(e => `
           <label class="checkbox-label">
             <input type="checkbox" name="wh-events" value="${e}" checked>
             <code class="mono">${e}</code>
           </label>`).join('')}
       </div>
     </div>
     <div class="form-group">
       <label for="m-wh-secret">Secret (optional)</label>
       <input type="password" id="m-wh-secret" placeholder="Used for HMAC-SHA256 signing">
       <div class="form-hint">Leave blank for unsigned deliveries</div>
     </div>`,
    `<button class="btn btn-ghost" onclick="UI.closeModal()">Cancel</button>
     <button class="btn btn-primary" onclick="window._webhooksPage.submitRegister()">Register</button>`
  );
}

async function submitRegister() {
  const url = document.getElementById('m-wh-url')?.value?.trim();
  if (!url) { toast('warning', 'Enter a URL'); return; }

  const eventTypes = [...document.querySelectorAll('input[name="wh-events"]:checked')].map(c => c.value);
  if (!eventTypes.length) { toast('warning', 'Select at least one event type'); return; }

  const secret = document.getElementById('m-wh-secret')?.value?.trim() || undefined;

  try {
    const sub = await API.registerWebhook({ url, event_types: eventTypes, secret });
    _subs.push(sub);
    closeModal();
    render(document.getElementById('page-actions'));
    toast('success', 'Webhook registered', url);
  } catch (err) {
    toast('error', 'Registration failed', err.message);
  }
}

async function deleteSub(id) {
  const sub = _subs.find(s => s.id === id);
  if (!sub) return;

  showModal(
    'Delete Subscription',
    `<p class="text-2 text-sm">Remove webhook for:</p>
     <div class="mono mt-2" style="word-break:break-all;color:var(--danger)">${esc(sub.url)}</div>`,
    `<button class="btn btn-ghost" onclick="UI.closeModal()">Cancel</button>
     <button class="btn btn-danger" onclick="window._webhooksPage._submitDelete('${id}')">Delete</button>`
  );
}

async function _submitDelete(id) {
  try {
    await API.deleteWebhook(id);
    _subs = _subs.filter(s => s.id !== id);
    closeModal();
    render(document.getElementById('page-actions'));
    toast('success', 'Webhook deleted');
  } catch (err) {
    toast('error', 'Delete failed', err.message);
  }
}

window._webhooksPage = { openRegisterModal, submitRegister, deleteSub, _submitDelete };
