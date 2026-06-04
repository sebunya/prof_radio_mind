/**
 * Operations page — read-only view of system operational state.
 *
 * Shows: environment, scheduler, collector flags, docs exposure,
 * admin auth, dedup, retention, and production guardrails.
 * No action buttons. All state is informational only.
 */

import { API } from '../api.js';
import { esc } from '../ui.js';

export async function init(container) {
  container.innerHTML = '<div class="loader-center"><div class="loader" role="status" aria-label="Loading"></div></div>';

  let ov = null;
  try {
    ov = await API.adminOverview();
  } catch (err) {
    container.innerHTML = `<div class="alert alert-danger">
      Unable to load operational state: ${esc(err.message)}
    </div>`;
    return;
  }

  container.innerHTML = `
    <!-- ── System Configuration ── -->
    <div class="ops-section">
      <div class="ops-section-title">System Configuration</div>
      <div class="ops-grid">
        ${opsCard('Environment', envValue(ov), envDesc(ov))}
        ${opsCard('Scheduler', ov.scheduler_enabled ? stateChip('Enabled', 'chip-warn') : stateChip('Disabled', 'chip-muted'), 'Automated collection jobs. All jobs are disabled by default.')}
        ${opsCard('API Docs', isDocsExposed(ov) ? stateChip('Exposed', isProd(ov) ? 'chip-warn' : 'chip-info') : stateChip('Hidden', 'chip-ok'), 'Interactive /docs endpoint. Hidden in production unless ENABLE_DOCS_IN_PRODUCTION=true.')}
        ${opsCard('Admin Auth', ov.admin_basic_auth_configured ? stateChip('Protected', 'chip-ok') : stateChip('Public', 'chip-info'), 'HTTP Basic Auth for the /admin console. Configured via ADMIN_BASIC_AUTH_USER and ADMIN_BASIC_AUTH_PASSWORD.')}
        ${opsCard('Deduplication', stateChip('Active', 'chip-ok'), 'Play event fingerprint dedup is always enabled. Duplicate events within the dedup window are suppressed.')}
        ${opsCard('Raw Payload Retention', retentionValue(ov), retentionDesc(ov))}
      </div>
    </div>

    <!-- ── Collector Flags ── -->
    <div class="ops-section">
      <div class="ops-section-title">Collector Flags</div>
      <div class="card">
        <div class="info-box">
          <p>All collectors are <strong>disabled by default</strong>. Enabling a collector requires configuration changes and a separate operations pass. No collectors can be enabled from this console.</p>
        </div>
        <table class="flag-table">
          <tbody>
            ${collectorRow('Capital FM UK',           ov.enable_capital_collector,       'ENABLE_CAPITAL_COLLECTOR')}
            ${collectorRow('Nova 96.9 FM',             ov.enable_nova_collector,           'ENABLE_NOVA_COLLECTOR')}
            ${collectorRow('KIIS FM 102.7',            ov.enable_kiis_collector,           'ENABLE_KIIS_COLLECTOR')}
            ${collectorRow('Nightly Reconciliation',   ov.enable_nightly_reconciliation,   'ENABLE_NIGHTLY_RECONCILIATION')}
          </tbody>
        </table>
      </div>
    </div>

    <!-- ── Production Guardrails ── -->
    <div class="ops-section">
      <div class="ops-section-title">Production Guardrails</div>
      ${guardrailBox('Collectors are disabled by default and must be validated before enabling. Validation requires live network access and human operator review. See VALIDATION_REGISTER.md.')}
      ${guardrailBox('The scheduler is disabled by default. Starting the scheduler without confirmed collector validation may result in silent data collection errors or wrong-station data.')}
      ${ov.raw_payload_retention_days > 0
        ? ''
        : guardrailBox('Raw payload retention is off (RAW_PAYLOAD_RETENTION_DAYS=0). Raw payloads are stored indefinitely. Use app/tools/prune_raw_payloads.py to prune manually when needed.')}
      ${!ov.admin_basic_auth_configured
        ? guardrailBox('The /admin console has no password protection. Set ADMIN_BASIC_AUTH_USER and ADMIN_BASIC_AUTH_PASSWORD in production to restrict access.')
        : ''}
      ${isDocsExposed(ov) && isProd(ov)
        ? guardrailBox('API docs are exposed in production. Set ENABLE_DOCS_IN_PRODUCTION=false or leave APP_ENV=production to hide /docs automatically.')
        : ''}
    </div>

    <!-- ── Safe Actions ── -->
    <div class="ops-section">
      <div class="ops-section-title">Operational Reference</div>
      <div class="card">
        <div class="card-header"><span class="card-title">What you can safely do from this console</span></div>
        <ul style="font-size:13px;color:var(--text2);line-height:2;padding-left:20px;margin:0">
          <li>Review pending items in the Review Queue</li>
          <li>Generate and download station reports</li>
          <li>Register or remove webhooks</li>
          <li>Backfill historical play data from CSV</li>
          <li>Ingest and view ARIA chart data</li>
          <li>Analyse and approve playlist rotation recommendations</li>
        </ul>
        <hr>
        <div class="card-header" style="margin-top:12px"><span class="card-title">What requires a separate operations pass</span></div>
        <ul style="font-size:13px;color:var(--text3);line-height:2;padding-left:20px;margin:0">
          <li>Enabling collectors (requires VAL-* validation first)</li>
          <li>Starting the scheduler</li>
          <li>Deploying changes to production</li>
          <li>Running collector dry-runs (<code class="mono">python -m app.tools.dry_run_capital</code>)</li>
          <li>Pruning raw payloads (<code class="mono">python -m app.tools.prune_raw_payloads</code>)</li>
          <li>Rolling back migrations</li>
          <li>Changing station UUIDs or seeder data</li>
        </ul>
      </div>
    </div>`;
}

function stateChip(label, cls) {
  return `<span class="status-chip ${cls}">${esc(label)}</span>`;
}

function opsCard(label, valueHtml, desc) {
  return `<div class="ops-card">
    <div class="ops-card-label">${esc(label)}</div>
    <div class="ops-card-value">${valueHtml}</div>
    <div class="ops-card-desc">${esc(desc)}</div>
  </div>`;
}

function isProd(ov) {
  return ov.app_env === 'production';
}

function isDocsExposed(ov) {
  return !isProd(ov) || ov.enable_docs_in_production;
}

function envValue(ov) {
  const label = ov.app_env || 'unknown';
  const cls   = isProd(ov)          ? 'env-badge env-prod' :
                label === 'staging' ? 'env-badge env-staging' : 'env-badge env-dev';
  return `<span class="${cls}" style="font-size:11px;padding:3px 8px">${esc(label.toUpperCase())}</span>`;
}

function envDesc(ov) {
  if (isProd(ov)) return 'Production environment. All safety defaults apply.';
  if (ov.app_env === 'staging') return 'Staging environment. Treat as production-like.';
  return 'Development environment. Docs are exposed and auth is optional.';
}

function retentionValue(ov) {
  if (ov.raw_payload_retention_days > 0) {
    return stateChip(`${ov.raw_payload_retention_days} days`, 'chip-info');
  }
  return stateChip('Off (0 days)', 'chip-muted');
}

function retentionDesc(ov) {
  if (ov.raw_payload_retention_days > 0) {
    return `Raw payloads older than ${ov.raw_payload_retention_days} days are pruned by the retention job. Configured via RAW_PAYLOAD_RETENTION_DAYS.`;
  }
  return 'Retention disabled. Raw payloads accumulate until manually pruned. Set RAW_PAYLOAD_RETENTION_DAYS > 0 to enable automatic pruning.';
}

function collectorRow(name, enabled, envVar) {
  const chip = enabled
    ? `<span class="status-chip chip-warn">Enabled</span>`
    : `<span class="status-chip chip-muted">Disabled</span>`;
  return `<tr>
    <td class="flag-label">${esc(name)}</td>
    <td style="text-align:right;padding-right:0">${chip}</td>
    <td style="width:220px;padding-left:12px">
      <code class="mono">${esc(envVar)}</code>
    </td>
  </tr>`;
}

function guardrailBox(text) {
  return `<div class="guardrail-box">
    <p><span class="guardrail-box-icon">⚠</span>${esc(text)}</p>
  </div>`;
}
