# Task Checklist — DEPLOY-UIUX-METADATA-AG1

- [x] Phase 0: Pre-deployment Local Verification
  - [x] Fast-forward local `main` with merged `feat/uiux-spotify-ag1` branch
  - [x] Verify PR commits exist on `main` (commit `74ec384` and `017eacd`)
  - [x] Run local quality gates (`ruff`, `mypy`, `pytest` full suite)
- [x] Phase 1: Production Pre-check
  - [x] Run SSH precheck to check current commit, environment switches, and DB migration version
  - [x] Confirm all safety flags (scheduler, collectors, enrichment) are disabled
- [x] Phase 2: Pull and Rebuild App
  - [x] SSH and pull remote `main` branch to reset hard
  - [x] Rebuild `app` container via docker compose
  - [x] Confirm healthy startup states
- [x] Phase 3: Post-deployment Validation
  - [x] Check liveness endpoints and metadata API responses
  - [x] Confirm no migrations were applied (db schema stable at `c4e2a1f9b8d7`)
  - [x] Verify API JSON safety (no secrets, no active triggers, correct readiness mode)
- [x] Phase 4: Documentation & Wrap-up
  - [x] Draft `DEPLOY-UIUX-METADATA-AG1-production-deploy.md` report
  - [x] Stage and commit deployment documentation to `main`
