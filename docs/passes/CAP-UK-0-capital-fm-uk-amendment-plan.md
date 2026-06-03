# CAP-UK-0 — Capital FM UK Identity, Source Candidate, Scheduler Safety, Workspace Verification, Documentation Reconciliation and Claude-Code Preservation Pass

## Objective
The objective of this pass is to make a surgical amendment to the repository to correct the identity of Capital FM (from Sydney/Australia to London/United Kingdom/95.8 FM), candidate its source type to Online Radio Box, implement scheduler safety gating, reconcile the documentation, and verify the MacBook workspace.

## Business Correction
The third MVP station is **Capital FM UK** (London, GB, 95.8 FM), not Capital FM Sydney/Australia. The candidate automated source is Online Radio Box (`https://onlineradiobox.com/uk/capitalfmuk/`), which remains unvalidated.

## Local Workspace Verification Results
* **Project Folder**: `/Users/robertsebunya/Documents/Prof_Mind`
* **Git Root**: `/Users/robertsebunya/Documents/Prof_Mind`
* **Git Remote**: `https://github.com/sebunya/prof_radio_mind.git`
* **Branch before changes**: `master` (created and switched to `fix/cap-fm-uk-source-safety`)
* **Commit before changes**: `128e28c37b7e63064fbd0e885ce2110e9e4087c5`

## Current Repo Facts Found During Audit
1. **Capital Station Seed**:
   * call_sign: `CAPITALFM`
   * name: `Capital FM`
   * frequency: `96.1 FM`
   * city: `Sydney`
   * country_code: Defaults to `AU` (via `StationSeed` dataclass default)
2. **Capital Source Seed**:
   * station_call_sign: `CAPITALFM`
   * source_type: `SourceType.IHEART`
   * name: `Capital FM iHeart Now Playing`
   * base_url: `https://api.iheart.com/api/v3/live-meta/stream`
   * config: `{"station_id": "capitalfm"}`
   * priority: `1`
   * validation_note: `UNVALIDATED — VAL-CAP-001 must confirm iHeart station_id before enable`
3. **SourceType Enum**:
   * Defined in `app/domain/entities/source.py`.
   * Values: `RADIOWAVE`, `IHEART`, `MANUAL_CSV`, `UNKNOWN`.
   * `ONLINE_RADIO_BOX` does not exist yet.
4. **Seeder Behavior**:
   * Derives station ID deterministically using `uuid.uuid5(uuid.NAMESPACE_DNS, f"station.{call_sign}")`.
   * Derives source ID deterministically using `uuid.uuid5(uuid.NAMESPACE_DNS, f"source.{call_sign}.{source_type}")`.
   * Only inserts if record is missing (uses `repo.get_by_id(...) is None`). It does NOT update existing database rows.
5. **Scheduler Behavior**:
   * Starts unconditionally in `app/main.py` lifespan context manager.
   * Registers all 4 jobs unconditionally: `nova_daily_diary`, `kiis_now_playing`, `capital_now_playing`, `nightly_reconciliation`.
   * Does not check for environment flags or master switch.
6. **Settings**:
   * Defined in `app/core/settings.py` (inherits from `BaseSettings`).
   * Currently lacks any scheduler enable/disable switches or per-collector flags.
7. **.env.example**:
   * Lacks scheduler config flags.
8. **Docs**:
   * Mention "Capital Sydney" and/or "iHeart placeholder" source. Many references assume Pass 1 is the only thing complete.
9. **Tests**:
   * Unit tests assert that all station seeds default to `country_code == "AU"`.
   * Unit tests assert `build_scheduler()` registers exactly 4 jobs.

## Protected Modules
The following components must not be refactored, rewritten, or redesigned:
* Nova and KIIS collectors, parsers, and validation adapters.
* Repository patterns, database schemas, and FastAPI routes (except narrow changes for config mapping).
* Reports, Playlist, Review, Charts, Webhooks, and Proof-of-Play modules.
* Manual CSV importer (except for keeping Capital fallback tested).

## Files Likely to Change
* `app/domain/entities/source.py` (Add `ONLINE_RADIO_BOX` enum value)
* `app/application/source_config/station_seeds.py` (Correct Capital UK fields)
* `app/application/source_config/source_seeds.py` (Correct Capital source fields)
* `app/core/settings.py` (Add scheduler gating settings)
* `app/main.py` (Respect scheduler settings on startup/shutdown)
* `app/infrastructure/scheduler/scheduler.py` (Check flags before registering jobs)
* `app/application/validation/adapters/capital.py` (Add/adapt validations to target Online Radio Box candidate)
* `app/api/routes/sources.py` (Register Online Radio Box validator)
* `.env.example` (Document new scheduler flags)
* `docs/VALIDATION_REGISTER.md` (Update Capital FM section to reflect Online Radio Box candidate)
* `tests/unit/application/test_source_config.py` (Update tests to reflect corrected station country and source config)
* `tests/unit/test_scheduler.py` (Test conditional job registration)
* `tests/unit/application/test_capital_validation.py` (Update Capital validation tests)
* Other documentation files (README.md, docs/IMPLEMENTATION_PLAN.md, etc.)

## Deterministic UUID Risk Assessment
The seeder relies on `uuid.uuid5` hashing to compute IDs:
* Station ID: `uuid5(NS, "station.CAPITALFM")`
* Source ID: `uuid5(NS, f"source.CAPITALFM.{source_type}")`

If we rename `call_sign` to `CAPITALFMUK`, we change the deterministic Station UUID. This would orphan any existing DB records.
If we change `source_type` from `iheart` to `online_radio_box`, we change the Source UUID. This is acceptable for this pass because we are explicitly changing the candidate source type, but it means existing databases will contain the old `CAPITALFM.iheart` source as well as the new `CAPITALFM.online_radio_box` source.
**Decision Rule**:
We will keep `call_sign = "CAPITALFM"` as the stable internal key. We will amend only the business-facing fields: `name = "Capital FM UK"`, `frequency = "95.8 FM"`, `city = "London"`, `country_code = "GB"`. This keeps the pass highly surgical and avoids breaking existing database relationships.

## Scheduler Safety Risk Assessment
Starting the scheduler unconditionally could result in automated polling of unvalidated sources. We will implement settings flags:
* `scheduler_enabled: bool = False` (Global master switch)
* `enable_nova_collector: bool = False`
* `enable_kiis_collector: bool = False`
* `enable_capital_collector: bool = False`
* `enable_nightly_reconciliation: bool = False`

If `scheduler_enabled` is False, the scheduler is not started, and no jobs are registered or run. If it is True, only the explicitly enabled jobs are registered.

## Source Validation Risk Assessment
The candidate source `https://onlineradiobox.com/uk/capitalfmuk/` is unvalidated and parser logic has not been built yet. The validation adapter will return `FAILED` or `UNVALIDATED` status by default, and automated collection remains disabled.

## Existing DB Data Risk & Seeder Behavior
Since the seeder only runs `if existing is None`, already-seeded databases (e.g. locally or in testing environments) will not automatically update the `city` or `country_code` for `CAPITALFM`. A manual database update/migration would be required to modify existing records. We will document this risk in the migration section.

## Documentation Drift Risk
Documentation will be reconciled to reflect the true station status (Capital FM UK, London, 95.8 FM) and the new safety gates.

## Implementation Steps
1. Add `ONLINE_RADIO_BOX = "online_radio_box"` to `SourceType` StrEnum.
2. Update Capital station seed values in `station_seeds.py` (keeping call_sign as `CAPITALFM`).
3. Update Capital source seeds in `source_seeds.py` to use `ONLINE_RADIO_BOX` with the Online Radio Box URL and config.
4. Add scheduler gating parameters to `Settings` in `app/core/settings.py`.
5. Update `.env.example` to document the new environment variables (defaulting to `false`).
6. Update `app/main.py` lifespan context to gate scheduler startup.
7. Update `app/infrastructure/scheduler/scheduler.py` to conditionally register jobs based on settings flags.
8. Adapt validation adapters in `app/application/validation/adapters/capital.py` to target Online Radio Box.
9. Register the `online_radio_box` validator in `app/api/routes/sources.py`.
10. Update unit tests to reflect the new configurations and test the safety gating.
11. Update `VALIDATION_REGISTER.md` and other documentation files.
12. Run the quality gates (`pytest`, `ruff`, `mypy`).

## Verification & Test Plan
* Validate that `pytest` unit tests pass.
* Verify that unit tests for `station_seeds` and `source_seeds` confirm the new values.
* Verify that unit tests for the scheduler show it respects the new settings (no jobs registered by default, and conditional registration works).
* Verify that existing health and regression tests pass.

## Stop Condition
Once CAP-UK-0 is complete, stop. Do not proceed to parser implementation or live scraping.
