# RMIAS Configuration Reference

Complete reference for all environment variables accepted by RMIAS.
Copy `.env.example` to `.env` and fill in values before starting the application.

> **Security rule**: Never commit `.env` to version control — it contains secrets.
> `.env` is in `.gitignore` by default.

---

## Quick-start

```bash
# 1. Copy the template
cp .env.example .env

# 2. Generate a strong API key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 3. Edit .env and set at minimum:
#    API_KEY, POSTGRES_PASSWORD, DATABASE_URL (matching password)
#    SMTP_* (or leave SMTP_HOST blank for dry-run mode)

# 4. Start
docker compose up -d
docker compose exec app alembic upgrade head
```

---

## Application

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ENV` | `development` | Runtime environment. Set to `production` to enable security warnings on missing API key. Valid values: `development`, `staging`, `production`. |
| `APP_HOST` | `0.0.0.0` | IP address uvicorn binds to. Use `0.0.0.0` inside Docker to accept external connections. |
| `APP_PORT` | `8000` | TCP port uvicorn listens on. Exposed through the Docker Compose `ports` mapping. |
| `BASE_URL` | *(empty)* | Public-facing base URL used to build absolute links in outgoing emails (e.g. one-click unsubscribe). **No trailing slash.** Example: `https://rmias.shopgoldplus.com`. Leave blank to omit unsubscribe links (not recommended for production). |

---

## Database

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://rmias:rmias@db:5432/rmias` | Async SQLAlchemy connection URL for the application. **Must use the `+asyncpg` driver.** |
| `POSTGRES_DB` | `rmias` | Database name (used by the Docker Compose `db` service). |
| `POSTGRES_USER` | `rmias` | PostgreSQL user (used by the Docker Compose `db` service). |
| `POSTGRES_PASSWORD` | `rmias` | PostgreSQL password. **Change before deploying to production.** |
| `DB_PORT` | `5432` | Host port the Postgres container is exposed on (Docker Compose only). |

> **Scheduler job store**: APScheduler automatically creates an `apscheduler_jobs` table
> in the same PostgreSQL database using a separate sync psycopg2 connection (derived
> from `DATABASE_URL` by replacing `+asyncpg` with `+psycopg2`).  This persists
> scheduled fire-times across application restarts.  If the database is unreachable,
> the scheduler silently falls back to in-memory storage.

---

## Security

| Variable | Default | Description |
|----------|---------|-------------|
| `API_KEY` | *(empty)* | Master API key sent as `X-API-Key` header or `Bearer` token for all protected endpoints. **Leave blank in development only.** Generate with `openssl rand -hex 32`. |
| `CORS_ORIGINS` | *(empty = allow all)* | Comma-separated list of allowed CORS origins. Empty allows `*` which is fine when the API and frontend share an origin. Example: `https://rmias.example.com`. |
| `MAX_UPLOAD_BYTES` | `10485760` (10 MB) | Maximum size for backfill CSV upload requests. |
| `RATE_LIMIT_RPM` | `30` | Per-IP request rate limit (requests per minute) on rate-limited endpoints. Currently informational — enforcement middleware to be added. |

---

## Storage

| Variable | Default | Description |
|----------|---------|-------------|
| `RAW_PAYLOAD_STORAGE_PATH` | `/data/raw_payloads` | Local filesystem directory where raw collector payloads are persisted. Mount a named Docker volume at this path in production. |

---

## Email / SMTP (ZeptoMail)

RMIAS uses ZeptoMail (by Zoho) for email delivery.
Scheduled reports are sent via SMTP at:

| Cadence | UTC time | AEST time | Covers |
|---------|----------|-----------|--------|
| Daily | 22:00 | 08:00 next day | Yesterday (rolling 1-day window) |
| Weekly | Mon 22:00 | Tue 08:00 | Last 7 days (rolling 7-day window) |
| Monthly | 1st 22:00 | 2nd 08:00 | Last 30 days (rolling 30-day window) |

Leave `SMTP_HOST` blank to enable **dry-run mode**: email content is built and
logged to stdout but nothing is delivered.  This is the default and is safe for
development.

| Variable | Default | Description |
|----------|---------|-------------|
| `SMTP_HOST` | *(empty)* | SMTP relay hostname. Empty = dry-run mode. |
| `SMTP_PORT` | `587` | SMTP port. `587` = STARTTLS, `465` = implicit TLS, `25` = plain (not recommended). |
| `SMTP_USE_TLS` | `true` | Whether to use STARTTLS upgrade after connection. |
| `SMTP_USERNAME` | *(empty)* | SMTP authentication username. |
| `SMTP_PASSWORD` | *(empty)* | SMTP authentication password or API key. |
| `SMTP_FROM_EMAIL` | `reports@rmias.example.com` | The `From:` address that appears in sent emails. |
| `SMTP_FROM_NAME` | `RMIAS Radio Reports` | The display name that appears alongside `SMTP_FROM_EMAIL`. |

### ZeptoMail configuration

RMIAS uses **ZeptoMail** (by Zoho) as its email delivery provider.

```
SMTP_HOST=smtp.zeptomail.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=emailapikey
SMTP_PASSWORD=<your ZeptoMail SMTP token>
SMTP_FROM_EMAIL=reports@shopgoldplus.com
SMTP_FROM_NAME=RMIAS Radio Reports
```

**Where to find your credentials:**
1. Log in to [app.zeptomail.com](https://app.zeptomail.com)
2. Go to **Mail Agents** → select or create your mail agent
3. Copy the **SMTP Token** — this is your `SMTP_PASSWORD`
4. The username is always the literal string `emailapikey` (not your email address)
5. Under **Sender Domains / Addresses**, verify the domain or address you want to use as `SMTP_FROM_EMAIL`

> **Note:** ZeptoMail requires the sender address to be verified before it will
> accept outbound mail.  If you see an authentication or sender-not-allowed error,
> check that `SMTP_FROM_EMAIL` matches an address you have verified in the ZeptoMail
> dashboard.

---

## Trend Alerts

RMIAS fires webhook events nightly (23:00 UTC) when songs cross configured thresholds.

| Variable | Default | Description |
|----------|---------|-------------|
| `TREND_PLAYS_THRESHOLD` | `50` | Minimum plays in a rolling 7-day window to trigger a `song.trending` webhook event. The event is **edge-triggered**: it fires exactly once — the first night the threshold is crossed — not every subsequent night. |
| `TREND_NEW_ENTRY_PLAYS` | `10` | Minimum plays in a song's first 7-day window (zero plays in the preceding 7 days) to fire a `song.new_entry` event. Captures breakout new releases before they reach the trending threshold. |

### Webhook event types

Register a webhook at `POST /webhooks` and subscribe to any of:

| Event | When fired |
|-------|-----------|
| `song.trending` | Song crosses `TREND_PLAYS_THRESHOLD` plays in 7 days for the first time |
| `song.new_entry` | Brand-new song reaches `TREND_NEW_ENTRY_PLAYS` plays in its debut week |
| `song.aria_match` | A played song is currently ranked on the ARIA Singles chart |
| `play.detected` | Any new play event is recorded (high-volume — use with care) |

---

## Proxy Rotation

| Variable | Default | Description |
|----------|---------|-------------|
| `PROXY_URLS` | *(empty)* | Comma-separated list of proxy URLs for outbound collector HTTP requests. Supports `http://` and `socks5://` schemes. Leave blank for direct connections. Example: `http://user:pass@proxy1:8080,socks5://proxy2:1080` |

---

## Sentry (Error & Performance Monitoring)

Leave `SENTRY_DSN` blank to disable Sentry — this is the safe default for development.

| Variable | Default | Description |
|----------|---------|-------------|
| `SENTRY_DSN` | *(empty)* | Sentry Data Source Name. Get it from **Sentry → Project → Settings → Client Keys (DSN)**. Leave blank to disable. |
| `SENTRY_TRACES_SAMPLE_RATE` | `0.1` | Fraction of transactions captured for performance monitoring. `0.1` = 10 % (production default). `1.0` = 100 % (development / debug only — high volume). |

### What gets captured

| Integration | What it captures |
|-------------|----------------|
| `FastApiIntegration` | Unhandled exceptions, request context (URL, method, headers, IP) |
| `SqlAlchemyIntegration` | Slow queries as breadcrumbs, DB query spans in transactions |
| `LoggingIntegration` | `ERROR`+ log records become Sentry events; `INFO`+ become breadcrumbs |

### Verification

With the app running in development (`APP_ENV=development`):
```
GET http://localhost:8000/sentry-debug
```
This triggers a deliberate `ZeroDivisionError`.  Within a few seconds you should see:
- An **error event** in Sentry → Issues
- A **performance transaction** in Sentry → Performance

The `/sentry-debug` route is automatically **removed** when `APP_ENV=production`.

---

## S3 / Object Storage

Leave `S3_ENDPOINT_URL` blank to use the local filesystem (`RAW_PAYLOAD_STORAGE_PATH`).

| Variable | Default | Description |
|----------|---------|-------------|
| `S3_ENDPOINT_URL` | *(empty)* | S3-compatible endpoint URL. Hetzner example: `https://fsn1.your-objectstorage.com`. |
| `S3_ACCESS_KEY_ID` | *(empty)* | AWS-style access key ID. |
| `S3_SECRET_ACCESS_KEY` | *(empty)* | AWS-style secret access key. |
| `S3_BUCKET_NAME` | `rmias-raw-payloads` | Bucket name (must exist before starting the app). |
| `S3_REGION` | `eu-central-1` | AWS region or equivalent for the chosen provider. |

---

## Observability

RMIAS ships PgHero, Uptime Kuma, and the Grafana/Loki stack as Docker Compose services.
They require the following environment variables (see also [`docs/OBSERVABILITY.md`](OBSERVABILITY.md)):

### PgHero

| Variable | Default | Description |
|----------|---------|-------------|
| `PGHERO_USERNAME` | `admin` | HTTP basic-auth username for the PgHero web UI. |
| `PGHERO_PASSWORD` | `admin` | HTTP basic-auth password for the PgHero web UI. **Change in production.** |
| `PGHERO_DATABASE_URL` | *(derived)* | PostgreSQL connection URL for PgHero. Use `postgres://` prefix (not `+asyncpg`). Example: `postgres://rmias:password@db:5432/rmias`. |

### Grafana

| Variable | Default | Description |
|----------|---------|-------------|
| `GRAFANA_PASSWORD` | `admin` | Admin password for the Grafana web UI. **Change in production.** |

> Uptime Kuma has no environment variables — create the admin account through its web UI on first run (`http://localhost:3001`).

---

## Production checklist

Before going live, verify:

- [ ] `APP_ENV=production`
- [ ] `API_KEY` set to a strong random value (`openssl rand -hex 32`)
- [ ] `POSTGRES_PASSWORD` changed from the default
- [ ] `DATABASE_URL` uses the production password
- [ ] `CORS_ORIGINS` set to the exact admin frontend origin (not `*`)
- [ ] `BASE_URL` set to the public hostname (enables one-click unsubscribe links in emails)
- [ ] `SMTP_HOST` configured — emails will not be delivered otherwise
- [ ] `SMTP_FROM_EMAIL` set to a domain you own (improves deliverability)
- [ ] Database migrations applied: `docker compose exec app alembic upgrade head`
- [ ] Initial recipient added via admin UI or `POST /email-reports/recipients`
- [ ] Webhook registered for `song.trending` / `song.new_entry` if alerts are needed
- [ ] Persistent Docker volumes configured for `postgres_data` and `raw_payloads`
- [ ] Backups enabled (Hetzner server backups + `pg_dump` cron or managed DB backups)
- [ ] `PGHERO_USERNAME` / `PGHERO_PASSWORD` changed from defaults
- [ ] `PGHERO_DATABASE_URL` matches production DB credentials
- [ ] `GRAFANA_PASSWORD` set to a strong value
- [ ] Uptime Kuma admin account created and monitors configured
- [ ] SSH tunnel documented for team access to observability services

See [`docs/HETZNER_DEPLOYMENT.md`](HETZNER_DEPLOYMENT.md) for the full step-by-step cloud deployment guide.
See [`docs/OBSERVABILITY.md`](OBSERVABILITY.md) for the full observability setup guide.
