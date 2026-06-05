# RADIO-COVERAGE-ARCH-1 — Task Checklist

**Date:** 2026-06-05  
**Plan doc:** docs/passes/RADIO-COVERAGE-ARCH-1-plan.md  
**Status:** Plan complete. Awaiting first implementation pass approval.  
**Verdict:** RADIO-COVERAGE-ARCH-1 READY — PLAN ONLY

---

## Constraints (never violate in any pass that follows)

- [ ] Do not enable collectors or scheduler
- [ ] Do not modify `.env.production`
- [ ] Do not write DB records during diagnostics or planning
- [ ] Do not add scraping / User-Agent evasion logic
- [ ] Do not rotate IPs or proxies to avoid restrictions
- [ ] Do not use headless browser / Playwright for JS rendering
- [ ] Do not access authenticated, geo-restricted, or login-gated content
- [ ] Do not store audio bytes in any form
- [ ] Do not use Spotify or MusicBrainz as radio capture sources
- [ ] Do not guess or patch endpoints without validation proof

---

## Phase 1 — Diagnostics (complete these before starting any implementation pass)

### D6: Correct Radiowave Nova diagnostic (repair plan error)

The original D5 diagnostic tested IDDS=11129 against `radiowavemonitor.com`, but the Nova
collector actually uses `radiowave.com.au/diary`. Run the correct URL:

```bash
ssh -o IdentitiesOnly=yes -i ~/.ssh/id_ed25519 root@178.105.238.18 'bash -s' -- <<'EOF'
docker compose -f /opt/rmias/docker-compose.hetzner.yml --env-file /opt/rmias/.env.production \
  exec -T app python3 -c "
import asyncio
from datetime import UTC, datetime, timedelta
from app.infrastructure.http.client import build_client

async def scan():
    today = datetime.now(tz=UTC).date()
    async with await build_client(timeout=30.0) as c:
        # Nova actual URL (radiowave.com.au)
        for days_back in [1, 2, 3]:
            d = (today - timedelta(days=days_back)).strftime('%Y-%m-%d')
            url = f'https://www.radiowave.com.au/diary?idds=11129&date={d}'
            r = await c.get(url)
            from bs4 import BeautifulSoup
            rows = BeautifulSoup(r.content, 'lxml').select('tr.diary-row')
            print(f'radiowave.com.au IDDS=11129 date={d} HTTP={r.status_code} rows={len(rows)}')
        # KIIS actual URL (radiowavemonitor.com)
        for days_back in [1, 2, 3]:
            d = (today - timedelta(days=days_back)).strftime('%Y-%m-%d')
            url = f'https://www.radiowavemonitor.com/pub_charts/diaries.aspx?IDDS=5080&date={d}'
            r = await c.get(url)
            from bs4 import BeautifulSoup
            rows = BeautifulSoup(r.content, 'lxml').select('tr.diary-row')
            print(f'radiowavemonitor.com IDDS=5080 date={d} HTTP={r.status_code} rows={len(rows)}')

asyncio.run(scan())
"
EOF
```

- [ ] D6 run — results recorded
- [ ] radiowave.com.au NOVA rows for last 3 days: ______
- [ ] radiowavemonitor.com KIIS1027 rows for last 3 days: ______

**Decision gate:**
- If radiowave.com.au returns rows → Nova collector is fine; KIIS1027 domain is a separate issue
- If radiowave.com.au also returns 0 rows → `tr.diary-row` selector has drifted across both services
- radiowavemonitor.com 0 rows → KIIS1027 needs IDDS re-discovery OR service doesn't track US stations

---

### D7: Heart FM robots.txt check

```bash
ssh -o IdentitiesOnly=yes -i ~/.ssh/id_ed25519 root@178.105.238.18 'bash -s' -- <<'EOF'
docker compose -f /opt/rmias/docker-compose.hetzner.yml --env-file /opt/rmias/.env.production \
  exec -T app python3 -c "
import asyncio
from app.infrastructure.http.client import build_client

async def check():
    async with await build_client(timeout=10.0) as c:
        for url in [
            'https://www.heart.co.uk/robots.txt',
            'https://www.radiowave.com.au/robots.txt',
            'https://www.radiowavemonitor.com/robots.txt',
            'https://onlineradiobox.com/robots.txt',
        ]:
            r = await c.get(url)
            relevant = [l for l in r.text.splitlines() if 'Disallow' in l or 'User-agent' in l][:10]
            print(f'=== {url} HTTP {r.status_code} ===')
            for line in relevant:
                print(f'  {line}')

asyncio.run(check())
"
EOF
```

- [ ] D7 run — robots.txt results recorded
- [ ] heart.co.uk: disallow for `/radio/last-played-songs/`? YES / NO
- [ ] radiowave.com.au: general disallow? YES / NO
- [ ] radiowavemonitor.com: general disallow? YES / NO
- [ ] onlineradiobox.com: general disallow? YES / NO

**Decision gate:** If a domain disallows the target path → mark compliance_status=BLOCKED for that source.

---

### D8: Stream URL discovery probe (5-station baseline)

Read-only: check if the five highest-priority stations have discoverable ICY streams.
This is manual discovery assistance only; no streaming connection is made here.

For each station, the human operator should:
1. Visit the station website and look for "Listen live" or streaming link
2. Inspect browser Network tab for stream requests (application/octet-stream or audio/*)
3. Or use publicly documented stream directories (TuneIn, Radio Garden)

Known starting points:
```
BBC Radio 1:     http://stream.live.vc.bbcmedia.co.uk/bbc_radio_one  (documented publicly)
Nova 96.9 AU:    TuneIn or nova.com.au — find m3u/pls link
KIISFM AU:       iHeartRadio.com.au — find stream URL
Z100 NY:         iHeartRadio.com (US) or TuneIn
WKSC Chicago:    iHeartRadio.com (US) or TuneIn
Heart FM UK:     TuneIn or heart.co.uk
```

- [ ] D8: Stream URLs recorded for ≥1 station (to bootstrap STREAM-METADATA-DISCOVERY-1)
- [ ] BBC Radio 1 stream URL: ______
- [ ] Nova 96.9 stream URL: ______
- [ ] KIISFM AU stream URL: ______
- [ ] Z100 stream URL: ______
- [ ] Heart FM UK stream URL: ______

---

## Phase 2 — Plan Approval Gates

- [ ] RADIO-COVERAGE-ARCH-1-plan.md reviewed and approved
- [ ] STATION-COVERAGE-MATRIX.md reviewed; per-station gaps understood
- [ ] SOURCE-CAPABILITY-MODEL.md reviewed; data schema approved
- [ ] AUDIO-FINGERPRINTING-OPTIONS.md reviewed; Tier 4 approach approved in principle
- [ ] COMPLIANCE-AND-RETENTION-GUARDRAILS.md reviewed; all anti-patterns acknowledged

---

## Phase 3 — Implementation Pass Approvals (one at a time)

### PASS 1: STREAM-METADATA-DISCOVERY-1

**Purpose:** Confirm ICY stream metadata works for ≥1 station using the existing
`streamtheworld_icy.py` collector in a read-only, no-storage dry-run mode.

**Prerequisites:**
- [ ] D8 completed (at least one stream URL found)
- [ ] robots.txt and ToS for stream use: no explicit prohibition found
- [ ] This pass approved

**Deliverables:**
- [ ] VAL-STW-* entries created for each tested station
- [ ] Stream URL per station documented in STATION-COVERAGE-MATRIX.md
- [ ] ICY StreamTitle format confirmed (e.g., "Artist - Title", "Title\nArtist", etc.)
- [ ] No audio stored — confirmed
- [ ] Test results documented

---

### PASS 2: HEART-HTML-PARSER-FIX-1

**Purpose:** Capture a real heart.co.uk response, update parser selectors, update fixture.

**Prerequisites:**
- [ ] D7 robots.txt check: heart.co.uk does not disallow `/radio/last-played-songs/`
- [ ] ToS review for heart.co.uk scraping: no prohibition found
- [ ] This pass approved

**Scope:**
- Update `app/infrastructure/parsers/heart.py` with new selectors
- Update `tests/fixtures/html/heart_fm_last_played.html` from a real capture
- Update parser unit tests
- Re-run VAL-HEARTFM-002
- Do not enable collector until VAL-HEARTFM-002 passes

**Deliverables:**
- [ ] New selectors confirmed from live response capture
- [ ] Fixture updated
- [ ] Tests pass
- [ ] VAL-HEARTFM-002 PASS recorded in VALIDATION_REGISTER.md
- [ ] compliance_status set for HEARTFMUK source

---

### PASS 3: RADIOWAVE-REVALIDATION-1

**Purpose:** Confirm correct URLs, correct IDDS values, current selector status.

**Prerequisites:**
- [ ] D6 completed
- [ ] D7 robots.txt checks for both Radiowave domains complete

**Scope (depends on D6 outcome):**
- If radiowave.com.au selector drifted: update `radiowave.py`, update fixtures
- If KIIS1027 IDDS=5080 invalid: discover correct IDDS or mark source DISABLED
- Update VALIDATION_REGISTER.md entries for VAL-NOVA-001 through VAL-NOVA-004
- Update VAL-KIIS-RAD-001 status
- Update the D5 diagnostic in VAL-LIVE-ENDPOINTS-REPAIR-task.md to use correct URL

**Deliverables:**
- [ ] Nova Radiowave: confirmed working or FAILED
- [ ] KIIS1027 Radiowave: confirmed IDDS or marked UNSUPPORTED
- [ ] Fixtures updated if selector changed
- [ ] Tests pass

---

### PASS 4: BBC-TOS-REVIEW-1

**Purpose:** Human review of BBC Developer Terms. No code.

**Prerequisites:** None — can run in parallel with other passes

**Actions (human only):**
- [ ] Visit bbc.co.uk/developer
- [ ] Read BBC Sounds / RMS API terms
- [ ] Confirm: is 5-minute polling of `rms.api.bbc.co.uk/v2/services/bbc_radio_one/segments/latest` permitted?
- [ ] Record finding in docs/VALIDATION_REGISTER.md (VAL-BBC1-006)
- [ ] Set compliance_status = `approved` or `blocked` for BBCRADIO1 BBC_SOUNDS source

**If PASS:**
- [ ] Enable BBC Radio 1 collector (set ENABLE_BBC_RADIO1_COLLECTOR=true in .env.production)
- [ ] Run val-post-enable.sh --bbc

**If FAIL:**
- [ ] Mark VAL-BBC1-006 FAILED
- [ ] Mark compliance_status = `blocked`
- [ ] Remove BBC Radio 1 from enablement sequence
- [ ] Add T3 ICY stream as fallback in STATION-COVERAGE-MATRIX.md

---

### PASS 5: FINGERPRINTING-FEASIBILITY-1

**Purpose:** Research only. Evaluate ACRCloud and AudD terms and test APIs.

**Prerequisites:**
- [ ] STREAM-METADATA-DISCOVERY-1 complete (stream URLs needed for fingerprinting too)
- [ ] This pass approved

**Actions:**
- [ ] Review ACRCloud Broadcast Monitoring terms
- [ ] Review AudD terms for radio monitoring use case
- [ ] Test AudD free tier against one station (manual — not automated)
- [ ] Confirm: fingerprint-only transmission (no raw audio sent to API)?
- [ ] Document cost model for 8 stations, 24/7 monitoring
- [ ] Review legal risk for Hetzner Germany server (see COMPLIANCE-AND-RETENTION-GUARDRAILS.md §6)
- [ ] Produce go/no-go recommendation

**Deliverables:**
- [ ] FINGERPRINTING-FEASIBILITY-1 report document
- [ ] Provider recommendation (ACRCloud vs AudD vs defer)
- [ ] Legal review recommendation
- [ ] Cost estimate

---

### PASS 6: LICENSED-DATA-ASSESSMENT-1 (future)

**Purpose:** Evaluate whether a licensed data partnership (Luminate, Radio Monitor, BDS)
provides better economics and coverage than building and maintaining collectors.

**Prerequisites:** Passes 1–5 complete; collection results reviewed  
**Note:** This is a business decision as much as a technical one.

---

## Phase 4 — Revised Enablement Order (after repairs)

Replace the old 7-step order with this evidence-based sequence:

| Step | Collector | Prerequisite | Risk |
|---|---|---|---|
| 1 | BBC Radio 1 (`ENABLE_BBC_RADIO1_COLLECTOR`) | VAL-BBC1-006 PASS | Low — official API |
| 2 | Heart FM (`ENABLE_HEART_COLLECTOR`) | HEART-HTML-PARSER-FIX-1 + VAL-HEARTFM-002 PASS | Medium — HTML scraper |
| 3 | Nova 96.9 (`ENABLE_NOVA_COLLECTOR`) | RADIOWAVE-REVALIDATION-1 PASS | Medium — HTML scraper |
| 4 | ICY stream stations (Z100, WKSC, KIISFM, etc.) | STREAM-METADATA-DISCOVERY-1 PASS per station | Low — stream metadata |
| 5 | KIIS1027 (`ENABLE_KIIS_RADIOWAVE_COLLECTOR`) | RADIOWAVE-REVALIDATION-1 PASS + correct IDDS | Medium |
| 6 | KIIS top songs / recently-played | New endpoint found + validated | Medium–high |
| 7 | Audio fingerprinting | FINGERPRINTING-FEASIBILITY-1 PASS + legal review | High |

**Do not follow the old order blindly.** The old order assumed all VAL checks passed.
They did not. Enable only what is validated.

---

## Linked Documents

- `docs/passes/RADIO-COVERAGE-ARCH-1-plan.md` — master architecture plan
- `docs/passes/STATION-COVERAGE-MATRIX.md` — per-station source inventory
- `docs/passes/SOURCE-CAPABILITY-MODEL.md` — source schema and lifecycle
- `docs/passes/AUDIO-FINGERPRINTING-OPTIONS.md` — T4 feasibility
- `docs/passes/COMPLIANCE-AND-RETENTION-GUARDRAILS.md` — legal and retention policy
- `docs/passes/VAL-LIVE-ENDPOINTS-REPAIR-PLAN.md` — per-provider diagnosis
- `docs/passes/VAL-LIVE-ENDPOINTS-REPAIR-task.md` — repair diagnostics
- `docs/VALIDATION_REGISTER.md` — all VAL codes
