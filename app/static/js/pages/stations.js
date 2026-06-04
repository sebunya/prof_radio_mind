import { API } from '../api.js';
import { esc, badge, fmtDateTime } from '../ui.js';

export async function init(container, actions) {
  actions.innerHTML = '';
  container.innerHTML = '<div class="loader-center"><div class="loader" role="status" aria-label="Loading"></div></div>';

  let stations = [];
  let sources = [];
  try {
    [stations, sources] = await Promise.all([
      API.stations(),
      API.adminSourceHealth(),
    ]);
  } catch (err) {
    container.innerHTML = `<div class="alert alert-danger">Failed to load stations or sources health: ${esc(err.message)}</div>`;
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
    <!-- ── Stations List ── -->
    <div class="card mb-5">
      <div class="card-header">
        <span class="card-title">${stations.length} Station${stations.length !== 1 ? 's' : ''} Configured</span>
        <span class="text-3 text-sm">Station metadata & database registry</span>
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr>
            <th>Call Sign</th>
            <th>Station Name</th>
            <th>Frequency</th>
            <th>City</th>
            <th>Country</th>
            <th>Station ID (UUID)</th>
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
                <td><code class="mono" style="font-size:11px">${esc(s.id || '—')}</code></td>
              </tr>`).join('')}
          </tbody>
        </table>
      </div>
    </div>

    <!-- ── Sources & Validation Health ── -->
    <div class="card">
      <div class="card-header">
        <span class="card-title">Sources & Health Status</span>
        <span class="text-3 text-sm">Real-time source validation monitoring</span>
      </div>
      <div style="display:flex;flex-direction:column;gap:20px">
        ${stations.map(s => {
          const stationSources = sources.filter(src => src.station_call_sign === s.call_sign);
          return `
            <div style="border:1px solid var(--border);border-radius:6px;padding:16px;background:rgba(255,255,255,.01)">
              <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;border-bottom:1px solid var(--border);padding-bottom:8px">
                <div style="font-weight:600;font-size:14px;color:var(--text)">${esc(s.name)} (${esc(s.call_sign)})</div>
                <div class="text-3 text-xs">Sources linked: ${stationSources.length}</div>
              </div>

              ${stationSources.length > 0 ? `
                <div class="table-wrap">
                  <table style="font-size:12px">
                    <thead>
                      <tr>
                        <th>Priority</th>
                        <th>Source Type</th>
                        <th>Name</th>
                        <th>Endpoint / Config</th>
                        <th>Validation Code</th>
                        <th>Status</th>
                        <th>Last Verified (UTC)</th>
                      </tr>
                    </thead>
                    <tbody>
                      ${stationSources.map(src => {
                        let statusClass = 'badge-muted';
                        if (src.latest_validation_status === 'validated') statusClass = 'badge-success';
                        else if (src.latest_validation_status === 'failed') statusClass = 'badge-danger';
                        else if (src.latest_validation_status === 'unvalidated') statusClass = 'badge-warning';

                        const formattedConfig = src.base_url
                          ? `<a href="${esc(src.base_url)}" target="_blank" class="text-2" style="text-decoration:none">${esc(src.base_url.slice(0, 45))}... ↗</a>`
                          : '<span class="text-3">Manual Upload</span>';

                        return `
                          <tr>
                            <td><span class="pos-badge pos-n" style="width:20px;height:20px;font-size:10px">${src.priority}</span></td>
                            <td><span class="badge badge-info" style="font-size:9px">${esc(src.source_type)}</span></td>
                            <td style="font-weight:500">${esc(src.name)}</td>
                            <td>${formattedConfig}</td>
                            <td><code class="mono" style="font-size:10px">${esc(src.latest_validation_code || '—')}</code></td>
                            <td><span class="badge ${statusClass}">${esc(src.latest_validation_status || 'unvalidated')}</span></td>
                            <td class="text-3">${src.latest_validated_at ? fmtDateTime(src.latest_validated_at) : 'Never'}</td>
                          </tr>
                        `;
                      }).join('')}
                    </tbody>
                  </table>
                </div>
              ` : `
                <div class="text-3 text-sm" style="padding:10px 0">No sources configured in database for this station.</div>
              `}
            </div>
          `;
        }).join('')}
      </div>
    </div>
  `;
}
