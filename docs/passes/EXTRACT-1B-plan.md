# EXTRACT-1B-PLAN — Scheduler Wiring Plan for Extracted Collectors

**Date:** 2026-06-05  
**Pass type:** PLANNING ONLY — no code changes in this document  
**Branch for implementation:** `feat/recon2-scheduler-collector-wiring` (not yet created)  
**Depends on:** EXTRACT-1 merged (`df660b48`), SEC-AUTH-1C deployed  
**Blocks:** EXTRACT-2, any collector enablement  

---

## 1. Purpose

EXTRACT-1 added 6 new collector classes and 5 new settings flags to `main`. None are wired into the scheduler. None have station/source records in the database. This plan defines exactly what EXTRACT-1B must implement, what it must not touch, and what must land in EXTRACT-2 first before any collector can run.

---

## 2. Current State (Post EXTRACT-1)

### 2.1 New Collector Classes (library-only, not wired)

| Class | Source file | Key constructor param |
|-------|-------------|----------------------|
| `IHeartNowPlayingCollector` | `iheart_now_playing.py` | `iheart_station_id: str` |
| `IHeartRecentlyPlayedCollector` | `iheart_recently_played.py` | `iheart_station_id: str` |
| `IHeartTopSongsCollector` | `iheart_top_songs.py` | `iheart_station_id: str` |
| `BBCRadio1Collector` | `bbc_radio_1.py` | no station param (fixed URL) |
| `HeartRadioCollector` | `heart_radio.py` | no station param (fixed URL) |
| `KIISRadiowaveCollector` | `kiis_radiowave.py` | `idds: str = "5080"` |

### 2.2 New Settings Flags (all `False`, none scheduler-wired)

| Flag | Maps to | iHeart station ID |
|------|---------|------------------|
| `enable_bbc_radio1_collector` | `BBCRadio1Collector` | N/A |
| `enable_heart_collector` | `HeartRadioCollector` | N/A |
| `enable_z100_collector` | `IHeartNowPlayingCollector` | `"614"` |
| `enable_wksc_collector` | `IHeartNowPlayingCollector` | `"821"` |
| `enable_iheart_top_songs` | `IHeartTopSongsCollector` | see §3 |

### 2.3 Existing Scheduler Pattern (from `scheduler.py`)

```python
_NS = uuid.NAMESPACE_DNS
_STATION_ID = uuid.uuid5(_NS, "station.CALL_SIGN")
_SOURCE_ID  = uuid.uuid5(_NS, "source.CALL_SIGN.source_type_key")

async def job_collect_xxx() -> None:
    collector = XxxCollector(source_id=_SOURCE_ID, station_id=_STATION_ID, ...)
    result = await collector.run()
    logger.info("xxx status=%s plays=%d ...", ...)
    await _persist_result(result)

# In build_scheduler():
if settings.enable_xxx_collector:
    sched.add_job(job_collect_xxx, IntervalTrigger(minutes=N), id="xxx_id", ...)
```

### 2.4 Existing Station/Source Records in DB

| Station | call_sign | Source type | Source key |
|---------|-----------|-------------|------------|
| Nova 96.9 | `NOVA969` | radiowave | `radiowave` |
| KIIS-FM (Sydney) | `KIISFM` | iheart | `iheart` |
| Capital FM UK | `CAPITALFM` | online_radio_box | `online_radio_box` |

**The 4 new stations (BBC Radio 1, Heart FM UK, Z100, WKSC) have zero DB records.** EXTRACT-2 must add them.

---

## 3. Ambiguities Resolved

### 3.1 `enable_iheart_top_songs` — Which Station?

`IHeartTopSongsCollector` requires `iheart_station_id`. The flag is not per-station.

**Decision: gate KIIS-FM Sydney (station_id="2501") only.**

Rationale: KIIS is already production-known, station record exists, `VAL-KIIS-001` is the only partially-validated iHeart station. Z100 and WKSC top songs are deferred to a future flag per station once their DB records and live validation exist.

Top-songs runs daily (not polling) — see §5.3.

### 3.2 `KIISRadiowaveCollector` — No Dedicated Flag

`KIISRadiowaveCollector` targets KIIS-FM **Los Angeles** (102.7 FM, IDDS=5080). This is a **different station** from the existing `KIISFM` (Sydney, 106.5 FM). It has:
- No station record in DB
- No source record in DB
- No settings flag

**Decision: defer entirely to EXTRACT-1B-PART2 or EXTRACT-2.**

Rationale:
- Adding a new flag in EXTRACT-1B-PLAN scope would require a separate settings addition (minor but requires a separate PR)
- The LA KIIS station needs both a station seed and a source seed (EXTRACT-2 scope)
- `VAL-KIIS-RAD-001` (live reachability) is unconfirmed
- This collector can safely remain as library-only code for now

EXTRACT-1B will not wire `KIISRadiowaveCollector`.

### 3.3 `IHeartRecentlyPlayedCollector` — No Dedicated Flag

There is no `enable_*_recently_played` flag. Options:
- Wire recently-played under the same flag as now-playing (runs alongside)
- Add per-collector flags (scope creep)

**Decision: defer recently-played scheduler wiring to a future pass.**

Rationale: recently-played returns a batch of historical tracks; running it every 5 minutes alongside now-playing creates significant data volume and dedup complexity. This needs its own polling interval design. The library class exists and is tested — scheduling is separate.

### 3.4 `KIISIHeartCollector` vs `IHeartNowPlayingCollector` for Existing KIIS Job

The existing scheduler imports `KIISIHeartCollector` from `app.infrastructure.collectors.kiis_iheart`. This old per-station class still exists on main (not removed in EXTRACT-1). The new `IHeartNowPlayingCollector` is the generic replacement.

**Decision: do not replace the existing KIIS job in EXTRACT-1B.**

Rationale: the existing job is tested, stable, and production-running. Replacing it is a separate refactor risk. New stations (Z100, WKSC) use the generic class. The old KIIS job continues to use `KIISIHeartCollector` until a dedicated refactor pass.

---

## 4. New Station Identity Constants

The following call signs and source type keys define the deterministic UUIDs. **These must be chosen now and never changed** — changing them after any migration requires a data migration.

| Station | Call sign | Source type key | iHeart station ID |
|---------|-----------|-----------------|-------------------|
| BBC Radio 1 | `BBCRADIO1` | `bbc_sounds` | N/A |
| Heart FM UK | `HEARTFMUK` | `heart_last_played` | N/A |
| Z100 New York (WHTZ) | `WHTZ` | `iheart` | `614` |
| WKSC 103.5 Chicago | `WKSC` | `iheart` | `821` |

UUID derivation (identical to seeder pattern):
```python
_NS = uuid.NAMESPACE_DNS
_BBC1_STATION_ID   = uuid.uuid5(_NS, "station.BBCRADIO1")
_BBC1_SOURCE_ID    = uuid.uuid5(_NS, "source.BBCRADIO1.bbc_sounds")
_HEARTFM_STATION_ID = uuid.uuid5(_NS, "station.HEARTFMUK")
_HEARTFM_SOURCE_ID  = uuid.uuid5(_NS, "source.HEARTFMUK.heart_last_played")
_Z100_STATION_ID   = uuid.uuid5(_NS, "station.WHTZ")
_Z100_SOURCE_ID    = uuid.uuid5(_NS, "source.WHTZ.iheart")
_WKSC_STATION_ID   = uuid.uuid5(_NS, "station.WKSC")
_WKSC_SOURCE_ID    = uuid.uuid5(_NS, "source.WKSC.iheart")
```

These must also be used in EXTRACT-2 station/source seeds — the seeder uses the same `uuid5(_NS, ...)` derivation.

---

## 5. Scheduler Job Design

### 5.1 BBC Radio 1 — `job_collect_bbc_radio1()`

```python
async def job_collect_bbc_radio1() -> None:
    """Poll BBC Radio 1 RMS API for current segment (runs every 5 minutes)."""
    collector = BBCRadio1Collector(
        source_id=_BBC1_SOURCE_ID,
        station_id=_BBC1_STATION_ID,
        storage_root=settings.raw_payload_storage_path,
    )
    result = await collector.run()
    logger.info(
        "bbc_radio1_collected status=%s plays=%d no_tracks=%d",
        result.collector_run.status.value,
        len(result.play_events),
        len(result.no_track_events),
    )
    await _persist_result(result)
```

**Trigger:** `IntervalTrigger(minutes=5)`  
**Job ID:** `bbc_radio1_now_playing`  
**Gate flag:** `settings.enable_bbc_radio1_collector`  
**VAL outstanding:** `VAL-BBC1-001` (live reachability), `VAL-BBC1-006` (ToS)

### 5.2 Heart FM — `job_collect_heart_fm()`

```python
async def job_collect_heart_fm() -> None:
    """Scrape Heart FM last-played-songs page (runs every 5 minutes)."""
    collector = HeartRadioCollector(
        source_id=_HEARTFM_SOURCE_ID,
        station_id=_HEARTFM_STATION_ID,
        storage_root=settings.raw_payload_storage_path,
    )
    result = await collector.run()
    logger.info(
        "heart_fm_collected status=%s plays=%d no_tracks=%d",
        result.collector_run.status.value,
        len(result.play_events),
        len(result.no_track_events),
    )
    await _persist_result(result)
```

**Trigger:** `IntervalTrigger(minutes=5)`  
**Job ID:** `heart_fm_last_played`  
**Gate flag:** `settings.enable_heart_collector`  
**VAL outstanding:** `VAL-HEARTFM-002` (CSS selectors against live page — synthetic fixture only)

### 5.3 Z100 (WHTZ) — `job_collect_z100_now_playing()`

```python
async def job_collect_z100_now_playing() -> None:
    """Poll Z100 iHeart now-playing endpoint (runs every 5 minutes)."""
    collector = IHeartNowPlayingCollector(
        source_id=_Z100_SOURCE_ID,
        station_id=_Z100_STATION_ID,
        iheart_station_id="614",
        storage_root=settings.raw_payload_storage_path,
    )
    result = await collector.run()
    logger.info(
        "z100_now_playing status=%s plays=%d no_tracks=%d",
        result.collector_run.status.value,
        len(result.play_events),
        len(result.no_track_events),
    )
    await _persist_result(result)
```

**Trigger:** `IntervalTrigger(minutes=5)`  
**Job ID:** `z100_now_playing`  
**Gate flag:** `settings.enable_z100_collector`  
**VAL outstanding:** station_id=614 confirmed in fixture, not against live API

### 5.4 WKSC — `job_collect_wksc_now_playing()`

```python
async def job_collect_wksc_now_playing() -> None:
    """Poll WKSC 103.5 iHeart now-playing endpoint (runs every 5 minutes)."""
    collector = IHeartNowPlayingCollector(
        source_id=_WKSC_SOURCE_ID,
        station_id=_WKSC_STATION_ID,
        iheart_station_id="821",
        storage_root=settings.raw_payload_storage_path,
    )
    result = await collector.run()
    logger.info(
        "wksc_now_playing status=%s plays=%d no_tracks=%d",
        result.collector_run.status.value,
        len(result.play_events),
        len(result.no_track_events),
    )
    await _persist_result(result)
```

**Trigger:** `IntervalTrigger(minutes=5)`  
**Job ID:** `wksc_now_playing`  
**Gate flag:** `settings.enable_wksc_collector`  
**VAL outstanding:** station_id=821 confirmed in fixture, not against live API

### 5.5 iHeart Top Songs (KIIS primary) — `job_collect_kiis_top_songs()`

```python
async def job_collect_kiis_top_songs() -> None:
    """Collect KIIS-FM iHeart top songs chart (runs daily 00:00 UTC)."""
    collector = IHeartTopSongsCollector(
        source_id=_KIIS_SOURCE_ID,
        station_id=_KIIS_STATION_ID,
        iheart_station_id="2501",
        storage_root=settings.raw_payload_storage_path,
    )
    result = await collector.run()
    logger.info(
        "kiis_top_songs status=%s plays=%d no_tracks=%d",
        result.collector_run.status.value,
        len(result.play_events),
        len(result.no_track_events),
    )
    await _persist_result(result)
```

**Trigger:** `CronTrigger(hour=0, minute=0, timezone="UTC")` — daily snapshot, not polling  
**Job ID:** `kiis_top_songs_daily`  
**Gate flag:** `settings.enable_iheart_top_songs`  
**Uses existing:** `_KIIS_SOURCE_ID` and `_KIIS_STATION_ID` (already in scheduler)  
**VAL outstanding:** `VAL-IHEART-TOP-001` (endpoint schema unvalidated against live)

### 5.6 `build_scheduler()` additions

```python
if settings.enable_bbc_radio1_collector:
    sched.add_job(job_collect_bbc_radio1, IntervalTrigger(minutes=5),
        id="bbc_radio1_now_playing", name="BBC Radio 1 RMS API poll",
        replace_existing=True, misfire_grace_time=60)
    logger.info("Scheduler registered job: BBC Radio 1 RMS API poll")
else:
    logger.info("Scheduler skipped job: BBC Radio 1 (disabled)")

if settings.enable_heart_collector:
    sched.add_job(job_collect_heart_fm, IntervalTrigger(minutes=5),
        id="heart_fm_last_played", name="Heart FM last-played scrape",
        replace_existing=True, misfire_grace_time=60)
    logger.info("Scheduler registered job: Heart FM last-played scrape")
else:
    logger.info("Scheduler skipped job: Heart FM (disabled)")

if settings.enable_z100_collector:
    sched.add_job(job_collect_z100_now_playing, IntervalTrigger(minutes=5),
        id="z100_now_playing", name="Z100 iHeart now-playing poll",
        replace_existing=True, misfire_grace_time=60)
    logger.info("Scheduler registered job: Z100 now-playing poll")
else:
    logger.info("Scheduler skipped job: Z100 (disabled)")

if settings.enable_wksc_collector:
    sched.add_job(job_collect_wksc_now_playing, IntervalTrigger(minutes=5),
        id="wksc_now_playing", name="WKSC 103.5 iHeart now-playing poll",
        replace_existing=True, misfire_grace_time=60)
    logger.info("Scheduler registered job: WKSC now-playing poll")
else:
    logger.info("Scheduler skipped job: WKSC (disabled)")

if settings.enable_iheart_top_songs:
    sched.add_job(job_collect_kiis_top_songs, CronTrigger(hour=0, minute=0, timezone="UTC"),
        id="kiis_top_songs_daily", name="KIIS-FM iHeart top songs daily",
        replace_existing=True, misfire_grace_time=3600)
    logger.info("Scheduler registered job: KIIS top songs daily")
else:
    logger.info("Scheduler skipped job: iHeart top songs (disabled)")
```

---

## 6. Required Imports in `scheduler.py`

Add to existing imports:
```python
from app.infrastructure.collectors.bbc_radio_1 import BBCRadio1Collector
from app.infrastructure.collectors.heart_radio import HeartRadioCollector
from app.infrastructure.collectors.iheart_now_playing import IHeartNowPlayingCollector
from app.infrastructure.collectors.iheart_top_songs import IHeartTopSongsCollector
```

`IHeartNowPlayingCollector` replaces nothing — the existing `KIISIHeartCollector` import stays.

---

## 7. Test Plan for EXTRACT-1B

### 7.1 Update `test_scheduler_all_enabled_has_four_jobs`

This test must be renamed and updated — it asserts exactly 4 jobs, which will be wrong after EXTRACT-1B:

```python
def test_scheduler_all_enabled_has_nine_jobs() -> None:
    from app.core.settings import settings
    with (
        patch.object(settings, "enable_nova_collector", True),
        patch.object(settings, "enable_kiis_collector", True),
        patch.object(settings, "enable_capital_collector", True),
        patch.object(settings, "enable_nightly_reconciliation", True),
        patch.object(settings, "enable_bbc_radio1_collector", True),
        patch.object(settings, "enable_heart_collector", True),
        patch.object(settings, "enable_z100_collector", True),
        patch.object(settings, "enable_wksc_collector", True),
        patch.object(settings, "enable_iheart_top_songs", True),
    ):
        sched = build_scheduler()
        assert len(sched.get_jobs()) == 9
        ids = {j.id for j in sched.get_jobs()}
        assert ids == {
            "nova_daily_diary",
            "kiis_now_playing",
            "capital_now_playing",
            "nightly_reconciliation",
            "bbc_radio1_now_playing",
            "heart_fm_last_played",
            "z100_now_playing",
            "wksc_now_playing",
            "kiis_top_songs_daily",
        }
```

### 7.2 New per-job registration tests

For each new job, add:
```python
def test_bbc_radio1_job_uses_interval_trigger() -> None:
    with patch.object(settings, "enable_bbc_radio1_collector", True):
        sched = build_scheduler()
        job = sched.get_job("bbc_radio1_now_playing")
        assert job is not None
        assert isinstance(job.trigger, IntervalTrigger)

def test_heart_fm_job_uses_interval_trigger() -> None: ...
def test_z100_job_uses_interval_trigger() -> None: ...
def test_wksc_job_uses_interval_trigger() -> None: ...

def test_kiis_top_songs_job_uses_cron_trigger() -> None:
    with patch.object(settings, "enable_iheart_top_songs", True):
        sched = build_scheduler()
        job = sched.get_job("kiis_top_songs_daily")
        assert job is not None
        assert isinstance(job.trigger, CronTrigger)
```

### 7.3 New job function unit tests

For each new job function, add a test mirroring `test_nova_diary_job_invokes_collector`:
```python
@pytest.mark.anyio
async def test_bbc_radio1_job_invokes_collector() -> None:
    # patch BBCRadio1Collector, assert run() called once, _persist_result called
    ...

@pytest.mark.anyio
async def test_heart_fm_job_invokes_collector() -> None: ...

@pytest.mark.anyio
async def test_z100_job_invokes_collector() -> None: ...

@pytest.mark.anyio
async def test_wksc_job_invokes_collector() -> None: ...

@pytest.mark.anyio
async def test_kiis_top_songs_job_invokes_collector() -> None: ...
```

### 7.4 Disabled-by-default tests

```python
def test_new_collector_jobs_absent_when_disabled() -> None:
    from app.core.settings import settings
    with (
        patch.object(settings, "enable_bbc_radio1_collector", False),
        patch.object(settings, "enable_heart_collector", False),
        patch.object(settings, "enable_z100_collector", False),
        patch.object(settings, "enable_wksc_collector", False),
        patch.object(settings, "enable_iheart_top_songs", False),
        # keep existing disabled too
        patch.object(settings, "enable_nova_collector", False),
        patch.object(settings, "enable_kiis_collector", False),
        patch.object(settings, "enable_capital_collector", False),
        patch.object(settings, "enable_nightly_reconciliation", False),
    ):
        sched = build_scheduler()
        assert len(sched.get_jobs()) == 0
```

---

## 8. What EXTRACT-1B Does NOT Do

| Item | Reason |
|------|--------|
| Add `SourceType.BBC_SOUNDS` or `SourceType.HEART_LAST_PLAYED` to enum | EXTRACT-2 — requires migration |
| Add station seeds for BBC, Heart, Z100, WKSC | EXTRACT-2 scope |
| Add source seeds for BBC, Heart, Z100, WKSC | EXTRACT-2 scope |
| Wire `KIISRadiowaveCollector` | No flag; LA station needs seeds; VAL-KIIS-RAD-001 unconfirmed |
| Wire `IHeartRecentlyPlayedCollector` | Polling design unresolved |
| Enable any flag | All 5 new flags remain `False` |
| Apply or create migrations | Zero DB changes |
| Seed any source in DB | Zero DB changes |
| Touch admin UI | None |
| Touch `app/main.py` | None |

---

## 9. Dependency on EXTRACT-2

**EXTRACT-1B can be merged before EXTRACT-2.** The job functions exist as code; the flags keep them from running. The DB records (station/source) are only needed at runtime when the flags are enabled.

**Enablement order in production:**
1. EXTRACT-1B merged → scheduler code exists, all disabled
2. EXTRACT-2 merged → station/source seeds + migrations K-N applied
3. Only after both: set `ENABLE_BBC_RADIO1_COLLECTOR=true` etc., force-recreate app

If EXTRACT-1B is enabled before EXTRACT-2 lands (missing DB records), `_persist_result` will fail with FK violations logged as errors. The scheduler will continue running other jobs. No data corruption — failed `CollectorRun` records simply won't save (the session rollback path in `_persist_result` catches and logs the exception). This is a recoverable state, not catastrophic.

---

## 10. CI Live-Call Protection

All new scheduler job tests use `patch(f"{_sched}.BBCRadio1Collector", ...)` etc. to mock the collector class. No test calls `fetch_raw()` on the real collector. No test requires network access.

The existing `conftest.py` or test environment does not make live calls — confirmed by the EXTRACT-1 pass (492 tests, all fixture-driven). EXTRACT-1B adds no new test infrastructure; it reuses the existing mock pattern.

---

## 11. Production Safety Gate

EXTRACT-1B adds no changes to `.env.production.example` beyond what already exists. The 5 new flags already have `False` defaults via Pydantic `bool = False`. No additional env file changes are needed.

Rollback if a collector misbehaves after enabling:
1. Set `ENABLE_BBC_RADIO1_COLLECTOR=false` (or whichever flag) in `/opt/rmias/.env.production`
2. `docker compose -f docker-compose.hetzner.yml --env-file .env.production up -d --force-recreate app`
3. The job simply won't be registered in `build_scheduler()` — no migration, no data cleanup needed
4. Already-persisted records remain (idempotent dedup prevents re-saves on re-enable)

---

## 12. EXTRACT-2 Scope (Separate PR, After EXTRACT-1B)

EXTRACT-2 must:
1. Add `SourceType.BBC_SOUNDS` and `SourceType.HEART_LAST_PLAYED` to `SourceType` enum
2. Add station seeds: `BBCRADIO1`, `HEARTFMUK`, `WHTZ`, `WKSC`
3. Add source seeds: `bbc_sounds`, `heart_last_played`, `iheart` (×2)
4. Add idempotent Alembic migration K inserting station/source rows via `ON CONFLICT DO NOTHING`
5. Confirm call sign / source type key strings match exactly what EXTRACT-1B hardcoded in UUID derivation

---

## 13. EXTRACT-1B Implementation Checklist

- [ ] Create branch `feat/recon2-scheduler-collector-wiring` from latest `main`
- [ ] Add 8 new UUID constants to `scheduler.py` (4 station IDs, 4 source IDs)
- [ ] Add imports: `BBCRadio1Collector`, `HeartRadioCollector`, `IHeartNowPlayingCollector`, `IHeartTopSongsCollector`
- [ ] Add 5 new `job_collect_*()` async functions
- [ ] Add 5 new `if settings.enable_xxx` blocks in `build_scheduler()`
- [ ] Update `test_scheduler_all_enabled_has_four_jobs` → `_has_nine_jobs`
- [ ] Add 5 per-job registration tests (trigger type)
- [ ] Add 5 per-job function unit tests (mock collector + `_persist_result`)
- [ ] Add `test_new_collector_jobs_absent_when_disabled()`
- [ ] Ruff clean
- [ ] Mypy clean
- [ ] Full suite: expect ~502+ passed (≥10 new scheduler tests), 2 skipped
- [ ] Boundary check: zero migrations, zero seeds, zero UI, zero flags enabled
- [ ] Push PR with base `main`, draft until quality gates pass
