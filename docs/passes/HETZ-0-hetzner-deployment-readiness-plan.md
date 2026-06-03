# HETZ-0 — Hetzner Deployment Readiness, Production Safety and First-Deploy Runbook Pass

## Objective
The objective of this pass is to verify, reconcile, and harden the repository for a safe first deployment to Hetzner Cloud without actually deploying yet. We will ensure the configurations are safe, all safety gates (disabled-by-default scheduler, private ports, persistent storage volumes) are established, and a comprehensive runbook and checklists are documented.

## Current Repo State
* **Project Folder**: `/Users/robertsebunya/Documents/Prof_Mind`
* **Git Root**: `/Users/robertsebunya/Documents/Prof_Mind`
* **Git Remote**: `https://github.com/sebunya/prof_radio_mind.git`
* **Branch before changes**: `chore/hetzner-deployment-readiness` (branched from `fix/cap-fm-uk-source-safety`)
* **HEAD commit**: `2ececf0225e62bd803e0b70c1e27c11d706ce867`

## CAP-UK-0 Safety Verification
* **Capital UK Public Identity**: Seeded correctly as `Capital FM UK` / `95.8 FM` / `London` / `GB`.
* **Capital UK Stable Key**: call_sign `CAPITALFM` preserved to maintain deterministic Station UUID5 hash.
* **Capital UK Candidate Source**: Set to `online_radio_box` (Online Radio Box station page).
* **Capital UK Automated Source Validation**: Remains `UNVALIDATED` in seed database configuration and register.
* **Scheduler Safety**: Settings (`scheduler_enabled`, `enable_nova_collector`, `enable_kiis_collector`, etc.) default to `False`. The app starts without scheduling loops or active jobs by default, which is clean and safe for production.
* **No Live Network in Tests**: Unit tests use mocks and do not call the live Internet.

## Hetzner Target Architecture
```
        Internet
           │
           ▼
[ Hetzner Cloud Firewall ]  <-- Denies public 8000 and 5432 ports, allows 22, 80, 443
           │
           ▼
[ Reverse Proxy (Nginx) ]  <-- Publicly exposes ports 80/443, SSL termination
           │
           ▼ (Internal Docker Network "proxy")
    [ FastAPI App ]        <-- Internal only (port 8000), not exposed to host
           │
           ▼ (Internal Docker Network "internal")
    [ PostgreSQL 16 ]      <-- Internal only (port 5432), not exposed to host
           │
           ▼
  [ Named Volume ]         <-- Persistent data storage
```

## Protected Modules
The following components must not be refactored or rewritten:
* BaseCollector lifecycle, normalizer, and collectors (Nova, KIIS, Capital).
* Reporting, playlist, review, charts, webhooks, proof-of-play, and backfill modules.
* Core database models, migrations, and FastAPI routes (except narrow changes for configuration or deployment).

## Files Likely to Change
* `Dockerfile` — Fix target name issue by adding `AS production` to the base image to align with Compose configuration.
* `.gitignore` — Ensure it ignores all PEM keys, backups, and local secret directories.
* `docker-compose.hetzner.yml` — Verify and update configuration if needed to ensure secure bindings.
* `.env.production.example` — [NEW] Create template for production env.
* `docs/deployment/hetzner-deployment-runbook.md` — [NEW] Add Hetzner deployment runbook.
* `docs/passes/HETZ-0-hetzner-deployment-readiness-plan.md` — [NEW] Technical plan.
* `docs/passes/HETZ-0-task.md` — [NEW] Checklist file.

## Production Risk Assessment
1. **Unintended Scraping / Polling**: If scheduler or individual collectors run automatically on first boot, it could scrape endpoints without proper validation, leading to IP bans or database corruption. Gating flags default to false to mitigate this.
2. **Exposed Database Port**: If Postgres port `5432` is bound to `0.0.0.0`, the database is vulnerable to external port scanners. The compose file must restrict bindings to internal Docker networks only.
3. **Secret Commit**: Committing production credentials can compromise the host. `.gitignore` is updated to exclude `.env.production`.
4. **Volume Snapshot Caveat**: Hetzner server snapshots do not capture attached block volumes or may lead to database corruption if snapshots are taken during write. Backups must be done using `pg_dump` and file exports.

## Implementation Details

### 1. Dockerfile AS production Target
The existing `docker-compose.hetzner.yml` specifies `target: production` under the `app` service build section. The current `Dockerfile` does not name the stage (just `FROM python:3.12-slim`). To prevent build failure, we will update the Dockerfile to:
`FROM python:3.12-slim AS production`

### 2. .gitignore Enhancements
We will ensure that standard secret folders, certificates (`*.pem`, `*.key`), local data, and database backups are ignored in the repository:
```
# Secrets and keys
.env
.env.production
.env.staging
.env.*.local
*.pem
*.key
secrets/

# Runtime data & backups
data/
raw_payloads/
backups/
```

### 3. Production Environment Template
We will create `.env.production.example` with safe disabled-by-default parameters.

### 4. Deployment Documentation
We will document the server provisioning, DNS configuration, Hetzner Cloud firewall rules, Docker/Compose setup, database migrations, logs, backup/restore procedures, and rollback operations.

## Verification & Quality Gates
* Run `pytest` unit tests.
* Run `ruff check app/`.
* Run `mypy app/`.
* Run `docker compose -f docker-compose.yml config` and `docker compose -f docker-compose.hetzner.yml config` to verify syntax.
* Document any database migration or Docker test runs.
* Confirm no actual Hetzner provisioning or scraping is executed.
