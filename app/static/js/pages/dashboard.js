import { API } from '../api.js';
import { fmtRelative, badge, esc } from '../ui.js';

export async function init(container) {
  container.innerHTML = '<div class="loader-center"><div class="loader" role="status" aria-label="Loading"></div></div>';

  const [overview, events, reviewItems, metadata] = await Promise.allSettled([
    API.adminOverview(), API.adminRecentEvents(), API.reviewItems(), API.adminMetadataReadiness()
  ]);

  const ov = overview.status === 'fulfilled' ? overview.value : {};
  const ev = events.status === 'fulfilled' ? events.value : [];
  const il = reviewItems.status === 'fulfilled' ? reviewItems.value : [];
  const meta = metadata.status === 'fulfilled' ? metadata.value : {};

  const pending = ov.stats ? ov.stats.pending_reviews : il.filter(i => i.status === 'pending').length;
  const activeStationsCount = ov.stats ? ov.stats.active_stations : 0;
  const activeWebhooksCount = ov.stats ? ov.stats.active_webhooks : 0;
  const apiOk = ov.stats !== undefined;

  // Aggregate counts
  const byStatus = { pending: 0, reviewed: 0, dismissed: 0, escalated: 0 };
  const byType   = {};
  il.forEach(i => {
    byStatus[i.status] = (byStatus[i.status] || 0) + 1;
    byType[i.item_type] = (byType[i.item_type] || 0) + 1;
  });

  const envLabel = ov.app_env ? ov.app_env.toUpperCase() : 'DEVELOPMENT';
  const envBadgeClass = ov.app_env === 'production' ? 'badge-danger' : 'badge-accent';

  container.innerHTML = `
    <!-- ── Environment & Safety Banner ── -->
    <div style="background:var(--bg2);border:1px solid var(--border);border-radius:var(--r);padding:14px 20px;margin-bottom:20px;display:flex;align-items:center;justify-content:between;gap:12px;flex-wrap:wrap">
      <div style="display:flex;align-items:center;gap:10px">
        <span class="badge ${envBadgeClass}" style="font-size:11px;padding:3px 10px">${esc(envLabel)} ENVIRONMENT</span>
        <span class="text-2 text-sm">Safety flags are monitored. Automatic ingestion is gated.</span>
      </div>
      <div style="display:flex;gap:8px;align-items:center">
        <span class="badge ${ov.scheduler_enabled ? 'badge-success' : 'badge-muted'}">SCHEDULER: ${ov.scheduler_enabled ? 'ON' : 'OFF'}</span>
        <span class="badge ${ov.enable_capital_collector ? 'badge-success' : 'badge-muted'}">CAPITAL: ${ov.enable_capital_collector ? 'ON' : 'OFF'}</span>
        <span class="badge ${ov.enable_nova_collector ? 'badge-success' : 'badge-muted'}">NOVA: ${ov.enable_nova_collector ? 'ON' : 'OFF'}</span>
        <span class="badge ${ov.enable_kiis_collector ? 'badge-success' : 'badge-muted'}">KIIS: ${ov.enable_kiis_collector ? 'ON' : 'OFF'}</span>
      </div>
    </div>

    <!-- ── Stats ── -->
    <div class="stats-grid mb-5">
      <div class="stat-card">
        <div class="stat-label">Active Stations</div>
        <div class="stat-value accent">${activeStationsCount}</div>
        <div class="stat-meta">Radio stations seeded in DB</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Pending Reviews</div>
        <div class="stat-value ${pending > 0 ? 'warning' : 'success'}">${pending}</div>
        <div class="stat-meta">${il.length} total items in queue</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Active Webhooks</div>
        <div class="stat-value">${activeWebhooksCount}</div>
        <div class="stat-meta">Push subscriptions registered</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">System Status</div>
        <div class="stat-value ${apiOk ? 'success' : 'danger'}" style="font-size:20px;padding-top:6px">
          <span class="dot ${apiOk ? 'dot-ok' : 'dot-error'}"></span>
          ${apiOk ? 'Operational' : 'Degraded'}
        </div>
        <div class="stat-meta">
          Auth: ${ov.admin_basic_auth_configured ? '🔒 Secure' : '🔓 Public'}
          &nbsp;·&nbsp;
          Retention: ${ov.raw_payload_retention_days > 0 ? `${ov.raw_payload_retention_days}d` : 'Off'}
        </div>
      </div>
    </div>

    <!-- ── Metadata Enrichment Overview ── -->
    <div class="card mb-5">
      <div class="card-header">
        <span class="card-title">Metadata Enrichment Readiness</span>
        <span class="badge badge-muted">Status: ${esc(meta.status || 'disabled')} (${esc(meta.mode || 'readiness_only')})</span>
      </div>
      <div style="font-size:13px;line-height:1.5;padding:12px 0 0 0">
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:20px;margin-bottom:12px">
          <div style="background:var(--bg3);border-radius:6px;padding:12px;border:1px solid var(--border2)">
            <div style="font-weight:600;margin-bottom:6px;color:var(--text);display:flex;justify-content:space-between;font-size:12px">
              <span>MusicBrainz</span>
              <span class="badge badge-muted">Readiness Only</span>
            </div>
            <div style="font-size:11px;color:var(--text2)">
              Status: <strong>${meta.providers?.musicbrainz?.configured ? 'Configured' : 'Not Configured'}</strong><br>
              Enrichment: <strong>Disabled</strong><br>
              Role: Open Canonical Identity
            </div>
          </div>

          <div style="background:var(--bg3);border-radius:6px;padding:12px;border:1px solid var(--border2)">
            <div style="font-weight:600;margin-bottom:6px;color:var(--text);display:flex;justify-content:space-between;font-size:12px">
              <span>Spotify</span>
              <span class="badge badge-muted">Readiness Only</span>
            </div>
            <div style="font-size:11px;color:var(--text2)">
              Status: <strong>${meta.providers?.spotify?.configured ? 'Configured' : 'Not Configured'}</strong><br>
              Enrichment: <strong>Disabled</strong><br>
              Role: Catalogue Context
            </div>
          </div>

          <div style="background:var(--bg3);border-radius:6px;padding:12px;border:1px solid var(--border2)">
            <div style="font-weight:600;margin-bottom:6px;color:var(--text);display:flex;justify-content:space-between;font-size:12px">
              <span>Cover Art Archive</span>
              <span class="badge badge-muted">Readiness Only</span>
            </div>
            <div style="font-size:11px;color:var(--text2)">
              Status: <strong>${meta.providers?.cover_art_archive?.configured ? 'Configured' : 'Not Configured'}</strong><br>
              Enrichment: <strong>Disabled</strong><br>
              Role: Artwork Fallback
            </div>
          </div>
        </div>
        <div style="font-size:11px;color:var(--text3);padding-top:10px;border-top:1px solid var(--border2)">
          ℹ <strong>Resolved Metadata DB:</strong> No resolved metadata table has been implemented yet. Provider readiness is available for future enrichment passes.
        </div>
      </div>
    </div>

    <!-- ── System state strip ── -->
    ${ov ? systemStatusStrip(ov) : ''}

    <!-- ── Charts ── -->
    <div class="charts-grid mb-5">
      <div class="card">
        <div class="card-header">
          <span class="card-title">Queue by Status</span>
          <span class="text-3 text-sm">${il.length} items</span>
        </div>
        <div class="chart-wrap"><canvas id="ch-status"></canvas></div>
      </div>
      <div class="card">
        <div class="card-header">
          <span class="card-title">Queue by Type</span>
        </div>
        <div class="chart-wrap"><canvas id="ch-type"></canvas></div>
      </div>
    </div>

    <!-- ── Recent captured play events ── -->
    <div class="card mb-5">
      <div class="card-header">
        <span class="card-title">Live Capture Streams</span>
        <a href="#/play-events" class="btn btn-ghost btn-sm">View stream →</a>
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr>
            <th>Station</th><th>Played At (UTC)</th><th>Artist</th><th>Title</th><th>Deduplication</th>
          </tr></thead>
          <tbody>${ev.slice(0, 6).map(e => `
            <tr>
              <td><span class="badge badge-accent">${esc(e.station_call_sign)}</span></td>
              <td class="text-2">${fmtDateTime(e.played_at)}</td>
              <td style="font-weight:500">${esc(e.raw_artist)}</td>
              <td>${esc(e.raw_title)}</td>
              <td>
                ${e.is_duplicate ? '<span class="badge badge-warning">Duplicate</span>' : '<span class="badge badge-success">Unique</span>'}
              </td>
            </tr>`).join('') || `<tr><td colspan="5" class="td-empty">No tracks captured yet. Automatic ingestion is disabled. Use historical backfill.</td></tr>`}
          </tbody>
        </table>
      </div>
    </div>

    <!-- ── Recent review items ── -->
    <div class="card">
      <div class="card-header">
        <span class="card-title">Recent Review Items</span>
        <a href="#/review" class="btn btn-ghost btn-sm">View all →</a>
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Title</th><th>Type</th><th>Status</th><th>Age</th></tr></thead>
          <tbody>${il.slice(0, 6).map(item => `
            <tr>
              <td class="trunc" title="${esc(item.title)}" style="max-width:300px">${esc(item.title)}</td>
              <td>${badge(item.item_type)}</td>
              <td>${badge(item.status)}</td>
              <td class="text-3 text-sm">${fmtRelative(item.created_at)}</td>
            </tr>`).join('') || `<tr><td colspan="4" class="td-empty">No review items yet</td></tr>`}
          </tbody>
        </table>
      </div>
    </div>`;

  // Render charts after DOM update
  requestAnimationFrame(() => {
    renderStatusChart(byStatus);
    renderTypeChart(byType);
  });
}

function systemStatusStrip(ov) {
  function chip(label, value, cls) {
    const dotCls = {
      'chip-ok': 'dot-green',
      'chip-warn': 'dot-yellow',
      'chip-muted': 'dot-grey',
      'chip-info': 'dot-blue',
      'chip-danger': 'dot-red',
    }[cls] || 'dot-grey';
    return `<span class="status-chip ${cls}">
      <span class="status-dot ${dotCls}"></span>
      ${esc(label)}: ${esc(value)}
    </span>`;
  }

  const schedulerChip = ov.scheduler_enabled
    ? chip('Scheduler', 'Enabled', 'chip-warn')
    : chip('Scheduler', 'Disabled', 'chip-muted');

  const isProd = ov.app_env === 'production';
  const docsExposed = isProd ? ov.enable_docs_in_production : true;
  const docsChip = docsExposed
    ? chip('API Docs', 'Exposed', isProd ? 'chip-warn' : 'chip-info')
    : chip('API Docs', 'Hidden', 'chip-ok');

  const authChip = ov.admin_basic_auth_configured
    ? chip('Admin Auth', 'Protected', 'chip-ok')
    : chip('Admin Auth', 'Public', 'chip-info');

  const dedupChip = chip('Deduplication', 'Active', 'chip-ok');

  const retentionEnabled = ov.raw_payload_retention_days > 0;
  const retChip = retentionEnabled
    ? chip('Retention', `${ov.raw_payload_retention_days}d`, 'chip-info')
    : chip('Retention', 'Off', 'chip-muted');

  return `<div class="system-status-strip mb-5">
    ${schedulerChip}${docsChip}${authChip}${dedupChip}${retChip}
    <a href="#/operations" class="btn btn-ghost btn-xs" style="margin-left:auto">
      View Operations →
    </a>
  </div>`;
}

function renderStatusChart(d) {
  const ctx = document.getElementById('ch-status');
  if (!ctx || !window.Chart) return;
  new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Pending', 'Reviewed', 'Dismissed', 'Escalated'],
      datasets: [{
        data: [d.pending, d.reviewed, d.dismissed, d.escalated],
        backgroundColor: [
          'rgba(245,158,11,.75)',
          'rgba(16,185,129,.75)',
          'rgba(100,116,139,.75)',
          'rgba(239,68,68,.75)',
        ],
        borderColor: '#1e293b',
        borderWidth: 2,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false, cutout: '68%',
      plugins: {
        legend: { position: 'right', labels: { color: '#94a3b8', boxWidth: 10, padding: 10, font: { size: 11 } } },
      },
    },
  });
}

function renderTypeChart(d) {
  const ctx = document.getElementById('ch-type');
  if (!ctx || !window.Chart) return;
  const labels = Object.keys(d).map(k => k.replace(/_/g, ' '));
  const values = Object.values(d);
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{ data: values, backgroundColor: 'rgba(14,165,233,.6)', borderColor: '#0ea5e9', borderWidth: 1, borderRadius: 4 }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: '#94a3b8', font: { size: 10 } }, grid: { color: 'rgba(255,255,255,.04)' } },
        y: { ticks: { color: '#94a3b8', font: { size: 10 }, stepSize: 1 }, grid: { color: 'rgba(255,255,255,.04)' }, beginAtZero: true },
      },
    },
  });
}
