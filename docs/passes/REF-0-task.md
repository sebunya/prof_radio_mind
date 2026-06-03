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

## Risks still open (need approval)

- `/docs` publicly accessible → disable in production
- `/admin/` publicly accessible → protect via Cloudflare Access
- No DB-level unique constraint on `play_events` → REF-1
- Raw payload disk growth → add retention after CAP-4 stabilises

## Tests

333 passed, 0 failed. Ruff clean. Mypy clean.
