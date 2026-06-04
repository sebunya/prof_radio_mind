# UIUX-REF1 Admin Console Redesign

_Author: Claude · Date: 2026-06-04 · Branch: `feat/uiux-ref1-admin-console-redesign`_

---

## Verdict

**UI REDESIGN IMPLEMENTED — PR READY**

---

## Summary

This pass delivers a REF-0-aware admin console for TenX Radar that accurately reflects
operational state, enforces production guardrails, and fixes several correctness and
accessibility issues present in the prior UI.

---

## Branch Base

- **Base:** `main` (REF-0 PR #6 merged)
- **Branch:** `feat/uiux-ref1-admin-console-redesign`

## REF-0 Presence

- **Status:** Present — all 10 REF-0 artifacts confirmed before branching

---

## Files Changed

### Backend

| File | Change |
|---|---|
| `app/api/routes/admin_overview.py` | NEW — read-only `/api/admin/overview` endpoint |
| `app/main.py` | Add `admin_overview_router` import and `include_router` |

### Frontend

| File | Change |
|---|---|
| `app/static/index.html` | TenX Radar branding, Operations nav, mobile toggle, sidebar scrim, env badge slot, ARIA attributes, modal role attrs |
| `app/static/css/app.css` | Add: env badge, sidebar toggle, sidebar scrim, system status strip, status chips, ops cards, guardrail box, info box, nav section label, mobile ops-grid responsive |
| `app/static/js/api.js` | Add `adminOverview()` method |
| `app/static/js/app.js` | Add Operations page, env badge refresh, mobile sidebar toggle, stale navigation guard |
| `app/static/js/pages/dashboard.js` | Fix scheduler display bug, add system state strip (via overview API), add Operations link |
| `app/static/js/pages/stations.js` | Remove false static coverage badges, improve empty state text, add info box |
| `app/static/js/pages/operations.js` | NEW — full read-only operational state view |

### Tests

| File | Change |
|---|---|
| `tests/unit/test_admin_overview.py` | NEW — 12 tests for the overview endpoint |

### Documentation

| File | Change |
|---|---|
| `docs/passes/UIUX-REF1-admin-console-audit.md` | NEW — full Phase 1 audit |
| `docs/passes/UIUX-REF1-information-architecture.md` | NEW — Phase 2 IA |
| `docs/passes/UIUX-REF1-task.md` | NEW — pass record |
| `docs/passes/UIUX-REF1-admin-console-redesign.md` | This file |

---

## UI Screens Implemented

### Dashboard (improved)
- System state strip between stat cards and charts
- Shows: Scheduler, API Docs, Admin Auth, Deduplication, Retention chips
- "View Operations →" link from strip
- Fixed scheduler state display (`h.components?.scheduler` vs old broken `h.scheduler_running`)
- Empty state text improved ("No stations found" vs "Check API logs")

### Radio Stations (improved)
- Removed hardcoded static collection badges (Radiowave/iHeart/Manual CSV)
- Removed false "Auto-collected every 3 minutes" header text
- Added info box explaining source configuration approach
- Simplified table (removed phantom station ID column — stations API has no id field)

### Operations (new)
- System Configuration grid: Environment, Scheduler, API Docs, Admin Auth, Deduplication, Retention
- Collector Flags table: Capital, Nova, KIIS, Nightly Reconciliation with env var names
- Dynamic Production Guardrails section (only shows relevant warnings)
- Operational Reference section (what's safe vs what requires ops pass)
- No action buttons anywhere on the page

### App Shell (improved)
- Title: "TenX Radar — Admin Console"
- Sidebar brand: "TenX Radar / Radio Intelligence"
- Environment badge in sidebar header (hidden for dev, visible for prod/staging)
- Operations nav item under "System" section label
- Mobile hamburger toggle (sidebar-toggle button)
- Sidebar scrim overlay for mobile
- Improved ARIA attributes (modal roles, aria-live, aria-label on icon buttons)

---

## API Endpoints Used

| Endpoint | Pages |
|---|---|
| `GET /health` | Dashboard |
| `GET /stations` | Dashboard, Stations |
| `GET /review-items` | Dashboard, Review |
| `GET /webhooks` | Dashboard, Webhooks |
| `GET /api/admin/overview` | Dashboard (strip), Operations |

## API Endpoints Added

| Endpoint | Method | Returns | Notes |
|---|---|---|---|
| `/api/admin/overview` | GET | `AdminOverviewResponse` | Read-only, no secrets |

**AdminOverviewResponse fields:**
- `environment` — app_env string
- `is_production` — boolean
- `scheduler_enabled` — boolean
- `docs_exposed` — boolean (derived from env + flag)
- `admin_auth_enabled` — boolean (derived from user+password both set)
- `raw_payload_retention_days` — integer
- `retention_enabled` — boolean (derived: days > 0)
- `dedup_enabled` — always true
- `collector_flags.capital/nova/kiis/nightly_reconciliation` — booleans

**Secret exclusions verified:** No DATABASE_URL, API_KEY, admin password, SMTP credentials,
S3 secret key, or server paths in response.

---

## Tests Run and Results

| Suite | Before | After |
|---|---|---|
| `pytest tests/` | 348 passed, 2 skipped | 359 passed, 2 skipped |
| `ruff check` | Clean | Clean |

New tests (12): `tests/unit/test_admin_overview.py`
- `test_overview_returns_200`
- `test_overview_environment_key_present`
- `test_overview_scheduler_disabled_by_default`
- `test_overview_dedup_always_enabled`
- `test_overview_docs_exposed_in_development`
- `test_overview_admin_auth_disabled_by_default`
- `test_overview_retention_disabled_by_default`
- `test_overview_collector_flags_present`
- `test_overview_all_collectors_disabled_by_default`
- `test_overview_no_secret_fields`
- `test_overview_is_production_false_by_default`

---

## Safety Confirmation

| Check | Status |
|---|---|
| Scheduler not enabled | ✓ No change to SCHEDULER_ENABLED |
| Capital not enabled | ✓ No change to ENABLE_CAPITAL_COLLECTOR |
| Nova not enabled | ✓ No change to ENABLE_NOVA_COLLECTOR |
| KIIS not enabled | ✓ No change to ENABLE_KIIS_COLLECTOR |
| Nightly reconciliation not enabled | ✓ No change to ENABLE_NIGHTLY_RECONCILIATION |
| No secrets exposed | ✓ Test `test_overview_no_secret_fields` verifies |
| No destructive controls added | ✓ Operations page is read-only |
| No enable/disable buttons | ✓ No action buttons on Operations page |
| No raw payload delete buttons | ✓ None added |
| Existing routes unaffected | ✓ `/`, `/health`, `/admin/` all pass |

---

## Known Limitations

1. **Play events table not implemented** — requires `/play-events` endpoint (not on main)
2. **Collector health page not in this pass** — backend route on feature branch only
3. **Email reports page not in this pass** — backend route on feature branch only
4. **Migration version not displayed** — requires alembic introspection endpoint (deferred)
5. **Collector flags only show main-branch flags** — Z100, WKSC, BBC, Heart FM flags not on main
6. **No UI test for static files** — frontend correctness verified by manual inspection only

---

## Next Recommended Pass

**UIUX-REF2** — After `claude/sweet-archimedes-DFSWo` is merged into main:
- Expand Operations collector flags to include BBC Radio 1, Heart FM, Z100, WKSC, iHeart top-songs
- Add Collector Health page (route + UI)
- Add Play Events table (new read-only endpoint)
- Add Email Reports page integration
- Add Source Health detail view
- Consider migration version display endpoint

**UIUX-REF3** (later, high-risk):
- Raw payload evidence viewer (requires audit trail + access controls)
- Canary/dry-run reference commands (read-only display only)
- Rollback documentation panel
