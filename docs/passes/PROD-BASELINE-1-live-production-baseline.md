# PROD-BASELINE-1 — Live Production Baseline

This document freezes the baseline state of the live production setup for the Radio Music Intelligence & Automation System (RMIAS) on Hetzner Cloud.

---

## 1. Commit and Source Configuration
* **Target Domain**: `tenxradar.com` / `www.tenxradar.com`
* **Server IP**: `178.105.238.18`
* **Frozen Commit Hash**: `67278b9b2c889cc5db10c3c90248896f3719f926` (GitHub and local workspace fully aligned).
* **Workspace Directory (Server)**: `/opt/rmias`
* **Working Tree**: Clean.

---

## 2. Docker Container Status
All 4 containerised services are healthy and running:
* **rmias-app-1**: Up (healthy) — running Uvicorn FastAPI application.
* **rmias-db-1**: Up (healthy) — running PostgreSQL database (16-alpine).
* **rmias-nginx-1**: Up — running Nginx reverse proxy (1.27-alpine).
* **rmias-certbot-1**: Up — running Let's Encrypt Certbot.

---

## 3. Database Schema Status
* **Alembic Migration Version**: `b3c9d1f04a2e` (head).

---

## 4. Live Public Endpoint Verification
Verified over Cloudflare HTTPS:
* **`https://tenxradar.com/`** (GET) → `HTTP/2 200`
* **`https://tenxradar.com/health`** (GET) → `HTTP/2 200`
* **`https://www.tenxradar.com/`** (GET) → `HTTP/2 200`
* **`https://www.tenxradar.com/health`** (GET) → `HTTP/2 200`
* **`https://tenxradar.com/admin/`** (GET) → `HTTP/2 200` (serving admin dashboard HTML).

---

## 5. Security & Scheduler Safety Status
* **Scheduler Safety**: `SCHEDULER_ENABLED=false` is active in configuration; scheduler state is `stopped`.
* **Collectors**: `false` by default; all collectors are disabled.
* **Capital FM UK Parser**: `NOT_BUILT`.
* **Secrets**: No production database credentials or API keys are committed to the codebase; `.env.production` is gitignored.
