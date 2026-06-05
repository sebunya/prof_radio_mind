# VAL-LIVE-ENDPOINTS-REPAIR-PLAN

**Date:** 2026-06-05  
**Trigger:** VAL-LIVE-ENDPOINTS run on production HEAD ab563d5 — 1 passed, 6 failed  
**Status:** REPAIR-PLAN READY — NO CODE CHANGES YET  
**Branch required for fixes:** new branch off `main` (do not modify `claude/sweet-archimedes-DFSWo`)

---

## Summary

BBC Radio 1 endpoint passed. All five remaining live-endpoint checks failed. The failures
fall into three independent failure categories:

| Category | Providers affected | Root cause tier |
|---|---|---|
| iHeart endpoint / ID problems | Z100, WKSC, top songs, recently-played | Unverified station IDs + assumed URL sub-paths |
| Heart FM selector drift | Heart FM UK | JS-rendered page — raw HTML never contains target selectors |
| Radiowave IDDS unknown | KIIS-FM 102.7 LA | IDDS=5080 was never verified; Radiowave may not track US stations |

No code changes are made in this document. Every recommended action below is either a
read-only diagnostic command or a docs update. Code fixes proceed only after diagnostics
confirm the exact root cause for each provider.

---

## 1. iHeart: Four Failures, Two Distinct Problems

### 1a. Wrong / unverified station IDs (Z100 = 614, WKSC = 821)

**Failure reported:**
```
VAL-Z100-001: https://api.iheart.com/api/v3/live-meta/stream/614/currentTrack → 404 / no_currentTrack_field
VAL-WKSC-001: https://api.iheart.com/api/v3/live-meta/stream/821/currentTrack → 404 / no_currentTrack_field
```

**Source of these IDs:**  
`app/application/source_config/source_seeds.py` lines 154 and 174. Both carry the comment:
> *"confirmed in fixture; not validated against live API"*

The station IDs 614 and 821 were set during EXTRACT-2 implementation and tested only against
synthetic JSON fixtures. They were never verified against the live iHeart API.

**Why 404, not 204?**  
The iHeart `/currentTrack` endpoint returns:
- `HTTP 200 + JSON` — track currently playing
- `HTTP 204` — station is live but no track metadata available
- `HTTP 404` — station ID does not exist in iHeart's live-meta stream registry

A 404 (not 204) response means the iHeart stream registry has no entry for station IDs 614
or 821 under the `/api/v3/live-meta` API. This is consistent with wrong station IDs.

**Possible root causes, in order of likelihood:**

| # | Hypothesis | Evidence |
|---|---|---|
| 1 | Station IDs 614/821 are wrong for the live-meta API | Comment in source_seeds.py explicitly says "not validated against live API" |
| 2 | iHeart uses a different numeric ID scheme for the live-meta API vs its public-facing URL | iHeart has multiple ID namespaces (station ID ≠ stream ID ≠ content ID) |
| 3 | Geo-restriction from Hetzner Germany | US-centric stations; BBC (UK) passed while US stations fail |
| 4 | iHeart live-meta API discontinued or requires auth token | Affects all stations; unlikely given KIISFM 2501 unknown state |

**Critical unknown: does KIISFM (2501) still work?**  
The production VAL run did not test `2501/currentTrack`. The existing KIISFM collector uses
this endpoint. If `2501/currentTrack` now also returns 404, the problem is hypothesis 3 or 4.
If `2501/currentTrack` returns 200 or 204, the problem is hypothesis 1 or 2 for 614/821.

**Diagnosis command (run first, on production server):**
```bash
# Determine the baseline state of the existing KIISFM endpoint
docker compose -f /opt/rmias/docker-compose.hetzner.yml --env-file /opt/rmias/.env.production \
  exec -T app python3 -c "
import asyncio, json
from app.infrastructure.http.client import build_client

async def probe():
    urls = [
        ('KIISFM/2501/currentTrack', 'https://api.iheart.com/api/v3/live-meta/stream/2501/currentTrack'),
        ('Z100/614/currentTrack',    'https://api.iheart.com/api/v3/live-meta/stream/614/currentTrack'),
        ('WKSC/821/currentTrack',    'https://api.iheart.com/api/v3/live-meta/stream/821/currentTrack'),
        ('BASE/2501',                'https://api.iheart.com/api/v3/live-meta/stream/2501'),
    ]
    async with await build_client(timeout=15.0) as c:
        for label, url in urls:
            r = await c.get(url)
            body = r.content[:200].decode('utf-8', errors='replace')
            print(f'{label}: HTTP {r.status_code} | {body[:80]}')

asyncio.run(probe())
"
```

**Interpretation matrix:**

| 2501/currentTrack | 614 and 821/currentTrack | Diagnosis |
|---|---|---|
| 200 or 204 | 404 | Wrong station IDs for 614/821; iHeart API is fine |
| 404 | 404 | API change, geo-block, or auth required for all stations |
| 200 or 204 | 200 or 204 | Transient failure; re-run val-live-endpoints |

**If station IDs are wrong — discovery command (safe):**
```bash
# iHeart search API — find the live-meta stream IDs for Z100 and WKSC by call letters
docker compose -f /opt/rmias/docker-compose.hetzner.yml --env-file /opt/rmias/.env.production \
  exec -T app python3 -c "
import asyncio, json
from app.infrastructure.http.client import build_client

async def lookup():
    async with await build_client(timeout=15.0) as c:
        for call_sign in ['WHTZ', 'WKSC']:
            url = f'https://us.api.iheart.com/api/v2/content/liveStations?callLetters={call_sign}&limit=5'
            r = await c.get(url)
            print(f'=== {call_sign} (HTTP {r.status_code}) ===')
            if r.status_code == 200:
                data = json.loads(r.content)
                hits = data.get('hits', {}).get('hits', []) if 'hits' in data else data.get('stations', [])
                for h in hits[:3]:
                    print(f'  id={h.get(\"id\")} streamId={h.get(\"streams\",{}).get(\"shoutcast_stream\",\"\")} name={h.get(\"name\")}')
            else:
                print(f'  body: {r.content[:100]}')

asyncio.run(lookup())
"
```

---

### 1b. Non-existent sub-paths: `/topSongs` and `/recentlyPlayed`

**Failures reported:**
```
VAL-IHEART-TOP-001:    https://api.iheart.com/api/v3/live-meta/stream/2501/topSongs    → 404
VAL-IHEART-RECENT-001: https://api.iheart.com/api/v3/live-meta/stream/2501/recentlyPlayed → 404
```

**Critical observation:** Both failures use station 2501 (KIISFM), which is the verified base
station. The 404 is from the sub-path, not the station ID. This is strong evidence that
`/topSongs` and `/recentlyPlayed` do not exist as sub-paths of the iHeart live-meta v3 API.

**Source of these endpoint paths:**  
The paths were invented by pattern extension from `/currentTrack` during EXTRACT-1 parser
design. They appear only in collector docstrings and the EXTRACT plan documents — they were
never verified against a live API response or documented API spec.

**Diagnosis command:**
```bash
# Probe the base stream resource and any sub-paths that return non-404
docker compose -f /opt/rmias/docker-compose.hetzner.yml --env-file /opt/rmias/.env.production \
  exec -T app python3 -c "
import asyncio, json
from app.infrastructure.http.client import build_client

async def probe():
    base = 'https://api.iheart.com/api/v3/live-meta/stream/2501'
    sub_paths = ['', '/currentTrack', '/topSongs', '/recentlyPlayed',
                 '/history', '/playlist', '/songs', '/nowPlaying']
    async with await build_client(timeout=15.0) as c:
        for path in sub_paths:
            url = base + path
            r = await c.get(url)
            keys = ''
            if r.status_code == 200:
                try:
                    keys = str(list(json.loads(r.content).keys()))[:80]
                except Exception:
                    keys = r.content[:60].decode('utf-8', errors='replace')
            print(f'{path or \"/\":<20} HTTP {r.status_code}  keys={keys}')

asyncio.run(probe())
"
```

**Expected outcomes:**
- If `/topSongs` and `/recentlyPlayed` remain 404 but `/currentTrack` returns 200/204: the sub-paths
  genuinely do not exist. The collectors require a different API endpoint to be discovered.
- If the base path `/` returns JSON with a list of available sub-resources: use that to identify
  valid alternatives.

**Note on geo-blocking for top-songs/recently-played:**  
Even if geo-blocking is in effect, the fact that KIISFM (an Australian station) also returns 404
for `/topSongs` and `/recentlyPlayed` means the sub-paths themselves do not exist for that station,
regardless of geography. This rules out geo-blocking as the sole cause for these two failures.

---

## 2. Heart FM UK: Selector Drift (Likely JS Rendering)

**Failure reported:**
```
VAL-HEARTFM-002: https://www.heart.co.uk/radio/last-played-songs/ → HTTP 200 but div.station-song-history MISSING
```

**Page characteristics:**  
Heart FM UK (`heart.co.uk`) is operated by Global Radio, which runs a Next.js / React-based
web platform. Modern Global Radio station pages render their content via client-side JavaScript.
A raw HTTP GET retrieves a bare HTML shell; the actual song history is injected into the DOM
by JavaScript after page load.

**What the raw HTML response likely contains:**
- A `<script id="__NEXT_DATA__">` block with a JSON payload (Next.js SSR/ISR data)
- References to a CDN-hosted React bundle
- Placeholder `<div>` elements with no song content

The CSS class `div.station-song-history` in the parser fixture was likely either:
1. Present in an older version of the page (pre-Next.js redesign)
2. Only present in the JS-rendered DOM (never in raw HTML)

**Diagnosis command:**
```bash
# Inspect the raw HTML for JS rendering indicators and any song-related structure
docker compose -f /opt/rmias/docker-compose.hetzner.yml --env-file /opt/rmias/.env.production \
  exec -T app python3 -c "
import asyncio
from app.infrastructure.http.client import build_client

async def inspect():
    url = 'https://www.heart.co.uk/radio/last-played-songs/'
    async with await build_client(timeout=20.0) as c:
        r = await c.get(url)
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(r.content, 'lxml')

    # Next.js SSR data blob
    next_data = soup.select_one('#__NEXT_DATA__')
    print('Has __NEXT_DATA__:', next_data is not None)
    if next_data:
        import json
        try:
            nd = json.loads(next_data.string or '')
            # Print top-level keys of the SSR payload
            print('__NEXT_DATA__ top keys:', list(nd.keys()))
            # Check for song data in props
            props = nd.get('props', {})
            page_props = props.get('pageProps', {})
            print('pageProps keys:', list(page_props.keys())[:10])
        except Exception as e:
            print('__NEXT_DATA__ parse error:', e)

    # Look for any API URLs embedded in the HTML
    import re
    api_refs = re.findall(r'[\"\'](/api[^\"\']{1,80})', r.text)
    print('Embedded /api refs:', list(set(api_refs))[:10])

    # Look for any song/track/history class patterns
    from bs4 import BeautifulSoup
    all_divs = soup.select('div[class]')
    song_classes = [d.get('class') for d in all_divs
                    if any('song' in c or 'track' in c or 'played' in c or 'history' in c
                           for c in d.get('class', []))]
    print('Divs with song/track/played/history classes:', song_classes[:10])

asyncio.run(inspect())
"
```

**Alternative API discovery command:**
```bash
# Check if Global Radio exposes a documented playlist API
docker compose -f /opt/rmias/docker-compose.hetzner.yml --env-file /opt/rmias/.env.production \
  exec -T app python3 -c "
import asyncio
from app.infrastructure.http.client import build_client

async def probe_apis():
    candidates = [
        'https://www.heart.co.uk/api/playlist',
        'https://www.heart.co.uk/api/now-playing',
        'https://www.heart.co.uk/radio/last-played-songs/data/',
        'https://www.heart.co.uk/_next/data/last-played-songs.json',
        'https://music.heart.co.uk/api/recently-played',
    ]
    async with await build_client(timeout=10.0) as c:
        for url in candidates:
            try:
                r = await c.get(url)
                print(f'HTTP {r.status_code}: {url} | {r.content[:80].decode(\"utf-8\", errors=\"replace\")}')
            except Exception as e:
                print(f'ERROR: {url} | {e}')

asyncio.run(probe_apis())
"
```

**Expected finding:** The raw HTML will contain `__NEXT_DATA__` with a JSON payload. If that
payload includes recently-played track data (which it may for SSR pages), the parser can be
updated to extract from the JSON blob instead of DOM selectors. If the JSON is empty (client-side
only), a different API endpoint must be found.

---

## 3. Radiowave KIIS1027: IDDS=5080 Unverified

**Failure reported:**
```
VAL-KIIS-RAD-001: https://www.radiowavemonitor.com/pub_charts/diaries.aspx?IDDS=5080&date=YESTERDAY → HTTP 200 but 0 tr.diary-row rows
```

**Background on Radiowave Monitor:**  
Radiowave Monitor (`radiowavemonitor.com`) is a service that archives radio play history.
Nova 96.9 Sydney uses IDDS=11129. IDDS=5080 for KIIS-FM 102.7 LA was assigned during EXTRACT-3
implementation. The source seed comment confirms:
> *"UNVALIDATED — VAL-KIIS-RAD-001 required before enable"*

**Critical geographic question:**  
Radiowave Monitor appears to be primarily an Australian radio monitoring service. Its known
diary entries (Nova 96.9, KIISFM AU) are all Australian stations. It is not established that
Radiowave Monitor tracks US stations at all. If KIIS-FM 102.7 LA (Los Angeles) is not in
Radiowave's coverage, IDDS=5080 either does not exist or belongs to a different station
entirely.

**Two distinct failure modes for "HTTP 200 but 0 rows":**

| Scenario | What the page looks like | Action |
|---|---|---|
| A: IDDS=5080 not in system | Generic "no data" placeholder or empty table structure | IDDS is wrong; find correct IDDS or accept no Radiowave coverage for LA |
| B: IDDS=5080 is KIIS1027 but yesterday has no entries | Station is tracked but diary not yet published | Retry with dates 2–7 days ago to check for historical data |
| C: IDDS=5080 is a different station | Page shows data but for a different station identity | Completely wrong IDDS; start over with discovery |

**Diagnosis commands:**
```bash
# 1. Check station identity: what does IDDS=5080 actually represent?
docker compose -f /opt/rmias/docker-compose.hetzner.yml --env-file /opt/rmias/.env.production \
  exec -T app python3 -c "
import asyncio
from app.infrastructure.http.client import build_client

async def identify():
    url = 'https://www.radiowavemonitor.com/pub_charts/diaries.aspx?IDDS=5080'
    async with await build_client(timeout=30.0) as c:
        r = await c.get(url)
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(r.content, 'lxml')
    title = soup.select_one('title')
    headers = soup.select('h1,h2,h3,th')
    station_els = soup.select('[class*=station],[class*=diary],[id*=station]')
    print('HTTP:', r.status_code)
    print('Title:', title.get_text(strip=True) if title else 'none')
    print('Headers:', [h.get_text(strip=True) for h in headers[:8]])
    print('Station els text:', [e.get_text(strip=True) for e in station_els[:5]])

asyncio.run(identify())
"

# 2. Try multiple prior dates to check if IDDS=5080 ever has data
docker compose -f /opt/rmias/docker-compose.hetzner.yml --env-file /opt/rmias/.env.production \
  exec -T app python3 -c "
import asyncio
from datetime import UTC, datetime, timedelta
from app.infrastructure.http.client import build_client

async def scan_dates():
    today = datetime.now(tz=UTC).date()
    async with await build_client(timeout=30.0) as c:
        for days_back in range(1, 8):
            d = (today - timedelta(days=days_back)).strftime('%Y-%m-%d')
            url = f'https://www.radiowavemonitor.com/pub_charts/diaries.aspx?IDDS=5080&date={d}'
            r = await c.get(url)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(r.content, 'lxml')
            rows = soup.select('tr.diary-row')
            print(f'  date={d} HTTP={r.status_code} rows={len(rows)}')

asyncio.run(scan_dates())
"

# 3. Compare against confirmed Nova IDDS to verify the page structure is the same
docker compose -f /opt/rmias/docker-compose.hetzner.yml --env-file /opt/rmias/.env.production \
  exec -T app python3 -c "
import asyncio
from datetime import UTC, datetime, timedelta
from app.infrastructure.http.client import build_client

async def compare():
    yesterday = (datetime.now(tz=UTC).date() - timedelta(days=1)).strftime('%Y-%m-%d')
    urls = [
        ('NOVA969/11129', f'https://www.radiowavemonitor.com/pub_charts/diaries.aspx?IDDS=11129&date={yesterday}'),
        ('KIIS1027/5080', f'https://www.radiowavemonitor.com/pub_charts/diaries.aspx?IDDS=5080&date={yesterday}'),
    ]
    async with await build_client(timeout=30.0) as c:
        for label, url in urls:
            r = await c.get(url)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(r.content, 'lxml')
            rows = soup.select('tr.diary-row')
            title = soup.select_one('title')
            print(f'{label}: HTTP {r.status_code} rows={len(rows)} title={title.get_text(strip=True) if title else \"?\"}')

asyncio.run(compare())
"
```

**Interpretation:**
- If IDDS=11129 (Nova) has rows but IDDS=5080 has none: IDDS=5080 is wrong or the station is not tracked
- If IDDS=11129 also has 0 rows: The Radiowave site may be down or the `tr.diary-row` selector has drifted
- If IDDS=5080 has rows but the title shows a non-KIIS station: completely wrong IDDS

---

## 4. BBC Radio 1: Endpoint Valid, Manually Blocked

**Status:** PASS on VAL-BBC1-001  
**Blocker:** VAL-BBC1-006 — BBC Terms of Service manual review not yet completed  

BBC Radio 1 is ready from an endpoint perspective. No repair needed. Enablement remains blocked
until VAL-BBC1-006 is completed.

**Required action (human):** Visit https://www.bbc.co.uk/developer, review BBC Sounds / RMS API
terms, confirm whether automated 5-minute polling of `rms.api.bbc.co.uk/v2/services/bbc_radio_one/segments/latest`
is permissible, and record the finding in `docs/VALIDATION_REGISTER.md`.

---

## 5. Go/No-Go Matrix

| Provider | VAL Code | Endpoint HTTP | Root Cause | Discovery Status | Go/No-Go |
|---|---|---|---|---|---|
| BBC Radio 1 | VAL-BBC1-001 | PASS | — | — | NO-GO (ToS pending) |
| Z100 (WHTZ) | VAL-Z100-001 | 404 | Station ID 614 unverified in live API | Run diagnosis §1a first | NO-GO |
| WKSC 103.5 | VAL-WKSC-001 | 404 | Station ID 821 unverified in live API | Run diagnosis §1a first | NO-GO |
| iHeart Top Songs | VAL-IHEART-TOP-001 | 404 | `/topSongs` sub-path likely does not exist | Run diagnosis §1b first | NO-GO |
| iHeart Recently-Played | VAL-IHEART-RECENT-001 | 404 | `/recentlyPlayed` sub-path likely does not exist | Run diagnosis §1b first | NO-GO |
| KIIS1027 Radiowave | VAL-KIIS-RAD-001 | 200 / 0 rows | IDDS=5080 unverified; US coverage uncertain | Run diagnosis §3 first | NO-GO |
| Heart FM UK | VAL-HEARTFM-002 | 200 / selector absent | JS-rendered page; raw HTML has no selectors | Run diagnosis §2 first | NO-GO |

**Overall verdict: REPAIR-PLAN READY — NO CODE CHANGES YET**

Every failure requires a diagnostic read before a fix can be written. Running the wrong fix
based on an incorrect hypothesis will waste a deploy cycle and could introduce new assumptions
that are equally untested.

---

## 6. Revised Enablement Order (after repairs)

The previous order was Z100 → WKSC → iHeart Recently-Played → Top Songs → KIIS1027 → Heart → BBC.
That order assumed all seven VAL checks would pass. Given the failures, the revised order depends
on which providers are fixable and in what order they can be re-validated:

| Step | Provider | Dependency | Notes |
|---|---|---|---|
| 0 | Run all diagnostic commands | None | Read-only; run immediately |
| 1 | BBC Radio 1 | VAL-BBC1-006 manual ToS review | Endpoint healthy; only ToS blocks it |
| 2 | Z100 / WKSC | Correct station IDs confirmed | iHeart currentTrack path is proven; just need right IDs |
| 3 | iHeart Recently-Played | Correct sub-path or alternative confirmed | Depends on §1b discovery outcome |
| 4 | iHeart Top Songs | Correct sub-path or alternative confirmed | Same — may need new API endpoint |
| 5 | KIIS1027 Radiowave | IDDS verified + ≥1 date with rows | IDDS may need changing OR source may need replacement |
| 6 | Heart FM UK | API endpoint or JS-data extraction confirmed | Likely requires parser rewrite |

BBC Radio 1 is the only collector that could be enabled after repair — once ToS is cleared,
no code change is needed for it.

---

## 7. Constraints Carried Forward

- Do not enable collectors or scheduler
- Do not modify `.env.production`
- Do not write DB records
- Do not add scraping or User-Agent evasion logic
- Do not commit fixes to this branch — use a new fix branch off `main`
- All diagnostic commands are read-only; they make no API calls that have side effects

---

## 8. Files That Will Need Changing (after diagnosis)

| File | Change needed | Trigger condition |
|---|---|---|
| `app/infrastructure/scheduler/scheduler.py` | Update `iheart_station_id` for Z100/WKSC | If diagnosis confirms wrong IDs |
| `app/application/source_config/source_seeds.py` | Update `station_id` config values | Same |
| `app/infrastructure/collectors/iheart_top_songs.py` | New endpoint URL | If `/topSongs` confirmed absent |
| `app/infrastructure/parsers/iheart.py` | New response key mapping | Follows from endpoint change |
| `app/infrastructure/collectors/iheart_recently_played.py` | New endpoint URL | If `/recentlyPlayed` confirmed absent |
| `app/infrastructure/parsers/heart.py` | JSON extraction from `__NEXT_DATA__` or new API | If JS-rendered confirmed |
| `app/infrastructure/collectors/heart_radio.py` | New base URL | Follows from parser change |
| `app/application/source_config/source_seeds.py` (KIIS1027) | New IDDS value | If 5080 confirmed wrong |
| `docs/VALIDATION_REGISTER.md` | Mark VAL codes FAIL / update station IDs | After each diagnosis |
| `docs/passes/val-live-endpoints.sh` | Update station IDs in check commands | After IDs corrected |
| `tests/fixtures/json/iheart_z100_200.json` etc. | Update station IDs | After IDs confirmed |
