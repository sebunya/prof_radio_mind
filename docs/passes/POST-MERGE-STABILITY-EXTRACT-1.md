# POST-MERGE-STABILITY-EXTRACT-1 — Stability Report After PR #11 Merge

**Date:** 2026-06-05  
**Pass:** POST-MERGE-STABILITY-EXTRACT-1  
**PR merged:** [#11 — feat(collectors): add extracted parser/collector library from PR #3](https://github.com/sebunya/prof_radio_mind/pull/11)  
**Main before merge:** `1ec18c00`  
**Main after merge:** `df660b48`  
**Verdict:** `PR11 MERGED — POST-MERGE STABILITY PASSED`

---

## 1. PR #11 Merge Confirmation

| Item | Value |
|------|-------|
| PR number | #11 |
| Title | feat(collectors): add extracted parser/collector library from PR #3 |
| Head branch | `feat/recon2-parser-collector-library` @ `7dbb983` |
| Base branch | `main` @ `1ec18c00` |
| Merge commit | `df660b48` |
| Merge method | merge (fast-forward) |
| Draft before merge | yes — undrafted immediately before merge |
| Mergeability at merge time | `clean` |
| Files changed | 34 |
| Insertions | +3,157 |
| Deletions | −26 |

---

## 2. base.py Compatibility Verdict

**Change:** `_store_payload` converted from synchronous to `async def` using `asyncio.to_thread` for non-blocking file I/O.

| Question | Answer |
|----------|--------|
| Method signature changed? | No — parameters and return type (`RawPayload`) unchanged |
| Return value changed? | No |
| Caller in `run()` updated? | Yes — `raw_payload = await self._store_payload(...)` |
| Any subclass overrides `_store_payload`? | No — grep confirms single definition only |
| All tests exercise the new async path? | Yes — all use `@pytest.mark.anyio` + `await collector.run()` |
| Existing collectors broken? | No — all 390 pre-existing tests continued to pass |

**Verdict: BACKWARD COMPATIBLE**

---

## 3. Extracted Files Summary

### New Parsers (2)
- `app/infrastructure/parsers/bbc_sounds.py` — BBC Sounds RMS API JSON parser
- `app/infrastructure/parsers/heart.py` — Heart FM last-played HTML parser

### Modified Parsers (2)
- `app/infrastructure/parsers/iheart.py` — `parse_iheart_recently_played()`, `parse_iheart_top_songs()`, `IHeartTopSongResult`, millisecond timestamp guard
- `app/infrastructure/parsers/radiowave.py` — `station_timezone` parameter (default `Australia/Sydney`; backward-compatible)

### New Collectors (6)
- `app/infrastructure/collectors/iheart_now_playing.py`
- `app/infrastructure/collectors/iheart_recently_played.py`
- `app/infrastructure/collectors/iheart_top_songs.py`
- `app/infrastructure/collectors/bbc_radio_1.py`
- `app/infrastructure/collectors/heart_radio.py`
- `app/infrastructure/collectors/kiis_radiowave.py`

### Modified Collector Base (1)
- `app/infrastructure/collectors/base.py` — `_store_payload` async

### Tests (8 files)
- 7 new test modules (156 infrastructure tests)
- 1 updated test (`test_iheart_parser.py` import)

### Fixtures (12)
- 9 JSON, 3 HTML — all pre-saved, no live HTTP

### Settings (1 file)
- `app/core/settings.py` — 5 new flags, all `False`

---

## 4. Post-Merge Quality Gates

| Gate | Result |
|------|--------|
| Ruff | **CLEAN** |
| Mypy | **CLEAN** (124 source files) |
| Full test suite | **492 passed, 2 skipped** |
| Migrations in merge diff | **NONE** |
| Scheduler/seeds in merge diff | **NONE** |
| UI files in merge diff | **NONE** |
| New flags defaulting `False` | **CONFIRMED** |

---

## 5. Safety Confirmation

| Concern | Status |
|---------|--------|
| Migrations applied | NO |
| Migrations introduced | NO |
| Scheduler wiring added | NO |
| Source/station seeds added | NO |
| UI files touched | NO |
| Production env modified | NO |
| Production deployed | NO |
| Collectors enabled | NO |
| Live HTTP calls in tests | NO |
| Enabled flags in code | NONE |
| SEC-AUTH-1B weakened | NO |
| PR #9 admin UI overwritten | NO |
| `app/main.py` touched | NO |

---

## 6. Remaining Risks Carried Forward

| Risk | Description | Mitigation |
|------|-------------|------------|
| `VAL-HEARTFM-002` | Heart FM CSS selectors are synthetic — built against fixture, not live page | Must confirm selectors against live page before enabling |
| `VAL-IHEART-TOP-001` | iHeart top-songs endpoint schema unvalidated against live API | Confirm before enabling `enable_iheart_top_songs` |
| `VAL-BBC1-001` | BBC Radio 1 live reachability and ToS not yet confirmed | Confirm before enabling `enable_bbc_radio1_collector` |
| `VAL-KIIS-RAD-001` | KIIS Radiowave Monitor live reachability not yet tested | Confirm before enabling |
| New stations not in DB | BBC Radio 1, Heart FM, Z100 (WHTZ), WKSC 103.5 have no station records | EXTRACT-2 will add seeds + idempotent migrations K-N |
| 5 new flags exist but not wired | Scheduler has no job for any new collector | EXTRACT-1B will add scheduler entries (all disabled by default) |

---

## 7. Next Recommended Pass

| Pass | Branch | Scope | Prerequisite |
|------|--------|-------|--------------|
| `EXTRACT-1B-PLAN` | Planning only | Design scheduler wiring for 5 new flags; no code yet | This stability report |
| `EXTRACT-1B` | `feat/recon2-scheduler-collector-wiring` | Add scheduler entries gated by 5 new flags, all disabled | `EXTRACT-1B-PLAN` approved |
| `EXTRACT-2` | `feat/recon2-station-seeds-new-stations` | Station seeds + idempotent migrations K-N for BBC, Heart, Z100, WKSC | `EXTRACT-1B` merged |

**Do not start:** Spotify backend, Spotify worker, MusicBrainz, METADATA-1, production deployment, PR #3 wholesale rebase.
