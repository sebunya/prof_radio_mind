import { API } from '../api.js';
import { esc } from '../ui.js';

export async function init(container, actions) {
  actions.innerHTML = '';
  container.innerHTML = '<div class="loader-center"><div class="loader"></div></div>';

  let readiness = {};
  try {
    readiness = await API.adminMetadataReadiness();
  } catch (err) {
    container.innerHTML = `<div class="alert alert-danger">Failed to load metadata configuration: ${esc(err.message)}</div>`;
    return;
  }

  const mb = readiness.providers?.musicbrainz || {};
  const sp = readiness.providers?.spotify || {};
  const caa = readiness.providers?.cover_art_archive || {};
  const boundary = readiness.compliance_boundary || {};

  container.innerHTML = `
    <div style="margin-bottom:24px">
      <div style="font-size:14px;color:var(--text2);margin-top:4px">
        MusicBrainz, Spotify and Cover Art Archive enrich captured radio play records after TenX Radar has already captured what aired.
      </div>
    </div>

    <!-- ── Three Providers Grid ── -->
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:20px;margin-bottom:24px;align-items:start">
      
      <!-- MusicBrainz Card -->
      <div class="card" style="display:flex;flex-direction:column;height:100%">
        <div class="card-header">
          <span class="card-title">MusicBrainz</span>
          <span class="badge ${mb.enabled ? 'badge-success' : 'badge-muted'}">
            ${mb.enabled ? 'Enabled' : 'Readiness Only'}
          </span>
        </div>
        <div style="font-size:11px;color:var(--text3);font-weight:600;text-transform:uppercase;margin-bottom:8px">Open Canonical Music Identity</div>
        <div style="font-size:13px;line-height:1.45;color:var(--text2);margin-bottom:16px;flex-grow:1">
          MusicBrainz will help TenX Radar identify canonical recordings, artists, releases, release groups, works, ISRCs, aliases, labels, credits, genres and relationships from captured radio play records.
        </div>
        
        <div style="background:var(--bg3);border-radius:6px;padding:12px;display:flex;flex-direction:column;gap:8px;font-size:12px;margin-bottom:16px">
          <div style="display:flex;justify-content:space-between;border-bottom:1px solid var(--border2);padding-bottom:4px">
            <span class="text-3">Base URL Configured</span>
            <span style="font-weight:600">${mb.base_url_configured ? '✓ Yes' : '✕ No'}</span>
          </div>
          <div style="display:flex;justify-content:space-between;border-bottom:1px solid var(--border2);padding-bottom:4px">
            <span class="text-3">User-Agent Configured</span>
            <span style="font-weight:600">${mb.user_agent_configured ? '✓ Yes' : '✕ No'}</span>
          </div>
          <div style="display:flex;justify-content:space-between;border-bottom:1px solid var(--border2);padding-bottom:4px">
            <span class="text-3">Rate Limit</span>
            <span style="font-weight:600">${mb.rate_limit_per_second || 1} req/sec</span>
          </div>
          <div style="display:flex;justify-content:space-between;border-bottom:1px solid var(--border2);padding-bottom:4px">
            <span class="text-3">Default Format</span>
            <span class="mono" style="font-size:11px">${esc(mb.default_format || 'json')}</span>
          </div>
          <div style="display:flex;justify-content:space-between">
            <span class="text-3">Live Calls Enabled</span>
            <span class="badge badge-muted">FALSE</span>
          </div>
        </div>

        <div style="background:rgba(var(--text-rgb),0.02);border:1px solid var(--border2);border-radius:4px;padding:10px;font-size:11px;color:var(--text3)">
          <strong>Guardrails:</strong>
          <ul style="padding-left:14px;margin-top:4px;display:flex;flex-direction:column;gap:3px">
            <li>Metadata authority layer only</li>
            <li>Not a radio monitoring source</li>
            <li>Requires proper User-Agent header</li>
            <li>Public use must respect rate limits</li>
            <li>Preserves raw station text</li>
          </ul>
        </div>
      </div>

      <!-- Spotify Card -->
      <div class="card" style="display:flex;flex-direction:column;height:100%">
        <div class="card-header">
          <span class="card-title">Spotify</span>
          <span class="badge ${sp.configured ? 'badge-warning' : 'badge-muted'}">
            ${sp.configured ? 'Readiness Ready' : 'Not Configured'}
          </span>
        </div>
        <div style="font-size:11px;color:var(--text3);font-weight:600;text-transform:uppercase;margin-bottom:8px">Commercial Catalogue Context</div>
        <div style="font-size:13px;line-height:1.45;color:var(--text2);margin-bottom:16px;flex-grow:1">
          Spotify will help TenX Radar enrich resolved tracks with Spotify IDs, platform reference URLs, artwork, release information and popularity signals where available.
        </div>

        <div style="background:var(--bg3);border-radius:6px;padding:12px;display:flex;flex-direction:column;gap:8px;font-size:12px;margin-bottom:16px">
          <div style="display:flex;justify-content:space-between;border-bottom:1px solid var(--border2);padding-bottom:4px">
            <span class="text-3">Client ID Configured</span>
            <span style="font-weight:600">${sp.client_id_configured ? '✓ Yes' : '✕ No'}</span>
          </div>
          <div style="display:flex;justify-content:space-between;border-bottom:1px solid var(--border2);padding-bottom:4px">
            <span class="text-3">Client Secret</span>
            <span style="font-weight:600">${sp.client_secret_configured ? '✓ Masked' : '✕ Missing'}</span>
          </div>
          <div style="display:flex;justify-content:space-between;border-bottom:1px solid var(--border2);padding-bottom:4px">
            <span class="text-3">Redirect URI Configured</span>
            <span style="font-weight:600">${sp.redirect_uri_configured ? '✓ Yes' : '✕ No'}</span>
          </div>
          <div style="display:flex;justify-content:space-between">
            <span class="text-3">Live Calls Enabled</span>
            <span class="badge badge-muted">FALSE</span>
          </div>
        </div>

        <div style="background:rgba(var(--text-rgb),0.02);border:1px solid var(--border2);border-radius:4px;padding:10px;font-size:11px;color:var(--text3)">
          <strong>Guardrails:</strong>
          <ul style="padding-left:14px;margin-top:4px;display:flex;flex-direction:column;gap:3px">
            <li>Metadata search reference only</li>
            <li>NO audio playback allowed</li>
            <li>NO track downloads/previews</li>
            <li>NO interactive Spotify OAuth</li>
            <li>NO playlist scraping loops</li>
          </ul>
        </div>
      </div>

      <!-- Cover Art Archive Card -->
      <div class="card" style="display:flex;flex-direction:column;height:100%">
        <div class="card-header">
          <span class="card-title">Cover Art Archive</span>
          <span class="badge badge-muted">Future-Ready</span>
        </div>
        <div style="font-size:11px;color:var(--text3);font-weight:600;text-transform:uppercase;margin-bottom:8px">Linked Artwork Fallback</div>
        <div style="font-size:13px;line-height:1.45;color:var(--text2);margin-bottom:16px;flex-grow:1">
          Cover Art Archive can provide release artwork metadata when TenX Radar has a confirmed MusicBrainz release MBID.
        </div>

        <div style="background:var(--bg3);border-radius:6px;padding:12px;display:flex;flex-direction:column;gap:8px;font-size:12px;margin-bottom:16px">
          <div style="display:flex;justify-content:space-between;border-bottom:1px solid var(--border2);padding-bottom:4px">
            <span class="text-3">Base URL Configured</span>
            <span style="font-weight:600">${caa.base_url_configured ? '✓ Yes' : '✕ No'}</span>
          </div>
          <div style="display:flex;justify-content:space-between;border-bottom:1px solid var(--border2);padding-bottom:4px">
            <span class="text-3">Release MBID Linked</span>
            <span style="font-weight:600">${caa.requires_musicbrainz_release_mbid ? '✓ Yes' : '✕ No'}</span>
          </div>
          <div style="display:flex;justify-content:space-between">
            <span class="text-3">Live Calls Enabled</span>
            <span class="badge badge-muted">FALSE</span>
          </div>
        </div>

        <div style="background:rgba(var(--text-rgb),0.02);border:1px solid var(--border2);border-radius:4px;padding:10px;font-size:11px;color:var(--text3)">
          <strong>Guardrails:</strong>
          <ul style="padding-left:14px;margin-top:4px;display:flex;flex-direction:column;gap:3px">
            <li>Artwork reference links only</li>
            <li>No ownership of artwork implied</li>
            <li>Linked strictly to MBID identifiers</li>
            <li>No aggressive downloads</li>
            <li>Cache all image metadata</li>
          </ul>
        </div>
      </div>

    </div>

    <!-- ── TenX Radar Resolved Metadata Layer ── -->
    <div class="card mb-5">
      <div class="card-header">
        <span class="card-title">TenX Radar Resolved Metadata Layer</span>
        <span class="badge badge-info">Architecture Gated</span>
      </div>
      
      <div style="display:grid;grid-template-columns:1.5fr 1fr;gap:20px;font-size:13px;line-height:1.5">
        <div>
          <p style="margin-bottom:12px;color:var(--text2)">
            TenX Radar owns the radio airplay truth. Provider metadata completes and enriches play records after airplay capture has been validated and normalized.
          </p>
          <div style="background:var(--bg3);border-radius:6px;padding:12px;border:1px solid var(--border2);color:var(--text2)">
            <strong>Core Matching Responsibilities:</strong>
            <ul style="padding-left:16px;margin-top:6px;display:flex;flex-direction:column;gap:4px">
              <li><strong>Airplay Capture</strong>: Preserves raw station played metadata.</li>
              <li><strong>Normalization Heuristics</strong>: Cleans titles/artists and strips tags.</li>
              <li><strong>Local Cache Verification</strong>: Validates against local database first.</li>
              <li><strong>Candidate Scoring</strong>: Weights match confidence levels.</li>
              <li><strong>Exception Handling</strong>: Sends ambiguous matches to the manual review queue.</li>
            </ul>
          </div>
        </div>

        <div>
          <div style="font-weight:600;margin-bottom:8px;color:var(--text)">Future Matching Status States</div>
          <div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:16px">
            <span class="badge badge-success">matched_auto</span>
            <span class="badge badge-success">matched_manual</span>
            <span class="badge badge-warning">candidate_review</span>
            <span class="badge badge-danger">no_match</span>
            <span class="badge badge-warning">ambiguous</span>
            <span class="badge badge-danger">metadata_conflict</span>
          </div>
          <div class="alert alert-info" style="font-size:12px;margin:0">
            ℹ <strong>No resolved metadata table has been implemented yet.</strong> Provider readiness is available for future enrichment passes.
          </div>
        </div>
      </div>
    </div>

    <!-- ── Compliance Boundary ── -->
    <div class="card">
      <div class="card-header">
        <span class="card-title">Compliance & Provider Guardrails Boundary</span>
      </div>
      <div style="font-size:13px;line-height:1.5;color:var(--text2);display:grid;grid-template-columns:1fr 1fr;gap:20px">
        <div>
          <div style="font-weight:600;margin-bottom:6px;color:var(--text)">Data Ingestion Sources</div>
          <table style="width:100%;font-size:12px">
            <tbody>
              <tr>
                <td style="width:150px;color:var(--text3);font-weight:600">Airplay Source:</td>
                <td>${esc(boundary.radio_capture_source || 'TenX Radar capture sources')}</td>
              </tr>
              <tr>
                <td style="color:var(--text3);font-weight:600">MusicBrainz:</td>
                <td>${esc(boundary.musicbrainz || 'Canonical identity and disambiguation only')}</td>
              </tr>
              <tr>
                <td style="color:var(--text3);font-weight:600">Spotify:</td>
                <td>${esc(boundary.spotify || 'Catalogue and reference links only')}</td>
              </tr>
              <tr>
                <td style="color:var(--text3);font-weight:600">Cover Art:</td>
                <td>${esc(boundary.cover_art_archive || 'Release artwork only')}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div>
          <div style="font-weight:600;margin-bottom:6px;color:var(--text)">Strict Legal Switches</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:12px">
            <div style="background:rgba(239,68,68,0.06);border:1px solid rgba(239,68,68,0.15);border-radius:4px;padding:6px;text-align:center">
              <span style="font-weight:600;color:var(--danger)">NO Streaming</span>
            </div>
            <div style="background:rgba(239,68,68,0.06);border:1px solid rgba(239,68,68,0.15);border-radius:4px;padding:6px;text-align:center">
              <span style="font-weight:600;color:var(--danger)">NO Downloads</span>
            </div>
            <div style="background:rgba(239,68,68,0.06);border:1px solid rgba(239,68,68,0.15);border-radius:4px;padding:6px;text-align:center">
              <span style="font-weight:600;color:var(--danger)">NO Playlist Scraping</span>
            </div>
            <div style="background:rgba(239,68,68,0.06);border:1px solid rgba(239,68,68,0.15);border-radius:4px;padding:6px;text-align:center">
              <span style="font-weight:600;color:var(--danger)">NO Audio Playback</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  `;
}
