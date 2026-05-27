import { API } from '../api.js';
import { toast, esc } from '../ui.js';

let _stations = [];
let _selectedFile = null;
let _container;

export async function init(container, actions) {
  _container = container;
  actions.innerHTML = '';
  container.innerHTML = '<div class="loader-center"><div class="loader"></div></div>';

  try { _stations = await API.stations(); } catch { _stations = []; }
  renderPage();
}

function today() {
  return new Date().toISOString().split('T')[0];
}

function renderPage() {
  _container.innerHTML = `
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;align-items:start">

      <!-- ── Left: Form ── -->
      <div>
        <div class="card mb-5">
          <div class="card-header"><span class="card-title">Import Historical Plays</span></div>
          <div class="alert alert-info mb-4" style="font-size:12px">
            CSV must have columns: <code class="mono">artist</code>, <code class="mono">title</code>,
            <code class="mono">played_at</code>. Max 10 MB. Duplicate fingerprints within the same
            import are skipped.
          </div>

          <div class="form-group">
            <label>Station</label>
            <select id="bf-station">
              <option value="">— Select station —</option>
              ${_stations.map(s => `<option value="${s.id}">${esc(s.call_sign)} — ${esc(s.name)}</option>`).join('')}
            </select>
          </div>

          <div class="form-group">
            <label>Broadcast Date</label>
            <input type="date" id="bf-date" value="${today()}">
            <div class="form-hint">The date these plays were broadcast</div>
          </div>

          <div class="form-group">
            <label>CSV File</label>
            <div class="upload-zone" id="drop-zone" onclick="document.getElementById('bf-file').click()">
              <input type="file" id="bf-file" accept=".csv,text/csv" onchange="window._backfillPage.onFileChange(event)">
              <div class="upload-icon">📄</div>
              <div class="upload-label" id="upload-label">Click to browse or drag & drop</div>
              <div class="upload-hint">CSV files only · max 10 MB</div>
            </div>
          </div>

          <button class="btn btn-primary w-full" id="bf-btn" onclick="window._backfillPage.submit()">
            Import Historical Plays
          </button>
        </div>

        <!-- ── CSV format guide ── -->
        <div class="card">
          <div class="card-header"><span class="card-title">CSV Format</span></div>
          <table>
            <thead><tr><th>Column</th><th>Required</th><th>Format</th></tr></thead>
            <tbody>
              <tr>
                <td><code class="mono">artist</code></td>
                <td><span class="badge badge-danger">Yes</span></td>
                <td class="text-2 text-sm">Any string</td>
              </tr>
              <tr>
                <td><code class="mono">title</code></td>
                <td><span class="badge badge-danger">Yes</span></td>
                <td class="text-2 text-sm">Any string</td>
              </tr>
              <tr>
                <td><code class="mono">played_at</code></td>
                <td><span class="badge badge-danger">Yes</span></td>
                <td class="text-2 text-sm">
                  <code class="mono">HH:MM:SS</code> or ISO 8601<br>
                  <span class="text-3">e.g. 14:30:00 or 2026-05-24T14:30:00</span>
                </td>
              </tr>
            </tbody>
          </table>
          <div class="mt-4" style="background:var(--bg3);border-radius:6px;padding:12px;font-family:var(--mono);font-size:11px;color:var(--text2)">
            artist,title,played_at<br>
            Taylor Swift,Shake It Off,07:30:00<br>
            The Weeknd,Blinding Lights,07:33:00<br>
            Dua Lipa,Levitating,07:37:00
          </div>
        </div>
      </div>

      <!-- ── Right: Results ── -->
      <div id="bf-results">
        <div class="card">
          <div class="card-header"><span class="card-title">Results</span></div>
          <div class="empty-state" style="padding:32px">
            <div class="empty-icon">📥</div>
            <div class="empty-title">No import yet</div>
            <div class="empty-desc">Select a station, date and CSV file, then click Import.</div>
          </div>
        </div>
      </div>
    </div>`;

  // Wire up drag & drop
  const zone = document.getElementById('drop-zone');
  if (zone) {
    zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('dragover'); });
    zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
    zone.addEventListener('drop', e => {
      e.preventDefault();
      zone.classList.remove('dragover');
      const file = e.dataTransfer.files[0];
      if (file) setFile(file);
    });
  }
}

function onFileChange(event) {
  const file = event.target.files?.[0];
  if (file) setFile(file);
}

function setFile(file) {
  _selectedFile = file;
  const label = document.getElementById('upload-label');
  if (label) {
    const kb = (file.size / 1024).toFixed(1);
    label.textContent = `${file.name} (${kb} KB)`;
    label.style.color = 'var(--accent)';
  }
  if (file.size > 10 * 1024 * 1024) {
    toast('warning', 'File may be too large', `${(file.size/1024/1024).toFixed(1)} MB exceeds the 10 MB limit`);
  }
}

async function submit() {
  const stationId = document.getElementById('bf-station')?.value;
  const date      = document.getElementById('bf-date')?.value;

  if (!stationId)     { toast('warning', 'Select a station'); return; }
  if (!date)          { toast('warning', 'Select a broadcast date'); return; }
  if (!_selectedFile) { toast('warning', 'Choose a CSV file'); return; }
  if (_selectedFile.size > 10 * 1024 * 1024) {
    toast('error', 'File too large', 'Maximum size is 10 MB');
    return;
  }

  const btn = document.getElementById('bf-btn');
  btn.disabled = true;
  btn.innerHTML = '<span class="loader loader-sm" style="display:inline-block;margin-right:6px"></span>Importing…';

  const fd = new FormData();
  fd.append('file', _selectedFile);

  try {
    const result = await API.backfill(stationId, date, fd);
    renderResults(result);
    toast('success', 'Import complete', `${result.rows_accepted} rows accepted`);
  } catch (err) {
    toast('error', 'Import failed', err.message);
    document.getElementById('bf-results').innerHTML = `
      <div class="card">
        <div class="card-header"><span class="card-title">Import Failed</span></div>
        <div class="alert alert-danger">${esc(err.message)}</div>
      </div>`;
  } finally {
    btn.disabled = false;
    btn.textContent = 'Import Historical Plays';
  }
}

function renderResults(r) {
  const acceptPct = r.rows_submitted > 0 ? Math.round(r.rows_accepted / r.rows_submitted * 100) : 0;

  document.getElementById('bf-results').innerHTML = `
    <div class="card">
      <div class="card-header">
        <span class="card-title">Import Results</span>
        <span class="badge badge-success">Complete</span>
      </div>

      <div class="result-grid mb-5">
        <div class="result-card">
          <div class="result-num">${r.rows_submitted}</div>
          <div class="result-lbl">Submitted</div>
        </div>
        <div class="result-card" style="background:rgba(16,185,129,.12)">
          <div class="result-num" style="color:var(--success)">${r.rows_accepted}</div>
          <div class="result-lbl">Accepted</div>
        </div>
        <div class="result-card"${r.rows_rejected > 0 ? ' style="background:rgba(239,68,68,.12)"' : ''}>
          <div class="result-num"${r.rows_rejected > 0 ? ' style="color:var(--danger)"' : ''}>${r.rows_rejected}</div>
          <div class="result-lbl">Rejected</div>
        </div>
      </div>

      <!-- Acceptance bar -->
      <div class="mb-4">
        <div class="flex items-c j-between mb-4" style="margin-bottom:6px">
          <span class="text-sm text-2">Acceptance rate</span>
          <span class="text-sm font-500">${acceptPct}%</span>
        </div>
        <div class="conf-wrap">
          <div class="conf-bar ${acceptPct >= 90 ? 'conf-high' : acceptPct >= 60 ? 'conf-medium' : 'conf-low'}"
               style="width:${acceptPct}%"></div>
        </div>
      </div>

      <div class="flex gap-2 mb-4">
        <div style="background:var(--bg3);border-radius:6px;padding:8px 14px;flex:1;text-align:center">
          <div class="text-3 text-xs">Broadcast Date</div>
          <div class="text-sm font-500 mt-2">${esc(r.broadcast_date)}</div>
        </div>
        <div style="background:var(--bg3);border-radius:6px;padding:8px 14px;flex:1;text-align:center">
          <div class="text-3 text-xs">Review Item</div>
          <div class="text-xs mono mt-2 text-2" title="${esc(r.review_item_id)}">${r.review_item_id?.slice(0,8)}…</div>
        </div>
      </div>

      ${r.rejection_reasons?.length ? `
        <div>
          <div class="text-xs font-500 text-2 mb-4" style="margin-bottom:6px">Rejection Details</div>
          <div style="background:var(--bg);border-radius:6px;padding:10px;max-height:200px;overflow-y:auto">
            ${r.rejection_reasons.map(reason => `
              <div style="font-family:var(--mono);font-size:11px;color:var(--danger);padding:2px 0;border-bottom:1px solid var(--border2)">${esc(reason)}</div>
            `).join('')}
          </div>
        </div>` : '<div class="alert alert-success" style="font-size:12px">✓ No rejection reasons — all rows accepted cleanly.</div>'}
    </div>`;
}

window._backfillPage = { onFileChange, submit };
