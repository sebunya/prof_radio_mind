# ADR-0001: MVP Architecture
# Status: Accepted
# Date: 2026-05-24
# Authors: Claude Code / AntiGravity / Project Owner

---

## Context

The Radio Music Intelligence & Automation System requires a foundational architecture decision before any implementation begins. Multiple AI models were consulted during the research and scoping phase (Gemini Deep Research, Qwen AI, DeepSeek, ChatGPT Deep Research). Their recommendations were audited and synthesized.

The final synthesis concluded that DeepSeek produced the strongest backbone, Qwen provided useful engineering concreteness, and Gemini provided useful product framing. Several contradictory recommendations from these models were identified and rejected.

This ADR locks the MVP architecture so that no future pass, agent, or developer can silently change these decisions without creating a new ADR.

---

## Decision

### Runtime Language

**Python 3.12+**

Rationale:
- Strong data and web ecosystem
- Async-native with asyncio
- First-class BeautifulSoup4, httpx, and SQLAlchemy support
- Fastest path to MVP for this problem domain

Rejected alternatives:
- TypeScript/Node.js (Qwen's BullMQ/Hono detour): rejected as contradictory to earlier Qwen output and less suitable for data-heavy media monitoring work
- Go: considered but rejected; Python has better HTML parsing and data ecosystem for this use case

### API Framework

**FastAPI**

Rationale:
- Pydantic v2 native
- Async-native
- Automatic OpenAPI documentation
- Strong community and ecosystem

Rejected alternatives:
- Django: overkill for modular monolith; ORM coupling is harder to layer correctly with Clean Architecture
- Flask: less opinionated; more boilerplate for async; no built-in Pydantic integration

### Database

**PostgreSQL 16**

Rationale:
- Relational model fits airplay reporting schema
- Strong JSONB support for raw payload metadata
- Native timezone support
- ACID compliance required for play events and report versioning

Rejected alternatives:
- MySQL: inferior timezone handling and JSONB support
- SQLite: not suitable for concurrent writes or production media monitoring
- ClickHouse: analytical warehouse — deferred to future version if scale requires it
- MongoDB: schema validation weaker; relational model better for airplay confidence and versioning

### ORM and Migrations

**SQLAlchemy 2.x + Alembic**

Rationale:
- Async-capable (asyncpg backend)
- Explicit mapping preferred for Clean Architecture (domain entities not tied to ORM models)
- Alembic is the standard migration tool for SQLAlchemy

Rejected alternatives:
- Tortoise ORM: less mature
- Drizzle: TypeScript-only (Qwen's BullMQ detour, rejected)
- Raw SQL only: not practical at scale; lose migration tooling

### Scheduler

**APScheduler**

Rationale:
- In-process scheduler; no broker dependency
- Simple to configure for cron-style jobs
- Sufficient for MVP collection frequency (sub-hourly to hourly)

Rejected alternatives:
- Celery + Redis: overkill for MVP; introduces broker infrastructure; rejected for MVP
- Temporal: overkill for MVP; deferred to future if workflow complexity grows
- Cron + systemd: less observable; harder to integrate with FastAPI lifecycle

### HTTP Client

**httpx**

Rationale:
- Async-native
- Supports HTTP/2
- Consistent interface for sync and async use
- Suitable for Radiowave diary and iHeart endpoint fetching

Rejected alternatives:
- requests: sync-only; not suitable for async FastAPI context
- aiohttp: more boilerplate; httpx interface is cleaner

### HTML Parser

**BeautifulSoup4 + lxml**

Rationale:
- Standard Python HTML parsing stack
- lxml backend is significantly faster than html.parser
- Sufficient for Radiowave diary DOM parsing

Rejected alternatives:
- Playwright: NOT the default. Playwright is validation-only in MVP. Only introduced if httpx-based routes are documented as insufficient. Requires an ADR.
- Selenium: heavier than Playwright; rejected for same reasons

### String Matching

**rapidfuzz**

Rationale:
- Fast, Cython-based fuzzy string matching
- Industry standard for deduplication and title/artist normalization
- Lightweight dependency

Rejected alternatives:
- fuzzywuzzy: slower; replaced by rapidfuzz
- Custom implementation: unnecessary

### Testing

**pytest + pytest-asyncio**

Rationale:
- Standard Python test framework
- pytest-asyncio handles async test functions
- No live-network calls in unit tests
- Fixture-driven test design

### Linting and Formatting

**ruff**

Rationale:
- Single tool replacing flake8, isort, pyupgrade, and others
- Significantly faster than older toolchain

### Type Checking

**mypy**

Rationale:
- Standard Python static type checker
- Works well with FastAPI and Pydantic v2

### Containers

**Docker Compose**

Rationale:
- Simple single-node deployment
- Sufficient for MVP
- FastAPI app + PostgreSQL + volume mounts

Rejected alternatives:
- Kubernetes: overkill for MVP; deferred to future
- Bare metal: less reproducible

---

## Architecture Pattern

**Modular Monolith with Clean Architecture**

Rationale:
- Simpler to deploy than microservices for MVP
- Clean Architecture layers prevent domain from coupling to infrastructure
- Easier to extract microservices later if needed
- Consistent with GoldPlus engineering discipline

### Layers

```
domain/       — entities, value objects, domain services, events
              — no external dependencies
application/  — use cases, ports (interfaces), DTOs
              — depends only on domain
infrastructure/ — collectors, parsers, database repos, exporters, scheduler, storage
               — implements application ports
interfaces/   — API routes, CLI
             — depends on application layer
```

Collectors are behind application ports. Domain entities do not import from infrastructure.

---

## Deferred Technologies

The following are explicitly deferred. Do not implement in MVP without a new ADR.

| Technology | When |
|---|---|
| Celery + Redis | V1 only if scale demands it |
| Temporal | Future if workflow complexity grows |
| ClickHouse | V2 if analytical warehouse is needed |
| Playwright | After documented failure of httpx routes |
| Spotify enrichment API | V1 |
| StreamTheWorld ICY collector | V1 |
| Rebrowser/licensed datasets | V1 |
| Kubernetes | Post-MVP scaling |
| Dashboard UI | V1 |
| Playlist automation | Future (design only in Pass 21) |
| DJ assist UI | Future |
| Commercial/sponsored scheduling | Future |
| Proof-of-play engine | Future |
| Playout integrations | Future |
| Machine learning recommendations | Future |
| Multi-tenant billing | Future |

---

## Protected Decisions

The following decisions are locked for MVP. Changing any of them requires a new ADR.

1. Modular monolith before microservices
2. FastAPI before any other API framework
3. PostgreSQL before any NoSQL or analytical warehouse
4. APScheduler before Celery/Redis
5. httpx before Playwright
6. Fixture-driven unit tests only — no live-network calls
7. Manual CSV fallback is mandatory for all stations
8. Capital automated collection is validation-gated — not assumed
9. KIIS HTTP 204 is a no_track_event — not a failure
10. Raw payloads must be stored with SHA-256 hashes
11. Reports and exports must be versioned
12. Low-confidence reports must be labelled
13. Collectors must never fake success
14. No `git add .` — stage only exact files

---

## Consequences

**Positive:**

- Simple deployment
- Clear layer boundaries
- Fixture-first testing is safe from site changes
- Manual CSV fallback prevents total data loss if automation fails
- Report versioning allows correction without destroying history
- Pass-based delivery prevents overbuilding

**Negative / Trade-offs:**

- APScheduler is in-process; if the process dies, scheduled jobs stop. Mitigation: health endpoint, Docker restart policy, nightly reconciliation detects missed runs.
- Modular monolith means a future migration to microservices will require refactoring. Mitigation: Clean Architecture boundaries make this easier than a big-ball-of-mud approach.
- No Playwright by default means Capital may not be automatable in MVP. Mitigation: Capital is validation-gated, not a launch blocker. Manual CSV fallback covers it.

---

## Review

This ADR was accepted at Pass 0 planning. It must be reviewed if any protected decision is challenged. Any change requires a new numbered ADR with full rationale.
