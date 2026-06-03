# Production Deployment Checklist

Use this checklist to verify production readiness before pointing domain traffic to the live server.

---

## 1. Network & Infrastructure
- [ ] **Domain Registration**: Domain or subdomain is selected (e.g. `radio.yourdomain.com`).
- [ ] **DNS Records**: A/AAAA records point to the server's public IP address.
- [ ] **Firewall**: Hetzner Cloud Firewall is active, allowing only ports `22`, `80`, and `443` inbound.
- [ ] **Host Ports**: Ports `8000` (FastAPI) and `5432` (PostgreSQL) are restricted to the internal Docker network and not exposed to the host/Internet.
- [ ] **SSH Security**: Root password login is disabled. Deploy user connects via SSH key only.

---

## 2. Configuration & Secrets
- [ ] **.env.production**: Configured on the server from `.env.production.example`.
- [ ] **API_KEY**: Changed from default placeholder to a strong random token.
- [ ] **POSTGRES_PASSWORD**: Changed from default placeholder to a strong random password.
- [ ] **DATABASE_URL**: Set to use the updated `POSTGRES_PASSWORD`.
- [ ] **Git Protection**: Verified that `.env.production` is ignored by `.gitignore` and has not been committed.

---

## 3. Database & Persistence
- [ ] **Persistent Volume (DB)**: PostgreSQL container mounts to `postgres_data` volume to ensure data survives container restarts.
- [ ] **Database Migrations**: Applied all database schema modifications via `alembic upgrade head`.
- [ ] **Database Seeder**: Confirmed that the idempotent DB seeder ran successfully at startup and inserted default station and source configuration.

---

## 4. Raw Payloads & Object Storage
- [ ] **Persistent Volume (Evidence)**: Raw payload container folder mounts to `raw_payloads` volume or S3 storage.
- [ ] **Volume Hashing**: Hashing algorithm (SHA-256) is active and verified for all incoming payload writes.
- [ ] **Hetzner Object Storage (S3)**: If using S3, bucket credentials are set in `.env.production` and verify that the app connects.

---

## 5. Scheduler & Safety Gating
- [ ] **Scheduler Disabled by Default**: `SCHEDULER_ENABLED=false` is set in `.env.production` for initial deploy.
- [ ] **Collectors Disabled**: Nova, KIIS, and Capital collectors are disabled (`false`) in `.env.production`.
- [ ] **Nightly Reconciliation Disabled**: Reconciliation is disabled (`false`) in `.env.production`.
- [ ] **Accidental Polling Guard**: Verified that the log files confirm no collectors started at boot time.

---

## 6. Station Validation & Manual Fallbacks
- [ ] **Nova Status**: Primary source (Radiowave IDDS=11129) is validated or manual fallback is active.
- [ ] **KIIS Status**: Primary source (iHeart ID 2501) is validated or manual fallback is active.
- [ ] **Capital Status**: Automated Online Radio Box source remains unvalidated (`UNVALIDATED` status) and the collector is disabled.
- [ ] **Capital Fallback**: Capital Manual CSV fallback is active.
- [ ] **Report Safety**: No client-facing Capital reports will be generated automatically until validation or manual fallback is tested.

---

## 7. Backups & Monitoring
- [ ] **Database Dump Script**: `pg_dump` cron job is configured and active.
- [ ] **Raw Payloads Backup**: Payload backup job is configured and active.
- [ ] **Snapshot Warning**: Confirmed that backup scripts run independently of Hetzner Cloud snapshots (which do not cover attached volumes).
- [ ] **Health Monitoring**: External monitoring service (e.g. UptimeRobot) is set to check `/health` every 5 minutes.
- [ ] **Logs Rotation**: Log size limits (`max-size: 50m`) are configured on all Docker services to prevent disk exhaustion.
