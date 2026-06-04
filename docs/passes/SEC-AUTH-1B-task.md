# Task Checklist — SEC-AUTH-1B

- [x] Phase 1: Create hotfix branch from main
  - [x] `git fetch origin && git checkout main && git pull --ff-only origin main`
  - [x] `git checkout -b fix/sec-auth-1b-admin-api-auth`
  - [x] Confirmed clean working tree before changes

- [x] Phase 2: Inspect current auth file
  - [x] Confirmed middleware guard only checked `startswith("/admin")`, not `/api/admin`
  - [x] Confirmed admin API router uses `prefix="/api/admin"` (not `/admin`)
  - [x] Root cause documented

- [x] Phase 3: Patch path guard in `app/core/admin_auth.py`
  - [x] Added `_is_protected_admin_path` boundary-safe helper function
  - [x] Updated `dispatch()` guard to use helper
  - [x] Confirmed no changes to credential logic, enable/disable logic, or error response

- [x] Phase 4: Add focused tests in `tests/unit/test_admin_auth.py`
  - [x] 14 path helper tests (protected + not-protected boundary cases)
  - [x] Unauthenticated `/admin/*` and `/api/admin/*` return `401` when configured
  - [x] Authenticated success on both `/admin/*` and `/api/admin/*`
  - [x] Wrong credential rejection on both prefixes
  - [x] `/`, `/health`, `/api/stations` remain public
  - [x] Open-by-default preserved when no credentials set

- [x] Phase 5: Quality gates
  - [x] `ruff check` — PASSED (1 import order auto-fixed)
  - [x] `mypy app/ --ignore-missing-imports` — PASSED (116 files clean)
  - [x] `pytest tests/unit/test_admin_auth.py` — 28/28 PASSED
  - [x] `pytest tests/unit/test_admin_api.py tests/unit/test_api.py ...` — 38/38 PASSED
  - [x] `ruff check app/ tests/` — PASSED
  - [x] `pytest tests/ -x` — 380 passed, 2 skipped, 0 failures

- [x] Phase 6: Static safety search
  - [x] No unsafe enabled flags in committed code
  - [x] No secrets committed
  - [x] `DATABASE_URL` only in .env.example templates
  - [x] No `git add .` in executable scripts or CI

- [x] Phase 7: Documentation
  - [x] `docs/passes/SEC-AUTH-1B-admin-api-auth-patch.md` created
  - [x] `docs/passes/SEC-AUTH-1B-task.md` created

- [x] Phase 8: Diff review
  - [x] Only 4 files changed (admin_auth.py, test_admin_auth.py, two docs)

- [x] Phase 9: Commit and push hotfix branch
  - [x] Staged exact files only (no `git add .`)
  - [x] Committed with `fix(auth): protect admin API with basic auth`
  - [x] Pushed to `origin fix/sec-auth-1b-admin-api-auth`

- [x] Phase 10: PR created
  - [x] Base: `main`
  - [x] Head: `fix/sec-auth-1b-admin-api-auth`

- [ ] PENDING: User reviews and approves PR for merge
- [ ] PENDING: SEC-AUTH-1C — Deploy Auth Patch and Configure Production Credentials
- [ ] PENDING: Manual Browser UI QA
- [ ] BLOCKED: METADATA-1-PLAN (requires above items complete)
