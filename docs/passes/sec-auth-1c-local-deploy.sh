#!/usr/bin/env bash
# SEC-AUTH-1C-LOCAL — Final hardened deployment script
# Run from: ~/Documents/Prof_Mind on your Mac (where the Hetzner SSH key works)
# Usage: bash docs/passes/sec-auth-1c-local-deploy.sh | tee /tmp/sec-auth-1c-local-deploy.log
set -euo pipefail

SERVER="root@178.105.238.18"
KEY="$HOME/.ssh/id_ed25519"
REPO="$HOME/Documents/Prof_Mind"

echo "============================================================"
echo "SEC-AUTH-1C LOCAL DEPLOYMENT START"
echo "Started: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "============================================================"

# Capture expected commit from local git BEFORE any deployment
EXPECTED_COMMIT="$(git -C "$REPO" rev-parse origin/main)"
echo "EXPECTED_MAIN_COMMIT=$EXPECTED_COMMIT"

# ──────────────────────────────────────────────────────────────
echo ""
echo "PHASE 1 — PRODUCTION PREFLIGHT (read-only)"
# ──────────────────────────────────────────────────────────────
ssh -o IdentitiesOnly=yes -i "$KEY" "$SERVER" 'bash -s' <<'REMOTE_PREFLIGHT'
set -euo pipefail
cd /opt/rmias
COMPOSE="docker compose -f docker-compose.hetzner.yml --env-file .env.production"

flag_is_true() {
  grep -qiE "^${1}=(true|1|yes|on)$" .env.production 2>/dev/null
}

echo "=== Production git before deploy ==="
git log --oneline -10
git status --short
echo "PROD_BEFORE_COMMIT=$(git rev-parse HEAD)"

echo "=== Production containers ==="
$COMPOSE ps

echo "=== Safety flags in .env.production ==="
grep -E "^SCHEDULER_ENABLED=|^ENABLE_CAPITAL_COLLECTOR=|^ENABLE_NOVA_COLLECTOR=|^ENABLE_KIIS_COLLECTOR=|^ENABLE_NIGHTLY_RECONCILIATION=|^SPOTIFY_METADATA_ENRICHMENT_ENABLED=|^MUSICBRAINZ_METADATA_ENRICHMENT_ENABLED=|^METADATA_ENRICHMENT_ENABLED=|^ENABLE_BBC_RADIO1_COLLECTOR=|^ENABLE_HEART_COLLECTOR=|^ENABLE_HEART_FM_COLLECTOR=|^ENABLE_Z100_COLLECTOR=|^ENABLE_WKSC_COLLECTOR=|^ENABLE_IHEART_TOP_SONGS=|^ENABLE_GENERIC_IHEART_COLLECTOR=" .env.production || true

for flag in \
  SCHEDULER_ENABLED ENABLE_CAPITAL_COLLECTOR ENABLE_NOVA_COLLECTOR \
  ENABLE_KIIS_COLLECTOR ENABLE_NIGHTLY_RECONCILIATION \
  SPOTIFY_METADATA_ENRICHMENT_ENABLED MUSICBRAINZ_METADATA_ENRICHMENT_ENABLED \
  METADATA_ENRICHMENT_ENABLED \
  ENABLE_BBC_RADIO1_COLLECTOR \
  ENABLE_HEART_COLLECTOR ENABLE_HEART_FM_COLLECTOR \
  ENABLE_Z100_COLLECTOR ENABLE_WKSC_COLLECTOR \
  ENABLE_IHEART_TOP_SONGS ENABLE_GENERIC_IHEART_COLLECTOR
do
  if flag_is_true "$flag"; then
    echo "ERROR: $flag is active. Aborting."
    exit 1
  fi
done
echo "Safety flag gate: CLEAR"

echo "=== Admin auth presence (values hidden) ==="
grep -E "^ADMIN_BASIC_AUTH_USER=" .env.production | sed "s/=.*/=<hidden>/" || echo "ADMIN_BASIC_AUTH_USER not set"
grep -E "^ADMIN_BASIC_AUTH_PASSWORD=" .env.production | sed "s/=.*/=<hidden>/" || echo "ADMIN_BASIC_AUTH_PASSWORD not set"

echo "=== Route status before deploy ==="
echo -n "/: ";                                    curl -s -o /dev/null -w "%{http_code}\n" https://tenxradar.com/
echo -n "/health: ";                              curl -s -o /dev/null -w "%{http_code}\n" https://tenxradar.com/health
echo -n "/admin/ unauth: ";                       curl -s -o /dev/null -w "%{http_code}\n" https://tenxradar.com/admin/
echo -n "/api/admin/metadata-readiness unauth: "; curl -s -o /dev/null -w "%{http_code}\n" https://tenxradar.com/api/admin/metadata-readiness
echo -n "/api/admin/overview unauth: ";           curl -s -o /dev/null -w "%{http_code}\n" https://tenxradar.com/api/admin/overview

echo "=== Alembic current/head ==="
$COMPOSE exec -T app alembic current 2>&1 || true
$COMPOSE exec -T app alembic heads 2>&1 || true

echo "=== Log scan before deploy ==="
$COMPOSE logs --tail=300 app 2>&1 \
  | grep -i "error\|exception\|traceback\|scheduler.*start\|collector.*run\|capital\|nova\|kiis\|bbc\|heart\|z100\|wksc\|spotify\|musicbrainz\|enrichment" \
  | tail -30 || echo "Log scan before deploy: clean"
REMOTE_PREFLIGHT

# ──────────────────────────────────────────────────────────────
echo ""
echo "PHASE 2 — DEPLOY LATEST ORIGIN/MAIN"
# EXPECTED_COMMIT is expanded here by local shell into the SSH command string.
# The remote server receives: EXPECTED_COMMIT='<hash>' bash -s
# ──────────────────────────────────────────────────────────────
ssh -o IdentitiesOnly=yes -i "$KEY" "$SERVER" "EXPECTED_COMMIT='$EXPECTED_COMMIT' bash -s" <<'REMOTE_DEPLOY'
set -euo pipefail
cd /opt/rmias
COMPOSE="docker compose -f docker-compose.hetzner.yml --env-file .env.production"

flag_is_true() {
  grep -qiE "^${1}=(true|1|yes|on)$" .env.production 2>/dev/null
}

PROD_BEFORE_COMMIT="$(git rev-parse HEAD)"
echo "$PROD_BEFORE_COMMIT" > /root/tenx-radar-last-rollback-commit.txt
echo "PROD_BEFORE_COMMIT=$PROD_BEFORE_COMMIT"
echo "Rollback anchor written to /root/tenx-radar-last-rollback-commit.txt"

echo "=== Safety flag gate before pull ==="
for flag in \
  SCHEDULER_ENABLED ENABLE_CAPITAL_COLLECTOR ENABLE_NOVA_COLLECTOR \
  ENABLE_KIIS_COLLECTOR ENABLE_NIGHTLY_RECONCILIATION \
  SPOTIFY_METADATA_ENRICHMENT_ENABLED MUSICBRAINZ_METADATA_ENRICHMENT_ENABLED \
  METADATA_ENRICHMENT_ENABLED \
  ENABLE_BBC_RADIO1_COLLECTOR \
  ENABLE_HEART_COLLECTOR ENABLE_HEART_FM_COLLECTOR \
  ENABLE_Z100_COLLECTOR ENABLE_WKSC_COLLECTOR \
  ENABLE_IHEART_TOP_SONGS ENABLE_GENERIC_IHEART_COLLECTOR
do
  if flag_is_true "$flag"; then
    echo "ERROR: $flag is active. Aborting deploy."
    exit 1
  fi
done
echo "Safety gate: CLEAR"

echo "=== Pull latest origin/main ==="
git fetch origin
git reset --hard origin/main

PROD_AFTER_COMMIT="$(git rev-parse HEAD)"
echo "PROD_AFTER_COMMIT=$PROD_AFTER_COMMIT"

if [ "$PROD_AFTER_COMMIT" != "$EXPECTED_COMMIT" ]; then
  echo "ERROR: production landed on $PROD_AFTER_COMMIT, expected $EXPECTED_COMMIT"
  exit 1
fi
echo "COMMIT ASSERTION: PASSED — production is on $PROD_AFTER_COMMIT"

git log --oneline -10
git status --short

echo "=== Build and start app ==="
$COMPOSE up -d --build app

sleep 12

$COMPOSE ps

STATUS="$(curl -s -o /dev/null -w "%{http_code}" https://tenxradar.com/health)"
echo "/health after deploy: $STATUS expected 200"
test "$STATUS" = "200"
REMOTE_DEPLOY

# ──────────────────────────────────────────────────────────────
echo ""
echo "PHASE 3 — ROTATE SERVER-ONLY ADMIN CREDENTIALS"
# ──────────────────────────────────────────────────────────────
ssh -o IdentitiesOnly=yes -i "$KEY" "$SERVER" 'bash -s' <<'REMOTE_AUTH'
set -euo pipefail
cd /opt/rmias

export ADMIN_USER="tenxadmin"
export ADMIN_PASS="$(openssl rand -hex 32)"
CRED_FILE="/root/tenx-admin-auth.txt"

python3 - <<'PY'
import os
from pathlib import Path

env_path = Path("/opt/rmias/.env.production")
lines = env_path.read_text().splitlines()

updates = {
    "ADMIN_BASIC_AUTH_USER": os.environ["ADMIN_USER"],
    "ADMIN_BASIC_AUTH_PASSWORD": os.environ["ADMIN_PASS"],
}

seen = set()
out = []

for line in lines:
    if "=" not in line or line.strip().startswith("#"):
        out.append(line)
        continue
    key = line.split("=", 1)[0]
    if key in updates:
        out.append(f"{key}={updates[key]}")
        seen.add(key)
    else:
        out.append(line)

for key, value in updates.items():
    if key not in seen:
        out.append(f"{key}={value}")

env_path.write_text("\n".join(out) + "\n")
PY

cat > "$CRED_FILE" <<EOF
TenX Radar Production Admin Credentials
Domain: https://tenxradar.com/admin/
Username: $ADMIN_USER
Password: $ADMIN_PASS
Rotated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
EOF

chmod 600 "$CRED_FILE"

echo "=== Credentials written, values hidden ==="
grep -E "^ADMIN_BASIC_AUTH_USER=" .env.production | sed "s/=.*/=<hidden>/"
grep -E "^ADMIN_BASIC_AUTH_PASSWORD=" .env.production | sed "s/=.*/=<hidden>/"
ls -l "$CRED_FILE"
REMOTE_AUTH

# ──────────────────────────────────────────────────────────────
echo ""
echo "PHASE 4 — FORCE-RECREATE APP TO LOAD AUTH ENV"
# ──────────────────────────────────────────────────────────────
ssh -o IdentitiesOnly=yes -i "$KEY" "$SERVER" 'bash -s' <<'REMOTE_RECREATE'
set -euo pipefail
cd /opt/rmias
COMPOSE="docker compose -f docker-compose.hetzner.yml --env-file .env.production"

$COMPOSE up -d --force-recreate app

sleep 10

$COMPOSE ps

echo "=== Auth env in container (values hidden) ==="
$COMPOSE exec -T app env \
  | grep -E "^ADMIN_BASIC_AUTH_USER=|^ADMIN_BASIC_AUTH_PASSWORD=" \
  | sed "s/=.*/=<hidden>/"

STATUS="$(curl -s -o /dev/null -w "%{http_code}" https://tenxradar.com/health)"
echo "/health after auth reload: $STATUS expected 200"
test "$STATUS" = "200"
REMOTE_RECREATE

# ──────────────────────────────────────────────────────────────
echo ""
echo "PHASE 5 — VERIFY UNAUTHENTICATED ROUTES"
# ──────────────────────────────────────────────────────────────
ssh -o IdentitiesOnly=yes -i "$KEY" "$SERVER" 'bash -s' <<'REMOTE_VERIFY_UNAUTH'
set -euo pipefail

check_status() {
  local label="$1" url="$2" expected="$3" actual
  actual="$(curl -s -o /dev/null -w "%{http_code}" "$url")"
  echo "$label: $actual expected $expected"
  if [ "$actual" != "$expected" ]; then
    echo "ERROR: $label returned $actual, expected $expected"
    exit 1
  fi
}

check_status "/"                             "https://tenxradar.com/"                             "200"
check_status "/health"                       "https://tenxradar.com/health"                       "200"
check_status "/admin/"                       "https://tenxradar.com/admin/"                       "401"
check_status "/admin/js/app.js"              "https://tenxradar.com/admin/js/app.js"              "401"
check_status "/api/admin/metadata-readiness" "https://tenxradar.com/api/admin/metadata-readiness" "401"
check_status "/api/admin/overview"           "https://tenxradar.com/api/admin/overview"           "401"
check_status "/api/admin/source-health"      "https://tenxradar.com/api/admin/source-health"      "401"

echo "=== WWW-Authenticate header on /admin/ ==="
curl -sI https://tenxradar.com/admin/ | grep -i "www-authenticate" || echo "WARNING: WWW-Authenticate header missing"
REMOTE_VERIFY_UNAUTH

# ──────────────────────────────────────────────────────────────
echo ""
echo "PHASE 6 — VERIFY AUTHENTICATED ROUTES"
# ──────────────────────────────────────────────────────────────
ssh -o IdentitiesOnly=yes -i "$KEY" "$SERVER" 'bash -s' <<'REMOTE_VERIFY_AUTH'
set -euo pipefail
cd /opt/rmias

U="$(grep "^ADMIN_BASIC_AUTH_USER=" .env.production | cut -d= -f2-)"
P="$(grep "^ADMIN_BASIC_AUTH_PASSWORD=" .env.production | cut -d= -f2-)"

check_auth() {
  local label="$1" url="$2" expected="$3" actual
  actual="$(curl -s -u "$U:$P" -o /dev/null -w "%{http_code}" "$url")"
  echo "$label: $actual expected $expected"
  if [ "$actual" != "$expected" ]; then
    echo "ERROR: $label returned $actual, expected $expected"
    exit 1
  fi
}

check_auth "/admin/"                       "https://tenxradar.com/admin/"                       "200"
check_auth "/admin/js/app.js"              "https://tenxradar.com/admin/js/app.js"              "200"
check_auth "/api/admin/metadata-readiness" "https://tenxradar.com/api/admin/metadata-readiness" "200"
check_auth "/api/admin/overview"           "https://tenxradar.com/api/admin/overview"           "200"
check_auth "/api/admin/source-health"      "https://tenxradar.com/api/admin/source-health"      "200"

STATUS="$(curl -s -o /dev/null -w "%{http_code}" https://tenxradar.com/health)"
echo "/health public: $STATUS expected 200"
test "$STATUS" = "200"
REMOTE_VERIFY_AUTH

# ──────────────────────────────────────────────────────────────
echo ""
echo "PHASE 7 — RESPONSE SAFETY AND SAFETY FLAGS"
# ──────────────────────────────────────────────────────────────
ssh -o IdentitiesOnly=yes -i "$KEY" "$SERVER" 'bash -s' <<'REMOTE_SAFETY'
set -euo pipefail
cd /opt/rmias
COMPOSE="docker compose -f docker-compose.hetzner.yml --env-file .env.production"

flag_is_true() {
  grep -qiE "^${1}=(true|1|yes|on)$" .env.production 2>/dev/null
}

U="$(grep "^ADMIN_BASIC_AUTH_USER=" .env.production | cut -d= -f2-)"
P="$(grep "^ADMIN_BASIC_AUTH_PASSWORD=" .env.production | cut -d= -f2-)"

RESP="$(curl -s -u "$U:$P" https://tenxradar.com/api/admin/metadata-readiness)"
echo "=== Metadata readiness high-level markers ==="
echo "$RESP" | grep -E "musicbrainz|spotify|cover_art|no_streaming|no_downloads|no_playlist_scraping|no_playback|\"status\"|\"mode\"" || true

echo "=== Secret leakage check ==="
if echo "$RESP" | grep -qE "SPOTIFY_CLIENT_SECRET|DATABASE_URL|ADMIN_BASIC_AUTH_PASSWORD|access_token|refresh_token|\.env\.production"; then
  echo "ERROR: secret marker found in response — STOP"
  exit 1
fi
echo "No secret markers found in metadata-readiness response"

echo "=== Safety flags in .env.production after deploy ==="
grep -E "^SCHEDULER_ENABLED=|^ENABLE_CAPITAL_COLLECTOR=|^ENABLE_NOVA_COLLECTOR=|^ENABLE_KIIS_COLLECTOR=|^ENABLE_NIGHTLY_RECONCILIATION=|^SPOTIFY_METADATA_ENRICHMENT_ENABLED=|^MUSICBRAINZ_METADATA_ENRICHMENT_ENABLED=|^METADATA_ENRICHMENT_ENABLED=|^ENABLE_BBC_RADIO1_COLLECTOR=|^ENABLE_HEART_COLLECTOR=|^ENABLE_HEART_FM_COLLECTOR=|^ENABLE_Z100_COLLECTOR=|^ENABLE_WKSC_COLLECTOR=|^ENABLE_IHEART_TOP_SONGS=|^ENABLE_GENERIC_IHEART_COLLECTOR=" .env.production || true

for flag in \
  SCHEDULER_ENABLED ENABLE_CAPITAL_COLLECTOR ENABLE_NOVA_COLLECTOR \
  ENABLE_KIIS_COLLECTOR ENABLE_NIGHTLY_RECONCILIATION \
  SPOTIFY_METADATA_ENRICHMENT_ENABLED MUSICBRAINZ_METADATA_ENRICHMENT_ENABLED \
  METADATA_ENRICHMENT_ENABLED \
  ENABLE_BBC_RADIO1_COLLECTOR \
  ENABLE_HEART_COLLECTOR ENABLE_HEART_FM_COLLECTOR \
  ENABLE_Z100_COLLECTOR ENABLE_WKSC_COLLECTOR \
  ENABLE_IHEART_TOP_SONGS ENABLE_GENERIC_IHEART_COLLECTOR
do
  if flag_is_true "$flag"; then
    echo "ERROR: $flag is active after deploy"
    exit 1
  fi
done
echo "All safety flags remain false or absent"

echo "=== Log scan after deploy ==="
$COMPOSE logs --tail=800 app 2>&1 \
  | grep -i "error\|exception\|traceback\|scheduler.*start\|collector.*run\|capital\|nova\|kiis\|bbc\|heart\|z100\|wksc\|spotify\|musicbrainz\|enrichment" \
  | tail -30 || echo "Log scan: clean"
REMOTE_SAFETY

# ──────────────────────────────────────────────────────────────
echo ""
echo "PHASE 8 — PASSIVE OBSERVATION (5 minutes)"
echo "Waiting 300 seconds..."
# ──────────────────────────────────────────────────────────────
sleep 300

ssh -o IdentitiesOnly=yes -i "$KEY" "$SERVER" 'bash -s' <<'REMOTE_OBSERVE'
set -euo pipefail
cd /opt/rmias
COMPOSE="docker compose -f docker-compose.hetzner.yml --env-file .env.production"

$COMPOSE ps

HEALTH="$(curl -s -o /dev/null -w "%{http_code}" https://tenxradar.com/health)"
ADMIN_UNAUTH="$(curl -s -o /dev/null -w "%{http_code}" https://tenxradar.com/admin/)"
API_UNAUTH="$(curl -s -o /dev/null -w "%{http_code}" https://tenxradar.com/api/admin/metadata-readiness)"

echo "/health: $HEALTH expected 200"
echo "/admin/ unauth: $ADMIN_UNAUTH expected 401"
echo "/api/admin/metadata-readiness unauth: $API_UNAUTH expected 401"

test "$HEALTH" = "200"
test "$ADMIN_UNAUTH" = "401"
test "$API_UNAUTH" = "401"

echo "=== Log scan after 5-minute observation ==="
$COMPOSE logs --tail=1200 app 2>&1 \
  | grep -i "error\|exception\|traceback\|scheduler.*start\|collector.*run\|capital\|nova\|kiis\|bbc\|heart\|z100\|wksc\|spotify\|musicbrainz\|enrichment" \
  | tail -30 || echo "Log scan: clean"
REMOTE_OBSERVE

echo ""
echo "============================================================"
echo "SEC-AUTH-1C LOCAL DEPLOYMENT COMPLETE"
echo "Finished: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "============================================================"
echo ""
echo "Retrieve credentials with:"
echo "  ssh -o IdentitiesOnly=yes -i ~/.ssh/id_ed25519 root@178.105.238.18 'cat /root/tenx-admin-auth.txt'"
echo ""
echo "Then open: https://tenxradar.com/admin/"
