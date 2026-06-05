# EXTRACT-1 — Parser and Collector Library Extraction Report

**Date:** 2026-06-04  
**Pass:** EXTRACT-1  
**Branch:** `feat/recon2-parser-collector-library`  
**Source branch:** `claude/sweet-archimedes-DFSWo` (PR #3)  
**Base:** `main` at `1ec18c00`  
**Verdict:** `EXTRACT-1 COMPLETE — PR READY`

---

## 1. Why This Extraction Was Needed

PR #3 (`claude/sweet-archimedes-DFSWo`) contains 40 unique commits and 136 changed files against current `main`, including 11 unapplied database migrations. It cannot be safely rebased wholesale due to:

- Migration Phase E conflict (2-column vs 3-column dedup index design)
- `main.py` changes intertwined with Sentry, CORS, and email router
- `scheduler.py` changes intertwined with email reporting system
- UI changes superseded by PR #9
- Documentation contamination (RECON-1 and POST-MERGE-STABILITY-1 docs at HEAD)

RECON-2A identified the parser/collector library as the safest first extraction slice: pure Python logic, tested via fixtures, no database requirements.

---

## 2. Approach: Manual File Porting (Not Cherry-Pick)

Every file was individually inspected with `git show origin/claude/sweet-archimedes-DFSWo:<path>` before porting. No commits were cherry-picked wholesale. Forbidden file categories (migrations, UI, scheduler, seeds, deployment) were explicitly excluded at every step.

---

## 3. Files Extracted

### New Parser Files
| File | Description |
|------|-------------|
| `app/infrastructure/parsers/bbc_sounds.py` | BBC Sounds RMS API JSON parser |
| `app/infrastructure/parsers/heart.py` | Heart FM last-played-songs HTML parser |

### Modified Parser Files
| File | Change |
|------|--------|
| `app/infrastructure/parsers/iheart.py` | Added `parse_iheart_recently_played()`, `parse_iheart_top_songs()`, `IHeartTopSongResult` dataclass; millisecond timestamp guard |
| `app/infrastructure/parsers/radiowave.py` | Added `station_timezone` parameter (default `Australia/Sydney`); enables KIIS-FM LA timezone support |

### New Collector Files
| File | Description |
|------|-------------|
| `app/infrastructure/collectors/iheart_now_playing.py` | Generic iHeart now-playing (any station via station ID) |
| `app/infrastructure/collectors/iheart_recently_played.py` | Generic iHeart recently-played batch collector |
| `app/infrastructure/collectors/iheart_top_songs.py` | Generic iHeart top-songs chart collector |
| `app/infrastructure/collectors/bbc_radio_1.py` | BBC Radio 1 via BBC Sounds RMS API |
| `app/infrastructure/collectors/heart_radio.py` | Heart FM last-played-songs page |
| `app/infrastructure/collectors/kiis_radiowave.py` | KIIS-FM 102.7 via Radiowave Monitor (LA timezone) |

### Modified Collector Files
| File | Change |
|------|--------|
| `app/infrastructure/collectors/base.py` | `_store_payload` made async using `asyncio.to_thread` (non-blocking file I/O) |

### Modified Test Files
| File | Change |
|------|--------|
| `tests/unit/infrastructure/test_iheart_parser.py` | Import updated: `KIISIHeartCollector` → `IHeartNowPlayingCollector`; constructor adds `iheart_station_id="2501"` |

### New Test Files (7)
| File | Tests |
|------|-------|
| `tests/unit/infrastructure/test_iheart_top_songs_collector.py` | Generic top-songs collector; 3-station fixture coverage |
| `tests/unit/infrastructure/test_kiis_iheart_history_collector.py` | KIIS recently-played; URL, timestamps, 204 |
| `tests/unit/infrastructure/test_wksc_iheart_collector.py` | WKSC now-playing + history; station ID 821 |
| `tests/unit/infrastructure/test_z100_iheart_collector.py` | Z100 now-playing + history; station ID 614 |
| `tests/unit/infrastructure/test_bbc_radio1_collector.py` | BBC Radio 1; segment selection, speech skip, timestamps |
| `tests/unit/infrastructure/test_heart_radio_collector.py` | Heart FM; CSS selector parsing, time anchoring, drift detection |
| `tests/unit/infrastructure/test_kiis_radiowave_collector.py` | KIIS Radiowave; LA timezone conversion, URL construction |

### New Test Fixtures
| File | Type |
|------|------|
| `tests/fixtures/json/iheart_kiis_recently_played.json` | KIIS recently-played response |
| `tests/fixtures/json/iheart_kiis_top_songs.json` | KIIS top-songs response |
| `tests/fixtures/json/iheart_wksc_200.json` | WKSC now-playing 200 response |
| `tests/fixtures/json/iheart_wksc_recently_played.json` | WKSC recently-played response |
| `tests/fixtures/json/iheart_wksc_top_songs.json` | WKSC top-songs response |
| `tests/fixtures/json/iheart_z100_200.json` | Z100 now-playing 200 response |
| `tests/fixtures/json/iheart_z100_recently_played.json` | Z100 recently-played response |
| `tests/fixtures/json/iheart_z100_top_songs.json` | Z100 top-songs response |
| `tests/fixtures/json/bbc_radio1_segments.json` | BBC Radio 1 RMS segments response |
| `tests/fixtures/html/heart_fm_last_played.html` | Heart FM last-played-songs HTML |
| `tests/fixtures/html/heart_fm_last_played_empty.html` | Heart FM empty track list HTML |
| `tests/fixtures/html/radiowave_kiis_diary.html` | KIIS Radiowave diary HTML |

### Settings Changes
| Setting | Default | Purpose |
|---------|---------|---------|
| `enable_bbc_radio1_collector` | `False` | BBC Radio 1 scheduler gate (not wired) |
| `enable_heart_collector` | `False` | Heart FM scheduler gate (not wired) |
| `enable_z100_collector` | `False` | Z100 scheduler gate (not wired) |
| `enable_wksc_collector` | `False` | WKSC scheduler gate (not wired) |
| `enable_iheart_top_songs` | `False` | Generic iHeart top-songs gate (not wired) |

---

## 4. Files Explicitly Excluded

| Category | Example files | Reason |
|----------|--------------|--------|
| Migrations | `e1f2a3b4c5d6_phase_e_prod_hardening.py`, `l3m4n5o6p7q8_phase_k_bbc_radio_1.py`, etc. | Migration Phase E conflicts with main; station inserts are separate EXTRACT-2 pass |
| Scheduler | `app/infrastructure/scheduler/scheduler.py` | Email reporting intertwined; separate EXTRACT-1B pass |
| Source/station seeds | `source_seeds.py`, `station_seeds.py` | Separate EXTRACT-2 pass |
| UI | `app/static/*` | Superseded by PR #9 |
| `app/main.py` | — | Sentry/CORS/email routers — separate passes |
| Email reporting | `app/infrastructure/email/`, `email_report_builder.py` | Large feature — separate EXTRACT-EMAIL-1 pass |
| Deployment | `docker-compose.hetzner.yml`, `.github/workflows/` | Infrastructure decisions — separate INFRA passes |
| Docs contamination | `RECON-1-*.md`, `POST-MERGE-STABILITY-1-report.md` | Not code; contaminated the HEAD of PR #3 |
| Per-station wrappers | `kiis_iheart_history.py`, `wksc_iheart.py`, `z100_iheart.py` | Thin wrappers superseded by generic classes; not imported by any test |

---

## 5. New Collectors Are NOT Registered in Scheduler

Zero changes to `app/infrastructure/scheduler/scheduler.py`. The 5 new settings flags exist as gating stubs only. The next extraction pass (`EXTRACT-1B`) will wire scheduler entries pointing to these flags.

---

## 6. No Source Seeding

Zero changes to `app/application/source_config/source_seeds.py` or `station_seeds.py`. New stations (BBC Radio 1, Heart FM, Z100, WKSC) are not yet in the seed data. EXTRACT-2 will handle station seeds and migrations K-N.

---

## 7. No Live HTTP Calls in Tests

All tests use:
- Pre-saved JSON fixtures (iHeart, BBC)
- Pre-saved HTML fixtures (Heart FM, Radiowave)
- `unittest.mock.AsyncMock` / `patch` to intercept `fetch_raw`

No test connects to any live radio service or external API.

---

## 8. Test Results

| Gate | Result |
|------|--------|
| Infrastructure tests (targeted) | **156 passed** |
| Full test suite | **492 passed, 2 skipped** (+102 from baseline 390) |
| Ruff | **Clean** |
| Mypy | **Clean** |

---

## 9. Static Safety Scan

| Scan | Result |
|------|--------|
| Unsafe enabled flags (`ENABLE_*=true`) | Clean — only in rollback script comment and historical docs |
| Secrets | None found |
| Live call patterns in new files | None — all use lazy `build_client` import |
| Scheduler wiring in new files | None |
| Production env changes | None |

---

## 10. base.py async I/O Change

The `_store_payload` method in `base.py` was made `async` using `asyncio.to_thread` for the file write. This is a non-blocking I/O improvement that was part of the RECON-2A "valuable work" classification.

**Impact:** All existing collectors inherit from `BaseCollector` and call `run()`. The change is backward-compatible:
- No subclass overrides `_store_payload`
- All tests use `@pytest.mark.anyio` and `await collector.run()`
- All 390 existing tests pass unchanged

---

## 11. Remaining Risks

| Risk | Mitigation |
|------|-----------|
| VAL flags on new collectors | All documented in collector docstrings (VAL-BBC1-001, VAL-HEARTFM-002, etc.) — must be confirmed before enabling |
| Heart FM CSS selectors are synthetic | See `VAL-HEARTFM-002` — selectors were built against synthetic fixture, not live page |
| iHeart top-songs endpoint schema unvalidated | See `VAL-IHEART-TOP-001` — confirm against live page before enabling |
| Radiowave KIIS timezone | Uses `America/Los_Angeles` — confirmed in source; not yet live-tested |
| New stations not in DB | Needs EXTRACT-2 (station seeds + idempotent migrations K-N) before collectors can run in production |

---

## 12. Production Safety

| Concern | Status |
|---------|--------|
| Production deployment | NOT performed |
| Production env modified | NO |
| Migrations applied | NO |
| Scheduler enabled | NO |
| Any collector enabled | NO |
| Any enrichment enabled | NO |
| Live HTTP calls | NO |
| main force-pushed | NO |

---

## 13. Next Recommended Passes

| Pass | Branch | Scope |
|------|--------|-------|
| `POST-MERGE-STABILITY-EXTRACT-1` | `main` | Pull latest after EXTRACT-1 merges, confirm 492 tests, no collectors enabled |
| `EXTRACT-1B` | `feat/recon2-scheduler-collector-wiring` | Add scheduler entries gated by the 5 new flags; defaults disabled |
| `EXTRACT-2` | `feat/recon2-station-seeds-new-stations` | Station seeds + idempotent migrations K-N for BBC, Heart, Z100, WKSC |
