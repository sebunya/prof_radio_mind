#!/usr/bin/env bash
# val-post-enable.sh — Post-enablement observation check.
#
# Run this 15–30 minutes after enabling a single collector and restarting the
# container. Verifies that:
#   1. The collector flag is TRUE in .env.production
#   2. The app container is running
#   3. The scheduler registered the job on startup
#   4. At least one collector run completed (COMPLETED or NO_CONTENT) in the
#      observation window
#   5. No unexpected FAILED runs in the same window
#
# Does NOT enable or disable any flag. Does NOT modify production.
#
# Usage — exactly one collector flag required:
#
#   ssh -o IdentitiesOnly=yes -i ~/.ssh/id_ed25519 root@178.105.238.18 'bash -s' -- --z100 \
#       < ~/Documents/Prof_Mind/docs/passes/val-post-enable.sh \
#       | tee /tmp/val-post-enable-z100.log
#
# Available flags: --z100  --wksc  --kiis_top  --heart  --bbc  --iheart_recent
#                  --kiis1027_radiowave
#
# Exit codes:
#   0  all checks passed (collector is running cleanly)
#   1  one or more checks failed

set -euo pipefail

SERVER_DIR="/opt/rmias"
COMPOSE="docker compose -f ${SERVER_DIR}/docker-compose.hetzner.yml --env-file ${SERVER_DIR}/.env.production"

PASS=0
FAIL=0
WARN=0

_pass() { echo "  PASS  $*"; PASS=$((PASS+1)); }
_fail() { echo "  FAIL  $*"; FAIL=$((FAIL+1)); }
_warn() { echo "  WARN  $*"; WARN=$((WARN+1)); }
_info() { echo "  INFO  $*"; }
_head() { echo ""; echo "=== $* ==="; }

# ── Parse collector selector ──────────────────────────────────────
COLLECTOR=""
for arg in "$@"; do
  case "$arg" in
    --z100)          COLLECTOR="z100" ;;
    --wksc)          COLLECTOR="wksc" ;;
    --kiis_top)      COLLECTOR="kiis_top" ;;
    --heart)         COLLECTOR="heart" ;;
    --bbc)           COLLECTOR="bbc" ;;
    --iheart_recent)      COLLECTOR="iheart_recent" ;;
    --kiis1027_radiowave) COLLECTOR="kiis1027_radiowave" ;;
  esac
done

if [ -z "$COLLECTOR" ]; then
  echo "ERROR: Specify exactly one collector: --z100 | --wksc | --kiis_top | --heart | --bbc | --iheart_recent | --kiis1027_radiowave"
  exit 1
fi

# ── Collector-specific config ─────────────────────────────────────
case "$COLLECTOR" in
  z100)
    FLAG="ENABLE_Z100_COLLECTOR"
    LOG_KEYWORD="z100_now_playing"
    CALL_SIGN="WHTZ"
    SOURCE_TYPE="iheart"
    JOB_ID="z100_now_playing"
    CADENCE="every 5 minutes"
    WINDOW_MINUTES=30
    ;;
  wksc)
    FLAG="ENABLE_WKSC_COLLECTOR"
    LOG_KEYWORD="wksc_now_playing"
    CALL_SIGN="WKSC"
    SOURCE_TYPE="iheart"
    JOB_ID="wksc_now_playing"
    CADENCE="every 5 minutes"
    WINDOW_MINUTES=30
    ;;
  kiis_top)
    FLAG="ENABLE_IHEART_TOP_SONGS"
    LOG_KEYWORD="kiis_top_songs"
    CALL_SIGN="KIISFM"
    SOURCE_TYPE="iheart"
    JOB_ID="kiis_top_songs_daily"
    CADENCE="daily at 00:00 UTC"
    WINDOW_MINUTES=1440
    ;;
  heart)
    FLAG="ENABLE_HEART_COLLECTOR"
    LOG_KEYWORD="heart_fm_collected"
    CALL_SIGN="HEARTFMUK"
    SOURCE_TYPE="heart_last_played"
    JOB_ID="heart_fm_last_played"
    CADENCE="every 5 minutes"
    WINDOW_MINUTES=30
    ;;
  bbc)
    FLAG="ENABLE_BBC_RADIO1_COLLECTOR"
    LOG_KEYWORD="bbc_radio1_collected"
    CALL_SIGN="BBCRADIO1"
    SOURCE_TYPE="bbc_sounds"
    JOB_ID="bbc_radio1_now_playing"
    CADENCE="every 5 minutes"
    WINDOW_MINUTES=30
    ;;
  iheart_recent)
    FLAG="ENABLE_IHEART_RECENTLY_PLAYED"
    LOG_KEYWORD="iheart_recently_played_collected"
    # Batch job covers KIISFM + Z100 + WKSC; KIISFM used as representative for DB check
    CALL_SIGN="KIISFM"
    SOURCE_TYPE="iheart"
    JOB_ID="iheart_recently_played_hourly"
    CADENCE="every 60 minutes"
    WINDOW_MINUTES=90
    ;;
  kiis1027_radiowave)
    FLAG="ENABLE_KIIS_RADIOWAVE_COLLECTOR"
    LOG_KEYWORD="kiis1027_radiowave_collected"
    CALL_SIGN="KIIS1027"
    SOURCE_TYPE="radiowave"
    JOB_ID="kiis1027_radiowave_diary"
    CADENCE="daily at 09:00 UTC"
    WINDOW_MINUTES=1440
    ;;
esac

echo "============================================================"
echo " VAL-POST-ENABLE  collector=${COLLECTOR}  $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo " Flag: ${FLAG}"
echo " Station: ${CALL_SIGN}  Source type: ${SOURCE_TYPE}"
echo " Cadence: ${CADENCE}  Observation window: ${WINDOW_MINUTES} min"
echo "============================================================"

# ── 1. Flag must be TRUE ──────────────────────────────────────────
_head "1. Collector flag"

flag_is_true() {
  grep -qiE "^${1}=(true|1|yes|on)$" "${SERVER_DIR}/.env.production" 2>/dev/null
}

flag_val="$(grep -E "^${FLAG}=" "${SERVER_DIR}/.env.production" 2>/dev/null | cut -d= -f2- || echo 'not_set')"
echo "  ${FLAG}=${flag_val}"

if flag_is_true "${FLAG}"; then
  _pass "${FLAG} is enabled"
else
  _fail "${FLAG} is not true — set it to true in .env.production and restart before running this script"
  echo ""
  echo "  Cannot continue — flag must be enabled first."
  echo "  SUMMARY: ABORTED — flag not set"
  exit 1
fi

# ── 2. Container running ──────────────────────────────────────────
_head "2. Container status"

container_ok=false
if $COMPOSE ps app 2>/dev/null | grep -qiE "running|Up"; then
  _pass "app container running"
  container_ok=true
else
  _fail "app container not running"
fi

# ── 3. Scheduler job registered (startup log) ─────────────────────
_head "3. Scheduler job registration"

startup_logs="$($COMPOSE logs --tail=300 app 2>/dev/null || true)"
job_registered="$(echo "${startup_logs}" | grep -i "Scheduler registered job" | grep -i "${JOB_ID}\|${CALL_SIGN}\|$(echo "${COLLECTOR}" | tr '_' ' ')" || true)"

if [ -n "${job_registered}" ]; then
  _pass "scheduler job registered at startup"
  echo "${job_registered}" | tail -3 | sed 's/^/    /'
else
  _warn "scheduler job registration line not found in last 300 log lines"
  _info "(container may have been running before log buffer; check manually)"
fi

# ── 4. Recent collector runs in DB ───────────────────────────────
_head "4. Recent collector runs (last ${WINDOW_MINUTES} minutes)"

$COMPOSE exec -T app python3 -c "
import asyncio, uuid
from sqlalchemy import text
from app.infrastructure.database.session import _get_factory as _factory

_NS = uuid.NAMESPACE_DNS
source_id = uuid.uuid5(_NS, 'source.${CALL_SIGN}.${SOURCE_TYPE}')
station_id = uuid.uuid5(_NS, 'station.${CALL_SIGN}')
window_minutes = ${WINDOW_MINUTES}

async def run():
    async with _factory()() as s:
        rows = await s.execute(text('''
            SELECT status, started_at, rows_fetched, rows_parsed, rows_persisted, error_message
            FROM collector_runs
            WHERE source_id = :src
              AND started_at > NOW() - INTERVAL :win
            ORDER BY started_at DESC
            LIMIT 20
        '''), {'src': str(source_id), 'win': f'{window_minutes} minutes'})
        results = rows.fetchall()
        if not results:
            print('RUNS=0')
            return
        completed = sum(1 for r in results if r[0] in ('completed', 'no_content', 'partial_success'))
        failed = sum(1 for r in results if r[0] == 'failed')
        print(f'RUNS={len(results)} COMPLETED={completed} FAILED={failed}')
        for r in results[:5]:
            print(f'  run status={r[0]} at={r[1]} fetched={r[2]} parsed={r[3]} persisted={r[4]}')
            if r[5]:
                print(f'    error={r[5][:120]}')

asyncio.run(run())
" 2>/dev/null | {
  first_line=true
  run_summary=""
  while IFS= read -r line; do
    if $first_line; then
      run_summary="$line"
      first_line=false
    else
      echo "  $line"
    fi
  done

  echo "  ${run_summary}"

  run_count="$(echo "${run_summary}" | grep -oE "RUNS=[0-9]+" | cut -d= -f2 || echo 0)"
  completed="$(echo "${run_summary}" | grep -oE "COMPLETED=[0-9]+" | cut -d= -f2 || echo 0)"
  failed_db="$(echo "${run_summary}" | grep -oE "FAILED=[0-9]+" | cut -d= -f2 || echo 0)"

  if [ "${run_count:-0}" -eq 0 ]; then
    if [ "${COLLECTOR}" = "kiis_top" ]; then
      _warn "no collector runs in last 24h — daily collector runs at 00:00 UTC only"
    elif [ "${COLLECTOR}" = "kiis1027_radiowave" ]; then
      _warn "no collector runs in last 24h — daily collector runs at 09:00 UTC only"
    elif [ "${COLLECTOR}" = "iheart_recent" ]; then
      _warn "no collector runs in last 90 min — hourly batch job; wait up to 60 min for first run"
    else
      _fail "no collector runs in observation window — expected at least one run every 5 minutes"
    fi
  elif [ "${completed:-0}" -gt 0 ]; then
    _pass "${completed} completed run(s) in window (completed/no_content)"
  else
    _fail "runs found but none completed successfully (COMPLETED=${completed:-0} FAILED=${failed_db:-0})"
  fi

  if [ "${failed_db:-0}" -gt 0 ]; then
    _warn "${failed_db} FAILED run(s) in window — review error messages above"
  fi
}

# ── 5. Recent play/no-track events in DB ─────────────────────────
_head "5. Recent play and no-track events (last ${WINDOW_MINUTES} minutes)"

$COMPOSE exec -T app python3 -c "
import asyncio, uuid
from sqlalchemy import text
from app.infrastructure.database.session import _get_factory as _factory

_NS = uuid.NAMESPACE_DNS
source_id = uuid.uuid5(_NS, 'source.${CALL_SIGN}.${SOURCE_TYPE}')
window_minutes = ${WINDOW_MINUTES}

async def run():
    async with _factory()() as s:
        plays = (await s.execute(text('''
            SELECT COUNT(*) FROM play_events
            WHERE source_id = :src AND played_at > NOW() - INTERVAL :win
        '''), {'src': str(source_id), 'win': f'{window_minutes} minutes'})).scalar()

        no_tracks = (await s.execute(text('''
            SELECT COUNT(*) FROM no_track_events
            WHERE source_id = :src AND observed_at > NOW() - INTERVAL :win
        '''), {'src': str(source_id), 'win': f'{window_minutes} minutes'})).scalar()

        # Most recent play
        latest = (await s.execute(text('''
            SELECT raw_artist, raw_title, played_at
            FROM play_events
            WHERE source_id = :src
            ORDER BY played_at DESC LIMIT 1
        '''), {'src': str(source_id)})).fetchone()

        print(f'PLAYS={plays} NO_TRACKS={no_tracks}')
        if latest:
            print(f'  latest: {latest[0]!r} — {latest[1]!r} at {latest[2]}')
        else:
            print('  (no play events ever for this source)')

asyncio.run(run())
" 2>/dev/null | {
  first_line=true
  event_summary=""
  while IFS= read -r line; do
    if $first_line; then
      event_summary="$line"
      first_line=false
    else
      echo "  $line"
    fi
  done

  echo "  ${event_summary}"

  plays="$(echo "${event_summary}" | grep -oE "PLAYS=[0-9]+" | cut -d= -f2 || echo 0)"
  no_tracks="$(echo "${event_summary}" | grep -oE "NO_TRACKS=[0-9]+" | cut -d= -f2 || echo 0)"
  total=$(( ${plays:-0} + ${no_tracks:-0} ))

  if [ "${total}" -gt 0 ]; then
    _pass "${plays} play event(s), ${no_tracks} no-track event(s) in window"
  elif [ "${COLLECTOR}" = "kiis_top" ]; then
    _info "no events yet — daily collector first runs at midnight UTC"
  elif [ "${COLLECTOR}" = "kiis1027_radiowave" ]; then
    _info "no events yet — daily collector first runs at 09:00 UTC"
  elif [ "${COLLECTOR}" = "iheart_recent" ]; then
    _info "no events yet for KIISFM/iheart in window — check Z100 and WKSC source_ids too"
  else
    _warn "0 events in window — collector may have run but station was silent; check logs"
  fi
}

# ── 6. Log scan for collector activity ───────────────────────────
_head "6. Log scan — collector activity"

recent_logs="$($COMPOSE logs --tail=200 app 2>/dev/null || true)"
collector_lines="$(echo "${recent_logs}" | grep -i "${LOG_KEYWORD}" || true)"

if [ -n "${collector_lines}" ]; then
  line_count="$(echo "${collector_lines}" | wc -l | tr -d ' ')"
  _pass "${line_count} log line(s) matching '${LOG_KEYWORD}'"
  echo "${collector_lines}" | tail -5 | sed 's/^/    /'
else
  if [ "${COLLECTOR}" = "kiis_top" ]; then
    _info "no '${LOG_KEYWORD}' log lines yet — daily job has not fired since last restart"
  elif [ "${COLLECTOR}" = "iheart_recent" ]; then
    _warn "no '${LOG_KEYWORD}' log lines yet — hourly job; wait up to 60 min for first run"
  elif [ "${COLLECTOR}" = "kiis1027_radiowave" ]; then
    _info "no '${LOG_KEYWORD}' log lines yet — daily job fires at 09:00 UTC"
  else
    _fail "no '${LOG_KEYWORD}' log lines in last 200 lines — collector may not be running"
  fi
fi

# ── 7. Scan for FAILED runs in logs ──────────────────────────────
_head "7. Log scan — failures"

fail_lines="$(echo "${recent_logs}" | grep -iE "ERROR|CRITICAL|Traceback" \
  | grep -viE "persist_result_failed|capital_now_playing|No such container" || true)"

if [ -n "${fail_lines}" ]; then
  _warn "error/exception lines found in recent logs"
  echo "${fail_lines}" | head -5 | sed 's/^/    /'
else
  _pass "no ERROR/CRITICAL/Traceback in last 200 log lines"
fi

# ── Summary ───────────────────────────────────────────────────────
echo ""
echo "============================================================"
echo " SUMMARY: ${PASS} passed, ${FAIL} failed, ${WARN} warnings"
echo "============================================================"

if [ "${FAIL}" -gt 0 ]; then
  echo " One or more checks FAILED. Review output above."
  echo " Do not enable the next collector until this one is stable."
  exit 1
fi

if [ "${WARN}" -gt 0 ]; then
  echo " Checks passed with warnings. Review warnings above."
  echo " Wait for the 24-hour observation window before enabling the next collector."
else
  echo " All checks passed. Collector is running cleanly."
  echo " Wait 24 hours of passive observation before enabling the next collector."
fi
