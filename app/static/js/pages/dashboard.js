import { API } from '../api.js';
import { fmtRelative, badge, esc } from '../ui.js';

export async function init(container) {
  container.innerHTML = '<div class="loader-center"><div class="loader"></div></div>';

  const [health, stations, items, hooks] = await Promise.allSettled([
    API.health(), API.stations(), API.reviewItems(), API.webhooks(),
  ]);

  const h  = health.status    === 'fulfilled' ? health.value    : {};
  const sl = stations.status  === 'fulfilled' ? stations.value  : [];
  const il = items.status     === 'fulfilled' ? items.value     : [];
  const hl = hooks.status     === 'fulfilled' ? hooks.value     : [];

  const pending = il.filter(i => i.status === 'pending').length;
  const apiOk   = h.status === 'ok';

  // Aggregate counts
  const byStatus = { pending: 0, reviewed: 0, dismissed: 0, escalated: 0 };
  const byType   = {};
  il.forEach(i => {
    byStatus[i.status] = (byStatus[i.status] || 0) + 1;
    byType[i.item_type] = (byType[i.item_type] || 0) + 1;
  });

  container.innerHTML = `
    <!-- ── Stats ── -->
    <div class="stats-grid mb-5">
      <div class="stat-card">
        <div class="stat-label">Active Stations</div>
        <div class="stat-value accent">${sl.length}</div>
        <div class="stat-meta">Radio stations monitored</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Pending Reviews</div>
        <div class="stat-value ${pending > 0 ? 'warning' : 'success'}">${pending}</div>
        <div class="stat-meta">${il.length} total items in queue</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Active Webhooks</div>
        <div class="stat-value">${hl.length}</div>
        <div class="stat-meta">Push subscriptions registered</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">System Status</div>
        <div class="stat-value ${apiOk ? 'success' : 'danger'}" style="font-size:20px;padding-top:6px">
          <span class="dot ${apiOk ? 'dot-ok' : 'dot-error'}"></span>
          ${apiOk ? 'Operational' : 'Degraded'}
        </div>
        <div class="stat-meta">
          Scheduler: ${h.scheduler_running ? '▶ Running' : '■ Stopped'}
          &nbsp;·&nbsp; v${h.version || '?'}
        </div>
      </div>
    </div>

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

    <!-- ── Station list ── -->
    <div class="card mb-5">
      <div class="card-header">
        <span class="card-title">Monitored Stations</span>
        <a href="#/stations" class="btn btn-ghost btn-sm">View all →</a>
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr>
            <th>Call Sign</th><th>Name</th><th>Frequency</th><th>City</th>
          </tr></thead>
          <tbody>${sl.slice(0,5).map(s => `
            <tr>
              <td><span class="badge badge-accent">${esc(s.call_sign)}</span></td>
              <td>${esc(s.name)}</td>
              <td>${esc(s.frequency || '—')}</td>
              <td class="text-2">${esc(s.city || '—')}</td>
            </tr>`).join('') || `<tr><td colspan="4" class="td-empty">No stations</td></tr>`}
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
          <tbody>${il.slice(0,8).map(item => `
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
