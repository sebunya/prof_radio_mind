# Task Checklist — SEC-AUTH-1C

- [x] Phase 0: Local pre-deploy verification
  - [x] `git checkout main && git pull --ff-only origin main`
  - [x] Confirmed local main at `d5ec156` (PR #8 merge commit)
  - [x] `ruff check app/ tests/` — clean
  - [x] `mypy app/ --ignore-missing-imports` — clean
  - [x] `pytest tests/ -x` — 380 passed, 2 skipped

- [x] Phase 1: Production precheck (read-only)
  - [x] Confirmed production at `94194ab` (pre-patch)
  - [x] Confirmed `ADMIN_BASIC_AUTH_USER` and `ADMIN_BASIC_AUTH_PASSWORD` not present
  - [x] Confirmed all safety flags false
  - [x] Confirmed Alembic at `c4e2a1f9b8d7` (head)
  - [x] Confirmed all containers healthy

- [x] Phase 2: Pull merged code to production
  - [x] `git reset --hard origin/main` on server
  - [x] Confirmed production now at `d5ec156`
  - [x] Confirmed `_is_protected_admin_path` present in `app/core/admin_auth.py`

- [x] Phase 3: Generate and configure credentials (server-only)
  - [x] Generated `ADMIN_USER=tenxadmin`
  - [x] Generated `ADMIN_PASS=$(openssl rand -hex 32)` — never printed
  - [x] Written to `/root/tenx-admin-auth.txt` with `chmod 600`
  - [x] Updated `/opt/rmias/.env.production` via Python script
  - [x] Confirmed keys present (values hidden) in `.env.production`
  - [x] Confirmed safety flags unchanged

- [x] Phase 4: Rebuild and recreate app container
  - [x] `docker compose build --no-cache app` — image built successfully
  - [x] `docker compose up -d --force-recreate app` — container started healthy
  - [x] Confirmed auth env vars loaded in container (keys only, values hidden)
  - [x] Confirmed scheduler disabled in container
  - [x] Confirmed `/` and `/health` return `200` after recreate

- [x] Phase 5: Unauthenticated route verification
  - [x] `/` → `200` ✅
  - [x] `/health` → `200` ✅
  - [x] `/admin/` → `401` ✅
  - [x] `/admin/js/app.js` → `401` ✅
  - [x] `/admin/css/app.css` → `401` ✅
  - [x] `/api/admin/metadata-readiness` → `401` ✅
  - [x] `/api/admin/overview` → `401` ✅
  - [x] `/api/admin/source-health` → `401` ✅
  - [x] `/api/admin/operations` → `401` ✅
  - [x] `WWW-Authenticate` header confirmed on 401 responses

- [x] Phase 6: Authenticated route verification
  - [x] `/admin/` → `200` ✅
  - [x] `/admin/js/app.js` → `200` ✅
  - [x] `/admin/css/app.css` → `200` ✅
  - [x] `/api/admin/metadata-readiness` → `200` ✅
  - [x] `/api/admin/overview` → `200` ✅
  - [x] `/api/admin/source-health` → `200` ✅
  - [x] `/api/admin/operations` → `200` ✅

- [x] Phase 7: Response safety and post-hardening checks
  - [x] Metadata readiness response structure confirmed (disabled/readiness_only)
  - [x] No secrets in API response
  - [x] Safety flags unchanged after hardening
  - [x] App logs clean — no errors, no scheduler/collector/enrichment activity
  - [x] Alembic still at `c4e2a1f9b8d7` (head) — no migrations applied

- [x] Phase 8: Documentation
  - [x] `docs/passes/SEC-AUTH-1C-deploy-admin-auth.md` created
  - [x] `docs/passes/SEC-AUTH-1C-task.md` created
  - [x] Committed and pushed to `main`

- [ ] PENDING: User retrieves credentials from server
- [ ] PENDING: User completes manual browser UI QA
- [ ] BLOCKED: METADATA-1-PLAN (requires manual UI QA confirmation)
