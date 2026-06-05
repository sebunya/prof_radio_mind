# VAL-COLLECTORS-1 — Production Validation Task

**Date:** 2026-06-05
**Pass:** VAL-COLLECTORS-1
**Status:** PENDING — awaiting EXTRACT-2 production deployment

---

## Objective

Confirm that the EXTRACT-2 deployment (station/source seeds for BBC Radio 1, Heart FM UK,
Z100, WKSC) landed correctly in production and that no collectors, scheduler, or enrichment
are enabled. This is a read-only passive check — no changes are made to production.

---

## Hard Rules

- Do not enable any collector flag
- Do not enable the scheduler
- Do not run live provider calls (no BBC, Heart, iHeart, Spotify, MusicBrainz)
- Do not apply or run migrations
- Do not modify `.env.production`
- Do not run source seeding manually
- Do not use `git add .`
- Do not force-push main

---

## What the Script Checks

| Section | Check | Expected |
|---------|-------|----------|
| 1. Deployment version | git HEAD contains EXTRACT-2 merge commit `0f6049b` | PASS |
| 2. Container status | app container running | PASS |
| 3. Safety flags | 15 flags all false/absent | PASS (all false) |
| 4. HTTP health | `GET /` → 200, `GET /health` → 200 | 200 |
| 4. Auth protection | `GET /admin/` → 401, `/api/admin/overview` → 401, `/api/admin/metadata-readiness` → 401 | 401 |
| 4. Auth header | `WWW-Authenticate: Basic realm` present on 401 | PASS |
| 5. Migration version | `alembic_version` = `c4e2a1f9b8d7` | PASS |
| 6. Station count | `SELECT COUNT(*) FROM stations` ≥ 7 | PASS |
| 6. Original stations | NOVA969, KIISFM, CAPITALFM — FOUND | PASS |
| 6. EXTRACT-2 stations | BBCRADIO1, HEARTFMUK, WHTZ, WKSC — FOUND | PASS |
| 6. EXTRACT-2 sources | bbc_sounds, heart_last_played, iheart×2 — FOUND | PASS |
| 7. Collector imports | 9 collectors importable, no missing modules | PASS |
| 7. Parser imports | 5 parsers importable, no missing modules | PASS |
| 7. Scheduler import | `build_scheduler` importable | PASS |
| 8. Scheduler state | No "scheduler start/running" in recent logs | PASS |
| 9. Log scan — errors | No ERROR/CRITICAL/Traceback in last 80 lines | PASS |
| 9. Log scan — activity | No extracted-collector job output in logs | PASS |
| 9. Seeder | `seeder complete` present in recent logs | INFO |

---

## How to Run

From your Mac, after EXTRACT-2 is deployed and app restarted:

```bash
ssh -o IdentitiesOnly=yes -i ~/.ssh/id_ed25519 root@178.105.238.18 'bash -s' \
    < ~/Documents/Prof_Mind/docs/passes/val-collectors-1-dryrun.sh \
    | tee /tmp/val-collectors-1.log
```

Review the log. Report only the summary line:

```
SUMMARY: N passed, N failed
```

If any check fails, do not proceed to collector enablement.

---

## Checklist

### Pre-Run
- [ ] EXTRACT-2 deployed — `git reset --hard origin/main` on server, `docker compose up -d --build app`
- [ ] App restarted and health = 200

### Script Execution
- [ ] Script runs without error
- [ ] Section 1 — git version: PASS
- [ ] Section 2 — container running: PASS
- [ ] Section 3 — all 15 safety flags false: PASS
- [ ] Section 4 — `/` and `/health` = 200: PASS
- [ ] Section 4 — `/admin/` and `/api/admin/*` = 401 unauth: PASS
- [ ] Section 4 — `WWW-Authenticate: Basic realm` on 401: PASS
- [ ] Section 5 — alembic head = `c4e2a1f9b8d7`: PASS
- [ ] Section 6 — station count ≥ 7: PASS
- [ ] Section 6 — original 3 stations FOUND: PASS
- [ ] Section 6 — 4 EXTRACT-2 stations FOUND: PASS
- [ ] Section 6 — 4 EXTRACT-2 primary sources FOUND: PASS
- [ ] Section 7 — all collector/parser/scheduler imports: PASS
- [ ] Section 8 — scheduler not running: PASS
- [ ] Section 9 — no errors in logs: PASS
- [ ] Section 9 — no extracted-collector activity: PASS
- [ ] SUMMARY: N passed, 0 failed

### Post-Validation
- [ ] Report summary to Claude
- [ ] BLOCKED until SUMMARY: 0 failed — do not enable any collector flag

---

## Next Step After This Pass

Only after all checklist items are marked complete:

Proceed to per-collector live validation (one at a time, separate pass per collector):
- `VAL-BBC1-001` — BBC Radio 1 live endpoint reachability (separate pass)
- `VAL-BBC1-006` — BBC ToS manual review (separate pass)
- `VAL-HEARTFM-002` — Heart FM live CSS selectors (separate pass)
- `VAL-Z100-001` — Z100 iHeart live endpoint (separate pass)
- `VAL-WKSC-001` — WKSC iHeart live endpoint (separate pass)
- `VAL-IHEART-TOP-001` — KIIS top songs live endpoint (separate pass)

Each live validation pass is a separate task. None are included in this script.
