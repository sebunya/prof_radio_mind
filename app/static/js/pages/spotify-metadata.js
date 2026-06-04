import { API } from '../api.js';
import { esc } from '../ui.js';

export async function init(container, actions) {
  actions.innerHTML = '';
  container.innerHTML = '<div class="loader-center"><div class="loader"></div></div>';

  let readiness = {};
  let status = {};
  try {
    [readiness, status] = await Promise.all([
      API.adminSpotifyReadiness(),
      API.adminEnrichmentStatus(),
    ]);
  } catch (err) {
    container.innerHTML = `<div class="alert alert-danger">Failed to load Spotify configuration: ${esc(err.message)}</div>`;
    return;
  }

  container.innerHTML = `
    <!-- ── Readiness checklist and flags ── -->
    <div style="display:grid;grid-template-columns:2fr 1fr;gap:20px;margin-bottom:20px">
      
      <!-- Configuration State -->
      <div class="card">
        <div class="card-header">
          <span class="card-title">Spotify Web API Integration Readiness</span>
          <span class="badge ${readiness.client_id_configured && readiness.client_secret_configured ? 'badge-success' : 'badge-warning'}">
            ${readiness.client_id_configured && readiness.client_secret_configured ? 'Ready' : 'Pending Credentials'}
          </span>
        </div>
        
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px">
          <div style="background:var(--bg3);border-radius:6px;padding:12px;display:flex;align-items:center;justify-content:space-between">
            <div>
              <div style="font-size:11px;color:var(--text3);font-weight:600;text-transform:uppercase">Spotify Client ID</div>
              <div style="font-weight:600;font-size:13px;margin-top:2px">${readiness.client_id_configured ? '✓ Configured' : '✕ Missing'}</div>
            </div>
          </div>
          <div style="background:var(--bg3);border-radius:6px;padding:12px;display:flex;align-items:center;justify-content:space-between">
            <div>
              <div style="font-size:11px;color:var(--text3);font-weight:600;text-transform:uppercase">Spotify Client Secret</div>
              <div style="font-weight:600;font-size:13px;margin-top:2px">${readiness.client_secret_configured ? '✓ Masked & Secure' : '✕ Missing'}</div>
            </div>
          </div>
        </div>

        <div style="display:flex;flex-direction:column;gap:10px;font-size:13px">
          <div style="display:flex;justify-content:space-between;border-bottom:1px solid var(--border2);padding-bottom:6px">
            <span class="text-2">Metadata Enrichment Switch</span>
            <span class="badge ${readiness.enrichment_enabled_flag ? 'badge-success' : 'badge-muted'}">
              ${readiness.enrichment_enabled_flag ? 'ENABLED' : 'DISABLED'}
            </span>
          </div>
          <div style="display:flex;justify-content:space-between;border-bottom:1px solid var(--border2);padding-bottom:6px">
            <span class="text-2">Redirect URI (Production)</span>
            <span class="mono" style="font-size:11px">${esc(readiness.redirect_uri)}</span>
          </div>
          <div style="display:flex;justify-content:space-between;border-bottom:1px solid var(--border2);padding-bottom:6px">
            <span class="text-2">Redirect URI (Local Dev Override)</span>
            <span class="mono" style="font-size:11px">http://127.0.0.1:3000/api/auth/spotify/callback</span>
          </div>
          <div style="display:flex;justify-content:space-between;border-bottom:1px solid var(--border2);padding-bottom:6px">
            <span class="text-2">Confidence Match Threshold</span>
            <span style="font-weight:600">${Math.round(readiness.match_confidence_threshold * 100)}%</span>
          </div>
          <div style="display:flex;justify-content:space-between;border-bottom:1px solid var(--border2);padding-bottom:6px">
            <span class="text-2">API Timeout / Max Retries</span>
            <span style="font-weight:600">${readiness.request_timeout_seconds}s / ${readiness.max_retries} attempts</span>
          </div>
        </div>
      </div>

      <!-- Compliance Policy -->
      <div class="card" style="display:flex;flex-direction:column;justify-content:between">
        <div>
          <div class="card-header" style="margin-bottom:8px">
            <span class="card-title">Compliance Boundary</span>
          </div>
          <div style="font-size:12px;line-height:1.45;color:var(--text2)">
            <p style="margin-bottom:8px"><strong>TenX Radar</strong> is registered as a metadata-only intelligence client application.</p>
            <p style="margin-bottom:8px">Under the Spotify Developer Terms, this app operates within the following strictly enforced guardrails:</p>
            <ul style="padding-left:14px;display:flex;flex-direction:column;gap:4px">
              <li><strong>NO Audio Playback</strong>: Do not embed Web Playback SDK.</li>
              <li><strong>NO Audio Preview</strong>: Audio streaming or track downloads are disabled.</li>
              <li><strong>NO User Login</strong>: Runs entirely server-side via Client Credentials Flow.</li>
            </ul>
          </div>
        </div>
        <div style="background:rgba(245,158,11,.08);border:1px solid rgba(245,158,11,.2);border-radius:4px;padding:8px 10px;font-size:11px;color:var(--warning);margin-top:12px">
          ⚠ Live Spotify queries and enrichment jobs are disabled.
        </div>
      </div>

    </div>

    <!-- ── Developer App Branding Registry ── -->
    <div class="card mb-5">
      <div class="card-header">
        <span class="card-title">Spotify Developer App Registration Details</span>
      </div>
      <div style="font-size:13px;line-height:1.5;color:var(--text2)">
        <table style="width:100%;font-size:13px">
          <tbody>
            <tr>
              <td style="width:180px;font-weight:600;color:var(--text)">App Name:</td>
              <td><code>TenX Radar</code></td>
            </tr>
            <tr>
              <td style="font-weight:600;color:var(--text)">App Description:</td>
              <td>
                <span class="text-sm">
                  TenX Radar is a radio airplay and media intelligence platform that helps broadcasters, music teams, brands, and media analysts monitor songs played across radio stations, identify tracks, enrich song metadata, and generate music trend reports. Spotify’s Web API will be used only for music metadata enrichment, including track titles, artists, albums, artwork, Spotify IDs, release dates, popularity signals, and official Spotify reference links where available. TenX Radar does not stream, download, redistribute, or sell Spotify audio content.
                </span>
              </td>
            </tr>
            <tr>
              <td style="font-weight:600;color:var(--text)">Website URL:</td>
              <td><code>https://tenxradar.com</code></td>
            </tr>
            <tr>
              <td style="font-weight:600;color:var(--text)">APIs / SDKs:</td>
              <td><code>Web API only</code></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ── Spotify Metadata Enrichment Telemetry ── -->
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;margin-bottom:20px">
      <div style="background:var(--bg3);border-radius:6px;padding:16px;display:flex;flex-direction:column;align-items:center;justify-content:center;border:1px solid var(--border2)">
        <div style="font-size:11px;color:var(--text3);font-weight:600;text-transform:uppercase;margin-bottom:4px">Matched Tracks</div>
        <div style="font-size:28px;font-weight:700;color:var(--success)">${status.counts?.matched ?? 0}</div>
      </div>
      <div style="background:var(--bg3);border-radius:6px;padding:16px;display:flex;flex-direction:column;align-items:center;justify-content:center;border:1px solid var(--border2)">
        <div style="font-size:11px;color:var(--text3);font-weight:600;text-transform:uppercase;margin-bottom:4px">Failed Matches</div>
        <div style="font-size:28px;font-weight:700;color:var(--danger)">${status.counts?.failed ?? 0}</div>
      </div>
      <div style="background:var(--bg3);border-radius:6px;padding:16px;display:flex;flex-direction:column;align-items:center;justify-content:center;border:1px solid var(--border2)">
        <div style="font-size:11px;color:var(--text3);font-weight:600;text-transform:uppercase;margin-bottom:4px">Pending Enrichment</div>
        <div style="font-size:28px;font-weight:700;color:var(--warning)">${status.counts?.pending ?? 0}</div>
      </div>
    </div>

    <!-- ── Active Database Integration Schema & CLI ── -->
    <div class="card">
      <div class="card-header">
        <span class="card-title">Database Schema & Execution Commands</span>
        <span class="badge badge-success">Active Schema</span>
      </div>
      <div style="font-size:13px;line-height:1.5">
        <p class="text-2 mb-4">
          The Spotify enrichment schema is fully active inside the <code>songs</code> database table. The following metadata fields are tracked:
        </p>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
          
          <div>
            <div style="font-weight:600;margin-bottom:8px;color:var(--text)">Tracked Database Fields</div>
            <ul style="padding-left:16px;color:var(--text2);display:flex;flex-direction:column;gap:4px;font-size:12px">
              <li><code class="mono">spotify_track_id</code> (String) - Spotify unique ID for the track</li>
              <li><code class="mono">spotify_artist_id</code> (String) - Spotify ID for the main artist</li>
              <li><code class="mono">spotify_album_id</code> (String) - Spotify ID for the album</li>
              <li><code class="mono">spotify_uri</code> (String) - Spotify standard URI</li>
              <li><code class="mono">spotify_external_url</code> (Text) - Spotify URL for Web App link</li>
              <li><code class="mono">spotify_isrc</code> (String) - International Standard Recording Code</li>
              <li><code class="mono">spotify_artwork_url</code> (Text) - High-resolution artwork URL</li>
              <li><code class="mono">spotify_popularity_score</code> (Integer) - Score from 0 to 100</li>
              <li><code class="mono">match_confidence_score</code> (Float) - Match confidence ratio</li>
              <li><code class="mono">spotify_enriched_at</code> (DateTime) - Timestamp of last enrichment attempt</li>
            </ul>
          </div>

          <div>
            <div style="font-weight:600;margin-bottom:8px;color:var(--text)">Run Manual Catalog Enrichment</div>
            <p class="text-2 mb-3" style="font-size:12px">
              Developers can execute manual, rate-limited batch enrichment tasks against the database using the command line utility:
            </p>
            <div style="background:var(--bg3);border-radius:6px;padding:12px;font-family:var(--mono);font-size:11px;color:var(--text2);position:relative;border:1px solid var(--border2);margin-bottom:12px">
              <span style="position:absolute;top:6px;right:10px;font-size:9px;color:var(--text3);font-family:sans-serif;text-transform:uppercase;font-weight:bold">Command</span>
              python -m scripts.enrich_catalog --limit 100 --delay 0.5
            </div>
            <div class="text-3 text-xs">
              <strong>Usage Parameters:</strong><br>
              • <code>--limit N</code>: Maximum number of songs to attempt to enrich.<br>
              • <code>--delay S</code>: Cool-down delay in seconds between queries to prevent API rate-limiting.<br>
              • <code>--batch-size B</code>: Database query size limit per loop check.
            </div>
          </div>

        </div>

      </div>
    </div>
  `;
}
