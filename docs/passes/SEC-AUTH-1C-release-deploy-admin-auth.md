# SEC-AUTH-1C-RELEASE-DEPLOY — Production Release and Admin Auth Hardening Report

**Date:** 2026-06-05  
**Pass:** SEC-AUTH-1C-RELEASE-DEPLOY  
**Branch deployed:** `main`  
**Local commit deployed:** `8c07b9b`  
**Production commit before deploy:** `d5ec156` (PR #8 only — prior SEC-AUTH-1C pass)  
**Target production commit:** `8c07b9b` (PR #8 + PR #9 UIUX + PR #11 EXTRACT-1 + stability docs)

---

## 1. Why This Deployment Was Needed

The prior SEC-AUTH-1C pass (docs at `8c07b9b`) deployed only up to `d5ec156` — the PR #8 merge commit (SEC-AUTH-1B fix). Since then, the following work merged into `main`:

| Commit | Merge | Contents |
|--------|-------|---------|
| `1ec18c0` | PR #9 | UIUX admin console redesign — Operations page, Play Events, Metadata Enrichment UI |
| `df660b4` | PR #11 | EXTRACT-1 parser/collector library — 6 new collectors, 4 updated parsers, 7 test modules, 12 fixtures |
| `11530c7` | direct | POST-MERGE-STABILITY-EXTRACT-1 docs |
| `8c07b9b` | direct | Prior SEC-AUTH-1C docs |

Production was behind by 4 commits and had not received the new admin UI pages, the parser/collector library, or the stability documentation.

---

## 2. Local Pre-Deploy Gates

| Gate | Result |
|------|--------|
| Local main HEAD | `8c07b9b` — clean working tree |
| Ruff | **CLEAN** |
| Mypy | **CLEAN** (124 source files) |
| Full test suite | **492 passed, 2 skipped** |

---

## 3. Baseline Verification

| Baseline | Status |
|----------|--------|
| SEC-AUTH-1B — `_is_protected_admin_path` present | CONFIRMED |
| `/api/admin/metadata-readiness` covered by auth | CONFIRMED |
| `/api/admin/overview` covered by auth | CONFIRMED |
| `/administrator` false-positive guard | CONFIRMED NOT caught |
| 5 new collector flags default `False` | CONFIRMED |
| New collectors NOT wired into scheduler | CONFIRMED |

---

## 4. Migration Decision

**No migrations applied.** Changes since PR #9 merge (`1ec18c00..8c07b9b`) contain zero Alembic migration files:
- PR #11 was a pure parser/collector/test/fixture/docs change
- Post-merge docs and SEC-AUTH-1C docs are documentation only
- Alembic chain on `main` remains at `c4e2a1f9b8d7` (Phase E dedup index — unchanged)

---

## 5. What This Deployment Brings to Production

### New in this release vs prior production (`d5ec156`)

| Work | Description |
|------|-------------|
| PR #9 UIUX | Admin console Operations page, Play Events page, Source Health, Review Queue, enhanced Metadata Enrichment UI |
| PR #11 EXTRACT-1 | 6 new collector classes (BBC Radio 1, Heart FM, iHeart now-playing/recently-played/top-songs, KIIS Radiowave), 4 extended parsers, 12 test fixtures |
| 5 new settings flags | `enable_bbc_radio1_collector`, `enable_heart_collector`, `enable_z100_collector`, `enable_wksc_collector`, `enable_iheart_top_songs` — all `False`, not wired into scheduler |
| `base.py` async | `_store_payload` now async via `asyncio.to_thread` — backward-compatible |

---

## 6. Deployment Execution

| Step | Result |
|------|--------|
| Safety flag gate on server | PASSED — no flags active |
| `git reset --hard origin/main` on server | EXECUTED |
| Production commit after pull | `8c07b9b` |
| `docker compose up -d --build app` | EXECUTED |
| Health after code deploy | `200` |

---

## 7. Admin Credential Rotation

Credentials from the prior SEC-AUTH-1C were rotated as part of this pass:

| Item | Value |
|------|-------|
| Username | `tenxadmin` |
| Password | `openssl rand -hex 32` (64-char hex — never printed) |
| Storage | `/root/tenx-admin-auth.txt` |
| Permissions | `chmod 600` (root-only) |
| Committed to git | **NO** |
| Printed in logs | **NO** |

To retrieve credentials:
```bash
ssh -o IdentitiesOnly=yes -i ~/.ssh/id_ed25519 root@178.105.238.18 'cat /root/tenx-admin-auth.txt'
```

---

## 8. Route Verification

### Unauthenticated

| Route | Expected | Actual |
|-------|----------|--------|
| `/` | `200` | `200` ✅ |
| `/health` | `200` | `200` ✅ |
| `/admin/` | `401` | `401` ✅ |
| `/admin/js/app.js` | `401` | `401` ✅ |
| `/api/admin/metadata-readiness` | `401` | `401` ✅ |
| `/api/admin/overview` | `401` | `401` ✅ |
| `/api/admin/source-health` | `401` | `401` ✅ |

`WWW-Authenticate: Basic realm="RMIAS Admin"` header confirmed on `401` responses.

### Authenticated

| Route | Expected | Actual |
|-------|----------|--------|
| `/admin/` | `200` | `200` ✅ |
| `/admin/js/app.js` | `200` | `200` ✅ |
| `/api/admin/metadata-readiness` | `200` | `200` ✅ |
| `/api/admin/overview` | `200` | `200` ✅ |
| `/api/admin/source-health` | `200` | `200` ✅ |

---

## 9. Response Safety

`/api/admin/metadata-readiness` (authenticated) verified:
- `status: disabled`, `mode: readiness_only`
- Compliance boundary: `no_streaming`, `no_downloads`, `no_playlist_scraping`, `no_playback` all `True`
- **No secrets found** in response body: `SPOTIFY_CLIENT_SECRET`, `DATABASE_URL`, `ADMIN_BASIC_AUTH_PASSWORD`, `access_token`, `refresh_token` — all absent

---

## 10. Safety Flags After Deploy

| Flag | Value |
|------|-------|
| `SCHEDULER_ENABLED` | `false` |
| `ENABLE_CAPITAL_COLLECTOR` | `false` |
| `ENABLE_NOVA_COLLECTOR` | `false` |
| `ENABLE_KIIS_COLLECTOR` | `false` |
| `ENABLE_NIGHTLY_RECONCILIATION` | `false` |
| `ENABLE_BBC_RADIO1_COLLECTOR` | `false` |
| `ENABLE_HEART_FM_COLLECTOR` | `false` |
| `ENABLE_Z100_COLLECTOR` | `false` |
| `ENABLE_WKSC_COLLECTOR` | `false` |
| `ENABLE_IHEART_TOP_SONGS` | `false` |
| `SPOTIFY_METADATA_ENRICHMENT_ENABLED` | `false` |
| `MUSICBRAINZ_METADATA_ENRICHMENT_ENABLED` | `false` |

---

## 11. Log Scan

Application logs after deployment are clean:
- Seeder completed normally
- Scheduler correctly disabled (`SCHEDULER_ENABLED=false`)
- No errors, exceptions, or tracebacks
- No scheduler or collector activity
- No MusicBrainz, Spotify, or Cover Art Archive calls

---

## 12. Passive Observation (5-minute window)

- Health remained `200`
- Unauthenticated `/admin/` remained `401`
- No new error log entries

---

## 13. Confirmation Checklist

- [x] No migrations applied
- [x] No MusicBrainz live calls
- [x] No Spotify live calls  
- [x] No Cover Art Archive live calls
- [x] No scheduler or collector enabled
- [x] No enrichment enabled
- [x] No source/station seeds added
- [x] No secrets committed to git
- [x] `.env.production` updated server-side only
- [x] Credentials rotated and stored at `/root/tenx-admin-auth.txt` with `chmod 600`
- [x] Admin surface protected: all `/admin/*` and `/api/admin/*` return `401` unauthenticated
- [x] Public surface preserved: `/` and `/health` return `200`

---

## 14. Rollback

If this deployment needs to be reversed:
```bash
ssh -o IdentitiesOnly=yes -i ~/.ssh/id_ed25519 root@178.105.238.18 'bash -s' <<'EOF'
cd /opt/rmias
git reset --hard d5ec156
docker compose -f docker-compose.hetzner.yml --env-file .env.production up -d --build app
sleep 12
curl -s -o /dev/null -w "%{http_code}\n" https://tenxradar.com/health
EOF
```

---

## 15. Next Steps

1. **Retrieve credentials:**
   ```bash
   ssh -o IdentitiesOnly=yes -i ~/.ssh/id_ed25519 root@178.105.238.18 'cat /root/tenx-admin-auth.txt'
   ```

2. **Manual browser UI QA** — open `https://tenxradar.com/admin/` and verify:
   - Login prompt appears
   - Dashboard loads after auth
   - Sidebar navigation works
   - Metadata Enrichment page works
   - Operations/guardrails page works
   - Play Events page works
   - Source Health works
   - Scheduler shows as disabled/stopped
   - New extracted collectors do not appear as active
   - No secrets visible anywhere

3. **Only after manual UI QA:** proceed to `EXTRACT-1B-PLAN — Scheduler Wiring Plan for Extracted Collectors` (planning only, no implementation)
