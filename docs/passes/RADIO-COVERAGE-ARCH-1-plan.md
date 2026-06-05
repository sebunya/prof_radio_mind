# RADIO-COVERAGE-ARCH-1 — Resilient Radio Capture Architecture

**Date:** 2026-06-05  
**Status:** PLAN ONLY — no code changes in this pass  
**Scope:** Architecture, source strategy, station coverage, compliance framework  
**Verdict:** RADIO-COVERAGE-ARCH-1 READY — PLAN ONLY

---

## 1. Context: Why Endpoint-Only Collection Is Fragile

The current system is built as one collector per source endpoint. Each collector is a
direct point-to-point dependency on a single external resource. When that resource changes —
API deprecation, HTML restructure, IDDS reassignment, geo-block — collection silently
stops or hard-fails. There is no fallback.

The production VAL-LIVE-ENDPOINTS run confirmed this structural weakness:

| Provider | Failure mode | Immediate cause |
|---|---|---|
| iHeart v3 live-meta | 404 across all sub-paths, all stations | API endpoint gone; no fallback |
| Heart FM CSS selectors | Container missing from raw HTML | Site redesign; no fallback |
| Radiowave KIIS1027 | HTTP 200 but 0 rows | IDDS unverified; no fallback |
| iHeart top songs | 404 | Sub-path assumed but never existed |
| iHeart recently-played | 404 | Sub-path assumed but never existed |

BBC Radio 1 passed, but it too is a single-source dependency, blocked by a manual ToS review.

The Nova Radiowave diagnostic also revealed a silent error in the repair plan: the D5
diagnostic tested `radiowavemonitor.com/IDDS=11129`, but the Nova collector's actual URL
is `radiowave.com.au/diary?idds=11129`. Two different domains. The 0-rows result for
the "Nova baseline" is meaningless — the wrong service was probed.

**Root cause of all failures:** Every source was an unvalidated assumption. Station IDs came
from synthetic fixtures. CSS selectors came from a snapshot. Sub-paths were invented by
URL-pattern extension. No live verification occurred before code was written.

**Structural fix:** Replace single-dependency collectors with a tiered, multi-source
architecture where each station has at least two independent observation paths, health is
monitored per source, and failures are classified and handled automatically.

---

## 2. Architecture Overview: Six Source Tiers

```
STATION
  │
  ├── T1: Official / Permissioned Broadcaster APIs
  │       BBC RMS, direct broadcaster APIs, approved partner integrations
  │
  ├── T2: Public Web Metadata
  │       Now-playing pages, last-played pages — only raw HTML or embedded JSON
  │       No JS rendering, no auth bypass, no evasion
  │
  ├── T3: Stream Metadata (ICY / HLS timed metadata)
  │       Public broadcast streams carry track metadata in-band
  │       Already partially implemented (streamtheworld_icy.py — deferred)
  │       Do NOT store audio
  │
  ├── T4: Audio Fingerprinting (future)
  │       Short sample → fingerprint → identify → discard sample
  │       Legal only where permissioned or clearly lawful
  │       Commercial API required (ACRCloud, AudD)
  │
  ├── T5: Licensed Third-Party Monitoring Data (future)
  │       Radio Monitor, BDS, MediaMonitors, Luminate, etc.
  │       Coverage, rights, cost, and terms evaluated before integration
  │
  └── T6: Metadata Enrichment Only (NOT capture sources)
          MusicBrainz: canonical identity, MBIDs, ISRCs, aliases
          Spotify: catalogue context, artwork, popularity, external links
          Neither proves a song was played on radio
```

### Tier characteristics

| Tier | Latency | Reliability | Legal clarity | Implementation cost |
|---|---|---|---|---|
| T1: Official API | Low | High (SLA) | Highest — requires permission or ToS review | Low once approved |
| T2: Web metadata | Low–medium | Medium — selector drift risk | Medium — public page, must check ToS | Medium — needs maintenance |
| T3: Stream metadata | Very low | High — metadata in-band with broadcast | High — receiving public broadcast | Low — collector exists |
| T4: Audio fingerprint | Low (API call) | High (commercial service) | Medium — short sample, API terms needed | Medium — vendor integration |
| T5: Licensed data | Hours–days | Very high | Highest — licensed contract | High — cost + integration |
| T6: Enrichment | Async | High | Defined by existing approval | Low — already integrated |

---

## 3. What Already Exists (and Is Deferred)

The system already contains stream metadata infrastructure that was never activated:

**`app/infrastructure/collectors/streamtheworld_icy.py`**  
— Reads ICY `StreamTitle` from public HTTP audio streams  
— Max 64 KB read, then disconnects (does not store audio)  
— Header: `{"Icy-MetaData": "1"}` to request inline metadata  
— Parses `StreamTitle='Artist - Title'`  
— Status: `DEFERRED — VAL-STW-001 required (stream URL + ICY format confirmation)`

This collector is architecturally correct for Tier 3. It needs stream URLs, not code.
Discovery is the next step, not implementation.

---

## 4. Capture Resolver Design

The resolver is the core intelligence layer. It combines observations from multiple sources
into a single high-confidence play event.

### 4.1 Input: multi-source observation window

```
CaptureObservation:
  observed_at:       datetime (UTC)
  station_id:        UUID
  source_id:         UUID
  source_tier:       int (1–5)
  source_type:       SourceType
  raw_artist:        str
  raw_title:         str
  raw_metadata:      str | None   (StreamTitle or raw JSON)
  source_event_id:   str | None   (stable ID from provider)
  duration_seconds:  int | None
  confidence_raw:    float        (0.0–1.0, from source-specific signals)
```

### 4.2 Resolution logic

1. **Dedup gate**: If `source_event_id` matches an existing PlayEvent for this station
   within 24 hours → skip.
2. **Fingerprint gate**: If SHA-256 fingerprint of normalized(artist + title) matches
   within 30 minutes → skip.
3. **Conflict detection**: If two sources report different artists/titles within the same
   2-minute window, the higher-tier source wins. Log conflict.
4. **Confidence scoring**:
   - Source tier weight: T1=1.0, T2=0.8, T3=0.9, T4=0.7, T5=0.95
   - Cross-source agreement multiplier: +0.2 if two or more sources agree
   - Parse quality: penalize if artist or title is empty, contains only digits, or
     matches commercial-break patterns
5. **Attribution**: record which source produced the accepted event

### 4.3 Failure passthrough

If all sources for a station fail within a collection window, emit a `NoTrackEvent` with
`reason=NO_SOURCE_DATA` and classify each source failure using the taxonomy (§7).

---

## 5. Source Health System

Each source accumulates a health record that drives automatic failure classification
and operator alerting.

### Health fields per source

```
SourceHealthRecord:
  source_id:                 UUID
  last_successful_fetch_at:  datetime | None
  last_failed_fetch_at:      datetime | None
  consecutive_failures:      int
  http_status_history:       list[int]       (last 20 runs)
  parser_success_rate:       float           (last 20 runs)
  tracks_found_per_run:      list[int]       (last 20 runs)
  avg_latency_ms:            float
  last_failure_class:        FailureClass    (taxonomy below)
  disabled_reason:           str | None
  next_review_at:            datetime | None
  compliance_blocked:        bool
  selector_version:          str | None      (hash of selector set)
```

### Health state machine

```
HEALTHY
  → DEGRADED     (consecutive_failures >= 2 OR parser_success_rate < 0.7)
  → UNHEALTHY    (consecutive_failures >= 5 OR parser_success_rate < 0.3)
  → FAILED       (consecutive_failures >= 10 OR compliance_blocked)
  → DISABLED     (operator action, or failure class = source_not_supported)
```

On `FAILED` or `compliance_blocked`: emit alert, stop collection, preserve raw payloads.

---

## 6. Radiowave Domain Discrepancy — Critical Finding

The architecture audit uncovered a domain discrepancy:

| Station | Collector URL (actual) | D5 diagnostic URL (tested) | Match? |
|---|---|---|---|
| NOVA969 | `radiowave.com.au/diary?idds=11129` | `radiowavemonitor.com/pub_charts/diaries.aspx?IDDS=11129` | **NO** |
| KIIS1027 | `radiowavemonitor.com/pub_charts/diaries.aspx?IDDS=5080` | `radiowavemonitor.com/pub_charts/diaries.aspx?IDDS=5080` | YES |

**Consequence:** The claim "Nova baseline returned 0 rows" from the diagnostic is based on
the wrong domain. We have not tested `radiowave.com.au` at all. The Nova collector may
still be functional — or may not be — but the D5 result does not tell us.

**Action required (read-only):** Re-run Radiowave diagnostics using the correct URL for
each station. See RADIO-COVERAGE-ARCH-1-task.md §D6.

KIIS1027 (radiowavemonitor.com, IDDS=5080) remains uncertain regardless of the domain
finding: the page returned HTTP 200 with 0 `tr.diary-row` rows across multiple dates.
This could be wrong IDDS, selector drift specific to that domain, or US stations not tracked.

---

## 7. Failure Taxonomy

Every collector run failure must be classified as one of the following. The classification
drives the retry policy, alerting severity, and remediation path.

| Class | Description | Retry policy | Remediation |
|---|---|---|---|
| `provider_removed_endpoint` | API path returned 404 persistently | Stop retrying; mark source FAILED | Find alternative endpoint or source |
| `wrong_station_id` | Valid API, ID not found | Stop retrying; flag for human fix | Discover correct ID via provider search API |
| `selector_drift` | HTML 200 but target selector absent | Degrade; alert; retry next cycle | Re-inspect page, update fixture and parser |
| `js_rendered_content` | Content only in JS DOM, not raw HTML | Mark unsupported unless API alternative found | Implement API path or mark source DISABLED |
| `no_tracks_currently_available` | Valid source, no music playing (ads, talk) | Normal; continue | None — transient state |
| `geo_blocked` | Access denied by geography | Do not attempt evasion; mark BLOCKED | Use different lawful source |
| `rate_limited` | HTTP 429 | Back off exponentially; alert if persistent | Review polling cadence |
| `compliance_blocked` | ToS review pending or failed | Stop collection; block enablement | Human review and decision |
| `auth_required` | HTTP 401/403 without credentials | Mark BLOCKED; do not guess credentials | Investigate official access path |
| `date_window_empty` | Diary-type source, no entries for date yet | Retry with day-1, day-2 offsets | Normal lag; not an error |
| `parser_error` | Source accessible but parse failed | Retry; alert on consecutive failures | Inspect raw payload; update fixture |
| `network_error` | TCP/DNS failure | Retry with backoff; alert if persistent | Infrastructure check |
| `endpoint_unknown` | No verified URL for this source | Block collection; do not guess | Discovery pass required |
| `source_not_supported` | Provider confirmed unavailable for this use | Mark DISABLED permanently | Accept limitation; find alternative |
| `vendor_unavailable` | Third-party service down | Retry after cooldown | Monitor vendor status page |
| `legal_review_required` | ToS/rights review not completed | Block enablement | Human action required |

---

## 8. Enablement Governance

No source can be enabled in production until all gates below pass:

1. **Endpoint gate**: URL, path, and response shape confirmed against live API or page.
2. **Parser gate**: Fixture created from a real captured response. Unit tests pass.
3. **Dedup gate**: Source event ID or fingerprint dedup tested with at least two duplicate
   inputs that produce exactly one stored event.
4. **Compliance gate**: Compliance status = `approved`. ToS reviewed and recorded in
   VALIDATION_REGISTER.md. robots.txt checked for crawl rules.
5. **Health gate**: Source health monitoring configured. Failure classification implemented.
6. **Retention gate**: Raw payload retention policy set. No audio stored.
7. **Rollback gate**: Rollback procedure documented in ENABLE-COLLECTORS-SEQUENCE-task.md.
8. **Test gate**: 526+ passing tests, no regressions.

The scheduler flag defaults to `false`. Each source has its own enable flag. No source is
enabled before its gate checklist is complete.

---

## 9. iHeart: Current Status and Path Forward

### What is known

- iHeart v3 live-meta API (`/api/v3/live-meta/stream/{id}/*`) returned 404 for all tested
  paths and all tested station IDs including 2501 (KIISFM), 614 (Z100), 821 (WKSC).
- iHeart v2 station discovery still works: WHTZ resolves to id 1469, WKSC to id 849.
- But correcting the station IDs alone will not fix the issue if the live-meta API itself
  is gone. Station ID correction is irrelevant until a working API path is confirmed.

### Path forward: three candidate approaches (choose after validation)

**Path A — Find a working iHeart live-meta endpoint**  
Use the v2 station discovery to find the stream URL or metadata URL for each station.
The iHeart web player makes API calls that expose now-playing data — these would need to
be identified via browser network inspection (by a human, not automation).

**Path B — ICY stream metadata from iHeart streams**  
iHeart stations stream publicly. Their streams carry ICY `StreamTitle` metadata.
The `streamtheworld_icy.py` collector is already implemented.
Discovery: find the actual iHeart stream URLs (AAC/MP3 streams) and test ICY metadata.
This does not require the v3 live-meta API to exist.

**Path C — Accept that iHeart live-metadata is gone and use stream metadata only**  
If Path A yields nothing, Path B becomes the primary collection path for all iHeart stations.
No code change needed beyond finding stream URLs and creating VAL-STW-* entries.

Path B is preferred because it is independent of API availability and uses existing code.

---

## 10. Heart FM: Repair Path

The raw HTML contains these classes (confirmed from production diagnostics):
- `now-playing__wrapper`
- `last_played_songs`
- `song_wrapper`
- `song__text-content`

These are usable for parsing without JS rendering. This is a repair, not a rewrite.

**Required steps:**
1. Capture a real response from `https://www.heart.co.uk/radio/last-played-songs/` (run once, store as fixture).
2. Inspect the full HTML structure: find which container holds songs, which elements hold
   title and artist text within `song_wrapper`.
3. Update parser selectors (container, song item, title, artist, time).
4. Update fixture file with the real response.
5. Update tests.
6. Re-run VAL-HEARTFM-002.
7. Do not enable until VAL-HEARTFM-002 passes.

**This is the most immediately fixable provider.** The page is accessible, returns 200, and
has song data in the raw HTML. It needs a selector update, not a new architecture.

---

## 11. BBC Radio 1: Path to Enablement

Endpoint health: confirmed. The only blocker is the manual BBC Developer Terms review
(VAL-BBC1-006). Once ToS is reviewed and the decision documented in VALIDATION_REGISTER.md,
BBC Radio 1 can be enabled without any code change.

This is the cleanest first-enablement candidate. No repair needed.

---

## 12. MusicBrainz and Spotify: Enrichment Boundary

These services are permanently in Tier 6. Their roles are:

| Service | Allowed uses | Prohibited uses |
|---|---|---|
| MusicBrainz | Canonical MBID, ISRC lookup, alias resolution, disambiguation | Proof that a song was played on radio; primary source of play events |
| Spotify | Catalogue metadata, artwork, popularity, Spotify ID, external links | Streaming, downloads, playlist scraping, radio capture, audio redistribution |

The fact that a track appears in Spotify's catalogue does not mean it was played on a
specific radio station. Play events come only from Tier 1–4 sources with station attribution.

---

## 13. Recommended Next Implementation Passes

The following passes are approved for planning and implementation, in this sequence:

### PASS 1 (Immediate): STREAM-METADATA-DISCOVERY-1
- Read-only: find public stream URLs for all target stations.
- Test each with the existing `streamtheworld_icy.py` collector (dry run, no storage).
- Confirm `StreamTitle` format per station.
- Create VAL-STW-* entries for each station tested.
- Do not enable scheduler. Do not store data.

### PASS 2 (Parallel or sequential): HEART-HTML-PARSER-FIX-1
- Capture a single live HTML response from heart.co.uk/radio/last-played-songs/.
- Inspect structure (run locally, not on production server).
- Update `heart.py` parser selectors.
- Update fixture.
- Run unit tests.
- Do not enable collector until VAL-HEARTFM-002 passes.

### PASS 3 (Parallel): RADIOWAVE-REVALIDATION-1
- Re-test Nova at the correct URL: `radiowave.com.au/diary?idds=11129` (NOT radiowavemonitor.com).
- Clarify whether radiowavemonitor.com has selector drift or no US data.
- If Nova at radiowave.com.au works: confirm `tr.diary-row` selector, update fixtures.
- If radiowavemonitor.com has drifted: inspect page, update KIIS1027 collector URL or selector.

### PASS 4 (Human action): BBC-TOS-REVIEW-1
- Manually review BBC Developer Terms at bbc.co.uk/developer.
- Record finding in VALIDATION_REGISTER.md.
- If PASS: enable BBC Radio 1 collector (no code change).
- If FAIL: mark VAL-BBC1-006 FAILED; disable BBC Radio 1 path permanently.

### PASS 5 (Future): FINGERPRINTING-FEASIBILITY-1
- Evaluate ACRCloud Broadcast Monitoring, AudD, AcoustID.
- Review retention model, cost, API terms.
- Do not integrate until feasibility report approved.

### PASS 6 (Future): LICENSED-DATA-ASSESSMENT-1
- Evaluate radio monitoring data vendors (Radio Monitor, BDS, Luminate).
- Coverage, cost, API terms, redistribution rights.
- Do not integrate until assessment approved.

---

## 14. Current Production Enablement Status

| Station | Source | Status | Gate |
|---|---|---|---|
| NOVA969 | Radiowave `radiowave.com.au` | UNKNOWN — wrong URL tested in diagnostic | Re-validate with correct URL |
| NOVA969 | Manual CSV | AVAILABLE | Fallback only |
| KIISFM | iHeart v3 live-meta | FAILED — API gone | New endpoint needed |
| KIISFM | Manual CSV | AVAILABLE | Fallback only |
| CAPITALFM | Online Radio Box | UNVALIDATED | VAL-CAPUK-ORB-001 |
| BBCRADIO1 | BBC RMS API | ENDPOINT VALID | ToS review required |
| HEARTFMUK | Heart FM HTML | SELECTOR DRIFT | Repair required |
| WHTZ / Z100 | iHeart v3 live-meta | FAILED — API gone | New endpoint needed |
| WKSC | iHeart v3 live-meta | FAILED — API gone | New endpoint needed |
| KIIS1027 | Radiowave Monitor | UNCERTAIN — 0 rows | IDDS unverified |
| KIIS1027 | Manual CSV | AVAILABLE | Fallback only |
| All stations | Stream metadata (ICY) | DEFERRED — VAL-STW-* needed | Discovery pass |
| All stations | Audio fingerprinting | NOT IMPLEMENTED | Feasibility first |
