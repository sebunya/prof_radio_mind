# VAL-LIVE-ENDPOINTS — Live Endpoint Reachability Validation

**Date:** 2026-06-05
**Pass:** VAL-LIVE-ENDPOINTS
**Status:** PENDING — requires VAL-COLLECTORS-1 to pass first

---

## Objective

Confirm that each new collector's live provider endpoint is reachable from the production
server and returns a response with the expected structure. This is a raw HTTP check only —
no collector is executed, no data is written to the database, no flags are changed.

Covers:

| VAL code | Collector | Endpoint |
|----------|-----------|----------|
| VAL-BBC1-001 | `BBCRadio1Collector` | BBC RMS API — `rms.api.bbc.co.uk/v2/services/bbc_radio_one/segments/latest` |
| VAL-HEARTFM-002 | `HeartRadioCollector` | Heart FM last-played-songs page |
| VAL-Z100-001 | `IHeartNowPlayingCollector` | iHeart stream 614 (Z100) currentTrack |
| VAL-WKSC-001 | `IHeartNowPlayingCollector` | iHeart stream 821 (WKSC 103.5) currentTrack |
| VAL-IHEART-TOP-001 | `IHeartTopSongsCollector` | iHeart stream 2501 (KIIS-FM) topSongs |

**VAL-BBC1-006** (BBC ToS manual review) is NOT in this script — it requires a manual
review of the BBC Developer terms of service. It must be completed before enabling
`ENABLE_BBC_RADIO1_COLLECTOR`.

---

## Hard Rules

- Do not enable any collector flag
- Do not enable the scheduler
- Do not write to the database
- Do not call `.run()` on any collector
- Do not call any parser
- Do not modify `.env.production`

---

## Acceptance Criteria

| VAL code | Pass condition | Acceptable alternative |
|----------|---------------|----------------------|
| VAL-BBC1-001 | HTTP 200, JSON `data` field is a list | HTTP 204 (no current segment) |
| VAL-HEARTFM-002 | HTTP 200, `div.station-song-history` found, ≥1 `div.song-item` | — |
| VAL-Z100-001 | HTTP 200, `currentTrack` dict present | HTTP 204 (no track) |
| VAL-WKSC-001 | HTTP 200, `currentTrack` dict present | HTTP 204 (no track) |
| VAL-IHEART-TOP-001 | HTTP 200, `topSongs`/`songs` list with ≥1 entry | — |

---

## How to Run

From your Mac, after VAL-COLLECTORS-1 passes:

```bash
ssh -o IdentitiesOnly=yes -i ~/.ssh/id_ed25519 root@178.105.238.18 'bash -s' \
    < ~/Documents/Prof_Mind/docs/passes/val-live-endpoints.sh \
    | tee /tmp/val-live-endpoints.log
```

Run a single endpoint only (example — Z100):

```bash
ssh -o IdentitiesOnly=yes -i ~/.ssh/id_ed25519 root@178.105.238.18 'bash -s' -- --z100 \
    < ~/Documents/Prof_Mind/docs/passes/val-live-endpoints.sh
```

Available flags: `--bbc`  `--heart`  `--z100`  `--wksc`  `--kiis_top`

---

## Expected Passing Output

```
=== Safety gate — collector flags must be false ===
  ENABLE_BBC_RADIO1_COLLECTOR=false  OK
  ENABLE_HEART_COLLECTOR=false       OK
  ENABLE_Z100_COLLECTOR=false        OK
  ENABLE_WKSC_COLLECTOR=false        OK
  ENABLE_IHEART_TOP_SONGS=false      OK
  SCHEDULER_ENABLED=false            OK

=== VAL-BBC1-001 — BBC Radio 1 RMS API ===
  URL: https://rms.api.bbc.co.uk/v2/services/bbc_radio_one/segments/latest
  STATUS=200 SEGMENTS=5 MUSIC=2
  PASS  VAL-BBC1-001 — HTTP 200, data list present
  NOTE: VAL-BBC1-006 (BBC ToS review) is a manual check — not automated here.

=== VAL-HEARTFM-002 — Heart FM last-played-songs page ===
  URL: https://www.heart.co.uk/radio/last-played-songs/
  STATUS=200 CONTAINER=FOUND ITEMS=10 TITLES=10
  PASS  VAL-HEARTFM-002 — HTTP 200, div.station-song-history found, song items present

=== VAL-Z100-001 — Z100 iHeart now-playing (station 614) ===
  URL: https://api.iheart.com/api/v3/live-meta/stream/614/currentTrack
  STATUS=200 CURRENT_TRACK=FOUND HAS_ARTIST_TITLE=True
  PASS  VAL-Z100-001 — HTTP 200, currentTrack present

=== VAL-WKSC-001 — WKSC 103.5 iHeart now-playing (station 821) ===
  URL: https://api.iheart.com/api/v3/live-meta/stream/821/currentTrack
  STATUS=200 CURRENT_TRACK=FOUND HAS_ARTIST_TITLE=True
  PASS  VAL-WKSC-001 — HTTP 200, currentTrack present

=== VAL-IHEART-TOP-001 — KIIS-FM iHeart top songs (station 2501) ===
  URL: https://api.iheart.com/api/v3/live-meta/stream/2501/topSongs
  STATUS=200 SONGS=20
  PASS  VAL-IHEART-TOP-001 — HTTP 200, topSongs list with entries

============================================================
 SUMMARY: 5 passed, 0 failed
============================================================
```

HTTP 204 responses (between songs) are also valid for now-playing endpoints.

---

## Failure Handling

| Failure output | Likely cause | Action |
|----------------|--------------|--------|
| `STATUS=ERROR EXCEPTION=ConnectError` | Endpoint unreachable from production server | Check URL; retry; investigate network |
| `STATUS=403` or `STATUS=429` | API blocked / rate limited | Check headers; review ToS; do not enable |
| `STATUS=200 ERROR=json_parse` | Endpoint returned non-JSON | Collector/parser will fail — do not enable |
| `STATUS=200 ERROR=no_currentTrack_field` | iHeart response schema changed | Update parser; file bug; do not enable |
| `CONTAINER=MISSING` | Heart FM CSS selector drift | Update parser CSS selectors; file bug; do not enable |
| `STATUS=200 SONGS=0` | iHeart topSongs returned empty list | Unexpected — check if API changed; do not enable |

---

## Checklist

### Pre-Run
- [ ] VAL-COLLECTORS-1 passed (SUMMARY: N passed, 0 failed)
- [ ] App is running and `GET /health` returns 200

### Script Execution
- [ ] Script runs without bash error
- [ ] Safety gate passes — all 6 flags false
- [ ] VAL-BBC1-001 PASS (BBC RMS API reachable, data list present)
- [ ] VAL-HEARTFM-002 PASS (page reachable, selector found, ≥1 song item)
- [ ] VAL-Z100-001 PASS (iHeart 614 reachable, 200 or 204)
- [ ] VAL-WKSC-001 PASS (iHeart 821 reachable, 200 or 204)
- [ ] VAL-IHEART-TOP-001 PASS (iHeart 2501 topSongs, ≥1 song)
- [ ] SUMMARY: 5 passed, 0 failed

### Manual Check (separate — not scripted)
- [ ] VAL-BBC1-006 — BBC Developer ToS reviewed; automated access to RMS API confirmed permissible

---

## Next Step After This Pass

Only after all checklist items are marked complete:

Proceed to enablement — one collector at a time, in recommended order:

| Step | Flag | Prerequisite VAL codes |
|------|------|----------------------|
| 1 | `ENABLE_Z100_COLLECTOR` | VAL-Z100-001 PASS |
| 2 | `ENABLE_WKSC_COLLECTOR` | VAL-WKSC-001 PASS |
| 3 | `ENABLE_IHEART_TOP_SONGS` | VAL-IHEART-TOP-001 PASS |
| 4 | `ENABLE_HEART_COLLECTOR` | VAL-HEARTFM-002 PASS |
| 5 | `ENABLE_BBC_RADIO1_COLLECTOR` | VAL-BBC1-001 PASS + VAL-BBC1-006 manual PASS |

Enablement procedure for each collector:
1. Set the flag to `true` in `.env.production` on the server
2. Force-recreate: `docker compose -f /opt/rmias/docker-compose.hetzner.yml up -d --force-recreate app`
3. Wait 15 minutes
4. Check logs: `docker compose ... logs --tail=50 app | grep -E "collected|FAILED|ERROR"`
5. Confirm play events appear in the admin UI
6. Wait 24 hours before enabling the next collector
