import { API } from '../api.js';
import { esc, badge } from '../ui.js';

export async function init(container, actions) {
  actions.innerHTML = '';
  container.innerHTML = '<div class="loader-center"><div class="loader"></div></div>';

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
      <div class="empty-desc">Station seeds may not have run yet. Check the API logs.</div>
    </div>`;
    return;
  }

  container.innerHTML = `
    <div class="card">
      <div class="card-header">
        <span class="card-title">${stations.length} Station${stations.length !== 1 ? 's' : ''}</span>
        <span class="text-3 text-sm">Auto-collected every 3 minutes</span>
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr>
            <th>Call Sign</th>
            <th>Station Name</th>
            <th>Frequency</th>
            <th>City</th>
            <th>Country</th>
            <th>Station ID</th>
          </tr></thead>
          <tbody>
            ${stations.map(s => `
              <tr>
                <td><span class="badge badge-accent" style="font-size:12px">${esc(s.call_sign)}</span></td>
                <td style="font-weight:500">${esc(s.name)}</td>
                <td class="text-2">${esc(s.frequency || '—')}</td>
                <td class="text-2">${esc(s.city || '—')}</td>
                <td>
                  <span class="badge badge-muted">${esc(s.country_code || 'AU')}</span>
                </td>
                <td><code class="mono">${s.id ? s.id.slice(0,8) + '…' : '—'}</code></td>
              </tr>`).join('')}
          </tbody>
        </table>
      </div>
    </div>

    <div class="card mt-4">
      <div class="card-header">
        <span class="card-title">Collection Coverage</span>
      </div>
      <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px">
        ${stations.map(s => `
          <div style="background:var(--bg3);border-radius:6px;padding:14px">
            <div style="font-weight:600;margin-bottom:6px">${esc(s.call_sign)}</div>
            <div class="text-3 text-xs" style="margin-bottom:8px">${esc(s.name)}</div>
            <div style="display:flex;gap:6px;flex-wrap:wrap">
              <span class="badge badge-info">Radiowave</span>
              <span class="badge badge-accent">iHeart</span>
              <span class="badge badge-muted">Manual CSV</span>
            </div>
          </div>`).join('')}
      </div>
    </div>`;
}
