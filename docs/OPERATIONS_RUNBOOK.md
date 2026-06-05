# RMIAS Operations Runbook

**System:** Radio Music Intelligence & Automation System  
**Stack:** Python 3.12 / FastAPI / PostgreSQL 16 / APScheduler  
**Version:** 0.1.0 (MVP)

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Local Development](#local-development)
4. [Production Deployment (Docker Compose)](#production-deployment)
5. [Database Migrations](#database-migrations)
6. [API Reference](#api-reference)
7. [Scheduled Jobs](#scheduled-jobs)
8. [Review Queue Operations](#review-queue-operations)
9. [Log Format](#log-format)
10. [Health Monitoring](#health-monitoring)
11. [Troubleshooting](#troubleshooting)
12. [Security Notes](#security-notes)

---

## Prerequisites

| Tool        | Version   | Notes                          |
|-------------|-----------|--------------------------------|
| Python      | 3.12+     | Required for production code   |
| Docker      | 24+       | Container runtime              |
| Docker Compose | v2.20+ | Compose V2 syntax              |
| PostgreSQL  | 16+       | Managed via Docker in MVP      |

---

## Environment Setup

Copy the example env file and fill in secrets:

```bash
cp .env.example .env
```

**Required changes before production:**

| Variable | Default | Action Required |
|---|---|---|
| `POSTGRES_PASSWORD` | `change_me_in_production` | **Must change** |
| `DATABASE_URL` | asyncpg URL with default password | Update to match `POSTGRES_PASSWORD` |
| `APP_ENV` | `development` | Set to `production` |
| `MAX_UPLOAD_BYTES` | `10485760` (10 MB) | Tune if needed |
| `RATE_LIMIT_RPM` | `30` | Tune for expected traffic |

---

## Local Development

### Install dependencies

```bash
pip install -e ".[dev]"
```

### Run tests

```bash
python -m pytest
```

### Lint and type-check

```bash
python -m ruff check .
python -m mypy app/
```

### Start the API server (without Docker)

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Production Deployment

### First-time startup

```bash
# 1. Build images
docker compose build

# 2. Start database first (app waits for db healthcheck)
docker compose up -d db

# 3. Run migrations
docker compose run --rm app alembic upgrade head

# 4. Start application
docker compose up -d app
```

### Subsequent deploys

```bash
# Pull latest image or rebuild
docker compose build app

# Apply any new migrations
docker compose run --rm app alembic upgrade head

# Rolling restart (zero-downtime with a load balancer)
docker compose up -d --no-deps app
```

### Stop services

```bash
docker compose down          # preserves volumes
docker compose down -v       # WARNING: destroys database and raw payload volumes
```

### View logs

```bash
docker compose logs -f app   # follow app logs
docker compose logs -f db    # follow database logs
```

### Scale (future — requires load balancer)

```bash
docker compose up -d --scale app=2
```

> **Note:** The in-memory rate limiter and ReviewStore are single-process only. Horizontal scaling requires replacing them with Redis-backed equivalents.

---

## Database Migrations

RMIAS uses Alembic for schema migrations (three-phase schema):

| Phase | Migration file | Tables added |
|---|---|---|
| A | `ade166ae8d36_phase_a_initial_schema.py` | 14 core tables |
| B | `2fa7e19610e8_phase_b_events_schema.py` | artists, songs, play_events, no_track_events, review_items |
| C | `45770ddee81b_phase_c_reports_schema.py` | daily_reports, report_versions, exports |

### Apply all migrations

```bash
alembic upgrade head
```

### Check current revision

```bash
alembic current
```

### Rollback one revision

```bash
alembic downgrade -1
```

### Generate a new migration

```bash
alembic revision --autogenerate -m "describe the change"
```

> **Important:** The `DATABASE_URL` env var must use `postgresql://` (not `postgresql+asyncpg://`) when running Alembic directly. The `migrations/env.py` performs this substitution automatically.

---

## API Reference

All endpoints return JSON. Errors follow RFC 7807 Problem Details.

### Health

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness check with component status |

**Sample response:**
```json
{
  "status": "ok",
  "service": "radio-music-intelligence",
  "version": "0.1.0",
  "components": {
    "scheduler": "running",
    "review_queue_pending": 3
  }
}
```

### Stations

| Method | Path | Description |
|---|---|---|
| GET | `/stations` | List all active stations (NOVA969, KIISFM, CAPITALFM) |

### Manual Imports

| Method | Path | Description |
|---|---|---|
| POST | `/manual-imports/{station_id}` | Upload a CSV file for a station |

**Request:** `multipart/form-data` with `file` field (`.csv`, max 10 MB)

**CSV required columns:** `played_at`, `artist`, `title`, `source_type`

**Response (201):**
```json
{
  "batch_id": "uuid",
  "station_id": "uuid",
  "filename": "upload.csv",
  "status": "completed",
  "total_rows": 5,
  "imported_rows": 5,
  "error_rows": 0,
  "errors": []
}
```

**Error codes:** 400 (bad file type / empty), 413 (file too large), 422 (no importable rows), 429 (rate limited)

### Review Queue

| Method | Path | Description |
|---|---|---|
| GET | `/review-items` | List review items (`?status=pending\|reviewed\|dismissed\|escalated`) |
| GET | `/review-items/{id}` | Get a single review item |
| POST | `/review-items/{id}/resolve` | Mark as reviewed |
| POST | `/review-items/{id}/dismiss` | Dismiss as not actionable |
| POST | `/review-items/{id}/escalate` | Escalate for senior review |

**Resolve/dismiss/escalate body:**
```json
{
  "resolved_by": "operator@example.com",
  "notes": "Optional notes"
}
```

---

## Scheduled Jobs

Jobs are registered at startup via APScheduler (`AsyncIOScheduler`, timezone UTC):

All jobs are flag-gated and **disabled by default**. Enable only after the corresponding VAL checks pass.

| Job ID | Schedule | Flag | Description |
|---|---|---|---|
| `nova_daily_diary` | Cron: 16:00 UTC daily | `ENABLE_NOVA_COLLECTOR` | Nova 96.9 Radiowave diary (02:00 AEST) |
| `kiis_now_playing` | Interval: every 5 min | `ENABLE_KIIS_COLLECTOR` | KIIS-FM 106.5 (AU) iHeart now-playing poll |
| `capital_now_playing` | Interval: every 15 min | `ENABLE_CAPITAL_COLLECTOR` | Capital FM Online Radio Box now-playing scrape |
| `nightly_reconciliation` | Cron: 17:00 UTC daily | `ENABLE_NIGHTLY_RECONCILIATION` | Deduplication and normalization pass (03:00 AEST) |
| `nightly_report_generation` | Cron: 18:00 UTC daily | `ENABLE_NIGHTLY_REPORT_GENERATION` | Build DailyReport records for all active stations |
| `bbc_radio1_now_playing` | Interval: every 5 min | `ENABLE_BBC_RADIO1_COLLECTOR` | BBC Radio 1 RMS API now-playing poll |
| `heart_fm_last_played` | Interval: every 5 min | `ENABLE_HEART_COLLECTOR` | Heart FM last-played page scrape |
| `z100_now_playing` | Interval: every 5 min | `ENABLE_Z100_COLLECTOR` | Z100 (WHTZ) iHeart now-playing poll |
| `wksc_now_playing` | Interval: every 5 min | `ENABLE_WKSC_COLLECTOR` | WKSC 103.5 Kiss FM iHeart now-playing poll |
| `kiis_top_songs_daily` | Cron: 00:00 UTC daily | `ENABLE_IHEART_TOP_SONGS` | KIIS-FM 106.5 iHeart top songs chart (midnight) |
| `iheart_recently_played_hourly` | Interval: every 60 min | `ENABLE_IHEART_RECENTLY_PLAYED` | iHeart recently-played batch fallback (KIISFM, Z100, WKSC) |
| `kiis1027_radiowave_diary` | Cron: 09:00 UTC daily | `ENABLE_KIIS_RADIOWAVE_COLLECTOR` | KIIS-FM 102.7 LA Radiowave diary (01:00 PDT) |

See [VALIDATION_REGISTER.md](../VALIDATION_REGISTER.md) for full validation status and enablement order.

---

## Review Queue Operations

The review queue surfaces items that require human attention (drift detected, low confidence, parse errors, schema changes).

### Typical daily workflow

1. Check pending items:
   ```bash
   curl http://localhost:8000/review-items?status=pending
   ```

2. Inspect a specific item:
   ```bash
   curl http://localhost:8000/review-items/{item_id}
   ```

3. Resolve (confirmed correct):
   ```bash
   curl -X POST http://localhost:8000/review-items/{item_id}/resolve \
     -H "Content-Type: application/json" \
     -d '{"resolved_by": "operator@example.com", "notes": "Verified correct"}'
   ```

4. Dismiss (false positive):
   ```bash
   curl -X POST http://localhost:8000/review-items/{item_id}/dismiss \
     -H "Content-Type: application/json" \
     -d '{"resolved_by": "operator@example.com"}'
   ```

> **MVP limitation:** The review store is in-memory. Items are lost on application restart until the DB persistence layer is wired.

---

## Log Format

Logs are emitted as single-line JSON to stdout:

```json
{"ts": "2026-05-24T16:00:01Z", "level": "INFO", "logger": "app.infrastructure.scheduler.scheduler", "msg": "nova_diary_collected status=completed plays=48 no_tracks=0"}
```

| Field | Description |
|---|---|
| `ts` | UTC timestamp in ISO-8601 format |
| `level` | DEBUG / INFO / WARNING / ERROR |
| `logger` | Python logger name (module path) |
| `msg` | Log message |
| `exc` | Exception traceback (ERROR records only) |

### Log levels by component

| Component | Level |
|---|---|
| Application | INFO |
| APScheduler | WARNING (suppressed in production) |
| uvicorn.access | WARNING (suppressed in production) |
| httpx | WARNING (suppressed in production) |

---

## Health Monitoring

### Liveness probe

```
GET /health
```

Returns 200 if the application process is running. Use this for Docker/Kubernetes liveness probes.

### Key metrics to monitor (future)

- `review_queue_pending` — should stay near 0; spikes indicate collection issues
- `scheduler: running` — alert if this is `stopped`
- CSV import error rate — `error_rows / total_rows > 0.1` warrants investigation

### Docker health check

The `Dockerfile` includes a built-in healthcheck:

```
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
```

---

## Troubleshooting

### Application won't start

1. Check the database is healthy: `docker compose ps db`
2. Check migrations are applied: `docker compose run --rm app alembic current`
3. Verify `.env` has correct `DATABASE_URL`

### Scheduler jobs not running

1. Check `/health` — `components.scheduler` must be `"running"`
2. If `"stopped"`, the lifespan startup failed — check logs: `docker compose logs app`
3. APScheduler logs at WARNING level — lower to DEBUG temporarily:
   ```python
   logging.getLogger("apscheduler").setLevel(logging.DEBUG)
   ```

### CSV import failing with 422

The import returned 422 meaning no rows could be imported. Check:
- Required columns present: `played_at`, `artist`, `title`, `source_type`
- `played_at` format: `DD/MM/YYYY HH:MM` or ISO-8601
- File is not empty and is valid CSV

### High review queue

If `review_queue_pending` is growing:
1. List pending items: `GET /review-items?status=pending`
2. Check for pattern — all from same station or same date?
3. Could indicate a source schema change or parsing issue

### Rate limit errors (429)

The import endpoint is rate-limited to `RATE_LIMIT_RPM` requests per minute per IP.  
In development, reset the limiter by restarting the app (in-memory store is cleared).

---

## Security Notes

1. **Never commit `.env`** — it is gitignored; always use `.env.example` as template
2. **Change `POSTGRES_PASSWORD`** before any non-local deployment
3. **Rate limiting** is in-memory (single-process). Replace with Redis-backed limiter before horizontal scaling.
4. **Unvalidated VAL codes** — Nova and KIIS collectors must be validated before running in production. See VALIDATION_REGISTER.md.
5. **File uploads** are limited to `MAX_UPLOAD_BYTES` (default 10 MB). Adjust via env var.
6. **Non-root Docker user** — the app container runs as `rmias` (non-root) for reduced blast radius.
