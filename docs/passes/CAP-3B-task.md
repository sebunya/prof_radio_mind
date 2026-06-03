# CAP-3B Task Checklist

- [x] Create the one-shot dry-run script `scripts/dry_run_capital.py`
- [x] Verify imports formatting and line lengths (Ruff & Mypy Success)
- [x] Run pytest locally to verify tests pass (All 321 tests pass)
- [x] Push script to GitHub origin main
- [x] Pull latest commit on Hetzner server
- [x] Rebuild and restart the production application container
- [x] Copy dry-run script into production container
- [x] Run one-shot production dry run
- [x] Log execution outputs (crawling target, http code 200, parsed track)
- [x] Confirm no scheduler started and no safety flags modified
- [x] Confirm database play_event record created correctly
- [x] Confirm / and /health remain HTTP 200
- [x] Write dry-run report `docs/passes/CAP-3B-capital-one-shot-production-dry-run.md`
