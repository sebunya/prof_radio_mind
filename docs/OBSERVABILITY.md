# RMIAS Observability Guide

RMIAS ships a full observability stack alongside the application:

| Tool | Purpose | Dev URL | Prod access |
|------|---------|---------|-------------|
| **PgHero** | PostgreSQL performance & query analysis | `http://localhost:8081` | SSH tunnel → port 8081 |
| **Uptime Kuma** | Service uptime & alerting | `http://localhost:3001` | SSH tunnel → port 3001 |
| **Grafana** | Log explorer & dashboards | `http://localhost:3000` | SSH tunnel → port 3000 |
| **Loki** | Log aggregation backend | `http://localhost:3100` | Internal only |
| **Promtail** | Docker log collector | N/A (no UI) | Internal only |
| **Sentry** | Error & performance monitoring | `https://sentry.io` | Public SaaS |

---

## Quick start (development)

```bash
docker compose up -d
```

All services start together.  The app, database, and observability stack are all included in the default `docker-compose.yml`.

---

## PgHero

PgHero gives you a real-time view into PostgreSQL: slow queries, index usage, bloat, connection counts, and more.

### Credentials

Set `PGHERO_USERNAME` and `PGHERO_PASSWORD` in `.env`.  Defaults to `admin`/`admin` in development — **change both before deploying to production**.

### Connection

PgHero reads the database via `PGHERO_DATABASE_URL`.  This must use the standard `postgres://` prefix (not `postgresql+asyncpg://`).

```env
PGHERO_DATABASE_URL=postgres://rmias:your_password@db:5432/rmias
```

### What to check regularly

- **Slow Queries** — queries with high mean execution time; add indexes if needed.
- **Index Usage** — tables with low index hit rate may need indexes or a `VACUUM ANALYZE`.
- **Space** — watch for table/index bloat.  Run `VACUUM ANALYZE` if bloat is high.
- **Connections** — if approaching `max_connections` (default 100), review connection pooling.

### Enabling query statistics

PgHero works best with `pg_stat_statements` enabled.  Run once as a superuser:

```sql
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
```

The RMIAS Docker Compose DB does not enable this by default (it requires a Postgres superuser).  You can add it to a custom `postgresql.conf` mounted into the `db` service.

---

## Uptime Kuma

Uptime Kuma monitors whether services are reachable and sends alerts when they go down.

### First-run setup

1. Open `http://localhost:3001` (or SSH tunnel in production).
2. Create an admin account — **this account is not set via env vars**; it is stored in the SQLite database inside the `uptime_kuma_data` volume.

### Recommended monitors to add

| Monitor name | Type | URL / address | Interval |
|---|---|---|---|
| RMIAS app | HTTP(S) | `http://app:8000/health` | 60 s |
| PostgreSQL | TCP port | `db:5432` | 60 s |
| RMIAS public URL | HTTP(S) | `https://rmias.example.com/health` | 60 s |
| Sentry (optional) | HTTP(S) | `https://sentry.io` | 300 s |

> **Internal Docker hostnames** (`app`, `db`) work when Uptime Kuma runs inside the same Docker Compose network.  For production, use the public hostname for the external-facing check.

### Notifications

Uptime Kuma supports Slack, Discord, email, Telegram, and many others.  Configure a notification channel under **Settings → Notifications** so you receive alerts when RMIAS goes down.

---

## Grafana Loki stack

The Loki stack gives you full-text log search across all Docker containers with structured filtering by `level`, `logger`, and `service`.

### Architecture

```
Docker containers
      │  (stdout/stderr JSON logs)
      ▼
  Promtail  ──push──▶  Loki  ◀──query──  Grafana
                       (storage)           (UI)
```

- **Promtail** reads container logs via `/var/run/docker.sock` and forwards them to Loki.
- **Loki** stores logs efficiently as compressed chunks, indexed by labels.
- **Grafana** queries Loki using LogQL and renders results as log panels or metrics.

### Logging format

Every RMIAS application log line is emitted as a JSON object:

```json
{"ts": "2025-01-15T08:00:00Z", "level": "INFO", "logger": "app.api.routes.stations", "service": "rmias", "msg": "stations listed count=12"}
```

Promtail extracts `level` and `logger` as Loki stream labels, enabling fast filtered queries.

### Querying logs in Grafana

1. Open `http://localhost:3000` → **Explore** → select **Loki** datasource.
2. Example LogQL queries:

```logql
# All RMIAS app logs
{service="app"}

# Only errors from any container
{service="app"} | json | level="ERROR"

# Slow SQL or scheduler issues
{service="app"} | json | logger=~"sqlalchemy.*|apscheduler.*"

# Rate limit hits
{service="app"} | json | msg=~".*Rate limit.*"

# Log volume over time (metrics query)
sum(rate({service="app"}[5m])) by (level)
```

3. Use **Add to dashboard** to save queries as panels.

### Log retention

Logs are retained for **31 days** by default (configured in `config/loki/loki-config.yml` via `retention_period: 744h`).  Adjust to suit your disk budget.

### Grafana credentials

Default: `admin` / value of `GRAFANA_PASSWORD` env var (development default: `admin`).

**Change before going to production.**

---

## Production access (Hetzner)

Observability tools are bound to `127.0.0.1` only in the production compose file — they are never exposed directly to the internet.

Use an SSH tunnel to access them securely:

```bash
ssh -L 8081:localhost:8081 \
    -L 3000:localhost:3000 \
    -L 3001:localhost:3001 \
    user@your-hetzner-server
```

Then open in your local browser:
- `http://localhost:8081` — PgHero
- `http://localhost:3000` — Grafana
- `http://localhost:3001` — Uptime Kuma

---

## Sentry

Sentry captures unhandled exceptions and slow transactions from the RMIAS FastAPI application.

See [`docs/CONFIGURATION.md`](CONFIGURATION.md#sentry-error--performance-monitoring) for setup details.

The `/sentry-debug` endpoint (only available when `APP_ENV != production`) triggers a deliberate error to verify the Sentry integration is working.

---

## Production checklist (observability)

- [ ] `PGHERO_USERNAME` and `PGHERO_PASSWORD` set to non-default values
- [ ] `PGHERO_DATABASE_URL` matches production DB credentials
- [ ] `GRAFANA_PASSWORD` set to a strong value
- [ ] Uptime Kuma admin account created and monitors configured
- [ ] At least one notification channel configured in Uptime Kuma
- [ ] Sentry DSN set (`SENTRY_DSN`) and a test error verified in Sentry dashboard
- [ ] `pg_stat_statements` extension enabled in Postgres for PgHero slow-query tracking
- [ ] SSH tunnel documented / shared with all operators
