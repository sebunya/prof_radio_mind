# RECON-2A Task — PR #3 Branch Hygiene, Contamination Check and Extraction Plan

**Date:** 2026-06-04  
**Branch:** `docs/recon-2a-pr3-extraction-plan`  
**Status:** COMPLETE — see `RECON-2A-pr3-branch-hygiene-and-extraction-plan.md`

---

## Objective

Audit `claude/sweet-archimedes-DFSWo` (PR #3) after `main` stabilised at `1ec18c00`  
(post PR #9 UIUX merge). Decide the safest way to adopt only the valuable remaining work.

---

## Hard Safety Rules

- Do NOT rebase PR #3 wholesale
- Do NOT merge PR #3
- Do NOT cherry-pick yet
- Do NOT deploy
- Do NOT start new feature work
- Do NOT touch Spotify/worker branches
- Do NOT start METADATA-1 or MusicBrainz
- Do NOT commit code in this pass

---

## Checklist

- [x] main synced to origin
- [x] main tests run (390 passed, 2 skipped)
- [x] PR #9 merge confirmed in main (`1ec18c00`)
- [x] REF-0 baseline checked (dry_run_capital, prune_raw_payloads, rollback-capital)
- [x] SEC-AUTH-1B baseline checked (28/28 auth tests pass)
- [x] UIUX/metadata readiness baseline checked (operations-guardrails, play-events, spotify-metadata)
- [x] POST-MERGE-STABILITY docs contamination checked
- [x] PR #3 inspected read-only (fetch, log, diff stat, files)
- [x] All 40 unique PR #3 commits classified
- [x] Migration chain analysed (11 migrations, complex branch+merge DAG)
- [x] Static safety scan run (no unsafe flags, no secrets, no live-enable code)
- [x] Extraction strategy selected (Option A — close PR #3, extract via smaller PRs)
- [x] First extraction slice defined (parser + collector library, no migrations)
- [x] Docs created
- [x] No production changes made
- [x] No code committed in this pass

---

## Questions Answered

| # | Question | Answer |
|---|----------|--------|
| 1 | Is `main` still clean after PR #9 merge? | YES — 390/2, ruff, mypy all green |
| 2 | Where is POST-MERGE-STABILITY-1 doc? | On `claude/sweet-archimedes-DFSWo` only |
| 3 | Was that doc accidentally committed to PR #3? | YES — contamination confirmed |
| 4 | Is PR #3 contaminated? | YES — top 2 commits are docs-only |
| 5 | What commits are unique to PR #3? | 40 commits |
| 6 | Which are already merged/superseded? | ~8 (old UI, old CORS fix that's now in main differently) |
| 7 | Which are still valuable? | Parser/collector library (~10 commits) |
| 8 | Which are risky? | Migration chain (11 files), scheduler changes, main.py changes |
| 9 | Which PR #3 files conflict with main? | scheduler.py, main.py, app/static/*, settings.py |
| 10 | PR #3 strategy? | **Option A — close, extract via smaller PRs** |
| 11 | Smallest safe first extraction slice? | Parser + collector library (no migrations) |
| 12 | Exact next branch and pass? | `feat/recon2-parser-collector-library` via EXTRACT-1 pass |
