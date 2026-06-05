# Production Deployment Report — SEC-AUTH-1C

## Pass Name
SEC-AUTH-1C — Deploy Admin Auth Patch and Configure Production Credentials

## 1. Context

This pass deployed the admin authentication hotfix merged in PR #8 (`fix/sec-auth-1b-admin-api-auth`) and configured server-only Basic Auth credentials on the Hetzner production server.

Before this pass:
- Production was running `94194ab` (pre-patch, admin routes public)
- No admin credentials were set in `.env.production`
- All admin routes returned `HTTP 200` unauthenticated

After this pass:
- Production is running `d5ec156` (merge commit of PR #8)
- Admin credentials are configured server-only (never committed)
- All admin routes return `HTTP 401` unauthenticated
- All admin routes return `HTTP 200` with valid credentials
- Public routes `/` and `/health` remain `HTTP 200`

---

## 2. Deployment Steps Executed

### 2.1 Local Pre-Deploy Gates
| Gate | Result |
|:---|:---|
| `ruff check app/ tests/` | ✅ All checks passed |
| `mypy app/ --ignore-missing-imports` | ✅ 116 files clean |
| `pytest tests/ -x` | ✅ 380 passed, 2 skipped |

### 2.2 Production Pull
- Pulled `origin/main` to production server at `/opt/rmias`
- New commit: `d5ec156 — Merge pull request #8 from sebunya/fix/sec-auth-1b-admin-api-auth`
- Confirmed `_is_protected_admin_path` present in `app/core/admin_auth.py`

### 2.3 Credential Generation
- Generated username: `tenxadmin`
- Generated password: `openssl rand -hex 32` (64-char hex, never printed)
- Written to `/root/tenx-admin-auth.txt` with `chmod 600`
- Injected into `/opt/rmias/.env.production` via Python script (no sed, no shell interpolation risks)
- Credentials **never committed**, **never printed** in logs

### 2.4 Docker Rebuild and Recreate
- Rebuilt `rmias-app` image with `--no-cache` (required: code change in `app/core/admin_auth.py`)
- Force-recreated `rmias-app-1` container
- Container status: `healthy` within 10 seconds of start

---

## 3. Pre-Hardening State (Confirmed)

| Route | Status Before |
|:---|:---|
| `/` | `200` (public) |
| `/health` | `200` (public) |
| `/admin/` | `200` ⚠️ (unprotected) |
| `/admin/js/app.js` | `200` ⚠️ (unprotected) |
| `/api/admin/metadata-readiness` | `200` 🔴 (unprotected) |
| `/api/admin/overview` | `200` 🔴 (unprotected) |

---

## 4. Post-Hardening State (Verified)

### Unauthenticated (expected: 401 for admin, 200 for public)

| Route | Status After |
|:---|:---|
| `/` | ✅ `200` (public — unchanged) |
| `/health` | ✅ `200` (public — unchanged) |
| `/admin/` | ✅ `401` (protected) |
| `/admin/js/app.js` | ✅ `401` (protected) |
| `/admin/css/app.css` | ✅ `401` (protected) |
| `/api/admin/metadata-readiness` | ✅ `401` (protected) |
| `/api/admin/overview` | ✅ `401` (protected) |
| `/api/admin/source-health` | ✅ `401` (protected) |
| `/api/admin/operations` | ✅ `401` (protected) |

`WWW-Authenticate: Basic realm="RMIAS Admin", charset="UTF-8"` header confirmed present on `401` responses.

### Authenticated (expected: 200 for all admin routes)

| Route | Status After |
|:---|:---|
| `/admin/` | ✅ `200` |
| `/admin/js/app.js` | ✅ `200` |
| `/admin/css/app.css` | ✅ `200` |
| `/api/admin/metadata-readiness` | ✅ `200` |
| `/api/admin/overview` | ✅ `200` |
| `/api/admin/source-health` | ✅ `200` |
| `/api/admin/operations` | ✅ `200` |

---

## 5. API Response Safety Check

`/api/admin/metadata-readiness` (authenticated) verified:
- `status: disabled`
- `mode: readiness_only`
- Providers: `musicbrainz`, `spotify`, `cover_art_archive`
- Compliance boundary: `no_streaming=True`, `no_downloads=True`, `no_playlist_scraping=True`, `no_playback=True`
- **No secrets found**: `SPOTIFY_CLIENT_SECRET`, `DATABASE_URL`, `ADMIN_BASIC_AUTH_PASSWORD`, `access_token`, `refresh_token` — all absent from response

---

## 6. Safety Flags (Unchanged)

| Flag | Value |
|:---|:---|
| `SCHEDULER_ENABLED` | `false` |
| `ENABLE_CAPITAL_COLLECTOR` | `false` |
| `ENABLE_NOVA_COLLECTOR` | `false` |
| `ENABLE_KIIS_COLLECTOR` | `false` |
| `ENABLE_NIGHTLY_RECONCILIATION` | `false` |

No enrichment, metadata, or provider flags were changed.

---

## 7. Log Scan

Application logs after rebuild are **clean**:
- Seeder completed normally
- Scheduler correctly disabled (`SCHEDULER_ENABLED=false`)
- No errors, exceptions, tracebacks
- No scheduler activity
- No collector activity
- No MusicBrainz, Spotify, or Cover Art Archive calls

---

## 8. Database

- Alembic version: `c4e2a1f9b8d7 (head)` — unchanged
- No migrations applied
- No schema changes

---

## 9. Credential Storage

- Location: `/root/tenx-admin-auth.txt`
- Permissions: `chmod 600` (root-only)
- Format: Plain text (username + password + domain + created timestamp)
- **Never committed to git**
- **Never printed in agent logs**

To retrieve credentials:
```bash
ssh -o IdentitiesOnly=yes -i ~/.ssh/id_ed25519 root@178.105.238.18 'cat /root/tenx-admin-auth.txt'
```

---

## 10. Confirmation Checklist

- ✅ No migrations applied
- ✅ No MusicBrainz live calls
- ✅ No Spotify live calls
- ✅ No Cover Art Archive live calls
- ✅ No scheduler or collector enabled
- ✅ No enrichment enabled
- ✅ No Docker Compose or Nginx changes
- ✅ No secrets committed to git
- ✅ `.env.production` updated server-side only
- ✅ Rebuild required (code change) — completed successfully
- ✅ Production healthy and responding correctly

---

## 11. Security Hardening Summary

| Surface | Before SEC-AUTH-1C | After SEC-AUTH-1C |
|:---|:---|:---|
| Admin SPA (`/admin/*`) | Public `200` | Protected `401` → `200` with creds |
| Admin API (`/api/admin/*`) | Public `200` | Protected `401` → `200` with creds |
| Public root (`/`) | `200` | `200` (unchanged) |
| Health (`/health`) | `200` | `200` (unchanged) |

---

## 12. Next Steps

Manual browser UI QA is now unblocked. The user should:

1. Retrieve credentials:
   ```bash
   ssh -o IdentitiesOnly=yes -i ~/.ssh/id_ed25519 root@178.105.238.18 'cat /root/tenx-admin-auth.txt'
   ```
2. Open `https://tenxradar.com/admin/` in a browser.
3. Enter the username and password when prompted.
4. Complete the manual UI QA checklist from `POSTDEPLOY-UIUX-METADATA-AG1-qa.md`.

Only after manual browser UI QA is confirmed should the next pass begin:

`METADATA-1-PLAN — MusicBrainz Canonical Identity Foundation Planning Pass`
