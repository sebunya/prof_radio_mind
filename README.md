# Radio Music Intelligence & Automation System (RMIAS)

A resilient radio music intelligence platform for automated airplay extraction, daily reporting, and future playlist intelligence.

---

## Project Status

**Pass 1 complete** — project skeleton, health endpoint, Docker Compose.
*The repo contains additional implementation beyond the original Pass 1 skeleton; documentation is being reconciled through pass-based updates.*

See [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) for the full pass plan.

---

## Prerequisites

- Python 3.12+
- Docker and Docker Compose (for containerised development)

---

## Local Development Setup

### 1. Clone and enter the project

```bash
git clone git@github.com:sebunya/prof_radio_mind.git
cd prof_radio_mind
```

### 2. Create a virtual environment

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies (including dev tools)

```bash
pip install -e ".[dev]"
```

### 4. Copy the environment file

```bash
cp .env.example .env
```

> The `.env` file is gitignored. Never commit secrets.

### 5. Run the app locally

```bash
uvicorn app.main:app --reload
```

The API will be available at http://localhost:8000

Health check: http://localhost:8000/health

---

## Running Tests

```bash
pytest
```

---

## Linting

```bash
ruff check .
```

To auto-fix:

```bash
ruff check . --fix
```

---

## Type Checking

```bash
mypy app/
```

---

## Docker Compose

### Build and start all services (app + PostgreSQL)

```bash
cp .env.example .env
docker compose up --build
```

Health check: http://localhost:8000/health

### Stop services

```bash
docker compose down
```

### Destroy volumes (database data)

```bash
docker compose down -v
```

---

## Project Structure

```
app/                    FastAPI application
  api/routes/           API route handlers
  domain/               Domain entities and value objects (Pass 3+)
  application/          Use cases and ports (Pass 3+)
  infrastructure/       Collectors, parsers, DB repos (Pass 4+)
tests/
  fixtures/             HTML, JSON, CSV, golden test fixtures
  unit/                 Unit tests (fixture-driven, no live network)
  integration/          Integration tests against local DB only
migrations/             Alembic schema migrations (Pass 2+)
docs/
  deployment/           Hetzner Cloud runbook and production checklists
  adr/                  Architecture Decision Records
  IMPLEMENTATION_PLAN.md
  VALIDATION_REGISTER.md
  AGENT_TASKS.md
```

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | /health | Service health check |

---

## Architecture

Modular monolith with Clean Architecture.
Full architecture decisions documented in [docs/adr/0001-mvp-architecture.md](docs/adr/0001-mvp-architecture.md).
