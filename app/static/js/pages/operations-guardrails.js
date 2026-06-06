import { API } from '../api.js';
import { esc } from '../ui.js';

export async function init(container, actions) {
  actions.innerHTML = '';
  container.innerHTML = '<div class="loader-center"><div class="loader"></div></div>';

  let ops = {};
  try {
    ops = await API.adminOperations();
  } catch (err) {
    container.innerHTML = `<div class="alert alert-danger">Failed to load operations config: ${esc(err.message)}</div>`;
    return;
  }

  container.innerHTML = `
    <!-- ── Safety Toggles and Environmental Variables ── -->
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:20px;margin-bottom:20px">
      
      <!-- Gated Airplay Settings -->
      <div class="card">
        <div class="card-header">
          <span class="card-title">Airplay Collector Controls (Read-Only)</span>
        </div>
        <div style="display:flex;flex-direction:column;gap:10px;font-size:13px">
          <div style="display:flex;justify-content:space-between;border-bottom:1px solid var(--border2);padding-bottom:6px">
            <span class="text-2">Global Scheduler Daemon</span>
            <span class="badge ${ops.scheduler_enabled ? 'badge-success' : 'badge-muted'}">
              ${ops.scheduler_enabled ? 'ENABLED' : 'DISABLED'}
            </span>
          </div>
          <div style="display:flex;justify-content:space-between;border-bottom:1px solid var(--border2);padding-bottom:6px">
            <span class="text-2">Nova 96.9 (Radiowave)</span>
            <span class="badge ${ops.enable_nova_collector ? 'badge-success' : 'badge-muted'}">
              ${ops.enable_nova_collector ? 'ENABLED' : 'DISABLED'}
            </span>
          </div>
          <div style="display:flex;justify-content:space-between;border-bottom:1px solid var(--border2);padding-bottom:6px">
            <span class="text-2">Nova 96.9 (Radoxo)</span>
            <span class="badge ${ops.enable_nova_radoxo_collector ? 'badge-success' : 'badge-muted'}">
              ${ops.enable_nova_radoxo_collector ? 'ENABLED' : 'DISABLED'}
            </span>
          </div>
          <div style="display:flex;justify-content:space-between;border-bottom:1px solid var(--border2);padding-bottom:6px">
            <span class="text-2">Nova 96.9 (Radio Australia)</span>
            <span class="badge ${ops.enable_nova_radio_australia_collector ? 'badge-success' : 'badge-muted'}">
              ${ops.enable_nova_radio_australia_collector ? 'ENABLED' : 'DISABLED'}
            </span>
          </div>
          <div style="display:flex;justify-content:space-between;border-bottom:1px solid var(--border2);padding-bottom:6px">
            <span class="text-2">Capital FM UK (Online Radio Box)</span>
            <span class="badge ${ops.enable_capital_collector ? 'badge-success' : 'badge-muted'}">
              ${ops.enable_capital_collector ? 'ENABLED' : 'DISABLED'}
            </span>
          </div>
          <div style="display:flex;justify-content:space-between;border-bottom:1px solid var(--border2);padding-bottom:6px">
            <span class="text-2">Capital FM UK (UK Radio Live)</span>
            <span class="badge ${ops.enable_capital_ukradiolive_collector ? 'badge-success' : 'badge-muted'}">
              ${ops.enable_capital_ukradiolive_collector ? 'ENABLED' : 'DISABLED'}
            </span>
          </div>
          <div style="display:flex;justify-content:space-between;border-bottom:1px solid var(--border2);padding-bottom:6px">
            <span class="text-2">KIIS-FM 102.7 (iHeart Web)</span>
            <span class="badge ${ops.enable_kiis_iheart_web_collector ? 'badge-success' : 'badge-muted'}">
              ${ops.enable_kiis_iheart_web_collector ? 'ENABLED' : 'DISABLED'}
            </span>
          </div>
          <div style="display:flex;justify-content:space-between;border-bottom:1px solid var(--border2);padding-bottom:6px">
            <span class="text-2">KIIS-FM 102.7 (Radiowave)</span>
            <span class="badge ${ops.enable_kiis_radiowave_collector ? 'badge-success' : 'badge-muted'}">
              ${ops.enable_kiis_radiowave_collector ? 'ENABLED' : 'DISABLED'}
            </span>
          </div>
          <div style="display:flex;justify-content:space-between;border-bottom:1px solid var(--border2);padding-bottom:6px">
            <span class="text-2">Nightly Reconciliation</span>
            <span class="badge ${ops.enable_nightly_reconciliation ? 'badge-success' : 'badge-muted'}">
              ${ops.enable_nightly_reconciliation ? 'ENABLED' : 'DISABLED'}
            </span>
          </div>
          <div style="display:flex;justify-content:space-between;border-bottom:1px solid var(--border2);padding-bottom:6px">
            <span class="text-2">Nightly Report Generation</span>
            <span class="badge ${ops.enable_nightly_report_generation ? 'badge-success' : 'badge-muted'}">
              ${ops.enable_nightly_report_generation ? 'ENABLED' : 'DISABLED'}
            </span>
          </div>
        </div>
      </div>

      <!-- Infrastructure Config -->
      <div class="card">
        <div class="card-header">
          <span class="card-title">System Infrastructure Configurations</span>
        </div>
        <div style="display:flex;flex-direction:column;gap:10px;font-size:13px">
          <div style="display:flex;justify-content:space-between;border-bottom:1px solid var(--border2);padding-bottom:6px">
            <span class="text-2">Environment Profile</span>
            <span class="badge ${ops.app_env === 'production' ? 'badge-danger' : 'badge-accent'}">${esc(ops.app_env.toUpperCase())}</span>
          </div>
          <div style="display:flex;justify-content:space-between;border-bottom:1px solid var(--border2);padding-bottom:6px">
            <span class="text-2">Database Schema Migration</span>
            <span class="mono" style="font-size:11px">${esc(ops.db_migration_version)} (c4e2a1f9b8d7)</span>
          </div>
          <div style="display:flex;justify-content:space-between;border-bottom:1px solid var(--border2);padding-bottom:6px">
            <span class="text-2">Raw Payload Retention</span>
            <span style="font-weight:600">
              ${ops.raw_payload_retention_days > 0 ? `${ops.raw_payload_retention_days} Days` : 'Off (Keep Forever)'}
            </span>
          </div>
          <div style="display:flex;justify-content:space-between;border-bottom:1px solid var(--border2);padding-bottom:6px">
            <span class="text-2">Interactive API Docs Gating</span>
            <span class="badge ${ops.enable_docs_in_production ? 'badge-success' : 'badge-muted'}">
              ${ops.enable_docs_in_production ? 'EXPOSED' : 'HIDDEN IN PROD'}
            </span>
          </div>
          <div style="display:flex;justify-content:space-between;border-bottom:1px solid var(--border2);padding-bottom:6px">
            <span class="text-2">Console HTTP Basic Auth</span>
            <span class="badge ${ops.admin_basic_auth_configured ? 'badge-success' : 'badge-warning'}">
              ${ops.admin_basic_auth_configured ? 'SECURED' : 'UNCONFIGURED'}
            </span>
          </div>
        </div>
      </div>

      <!-- Metadata Enrichment Guardrails -->
      <div class="card">
        <div class="card-header">
          <span class="card-title">Metadata Enrichment Guardrails</span>
        </div>
        <div style="display:flex;flex-direction:column;gap:10px;font-size:13px">
          <div style="display:flex;justify-content:space-between;border-bottom:1px solid var(--border2);padding-bottom:6px">
            <span class="text-2">Global Enrichment Enabled</span>
            <span class="badge badge-muted">DISABLED</span>
          </div>
          <div style="display:flex;justify-content:space-between;border-bottom:1px solid var(--border2);padding-bottom:6px">
            <span class="text-2">MusicBrainz Enrichment</span>
            <span class="badge badge-muted">DISABLED</span>
          </div>
          <div style="display:flex;justify-content:space-between;border-bottom:1px solid var(--border2);padding-bottom:6px">
            <span class="text-2">Spotify Enrichment</span>
            <span class="badge badge-muted">DISABLED</span>
          </div>
          <div style="display:flex;justify-content:space-between;border-bottom:1px solid var(--border2);padding-bottom:6px">
            <span class="text-2">Live Provider Calls</span>
            <span class="badge badge-muted">DISABLED</span>
          </div>
          <div style="display:flex;justify-content:space-between;border-bottom:1px solid var(--border2);padding-bottom:6px">
            <span class="text-2">Enrichment Scheduler</span>
            <span class="badge badge-muted">DISABLED</span>
          </div>
          <div style="display:flex;justify-content:space-between;border-bottom:1px solid var(--border2);padding-bottom:6px">
            <span class="text-2">Enrichment Worker</span>
            <span class="badge badge-muted">DISABLED</span>
          </div>
          <div style="display:flex;justify-content:space-between">
            <span class="text-2">DB Migration in this Pass</span>
            <span class="badge badge-muted">NONE</span>
          </div>
        </div>
      </div>

    </div>

    <!-- ── Copy-Paste Operations Terminal Runbook ── -->
    <div class="card mb-5">
      <div class="card-header">
        <span class="card-title">Runbook Guidelines & Copy-Paste Commands</span>
        <span class="text-3 text-sm">Secure terminal tools to run on the production server</span>
      </div>
      
      <div style="font-size:13px;line-height:1.5">
        
        <!-- 1. Dry Run -->
        <div style="margin-bottom:20px">
          <div style="font-weight:600;margin-bottom:6px;color:var(--text)">1. Capital FM UK One-Shot Dry Run</div>
          <p class="text-2 mb-2">To perform a dry-run check of the Capital HTML ingestion parser locally on the app container without updating database states or starting the scheduler daemon, execute:</p>
          <pre class="mono" style="padding:12px;background:var(--bg);border:1px solid var(--border);border-radius:4px;color:var(--accent);display:block;white-space:pre-wrap">docker exec -it rmias-app-1 python -m app.tools.dry_run_capital</pre>
        </div>

        <!-- 2. Payload Pruning -->
        <div style="margin-bottom:20px">
          <div style="font-weight:600;margin-bottom:6px;color:var(--text)">2. Manual Payload Pruning Job</div>
          <p class="text-2 mb-2">If payload retention is configured (`RAW_PAYLOAD_RETENTION_DAYS > 0`), the pruning job can be manually triggered to purge outdated on-disk payload backups:</p>
          <pre class="mono" style="padding:12px;background:var(--bg);border:1px solid var(--border);border-radius:4px;color:var(--accent);display:block;white-space:pre-wrap">docker exec -it rmias-app-1 python -m app.tools.prune_raw_payloads</pre>
        </div>

        <!-- 3. Rollback -->
        <div>
          <div style="font-weight:600;margin-bottom:6px;color:var(--text)">3. Capital Rollback & Config Reload</div>
          <p class="text-2 mb-2">If environment parameters (`.env.production`) are updated on the host server, containers must be force-recreated to load new settings safely. Trigger the rollback script:</p>
          <pre class="mono" style="padding:12px;background:var(--bg);border:1px solid var(--border);border-radius:4px;color:var(--accent);display:block;white-space:pre-wrap">ssh root@178.105.238.18 'bash /opt/rmias/scripts/rollback-capital.sh'</pre>
        </div>

      </div>
    </div>

    <!-- ── Metadata Provider Guardrails Reference ── -->
    <div class="card mb-5">
      <div class="card-header">
        <span class="card-title">Enrichment Provider Operation Rules</span>
      </div>
      <div style="font-size:13px;line-height:1.5;color:var(--text2)">
        <ul style="padding-left:16px;display:flex;flex-direction:column;gap:6px">
          <li><strong>MusicBrainz</strong>: Public queries require a specific User-Agent configuration and must follow rate limits of max one request per second. Use score as matching signal only.</li>
          <li><strong>Spotify</strong>: Client secrets must remain masked on the server and are never exposed to client-side code. Avoid playback or playlist scraping loops.</li>
          <li><strong>Cover Art Archive</strong>: Requests depend entirely on verified MusicBrainz Release MBIDs; do not query cover art aggressively without verified identifiers.</li>
          <li><strong>TenX Radar Authority</strong>: TenX Radar remains the sole truth source for actual station radio airplay logs; external provider metadata is layered on top.</li>
        </ul>
      </div>
    </div>

    <!-- ── Deployment Guardrail Warning ── -->
    <div style="background:rgba(239,68,68,.08);border:1px solid rgba(239,68,68,.2);border-radius:6px;padding:16px;font-size:13px;line-height:1.45;color:var(--danger)">
      <div style="font-weight:700;margin-bottom:4px">⚠ IMPORTANT DEPLOYMENT BOUNDARY</div>
      Do NOT deploy this branch to Hetzner automatically. Git pushing to the `main` branch or deployment actions must undergo strict pre-merge review and manual deployment passes. Automation controls in production must remain toggled off.
    </div>
  `;
}
