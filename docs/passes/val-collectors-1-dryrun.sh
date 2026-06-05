#!/usr/bin/env bash
# VAL-COLLECTORS-1 — Live dry-run for the 5 new extracted collectors.
#
# Run this FROM THE SERVER after EXTRACT-2 is deployed:
#
#   ssh -o IdentitiesOnly=yes -i ~/.ssh/id_ed25519 root@178.105.238.18 'bash -s' \
#       < ~/Documents/Prof_Mind/docs/passes/val-collectors-1-dryrun.sh \
#       | tee /tmp/val-collectors-1.log
#
# Or run specific collectors by passing flags:
#   ... 'bash -s' -- --bbc --heart --z100 --wksc --kiis_top
#
# Exit codes:
#   0  all selected collectors passed
#   1  one or more collectors failed

set -euo pipefail

SERVER_DIR="/opt/rmias"
COMPOSE="docker compose -f ${SERVER_DIR}/docker-compose.hetzner.yml --env-file ${SERVER_DIR}/.env.production"

# Parse optional flags
RUN_BBC=false RUN_HEART=false RUN_Z100=false RUN_WKSC=false RUN_KIIS_TOP=false RUN_ALL=true
for arg in "$@"; do
  case "$arg" in
    --bbc)      RUN_BBC=true;      RUN_ALL=false ;;
    --heart)    RUN_HEART=true;    RUN_ALL=false ;;
    --z100)     RUN_Z100=true;     RUN_ALL=false ;;
    --wksc)     RUN_WKSC=true;     RUN_ALL=false ;;
    --kiis_top) RUN_KIIS_TOP=true; RUN_ALL=false ;;
  esac
done
if $RUN_ALL; then
  RUN_BBC=true; RUN_HEART=true; RUN_Z100=true; RUN_WKSC=true; RUN_KIIS_TOP=true
fi

echo "============================================================"
echo " VAL-COLLECTORS-1 dry-run  $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "============================================================"
echo ""

# ────────────────────────────────────────────────────────────────
# Safety gate: confirm all flags are still false before any run
# ────────────────────────────────────────────────────────────────
echo "=== Safety gate — flags must be false ==="
cd "${SERVER_DIR}"
for flag in ENABLE_BBC_RADIO1_COLLECTOR ENABLE_HEART_COLLECTOR ENABLE_Z100_COLLECTOR \
            ENABLE_WKSC_COLLECTOR ENABLE_IHEART_TOP_SONGS SCHEDULER_ENABLED; do
  val="$(grep -E "^${flag}=" .env.production 2>/dev/null | cut -d= -f2- || echo "not_set")"
  if echo "$val" | grep -qiE "^(true|1|yes|on)$"; then
    echo "ABORT: ${flag}=${val} — must be false before dry-run"
    exit 1
  fi
  echo "  ${flag}=${val:-not_set}  OK"
done
echo ""

PASS_COUNT=0
FAIL_COUNT=0

# ────────────────────────────────────────────────────────────────
# Helper: run a one-shot collector inside the container
# ────────────────────────────────────────────────────────────────
run_collector() {
  local label="$1"
  local python_expr="$2"

  echo "--- ${label} ---"
  local out
  out="$($COMPOSE exec -T app python3 -c "$python_expr" 2>&1)" && rc=0 || rc=$?
  echo "$out"
  if [ $rc -eq 0 ]; then
    echo "RESULT: ${label} PASS"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "RESULT: ${label} FAIL (exit $rc)"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
  echo ""
}

# ────────────────────────────────────────────────────────────────
# BBC Radio 1
# ────────────────────────────────────────────────────────────────
if $RUN_BBC; then
  run_collector "BBC Radio 1 (VAL-BBC1-001)" "
import asyncio, uuid
from app.infrastructure.collectors.bbc_radio_1 import BBCRadio1Collector

async def run():
    c = BBCRadio1Collector(
        source_id=uuid.UUID('32800202-78b8-5e48-a502-f771615c8402'),
        station_id=uuid.UUID('9ecfd309-55e9-5df9-996f-2ea283b10568'),
        storage_root='/tmp/val_dryrun',
    )
    result = await c.run()
    status = result.collector_run.status.value
    plays = len(result.play_events)
    no_tracks = len(result.no_track_events)
    print(f'status={status} plays={plays} no_tracks={no_tracks}')
    assert status in ('success', 'no_track'), f'unexpected status: {status}'
    assert plays + no_tracks > 0 or status == 'no_track', 'no output produced'
    print('VAL-BBC1-001: PASS')

asyncio.run(run())
"
fi

# ────────────────────────────────────────────────────────────────
# Heart FM
# ────────────────────────────────────────────────────────────────
if $RUN_HEART; then
  run_collector "Heart FM UK (VAL-HEARTFM-002)" "
import asyncio, uuid
from app.infrastructure.collectors.heart_radio import HeartRadioCollector

async def run():
    c = HeartRadioCollector(
        source_id=uuid.UUID('4be04973-0050-55fa-ba03-30fac85f94e1'),
        station_id=uuid.UUID('17f49778-fd59-5f82-886e-645c78356435'),
        storage_root='/tmp/val_dryrun',
    )
    result = await c.run()
    status = result.collector_run.status.value
    plays = len(result.play_events)
    no_tracks = len(result.no_track_events)
    print(f'status={status} plays={plays} no_tracks={no_tracks}')
    assert status in ('success', 'no_track'), f'unexpected status: {status}'
    assert plays + no_tracks > 0 or status == 'no_track', 'no output produced'
    print('VAL-HEARTFM-002: PASS')

asyncio.run(run())
"
fi

# ────────────────────────────────────────────────────────────────
# Z100 (WHTZ) iHeart now-playing
# ────────────────────────────────────────────────────────────────
if $RUN_Z100; then
  run_collector "Z100 iHeart now-playing (VAL-Z100-001)" "
import asyncio, uuid
from app.infrastructure.collectors.iheart_now_playing import IHeartNowPlayingCollector

async def run():
    c = IHeartNowPlayingCollector(
        source_id=uuid.UUID('b7cc2e45-5949-5995-be06-a89527aa4f66'),
        station_id=uuid.UUID('442dced5-003f-5d3f-acc7-dacf397be992'),
        iheart_station_id='614',
        storage_root='/tmp/val_dryrun',
    )
    result = await c.run()
    status = result.collector_run.status.value
    plays = len(result.play_events)
    no_tracks = len(result.no_track_events)
    print(f'status={status} plays={plays} no_tracks={no_tracks}')
    assert status in ('success', 'no_track'), f'unexpected status: {status}'
    print('VAL-Z100-001: PASS')

asyncio.run(run())
"
fi

# ────────────────────────────────────────────────────────────────
# WKSC iHeart now-playing
# ────────────────────────────────────────────────────────────────
if $RUN_WKSC; then
  run_collector "WKSC 103.5 iHeart now-playing (VAL-WKSC-001)" "
import asyncio, uuid
from app.infrastructure.collectors.iheart_now_playing import IHeartNowPlayingCollector

async def run():
    c = IHeartNowPlayingCollector(
        source_id=uuid.UUID('00535f6c-73c6-5cd0-aed0-2cc481891239'),
        station_id=uuid.UUID('189482a2-f5a0-50c6-8774-cfd22dd43037'),
        iheart_station_id='821',
        storage_root='/tmp/val_dryrun',
    )
    result = await c.run()
    status = result.collector_run.status.value
    plays = len(result.play_events)
    no_tracks = len(result.no_track_events)
    print(f'status={status} plays={plays} no_tracks={no_tracks}')
    assert status in ('success', 'no_track'), f'unexpected status: {status}'
    print('VAL-WKSC-001: PASS')

asyncio.run(run())
"
fi

# ────────────────────────────────────────────────────────────────
# KIIS-FM iHeart top songs
# ────────────────────────────────────────────────────────────────
if $RUN_KIIS_TOP; then
  run_collector "KIIS-FM iHeart top songs (VAL-IHEART-TOP-001)" "
import asyncio, uuid
from app.infrastructure.collectors.iheart_top_songs import IHeartTopSongsCollector

async def run():
    c = IHeartTopSongsCollector(
        source_id=uuid.UUID('14f4d232-3258-5688-8d63-77b23532e1d7'),
        station_id=uuid.UUID('dc1dc7fa-fb3a-5451-b6e8-42bcac001612'),
        iheart_station_id='2501',
        storage_root='/tmp/val_dryrun',
    )
    result = await c.run()
    status = result.collector_run.status.value
    plays = len(result.play_events)
    no_tracks = len(result.no_track_events)
    print(f'status={status} plays={plays} no_tracks={no_tracks}')
    assert status in ('success', 'no_track'), f'unexpected status: {status}'
    print('VAL-IHEART-TOP-001: PASS')

asyncio.run(run())
"
fi

# ────────────────────────────────────────────────────────────────
# Summary
# ────────────────────────────────────────────────────────────────
echo "============================================================"
echo " SUMMARY: ${PASS_COUNT} passed, ${FAIL_COUNT} failed"
echo "============================================================"

if [ $FAIL_COUNT -gt 0 ]; then
  echo "One or more collectors FAILED. Do not enable their flags."
  echo "Review output above and check VAL register before proceeding."
  exit 1
fi

echo "All selected collectors passed dry-run."
echo "Review plays/no_tracks output before enabling any flag."
echo "Each flag requires a separate production enablement pass."
