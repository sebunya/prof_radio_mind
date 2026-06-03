# Hetzner Deployment Guide

Step-by-step instructions for running RMIAS on a Hetzner Cloud server.

---

## 1. Server provisioning

**Minimum recommended spec**: CX21 (2 vCPU, 4 GB RAM, 40 GB NVMe).
For > 5 stations or high-frequency polling, use CX31 (4 vCPU, 8 GB RAM).

1. In Hetzner Cloud Console, create a new server:
   - Image: **Ubuntu 24.04**
   - Location: closest to AU (Singapore `ap-southeast` or Falkenstein `eu-central`)
   - Add your SSH key
   - Enable backups (strongly recommended)

2. Point your domain at the server IP (A record).

---

## 2. Server setup

```bash
# SSH in as root, then:
apt-get update && apt-get upgrade -y
apt-get install -y docker.io docker-compose-plugin git curl ufw

# Lock down the firewall — only SSH, HTTP, HTTPS
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable

# Create a non-root deploy user
useradd -m -s /bin/bash deploy
usermod -aG docker deploy
mkdir -p /home/deploy/.ssh
cp ~/.ssh/authorized_keys /home/deploy/.ssh/
chown -R deploy:deploy /home/deploy/.ssh
```

---

## 3. Application deployment

```bash
su - deploy
git clone https://github.com/sebunya/prof_radio_mind.git rmias
cd rmias

# Create production env file from template
cp .env.production.example .env.production
nano .env.production   # fill in all CHANGE_ME values
```

**Required substitutions in `.env.production`:**

| Variable | How to generate |
|---|---|
| `POSTGRES_PASSWORD` | `openssl rand -base64 32` |
| `DATABASE_URL` | same password as above |
| `API_KEY` | `python3 -c "import secrets; print(secrets.token_hex(32))"` |
| `S3_ACCESS_KEY_ID` | Hetzner Object Storage credentials (see §4) |
| `S3_SECRET_ACCESS_KEY` | Hetzner Object Storage credentials |

---

## 4. Hetzner Object Storage

Raw payload files are stored in Hetzner Object Storage (S3-compatible).

1. In Hetzner Console → **Object Storage** → Create bucket:
   - Name: `rmias-raw-payloads`
   - Location: same region as your server

2. Generate S3 credentials:
   - Console → Object Storage → **Manage credentials** → Create access key
   - Copy `Access Key` → `S3_ACCESS_KEY_ID`
   - Copy `Secret Key` → `S3_SECRET_ACCESS_KEY`

3. Set the endpoint URL in `.env.production`:
   ```
   S3_ENDPOINT_URL=https://fsn1.your-objectstorage.com
   S3_BUCKET_NAME=rmias-raw-payloads
   S3_REGION=eu-central-1
   ```

The app will automatically use Object Storage when `S3_ENDPOINT_URL` is non-empty;
it falls back to local filesystem (`/data/raw_payloads`) otherwise.

---

## 5. SSL / TLS

```bash
# Update nginx/rmias.conf — replace rmias.example.com with your domain
sed -i 's/rmias.example.com/api.yourdomain.com/g' nginx/rmias.conf

# Obtain a certificate (runs in one-shot mode, outside Docker)
apt-get install -y certbot
certbot certonly --standalone -d api.yourdomain.com --agree-tos --email you@example.com

# Now start the stack — certbot container will auto-renew every 12h
docker compose -f docker-compose.hetzner.yml --env-file .env.production up -d
```

---

## 6. Database migrations

Run Alembic migrations on first deploy and after every schema change:

```bash
docker compose -f docker-compose.hetzner.yml --env-file .env.production \
  exec app alembic upgrade head
```

The app also runs the seeder at startup (idempotent — safe to run multiple times).

---

## 7. IP rotation / anti-blocking

Radio station websites may rate-limit or block repeated requests from the same IP.
Three strategies are available, from simplest to most robust:

### Strategy A: Residential / datacenter proxies (recommended)

Subscribe to a proxy provider (e.g. SOAX, Bright Data, Oxylabs, Smartproxy).
Add the proxy list to `PROXY_URLS` in `.env.production`:

```
PROXY_URLS=http://user:pass@gate.soax.com:9000,http://user:pass@gate.soax.com:9001
```

The built-in `ProxyPool` rotates proxies in round-robin order on each HTTP request.
Supports `http://`, `socks5://`, and `socks5h://` (SOCKS5 with remote DNS — preferred).

### Strategy B: Hetzner Floating IP cycling

Hetzner Floating IPs can be reassigned programmatically via the Hetzner API.
Create a cron job that rotates the server's Floating IP daily:

```bash
# Assign a new Floating IP (requires hcloud CLI)
hcloud floating-ip assign <new-floating-ip-id> <server-id>
hcloud floating-ip unassign <old-floating-ip-id>
```

This is effective but requires pre-purchased Floating IPs (€0.99/month each).
Combine with Strategy A for maximum resilience.

### Strategy C: Tor exit node rotation (low cost, lower reliability)

Install Tor on the server and configure the app to use the SOCKS5 Tor proxy:

```bash
apt-get install -y tor
# tor listens on 127.0.0.1:9050 by default
```

```
PROXY_URLS=socks5h://127.0.0.1:9050
```

Tor exit nodes change every ~10 minutes. Not recommended for time-sensitive
production polling because Tor can be slow and some sites block known Tor exits.

---

## 8. Health monitoring

The API exposes `GET /health` which returns `{"status": "ok"}`.

**Simple uptime check** with a cron job on the server:

```bash
# /etc/cron.d/rmias-health
*/5 * * * * deploy curl -sf http://localhost:8000/health || \
  systemctl restart docker  # or send alert
```

**Recommended**: use an external monitor (UptimeRobot free tier, Better Uptime,
or Hetzner's own monitoring) pointed at `https://api.yourdomain.com/health`.

---

## 9. Log management

```bash
# Stream live logs
docker compose -f docker-compose.hetzner.yml logs -f app

# Check recent errors
docker compose -f docker-compose.hetzner.yml logs --since 1h app | grep ERROR
```

Log files are capped at 50 MB × 5 files per service (see `docker-compose.hetzner.yml`).
For centralised logging, set `LOG_LEVEL=INFO` and pipe to Loki / Datadog / Logtail.

---

## 10. Backups

```bash
# One-shot PostgreSQL dump
docker compose -f docker-compose.hetzner.yml --env-file .env.production \
  exec db pg_dump -U rmias rmias | gzip > /backups/rmias-$(date +%F).sql.gz
```

Add to a daily cron job and sync to Hetzner Object Storage or another bucket.
Enable automated server snapshots in the Hetzner Console for a full-disk backup.

---

## 11. Updating the application

```bash
cd ~/rmias
git pull origin main
docker compose -f docker-compose.hetzner.yml --env-file .env.production build app
docker compose -f docker-compose.hetzner.yml --env-file .env.production up -d app
docker compose -f docker-compose.hetzner.yml --env-file .env.production \
  exec app alembic upgrade head
```

Zero-downtime rolling update is not required at MVP scale — the brief restart window
(< 5 seconds) is acceptable because collection jobs retry on the next scheduled run.
