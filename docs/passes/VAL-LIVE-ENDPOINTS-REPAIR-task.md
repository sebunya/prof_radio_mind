# VAL-LIVE-ENDPOINTS-REPAIR — Task Checklist

**Date:** 2026-06-05  
**Plan doc:** docs/passes/VAL-LIVE-ENDPOINTS-REPAIR-PLAN.md  
**Status:** BLOCKED — diagnostics must run before any code changes  

---

## Constraints (never violate)

- [ ] Do not enable collectors, scheduler, or any `ENABLE_*` flag
- [ ] Do not modify `.env.production`
- [ ] Do not write DB records
- [ ] Do not add scraping / User-Agent evasion logic
- [ ] Do not push fixes to `claude/sweet-archimedes-DFSWo` — create a new branch off `main`
- [ ] Do not commit any fix until the corresponding diagnostic confirms the root cause

---

## Phase 1 — Diagnostics (all read-only, run on production server)

### D1: iHeart baseline check (§1a)

Run the 4-URL probe to determine if KIISFM/2501 still responds:

```bash
ssh -o IdentitiesOnly=yes -i ~/.ssh/id_ed25519 root@178.105.238.18 'bash -s' -- <<'EOF'
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
EOF
```

- [ ] D1 run — result recorded
- [ ] Outcome: `2501/currentTrack` HTTP status = ______
- [ ] Outcome: `614/currentTrack` HTTP status = ______
- [ ] Outcome: `821/currentTrack` HTTP status = ______

**Decision gate:**
- If 2501 = 200/204 AND 614/821 = 404 → station IDs wrong → run D2
- If 2501 = 404 → geo-block or API deprecation → run D3 (auth probe)
- If all return 200/204 → transient failure; re-run VAL-LIVE-ENDPOINTS

---

### D2: iHeart station ID lookup via search API (§1a — only if D1 shows 2501 healthy)

```bash
ssh -o IdentitiesOnly=yes -i ~/.ssh/id_ed25519 root@178.105.238.18 'bash -s' -- <<'EOF'
docker compose -f /opt/rmias/docker-compose.hetzner.yml --env-file /opt/rmias/.env.production \
  exec -T app python3 -c "
import asyncio, json
from app.infrastructure.http.client import build_client

async def lookup():
    async with await build_client(timeout=15.0) as c:
        for call_sign in ['WHTZ', 'WKSC']:
            url = f'https://us.api.iheart.com/api/v2/content/liveStations?callLetters={call_sign}&limit=5'
            r = await c.get(url)
            print(f'=== {call_sign} HTTP {r.status_code} ===')
            if r.status_code == 200:
                try:
                    data = json.loads(r.content)
                    hits = data.get('hits', {}).get('hits', []) or data.get('stations', []) or []
                    for h in hits[:3]:
                        print(f'  id={h.get(\"id\")} name={h.get(\"name\")} streams={list((h.get(\"streams\") or {}).items())[:2]}')
                except Exception as e:
                    print(f'  parse error: {e}')
                    print(f'  raw: {r.content[:200]}')
            else:
                print(f'  body: {r.content[:150].decode(\"utf-8\", errors=\"replace\")}')

asyncio.run(lookup())
"
EOF
```

- [ ] D2 run — result recorded
- [ ] WHTZ (Z100) correct live-meta stream ID = ______  (currently assumed: 614)
- [ ] WKSC correct live-meta stream ID = ______  (currently assumed: 821)

---

### D3: iHeart sub-path discovery (§1b — always run regardless of D1 outcome)

```bash
ssh -o IdentitiesOnly=yes -i ~/.ssh/id_ed25519 root@178.105.238.18 'bash -s' -- <<'EOF'
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
            print(f'{path or \"/\":<22} HTTP {r.status_code}  keys={keys}')

asyncio.run(probe())
"
EOF
```

- [ ] D3 run — result recorded
- [ ] `/topSongs` HTTP status = ______
- [ ] `/recentlyPlayed` HTTP status = ______
- [ ] Alternative sub-path returning 200 = ______  (if any)
- [ ] Base `/` HTTP status and top-level keys = ______

---

### D4: Heart FM HTML structure inspection (§2)

```bash
ssh -o IdentitiesOnly=yes -i ~/.ssh/id_ed25519 root@178.105.238.18 'bash -s' -- <<'EOF'
docker compose -f /opt/rmias/docker-compose.hetzner.yml --env-file /opt/rmias/.env.production \
  exec -T app python3 -c "
import asyncio, json, re
from app.infrastructure.http.client import build_client

async def inspect():
    url = 'https://www.heart.co.uk/radio/last-played-songs/'
    async with await build_client(timeout=20.0) as c:
        r = await c.get(url)
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(r.content, 'lxml')
    nd = soup.select_one('#__NEXT_DATA__')
    print('Has __NEXT_DATA__:', nd is not None)
    if nd:
        try:
            data = json.loads(nd.string or '')
            print('__NEXT_DATA__ keys:', list(data.keys()))
            pp = data.get('props', {}).get('pageProps', {})
            print('pageProps keys:', list(pp.keys())[:10])
            for k, v in pp.items():
                if isinstance(v, (list, dict)):
                    print(f'  pageProps.{k} type={type(v).__name__} len={len(v) if isinstance(v, list) else len(v)}')
        except Exception as e:
            print('parse error:', e)
    api_refs = list(set(re.findall(r'[\"\'](/api[^\"\']{1,80})', r.text)))
    print('Embedded /api refs:', api_refs[:10])
    divs_with_class = soup.select('div[class]')
    song_classes = [d.get('class') for d in divs_with_class
                    if any('song' in c or 'track' in c or 'played' in c or 'history' in c
                           for c in d.get('class', []))]
    print('Song-like div classes:', song_classes[:5])
"
EOF
```

- [ ] D4 run — result recorded
- [ ] `__NEXT_DATA__` present: YES / NO
- [ ] If YES: `pageProps` keys that contain track/song data = ______
- [ ] Embedded `/api` refs found = ______
- [ ] Song-like div classes found = ______

---

### D4b: Heart FM API alternatives (§2 — only if D4 finds no song data in __NEXT_DATA__)

```bash
ssh -o IdentitiesOnly=yes -i ~/.ssh/id_ed25519 root@178.105.238.18 'bash -s' -- <<'EOF'
docker compose -f /opt/rmias/docker-compose.hetzner.yml --env-file /opt/rmias/.env.production \
  exec -T app python3 -c "
import asyncio
from app.infrastructure.http.client import build_client

async def probe():
    candidates = [
        'https://www.heart.co.uk/api/playlist',
        'https://www.heart.co.uk/api/now-playing',
        'https://www.heart.co.uk/radio/last-played-songs/data/',
        'https://music.heart.co.uk/api/recently-played',
        'https://www.heart.co.uk/api/songs/last-played',
    ]
    async with await build_client(timeout=10.0) as c:
        for url in candidates:
            try:
                r = await c.get(url)
                print(f'HTTP {r.status_code}: {url[:60]} | {r.content[:80].decode(\"utf-8\", errors=\"replace\")}')
            except Exception as e:
                print(f'ERROR: {url} | {e}')

asyncio.run(probe())
"
EOF
```

- [ ] D4b run — result recorded
- [ ] API endpoint returning 200 = ______  (if any)

---

### D5: Radiowave KIIS1027 IDDS verification (§3)

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
        # Check Nova for baseline (confirms selector works)
        for label, idds in [('NOVA969/11129', '11129'), ('KIIS1027/5080', '5080')]:
            for days_back in [1, 2, 3, 7]:
                d = (today - timedelta(days=days_back)).strftime('%Y-%m-%d')
                url = f'https://www.radiowavemonitor.com/pub_charts/diaries.aspx?IDDS={idds}&date={d}'
                r = await c.get(url)
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(r.content, 'lxml')
                rows = soup.select('tr.diary-row')
                title = soup.select_one('title')
                print(f'{label} date={d} HTTP={r.status_code} rows={len(rows)} title={title.get_text(strip=True)[:40] if title else \"?\"}')

asyncio.run(scan())
"
EOF
```

- [ ] D5 run — result recorded
- [ ] NOVA969 (11129) rows for yesterday = ______  (confirms selector works if >0)
- [ ] KIIS1027 (5080) rows across 7 days = all 0 / some non-zero
- [ ] KIIS1027 (5080) page title when IDDS=5080 queried = ______

**Decision gate:**
- Nova rows > 0 AND KIIS1027 always 0 → IDDS=5080 incorrect or station not tracked
- Nova rows = 0 AND KIIS1027 = 0 → Radiowave site issue or selector drift; re-run next day
- KIIS1027 title contains a different station name → completely wrong IDDS

---

## Phase 2 — Decision Table (fill after diagnostics)

| Provider | Diagnostic | Finding | Fix Required |
|---|---|---|---|
| iHeart baseline | D1 | | |
| Z100 station ID | D2 | | |
| WKSC station ID | D2 | | |
| iHeart topSongs path | D3 | | |
| iHeart recentlyPlayed path | D3 | | |
| Heart FM HTML | D4/D4b | | |
| Radiowave IDDS=5080 | D5 | | |

---

## Phase 3 — Code Fixes (only after Phase 2 complete)

### F1: iHeart station ID correction

- [ ] Create fix branch: `git checkout -b fix/iheart-station-ids main`
- [ ] Update `app/application/source_config/source_seeds.py` — `station_id` for WHTZ and WKSC
- [ ] Update `app/infrastructure/scheduler/scheduler.py` — `iheart_station_id` strings for Z100/WKSC jobs
- [ ] Update fixtures: `tests/fixtures/json/iheart_z100_200.json`, `iheart_wksc_200.json` (stationId fields)
- [ ] Update validation register: VAL-Z100-001 and VAL-WKSC-001 notes
- [ ] Update val-live-endpoints.sh: station IDs in check URLs
- [ ] Run tests: `python -m pytest --tb=short -q`
- [ ] Commit and push
- [ ] Re-run D1 equivalent on production after deploy

### F2: iHeart top-songs / recently-played endpoint correction

- [ ] Create fix branch (can merge with F1 if done concurrently)
- [ ] Identify correct endpoint from D3 findings
- [ ] Update `app/infrastructure/collectors/iheart_top_songs.py` — new URL
- [ ] Update `app/infrastructure/parsers/iheart.py` — new response key(s) if changed
- [ ] Update `app/infrastructure/collectors/iheart_recently_played.py` — new URL
- [ ] Update parser fallback keys if D3 reveals different JSON structure
- [ ] Update fixtures to match live response shape
- [ ] Run tests: `python -m pytest --tb=short -q`
- [ ] Update validation register and val-live-endpoints.sh
- [ ] Re-run VAL-IHEART-TOP-001 and VAL-IHEART-RECENT-001 on production after deploy

### F3: Heart FM parser fix

- [ ] Confirm from D4 whether `__NEXT_DATA__` contains track data or if an API endpoint was found
- [ ] If `__NEXT_DATA__`: rewrite `app/infrastructure/parsers/heart.py` to extract from JSON blob
- [ ] If API endpoint: update `app/infrastructure/collectors/heart_radio.py` + parser
- [ ] If neither: mark VAL-HEARTFM-002 BLOCKED — cannot collect without JS rendering
- [ ] Update fixture and tests
- [ ] Run tests and re-run VAL-HEARTFM-002 on production after deploy

### F4: Radiowave KIIS1027 IDDS correction

- [ ] If D5 finds the correct IDDS: update `app/application/source_config/source_seeds.py` (KIIS1027 config)
- [ ] Update `docs/VALIDATION_REGISTER.md` — VAL-KIIS-RAD-001 notes
- [ ] If Radiowave does not track US stations: mark KIIS1027 Radiowave source UNSUPPORTED and remove the collector from schedule
- [ ] If removing: update `app/core/settings.py` (remove flag), scheduler, admin.py, tests, .env.production.example
- [ ] Run tests and re-validate

---

## Phase 4 — Re-validation (after Phase 3 fixes deployed)

- [ ] Re-run `val-live-endpoints.sh` — all repaired checks
- [ ] Confirm SUMMARY: N passed, 0 failed for repaired providers
- [ ] Update `docs/VALIDATION_REGISTER.md` — mark each fixed VAL code as PASS
- [ ] Update `ENABLE-COLLECTORS-SEQUENCE-task.md` — remove/update steps for providers with changed order
- [ ] Re-confirm enablement order matches actual endpoint health

---

## BBC Radio 1 — Separate Track (no repair needed)

- [ ] Complete VAL-BBC1-006: BBC Developer Terms review at https://www.bbc.co.uk/developer
- [ ] Record PASS or FAIL in `docs/VALIDATION_REGISTER.md`
- [ ] If PASS: BBC Radio 1 can be enabled as Step 1 (no code changes needed)
- [ ] If FAIL: Disable `ENABLE_BBC_RADIO1_COLLECTOR` flag permanently; remove from enablement sequence
