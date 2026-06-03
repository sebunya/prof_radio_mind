# PASS: AG-ADOPT-REF0 — Claude Code REF-0 Refactor Branch Adoption Report

This report documents the local verification and adoption of the Claude Code `REF-0` refactor branch.

## 1. Verdict

> [!IMPORTANT]
> **ADOPTED LOCALLY — PR #6 READY FOR REVIEW**
> 
> All branch fixes have been verified locally, tests pass with `348 passed, 2 skipped`, static scanning checks pass cleanly, and the production server has been placed in freeze state. We are ready to merge PR #6 and proceed with deployment upon explicit approval.

---

## 2. Production Safety & Freeze Check

* **Canary Active Check**: An active scheduler container was found running with `SCHEDULER_ENABLED=true` inside the app container, although the Capital collector had been set to false on disk (the rollback script failed to reload the running container).
* **Rollback Action**: Completed. The rollback script was executed, followed by an explicit `docker compose up -d --force-recreate app` execution to force reload the container with the environment variables.
* **Final Flags State**:
  * `SCHEDULER_ENABLED=false`
  * `ENABLE_CAPITAL_COLLECTOR=false`
  * `ENABLE_NOVA_COLLECTOR=false`
  * `ENABLE_KIIS_COLLECTOR=false`
  * `ENABLE_NIGHTLY_RECONCILIATION=false`
* **Liveness**: Confirmed that `/` and `/health` remain fully responsive (returning HTTP/2 200).

---

## 3. Branch & PR Verification

* **Branch Name**: `chore/post-antigravity-refactor-audit`
* **PR Link**: [PR #6](https://github.com/sebunya/prof_radio_mind/pull/6)
* **Head Commit**: `c2b150b`
* **Top 3 Commits**:
  1. `c2b150b` ci: wire CI + Semgrep + Snyk onto this branch so PR #6 is validated
  2. `2b50681` REF-0 follow-up: remediate the 4 open audit risks (env-gated, safe defaults)
  3. `5c0476b` REF-0: post-AntiGravity audit — 5 surgical fixes, 12 new tests

---

## 4. File-Level Adoption Summary

The changes on the refactor branch compared to `main` comprise 27 files:

| Category | Files |
| :--- | :--- |
| **Migration/Database** | `migrations/env.py`, `migrations/versions/c4e2a1f9b8d7_phase_e_play_events_dedup_index.py` |
| **App Gating/Security** | `app/core/admin_auth.py`, `app/core/settings.py`, `app/main.py` |
| **Scheduler/Collector** | `app/infrastructure/scheduler/scheduler.py`, `app/infrastructure/http/client.py` |
| **Tools/Scripts** | `app/tools/__init__.py`, `app/tools/dry_run_capital.py`, `app/tools/prune_raw_payloads.py`, `scripts/dry_run_capital.py`, `scripts/rollback-capital.sh` |
| **Env Templates** | `.env.example`, `.env.production.example` |
| **Tests** | `tests/unit/test_admin_auth.py`, `tests/unit/test_docs_gating.py`, `tests/unit/test_dry_run_module.py`, `tests/unit/test_migrations_env_url.py`, `tests/unit/test_persist_result_dedup.py`, `tests/unit/test_prune_raw_payloads.py` |
| **CI/Workflows** | `.github/workflows/ci.yml`, `.github/workflows/semgrep.yml`, `.github/workflows/snyk.yml`, `.semgrep/rules.yml`, `.snyk` |
| **Documentation** | `docs/passes/REF-0-post-antigravity-refactor-audit.md`, `docs/passes/REF-0-task.md` |

---

## 5. Fix Verification Analysis

* **Alembic URL Safety**: Verified that `migrations/env.py` replaces `%` with `%%` on line 24. This ensures that URL-encoded DB passwords containing `%` characters do not cause configparser interpolation crashes.
* **Rollback Correctness**: Verified that `scripts/rollback-capital.sh` uses `up -d --force-recreate app` instead of a simple container restart, ensuring that modifications to `.env.production` are reloaded.
* **Dry Run as Module**: Verified that `app/tools/dry_run_capital.py` is invoked using `python -m app.tools.dry_run_capital`. It executes a single fetch-parse-persist run without starting APScheduler or altering environment variables, and properly masks DB credentials.
* **Scheduler Deduplication**: Verified that `app/infrastructure/scheduler/scheduler.py` uses `exists_by_fingerprint(within_seconds=1800)` to prevent duplicate play events within a 30-minute window (double the Capital FM UK poll interval).
* **Production Docs Gating**: Swagger/Redoc endpoints are hidden by default in production. Setting `ENABLE_DOCS_IN_PRODUCTION=true` restores them.
* **Optional Admin Basic Auth**: `AdminBasicAuthMiddleware` in `app/core/admin_auth.py` is fail-safe; it is active only when both `ADMIN_BASIC_AUTH_USER` and `ADMIN_BASIC_AUTH_PASSWORD` env variables are set.
* **Phase E Database Migration**: The migration `c4e2a1f9b8d7` flags historical duplicates with `is_duplicate = true` (keeping the earliest per group) and adds a partial unique index where `is_duplicate = false` and `fingerprint IS NOT NULL`. It is completely non-destructive and doesn't delete database rows.
* **Raw Payload Pruning**: The tool `app/tools/prune_raw_payloads.py` deletes payload files older than `RAW_PAYLOAD_RETENTION_DAYS` (default `0` = disabled) and deletes empty subdirectories.
* **CI Workflows**: Workflows for build tests (Pytest/Ruff/Mypy), Semgrep, and Snyk are correctly wired to branch/PR triggers.

---

## 6. Local Quality Gates & Static Checks

* **Ruff**: Passed cleanly.
* **Mypy**: Passed cleanly (`Success: no issues found in 115 source files`).
* **Pytest**: `348 passed, 2 skipped` in 1.50s.
* **Static Risk Searches**:
  * Grepped for hardcoded `SCHEDULER_ENABLED=true`, `ENABLE_*_COLLECTOR=true` (none found).
  * Grepped for `git add .` instructions (none found).
  * Grepped for evasive/bypass scraping terminology (none found).
  * Checked that `.env.production` is untracked and no credentials/secrets are committed.

---

## 7. Status and Next Steps

* **PR #6 Status**: Open and fully verified.
* **Deployment Status**: Skipped (waiting for PR merge approval).
* **Phase E Database Migration**: Not yet applied (will be applied on deployment via `alembic upgrade head`).
* **Remaining Risks**:
  * Root ssh deployment user is still in use.
  * Basic auth for admin is optional and needs to be explicitly configured.
  * Raw payload pruning defaults to off unless retention is configured.
  * Nova/KIIS collectors remain disabled and unvalidated for production.

### Next Recommended Pass
1. Review and Merge PR #6 via GitHub UI.
2. Deploy the changes from `main` to the production server.
3. Apply migration: `alembic upgrade head`.
4. Validate that production `/health` is healthy and the DB migration matches head.
5. Resume `CAP-4` monitored canary enablement on the updated codebase.
