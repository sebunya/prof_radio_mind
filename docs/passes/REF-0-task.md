# REF-0 Task

**Pass:** REF-0 — Post-AntiGravity Production Refactor Audit and Stabilisation  
**Status:** COMPLETE — SAFE FIXES APPLIED  
**Branch:** `chore/post-antigravity-refactor-audit`  
**Audited commit:** `5651799`

## What was done

Audited the entire codebase after multiple AntiGravity-generated passes. Found and fixed 5 real bugs. Created full audit document.

## Fixes

1. **Alembic % URL escaping** (`migrations/env.py`) — passwords with URL-encoded characters (e.g. `%40`) would crash Alembic migrations with `InterpolationSyntaxError`. Fixed.
2. **Rollback script silent failure** (`scripts/rollback-capital.sh`) — `docker compose restart` does not reload env vars. Changed to `up -d --force-recreate`. The old script was effectively a no-op for disabling Capital.
3. **Dry-run packaging** (`app/tools/dry_run_capital.py`) — dry-run script was not in the Docker image, requiring fragile `docker cp` workaround. Created as a proper module: `docker exec rmias-app-1 python -m app.tools.dry_run_capital`.
4. **Deduplication gap** (`app/infrastructure/scheduler/scheduler.py`) — `_persist_result` saved play events without checking for recent duplicates. Capital FM's 15-minute polling of the same now-playing song would create multiple identical events. Fixed with `exists_by_fingerprint(within_seconds=1800)` check.
5. **HTTP client comment** (`app/infrastructure/http/client.py`) — evasion-adjacent language removed.

## Follow-up fixes (approved, applied)

All four open risks were approved and remediated (env-gated, default = current behaviour):

- **`/docs` exposure** → hidden when `APP_ENV=production` (force on with `ENABLE_DOCS_IN_PRODUCTION=true`). Verified: 404 in prod.
- **`/admin/` exposure** → optional HTTP Basic auth (`AdminBasicAuthMiddleware`), enabled only when `ADMIN_BASIC_AUTH_USER` + `ADMIN_BASIC_AUTH_PASSWORD` both set. Default keeps `/admin` open so the live SPA never breaks.
- **DB duplicate guard** → migration `c4e2a1f9b8d7` (Phase E): non-destructive — flags existing dupes `is_duplicate=true`, then partial unique index on `(station_id, fingerprint, played_at) WHERE is_duplicate=false`. Backstop to the app-level 30-min window. Apply with `alembic upgrade head` on deploy.
- **Raw payload growth** → `app/tools/prune_raw_payloads.py`, gated by `RAW_PAYLOAD_RETENTION_DAYS` (0 = off). Run via `docker exec ... python -m app.tools.prune_raw_payloads`.

## Still open (not code)

- Docker runs as root on host → infra (rootless Docker / deploy user)
- CAP-4 canary completion → verify prod flags before resuming

## Tests

348 passed, 0 failed. Ruff clean. Mypy clean.

> Note: the Phase E migration was NOT applied to a live DB in this pass — no
> Postgres/Docker was runnable in the audit sandbox. The revision chain
> validates to a single linear head and the SQL was reviewed. Apply on deploy.
