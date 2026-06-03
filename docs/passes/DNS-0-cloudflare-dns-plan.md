# DNS-0 — Cloudflare DNS, SSL Mode and Hetzner Deployment Readiness Confirmation

## Objective
Confirm root and `www` domains resolution to Hetzner server `178.105.238.18`, and document the proxy mode transitions and SSL modes for a secure Let's Encrypt TLS setup.

## Cloudflare DNS Configuration
* **Root Domain (`tenxradar.com`)**:
  * Type: `A`
  * Content: `178.105.238.18`
  * Proxy status: `Proxied` (orange cloud) for production; temporarily set to `DNS-only` (grey cloud) during bootstrap.
  * TTL: `Auto`
* **WWW Subdomain (`www.tenxradar.com`)**:
  * Type: `CNAME`
  * Name: `www`
  * Target: `tenxradar.com`
  * Proxy status: `Proxied` (orange cloud) for production; temporarily set to `DNS-only` (grey cloud) during bootstrap.
  * TTL: `Auto`

## Verification Command Outputs
* `dig +short tenxradar.com` → `178.105.238.18`
* `dig +short www.tenxradar.com` → CNAME resolves to `178.105.238.18`
* Result: Root and WWW resolve cleanly to the target server IP address.

## Temporary Let's Encrypt Bootstrap Strategy
1. **De-proxy DNS Records**: Switch `tenxradar.com` and `www.tenxradar.com` from `Proxied` (orange) to `DNS-only` (grey) in the Cloudflare dashboard.
2. **Obtain SSL Certificates**: On the Hetzner server, run standalone Certbot:
   ```bash
   docker run -it --rm -p 80:80 \
     -v /etc/letsencrypt:/etc/letsencrypt \
     -v /var/www/certbot:/var/www/certbot \
     certbot/certbot certonly --standalone \
     -d tenxradar.com -d www.tenxradar.com --agree-tos --email admin@tenxradar.com
   ```
3. **Verify HTTPS**: Start the RMIAS stack and confirm:
   * `https://tenxradar.com/health` returns HTTP 200 `{"status":"ok",...}`
   * `https://www.tenxradar.com/health` returns HTTP 200 `{"status":"ok",...}`
4. **Re-proxy DNS Records**: Switch both records back to `Proxied` (orange) in Cloudflare.
5. **Set SSL/TLS Mode**: In the Cloudflare dashboard under SSL/TLS Overview, set SSL mode to **Full (strict)**.
