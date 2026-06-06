/**
 * RMIAS API client — all fetch calls go through here.
 * Auth is disabled in dev mode (API_KEY env var not set), so no key is sent.
 */

export async function apiCall(method, path, body = null, isFormData = false) {
  const headers = {};
  if (body && !isFormData) headers['Content-Type'] = 'application/json';

  const opts = { method, headers };
  if (body) opts.body = isFormData ? body : JSON.stringify(body);

  const resp = await fetch(path, opts);

  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`;
    try {
      const j = await resp.json();
      if (Array.isArray(j.detail)) {
        detail = j.detail.map(e => e.msg || JSON.stringify(e)).join('; ');
      } else {
        detail = j.detail || detail;
      }
    } catch { /* ignore */ }
    const err = new Error(detail);
    err.status = resp.status;
    throw err;
  }

  if (resp.status === 204) return null;
  const ct = resp.headers.get('content-type') || '';
  return ct.includes('json') ? resp.json() : resp.blob();
}

export const API = {
  // ── Health ──────────────────────────────────────────────────
  health: () => apiCall('GET', '/health'),

  // ── Stations ────────────────────────────────────────────────
  stations: () => apiCall('GET', '/stations'),

  // ── Review queue ────────────────────────────────────────────
  reviewItems: (status) =>
    apiCall('GET', `/review-items${status ? `?status=${status}` : ''}`),
  reviewItem: (id) => apiCall('GET', `/review-items/${id}`),
  resolveItem: (id, body) => apiCall('POST', `/review-items/${id}/resolve`, body),
  dismissItem: (id, body) => apiCall('POST', `/review-items/${id}/dismiss`, body),
  escalateItem: (id, body) => apiCall('POST', `/review-items/${id}/escalate`, body),

  // ── Reports ─────────────────────────────────────────────────
  generateReport: (stationId, body) =>
    apiCall('POST', `/reports/${stationId}/generate`, body),
  downloadReport: (stationId, date) =>
    apiCall('GET', `/reports/${stationId}/download?report_date=${date}`),
  masterReport: (date) =>
    apiCall('GET', `/reports/master/download${date ? `?report_date=${date}` : ''}`),

  // ── Playlist ─────────────────────────────────────────────────
  analyseRotation: (stationId, days = 7) =>
    apiCall('POST', `/playlist/${stationId}/analyse?lookback_days=${days}`),
  approveRec: (id, body) =>
    apiCall('POST', `/playlist/recommendations/${id}/approve`, body),

  // ── ARIA Charts ──────────────────────────────────────────────
  ingestAria: (date) =>
    apiCall('POST', `/charts/aria/ingest${date ? `?chart_date=${date}` : ''}`),
  latestAria: () => apiCall('GET', '/charts/aria/latest'),

  // ── Webhooks ─────────────────────────────────────────────────
  webhooks: () => apiCall('GET', '/webhooks'),
  registerWebhook: (body) => apiCall('POST', '/webhooks', body),
  deleteWebhook: (id) => apiCall('DELETE', `/webhooks/${id}`),

  // ── Backfill ─────────────────────────────────────────────────
  backfill: (stationId, date, formData) =>
    apiCall('POST', `/backfill/${stationId}?broadcast_date=${date}`, formData, true),

  // ── Admin Telemetry ──────────────────────────────────────────
  adminOverview: () => apiCall('GET', '/api/admin/overview'),
  adminOperations: () => apiCall('GET', '/api/admin/operations'),
  adminRecentEvents: () => apiCall('GET', '/api/admin/recent-events'),
  playEvents: (params = {}) => {
    const q = new URLSearchParams();
    if (params.station_id) q.set('station_id', params.station_id);
    if (params.date_from)  q.set('date_from', params.date_from);
    if (params.date_to)    q.set('date_to', params.date_to);
    if (params.limit)      q.set('limit', String(params.limit));
    if (params.offset)     q.set('offset', String(params.offset));
    const qs = q.toString();
    return apiCall('GET', `/api/admin/play-events${qs ? '?' + qs : ''}`);
  },
  adminSourceHealth: () => apiCall('GET', '/api/admin/source-health'),
  adminReviewSummary: () => apiCall('GET', '/api/admin/review-summary'),
  adminEnrichmentStatus: () => apiCall('GET', '/api/admin/enrichment-status'),
  adminSpotifyReadiness: () => apiCall('GET', '/api/admin/spotify-readiness'),
  adminMetadataReadiness: () => apiCall('GET', '/api/admin/metadata-readiness'),
  adminCollectorRuns: () => apiCall('GET', '/api/admin/collector-runs'),
};
