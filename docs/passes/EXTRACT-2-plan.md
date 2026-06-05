# EXTRACT-2-PLAN — Station Seeds and SourceType Extension for New Collectors

**Date:** 2026-06-05
**Pass type:** PLANNING ONLY — no code changes in this document
**Branch for implementation:** `feat/recon2-station-seeds-new-stations` (not yet created)
**Depends on:** EXTRACT-1B merged to main (PR #12)
**Blocks:** Enabling any of the 5 new collector flags in production

---

## 1. Purpose

EXTRACT-1B wired 5 collector jobs into the scheduler behind disabled flags. The jobs reference
8 deterministic UUIDs for 4 new stations and their sources. Those station and source records
do not exist in the database. Until they do, enabling any flag causes `_persist_result()` to
fail with a foreign-key violation (session rolls back, error logged, non-fatal).

EXTRACT-2 creates those records by:
1. Extending the `SourceType` Python enum with 2 new values
2. Adding 4 station seeds to `station_seeds.py`
3. Adding source seeds (primary + manual CSV fallback) for each station to `source_seeds.py`

No Alembic migration is required. No flag is enabled. No live collection runs.

---

## 2. Why No Migration Is Required

`source_type` is stored as `String(64)` (plain VARCHAR) with no CHECK constraint:

```python
# app/infrastructure/database/models/sources.py:20
source_type: Mapped[str] = mapped_column(String(64), nullable=False)
```

Confirmed in Phase A migration (`ade166ae8d36`): `sa.Column("source_type", sa.String(64), nullable=False)` — no enum type, no constraint.

The Python `SourceType(StrEnum)` is application-level only. Adding new values inserts new strings
into the VARCHAR column — the DB accepts them without schema changes.

Station and source records are inserted by the startup seeder, not via migrations. Seeder is
already idempotent (`get_by_id()` before insert).

---

## 3. SourceType Enum Extension

File: `app/domain/entities/source.py`

Add two values to `SourceType`:

```python
class SourceType(StrEnum):
    RADIOWAVE = "radiowave"
    IHEART = "iheart"
    ONLINE_RADIO_BOX = "online_radio_box"
    MANUAL_CSV = "manual_csv"
    UNKNOWN = "unknown"
    BBC_SOUNDS = "bbc_sounds"          # new
    HEART_LAST_PLAYED = "heart_last_played"  # new
```

Z100 (WHTZ) and WKSC both use the existing `IHEART` — no new value needed for them.

---

## 4. New Station Identity (immutable — must match EXTRACT-1B constants exactly)

These were chosen in EXTRACT-1B-PLAN and are encoded in `scheduler.py`. Any change here would
require a data migration.

| Station | Call sign | Source type key | iHeart station ID | Frequency | City | Country |
|---------|-----------|-----------------|-------------------|-----------|------|---------|
| BBC Radio 1 | `BBCRADIO1` | `bbc_sounds` | N/A | 97.6-99.8 FM | London | GB |
| Heart FM UK | `HEARTFMUK` | `heart_last_played` | N/A | 106.2 FM | London | GB |
| Z100 New York | `WHTZ` | `iheart` | `614` | 100.3 FM | New York | US |
| WKSC 103.5 | `WKSC` | `iheart` | `821` | 103.5 FM | Chicago | US |

### Pre-computed UUIDs (must be identical to EXTRACT-1B scheduler constants)

```
BBCRADIO1 station_id:        9ecfd309-55e9-5df9-996f-2ea283b10568
BBCRADIO1 source_id:         32800202-78b8-5e48-a502-f771615c8402  (bbc_sounds)

HEARTFMUK station_id:        17f49778-fd59-5f82-886e-645c78356435
HEARTFMUK source_id:         4be04973-0050-55fa-ba03-30fac85f94e1  (heart_last_played)

WHTZ station_id:             442dced5-003f-5d3f-acc7-dacf397be992
WHTZ source_id:              b7cc2e45-5949-5995-be06-a89527aa4f66  (iheart)

WKSC station_id:             189482a2-f5a0-50c6-8774-cfd22dd43037
WKSC source_id:              00535f6c-73c6-5cd0-aed0-2cc481891239  (iheart)
```

These are derived by `uuid.uuid5(uuid.NAMESPACE_DNS, "station.<CALL_SIGN>")` and
`uuid.uuid5(uuid.NAMESPACE_DNS, "source.<CALL_SIGN>.<source_type_key>")` — the same derivation
used in `seeder.py` and already encoded in `scheduler.py` via the `_BBC1_*`, `_HEARTFM_*`,
`_Z100_*`, `_WKSC_*` constants.

---

## 5. Station Seeds to Add

File: `app/application/source_config/station_seeds.py`

Append to `STATION_SEEDS`:

```python
StationSeed(
    call_sign="BBCRADIO1",
    name="BBC Radio 1",
    frequency="97.6-99.8 FM",
    city="London",
    country_code="GB",
),
StationSeed(
    call_sign="HEARTFMUK",
    name="Heart FM UK",
    frequency="106.2 FM",
    city="London",
    country_code="GB",
),
StationSeed(
    call_sign="WHTZ",
    name="Z100 New York",
    frequency="100.3 FM",
    city="New York",
    country_code="US",
),
StationSeed(
    call_sign="WKSC",
    name="WKSC 103.5 Chicago",
    frequency="103.5 FM",
    city="Chicago",
    country_code="US",
),
```

---

## 6. Source Seeds to Add

File: `app/application/source_config/source_seeds.py`

### 6.1 BBC Radio 1

```python
# --- BBC Radio 1 ---
# VAL-BBC1-001: BBC Sounds/RMS API reachability UNVALIDATED
# VAL-BBC1-006: BBC ToS for automated access UNCONFIRMED
SourceSeed(
    station_call_sign="BBCRADIO1",
    source_type=SourceType.BBC_SOUNDS,
    name="BBC Radio 1 RMS API",
    base_url="https://rms.api.bbc.co.uk/v2/services/bbc_radio_one/segments/latest",
    config={"service_id": "bbc_radio_one"},
    priority=1,
    validation_note="UNVALIDATED — VAL-BBC1-001 (live reachability) and VAL-BBC1-006 (ToS) required",
),
SourceSeed(
    station_call_sign="BBCRADIO1",
    source_type=SourceType.MANUAL_CSV,
    name="BBC Radio 1 Manual CSV Fallback",
    base_url=None,
    config=None,
    priority=99,
    validation_note="Always available — manual fallback",
),
```

### 6.2 Heart FM UK

```python
# --- Heart FM UK ---
# VAL-HEARTFM-002: CSS selectors against live page UNVALIDATED (synthetic fixture only)
SourceSeed(
    station_call_sign="HEARTFMUK",
    source_type=SourceType.HEART_LAST_PLAYED,
    name="Heart FM Last Played Page",
    base_url="https://www.heart.co.uk/radio/",
    config={"parser": "heart_last_played_css"},
    priority=1,
    validation_note="UNVALIDATED — VAL-HEARTFM-002 (live CSS selectors) required",
),
SourceSeed(
    station_call_sign="HEARTFMUK",
    source_type=SourceType.MANUAL_CSV,
    name="Heart FM UK Manual CSV Fallback",
    base_url=None,
    config=None,
    priority=99,
    validation_note="Always available — manual fallback",
),
```

### 6.3 Z100 (WHTZ)

```python
# --- Z100 New York (WHTZ) ---
# VAL-Z100-001: iHeart station_id=614 confirmed in fixture; not validated against live API
SourceSeed(
    station_call_sign="WHTZ",
    source_type=SourceType.IHEART,
    name="Z100 iHeart Now Playing",
    base_url="https://api.iheart.com/api/v3/live-meta/stream",
    config={"station_id": "614"},
    priority=1,
    validation_note="UNVALIDATED — VAL-Z100-001 (live station_id=614) required before enable",
),
SourceSeed(
    station_call_sign="WHTZ",
    source_type=SourceType.MANUAL_CSV,
    name="Z100 Manual CSV Fallback",
    base_url=None,
    config=None,
    priority=99,
    validation_note="Always available — manual fallback",
),
```

### 6.4 WKSC

```python
# --- WKSC 103.5 Chicago ---
# VAL-WKSC-001: iHeart station_id=821 confirmed in fixture; not validated against live API
SourceSeed(
    station_call_sign="WKSC",
    source_type=SourceType.IHEART,
    name="WKSC 103.5 iHeart Now Playing",
    base_url="https://api.iheart.com/api/v3/live-meta/stream",
    config={"station_id": "821"},
    priority=1,
    validation_note="UNVALIDATED — VAL-WKSC-001 (live station_id=821) required before enable",
),
SourceSeed(
    station_call_sign="WKSC",
    source_type=SourceType.MANUAL_CSV,
    name="WKSC 103.5 Manual CSV Fallback",
    base_url=None,
    config=None,
    priority=99,
    validation_note="Always available — manual fallback",
),
```

---

## 7. What EXTRACT-2 Does NOT Do

| Item | Reason |
|------|--------|
| No Alembic migrations | `source_type` is VARCHAR(64) with no constraint — no schema change |
| No SourceRoutePriority records | Seeder doesn't populate those today; not needed for collection |
| No collector flag enablement | Flags stay `False`; seeds create DB records only |
| No scheduler changes | EXTRACT-1B is already complete |
| No KIISRadiowaveCollector wiring | LA KIIS (102.7 FM) is a different station, needs separate seeds + flag |
| No IHeartRecentlyPlayedCollector wiring | Deferred (polling design); no flag, no seeds |
| No UI changes | Source health UI already reads from DB; new stations appear automatically |
| No deployment steps | Seeds take effect on next `docker compose up` restart |
| No live collection | Flags are `False` until explicitly enabled in a future pass |

---

## 8. Testing Plan

### 8.1 Seeder unit tests

File: `tests/unit/test_seeder.py` (check if it exists; add if not)

- Test that `seed_database()` creates records for all 4 new stations
- Test that `seed_database()` is idempotent (second call produces no duplicates)
- Test that derived `station_id_for("BBCRADIO1")` matches the pre-computed UUID
- Test that derived `source_id_for("BBCRADIO1", "bbc_sounds")` matches the pre-computed UUID
- Same UUID checks for HEARTFMUK, WHTZ, WKSC

### 8.2 SourceType enum tests

Wherever `SourceType` is tested, verify `BBC_SOUNDS` and `HEART_LAST_PLAYED` parse correctly:
```python
assert SourceType("bbc_sounds") == SourceType.BBC_SOUNDS
assert SourceType("heart_last_played") == SourceType.HEART_LAST_PLAYED
```

### 8.3 Full suite gate

Expected after EXTRACT-2: all prior tests still pass, plus new seeder/enum tests.
Scheduler tests must be unaffected (the UUID constants in `scheduler.py` are already correct).

---

## 9. How to Verify Source Records Without Touching Production

Before enabling any flag, verify the seeder created the correct records in production:

```bash
ssh -o IdentitiesOnly=yes -i ~/.ssh/id_ed25519 root@178.105.238.18 \
  'docker compose -f /opt/rmias/docker-compose.hetzner.yml --env-file /opt/rmias/.env.production exec -T app \
   python3 -c "
import asyncio, uuid
from app.infrastructure.database.session import _get_factory as _factory

NS = uuid.NAMESPACE_DNS
checks = [
    (\"station\", uuid.uuid5(NS, \"station.BBCRADIO1\")),
    (\"source\",  uuid.uuid5(NS, \"source.BBCRADIO1.bbc_sounds\")),
    (\"station\", uuid.uuid5(NS, \"station.HEARTFMUK\")),
    (\"source\",  uuid.uuid5(NS, \"source.HEARTFMUK.heart_last_played\")),
    (\"station\", uuid.uuid5(NS, \"station.WHTZ\")),
    (\"source\",  uuid.uuid5(NS, \"source.WHTZ.iheart\")),
    (\"station\", uuid.uuid5(NS, \"station.WKSC\")),
    (\"source\",  uuid.uuid5(NS, \"source.WKSC.iheart\")),
]

async def run():
    async with _factory()() as s:
        from sqlalchemy import text
        for kind, uid in checks:
            table = \"stations\" if kind == \"station\" else \"sources\"
            row = await s.execute(text(f\"SELECT id FROM {table} WHERE id = :id\"), {\"id\": str(uid)})
            found = row.fetchone()
            print(f\"{kind} {uid}: {'FOUND' if found else 'MISSING'}\")

asyncio.run(run())
"'
```

All 8 UUIDs should return `FOUND` before enabling any flag.

---

## 10. Rollback Design

Seeds are DB rows. Rollback scenarios:

| Scenario | Action |
|----------|--------|
| EXTRACT-2 causes test failures | Revert branch, do not deploy |
| Seeds deployed but collector not yet enabled | No action needed — seeds are inert without flags |
| Seeds deployed, flag enabled, collector misbehaves | Set flag `false`, force-recreate app; seeds remain in DB (safe) |
| Need to remove a seed record | Write a one-off migration (DELETE by deterministic UUID); execute manually |

The seeder never deletes — it is purely additive. Removing a seed from `station_seeds.py`/
`source_seeds.py` does not remove the DB row; it only prevents re-creation on restart.

---

## 11. Post-EXTRACT-2 Enabling Sequence (future pass, not in scope here)

After EXTRACT-2 is merged and deployed:

1. **Verify all 8 UUIDs FOUND** in production (§9 check script)
2. **VAL-* confirmations required** before each flag:
   - `ENABLE_BBC_RADIO1_COLLECTOR=true` requires VAL-BBC1-001 (live reachability) + VAL-BBC1-006 (ToS)
   - `ENABLE_HEART_COLLECTOR=true` requires VAL-HEARTFM-002 (live CSS selectors)
   - `ENABLE_Z100_COLLECTOR=true` requires VAL-Z100-001 (live station_id=614)
   - `ENABLE_WKSC_COLLECTOR=true` requires VAL-WKSC-001 (live station_id=821)
   - `ENABLE_IHEART_TOP_SONGS=true` requires VAL-IHEART-TOP-001 (top songs schema)
3. **One flag at a time**, with 24h passive observation before next
4. **Never enable more than one new collector per deployment**

---

## 12. Implementation Branch

Branch: `feat/recon2-station-seeds-new-stations`
Base: `main` after EXTRACT-1B (PR #12) merges

Files to change:
- `app/domain/entities/source.py` — add `BBC_SOUNDS`, `HEART_LAST_PLAYED` to `SourceType`
- `app/application/source_config/station_seeds.py` — 4 new `StationSeed` entries
- `app/application/source_config/source_seeds.py` — 8 new `SourceSeed` entries (4 primary + 4 CSV fallback)
- `tests/` — new seeder UUID-match tests, new SourceType enum tests

Files explicitly NOT changed:
- `migrations/` — no new migration files
- `app/infrastructure/scheduler/scheduler.py` — already done in EXTRACT-1B
- `app/core/settings.py` — no new flags
- `.env.production` — no changes
- Any UI, admin, auth, Docker, or nginx files
