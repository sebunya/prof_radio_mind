#!/usr/bin/env bash
# VAL-COLLECTORS-1 — Read-only production validation for EXTRACT-2/3/4 deployment.
#
# Checks only. Makes no changes. Enables nothing.
# Verifies: container health, safety flags, auth protection, migration
# version, DB station/source counts, collector/parser code presence, logs.
#
# Run FROM YOUR MAC after EXTRACT-2/3/4 is deployed:
#
#   ssh -o IdentitiesOnly=yes -i ~/.ssh/id_ed25519 root@178.105.238.18 'bash -s' \
#       < ~/Documents/Prof_Mind/docs/passes/val-collectors-1-dryrun.sh \
#       | tee /tmp/val-collectors-1.log
#
# Exit codes:
#   0  all checks passed
#   1  one or more checks failed

set -euo pipefail

SERVER_DIR="/opt/rmias"
COMPOSE="docker compose -f ${SERVER_DIR}/docker-compose.hetzner.yml --env-file ${SERVER_DIR}/.env.production"
APP_HOST="https://tenxradar.com"
EXPECTED_ALEMBIC_HEAD="c4e2a1f9b8d7"
EXPECTED_STATIONS=8
EXPECTED_GIT_COMMIT="d3684b4"   # EXTRACT-4 follow-through commit

PASS=0
FAIL=0

_pass() { echo "  PASS  $*"; PASS=$((PASS+1)); }
_fail() { echo "  FAIL  $*"; FAIL=$((FAIL+1)); }
_head() { echo ""; echo "=== $* ==="; }

echo "============================================================"
echo " VAL-COLLECTORS-1  $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "============================================================"

# ── 1. Git / deployment version ──────────────────────────────────
_head "1. Deployment version"

cd "${SERVER_DIR}"
actual_commit="$(git rev-parse --short HEAD)"
if git rev-parse HEAD | grep -q "$(git rev-parse "${EXPECTED_GIT_COMMIT}" 2>/dev/null || true)"; then
  _pass "git HEAD includes EXTRACT-4 commit ${EXPECTED_GIT_COMMIT}"
else
  # Short-hash check fallback
  full_actual="$(git rev-parse HEAD)"
  if git log --oneline | grep -q "${EXPECTED_GIT_COMMIT}"; then
    _pass "git HEAD (${actual_commit}) contains EXTRACT-4 commit in ancestry"
  else
    _fail "git HEAD=${actual_commit} — EXTRACT-4 commit ${EXPECTED_GIT_COMMIT} not found in log"
  fi
fi

echo "  git log (last 5):"
git log --oneline -5 | sed 's/^/    /'

# ── 2. Container status ──────────────────────────────────────────
_head "2. Container status"

container_status="$($COMPOSE ps --format json 2>/dev/null | python3 -c "
import sys, json
lines = [l.strip() for l in sys.stdin if l.strip()]
for line in lines:
    try:
        svc = json.loads(line)
        name = svc.get('Service', svc.get('Name', '?'))
        state = svc.get('State', svc.get('Status', '?'))
        print(f'  {name}: {state}')
    except Exception:
        print(f'  {line}')
" 2>/dev/null || $COMPOSE ps 2>/dev/null | tail -n +2 | awk '{print "  "$1": "$NF}')"
echo "$container_status"

if echo "$container_status" | grep -q "app.*running\|app.*Up"; then
  _pass "app container running"
else
  _fail "app container not running"
fi

# ── 3. Safety flags ──────────────────────────────────────────────
_head "3. Safety flags (all must be false/absent)"

flag_is_true() {
  grep -qiE "^${1}=(true|1|yes|on)$" "${SERVER_DIR}/.env.production" 2>/dev/null
}

safety_flags=(
  SCHEDULER_ENABLED
  ENABLE_CAPITAL_COLLECTOR
  ENABLE_NOVA_COLLECTOR
  ENABLE_KIIS_COLLECTOR
  ENABLE_NIGHTLY_RECONCILIATION
  ENABLE_BBC_RADIO1_COLLECTOR
  ENABLE_HEART_COLLECTOR
  ENABLE_HEART_FM_COLLECTOR
  ENABLE_Z100_COLLECTOR
  ENABLE_WKSC_COLLECTOR
  ENABLE_IHEART_TOP_SONGS
  ENABLE_KIIS_RADIOWAVE_COLLECTOR
  ENABLE_IHEART_RECENTLY_PLAYED
  ENABLE_NIGHTLY_REPORT_GENERATION
  ENABLE_GENERIC_IHEART_COLLECTOR
  SPOTIFY_METADATA_ENRICHMENT_ENABLED
  MUSICBRAINZ_METADATA_ENRICHMENT_ENABLED
  METADATA_ENRICHMENT_ENABLED
)

for flag in "${safety_flags[@]}"; do
  val="$(grep -E "^${flag}=" "${SERVER_DIR}/.env.production" 2>/dev/null | cut -d= -f2- || echo "not_set")"
  if flag_is_true "${flag}"; then
    _fail "${flag}=${val} — must be false"
  else
    _pass "${flag}=${val:-not_set}"
  fi
done

# ── 4. HTTP health and auth protection ──────────────────────────
_head "4. HTTP health and auth protection"

http_check() {
  local label="$1" url="$2" expected="$3" extra_args="${4:-}"
  # shellcheck disable=SC2086
  actual="$(curl -s --max-time 10 -o /dev/null -w "%{http_code}" ${extra_args} "${url}" 2>/dev/null || echo "FAILED")"
  if [ "${actual}" = "${expected}" ]; then
    _pass "${label} → ${actual}"
  else
    _fail "${label} → ${actual} (expected ${expected})"
  fi
}

http_check "GET /           (public)"  "${APP_HOST}/"                              "200"
http_check "GET /health     (public)"  "${APP_HOST}/health"                        "200"
http_check "GET /admin/     (unauth)"  "${APP_HOST}/admin/"                        "401"
http_check "GET /api/admin/overview  (unauth)"  "${APP_HOST}/api/admin/overview"   "401"
http_check "GET /api/admin/metadata-readiness (unauth)" \
  "${APP_HOST}/api/admin/metadata-readiness"                                        "401"

# Confirm WWW-Authenticate header is present on 401
www_auth="$(curl -s --max-time 10 -o /dev/null -D - "${APP_HOST}/admin/" 2>/dev/null \
  | grep -i "WWW-Authenticate:" | tr -d '\r' || echo "")"
if echo "${www_auth}" | grep -qi "Basic realm"; then
  _pass "WWW-Authenticate: Basic realm present on /admin/ 401"
else
  _fail "WWW-Authenticate: Basic realm MISSING on /admin/ 401"
fi

# ── 5. Alembic migration version ────────────────────────────────
_head "5. Alembic migration version"

actual_alembic="$($COMPOSE exec -T app python3 -c "
import asyncio
from sqlalchemy import text
from app.infrastructure.database.session import _get_factory as _factory
async def run():
    async with _factory()() as s:
        r = await s.execute(text('SELECT version_num FROM alembic_version'))
        row = r.fetchone()
        print(row[0] if row else 'NONE')
asyncio.run(run())
" 2>/dev/null | tr -d '[:space:]')"

echo "  alembic version: ${actual_alembic}"
if [ "${actual_alembic}" = "${EXPECTED_ALEMBIC_HEAD}" ]; then
  _pass "alembic at expected head ${EXPECTED_ALEMBIC_HEAD}"
else
  _fail "alembic version ${actual_alembic} (expected ${EXPECTED_ALEMBIC_HEAD})"
fi

# ── 6. DB station and source counts ─────────────────────────────
_head "6. DB station and source counts"

$COMPOSE exec -T app python3 -c "
import asyncio
from sqlalchemy import text
from app.infrastructure.database.session import _get_factory as _factory

async def run():
    async with _factory()() as s:
        # Counts
        sc = (await s.execute(text('SELECT COUNT(*) FROM stations'))).scalar()
        src = (await s.execute(text('SELECT COUNT(*) FROM sources'))).scalar()
        print(f'STATION_COUNT={sc}')
        print(f'SOURCE_COUNT={src}')

        # Original stations
        for cs in ('NOVA969', 'KIISFM', 'CAPITALFM'):
            r = (await s.execute(text('SELECT id FROM stations WHERE call_sign=:c'), {'c': cs})).fetchone()
            print(f'STATION_{cs}={\"FOUND\" if r else \"MISSING\"}')

        # EXTRACT-2 stations
        for cs in ('BBCRADIO1', 'HEARTFMUK', 'WHTZ', 'WKSC'):
            r = (await s.execute(text('SELECT id FROM stations WHERE call_sign=:c'), {'c': cs})).fetchone()
            print(f'STATION_{cs}={\"FOUND\" if r else \"MISSING\"}')

        # EXTRACT-3 station
        for cs in ('KIIS1027',):
            r = (await s.execute(text('SELECT id FROM stations WHERE call_sign=:c'), {'c': cs})).fetchone()
            print(f'STATION_{cs}={\"FOUND\" if r else \"MISSING\"}')

        # EXTRACT-2 sources by source_type
        for cs, st in (('BBCRADIO1','bbc_sounds'),('HEARTFMUK','heart_last_played'),
                       ('WHTZ','iheart'),('WKSC','iheart')):
            r = (await s.execute(
                text('SELECT id FROM sources s JOIN stations st ON s.station_id=st.id '
                     'WHERE st.call_sign=:c AND s.source_type=:t'),
                {'c': cs, 't': st}
            )).fetchone()
            print(f'SOURCE_{cs}_{st.upper()}={\"FOUND\" if r else \"MISSING\"}')

        # EXTRACT-3 source
        for cs, st in (('KIIS1027','radiowave'),):
            r = (await s.execute(
                text('SELECT id FROM sources s JOIN stations st ON s.station_id=st.id '
                     'WHERE st.call_sign=:c AND s.source_type=:t'),
                {'c': cs, 't': st}
            )).fetchone()
            print(f'SOURCE_{cs}_{st.upper()}={\"FOUND\" if r else \"MISSING\"}')

asyncio.run(run())
" 2>/dev/null | while IFS='=' read -r key val; do
  case "$key" in
    STATION_COUNT)
      echo "  stations in DB: ${val}"
      if [ "${val}" -ge "${EXPECTED_STATIONS}" ]; then
        _pass "station count ${val} >= ${EXPECTED_STATIONS}"
      else
        _fail "station count ${val} < ${EXPECTED_STATIONS} (expected at least ${EXPECTED_STATIONS})"
      fi ;;
    SOURCE_COUNT)
      echo "  sources in DB: ${val}" ;;
    STATION_*|SOURCE_*)
      label="${key//_/ }"
      if [ "${val}" = "FOUND" ]; then
        _pass "${label}"
      else
        _fail "${label}"
      fi ;;
  esac
done

# ── 7. Collector and parser code presence ────────────────────────
_head "7. Collector and parser code presence (import only)"

$COMPOSE exec -T app python3 -c "
modules = [
    # Existing collectors
    ('collector', 'app.infrastructure.collectors.nova_radiowave',        'NovaRadiowaveCollector'),
    ('collector', 'app.infrastructure.collectors.kiis_iheart',           'KIISIHeartCollector'),
    ('collector', 'app.infrastructure.collectors.online_radio_box',      'OnlineRadioBoxCollector'),
    # EXTRACT-1 new collectors
    ('collector', 'app.infrastructure.collectors.bbc_radio_1',           'BBCRadio1Collector'),
    ('collector', 'app.infrastructure.collectors.heart_radio',           'HeartRadioCollector'),
    ('collector', 'app.infrastructure.collectors.iheart_now_playing',    'IHeartNowPlayingCollector'),
    ('collector', 'app.infrastructure.collectors.iheart_recently_played','IHeartRecentlyPlayedCollector'),
    ('collector', 'app.infrastructure.collectors.iheart_top_songs',      'IHeartTopSongsCollector'),
    ('collector', 'app.infrastructure.collectors.kiis_radiowave',        'KIISRadiowaveCollector'),
    # Parsers
    ('parser',    'app.infrastructure.parsers.bbc_sounds',               None),
    ('parser',    'app.infrastructure.parsers.heart',                    None),
    ('parser',    'app.infrastructure.parsers.iheart',                   None),
    ('parser',    'app.infrastructure.parsers.online_radio_box',         None),
    ('parser',    'app.infrastructure.parsers.radiowave',                None),
    # Scheduler
    ('scheduler', 'app.infrastructure.scheduler.scheduler',              'build_scheduler'),
]
for kind, module, symbol in modules:
    try:
        mod = __import__(module, fromlist=[symbol] if symbol else [])
        if symbol:
            getattr(mod, symbol)
        print(f'IMPORT_OK {kind} {module}')
    except Exception as e:
        print(f'IMPORT_FAIL {kind} {module} {e}')
" 2>/dev/null | while read -r status kind module rest; do
  if [ "${status}" = "IMPORT_OK" ]; then
    _pass "${kind}: ${module}"
  else
    _fail "${kind}: ${module} — ${rest}"
  fi
done

# ── 8. Scheduler state (must not be running) ─────────────────────
_head "8. Scheduler state"

sched_log="$($COMPOSE logs --tail=100 app 2>/dev/null \
  | grep -i "scheduler\|SCHEDULER" | tail -10 || true)"
if echo "${sched_log}" | grep -qi "scheduler.*start\|scheduler.*running"; then
  _fail "scheduler appears to be running — check logs"
  echo "${sched_log}" | sed 's/^/    /'
else
  _pass "no scheduler start/running signals in recent logs"
fi

# ── 9. Recent log scan ───────────────────────────────────────────
_head "9. Recent log scan (last 80 lines)"

recent_logs="$($COMPOSE logs --tail=80 app 2>/dev/null || true)"

# Errors
error_lines="$(echo "${recent_logs}" | grep -iE "ERROR|CRITICAL|Traceback|Exception" \
  | grep -vE "persist_result_failed|capital_now_playing|No such container" || true)"
if [ -n "${error_lines}" ]; then
  _fail "error/exception lines found in recent logs"
  echo "${error_lines}" | head -10 | sed 's/^/    /'
else
  _pass "no ERROR/CRITICAL/Traceback in recent logs"
fi

# Collector activity (must be silent — all flags must be false)
collector_lines="$(echo "${recent_logs}" | grep -iE \
  "bbc_radio1_collected|heart_fm_collected|z100_now_playing|wksc_now_playing|kiis_top_songs|\
iheart_recently_played_collected|kiis1027_radiowave_collected" || true)"
if [ -n "${collector_lines}" ]; then
  _fail "new collector activity found in logs — flags should be false"
  echo "${collector_lines}" | head -5 | sed 's/^/    /'
else
  _pass "no extracted-collector activity in recent logs"
fi

# Seeder completion
if echo "${recent_logs}" | grep -q "seeder complete"; then
  _pass "seeder completed on last startup"
else
  echo "  INFO  seeder complete not found in last 80 lines (may be older startup)"
fi

# ── Summary ──────────────────────────────────────────────────────
echo ""
echo "============================================================"
echo " SUMMARY: ${PASS} passed, ${FAIL} failed"
echo "============================================================"

if [ "${FAIL}" -gt 0 ]; then
  echo " One or more checks FAILED. Do not enable any collector flag."
  echo " Review output above."
  exit 1
fi

echo " All checks passed."
echo " EXTRACT-2/3/4 deployment validated. Flags remain false."
echo " Proceed to VAL-LIVE-ENDPOINTS to validate each collector's endpoint before enabling."
