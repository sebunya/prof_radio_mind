# UIUX-REF1 Information Architecture

_Author: Claude · Date: 2026-06-04 · Branch: `feat/uiux-ref1-admin-console-redesign`_

---

## Admin Console Structure (Implemented in this Pass)

### Navigation

```
TenX Radar  [ENV badge]
Radio Intelligence

── Core ──────────────────────
Dashboard           /dashboard
Radio Stations      /stations
Review Queue        /review   [pending badge]
Reports             /reports
Playlist            /playlist
ARIA Charts         /charts
Webhooks            /webhooks
Backfill            /backfill

── System ────────────────────
Operations          /operations
```

---

## Page Designs

### 1. Dashboard (`/dashboard`)

**Primary purpose:** Immediate operational situational awareness.

**Sections:**
1. **Stat cards row (4-up)**
   - Active Stations (count, accent)
   - Pending Reviews (count, warning/success)
   - Active Webhooks (count)
   - System Status (ok/degraded with dot)

2. **System State Strip** ← NEW in this pass
   - Scheduler chip (disabled=grey, enabled=amber)
   - API Docs chip (hidden=green, exposed=info/amber)
   - Admin Auth chip (protected=green, public=info)
   - Deduplication chip (active=green)
   - Retention chip (off=grey, N days=info)
   - "View Operations →" link

3. **Review Queue charts (2-up)**
   - Doughnut: queue by status
   - Bar: queue by type

4. **Station list preview** (top 5, link to Stations)
5. **Recent review items** (top 8, link to Review Queue)

---

### 2. Radio Stations (`/stations`)

**Primary purpose:** Station registry overview.

**Sections:**
1. **Station table**
   - Call Sign (badge)
   - Station Name
   - Frequency
   - City
   - Country code

2. **About Data Collection** ← UPDATED
   - Info box explaining sources vary per station
   - No hardcoded static badges
   - Points to docs/NEXT_STEPS.md for collector readiness

---

### 3. Review Queue (`/review`)

Unchanged. Shows filter tabs (all/pending/reviewed/dismissed/escalated), item table, and action modals.

---

### 4. Reports (`/reports`)

Unchanged. Report generation, download, confidence display.

---

### 5. Playlist (`/playlist`)

Unchanged. Rotation analysis and tier recommendations.

---

### 6. ARIA Charts (`/charts`)

Unchanged. Chart ingestion and top-10 visual.

---

### 7. Webhooks (`/webhooks`)

Unchanged. Webhook management.

---

### 8. Backfill (`/backfill`)

Unchanged. CSV import.

---

### 9. Operations (`/operations`) ← NEW in this pass

**Primary purpose:** Read-only view of all operational state flags. No action buttons.

**Sections:**
1. **System Configuration grid (6 cards)**
   - Environment (badge: PRODUCTION/DEVELOPMENT/STAGING)
   - Scheduler (Enabled amber/Disabled grey)
   - API Docs (Exposed info/Hidden green)
   - Admin Auth (Protected green/Public info)
   - Deduplication (Active green — always)
   - Raw Payload Retention (N days info/Off grey)

2. **Collector Flags table**
   - Capital FM UK — ENABLE_CAPITAL_COLLECTOR
   - Nova 96.9 FM — ENABLE_NOVA_COLLECTOR
   - KIIS FM 102.7 — ENABLE_KIIS_COLLECTOR
   - Nightly Reconciliation — ENABLE_NIGHTLY_RECONCILIATION
   - Info box: "All disabled by default. No collector can be enabled from this console."

3. **Production Guardrails section**
   - Dynamic warnings based on current state
   - Collector validation required notice
   - Scheduler safety notice
   - Retention off notice (if applicable)
   - Admin auth public notice (if applicable)
   - Docs exposed in production notice (if applicable)

4. **Operational Reference section**
   - What you can do from this console (read list)
   - What requires a separate operations pass (read list)
   - Prune command reference (read-only, no execute button)
   - Dry-run command reference (read-only, no execute button)

---

## Design Tokens

All existing CSS tokens from `app/css/app.css` are preserved. New tokens added:

| Token use | CSS class | Color |
|---|---|---|
| Production env badge | `.env-prod` | Red tint (#fca5a5) |
| Staging env badge | `.env-staging` | Yellow tint (#fcd34d) |
| Dev env badge | `.env-dev` | Grey tint (text3) |
| Enabled/warning chip | `.chip-warn` | Amber |
| Disabled/muted chip | `.chip-muted` | Grey |
| OK/active chip | `.chip-ok` | Green |
| Info chip | `.chip-info` | Blue/accent |
| Guardrail box | `.guardrail-box` | Amber tint border |
| Info box | `.info-box` | Accent tint |

---

## API Endpoints Used in This Pass

| Endpoint | Page | Access |
|---|---|---|
| `GET /health` | Dashboard | Read |
| `GET /stations` | Dashboard, Stations | Read |
| `GET /review-items` | Dashboard, Review | Read |
| `GET /webhooks` | Dashboard, Webhooks | Read |
| `GET /api/admin/overview` | Dashboard (strip), Operations | Read |

---

## Deferred to Future Passes

| Feature | Reason |
|---|---|
| Play events table | Requires `/play-events` read endpoint (not on main) |
| Collector health | Route on feature branch only, not yet on main |
| Email reports | Route on feature branch only, not yet on main |
| Migration version display | Requires alembic introspection endpoint |
| Raw payload evidence viewer | High risk, requires secure audit controls |
| Source health detail table | Partial API available, full view deferred |
| Collector enable/disable controls | Expressly prohibited in this pass |
| Rollback/dry-run execution | Expressly prohibited in this pass |
