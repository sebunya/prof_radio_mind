import { API } from '../api.js';
import { toast, esc, openModal, closeModal, setBtnLoading } from '../ui.js';

let _recipients = [];
let _container;
let _editId = null;

export async function init(container, actions) {
  _container = container;
  actions.innerHTML = `
    <button class="btn btn-primary btn-sm" onclick="window._emailPage.openAddModal()">
      + Add Recipient
    </button>`;
  container.innerHTML = '<div class="loader-center"><div class="loader"></div></div>';

  await _refresh();
}

// ── Data load ─────────────────────────────────────────────────────────────────

async function _refresh() {
  try {
    const [recs, logs] = await Promise.all([
      API.emailRecipients(),
      API.emailLogs(),
    ]);
    _recipients = recs;
    _render(recs, logs);
  } catch (err) {
    _container.innerHTML = `<div class="alert alert-danger">
      <strong>Failed to load email report data:</strong> ${esc(err.message)}
      <button class="btn btn-ghost btn-sm" style="margin-left:12px"
              onclick="window._emailPage.reload()">Retry</button>
    </div>`;
  }
}

// ── Main render ───────────────────────────────────────────────────────────────

function _render(recipients, logs) {
  const active  = recipients.filter(r => r.is_active);
  const hasRecs = recipients.length > 0;

  _container.innerHTML = `
    <!-- ── Schedule overview ── -->
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:20px">
      ${_scheduleCard('Daily', '08:00 AEST', 'Plays from yesterday per station,<br>top songs & new debuts', 'badge-info')}
      ${_scheduleCard('Weekly', 'Tue 08:00 AEST', 'Full week rankings, trend analysis,<br>ARIA chart matches', 'badge-accent')}
      ${_scheduleCard('Monthly', '2nd 08:00 AEST', 'Month-over-month comparison,<br>music intelligence insights', 'badge-success')}
    </div>

    <!-- ── Recipients ── -->
    <div class="card mb-5">
      <div class="card-header">
        <span class="card-title">Recipients
          <span class="badge badge-muted" style="margin-left:6px">${active.length} active</span>
        </span>
        <button class="btn btn-primary btn-sm" onclick="window._emailPage.openAddModal()">
          + Add Recipient
        </button>
      </div>

      ${!hasRecs ? _emptyRecipients() : `
      <div class="table-wrap">
        <table>
          <thead><tr>
            <th>Name</th><th>Email</th><th>Frequencies</th><th>Status</th><th>Actions</th>
          </tr></thead>
          <tbody>
            ${recipients.map(r => _recipientRow(r)).join('')}
          </tbody>
        </table>
      </div>`}
    </div>

    <!-- ── Send now ── -->
    <div class="card mb-5">
      <div class="card-header"><span class="card-title">Send On-Demand</span></div>
      <p class="text-2 text-sm mb-4">
        Trigger an immediate report for all subscribed recipients.
        If SMTP is not configured the email is logged in dry-run mode.
      </p>

      <!-- Scheduled frequency quick-send -->
      <div style="font-size:12px;font-weight:600;color:var(--text3);
                  text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px">
        Scheduled Periods
      </div>
      <div class="flex gap-2 mb-4" style="flex-wrap:wrap">
        <button class="btn btn-secondary" id="send-daily-btn"
                onclick="window._emailPage.sendNow('daily')">
          📅 Send Daily Now
        </button>
        <button class="btn btn-secondary" id="send-weekly-btn"
                onclick="window._emailPage.sendNow('weekly')">
          📊 Send Weekly Now
        </button>
        <button class="btn btn-secondary" id="send-monthly-btn"
                onclick="window._emailPage.sendNow('monthly')">
          📈 Send Monthly Now
        </button>
        <a class="btn btn-ghost" href="/email-reports/preview/daily" target="_blank">
          👁 Preview Daily
        </a>
        <a class="btn btn-ghost" href="/email-reports/preview/weekly" target="_blank">
          👁 Preview Weekly
        </a>
        <a class="btn btn-ghost" href="/email-reports/preview/monthly" target="_blank">
          👁 Preview Monthly
        </a>
      </div>

      <!-- Custom date range -->
      <div style="border-top:1px solid var(--border);padding-top:16px">
        <div style="font-size:12px;font-weight:600;color:var(--text3);
                    text-transform:uppercase;letter-spacing:.5px;margin-bottom:10px">
          Custom Date Range
        </div>
        <p class="text-2 text-sm mb-3" style="margin-top:0">
          Send (or preview) a report for any arbitrary date window.
          Sent to <em>all active recipients</em> regardless of their
          frequency subscriptions. Both dates are inclusive.
        </p>
        <div class="flex gap-3" style="align-items:flex-end;flex-wrap:wrap">
          <div class="form-group" style="margin:0;flex:1;min-width:150px">
            <label style="font-size:12px;color:var(--text2);margin-bottom:4px;display:block">
              Start Date
            </label>
            <input type="date" id="custom-start-date" class="input"
                   style="width:100%;box-sizing:border-box"
                   max="${new Date().toISOString().slice(0,10)}">
          </div>
          <div class="form-group" style="margin:0;flex:1;min-width:150px">
            <label style="font-size:12px;color:var(--text2);margin-bottom:4px;display:block">
              End Date
            </label>
            <input type="date" id="custom-end-date" class="input"
                   style="width:100%;box-sizing:border-box"
                   max="${new Date().toISOString().slice(0,10)}">
          </div>
          <button class="btn btn-secondary" id="send-custom-btn"
                  onclick="window._emailPage.sendCustom()">
            📊 Send Custom Range
          </button>
          <button class="btn btn-ghost" id="preview-custom-btn"
                  onclick="window._emailPage.previewCustom()">
            👁 Preview Custom
          </button>
        </div>
        <p class="text-3 text-xs" style="margin-top:8px;font-size:11px">
          💡 <strong>Period definitions</strong> — Daily: yesterday (1 day) ·
          Weekly: rolling 7-day window · Monthly: rolling 30-day window
        </p>
      </div>
    </div>

    <!-- ── Send log ── -->
    <div class="card">
      <div class="card-header">
        <span class="card-title">Send Log</span>
        <button class="btn btn-ghost btn-sm" onclick="window._emailPage.reload()">↻ Refresh</button>
      </div>
      ${!logs.length ? `
        <div class="empty-state" style="padding:24px">
          <div class="empty-icon">📬</div>
          <div class="empty-title">No emails sent yet</div>
          <div class="empty-desc">Logs will appear here after the first send or scheduled run.</div>
        </div>` : `
      <div class="table-wrap">
        <table>
          <thead><tr>
            <th>Sent</th><th>Frequency</th><th>Recipients</th>
            <th>Plays</th><th>Status</th>
          </tr></thead>
          <tbody>
            ${logs.map(l => _logRow(l)).join('')}
          </tbody>
        </table>
      </div>`}
    </div>

    ${_recipientModal()}`;
}

// ── Small components ──────────────────────────────────────────────────────────

function _scheduleCard(label, time, desc, badgeClass) {
  return `
    <div style="background:var(--bg3);border-radius:8px;padding:16px;text-align:center">
      <span class="badge ${badgeClass}" style="margin-bottom:8px">${esc(label)}</span>
      <div style="font-size:13px;font-weight:600;color:var(--text1);margin-bottom:4px">
        ${esc(time)}</div>
      <div style="font-size:11px;color:var(--text3);line-height:1.5">${desc}</div>
    </div>`;
}

function _recipientRow(r) {
  const freqs = (r.frequencies || []).map(f =>
    `<span class="badge badge-${f === 'daily' ? 'info' : f === 'weekly' ? 'accent' : 'success'}"
            style="font-size:10px;margin-right:4px">${esc(f)}</span>`
  ).join('');

  const statusBadge = r.is_active
    ? '<span class="badge badge-success" style="font-size:10px">Active</span>'
    : '<span class="badge badge-muted" style="font-size:10px">Inactive</span>';

  return `<tr>
    <td style="font-weight:500">${esc(r.name)}</td>
    <td class="mono text-sm text-2">${esc(r.email)}</td>
    <td>${freqs || '—'}</td>
    <td>${statusBadge}</td>
    <td>
      <div class="flex gap-1">
        <button class="btn btn-ghost btn-sm"
                onclick="window._emailPage.openEditModal('${esc(r.id)}')">Edit</button>
        <button class="btn btn-ghost btn-sm"
                style="color:var(--danger)"
                onclick="window._emailPage.toggleActive('${esc(r.id)}', ${!r.is_active})">
          ${r.is_active ? 'Deactivate' : 'Reactivate'}
        </button>
      </div>
    </td>
  </tr>`;
}

function _logRow(l) {
  const statusColor = l.status === 'sent' ? 'success'
    : l.status === 'dry_run' ? 'info' : 'danger';
  const freqColor = l.frequency === 'daily' ? 'info'
    : l.frequency === 'weekly' ? 'accent'
    : l.frequency === 'monthly' ? 'success'
    : 'warning';  // custom / manual / on-demand
  const dt = new Date(l.sent_at);
  const dtStr = dt.toLocaleDateString('en-AU', { day: 'numeric', month: 'short', year: 'numeric' })
    + ' ' + dt.toLocaleTimeString('en-AU', { hour: '2-digit', minute: '2-digit' });

  return `<tr>
    <td class="text-sm text-2">${esc(dtStr)}</td>
    <td><span class="badge badge-${freqColor}" style="font-size:10px">${esc(l.frequency)}</span></td>
    <td class="text-sm text-2" style="max-width:200px;overflow:hidden;text-overflow:ellipsis;
        white-space:nowrap" title="${esc(l.recipients)}">${esc(l.recipients)}</td>
    <td class="text-sm">${l.total_plays != null ? l.total_plays.toLocaleString() : '—'}</td>
    <td>
      <span class="badge badge-${statusColor}" style="font-size:10px">${esc(l.status)}</span>
      ${l.error_message ? `<div class="text-xs text-danger mt-2" style="font-size:11px;
          max-width:180px" title="${esc(l.error_message)}">${esc(l.error_message.slice(0, 60))}…</div>` : ''}
    </td>
  </tr>`;
}

function _emptyRecipients() {
  return `
    <div class="empty-state" style="padding:32px">
      <div class="empty-icon">📧</div>
      <div class="empty-title">No recipients yet</div>
      <div class="empty-desc">
        Add at least one recipient to start receiving scheduled email reports.
      </div>
      <button class="btn btn-primary btn-sm" style="margin-top:12px"
              onclick="window._emailPage.openAddModal()">
        + Add First Recipient
      </button>
    </div>`;
}

function _recipientModal() {
  return `
    <template id="email-modal-tpl">
      <div class="form-group">
        <label for="em-name">Name</label>
        <input type="text" id="em-name" placeholder="Joel Isabirye" maxlength="255">
      </div>
      <div class="form-group">
        <label for="em-email">Email Address</label>
        <input type="email" id="em-email" placeholder="name@example.com" maxlength="512">
      </div>
      <div class="form-group">
        <label>Report Frequencies</label>
        <div class="flex gap-3" style="margin-top:6px;flex-wrap:wrap">
          <label style="display:flex;align-items:center;gap:6px;cursor:pointer">
            <input type="checkbox" id="em-daily" value="daily">
            <span class="badge badge-info">Daily</span>
          </label>
          <label style="display:flex;align-items:center;gap:6px;cursor:pointer">
            <input type="checkbox" id="em-weekly" value="weekly">
            <span class="badge badge-accent">Weekly</span>
          </label>
          <label style="display:flex;align-items:center;gap:6px;cursor:pointer">
            <input type="checkbox" id="em-monthly" value="monthly">
            <span class="badge badge-success">Monthly</span>
          </label>
        </div>
        <div class="form-hint">Select at least one frequency</div>
      </div>
    </template>`;
}

// ── Modal actions ─────────────────────────────────────────────────────────────

function openAddModal() {
  _editId = null;
  openModal({
    title: 'Add Email Recipient',
    size: 'sm',
    bodyHtml: _modalBodyHtml(),
    primaryLabel: 'Add Recipient',
    onConfirm: _saveRecipient,
  });
}

function openEditModal(id) {
  _editId = id;
  const rec = _recipients.find(r => r.id === id);
  if (!rec) return;

  openModal({
    title: 'Edit Recipient',
    size: 'sm',
    bodyHtml: _modalBodyHtml(rec),
    primaryLabel: 'Save Changes',
    onConfirm: _saveRecipient,
  });
}

function _modalBodyHtml(rec = null) {
  const name  = rec ? esc(rec.name) : '';
  const email = rec ? esc(rec.email) : '';
  const freqs = rec ? (rec.frequencies || []) : [];

  return `
    <div class="form-group">
      <label for="em-name">Name</label>
      <input type="text" id="em-name" value="${name}" placeholder="Joel Isabirye" maxlength="255">
    </div>
    <div class="form-group">
      <label for="em-email">Email Address</label>
      <input type="email" id="em-email" value="${email}" placeholder="name@example.com">
    </div>
    <div class="form-group">
      <label>Report Frequencies</label>
      <div class="flex gap-3" style="margin-top:6px;flex-wrap:wrap">
        <label style="display:flex;align-items:center;gap:6px;cursor:pointer">
          <input type="checkbox" id="em-daily" value="daily" ${freqs.includes('daily') ? 'checked' : ''}>
          <span class="badge badge-info">Daily</span>
        </label>
        <label style="display:flex;align-items:center;gap:6px;cursor:pointer">
          <input type="checkbox" id="em-weekly" value="weekly" ${freqs.includes('weekly') ? 'checked' : ''}>
          <span class="badge badge-accent">Weekly</span>
        </label>
        <label style="display:flex;align-items:center;gap:6px;cursor:pointer">
          <input type="checkbox" id="em-monthly" value="monthly" ${freqs.includes('monthly') ? 'checked' : ''}>
          <span class="badge badge-success">Monthly</span>
        </label>
      </div>
      <div class="form-hint">Select at least one frequency</div>
    </div>`;
}

async function _saveRecipient() {
  const name  = document.getElementById('em-name')?.value?.trim();
  const email = document.getElementById('em-email')?.value?.trim();
  const freqs = ['daily', 'weekly', 'monthly'].filter(
    f => document.getElementById(`em-${f}`)?.checked
  );

  if (!name)         { toast('warning', 'Enter a name'); return; }
  if (!email)        { toast('warning', 'Enter an email address'); return; }
  if (!freqs.length) { toast('warning', 'Select at least one frequency'); return; }

  try {
    if (_editId) {
      await API.updateEmailRecipient(_editId, { name, email, frequencies: freqs });
      toast('success', 'Recipient updated');
    } else {
      await API.addEmailRecipient({ name, email, frequencies: freqs });
      toast('success', 'Recipient added', `${name} will receive ${freqs.join(', ')} reports`);
    }
    closeModal();
    await _refresh();
  } catch (err) {
    toast('error', _editId ? 'Update failed' : 'Add failed', err.message);
  }
}

async function toggleActive(id, makeActive) {
  try {
    await API.updateEmailRecipient(id, { is_active: makeActive });
    toast('success', makeActive ? 'Recipient reactivated' : 'Recipient deactivated');
    await _refresh();
  } catch (err) {
    toast('error', 'Update failed', err.message);
  }
}

// ── Send now ──────────────────────────────────────────────────────────────────

async function sendNow(frequency) {
  const btn = document.getElementById(`send-${frequency}-btn`);
  setBtnLoading(btn, true, 'Sending…');
  try {
    const result = await API.sendEmailNow(frequency);
    if (result.dry_run) {
      toast('info', 'Dry run complete',
        `${result.total_plays} plays, ${result.recipients_count} recipient(s) — SMTP not configured`);
    } else {
      toast('success', `${frequency.charAt(0).toUpperCase() + frequency.slice(1)} report sent`,
        `Sent to ${result.sent_count}/${result.recipients_count} recipient(s)`);
    }
    await _refresh();  // refresh log
  } catch (err) {
    toast('error', 'Send failed', err.message);
  } finally {
    setBtnLoading(btn, false);
  }
}

async function sendCustom() {
  const startDate = document.getElementById('custom-start-date')?.value;
  const endDate   = document.getElementById('custom-end-date')?.value;

  if (!startDate || !endDate) {
    toast('warning', 'Select a date range', 'Choose both a start and end date first');
    return;
  }
  if (startDate > endDate) {
    toast('warning', 'Invalid range', 'Start date must be on or before end date');
    return;
  }

  const btn = document.getElementById('send-custom-btn');
  setBtnLoading(btn, true, 'Sending…');
  try {
    const result = await API.sendEmailNow('custom', startDate, endDate);
    if (result.dry_run) {
      toast('info', 'Dry run complete',
        `${result.total_plays} plays, ${result.recipients_count} recipient(s) — SMTP not configured`);
    } else {
      toast('success', 'Custom report sent',
        `Sent to ${result.sent_count}/${result.recipients_count} recipient(s)`);
    }
    await _refresh();
  } catch (err) {
    toast('error', 'Send failed', err.message);
  } finally {
    setBtnLoading(btn, false);
  }
}

function previewCustom() {
  const startDate = document.getElementById('custom-start-date')?.value;
  const endDate   = document.getElementById('custom-end-date')?.value;

  if (!startDate || !endDate) {
    toast('warning', 'Select a date range', 'Choose both a start and end date before previewing');
    return;
  }
  if (startDate > endDate) {
    toast('warning', 'Invalid range', 'Start date must be on or before end date');
    return;
  }

  window.open(
    `/email-reports/preview/custom?start_date=${startDate}&end_date=${endDate}`,
    '_blank',
  );
}

function reload() {
  _container.innerHTML = '<div class="loader-center"><div class="loader"></div></div>';
  _refresh();
}

window._emailPage = {
  openAddModal, openEditModal, toggleActive,
  sendNow, sendCustom, previewCustom,
  reload,
};
