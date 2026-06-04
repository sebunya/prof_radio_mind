# Security Hotfix Report — SEC-AUTH-1B

## Pass Name
SEC-AUTH-1B — Surgical Admin API Auth Coverage Patch

## 1. Why This Pass Was Needed

After deploying the `UIUX-METADATA-AG1` Metadata Enrichment Readiness Admin UI (PR #7, commit `94194ab`), a production security audit in pass `SEC-AUTH-1` confirmed that the admin REST API surface at `/api/admin/*` was publicly accessible without credentials.

The root cause is a path-prefix mismatch in the existing `AdminBasicAuthMiddleware`:
* The middleware checked `request.url.path.startswith("/admin")`.
* The admin SPA is mounted at `/admin`, so its static assets are protected.
* The admin JSON API router is mounted at prefix `/api/admin` (not `/admin`).
* Therefore, `/api/admin/metadata-readiness`, `/api/admin/overview`, etc. were never intercepted by the middleware and remained public, even when credentials would have been configured.

Additionally, `ADMIN_BASIC_AUTH_USER` and `ADMIN_BASIC_AUTH_PASSWORD` were never set in production, so the middleware was also disabled entirely.

---

## 2. Contradiction Resolved (from Previous Reports)

| Report | Claim | Truth |
|:---|:---|:---|
| `DEPLOY-UIUX-METADATA-AG1-production-deploy.md` | "Basic authentication is active on the `/admin/` root path" | **Incorrect.** No credentials were set; middleware was disabled. |
| `POSTDEPLOY-UIUX-METADATA-AG1-qa.md` | "Serves HTTP 200 to unauthenticated curl requests because Basic Auth is currently unconfigured" | **Correct on both counts.** No credentials AND code gap. |

Even if credentials had been configured at time of deployment, the `/api/admin/*` routes would have remained public due to the code path guard only checking `/admin` prefix.

---

## 3. Root Cause (Technical)

**File**: `app/core/admin_auth.py`

**Before (original guard)**:
```python
if not self._enabled or not request.url.path.startswith("/admin"):
    return await call_next(request)
```

**Why this failed**:
- `/api/admin/metadata-readiness` does NOT start with `/admin`
- It starts with `/api/admin` — a completely different prefix
- The middleware let it pass through unconditionally

---

## 4. The Patch

**File changed**: `app/core/admin_auth.py`

A boundary-safe helper function `_is_protected_admin_path` was added before the class definition:

```python
def _is_protected_admin_path(path: str) -> bool:
    """Return True for paths that require Basic auth credentials.

    Guards both the /admin SPA and the /api/admin JSON routes.
    Boundary-safe: requires an exact match or an immediately following '/'
    so that paths like /administrator or /api/administer are never matched.
    """
    return (
        path == "/admin"
        or path.startswith("/admin/")
        or path == "/api/admin"
        or path.startswith("/api/admin/")
    )
```

The middleware dispatch guard was updated to use this helper:

```python
# BEFORE
if not self._enabled or not request.url.path.startswith("/admin"):

# AFTER
if not self._enabled or not _is_protected_admin_path(request.url.path):
```

**Why boundary-safe matters**: Loose `startswith(("/admin", "/api/admin"))` would accidentally protect paths like `/administrator`, `/administrator/settings`, `/api/administer`. The helper uses either exact match or a `/`-prefixed check.

---

## 5. Files Changed

| File | Change Type | Description |
|:---|:---|:---|
| `app/core/admin_auth.py` | Modified | Added `_is_protected_admin_path` helper; updated middleware dispatch guard. |
| `tests/unit/test_admin_auth.py` | Modified | Expanded from 5 tests to 28 tests covering the helper, `/api/admin/*` protection, auth success/rejection, and public route invariants. |
| `docs/passes/SEC-AUTH-1B-admin-api-auth-patch.md` | New | This document. |
| `docs/passes/SEC-AUTH-1B-task.md` | New | Task checklist. |

No other files were changed.

---

## 6. Tests Added

### Path Helper Tests (14)
- Protected: `/admin`, `/admin/`, `/admin/js/app.js`, `/api/admin`, `/api/admin/metadata-readiness`, `/api/admin/overview`, `/api/admin/source-health`
- Not protected: `/`, `/health`, `/api/stations`, `/administrator`, `/administrator/settings`, `/api/administrator`, `/api/administer`

### Middleware Integration Tests (14)
- Unauthenticated `/admin/*` returns `401` when credentials set.
- Unauthenticated `/api/admin/metadata-readiness` returns `401` when credentials set.
- Unauthenticated `/api/admin/overview` returns `401` when credentials set.
- Authenticated `/admin/*` returns `200`.
- Authenticated `/api/admin/metadata-readiness` returns `200`.
- Authenticated `/api/admin/overview` returns `200`.
- Wrong credentials rejected: `/admin/*` and `/api/admin/*` both return `401`.
- `/` and `/health` remain `200` even when credentials configured.
- `/api/stations` remains `200` even when credentials configured.
- Open-by-default preserved when no credentials set (backward compat).

---

## 7. Quality Gate Results

| Gate | Result |
|:---|:---|
| `ruff check app/core/admin_auth.py tests/unit/test_admin_auth.py` | ✅ All checks passed (1 import order auto-fixed) |
| `mypy app/ --ignore-missing-imports` | ✅ Success: no issues found in 116 source files |
| `pytest tests/unit/test_admin_auth.py` | ✅ 28/28 passed |
| `pytest tests/unit/test_admin_api.py tests/unit/test_api.py tests/unit/test_auth.py tests/unit/test_scheduler.py` | ✅ 38/38 passed |
| `ruff check app/ tests/` | ✅ All checks passed |
| `pytest tests/ -x` | ✅ 380 passed, 2 skipped, 0 failures |

---

## 8. Safety Confirmations

* No database migrations applied.
* No Docker changes.
* No docker-compose changes.
* No production `.env.production` changes.
* No secrets committed.
* No scheduler, collector, or enrichment flags changed.
* No MusicBrainz, Spotify, or Cover Art Archive live calls.
* No production server state changed.
* No data was deleted or reset.

---

## 9. Deployment Steps Required After PR Merge

This code patch alone does not enable auth in production. After the PR is merged, a separate pass `SEC-AUTH-1C` must:

1. Pull latest `main` to production server.
2. Rebuild the app image (code change requires rebuild).
3. Generate server-only admin credentials (`openssl rand -hex 32`).
4. Store credentials at `/root/tenx-admin-auth.txt` with `chmod 600`.
5. Update `/opt/rmias/.env.production` with `ADMIN_BASIC_AUTH_USER` and `ADMIN_BASIC_AUTH_PASSWORD` (server-only, never committed).
6. Force-recreate the app container to load new env.
7. Verify unauthenticated routes return `401`.
8. Verify authenticated routes return `200`.
9. Verify `/` and `/health` remain `200` publicly.

---

## 10. Manual UI QA Status

Manual browser UI QA remains pending until SEC-AUTH-1C is complete and credentials are available for the user to log in.

---

## 11. METADATA-1 Planning Gate

METADATA-1 planning is blocked until:
1. SEC-AUTH-1B is merged. ← This PR.
2. SEC-AUTH-1C is deployed and verified.
3. Manual browser UI QA is confirmed by the user.
