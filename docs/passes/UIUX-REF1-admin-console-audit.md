# UIUX-REF1 Admin Console Audit

_Author: Claude · Date: 2026-06-04 · Branch: `feat/uiux-ref1-admin-console-redesign`_

---

## 1. Branch Base and REF-0 Presence

- **Branch base:** `main` (REF-0 merged via PR #6)
- **REF-0 presence:** Present — all 10 expected REF-0 artifacts confirmed:
  - `app/tools/dry_run_capital.py` ✓
  - `app/tools/prune_raw_payloads.py` ✓
  - `scripts/rollback-capital.sh` ✓
  - `migrations/versions/c4e2a1f9b8d7_phase_e_play_events_dedup_index.py` ✓
  - `ENABLE_DOCS_IN_PRODUCTION` gating ✓
  - `ADMIN_BASIC_AUTH_USER/PASSWORD` optional auth ✓
  - `RAW_PAYLOAD_RETENTION_DAYS` setting ✓
  - `exists_by_fingerprint()` dedup in scheduler ✓
  - `.github/workflows/ci.yml`, `semgrep.yml`, `snyk.yml` ✓
  - Phase E migration (`c4e2a1f9b8d7`) ✓

---

## 2. Existing UI Inventory

### Static files (`app/static/`)
- `index.html` — Single-page app shell with hash-based router
- `css/app.css` — 862-line design system (tokens, components, utilities)
- `js/api.js` — Centralised API client (40+ methods)
- `js/ui.js` — Shared utilities (escape, toasts, modals, formatters, badges)
- `js/app.js` — Router, nav, API status polling, pending-review badge
- `js/pages/dashboard.js` — Overview stats, charts, station list, review items
- `js/pages/stations.js` — Station table with hardcoded static coverage badges
- `js/pages/review.js` — Review queue with filter tabs and action modals
- `js/pages/reports.js` — Report generation, download, confidence display
- `js/pages/playlist.js` — Rotation analysis, tier recommendations, batch approve
- `js/pages/aria-charts.js` — ARIA chart ingestion, top-10 visual, full table
- `js/pages/webhooks.js` — Webhook registration, cards, delete confirmation
- `js/pages/backfill.js` — CSV upload, drag-and-drop, results display

### Nav pages (8 total): dashboard, stations, review, reports, playlist, charts, webhooks, backfill

---

## 3. API Routes on Main Branch

| Route | Method | Purpose |
|---|---|---|
| `/health` | GET | Liveness check (scheduler, DB, pending count) |
| `/stations` | GET | Station list from STATION_SEEDS |
| `/review-items` | GET/POST | Review queue CRUD |
| `/reports/{station_id}/generate` | POST | Generate daily report |
| `/reports/{station_id}/download` | GET | Download CSV report |
| `/reports/master/download` | GET | Master cross-station report |
| `/playlist/{station_id}/analyse` | POST | Rotation analysis |
| `/playlist/recommendations/{id}/approve` | POST | Approve recommendation |
| `/charts/aria/ingest` | POST | Ingest ARIA chart |
| `/charts/aria/latest` | GET | Latest ARIA chart |
| `/webhooks` | GET/POST/DELETE | Webhook subscriptions |
| `/backfill/{station_id}` | POST | CSV backfill upload |
| `/sources/{source_id}/validate` | POST | Source validation |
| `/sources/{source_id}/validations` | GET | Validation history |
| `/proof-of-play/*` | GET | Proof-of-play evidence |

---

## 4. What UI Exists Today — Audit Findings

### 4.1 Missing REF-0 Representation
- No environment badge (no way to know if you're in production vs development)
- No scheduler enabled/disabled display on dashboard
- No docs exposure status
- No admin auth status
- No raw payload retention status
- No deduplication status display
- No operational flags view
- No guardrails section

### 4.2 Inaccurate Data
- `app/static/js/pages/stations.js`: Collection coverage shows hardcoded badges (Radiowave, iHeart, Manual CSV) for every station regardless of actual source configuration — misleading
- `app/static/js/pages/dashboard.js`: Uses `h.scheduler_running` but health response uses `h.components.scheduler` — always shows "Stopped" incorrectly

### 4.3 Missing Mobile Support
- No hamburger toggle button (sidebar cannot be opened on mobile)
- No sidebar scrim/overlay
- CSS has mobile rules but no triggering JS

### 4.4 Branding
- Title shows "RMIAS — Admin Dashboard" (internal code name, not product name)
- Sidebar shows "RMIAS / Admin" (should be "TenX Radar / Radio Intelligence")

### 4.5 Accessibility
- `aria-live` not present on API status indicator
- Modal overlay lacks `role="dialog"`, `aria-modal`, `aria-labelledby`
- No `aria-label` on icon-only buttons
- No `aria-hidden` on decorative SVGs
- Toast container lacks `aria-live="assertive"`

### 4.6 Security / Safety
- CSP allows `unsafe-inline` for scripts — low impact (SPA pattern) but noted
- `sentry_send_default_pii=True` — sends request headers including potential auth tokens
- Health endpoint leaks exception text in `db_status` — could expose connection errors

---

## 5. What APIs Are Safe for UI Use

**Safe (read-only, no state mutation):**
- `GET /health` — system state
- `GET /stations` — station list
- `GET /review-items` — review queue
- `GET /charts/aria/latest` — ARIA chart data
- `GET /webhooks` — webhook list
- `GET /sources/{id}/validations` — validation history
- `GET /proof-of-play/*` — evidence lookup

**New (proposed as part of this pass):**
- `GET /api/admin/overview` — operational state flags (no secrets)

**Caution (write operations, require API key in production):**
- POST/DELETE endpoints — all write actions require authentication in production
- Currently UI sends no auth headers — relies on API_KEY=empty in dev

---

## 6. What Must Not Be Exposed

- DATABASE_URL (connection string with credentials)
- API_KEY value
- ADMIN_BASIC_AUTH_PASSWORD
- SMTP credentials
- S3 secret key
- Server IP / SSH paths
- Raw payload file contents (require evidence viewer approval)
- Full environment variable dump

---

## 7. Operational States That Must Be Shown

| State | Source | Current Display |
|---|---|---|
| Environment (production/dev) | `/api/admin/overview` | Missing |
| Scheduler enabled | `/api/admin/overview` | Missing |
| Collector flags | `/api/admin/overview` | Missing |
| Docs exposure | `/api/admin/overview` | Missing |
| Admin auth status | `/api/admin/overview` | Missing |
| Dedup enabled | `/api/admin/overview` | Missing |
| Raw payload retention | `/api/admin/overview` | Missing |
| API health | `/health` | Shown (dashboard stat) |
| Pending reviews | `/health` | Shown (dashboard stat) |

---

## 8. What Can Be Improved With Frontend-Only Work

- Fix scheduler display bug (h.scheduler_running → h.components?.scheduler)
- Remove hardcoded station coverage badges
- Add mobile sidebar toggle
- Fix title/branding
- Improve accessibility attributes
- Add empty state messaging improvements
- Add environment badge from `/api/admin/overview`

---

## 9. What Requires New Backend Support

- `/api/admin/overview` endpoint — **added in this pass** (read-only)

---

## 10. What Is Deferred to Future Passes

- Evidence/raw payload viewer (requires secure audit trail and authorisation controls)
- Play events table (requires dedicated `/play-events` read endpoint)
- Collector health page (route exists on feature branch, not yet on main)
- Email reports page (route exists on feature branch, not yet on main)
- Collector run history (route exists on feature branch, not yet on main)
- Migration version display (requires alembic introspection endpoint)
- Canary / dry-run execution controls (high risk, separate ops pass)
- Rollback execution controls (high risk, separate ops pass)
- Source health details table (partial `/sources` API exists)
