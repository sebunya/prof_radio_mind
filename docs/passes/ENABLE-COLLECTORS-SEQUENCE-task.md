# ENABLE-COLLECTORS-SEQUENCE — Ordered Collector Enablement Plan

**Date:** 2026-06-05
**Status:** BLOCKED — requires VAL-COLLECTORS-1 and VAL-LIVE-ENDPOINTS to pass first

---

## Prerequisites (all must be ✅ before any collector is enabled)

- [ ] EXTRACT-2/3/4 deployed to production and confirmed in DB (VAL-COLLECTORS-1 pass)
- [ ] All live endpoints reachable (VAL-LIVE-ENDPOINTS pass — 7 passed, 0 failed)
- [ ] VAL-BBC1-006: BBC ToS manual review complete (before Step 7 only)
- [ ] `GET /health` returns 200

---

## Hard Rules

- Enable exactly **one** collector at a time
- Wait **24 hours** of passive observation before enabling the next
- Never enable a collector whose VAL code has not passed
- Never modify more than one flag per restart
- Never enable the scheduler without first enabling at least one collector flag
- Do not force-push main during any enablement step

---

## Enablement Procedure (repeated for each step below)

1. On the production server, edit `.env.production`:
   ```
   ENABLE_<FLAG>=true
   ```
2. Force-recreate the app container:
   ```bash
   docker compose -f /opt/rmias/docker-compose.hetzner.yml up -d --force-recreate app
   ```
3. Wait **15 minutes** for the first poll cycle to complete.
4. Run the post-enablement check from your Mac:
   ```bash
   ssh -o IdentitiesOnly=yes -i ~/.ssh/id_ed25519 root@178.105.238.18 'bash -s' -- --<flag> \
       < ~/Documents/Prof_Mind/docs/passes/val-post-enable.sh \
       | tee /tmp/val-post-enable-<flag>.log
   ```
5. Confirm `SUMMARY: N passed, 0 failed` (warnings acceptable if explained).
6. Check admin UI: play events appear for the station.
7. **Wait 24 hours** before proceeding to the next step.

---

## Step 1 — Z100 (`ENABLE_Z100_COLLECTOR`)

**Prerequisite VAL codes:** VAL-Z100-001 PASS

| Item | Detail |
|------|--------|
| Flag | `ENABLE_Z100_COLLECTOR=true` |
| Station | Z100 New York (`WHTZ`) |
| Source type | `iheart` (station_id 614) |
| Collector | `IHeartNowPlayingCollector` |
| Cadence | Every 5 minutes |
| Log pattern | `z100_now_playing status=... plays=... no_tracks=...` |
| Post-enable flag | `--z100` |

**Why first:** Same iHeart API pattern as existing KIIS collector — lowest risk, already proven working infrastructure.

### Checklist
- [ ] VAL-Z100-001 PASS confirmed
- [ ] `ENABLE_Z100_COLLECTOR=true` set in `.env.production`
- [ ] Container force-recreated
- [ ] Waited 15 minutes
- [ ] `val-post-enable.sh --z100` → SUMMARY: 0 failed
- [ ] Play events visible in admin UI for Z100
- [ ] `ENABLE_NIGHTLY_REPORT_GENERATION=true` set (safe to enable now; job skips stations with no data)
- [ ] Waiting 24 hours

---

## Step 2 — WKSC (`ENABLE_WKSC_COLLECTOR`)

**Prerequisite VAL codes:** VAL-WKSC-001 PASS

| Item | Detail |
|------|--------|
| Flag | `ENABLE_WKSC_COLLECTOR=true` |
| Station | WKSC 103.5 Chicago (`WKSC`) |
| Source type | `iheart` (station_id 821) |
| Collector | `IHeartNowPlayingCollector` |
| Cadence | Every 5 minutes |
| Log pattern | `wksc_now_playing status=... plays=... no_tracks=...` |
| Post-enable flag | `--wksc` |

**Why second:** Same iHeart pattern, second lowest risk.

### Checklist
- [ ] Z100 (Step 1) stable for 24 hours
- [ ] VAL-WKSC-001 PASS confirmed

- [ ] `ENABLE_WKSC_COLLECTOR=true` set in `.env.production`
- [ ] Container force-recreated
- [ ] Waited 15 minutes
- [ ] `val-post-enable.sh --wksc` → SUMMARY: 0 failed
- [ ] Play events visible in admin UI for WKSC
- [ ] Waiting 24 hours

---

## Step 3 — iHeart Recently-Played (`ENABLE_IHEART_RECENTLY_PLAYED`)

**Prerequisite VAL codes:** VAL-IHEART-RECENT-001 PASS

| Item | Detail |
|------|--------|
| Flag | `ENABLE_IHEART_RECENTLY_PLAYED=true` |
| Station | KIISFM + Z100 (WHTZ) + WKSC — all three in one job |
| Source type | `iheart` (station IDs 2501 / 614 / 821) |
| Collector | `IHeartRecentlyPlayedCollector` |
| Cadence | Every **60 minutes** |
| Log pattern | `iheart_recently_played_collected station_id=... iheart_id=... status=... plays=...` |
| Post-enable flag | `--iheart_recent` |

**Why third:** iHeart API, same stations as Steps 1–2. Batch fallback that catches short tracks missed by the 5-minute now-playing poll. Low traffic (1 request/hour per station). `source_event_id` dedup prevents re-insertion on repeat polls. Enable after Z100 and WKSC now-playing are confirmed stable so the fallback complements rather than replaces primary collection.

**Note:** Post-enable check uses KIISFM as the representative DB query station. To verify all three stations, check DB directly:
```sql
SELECT source_id, COUNT(*), MAX(played_at)
FROM play_events
WHERE played_at > NOW() - INTERVAL '90 minutes'
GROUP BY source_id;
```

### Checklist
- [ ] WKSC (Step 2) stable for 24 hours
- [ ] VAL-IHEART-RECENT-001 PASS confirmed
- [ ] `ENABLE_IHEART_RECENTLY_PLAYED=true` set in `.env.production`
- [ ] Container force-recreated
- [ ] Waited 65 minutes for first run
- [ ] `val-post-enable.sh --iheart_recent` → SUMMARY: 0 failed
- [ ] Play events visible in admin UI for at least one of KIISFM / Z100 / WKSC
- [ ] Waiting 24 hours

---

## Step 4 — KIIS-FM Top Songs (`ENABLE_IHEART_TOP_SONGS`)

**Prerequisite VAL codes:** VAL-IHEART-TOP-001 PASS

| Item | Detail |
|------|--------|
| Flag | `ENABLE_IHEART_TOP_SONGS=true` |
| Station | KIIS-FM (`KIISFM`) |
| Source type | `iheart` (station_id 2501) |
| Collector | `IHeartTopSongsCollector` |
| Cadence | Daily at **00:00 UTC** |
| Log pattern | `kiis_top_songs status=... plays=... no_tracks=...` |
| Post-enable flag | `--kiis_top` |

**Why fourth:** iHeart API, daily cron — very low traffic. First run will be at the next midnight UTC after enablement.

### Checklist
- [ ] iHeart recently-played (Step 3) stable for 24 hours
- [ ] VAL-IHEART-TOP-001 PASS confirmed
- [ ] `ENABLE_IHEART_TOP_SONGS=true` set in `.env.production`
- [ ] Container force-recreated
- [ ] `val-post-enable.sh --kiis_top` after next midnight UTC → SUMMARY: 0 failed
- [ ] Top-songs play events visible in admin UI for KIIS-FM
- [ ] Waiting 24 hours (first confirmed run)

---

## Step 5 — KIIS-FM 102.7 Radiowave (`ENABLE_KIIS_RADIOWAVE_COLLECTOR`)

**Prerequisite VAL codes:** VAL-KIIS-RAD-001 PASS

| Item | Detail |
|------|--------|
| Flag | `ENABLE_KIIS_RADIOWAVE_COLLECTOR=true` |
| Station | KIIS-FM 102.7 Los Angeles (`KIIS1027`) |
| Source type | `radiowave` (IDDS=5080) |
| Collector | `KIISRadiowaveCollector` |
| Cadence | Daily at **09:00 UTC** (01:00 AM Pacific) |
| Log pattern | `kiis1027_radiowave_collected date=... status=... plays=... no_tracks=...` |
| Post-enable flag | `--kiis1027_radiowave` |

**Why fifth:** Daily Radiowave diary — same parser as Nova (proven). Very low traffic. First confirmed run is the day after enablement at 09:00 UTC.

**Note:** The post-enable check window is 24 hours. Run `val-post-enable.sh --kiis1027_radiowave` the following morning (after 09:00 UTC) to confirm the first diary run.

### Checklist
- [ ] iHeart recently-played (Step 3) and KIIS top songs (Step 4) stable
- [ ] VAL-KIIS-RAD-001 PASS confirmed
- [ ] `ENABLE_KIIS_RADIOWAVE_COLLECTOR=true` set in `.env.production`
- [ ] Container force-recreated
- [ ] Waited until 09:00 UTC the following day for first diary run
- [ ] `val-post-enable.sh --kiis1027_radiowave` → SUMMARY: 0 failed
- [ ] Play events visible in admin UI for KIIS-FM 102.7
- [ ] Waiting 24 hours (from first confirmed run)

---

## Step 6 — Heart FM (`ENABLE_HEART_COLLECTOR`)

**Prerequisite VAL codes:** VAL-HEARTFM-002 PASS

| Item | Detail |
|------|--------|
| Flag | `ENABLE_HEART_COLLECTOR=true` |
| Station | Heart FM UK (`HEARTFMUK`) |
| Source type | `heart_last_played` |
| Collector | `HeartRadioCollector` |
| Cadence | Every 5 minutes |
| Log pattern | `heart_fm_collected status=... plays=... no_tracks=...` |
| Post-enable flag | `--heart` |

**Risk note:** CSS scraper — higher maintenance risk than API-based collectors. If `div.station-song-history` selector drifts, the collector fails with `SCHEMA_CHANGED`. Monitor logs more closely for the first 48 hours.

### Checklist
- [ ] KIIS1027 radiowave (Step 5) stable (at least one confirmed daily run)
- [ ] VAL-HEARTFM-002 PASS confirmed
- [ ] `ENABLE_HEART_COLLECTOR=true` set in `.env.production`
- [ ] Container force-recreated
- [ ] Waited 15 minutes
- [ ] `val-post-enable.sh --heart` → SUMMARY: 0 failed
- [ ] Play events visible in admin UI for Heart FM UK
- [ ] Monitoring logs for selector drift (48-hour watch)
- [ ] Waiting 24 hours

---

## Step 7 — BBC Radio 1 (`ENABLE_BBC_RADIO1_COLLECTOR`)

**Prerequisite VAL codes:** VAL-BBC1-001 PASS **and** VAL-BBC1-006 PASS (manual ToS)

| Item | Detail |
|------|--------|
| Flag | `ENABLE_BBC_RADIO1_COLLECTOR=true` |
| Station | BBC Radio 1 (`BBCRADIO1`) |
| Source type | `bbc_sounds` |
| Collector | `BBCRadio1Collector` |
| Cadence | Every 5 minutes |
| Log pattern | `bbc_radio1_collected status=... plays=... no_tracks=...` |
| Post-enable flag | `--bbc` |

**Risk note:** VAL-BBC1-006 (ToS review) must be completed manually before this step. Do not enable BBC Radio 1 collector without confirming that automated access to `rms.api.bbc.co.uk` is permissible under BBC Developer terms.

### VAL-BBC1-006 Manual Checklist
- [ ] BBC Developer terms reviewed at https://www.bbc.co.uk/developer
- [ ] BBC Sounds / RMS API terms reviewed
- [ ] Confirmed: automated polling of `rms.api.bbc.co.uk/v2/services/bbc_radio_one/segments/latest` at 5-minute intervals is permissible
- [ ] Finding documented (PASS/FAIL) in `docs/VALIDATION_REGISTER.md`

### Step 7 Enablement Checklist
- [ ] Heart FM (Step 6) stable for 24 hours
- [ ] VAL-BBC1-001 PASS confirmed
- [ ] VAL-BBC1-006 PASS confirmed (manual)
- [ ] `ENABLE_BBC_RADIO1_COLLECTOR=true` set in `.env.production`
- [ ] Container force-recreated
- [ ] Waited 15 minutes
- [ ] `val-post-enable.sh --bbc` → SUMMARY: 0 failed
- [ ] Play events visible in admin UI for BBC Radio 1
- [ ] Waiting 24 hours

---

## Post-Enablement Log Commands (reference)

```bash
# Live log tail for a specific collector
ssh root@178.105.238.18 "docker compose -f /opt/rmias/docker-compose.hetzner.yml logs -f app" \
  | grep -i "z100_now_playing\|wksc_now_playing\|iheart_recently_played_collected\|kiis_top_songs\|heart_fm_collected\|bbc_radio1_collected"

# Check for failures in last 50 lines
ssh root@178.105.238.18 "docker compose -f /opt/rmias/docker-compose.hetzner.yml logs --tail=50 app" \
  | grep -iE "FAILED|ERROR|CRITICAL|Traceback"
```

---

## Rollback Procedure

If a collector runs but produces only FAILED status for >30 minutes:

1. Set the flag back to `false` in `.env.production`
2. Force-recreate: `docker compose ... up -d --force-recreate app`
3. Confirm the collector is no longer running (`val-post-enable.sh --<flag>` should show flag=false)
4. Investigate the failure — check raw payloads at `/data/raw_payloads/` inside the container
5. Do not re-enable until root cause is identified and fixed

```bash
# Inspect raw payloads for a collector
docker compose -f /opt/rmias/docker-compose.hetzner.yml exec app \
  ls -lt /data/raw_payloads/ | head -20
```
