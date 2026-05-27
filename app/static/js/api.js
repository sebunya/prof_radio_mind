/**
 * RMIAS API client — all fetch calls go through here.
 * Auth is disabled in dev mode (API_KEY env var not set), so no key is sent.
 */

/**
 * Like apiCall but also returns the X-Total-Count header for paginated endpoints.
 * Returns { items: Array, total: number }.
 */
export async function apiCallPaged(method, path, body = null) {
  const headers = {};
  if (body) headers['Content-Type'] = 'application/json';
  const opts = { method, headers };
  if (body) opts.body = JSON.stringify(body);

  let resp;
  try {
    resp = await fetch(path, opts);
  } catch (networkErr) {
    const err = new Error('Network error — server unreachable');
    err.status = 0;
    err.cause = networkErr;
    throw err;
  }

  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`;
    try {
      const j = await resp.json();
      detail = Array.isArray(j.detail)
        ? j.detail.map(e => e.msg || JSON.stringify(e)).join('; ')
        : j.detail || detail;
    } catch { /* non-JSON */ }
    const err = new Error(detail);
    err.status = resp.status;
    throw err;
  }

  const total = parseInt(resp.headers.get('X-Total-Count') || '0', 10);
  const items = await resp.json();
  return { items, total };
}

export async function apiCall(method, path, body = null, isFormData = false) {
  const headers = {};
  if (body && !isFormData) headers['Content-Type'] = 'application/json';

  const opts = { method, headers };
  if (body) opts.body = isFormData ? body : JSON.stringify(body);

  let resp;
  try {
    resp = await fetch(path, opts);
  } catch (networkErr) {
    // fetch() itself threw — network unreachable, DNS failure, CORS preflight blocked, etc.
    const err = new Error('Network error — server unreachable');
    err.status = 0;
    err.cause = networkErr;
    throw err;
  }

  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`;
    try {
      const j = await resp.json();
      if (Array.isArray(j.detail)) {
        detail = j.detail.map(e => e.msg || JSON.stringify(e)).join('; ');
      } else if (j.detail && typeof j.detail === 'object') {
        detail = j.detail.message || JSON.stringify(j.detail);
      } else {
        detail = j.detail || detail;
      }
    } catch { /* non-JSON body — keep the HTTP status text */ }
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

  // ── Collector health ────────────────────────────────────────
  collectorSummary: () => apiCall('GET', '/collector-runs/summary'),
  collectorRuns: ({ status = null, stationId = null, limit = 50, offset = 0 } = {}) => {
    const p = new URLSearchParams({ limit, offset });
    if (status)    p.set('status', status);
    if (stationId) p.set('station_id', stationId);
    return apiCallPaged('GET', `/collector-runs?${p}`);
  },
  collectorRun: (id) => apiCall('GET', `/collector-runs/${id}`),

  // ── Review queue ────────────────────────────────────────────
  // Backward-compatible: returns array (uses default limit=50).
  reviewItems: (status) =>
    apiCall('GET', `/review-items${status ? `?status=${status}` : ''}`),
  // Paginated variant: returns { items, total }.
  reviewItemsPaged: ({ status = null, limit = 50, offset = 0 } = {}) => {
    const p = new URLSearchParams({ limit, offset });
    if (status) p.set('status', status);
    return apiCallPaged('GET', `/review-items?${p}`);
  },
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
  webhooksPaged: ({ limit = 50, offset = 0 } = {}) =>
    apiCallPaged('GET', `/webhooks?limit=${limit}&offset=${offset}`),
  registerWebhook: (body) => apiCall('POST', '/webhooks', body),
  deleteWebhook: (id) => apiCall('DELETE', `/webhooks/${id}`),

  // ── Backfill ─────────────────────────────────────────────────
  backfill: (stationId, date, formData) =>
    apiCall('POST', `/backfill/${stationId}?broadcast_date=${date}`, formData, true),

  // ── Email reports ─────────────────────────────────────────────
  emailRecipients: () => apiCall('GET', '/email-reports/recipients'),
  emailRecipientsPaged: ({ limit = 50, offset = 0 } = {}) =>
    apiCallPaged('GET', `/email-reports/recipients?limit=${limit}&offset=${offset}`),
  addEmailRecipient: (body) => apiCall('POST', '/email-reports/recipients', body),
  updateEmailRecipient: (id, body) =>
    apiCall('PATCH', `/email-reports/recipients/${id}`, body),
  removeEmailRecipient: (id) => apiCall('DELETE', `/email-reports/recipients/${id}`),
  emailLogs: (limit = 50) => apiCall('GET', `/email-reports/logs?limit=${limit}`),
  emailLogsPaged: ({ limit = 50, offset = 0 } = {}) =>
    apiCallPaged('GET', `/email-reports/logs?limit=${limit}&offset=${offset}`),
  sendEmailNow: (frequency, startDate = null, endDate = null) => {
    const body = { frequency };
    if (startDate) body.start_date = startDate;
    if (endDate)   body.end_date   = endDate;
    return apiCall('POST', '/email-reports/send-now', body);
  },
  previewEmail: (frequency, startDate = null, endDate = null) => {
    if (startDate && endDate) {
      return apiCall(
        'GET',
        `/email-reports/preview/${frequency}?start_date=${startDate}&end_date=${endDate}`,
      );
    }
    return apiCall('GET', `/email-reports/preview/${frequency}`);
  },
};
