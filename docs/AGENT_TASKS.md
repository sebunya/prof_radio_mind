# Radio Music Intelligence & Automation System
# Agent Tasks and Pass Checklist
# Pass 0 — Initial State
# Last updated: 2026-05-24

---

## Purpose

This document is the authoritative checklist for every implementation pass. It tracks protected decisions, quality gates, no-fake-success rules, and the exact scope of each pass. Any agent (Claude Code, AntiGravity, or human) working on this project must consult this document before making changes.

---

## Absolute Operating Rules

1. Audit before coding.
2. Create or update implementation_plan.md before implementation.
3. Work in controlled passes.
4. Stop after each pass.
5. Do not continue to the next pass without explicit approval.
6. Do not rewrite the whole project.
7. Do not "improve" unrelated files.
8. Do not introduce unnecessary frameworks.
9. Do not change protected architecture decisions without creating an ADR.
10. Do not fake success.
11. Do not silently swallow errors.
12. Do not mark a collector, report, export, import, or validation as successful unless it actually succeeded.
13. Do not make live websites part of unit tests.
14. Do not build future modules in MVP.
15. Do not create a fake success flow when data is missing, unvalidated, or low confidence.
16. Do not run `git add .`.
17. If committing, stage only exact files intentionally changed.
18. Report exact files created, modified, and intentionally untouched after every pass.
19. Run relevant quality gates before declaring completion.
20. If a quality gate cannot run, state exactly why.
21. Add or update repo-level docs after meaningful changes.
22. Leave a clear AntiGravity handoff note after every pass.
23. Prefer boring, reliable engineering over cleverness.
24. Prefer small reversible changes over large architectural jumps.
25. Do not hide risk. Document it.

---

## Protected Architecture Decisions

| Decision | ADR | Status |
|---|---|---|
| Modular monolith first | ADR-0001 | LOCKED |
| FastAPI first | ADR-0001 | LOCKED |
| PostgreSQL first | ADR-0001 | LOCKED |
| APScheduler first (no Celery/Redis) | ADR-0001 | LOCKED |
| Fixture-driven tests only | ADR-0001 | LOCKED |
| No live-network unit tests | ADR-0001 | LOCKED |
| No Playwright by default | ADR-0001 | LOCKED |
| No Celery/Redis in MVP | ADR-0001 | LOCKED |
| No dashboard UI in MVP | ADR-0001 | LOCKED |
| No playlist automation in MVP | ADR-0001 | LOCKED |
| Manual CSV fallback required | ADR-0001 | LOCKED |
| Capital automation is validation-gated | ADR-0001 | LOCKED |
| KIIS HTTP 204 is not a failure | ADR-0001 | LOCKED |
| Raw payloads must be stored and hashed | ADR-0001 | LOCKED |
| Reports and exports must be versioned | ADR-0001 | LOCKED |
| Low-confidence reports must be labelled | ADR-0001 | LOCKED |
| Collectors must never fake success | ADR-0001 | LOCKED |

**To change any protected decision:** Create a new ADR in `docs/adr/` with decision, reason, alternatives, impact, risk, and whether AntiGravity should review it. Do NOT implement the change before the ADR is written.

---

## Protected MVP Boundary

### Build in MVP

- Project skeleton
- Domain structure
- Station registry
- Source registry and validation
- Source priority model
- Collector framework
- Raw payload storage with SHA-256 hashing
- Radiowave parser (Nova 96.9 IDDS=11129)
- Nova Radiowave collector
- KIIS iHeart validator and collector (station ID 2501 after validation)
- KIIS HTTP 204 no-track handler
- Capital validation adapter
- Capital manual CSV fallback
- Play events
- No-track events
- Normalization and matching
- Deduplication
- Ranking (snapshot + ranked modes)
- Daily station report
- Master report
- CSV exports
- Report confidence scoring
- Report and export versioning
- Correction/backfill foundation
- APScheduler job scheduling
- Nightly reconciliation
- Health endpoints
- Structured logging
- Fixture tests
- Golden CSV tests
- Docker Compose deployment
- Operations runbook

### Do NOT build in MVP

- Playwright as default collector
- Celery or Redis
- Kubernetes
- Temporal
- ClickHouse
- Dashboard UI
- Playlist automation (design doc only in Pass 21)
- DJ assist UI
- Commercial/sponsored scheduling
- Proof-of-play engine
- Playout integrations
- Machine learning recommendations
- Multi-tenant billing
- Spotify enrichment (V1)
- StreamTheWorld ICY collector (V1)
- Rebrowser/licensed datasets (V1)
- Radio-Australia (out of scope)
- Complex BI warehouse

---

## No-Fake-Success Rules

A pass is NOT complete if any of the following are true:

- A collector reported success but the raw payload was not stored
- A collector reported success but the SHA-256 hash was not created
- A parser reported success but returned zero rows from a populated fixture
- A report was generated but the confidence score was not computed
- A report was generated but the source coverage data was missing
- A CSV export was reported as generated but the file does not exist
- A manual import was reported as successful but row validation was skipped
- A validation was reported as passed without running against a real response fixture
- A test was marked as passing but it called a live website

**Real collector statuses to use:**

```
scheduled
validating
fetching
raw_stored
parsed
normalized
persisted
completed
partial_success
failed
no_content
timeout
blocked
rate_limited
schema_changed
auth_required
manual_review_required
degraded
fallback_used
```

**Never use:** "success" without the underlying evidence stored and verified.

---

## Required Quality Gates

Before declaring any pass complete, the following must pass (or the reason for skip must be documented):

| Gate | When required | Skip condition |
|---|---|---|
| `pytest` | Every pass that adds or modifies code | No code added in this pass |
| `ruff check .` | Every pass that adds or modifies Python files | No Python files in this pass |
| `mypy .` | Every pass after mypy is configured | Not configured yet |
| `alembic upgrade head` | Every pass that adds migrations | No migrations in this pass |
| Docker Compose boots | After Pass 1 | Docker not yet introduced |
| Golden CSV match | After Pass 13 | Golden CSV not yet created |
| No live network calls in tests | Every test pass | N/A — always required |

---

## Pass-by-Pass Checklist

### Pass 0: Audit and Planning

**Objective:** Inspect repo, create all planning documents, no runtime code.

- [x] Repo state audited
- [x] docs/IMPLEMENTATION_PLAN.md created
- [x] docs/VALIDATION_REGISTER.md created
- [x] docs/AGENT_TASKS.md created
- [x] docs/ANTIGRAVITY_HANDOFF.md created
- [x] docs/adr/0001-mvp-architecture.md created
- [x] No collectors implemented
- [x] No migrations created
- [x] No dependencies added
- [x] No runtime behavior changed

**Quality gates run:** None required (docs only).

---

### Pass 1: Project Skeleton

**Objective:** Create working dev environment with FastAPI health endpoint and Docker Compose.

- [ ] pyproject.toml with all MVP dependencies declared
- [ ] src/rmias/ directory structure created
- [ ] FastAPI app boots
- [ ] GET /health returns 200
- [ ] Dockerfile created
- [ ] docker-compose.yml created
- [ ] .env.example created (no secrets committed)
- [ ] .gitignore created
- [ ] ruff configured
- [ ] mypy configured
- [ ] README.md updated with setup instructions
- [ ] `ruff check .` passes
- [ ] `pytest` passes (empty or skeleton tests)
- [ ] Docker Compose boots
- [ ] GET /health verified manually in container

**Quality gates required:** ruff, pytest, Docker Compose boot.

---

### Pass 2: Core Schema Phase A

**Objective:** Alembic initialized, Phase A migrations written and applied.

- [ ] Alembic initialized
- [ ] Migration: users, roles
- [ ] Migration: stations, station_markets, station_broadcast_days
- [ ] Migration: sources, source_validations, source_route_priorities
- [ ] Migration: collector_runs, raw_payloads
- [ ] Migration: errors, alerts, audit_logs, system_settings
- [ ] `alembic upgrade head` applies cleanly from empty DB
- [ ] `alembic downgrade base` works without data loss errors
- [ ] All timestamps stored in UTC
- [ ] SQLAlchemy models created for all Phase A tables
- [ ] `pytest` passes
- [ ] `ruff check .` passes
- [ ] `mypy .` passes

**Quality gates required:** pytest, ruff, mypy, alembic upgrade head.

---

### Pass 3: Domain Model and Ports

**Objective:** Domain layer entities, value objects, and repository port interfaces created. No infrastructure yet.

- [ ] Station entity
- [ ] Source entity and SourceType enum
- [ ] CollectorRun entity and CollectorStatus enum
- [ ] RawPayload value object
- [ ] PlayEvent entity
- [ ] NoTrackEvent entity
- [ ] Repository port interfaces (abstract base classes)
- [ ] No database code in domain layer
- [ ] `pytest` passes (domain unit tests)
- [ ] `ruff check .` passes
- [ ] `mypy .` passes

---

### Pass 4: Source Configuration and Validation Framework

**Objective:** Source config registry, route priority model, validation adapter base.

- [ ] Source config loader
- [ ] Station seeds (Nova, KIIS, Capital)
- [ ] Source seeds (Radiowave IDDS=11129, iHeart 2501 unconfirmed, Capital unvalidated)
- [ ] Source route priority records
- [ ] SourceValidationAdapter abstract base
- [ ] Source validation command (run validation against a fixture or live and store result)
- [ ] source_validations table populated on run
- [ ] `pytest` passes
- [ ] `ruff check .` passes
- [ ] `mypy .` passes

---

### Pass 5: Collector Framework

**Objective:** Base collector contract, lifecycle, raw payload store, SHA-256 hashing.

- [ ] BaseCollector abstract class with full lifecycle
- [ ] CollectorRun persistence
- [ ] RawPayload store (write to filesystem + record in DB)
- [ ] SHA-256 hash of every payload stored
- [ ] Collector status machine (all defined statuses)
- [ ] One collector failure does not stop other collectors
- [ ] fixture test: raw payload stored and hashed
- [ ] fixture test: failed collector does not propagate exception
- [ ] `pytest` passes
- [ ] `ruff check .` passes
- [ ] `mypy .` passes

---

### Pass 6: Radiowave Parser and Nova Collector

**Objective:** Nova 96.9 Radiowave diary fetcher, HTML parser, fixture tests.

- [ ] Save real Radiowave HTML as test fixture (manually, not in test code)
- [ ] Radiowave HTML parser implemented
- [ ] Parser extracts: artist, label (separated from artist), title, play timestamp, source_event_id
- [ ] Parser handles missing detail link
- [ ] Parser detects drift if row count drops unexpectedly
- [ ] Parser creates review_item on drift
- [ ] Nova Radiowave collector uses BaseCollector
- [ ] Fixture test: parser extracts correct data from saved HTML fixture
- [ ] Fixture test: label removed from artist field
- [ ] Fixture test: missing detail link handled
- [ ] Fixture test: drift detected and review_item created
- [ ] Deduplication: source_event_id matching
- [ ] Deduplication: fingerprint fallback
- [ ] VAL-NOVA-001 confirmed (or documented as unvalidated with fallback plan)
- [ ] VAL-NOVA-002 confirmed (DOM selectors match fixture)
- [ ] `pytest` passes
- [ ] `ruff check .` passes
- [ ] `mypy .` passes

---

### Pass 7: KIIS/iHeart Parser and Collector

**Objective:** KIIS iHeart endpoint validator, HTTP 200 parser, HTTP 204 no-track handler.

- [ ] Save real iHeart HTTP 200 JSON response as test fixture
- [ ] Save iHeart HTTP 204 (empty body) fixture
- [ ] iHeart parser for HTTP 200 payload
- [ ] KIIS HTTP 204 guard: never call response.json() on empty 204
- [ ] HTTP 204 persists as no_track_event with reason=commercial_break_or_talk
- [ ] Deduplication: repeated current-track observation handling
- [ ] KIIS collector uses BaseCollector
- [ ] Fixture test: HTTP 200 produces play_event
- [ ] Fixture test: HTTP 204 produces no_track_event, no exception
- [ ] Fixture test: repeated observation deduplicated
- [ ] Fixture test: failed KIIS does not stop Nova or Capital jobs
- [ ] VAL-KIIS-001: station ID 2501 confirmed or documented with risk note
- [ ] VAL-KIIS-003: HTTP 204 behavior confirmed
- [ ] `pytest` passes
- [ ] `ruff check .` passes
- [ ] `mypy .` passes

---

### Pass 8: Capital Validation and Manual Fallback

**Objective:** Capital source config, validation adapter, manual CSV import foundation.

- [ ] Capital station record created
- [ ] Capital source records (all candidate routes, initially unvalidated)
- [ ] Capital validation adapter (runs httpx checks, stores results)
- [ ] Capital validation runner script or command
- [ ] VAL-CAP-001 run and result stored
- [ ] VAL-CAP-002 run and result stored
- [ ] Capital manual CSV import pathway scaffolded (full implementation in Pass 9)
- [ ] Capital does not block Nova or KIIS reports if all Capital routes fail
- [ ] `pytest` passes
- [ ] `ruff check .` passes
- [ ] `mypy .` passes

---

### Pass 9: Manual CSV Import

**Objective:** Full manual CSV import pipeline.

- [ ] POST /manual-imports endpoint
- [ ] Schema validation (expected columns present)
- [ ] Row-level validation (date format, required fields)
- [ ] Import batch ID assigned
- [ ] Attribution: source = manual_csv
- [ ] Rows mapped to play_events
- [ ] Invalid rows produce import error records, not silent drops
- [ ] Import status tracked
- [ ] Audit log entry created
- [ ] Confidence penalty applied to manually imported events
- [ ] Fixture test: valid CSV imports successfully
- [ ] Fixture test: CSV with invalid rows produces error report
- [ ] Fixture test: import attributed to correct station
- [ ] `pytest` passes
- [ ] `ruff check .` passes
- [ ] `mypy .` passes

---

### Passes 10–20

Detailed checklists will be added in future planning docs at the start of each pass.

---

## Expected Report Format After Each Pass

After every pass, provide:

1. **Verdict:** Completed / Blocked / Partial
2. Repo state summary
3. Files created (list exactly)
4. Files modified (list exactly)
5. Files intentionally not touched
6. Commands run
7. Tests run and results
8. Quality gates run and results
9. Key decisions preserved
10. Risks remaining
11. What was intentionally not done
12. Next recommended pass
13. AntiGravity handoff summary
14. Exact suggested AntiGravity prompt for next step

---

## Source Strategy Reference

| Station | Primary | Secondary | Emergency |
|---|---|---|---|
| Nova 96.9 | Radiowave IDDS=11129 | (none in MVP) | Manual CSV |
| KIIS-FM | iHeart endpoint (val. req.) | Radiowave IDDS=5080 (val. req.) | Manual CSV |
| Capital FM | First validated route | (none confirmed) | Manual CSV |
