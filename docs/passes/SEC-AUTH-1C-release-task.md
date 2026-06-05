# SEC-AUTH-1C-RELEASE-DEPLOY Task Checklist

**Date:** 2026-06-05  
**Pass:** SEC-AUTH-1C-RELEASE-DEPLOY  
**Status:** COMPLETE — see `SEC-AUTH-1C-release-deploy-admin-auth.md`

---

## Objective

Deploy latest stable `main` (`8c07b9b`) to production and rotate server-only admin credentials.
Previous production was at `d5ec156` (PR #8 only). This pass brings it to `8c07b9b` (PR #8 + PR #9 + PR #11).

---

## Hard Rules

- No migrations applied
- No scheduler enabled
- No collectors enabled
- No enrichment enabled
- No source/station seeds
- No secrets committed
- No `git add .`
- No force-push to main
- No deployment from feature branch
- Deploy from `origin/main` only
- Credentials stored server-side only (`/root/tenx-admin-auth.txt`)

---

## Checklist

### Local Verification
- [x] Local main at `8c07b9b`, clean working tree
- [x] Ruff: clean
- [x] Mypy: clean (124 source files)
- [x] Full test suite: 492 passed, 2 skipped
- [x] SEC-AUTH-1B present — `_is_protected_admin_path` covers `/admin/*` and `/api/admin/*`
- [x] False-positive guards confirmed — `/administrator` not caught
- [x] 5 new collector flags all default `False`
- [x] Extracted collectors confirmed NOT wired into scheduler
- [x] Zero migration files in `1ec18c00..8c07b9b` range
- [x] Alembic chain on main: `c4e2a1f9b8d7` (head) — no change required

### Production Execution (requires SSH from local machine)
- [x] Phase 5: Read-only precheck — production at `d5ec156`, all safety flags false, alembic at head
- [x] Phase 6: `git reset --hard origin/main` on server; `docker compose up -d --build app`; health = `200`
- [x] Phase 7: Credentials rotated; `/root/tenx-admin-auth.txt` written with `chmod 600`
- [x] Phase 8: `docker compose up -d --force-recreate app`; auth env loaded; health = `200`
- [x] Phase 9: Unauthenticated routes — `/` and `/health` = `200`; all `/admin*` = `401`
- [x] Phase 10: Authenticated routes — all `/admin*` = `200`
- [x] Phase 11: Metadata readiness response — no secret leakage
- [x] Phase 12: All safety/collector flags `false` in container; logs clean
- [x] Phase 13: 5-minute passive observation — health and auth stable; logs clean

### Post-Deploy
- [x] User retrieves credentials: `ssh ... 'cat /root/tenx-admin-auth.txt'`
- [x] User completes manual browser UI QA at `https://tenxradar.com/admin/`
- [x] UNBLOCKED: `EXTRACT-1B` draft PR opened — `feat/recon2-scheduler-collector-wiring`
