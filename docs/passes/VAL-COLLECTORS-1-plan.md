# VAL-COLLECTORS-1 — Live Endpoint Validation for Extracted Collectors

**Date:** 2026-06-05
**Pass type:** VALIDATION — live network required; run from production server
**Depends on:** EXTRACT-2 deployed (station/source seeds in production DB)
**Blocks:** Enabling any of the 5 new collector flags

---

## 1. Purpose

Before any extracted collector flag can be set to `true`, the collector must be validated
against a live endpoint on the production server. This pass defines the acceptance criteria
and provides a runnable dry-run script.

---

## 2. Validation Codes and Acceptance Criteria

| VAL code | Collector | Endpoint | Acceptance criteria |
|----------|-----------|----------|---------------------|
| VAL-BBC1-001 | `BBCRadio1Collector` | `rms.api.bbc.co.uk/v2/services/bbc_radio_one/segments/latest` | HTTP 200, JSON with segment data, parser extracts ≥1 play or no_track |
| VAL-BBC1-006 | BBC Radio 1 | BBC ToS review | Automated access to RMS API confirmed permissible (manual check) |
| VAL-HEARTFM-002 | `HeartRadioCollector` | `www.heart.co.uk/radio/last-played-songs/` | HTTP 200, CSS selectors return ≥1 song title, parser extracts ≥1 play |
| VAL-Z100-001 | `IHeartNowPlayingCollector` | `api.iheart.com/...stream/614/currentTrack` | HTTP 200 or 204, parser returns play or no_track, no exception |
| VAL-WKSC-001 | `IHeartNowPlayingCollector` | `api.iheart.com/...stream/821/currentTrack` | HTTP 200 or 204, parser returns play or no_track, no exception |
| VAL-IHEART-TOP-001 | `IHeartTopSongsCollector` | `api.iheart.com/...stream/2501/topSongs` | HTTP 200, parser returns ≥1 play event, no exception |

VAL-BBC1-006 is a **manual ToS review** — it cannot be automated. Research the BBC Developer
terms of service before enabling `ENABLE_BBC_RADIO1_COLLECTOR`.

---

## 3. Running the Dry-Run

The script `docs/passes/val-collectors-1-dryrun.sh` runs each collector inside the
production container using the exact production UUIDs. It does NOT write to the DB
(`_persist_result` is not called — the collector is instantiated directly).

**Run all 5 collectors:**
```bash
ssh -o IdentitiesOnly=yes -i ~/.ssh/id_ed25519 root@178.105.238.18 'bash -s' \
    < ~/Documents/Prof_Mind/docs/passes/val-collectors-1-dryrun.sh \
    | tee /tmp/val-collectors-1.log
```

**Run one collector (e.g. Z100 only):**
```bash
ssh -o IdentitiesOnly=yes -i ~/.ssh/id_ed25519 root@178.105.238.18 'bash -s' -- --z100 \
    < ~/Documents/Prof_Mind/docs/passes/val-collectors-1-dryrun.sh
```

Available flags: `--bbc`, `--heart`, `--z100`, `--wksc`, `--kiis_top`

---

## 4. Expected Passing Output

```
=== Safety gate — flags must be false ===
  ENABLE_BBC_RADIO1_COLLECTOR=false  OK
  ENABLE_HEART_COLLECTOR=false       OK
  ENABLE_Z100_COLLECTOR=false        OK
  ENABLE_WKSC_COLLECTOR=false        OK
  ENABLE_IHEART_TOP_SONGS=false      OK
  SCHEDULER_ENABLED=false            OK

--- BBC Radio 1 (VAL-BBC1-001) ---
status=success plays=1 no_tracks=0
VAL-BBC1-001: PASS

--- Heart FM UK (VAL-HEARTFM-002) ---
status=success plays=10 no_tracks=0
VAL-HEARTFM-002: PASS

--- Z100 iHeart now-playing (VAL-Z100-001) ---
status=success plays=1 no_tracks=0
VAL-Z100-001: PASS

--- WKSC 103.5 iHeart now-playing (VAL-WKSC-001) ---
status=success plays=1 no_tracks=0
VAL-WKSC-001: PASS

--- KIIS-FM iHeart top songs (VAL-IHEART-TOP-001) ---
status=success plays=20 no_tracks=0
VAL-IHEART-TOP-001: PASS

============================================================
 SUMMARY: 5 passed, 0 failed
============================================================
```

`no_track` status is also acceptable — it means the station is between songs.
`failed` status means the endpoint was unreachable or the parser errored.

---

## 5. Failure Handling

| Failure type | Action |
|---|---|
| HTTP timeout / connection refused | Endpoint unreachable — do not enable; investigate |
| HTTP 4xx / 5xx | API issue — check URL, headers, station_id |
| Parser assertion error | Parser broke against live response — file a bug, do not enable |
| `AssertionError: no output produced` | Collector ran but produced nothing — may be valid if `no_track`; review raw payload |

Raw payloads from the dry-run are written to `/tmp/val_dryrun/` inside the container.
Inspect them with:
```bash
docker compose -f /opt/rmias/docker-compose.hetzner.yml exec app ls /tmp/val_dryrun/
```

---

## 6. Post-Validation Enablement Sequence

After each collector's VAL-* code passes:

1. Enable exactly **one** collector at a time in `.env.production` on the server.
2. Force-recreate the app container: `docker compose ... up -d --force-recreate app`
3. Wait 15 minutes.
4. Check logs: `docker compose ... logs --tail=50 app | grep -E "collected|FAILED|ERROR"`
5. Confirm play events appear in the admin UI.
6. Wait 24 hours of passive observation before enabling the next collector.

Do not enable any collector until:
- Its VAL-* code is PASS
- VAL-BBC1-006 (ToS) reviewed for BBC (manual)
- EXTRACT-2 is confirmed deployed (all 8 UUIDs FOUND in DB)

---

## 7. Enablement Order (recommended)

| Priority | Collector | Flag | Reason |
|----------|-----------|------|--------|
| 1 | Z100 | `ENABLE_Z100_COLLECTOR` | iHeart API — same pattern as existing KIIS (lowest risk) |
| 2 | WKSC | `ENABLE_WKSC_COLLECTOR` | iHeart API — same pattern (lowest risk) |
| 3 | KIIS top songs | `ENABLE_IHEART_TOP_SONGS` | iHeart API — daily cron, low traffic |
| 4 | Heart FM | `ENABLE_HEART_COLLECTOR` | CSS scraper — higher maintenance risk |
| 5 | BBC Radio 1 | `ENABLE_BBC_RADIO1_COLLECTOR` | Requires ToS review first |
