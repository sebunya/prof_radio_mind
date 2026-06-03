# Radio Music Intelligence & Automation System
# AntiGravity Handoff Note
# Pass CAP-UK-0 — Capital FM UK Identity, Source Candidate & Scheduler Safety Pass
# Last updated: 2026-06-03

---

## What This Pass Did

Pass CAP-UK-0 successfully audited the repository workspace, aligned the third MVP station to **Capital FM UK** (London, GB, 95.8 FM), candidate its automated source to Online Radio Box, and established robust safety gates for the background scheduler.

Key achievements:
1. **Workspace Verification**: Restored the Git tracking configuration in the empty MacBook folder `/Users/robertsebunya/Documents/Prof_Mind` and integrated the downloaded zip files to form a clean workspace tracking origin/main.
2. **Business Correction**: Corrected Capital FM's public identity from Sydney/Australia/96.1 FM to Capital FM UK (London, GB, 95.8 FM). Kept call sign `CAPITALFM` internally to preserve deterministic UUID5 IDs and avoid database orphans.
3. **Candidate Source Correction**: Changed the primary automated candidate for Capital FM UK from the unvalidated iHeart placeholder to the Online Radio Box candidate (`https://onlineradiobox.com/uk/capitalfmuk/`). Added `ONLINE_RADIO_BOX` to the `SourceType` StrEnum.
4. **Scheduler Gating**: Implemented settings flags (`SCHEDULER_ENABLED`, `ENABLE_NOVA_COLLECTOR`, `ENABLE_KIIS_COLLECTOR`, `ENABLE_CAPITAL_COLLECTOR`, `ENABLE_NIGHTLY_RECONCILIATION`) in `Settings` and `.env.example`.
5. **Lifespan Context & Job Registration Protection**: Updated `main.py` lifespan and `scheduler.py` job registration to respect these switches. By default, the scheduler is disabled and registers zero jobs, preventing unauthorized or accidental live scraping.
6. **Validation Adaptation**: Created the `CapitalOnlineRadioBoxValidationAdapter` to validate reachability for the candidate page and registered it in the sources route.
7. **Quality Gates & Tests**: Added and updated unit tests (e.g. source seeds country test, scheduler gating, validation adapter tests) and updated a failing lifespan health test to match the disabled-by-default scheduler. All 307 unit tests, ruff check, and mypy check pass cleanly.

---

## Exact Files Changed

### Created
- `docs/passes/CAP-UK-0-capital-fm-uk-amendment-plan.md` — Technical plan and risk assessment
- `docs/passes/CAP-UK-0-task.md` — Tasks progress checklist

### Modified
- `app/domain/entities/source.py` — Added `ONLINE_RADIO_BOX` enum value
- `app/application/source_config/station_seeds.py` — Updated Capital FM UK station seed metadata and added UUID compatibility comment
- `app/application/source_config/source_seeds.py` — Updated Capital automated and manual CSV source seeds and wrapped validation notes strings
- `app/core/settings.py` — Added scheduler master switch and per-collector gating flags
- `app/main.py` — Gated scheduler startup/shutdown in lifespan context manager
- `app/infrastructure/scheduler/scheduler.py` — Gated individual job registrations in `build_scheduler()` and added logging
- `app/application/validation/adapters/capital.py` — Added `CapitalOnlineRadioBoxValidationAdapter` for reachability tests
- `app/api/routes/sources.py` — Registered the new validation adapter and annotated type variable
- `.env.example` — Added and documented new scheduler environment variables
- `README.md` — Added note clarifying project implementation status
- `docs/IMPLEMENTATION_PLAN.md` — Corrected station identity, candidate source type, scheduler safety, and database migration risks
- `docs/VALIDATION_REGISTER.md` — Rewrote Capital validation checks (VAL-CAPUK-ORB-001 to VAL-CAPUK-ORB-008) and updated validation progress summary table
- `docs/AGENT_TASKS.md` — Updated Capital seeds and source strategy checklist items
- `tests/unit/application/test_source_config.py` — Updated station seeds unit test to check GB country code
- `tests/unit/application/test_capital_validation.py` — Imported and tested the new validation adapter
- `tests/unit/test_scheduler.py` — Updated tests to verify default and conditional job registration
- `tests/unit/test_observability.py` — Updated lifespan test to check health status under enabled/disabled scheduler configurations

### Intentionally Not Touched (Protected)
- `app/infrastructure/collectors/kiis_iheart.py` (KIIS collector)
- `app/infrastructure/collectors/nova_radiowave.py` (Nova collector)
- `app/infrastructure/collectors/base.py` (Base collector lifecycle)
- `app/api/routes/reports.py` (Reports routes)
- `app/api/routes/playlist.py` (Playlist routes)
- `app/api/routes/review.py` (Review queue routes)
- `app/api/routes/charts.py` (Charts routes)
- `app/api/routes/webhooks.py` (Webhooks routes)
- `app/api/routes/proof_of_play.py` (Proof-of-play routes)
- `app/api/routes/backfill.py` (Backfill routes)

---

## Quality Gates Results

| Gate | Status | Detail |
|---|---|---|
| pytest | PASSED | 307 unit tests passed, 2 skipped (database integration tests) |
| ruff check app/ | PASSED | No errors found |
| mypy app/ | PASSED | Success: no issues found in 109 source files |
| Live-network calls in tests | CLEAN | TestClient and mocks only, no external calls |

---

## Risks Remaining & Next Steps

1. **Parser Implementation**: The Online Radio Box HTML parser for Capital FM UK has not been built yet. Automated polling remains disabled until the parser is implemented.
2. **Database Migration**: The DB seeder only inserts missing rows. Deployed databases that already seeded the old Capital Sydney station require controlled database update/data correction.
3. **Source Validation**: The source page and playlist HTML structures must be validated against real saved HTML fixtures.
4. **Polling Cadence & IP Safety**: Capital automated collection must observe conservative polling limits to prevent IP blocking.

## Next Recommended Pass
**CAP-UK-1 — Capital FM UK Online Radio Box Fixture and Parser Validation Pass**

Scope:
- Save real Online Radio Box HTML page as a test fixture.
- Implement HTML parser to extract current track, artist, title, and playlist history.
- Write unit tests using the HTML fixture to confirm parser correctness.
- Add drift detection and review item creation.
