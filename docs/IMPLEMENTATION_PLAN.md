# Radio Music Intelligence & Automation System
# Implementation Plan
# Pass 0 — Audit and Planning
# Last updated: 2026-05-24

---

## 1. Current Repo State

| Item | State |
|---|---|
| Repository | sebunya/prof_radio_mind |
| Active branch | claude/sweet-archimedes-DFSWo |
| Commits | 1 (Initial commit) |
| Files | README.md only |
| Language | None yet |
| Framework | None yet |
| Tests | None |
| Docker | None |
| Migrations | None |
| Dependencies | None |
| CI/CD | None detected |
| ADR system | None — being created in Pass 0 |

**Verdict:** Greenfield. No conflicting architecture. Full MVP stack can be laid down from scratch.

---

## 2. Target Architecture

### Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12+ |
| API framework | FastAPI |
| Database | PostgreSQL 16 |
| ORM | SQLAlchemy 2.x |
| Migrations | Alembic |
| Schema validation | Pydantic v2 |
| Scheduler | APScheduler |
| HTTP client | httpx |
| HTML parsing | BeautifulSoup4 + lxml |
| String matching | rapidfuzz |
| Testing | pytest + pytest-asyncio |
| Linting | ruff |
| Type checking | mypy |
| Containers | Docker Compose |

### Architecture Pattern

- Modular monolith
- Clean Architecture layers (domain / application / infrastructure / interfaces)
- Collectors behind application ports
- Parsers fixture-tested only
- Raw evidence preserved at every layer
- APScheduler invokes collection jobs
- API exposes health, admin, reports, exports, manual-import endpoints
- No live-network calls in unit tests
- No fake success at any layer

### Directory Target

```
rmias/
  app/
    main.py
    api/
      routes/
      dependencies.py
    domain/
      entities/
      value_objects/
      services/
      events/
    application/
      use_cases/
      ports/
      dto/
    infrastructure/
      database/
      collectors/
      parsers/
      exporters/
      scheduler/
      storage/
      logging/
    interfaces/
      cli/
  migrations/
  tests/
    fixtures/
      html/
      json/
      csv/
      golden/
    unit/
    integration/
  docs/
    adr/
  scripts/
  docker-compose.yml
  Dockerfile
  pyproject.toml
  README.md
```

---

## 3. Selected Stack

Final stack per cross-model audit (DeepSeek backbone, Qwen engineering detail, Gemini product framing):

- **Python 3.12+** — runtime
- **FastAPI** — API layer
- **PostgreSQL 16** — primary database
- **SQLAlchemy 2.x** — ORM (async-capable)
- **Alembic** — schema migrations
- **Pydantic v2** — data validation and DTOs
- **APScheduler** — job scheduling (not Celery)
- **httpx** — async HTTP client
- **BeautifulSoup4 + lxml** — HTML parsing
- **rapidfuzz** — fuzzy string matching for normalization
- **pytest** — test runner
- **pytest-asyncio** — async test support
- **ruff** — linting and formatting
- **mypy** — static type checking
- **Docker Compose** — local and production deployment

---

## 4. Pass Plan

| Pass | Name | Objective |
|---|---|---|
| 0 | Audit and planning | Inspect repo, create all planning docs, no code |
| 1 | Project skeleton | pyproject.toml, directory structure, Dockerfile, docker-compose.yml, ruff/mypy config, empty FastAPI app, health endpoint, README update |
| 2 | Core schema Phase A | Alembic init, Phase A migrations: users, roles, stations, station_markets, station_broadcast_days, sources, source_validations, source_route_priorities, collector_runs, raw_payloads, errors, alerts, audit_logs, system_settings |
| 3 | Domain model and ports | Domain entities, value objects, repository ports/interfaces, no infrastructure yet |
| 4 | Source configuration and validation framework | Source config registry, source route priority model, source validation adapter base, fixture tests |
| 5 | Collector framework | Base collector contract, collector run lifecycle, raw payload store, SHA-256 hashing, collector status tracking |
| 6 | Radiowave parser and collector | Nova 96.9 Radiowave diary fetcher, HTML parser, fixture tests, golden fixture, deduplication |
| 7 | KIIS/iHeart parser and collector | KIIS iHeart endpoint validator, HTTP 200 parser, HTTP 204 no-track handler, fixture tests |
| 8 | Capital validation and manual fallback | Capital source config, validation adapter, manual CSV import foundation |
| 9 | Manual CSV import | Upload endpoint, schema validation, row-level validation, import batch, audit log |
| 10 | Phase B schema | Artists, artist_aliases, songs, song_aliases, song_versions, song_matches, play_events, no_track_events, review_items |
| 11 | Normalization, matching, deduplication | Deterministic normalization, label-stripping, fuzzy matching, fingerprint dedup, review queue |
| 12 | Ranking engine | Daily snapshot mode, daily ranked mode, first/last seen, play counts, movement |
| 13 | Phase C schema + reports and exports | daily_reports, report_items, report_versions, exports, export_files, export_versions, CSV exporters |
| 14 | Report confidence, correction, versioning | Confidence scoring, corrected-report generator, version lineage, change summary |
| 15 | API and CLI | All MVP API endpoints, CLI commands for manual operations |
| 16 | Scheduler and reconciliation | APScheduler wiring, nightly reconciliation, gap detection, fallback promotion |
| 17 | Review queue | Review items, resolution workflow, admin actions |
| 18 | Observability and operations | Structured logging, health endpoints, alerts, error tracking |
| 19 | Security hardening | Input validation, rate limiting scaffold, secrets management |
| 20 | Deployment documentation | Runbook, operations manual, backup/restore, cost guide, handover package |
| 21 | Future design only | Playlist automation, DJ assist, proof-of-play — design docs only, no code |

**Rule:** Stop after each pass. Do not proceed to the next pass without explicit approval.

---

## 5. MVP Boundary

### Build now (Passes 1–20):

- Project skeleton
- Domain structure
- Station registry
- Source registry and validation
- Source priority model
- Collector framework
- Raw payload storage with SHA-256 hashing
- Radiowave parser and Nova collector
- KIIS/iHeart validator and collector
- Capital validation adapter
- Manual CSV import fallback
- Play events and no-track events
- Normalization, matching, deduplication
- Ranking
- Daily station report
- Master report
- CSV exports
- Report confidence scoring
- Report and export versioning
- Correction/backfill foundation
- Scheduler foundation
- Health endpoints
- Structured logs
- Fixture tests
- Golden CSV tests
- Docker Compose deployment

### Do not build in MVP:

- Playlist automation (design only in Pass 21)
- DJ assist UI
- Commercial/sponsored scheduling
- Proof-of-play engine
- Playout integrations
- Advanced dashboard UI
- Machine learning recommendations
- Multi-tenant billing
- ClickHouse analytics warehouse
- Temporal workflow engine
- Kubernetes deployment
- Celery/Redis queue
- Spotify enrichment (deferred to V1)
- Nova StreamTheWorld ICY collector (deferred to V1)
- Rebrowser/licensed dataset integration (deferred to V1)
- Radio-Australia (out of scope for this project)

---

## 6. Protected Architecture Decisions

| Decision | Rationale |
|---|---|
| Modular monolith first | Simplest deployment, full refactoring to microservices later if needed |
| FastAPI first | Async-native, Pydantic-integrated, typed |
| PostgreSQL first | Relational data fits airplay reporting model |
| APScheduler first | No Celery/Redis overhead for MVP |
| Fixture-driven tests | No live-network calls in unit tests |
| No Playwright by default | Use httpx/API/HTML routes first; Playwright only if documented and validated |
| No Celery/Redis in MVP | Not needed at MVP scale |
| No dashboard UI in MVP | CSV exports and API are sufficient |
| No playlist automation in MVP | Future-only |
| Manual CSV fallback required | Must work regardless of automation status |
| Capital automation is validation-gated | Do not assume automated Capital extraction works |
| KIIS HTTP 204 is not a failure | Persist as no_track_event |
| Raw payloads must be stored and hashed | SHA-256 integrity for every capture |
| Reports and exports must be versioned | Correction and backfill must be traceable |
| Low-confidence reports must be labelled | No silent low-quality output |
| Collectors must never fake success | Real statuses always |

To change any protected decision, create a new ADR in `docs/adr/` before implementation.

---

## 7. Source Strategy

### Nova 96.9

| Item | Value |
|---|---|
| Primary source | Radiowave Monitor diary |
| IDDS | 11129 |
| Role | Primary reporting source |
| MVP status | Committed |
| Fallback | Manual CSV |
| Deferred | StreamTheWorld ICY (V1 validation) |

### KIIS-FM

| Item | Value |
|---|---|
| Primary source | iHeart metadata endpoint (validated) |
| Station ID (unconfirmed) | 2501 |
| HTTP 200 | Produce play_event |
| HTTP 204 | Produce no_track_event, not failure |
| Secondary | Radiowave IDDS=5080 (if validated) |
| Tertiary | KIIS official HTML parser |
| Emergency | Manual CSV |
| MVP status | Committed with validation checkpoint |

### Capital FM London

| Item | Value |
|---|---|
| Primary source | First validated stable route |
| Routes to validate | Public last-played page, Global Player API, third-party diary, licensed/partner data |
| MVP status | Conditional — validation-gated |
| Automation launch blocker | No |
| Fallback | Manual CSV (always required regardless of automation) |
| Playwright | Not the default; only if httpx routes fail and reason is documented |

---

## 8. Database Phasing Plan

### Phase A — Core operational schema (Pass 2)

```
users, roles, stations, station_markets, station_broadcast_days,
sources, source_validations, source_route_priorities,
collector_runs, raw_payloads,
errors, alerts, audit_logs, system_settings
```

### Phase B — Airplay and metadata schema (Pass 10)

```
artists, artist_aliases, songs, song_aliases, song_versions, song_matches,
play_events, no_track_events, review_items
```

### Phase C — Reporting and export schema (Pass 13)

```
daily_reports, daily_report_items, report_confidence_scores,
report_versions, exports, export_files, export_versions
```

### Phase D — Fallback and enrichment schema (Pass 10 + deferred)

```
manual_imports, source_conflicts, enrichment_jobs, metadata_enrichment_records
```

**Rule:** Do not create all tables in one pass. Migrate in phases.

---

## 9. Test Strategy

### Rules

- All unit tests use fixtures. No live-network calls.
- Integration tests may hit a local Docker PostgreSQL only.
- No live radio website calls in any automated test.

### Required Test Coverage

| Test Type | Pass |
|---|---|
| Radiowave DOM parser | 6 |
| Radiowave deduplication | 6 |
| KIIS iHeart HTTP 200 | 7 |
| KIIS HTTP 204 no-track | 7 |
| KIIS no-track persistence | 7 |
| Capital validator | 8 |
| Manual CSV import | 9 |
| Raw payload hash | 5 |
| Normalization | 11 |
| Label-removal | 11 |
| Duplicate detection | 11 |
| Timezone | 2/11 |
| DST | 11 |
| Broadcast day | 11 |
| Ranking | 12 |
| Report confidence | 14 |
| Report/export versioning | 14 |
| Correction/backfill | 14 |
| Golden CSV | 13 |
| Failed-source isolation | 5/6/7 |
| Parser drift | 6/7 |
| API tests | 15 |
| Scheduler tests | 16 |
| Docker smoke tests | 20 |

### Quality Gates (must pass before declaring any pass complete)

- `pytest` passes
- `ruff check .` passes
- `mypy` passes if configured
- `alembic upgrade head` applies cleanly (once migrations exist)
- Docker Compose boots cleanly (once introduced in Pass 1)
- Golden CSV outputs match expected files

---

## 10. Deployment Plan

### MVP deployment target

Docker Compose on a single VPS or cloud VM.

### Components

- FastAPI application container
- PostgreSQL 16 container
- Persistent volume for database data
- Persistent volume for raw payload storage
- Shared .env for secrets (not committed)

### Future options (not MVP)

- Managed PostgreSQL (AWS RDS, Supabase)
- Object storage for raw payloads (S3-compatible)
- Managed alerting

---

## 11. Risks

| Risk | Severity | Status |
|---|---|---|
| Radiowave DOM selectors may have changed | High | Unvalidated — must fixture-test against a real snapshot |
| KIIS station ID 2501 is unconfirmed | High | Must validate before production use |
| KIIS iHeart endpoint stability | Medium | Unknown — must validate |
| Capital automated route | High | Completely unvalidated — gated |
| Capital public page may require JS rendering | Medium | Will determine during validation pass |
| Radiowave IDDS=5080 for KIIS | Medium | Not yet validated |
| Nova StreamTheWorld ICY | Low | Deferred, not MVP |
| Spotify enrichment | Low | Deferred, not MVP |
| Manual CSV schema drift | Low | Schema validation in Pass 9 mitigates |
| DST edge cases in timestamp grouping | Medium | DST tests required |
| Broadcast day definition mismatch with client | Medium | Must confirm with client before Pass 13 |
| Parser drift (Radiowave DOM changes) | Medium | Drift detection required in parser |
| iHeart 204/JSON call mismatch | High | Strict 204 guard required — no response.json() on empty body |

---

## 12. Next Pass

**Pass 1: Project skeleton**

- pyproject.toml with all MVP dependencies declared
- Directory structure created
- Empty FastAPI app with GET /health endpoint
- Dockerfile and docker-compose.yml
- ruff and mypy configuration
- .env.example
- .gitignore
- Updated README.md

Do not start Pass 1 without explicit approval.
