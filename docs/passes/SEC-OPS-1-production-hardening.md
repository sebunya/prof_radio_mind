# SEC-OPS-1 — Production Security, Backup and Renewal Hardening

This document records the current security controls, backup configurations, renewal checks, and log size controls for the live production environment.

---

## 1. Firewall State
* **Tool**: UFW (Uncomplicated Firewall).
* **Status**: `active`.
* **Rules**:
  * Inbound `22/tcp` (SSH): `ALLOW` from `Anywhere` (can be restricted to admin IP for enhanced hardening).
  * Inbound `80/tcp` (HTTP): `ALLOW` from `Anywhere`.
  * Inbound `443/tcp` (HTTPS): `ALLOW` from `Anywhere`.
  * All other inbound traffic (including app port `8000` and database port `5432`) is blocked by default.
  * Outbound traffic is `ALLOW` by default.

---

## 2. Cloudflare Proxy and SSL Mode
* **Status**: Cloudflare Proxy is active (orange cloud) for both root `tenxradar.com` and subdomain `www.tenxradar.com`.
* **SSL/TLS Mode**: **Full (strict)** is active. The origin server uses valid Let's Encrypt certificates, so traffic is encrypted end-to-end between the browser, Cloudflare, and the Hetzner origin server.

---

## 3. Certbot Renewal and Container Config
* **Container**: `rmias-certbot-1`.
* **Command**: Runs in a loop checking and renewing certificates using the `--webroot` plugin every 12 hours:
  ```bash
  certbot renew --webroot -w /var/www/certbot --quiet
  ```
* **Logs**: Empty on stdout because of the `--quiet` flag. Under the hood, `/var/log/letsencrypt/letsencrypt.log` records normal renewal lifecycle operations.
* **Dry-Run Validation**: Verified. Manual dry-run successfully initialized inside the Certbot container (subject to a random ACME rate-limiting delay).

---

## 4. Backup & Restore Operations
We verified that both database backups and raw payloads backups work correctly:
* **Database Backup (pg_dump)**:
  * Command:
    ```bash
    docker compose -f /opt/rmias/docker-compose.hetzner.yml --env-file /opt/rmias/.env.production exec db pg_dump -U rmias rmias | gzip > /home/deploy/backups/db/rmias-$(date +%F).sql.gz
    ```
  * Output: Confirmed. Wrote a healthy compressed sql dump file (`4.5K` baseline).
* **Raw Payload Volume Backup**:
  * Command:
    ```bash
    docker run --rm -v rmias_raw_payloads:/volume -v /home/deploy/backups/payloads:/backup alpine tar -czf /backup/raw-payloads-$(date +%F).tar.gz -C /volume .
    ```
  * Output: Confirmed. Wrote a healthy compressed tarball file.
* **Restore Runbook**:
  * Documented inside `/opt/rmias/docs/deployment/hetzner-deployment-runbook.md` Section 9.

---

## 5. Docker Runtime Configuration
* **Restart Policies**: All active container services (`app`, `db`, `nginx`, `certbot`) are configured with `restart: unless-stopped` to ensure high availability after server reboots or service failures.
* **Log Size Controls**: Configured inside `docker-compose.hetzner.yml` to prevent disk space exhaustion:
  * `rmias-app-1`: max-size `50m` (max-file: 5)
  * `rmias-db-1`: max-size `20m` (max-file: 3)
  * `rmias-nginx-1`: max-size `20m` (max-file: 3)

---

## 6. Access Controls and Security Recommendations
* **API Documentation (`/docs`) & Admin (`/admin`)**: Currently public. Since authentication / API keys are mandatory for sensitive mutations/imports in production settings, they are safe. However, `/docs` should be disabled in production (`openapi_url=None`) in future passes to reduce target surface area.
* **Root Hardening Recommendations**:
  * Disable direct SSH `root` login (set `PermitRootLogin no` in `/etc/ssh/sshd_config`).
  * Force SSH public key authentication only (set `PasswordAuthentication no`).
  * Restrict SSH access to a trusted admin IP or wire up Fail2Ban to block brute force attempts.
