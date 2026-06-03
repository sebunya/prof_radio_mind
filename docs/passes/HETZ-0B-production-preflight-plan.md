# HETZ-0B — Production Deployment Preflight, Merge Hygiene, Docker Runtime Verification and TLS Strategy Review

## Objective
The objective of this preflight hardening pass is to verify, validate, and document repository and branch merge hygiene, resolve conflicting production environment templates, review and improve Nginx/TLS bootstrap procedures, and perform a real local Docker runtime validation (verifying container builds, migrations, and health checks inside Docker) prior to actual server deployment.

## Current Repo State
* **Project Folder**: `/Users/robertsebunya/Documents/Prof_Mind`
* **Branch**: `chore/hetzner-deployment-readiness`
* **HEAD commit**: `0e9b48e88bc0bcd2de93d5b907afaefa1793ee00`
* **Working tree**: Clean

## GitHub Branch & Merge Hygiene Audit
* **Local Branches**:
  * `master` (at `128e28c`)
  * `fix/cap-fm-uk-source-safety` (at `2ececf0`)
  * `chore/hetzner-deployment-readiness` (at `0e9b48e` - HEAD)
* **Remote Tracking (`origin/main`)**: Points to `128e28c` (matching local `master`).
* **Upstream Status**: Both `fix/cap-fm-uk-source-safety` and `chore/hetzner-deployment-readiness` are local-only and not yet pushed or merged to remote.
* **Handoff & Merge Recommendation**:
  1. Push `fix/cap-fm-uk-source-safety` and open a Pull Request for CAP-UK-0.
  2. Merge CAP-UK-0 into `main` after client verification.
  3. Rebase/merge `main` into `chore/hetzner-deployment-readiness`.
  4. Push `chore/hetzner-deployment-readiness` and open a Pull Request for HETZ-0 / HETZ-0B.
  5. Merge HETZ-0/HETZ-0B into `main`.
  6. Deploy to Hetzner only from the merged `main` branch or an official release tag.

## Production Config & Docker Runtime Validation Plan
To verify the Docker runtime, we will execute the following local preflight checks (if Docker is available):
1. Temporarily copy `.env.production.example` to `.env.production`.
2. Boot the production stack using `docker compose -f docker-compose.hetzner.yml up -d --build`.
3. Verify that all 4 containers (`app`, `db`, `nginx`, `certbot`) build and start successfully.
4. Execute database migrations in the container: `docker compose -f docker-compose.hetzner.yml exec app alembic upgrade head`.
5. Execute health smoke checks inside the container network to verify the application boots successfully, database connectivity is active, and the scheduler is in a stopped state.
6. Verify logs for clean startup.
7. Stop and dismantle the containers using `docker compose -f docker-compose.hetzner.yml down`.
8. Delete the temporary `.env.production`.

## TLS Strategy Review & Nginx Bootstrapping
* **Issue**: The Nginx configuration in `nginx/rmias.conf` expects Let's Encrypt SSL certificate files to exist on the host directory `/etc/letsencrypt/live/radio.yourdomain.com/...`. If Nginx starts inside Docker before these files exist, Nginx will fail to parse and crash immediately, preventing the Certbot container from verifying the HTTP-01 challenge.
* **Resolution**:
  * **Option A** (Standalone Certbot bootstrapping): The runbook documents running standalone Certbot on the host port 80 to obtain the certificate *before* booting the Docker Compose stack. UFW firewall permits port 80. Once certs are written to the host filesystem, the Docker Nginx container can start safely and mount the certificates. This is the simplest option and avoids modifying the Nginx reverse proxy architecture.
  * We will keep Nginx with this standalone Certbot bootstrapping method and update the runbook to make the sequence explicit.

## Env Template Authority Reconciliation
* **Issue**: Both `.env.hetzner` and `.env.production.example` serve as production configuration templates, creating risk of drift.
* **Resolution**:
  * We will deprecate `.env.hetzner` and delete it from the repository.
  * All documentation, runbooks, and compose configurations will reference `.env.production.example` as the single authoritative production template.

## Backup & Smoke-Test Wording Adjustments
1. **Raw Payloads Backup**: Compressing `/data/raw_payloads` from the host will fail because the folder does not exist on the host (it is a named Docker volume `rmias_raw_payloads`). We will update the backup command in the runbook to run a temporary Docker container mounting the volume:
   ```bash
   docker run --rm -v rmias_raw_payloads:/volume -v /home/deploy/backups/payloads:/backup alpine \
     tar -czf /backup/raw-payloads-$(date +%F).tar.gz -C /volume .
   ```
2. **Smoke Test Script**: Verify that `scripts/deploy/hetzner-smoke-test.sh` correctly checks that the scheduler is stopped using the `/health` endpoint response and adjust text to confirm it's a pre-deployment preflight test.

## Protected Modules
The following components remain protected and must not be changed:
* Core collectors, parsers, and validation adapters.
* Database models, schemas, and repositories.
* FastAPI app structure and routes.

## Files Likely to Change
* `.env.hetzner` [DELETE]
* `docker-compose.hetzner.yml` [MODIFY]
* `docs/HETZNER_DEPLOYMENT.md` [MODIFY]
* `docs/deployment/hetzner-deployment-runbook.md` [MODIFY]
* `docs/passes/HETZ-0B-production-preflight-plan.md` [NEW]
* `docs/passes/HETZ-0B-task.md` [NEW]

## Verification & Stop Condition
* All 307 unit tests must pass.
* Ruff and mypy linting must be clean.
* Docker Compose local runtime validation must run successfully.
* Once preflight validation is complete, stop. Do not deploy or SSH.
