import { API } from '../api.js';
import { esc } from '../ui.js';

export async function init(container, actions) {
  actions.innerHTML = '';
  container.innerHTML = '<div class="loader-center"><div class="loader" role="status" aria-label="Loading"></div></div>';

  let stations;
  try {
    stations = await API.stations();
  } catch (err) {
    container.innerHTML = `<div class="alert alert-danger">Failed to load stations: ${esc(err.message)}</div>`;
    return;
  }

  if (!stations.length) {
    container.innerHTML = `<div class="empty-state">
      <div class="empty-icon">📡</div>
      <div class="empty-title">No stations found</div>
      <div class="empty-desc">Station seeds may not have run yet. Check application startup logs.</div>
    </div>`;
    return;
  }

  container.innerHTML = `
    <div class="card mb-5">
      <div class="card-header">
        <span class="card-title">${stations.length} Station${stations.length !== 1 ? 's' : ''}</span>
        <span class="text-3 text-sm">Configured sources vary per station</span>
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr>
            <th>Call Sign</th>
            <th>Station Name</th>
            <th>Frequency</th>
            <th>City</th>
            <th>Country</th>
          </tr></thead>
          <tbody>
            ${stations.map(s => `
              <tr>
                <td><span class="badge badge-accent" style="font-size:12px">${esc(s.call_sign)}</span></td>
                <td style="font-weight:500">${esc(s.name)}</td>
                <td class="text-2">${esc(s.frequency || '—')}</td>
                <td class="text-2">${esc(s.city || '—')}</td>
                <td><span class="badge badge-muted">${esc(s.country_code || '—')}</span></td>
              </tr>`).join('')}
          </tbody>
        </table>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <span class="card-title">About Station Data Collection</span>
      </div>
      <div class="info-box" style="margin-bottom:0">
        <p>
          Each station may have one or more configured data sources (iHeart now-playing,
          recently-played, Online Radio Box, Radiowave Monitor, BBC Sounds, or Manual CSV import).
          Source configuration and collector enablement is managed via environment variables and
          operations passes — not from this console.
          See <code style="font-family:var(--mono);font-size:11px;background:rgba(14,165,233,.15);padding:1px 4px;border-radius:3px">docs/NEXT_STEPS.md</code>
          and the validation register for collector readiness status.
        </p>
      </div>
    </div>`;
}
