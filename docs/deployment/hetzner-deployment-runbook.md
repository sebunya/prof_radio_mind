# Hetzner Cloud Production Deployment Runbook

This runbook guides you through provisioning, configuring, securing, and deploying the Radio Music Intelligence & Automation System (RMIAS) to Hetzner Cloud.

---

## 1. Server Provisioning & Hardware Specification

### Recommended VM Sizing
* **Minimum / MVP Specification**: `CX21` or `CPX21` (2 vCPU, 4 GB RAM, 40 GB NVMe).
* **High Load / High Volume Specification** (needed if parsing > 5 stations concurrently or if browser automation/Playwright is added in the future): `CX31` or `CPX31` (4 vCPU, 8 GB RAM, 80 GB NVMe).

### Server Provisioning Checklist
1. Log in to the [Hetzner Cloud Console](https://console.hetzner.com).
2. Choose your project and click **Add Server**.
3. **Location**: Select Falkenstein (`eu-central`) or Nuremberg (`eu-central`) for low latency to third-party third-party servers.
4. **Image**: Select **Ubuntu 24.04 LTS** (default, clean).
5. **Type**: Shared vCPU (AMD/Intel) is sufficient. Select `CX21`.
6. **SSH Keys**: Add your public SSH key (do not use root passwords).
7. **Volume**: If storing raw payloads locally (without Hetzner S3 Object Storage), attach a separate Block Volume (e.g. 50-100 GB) for `/data/raw_payloads`.
8. **Backups**: Enable Hetzner Backups (€0.99/month extra) for server snapshots.
9. Click **Create & Buy**.

---

## 2. Firewall and Network Security Configuration

Hetzner Cloud Firewall must restrict incoming traffic. Ports 8000 and 5432 must NEVER be publicly exposed.

### Hetzner Cloud Firewall Rules
Create a firewall named `rmias-firewall` and apply it to the server:

| Direction | Port / Protocol | Source IP | Description |
|---|---|---|---|
| Inbound | `22 / TCP` | `Any` (or admin IP range) | SSH administration |
| Inbound | `80 / TCP` | `Any` | HTTP (Caddy/Nginx ACME challenge) |
| Inbound | `443 / TCP` | `Any` | HTTPS (Public API and Admin UI) |
| Inbound | Other ports | `Blocked` | Ports `8000` and `5432` are blocked |
| Outbound | `Any` | `Any` | Allow all outbound traffic |

### Local Server Firewall Setup (UFW)
Log in via SSH and apply local rules as a secondary defense layer:
```bash
# SSH as root
apt-get update && apt-get install -y ufw

# Deny all incoming by default, allow outgoing
ufw default deny incoming
ufw default allow outgoing

# Allow standard ports
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp

# Enable firewall
ufw enable
```

---

## 3. DNS Configuration

Point your domain or subdomain to the Hetzner server's public IPv4 and (optional) IPv6 addresses.

* **A Record**: Point `radio.yourdomain.com` to the server's public IPv4.
* **AAAA Record**: Point `radio.yourdomain.com` to the server's public IPv6 (if configured).
* **TTL**: Set to `300` (5 minutes) initially to support fast rollback/switchover.

---

## 4. Server Dependencies & Deploy User Configuration

Set up a dedicated non-root user `deploy` and install Docker.

```bash
# Install Docker and git
apt-get install -y docker.io docker-compose-plugin git curl

# Create deploy user
useradd -m -s /bin/bash deploy
usermod -aG docker deploy

# Copy authorized SSH keys to deploy user
mkdir -p /home/deploy/.ssh
cp ~/.ssh/authorized_keys /home/deploy/.ssh/
chown -R deploy:deploy /home/deploy/.ssh
chmod 700 /home/deploy/.ssh
chmod 600 /home/deploy/.ssh/authorized_keys
```

---

## 5. Application Deployment

Log in as the `deploy` user to complete the deployment:

```bash
# Switch to deploy user
su - deploy

# Clone the repository
git clone https://github.com/sebunya/prof_radio_mind.git rmias
cd rmias

# Create the production environment config file
cp .env.production.example .env.production
```

### Fill in Secrets in `.env.production`
Edit `.env.production` using `nano` or `vi`:
1. Generate `POSTGRES_PASSWORD` with `openssl rand -base64 32`.
2. Update the `DATABASE_URL` line to match the generated password.
3. Generate `API_KEY` with `python3 -c "import secrets; print(secrets.token_hex(32))"`.
4. Ensure the safety switches are explicitly disabled (`false`) for the first boot:
   ```env
   SCHEDULER_ENABLED=false
   ENABLE_NOVA_COLLECTOR=false
   ENABLE_KIIS_COLLECTOR=false
   ENABLE_CAPITAL_COLLECTOR=false
   ENABLE_NIGHTLY_RECONCILIATION=false
   ```

### Reverse Proxy Configuration (Nginx)
Verify that `/home/deploy/rmias/nginx/rmias.conf` has been configured with the correct domain:
```nginx
server_name radio.yourdomain.com;
ssl_certificate     /etc/letsencrypt/live/radio.yourdomain.com/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/radio.yourdomain.com/privkey.pem;
```

---

## 6. First Stack Launch and Let's Encrypt Setup

1. Check the Docker Compose configuration for syntax errors:
   ```bash
   docker compose -f docker-compose.hetzner.yml --env-file .env.production config
   ```

2. Generate the SSL certificate using Let's Encrypt / Certbot inside Docker by running a one-shot container before starting the main stack:
   ```bash
   # Request certificate via standalone Certbot image mapping port 80:
   docker run -it --rm -p 80:80 \
     -v /etc/letsencrypt:/etc/letsencrypt \
     -v /var/www/certbot:/var/www/certbot \
     certbot/certbot certonly --standalone \
     -d radio.yourdomain.com --agree-tos --email admin@yourdomain.com
   ```

3. Launch the RMIAS stack in daemon mode:
   ```bash
   docker compose -f docker-compose.hetzner.yml --env-file .env.production up -d --build
   ```

---

## 7. Database Migrations

Apply Alembic migrations to build the tables:

```bash
docker compose -f docker-compose.hetzner.yml --env-file .env.production \
  exec app alembic upgrade head
```

---

## 8. Log Management & Monitoring

Use the following commands to inspect execution logs:

```bash
# Check recent application logs
docker compose -f docker-compose.hetzner.yml logs --tail=100 -f app

# Search logs for errors
docker compose -f docker-compose.hetzner.yml logs app | grep ERROR

# View reverse proxy access logs
docker compose -f docker-compose.hetzner.yml logs -f nginx
```

---

## 9. Backup and Restore Procedures

> [!WARNING]
> Hetzner Cloud automatic server backups/snapshots **do NOT** include separate attached block volumes. If you mount `/data/raw_payloads` to an attached volume, it will not be backed up by server snapshots. You must run independent file backups.

### Database Backups (pg_dump)
Set up a daily cron job to dump the Postgres database:
```bash
# Run backup dump
docker compose -f docker-compose.hetzner.yml --env-file .env.production \
  exec db pg_dump -U rmias rmias | gzip > /home/deploy/backups/db/rmias-$(date +%F).sql.gz
```

### Raw Payload Storage Backups
Compress raw payload files (which serve as compliance audit evidence) from the named Docker volume:
```bash
docker run --rm -v rmias_raw_payloads:/volume -v /home/deploy/backups/payloads:/backup alpine \
  tar -czf /backup/raw-payloads-$(date +%F).tar.gz -C /volume .
```

### Database Restore Procedure
In case of server failure or corruption:
```bash
# Stop the app container
docker compose -f docker-compose.hetzner.yml stop app

# Drop and recreate the DB
docker compose -f docker-compose.hetzner.yml exec db dropdb -U rmias rmias
docker compose -f docker-compose.hetzner.yml exec db createdb -U rmias rmias

# Restore the dump file
gunzip -c /home/deploy/backups/db/rmias-YYYY-MM-DD.sql.gz | \
  docker compose -f docker-compose.hetzner.yml exec -T db psql -U rmias -d rmias

# Restart the app
docker compose -f docker-compose.hetzner.yml start app
```

---

## 10. Rollback Strategy

If a deployment fails or contains critical regressions:

1. Stop the current stack:
   ```bash
   docker compose -f docker-compose.hetzner.yml down
   ```

2. Revert the repository to the last stable release tag or commit hash:
   ```bash
   git checkout <stable-commit-hash>
   ```

3. If a database schema modification was applied, and downgrade is safe/necessary:
   ```bash
   # Optional: Downgrade DB to previous version
   docker compose -f docker-compose.hetzner.yml --env-file .env.production \
     exec app alembic downgrade -1
   ```

4. Rebuild and launch the stable stack:
   ```bash
   docker compose -f docker-compose.hetzner.yml --env-file .env.production up -d --build
   ```

---

## 11. Post-Deployment Smoke Testing

Verify the application state immediately after booting:

1. Request the health check from the host server:
   ```bash
   curl -f http://localhost:8000/health
   ```
   *Expected response*: `{"status":"ok","components":{"scheduler":"stopped",...}}`

2. Request the health check publicly through the HTTPS reverse proxy:
   ```bash
   curl -f https://radio.yourdomain.com/health
   ```
   *Expected response*: HTTP 200 with status `ok` and HTTPS connection secured.

3. Inspect application logs:
   ```bash
   docker compose -f docker-compose.hetzner.yml logs app
   ```
   Confirm the log prints:
   `Scheduler is disabled by configuration (SCHEDULER_ENABLED=false)`
   Verify that **no** collector runs are triggered.
