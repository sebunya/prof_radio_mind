#!/usr/bin/env bash
# val-live-endpoints.sh — Live endpoint reachability validation.
# VAL-BBC1-001, VAL-HEARTFM-002, VAL-Z100-001, VAL-WKSC-001,
# VAL-IHEART-TOP-001, VAL-IHEART-RECENT-001
#
# Makes raw HTTP requests only. No collector execution. No parser execution.
# No DB reads or writes. No flag changes. No scheduler interaction.
#
# Prerequisite: VAL-COLLECTORS-1 must pass (all flags confirmed false, EXTRACT-2
# station/source records confirmed in DB) before running this script.
#
# Run FROM YOUR MAC:
#
#   ssh -o IdentitiesOnly=yes -i ~/.ssh/id_ed25519 root@178.105.238.18 'bash -s' \
#       < ~/Documents/Prof_Mind/docs/passes/val-live-endpoints.sh \
#       | tee /tmp/val-live-endpoints.log
#
# Run a single endpoint only:
#   ssh -o IdentitiesOnly=yes -i ~/.ssh/id_ed25519 root@178.105.238.18 'bash -s' -- --z100 \
#       < ~/Documents/Prof_Mind/docs/passes/val-live-endpoints.sh
#
# Available flags: --bbc  --heart  --z100  --wksc  --kiis_top  --iheart_recent
#                  (default: all six)
#
# Exit codes:
#   0  all selected checks passed
#   1  one or more checks failed, or safety gate tripped

set -euo pipefail

SERVER_DIR="/opt/rmias"
COMPOSE="docker compose -f ${SERVER_DIR}/docker-compose.hetzner.yml --env-file ${SERVER_DIR}/.env.production"

PASS=0
FAIL=0

_pass() { echo "  PASS  $*"; PASS=$((PASS+1)); }
_fail() { echo "  FAIL  $*"; FAIL=$((FAIL+1)); }
_head() { echo ""; echo "=== $* ==="; }

# ── Parse run-mode flags ──────────────────────────────────────────
RUN_BBC=false; RUN_HEART=false; RUN_Z100=false; RUN_WKSC=false
RUN_KIIS_TOP=false; RUN_IHEART_RECENT=false
RUN_ALL=true

for arg in "$@"; do
  case "$arg" in
    --bbc)           RUN_BBC=true;           RUN_ALL=false ;;
    --heart)         RUN_HEART=true;         RUN_ALL=false ;;
    --z100)          RUN_Z100=true;          RUN_ALL=false ;;
    --wksc)          RUN_WKSC=true;          RUN_ALL=false ;;
    --kiis_top)      RUN_KIIS_TOP=true;      RUN_ALL=false ;;
    --iheart_recent) RUN_IHEART_RECENT=true; RUN_ALL=false ;;
  esac
done

if $RUN_ALL; then
  RUN_BBC=true; RUN_HEART=true; RUN_Z100=true; RUN_WKSC=true
  RUN_KIIS_TOP=true; RUN_IHEART_RECENT=true
fi

echo "============================================================"
echo " VAL-LIVE-ENDPOINTS  $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "============================================================"

# ── Safety gate — all collector flags must be false ───────────────
_head "Safety gate — collector flags must be false"

flag_is_true() {
  grep -qiE "^${1}=(true|1|yes|on)$" "${SERVER_DIR}/.env.production" 2>/dev/null
}

GATE_OK=true
for flag in \
  ENABLE_BBC_RADIO1_COLLECTOR \
  ENABLE_HEART_COLLECTOR \
  ENABLE_Z100_COLLECTOR \
  ENABLE_WKSC_COLLECTOR \
  ENABLE_IHEART_TOP_SONGS \
  ENABLE_IHEART_RECENTLY_PLAYED \
  SCHEDULER_ENABLED; do
  val="$(grep -E "^${flag}=" "${SERVER_DIR}/.env.production" 2>/dev/null | cut -d= -f2- || echo 'not_set')"
  if flag_is_true "${flag}"; then
    echo "  ${flag}=${val} — ACTIVE — ABORT"
    GATE_OK=false
  else
    echo "  ${flag}=${val:-not_set}  OK"
  fi
done

if ! $GATE_OK; then
  echo ""
  echo "SAFETY GATE FAILED. One or more collector flags are active."
  echo "Do not run live endpoint checks while any collector flag is enabled."
  echo "SUMMARY: ABORTED"
  exit 1
fi

# ── VAL-BBC1-001: BBC Radio 1 RMS API ────────────────────────────
if $RUN_BBC; then
  _head "VAL-BBC1-001 — BBC Radio 1 RMS API"
  echo "  URL: https://rms.api.bbc.co.uk/v2/services/bbc_radio_one/segments/latest"

  bbc_result="$($COMPOSE exec -T app python3 -c "
import asyncio, json
from app.infrastructure.http.client import build_client

async def check():
    url = 'https://rms.api.bbc.co.uk/v2/services/bbc_radio_one/segments/latest'
    try:
        async with await build_client(timeout=15.0) as c:
            r = await c.get(url)
        status = r.status_code
        if status == 204:
            print('STATUS=204 RESULT=no_segment')
            return
        try:
            data = json.loads(r.content)
        except Exception:
            print(f'STATUS={status} ERROR=json_parse')
            return
        segs = data.get('data')
        if not isinstance(segs, list):
            print(f'STATUS={status} ERROR=no_data_list')
            return
        music_count = sum(1 for s in segs if isinstance(s, dict) and s.get('type') == 'music')
        print(f'STATUS={status} SEGMENTS={len(segs)} MUSIC={music_count}')
    except Exception as e:
        print(f'STATUS=ERROR EXCEPTION={type(e).__name__}')

asyncio.run(check())
" 2>&1 | tail -1)"

  echo "  ${bbc_result}"

  if echo "${bbc_result}" | grep -qE "^STATUS=200 SEGMENTS=[0-9]+"; then
    _pass "VAL-BBC1-001 — HTTP 200, data list present"
  elif echo "${bbc_result}" | grep -qE "^STATUS=204"; then
    _pass "VAL-BBC1-001 — HTTP 204 (no current segment)"
  else
    _fail "VAL-BBC1-001 — ${bbc_result}"
  fi

  echo "  NOTE: VAL-BBC1-006 (BBC ToS review) is a manual check — not automated here."
fi

# ── VAL-HEARTFM-002: Heart FM last-played-songs CSS selectors ─────
if $RUN_HEART; then
  _head "VAL-HEARTFM-002 — Heart FM last-played-songs page"
  echo "  URL: https://www.heart.co.uk/radio/last-played-songs/"

  heart_result="$($COMPOSE exec -T app python3 -c "
import asyncio
from app.infrastructure.http.client import build_client

async def check():
    url = 'https://www.heart.co.uk/radio/last-played-songs/'
    try:
        async with await build_client(timeout=20.0) as c:
            r = await c.get(url)
        status = r.status_code
        if status != 200:
            print(f'STATUS={status} ERROR=non_200')
            return
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(r.content, 'lxml')
        container = soup.select_one('div.station-song-history')
        if container is None:
            print(f'STATUS={status} CONTAINER=MISSING')
            return
        items = container.select('div.song-item')
        titles = [el.get_text(strip=True) for el in container.select('span.song-item__title')]
        valid_titles = [t for t in titles if t]
        print(f'STATUS={status} CONTAINER=FOUND ITEMS={len(items)} TITLES={len(valid_titles)}')
    except Exception as e:
        print(f'STATUS=ERROR EXCEPTION={type(e).__name__}')

asyncio.run(check())
" 2>&1 | tail -1)"

  echo "  ${heart_result}"

  if echo "${heart_result}" | grep -qE "^STATUS=200 CONTAINER=FOUND ITEMS=[1-9]"; then
    _pass "VAL-HEARTFM-002 — HTTP 200, div.station-song-history found, song items present"
  elif echo "${heart_result}" | grep -qE "^STATUS=200 CONTAINER=FOUND ITEMS=0"; then
    _fail "VAL-HEARTFM-002 — container found but 0 song items (possible selector drift or empty page)"
  elif echo "${heart_result}" | grep -qE "CONTAINER=MISSING"; then
    _fail "VAL-HEARTFM-002 — div.station-song-history not found (selector drift — do not enable)"
  else
    _fail "VAL-HEARTFM-002 — ${heart_result}"
  fi
fi

# ── VAL-Z100-001: Z100 iHeart now-playing (station 614) ──────────
if $RUN_Z100; then
  _head "VAL-Z100-001 — Z100 iHeart now-playing (station 614)"
  echo "  URL: https://api.iheart.com/api/v3/live-meta/stream/614/currentTrack"

  z100_result="$($COMPOSE exec -T app python3 -c "
import asyncio, json
from app.infrastructure.http.client import build_client

async def check():
    url = 'https://api.iheart.com/api/v3/live-meta/stream/614/currentTrack'
    try:
        async with await build_client(timeout=15.0) as c:
            r = await c.get(url)
        status = r.status_code
        if status == 204:
            print('STATUS=204 RESULT=no_track')
            return
        try:
            data = json.loads(r.content)
        except Exception:
            print(f'STATUS={status} ERROR=json_parse')
            return
        ct = data.get('currentTrack')
        if not isinstance(ct, dict):
            print(f'STATUS={status} ERROR=no_currentTrack_field')
            return
        artist = (ct.get('artist') or '').strip()
        title = (ct.get('title') or '').strip()
        has_track = bool(artist and title)
        print(f'STATUS={status} CURRENT_TRACK=FOUND HAS_ARTIST_TITLE={has_track}')
    except Exception as e:
        print(f'STATUS=ERROR EXCEPTION={type(e).__name__}')

asyncio.run(check())
" 2>&1 | tail -1)"

  echo "  ${z100_result}"

  if echo "${z100_result}" | grep -qE "^STATUS=200 CURRENT_TRACK=FOUND"; then
    _pass "VAL-Z100-001 — HTTP 200, currentTrack present"
  elif echo "${z100_result}" | grep -qE "^STATUS=204"; then
    _pass "VAL-Z100-001 — HTTP 204 (no track, between songs)"
  else
    _fail "VAL-Z100-001 — ${z100_result}"
  fi
fi

# ── VAL-WKSC-001: WKSC 103.5 iHeart now-playing (station 821) ────
if $RUN_WKSC; then
  _head "VAL-WKSC-001 — WKSC 103.5 iHeart now-playing (station 821)"
  echo "  URL: https://api.iheart.com/api/v3/live-meta/stream/821/currentTrack"

  wksc_result="$($COMPOSE exec -T app python3 -c "
import asyncio, json
from app.infrastructure.http.client import build_client

async def check():
    url = 'https://api.iheart.com/api/v3/live-meta/stream/821/currentTrack'
    try:
        async with await build_client(timeout=15.0) as c:
            r = await c.get(url)
        status = r.status_code
        if status == 204:
            print('STATUS=204 RESULT=no_track')
            return
        try:
            data = json.loads(r.content)
        except Exception:
            print(f'STATUS={status} ERROR=json_parse')
            return
        ct = data.get('currentTrack')
        if not isinstance(ct, dict):
            print(f'STATUS={status} ERROR=no_currentTrack_field')
            return
        artist = (ct.get('artist') or '').strip()
        title = (ct.get('title') or '').strip()
        has_track = bool(artist and title)
        print(f'STATUS={status} CURRENT_TRACK=FOUND HAS_ARTIST_TITLE={has_track}')
    except Exception as e:
        print(f'STATUS=ERROR EXCEPTION={type(e).__name__}')

asyncio.run(check())
" 2>&1 | tail -1)"

  echo "  ${wksc_result}"

  if echo "${wksc_result}" | grep -qE "^STATUS=200 CURRENT_TRACK=FOUND"; then
    _pass "VAL-WKSC-001 — HTTP 200, currentTrack present"
  elif echo "${wksc_result}" | grep -qE "^STATUS=204"; then
    _pass "VAL-WKSC-001 — HTTP 204 (no track, between songs)"
  else
    _fail "VAL-WKSC-001 — ${wksc_result}"
  fi
fi

# ── VAL-IHEART-TOP-001: KIIS-FM iHeart top songs (station 2501) ──
if $RUN_KIIS_TOP; then
  _head "VAL-IHEART-TOP-001 — KIIS-FM iHeart top songs (station 2501)"
  echo "  URL: https://api.iheart.com/api/v3/live-meta/stream/2501/topSongs"

  kiis_result="$($COMPOSE exec -T app python3 -c "
import asyncio, json
from app.infrastructure.http.client import build_client

async def check():
    url = 'https://api.iheart.com/api/v3/live-meta/stream/2501/topSongs'
    try:
        async with await build_client(timeout=15.0) as c:
            r = await c.get(url)
        status = r.status_code
        if status == 204:
            print('STATUS=204 RESULT=no_songs')
            return
        try:
            data = json.loads(r.content)
        except Exception:
            print(f'STATUS={status} ERROR=json_parse')
            return
        songs = data.get('topSongs') or data.get('songs')
        if songs is None:
            print(f'STATUS={status} ERROR=no_topSongs_or_songs_field')
            return
        if not isinstance(songs, list):
            print(f'STATUS={status} ERROR=songs_not_list')
            return
        print(f'STATUS={status} SONGS={len(songs)}')
    except Exception as e:
        print(f'STATUS=ERROR EXCEPTION={type(e).__name__}')

asyncio.run(check())
" 2>&1 | tail -1)"

  echo "  ${kiis_result}"

  if echo "${kiis_result}" | grep -qE "^STATUS=200 SONGS=[1-9]"; then
    _pass "VAL-IHEART-TOP-001 — HTTP 200, topSongs list with entries"
  elif echo "${kiis_result}" | grep -qE "^STATUS=200 SONGS=0"; then
    _fail "VAL-IHEART-TOP-001 — HTTP 200 but 0 songs returned (unexpected)"
  else
    _fail "VAL-IHEART-TOP-001 — ${kiis_result}"
  fi
fi

# ── VAL-IHEART-RECENT-001: iHeart recently-played (station 2501, representative) ──
if $RUN_IHEART_RECENT; then
  _head "VAL-IHEART-RECENT-001 — iHeart recently-played (station 2501 / KIISFM)"
  echo "  URL: https://api.iheart.com/api/v3/live-meta/stream/2501/recentlyPlayed"
  echo "  (Same URL pattern used for Z100/614 and WKSC/821 — tested here via KIISFM as representative)"

  recent_result="$($COMPOSE exec -T app python3 -c "
import asyncio, json
from app.infrastructure.http.client import build_client

async def check():
    url = 'https://api.iheart.com/api/v3/live-meta/stream/2501/recentlyPlayed'
    try:
        async with await build_client(timeout=15.0) as c:
            r = await c.get(url)
        status = r.status_code
        if status == 204:
            print('STATUS=204 RESULT=no_tracks')
            return
        try:
            data = json.loads(r.content)
        except Exception:
            print(f'STATUS={status} ERROR=json_parse')
            return
        tracks = data.get('tracks') or data.get('recentTracks')
        if tracks is None:
            print(f'STATUS={status} ERROR=no_tracks_or_recentTracks_field')
            return
        if not isinstance(tracks, list):
            print(f'STATUS={status} ERROR=tracks_not_list')
            return
        print(f'STATUS={status} TRACKS={len(tracks)}')
    except Exception as e:
        print(f'STATUS=ERROR EXCEPTION={type(e).__name__}')

asyncio.run(check())
" 2>&1 | tail -1)"

  echo "  ${recent_result}"

  if echo "${recent_result}" | grep -qE "^STATUS=200 TRACKS=[1-9]"; then
    _pass "VAL-IHEART-RECENT-001 — HTTP 200, tracks list with entries"
  elif echo "${recent_result}" | grep -qE "^STATUS=200 TRACKS=0"; then
    _fail "VAL-IHEART-RECENT-001 — HTTP 200 but 0 tracks returned (station may be mid-show silence)"
  elif echo "${recent_result}" | grep -qE "^STATUS=204"; then
    _pass "VAL-IHEART-RECENT-001 — HTTP 204 (endpoint reachable; no recently-played data at this moment)"
  else
    _fail "VAL-IHEART-RECENT-001 — ${recent_result}"
  fi
fi

# ── Summary ───────────────────────────────────────────────────────
echo ""
echo "============================================================"
echo " SUMMARY: ${PASS} passed, ${FAIL} failed"
echo "============================================================"

if [ "${FAIL}" -gt 0 ]; then
  echo " One or more endpoint checks FAILED."
  echo " Do not enable the corresponding collector flag."
  echo " Review the failure output above."
  exit 1
fi

echo " All selected endpoint checks passed."
echo ""
echo " Reminder — manual check still required:"
echo "   VAL-BBC1-006: BBC Terms of Service review before enabling BBC Radio 1 collector."
echo ""
echo " Enablement order (one at a time, 24h observation between each):"
echo "   1. ENABLE_Z100_COLLECTOR"
echo "   2. ENABLE_WKSC_COLLECTOR"
echo "   3. ENABLE_IHEART_RECENTLY_PLAYED  (batch fallback: KIISFM + Z100 + WKSC)"
echo "   4. ENABLE_IHEART_TOP_SONGS"
echo "   5. ENABLE_HEART_COLLECTOR"
echo "   6. ENABLE_BBC_RADIO1_COLLECTOR (after VAL-BBC1-006 manual review)"
