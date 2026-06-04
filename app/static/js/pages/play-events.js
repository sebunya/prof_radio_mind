import { API } from '../api.js';
import { esc, fmtDateTime } from '../ui.js';

export async function init(container, actions) {
  actions.innerHTML = '';
  container.innerHTML = '<div class="loader-center"><div class="loader"></div></div>';

  let events = [];
  try {
    events = await API.adminRecentEvents();
  } catch (err) {
    container.innerHTML = `<div class="alert alert-danger">Failed to load captured play events: ${esc(err.message)}</div>`;
    return;
  }

  container.innerHTML = `
    <div class="card">
      <div class="card-header">
        <span class="card-title">Real-Time Ingestion Logs</span>
        <span class="text-3 text-sm">Showing last 10 captured broadcasts</span>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Station</th>
              <th>Played At (UTC)</th>
              <th>Artist Name</th>
              <th>Song Title</th>
              <th>Deduplication</th>
              <th>Fingerprint</th>
              <th>Spotify Enrichment</th>
            </tr>
          </thead>
          <tbody>
            ${events.map(e => {
              const duplicateBadge = e.is_duplicate 
                ? '<span class="badge badge-warning">Duplicate</span>' 
                : '<span class="badge badge-success">Unique</span>';

              return `
                <tr>
                  <td><span class="badge badge-accent">${esc(e.station_call_sign)}</span></td>
                  <td class="text-2">${fmtDateTime(e.played_at)}</td>
                  <td style="font-weight:500">${esc(e.raw_artist)}</td>
                  <td>${esc(e.raw_title)}</td>
                  <td>${duplicateBadge}</td>
                  <td><code class="mono" style="font-size:10px" title="${esc(e.fingerprint || '—')}">${esc(e.fingerprint ? e.fingerprint.slice(0, 12) + '...' : '—')}</code></td>
                  <td><span class="badge badge-muted">Not Configured</span></td>
                </tr>
              `;
            }).join('') || `
              <tr>
                <td colspan="7" class="td-empty">
                  <div class="empty-state">
                    <div class="empty-icon">📻</div>
                    <div class="empty-title">Capture stream is empty</div>
                    <div class="empty-desc">Scheduler and collectors are offline. Use the Backfill tab to import tracks.</div>
                  </div>
                </td>
              </tr>
            `}
          </tbody>
        </table>
      </div>
    </div>
  `;
}
