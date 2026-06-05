# Radio Music Intelligence & Automation System
# Validation Register
# Last updated: 2026-06-05 (RADIO-COVERAGE-ARCH-1: production VAL-LIVE-ENDPOINTS findings applied)

---

## Purpose

This register tracks the validation status of every external source, endpoint, selector, and behavioral assumption that the system depends on. No source may be promoted to production collection status without a passed validation entry here.

Validation must be performed by a human or a dedicated validation command. Results must be stored as raw evidence in the system (source_validations table) once the database is provisioned.

**Status codes:**

| Code | Meaning |
|---|---|
| UNVALIDATED | Not yet tested — default for all entries |
| PASSED | Tested and confirmed working |
| FAILED | Tested and confirmed not working |
| PARTIAL | Working but with known limitations |
| DEFERRED | Not needed for MVP — validate in a later version |
| BLOCKED | Requires action (legal, licensing, operator) before testing |
| MANUAL_ONLY | Automated route unavailable — manual CSV fallback required |

---

## 1. Nova 96.9 — Radiowave Monitor

### 1.1 Radiowave IDDS=11129 Endpoint Reachability

| Field | Value |
|---|---|
| ID | VAL-NOVA-001 |
| Description | Confirm the Radiowave Monitor diary URL for Nova 96.9 (IDDS=11129) is reachable and returns the expected HTML diary page |
| Status | UNVALIDATED — **domain discrepancy found** |
| Validated by | — |
| Validated at | — |
| Notes | **CRITICAL: Nova collector uses `radiowave.com.au/diary?idds=11129`. The D5 diagnostic incorrectly tested `radiowavemonitor.com/IDDS=11129` (wrong domain). radiowave.com.au has never been tested live. Run D6 diagnostic in RADIO-COVERAGE-ARCH-1-task.md.** |
| Risk if fails | Nova collection blocked; escalate to manual CSV fallback |

### 1.2 Radiowave DOM Selector Validation

| Field | Value |
|---|---|
| ID | VAL-NOVA-002 |
| Description | Confirm the following DOM selectors are present and accurate in a real Radiowave diary snapshot: div.column_3 (container), div.row_80 (play row), div.row_82 (track title), div.row_83 (artist/label), div.row_84 (play timestamp), a[href*="diaries_np.aspx"] (detail link / source_event_id) |
| Status | UNVALIDATED |
| Validated by | — |
| Validated at | — |
| Notes | Save a real HTML fixture from the page. Test parser against it. Drift detection must be built in. |
| Risk if fails | Parser will silently return zero rows unless drift detection is implemented |

### 1.3 Radiowave IDDS Detail-Link and source_event_id

| Field | Value |
|---|---|
| ID | VAL-NOVA-003 |
| Description | Confirm that detail links (diaries_np.aspx?...) are present in diary rows and that a unique source_event_id can be extracted reliably |
| Status | UNVALIDATED |
| Validated by | — |
| Validated at | — |
| Notes | If detail links are absent, deduplication falls back to fingerprint-based method |
| Risk if fails | Deduplication less precise; acceptable but must be documented |

### 1.4 Radiowave IDDS=11129 Twice-Daily Cadence

| Field | Value |
|---|---|
| ID | VAL-NOVA-004 |
| Description | Confirm whether Radiowave diary pages for Nova update in near-real-time or batch (once daily / twice daily / hourly) |
| Status | UNVALIDATED |
| Validated by | — |
| Validated at | — |
| Notes | Cadence determines APScheduler job frequency |
| Risk if fails | Over-polling or under-polling; adjust scheduler config |

---

## 2. Nova 96.9 — StreamTheWorld ICY (Deferred)

### 2.1 StreamTheWorld ICY Metadata Endpoint

| Field | Value |
|---|---|
| ID | VAL-NOVA-ICY-001 |
| Description | Validate that the StreamTheWorld ICY metadata endpoint for Nova 96.9 is accessible, returns current-track metadata, and is stable enough for V1 freshness use |
| Status | DEFERRED |
| Validated by | — |
| Validated at | — |
| Notes | V1 candidate only. Not a launch blocker. Do not implement in MVP. |
| Risk if deferred | No live freshness signal for Nova in MVP — acceptable |

---

## 3. KIIS-FM — iHeart Metadata Endpoint

### 3.1 iHeart Station ID 2501 Validation

| Field | Value |
|---|---|
| ID | VAL-KIIS-001 |
| Description | Confirm that station ID 2501 is the correct iHeart station ID for KIIS-FM (102.7 Los Angeles). Fetch the iHeart metadata endpoint with this ID and confirm the response contains KIIS-FM track data |
| Status | UNVALIDATED |
| Validated by | — |
| Validated at | — |
| Notes | Station ID from feasibility notes — must be confirmed before production use. If wrong, find correct ID. |
| Risk if fails | Collector fetches wrong station data; silent data corruption if not caught |

### 3.2 iHeart Endpoint URL and Format

| Field | Value |
|---|---|
| ID | VAL-KIIS-002 |
| Description | Confirm the exact iHeart endpoint URL pattern, required headers, and JSON response schema for the current-track and recently-played payloads |
| Status | UNVALIDATED |
| Validated by | — |
| Validated at | — |
| Notes | Save a real JSON fixture. Build parser against fixture, not live endpoint. |
| Risk if fails | Parser built against wrong schema |

### 3.3 iHeart HTTP 204 Behavior

| Field | Value |
|---|---|
| ID | VAL-KIIS-003 |
| Description | Confirm that the iHeart endpoint returns HTTP 204 (No Content) during commercial breaks, talk segments, or promotional blocks. Confirm that the response body is genuinely empty when 204 is returned. Confirm that response.json() must NOT be called on a 204 response. |
| Status | UNVALIDATED |
| Validated by | — |
| Validated at | — |
| Notes | CRITICAL. The 204 guard must be implemented before any production run. Never call response.json() on a 204. Persist as no_track_event. |
| Risk if fails | If 204 treated as failure: false negative rates inflate. If response.json() called on empty body: unhandled exception crashes collector. |

### 3.4 iHeart Synchronization Lag

| Field | Value |
|---|---|
| ID | VAL-KIIS-004 |
| Description | Measure the typical lag between a song starting on air and it appearing in the iHeart metadata endpoint. Determine appropriate polling interval and deduplication window. |
| Status | UNVALIDATED |
| Validated by | — |
| Validated at | — |
| Notes | Affects deduplication tolerance window and polling schedule |
| Risk if fails | Over-polling creates noise; under-polling misses plays |

### 3.5 iHeart Rate Limiting

| Field | Value |
|---|---|
| ID | VAL-KIIS-005 |
| Description | Confirm whether the iHeart metadata endpoint enforces rate limits. Check for Retry-After headers on 429 responses. |
| Status | UNVALIDATED |
| Validated by | — |
| Validated at | — |
| Notes | Implement Retry-After handling regardless |
| Risk if fails | IP block or degraded data quality if over-polled |

### 3.6 iHeart Top Songs Endpoint — KIIS-FM (VAL-IHEART-TOP-001)

| Field | Value |
|---|---|
| ID | VAL-IHEART-TOP-001 |
| Description | Confirm that the iHeart topSongs endpoint for station 2501 is reachable, returns HTTP 200, and the JSON body contains a `topSongs` or `songs` list with ≥1 entry. |
| Status | **FAILED — endpoint path does not exist** |
| Validated by | val-live-endpoints.sh automated run |
| Validated at | 2026-06-05 |
| Script | `docs/passes/val-live-endpoints.sh --kiis_top` |
| Notes | **HTTP 404. The `/topSongs` sub-path was invented by pattern extension from `/currentTrack` and was never verified against a live API. The path does not exist. The entire `/api/v3/live-meta/stream/` base is also unavailable. Do not enable `ENABLE_IHEART_TOP_SONGS`. A new endpoint must be discovered before this VAL code can be re-attempted.** |
| Risk if fails | Top-songs chart collector cannot operate; do not enable |

---

## 4. KIIS-FM — Radiowave Fallback

### 4.1 Radiowave IDDS=5080 for KIIS

| Field | Value |
|---|---|
| ID | VAL-KIIS-RAD-001 |
| Description | Confirm the Radiowave Monitor has a diary for KIIS-FM 102.7 LA at IDDS=5080. Fetch `https://www.radiowavemonitor.com/pub_charts/diaries.aspx?IDDS=5080&date=YYYY-MM-DD` for yesterday from the production server. Confirm HTTP 200 and that `tr.diary-row` elements are present. |
| Status | **FAILED — HTTP 200 but 0 tr.diary-row rows across all tested dates** |
| Validated by | val-live-endpoints.sh + D5 diagnostic |
| Validated at | 2026-06-05 |
| Script | `docs/passes/val-live-endpoints.sh --kiis1027_radiowave` |
| Notes | **HTTP 200 but 0 diary rows for all dates tested (1–7 days back). IDDS=5080 was never verified against live data. Radiowave Monitor (`radiowavemonitor.com`) may not track US stations — its known coverage is Australian radio. IDDS re-discovery required. Do not enable `ENABLE_KIIS_RADIOWAVE_COLLECTOR`. See RADIOWAVE-REVALIDATION-1 in RADIO-COVERAGE-ARCH-1-task.md.** |
| Risk if fails | KIIS1027 Radiowave source unavailable; ICY stream is the next path |

---

## 5. KIIS-FM — Official HTML Fallback

### 5.1 KIIS Official HTML Recently Played / Top Songs

| Field | Value |
|---|---|
| ID | VAL-KIIS-HTML-001 |
| Description | Check whether the KIIS-FM official website exposes a recently played or top songs page accessible via httpx (no JS rendering required). Confirm if structured data is extractable. |
| Status | UNVALIDATED |
| Validated by | — |
| Validated at | — |
| Notes | Tertiary fallback only. Only implement if iHeart primary route fails. |
| Risk if fails | One fewer fallback option; not a blocker |

---

## 6. Capital FM UK — Online Radio Box Candidate Source

### 6.1 Online Radio Box Reachability

| Field | Value |
|---|---|
| ID | VAL-CAPUK-ORB-001 |
| Description | Confirm Online Radio Box Capital FM UK page is reachable and returns expected station page HTML |
| Status | UNVALIDATED |
| Validated by | — |
| Validated at | — |
| Notes | Test reachability using validation adapter |
| Risk if fails | Capital automated collection blocked; manual CSV fallback required |

### 6.2 Now-Playing Section Parseability

| Field | Value |
|---|---|
| ID | VAL-CAPUK-ORB-002 |
| Description | Confirm the page exposes a parseable “On the air” or now-playing section from saved HTML fixture |
| Status | UNVALIDATED |
| Validated by | — |
| Validated at | — |
| Notes | Save real HTML fixture from the page. Test parser against it. |
| Risk if fails | No live current-track signal |

### 6.3 History Playlist Parseability

| Field | Value |
|---|---|
| ID | VAL-CAPUK-ORB-003 |
| Description | Confirm the page exposes playlist/history records that can be parsed from saved fixture |
| Status | UNVALIDATED |
| Validated by | — |
| Validated at | — |
| Notes | Important for backfill or drift recovery |
| Risk if fails | Historical play recovery unavailable or incomplete |

### 6.4 Artist and Title Reliability

| Field | Value |
|---|---|
| ID | VAL-CAPUK-ORB-004 |
| Description | Confirm parser can extract artist and title reliably from saved fixture |
| Status | UNVALIDATED |
| Validated by | — |
| Validated at | — |
| Notes | Clean any label suffixes or extra text |
| Risk if fails | False plays or unusable reporting |

### 6.5 Time Extraction or observed_at Derivation

| Field | Value |
|---|---|
| ID | VAL-CAPUK-ORB-005 |
| Description | Confirm parser can extract event time or derive observed_at safely when source time is unavailable |
| Status | UNVALIDATED |
| Validated by | — |
| Validated at | — |
| Notes | Handle timezone offsets carefully |
| Risk if fails | Incorrect broadcast-day grouping |

### 6.6 No Visible Track / Commercial Break Stability

| Field | Value |
|---|---|
| ID | VAL-CAPUK-ORB-006 |
| Description | Confirm missing/no visible track creates no_track_event, not collector failure |
| Status | UNVALIDATED |
| Validated by | — |
| Validated at | — |
| Notes | Required to ensure continuous loop execution |
| Risk if fails | False error spikes and unstable collector behavior |

### 6.7 Polling Cadence and Source Limits

| Field | Value |
|---|---|
| ID | VAL-CAPUK-ORB-007 |
| Description | Confirm conservative polling cadence and source limitation policy |
| Status | UNVALIDATED |
| Validated by | — |
| Validated at | — |
| Notes | Avoid aggressive polling to prevent IP blocks |
| Risk if fails | Over-polling, IP blocking, unreliable data |

### 6.8 Disabled by Default Gate

| Field | Value |
|---|---|
| ID | VAL-CAPUK-ORB-008 |
| Description | Confirm Capital collector remains disabled by default until validation passes |
| Status | UNVALIDATED |
| Validated by | — |
| Validated at | — |
| Notes | Enforced by scheduler settings flags |
| Risk if fails | Unvalidated production collection |

---

## 7. Capital FM UK — Manual CSV Fallback

### 7.1 Capital Manual CSV Fallback

| Field | Value |
|---|---|
| ID | VAL-CAPUK-MANUAL-001 |
| Description | Confirm manual CSV import accepts Capital FM UK rows and attributes them to the correct station/source |
| Status | UNVALIDATED |
| Validated by | — |
| Validated at | — |
| Notes | Manual CSV fallback is mandatory. Must be tested before Capital is included in reporting. |
| Risk if fails | Capital cannot appear in client-facing reports if automation is not ready |

---

## 8. BBC Radio 1 — BBC Sounds RMS API (EXTRACT-2)

### 8.1 RMS API Reachability (VAL-BBC1-001)

| Field | Value |
|---|---|
| ID | VAL-BBC1-001 |
| Description | Confirm `GET https://rms.api.bbc.co.uk/v2/services/bbc_radio_one/segments/latest` is reachable from the production server, returns HTTP 200, and the JSON body contains a `data` list of segments. |
| Status | **PASSED** |
| Validated by | val-live-endpoints.sh automated run |
| Validated at | 2026-06-05 |
| Script | `docs/passes/val-live-endpoints.sh --bbc` |
| Notes | HTTP 200, `data` list present, music segments confirmed. **Only remaining blocker: VAL-BBC1-006 (manual ToS review).** |
| Risk if fails | N/A — passed |

### 8.2 BBC ToS — Automated Access Permissibility (VAL-BBC1-006)

| Field | Value |
|---|---|
| ID | VAL-BBC1-006 |
| Description | Manual review of BBC Developer terms of service to confirm that automated polling of the BBC Sounds RMS API at 5-minute intervals is permissible. Review https://www.bbc.co.uk/developer and any linked API terms. |
| Status | BLOCKED — manual review required |
| Validated by | — |
| Validated at | — |
| Script | None — manual check only |
| Notes | Must be completed before `ENABLE_BBC_RADIO1_COLLECTOR` is set to true. Document findings (PASS/FAIL + rationale) here when complete. This is a hard prerequisite for BBC enablement — Step 5 in `ENABLE-COLLECTORS-SEQUENCE-task.md`. |
| Risk if fails | ToS violation; must not enable BBC Radio 1 collector |

---

## 9. Heart FM UK — Last-Played-Songs Page (EXTRACT-2)

### 9.1 Page Reachability (VAL-HEARTFM-001)

| Field | Value |
|---|---|
| ID | VAL-HEARTFM-001 |
| Description | Confirm `GET https://www.heart.co.uk/radio/last-played-songs/` is reachable from the production server, returns HTTP 200, and the response body is non-empty HTML. |
| Status | UNVALIDATED |
| Validated by | — |
| Validated at | — |
| Script | `docs/passes/val-live-endpoints.sh --heart` (covers reachability and selector check together) |
| Notes | Covered by VAL-HEARTFM-002 script run — a pass on 002 implies 001 passes. |
| Risk if fails | Heart FM collection blocked; fall back to manual CSV |

### 9.2 CSS Selector Validation (VAL-HEARTFM-002)

| Field | Value |
|---|---|
| ID | VAL-HEARTFM-002 |
| Description | Confirm CSS selectors are present in a live page response and return ≥1 song entry. |
| Status | **PARSER_REPAIRED — awaiting live re-validation** |
| Validated by | val-live-endpoints.sh automated run (initial failure); HEART-HTML-PARSER-FIX-1 (repair) |
| Validated at | 2026-06-05 (failure); 2026-06-05 (repair implemented) |
| Script | `docs/passes/val-live-endpoints.sh --heart` |
| Notes | **Initial run: HTTP 200, `div.station-song-history` MISSING. New classes found: `now-playing__wrapper`, `last_played_songs`, `song_wrapper`, `song__text-content`. Parser repaired 2026-06-05: updated to new selectors + added `__NEXT_DATA__` JSON strategy + old-selector fallback. Fixture and tests updated (530 passing). Re-run VAL-HEARTFM-002 against live page to confirm parser returns ≥1 track. robots.txt and ToS review still pending.** |
| Risk if fails | Collector blocked; do not enable `ENABLE_HEART_COLLECTOR` until live re-validation passes |

### 9.3 Timezone Assumption (VAL-HEARTFM-005)

| Field | Value |
|---|---|
| ID | VAL-HEARTFM-005 |
| Description | Confirm that time values displayed on the Heart FM last-played page (`HH:MM` in `time.song-item__time`) correspond to UK time (Europe/London), and document whether times are in local clock time or UTC, including DST behavior. |
| Status | UNVALIDATED |
| Validated by | — |
| Validated at | — |
| Script | None — manual inspection of live page timestamps vs actual broadcast time |
| Notes | Parser currently assumes UTC directly from HH:MM without DST adjustment. If times are local UK time, `played_at` will be off by 1 hour during BST. Low urgency — timestamps are approximate anyway. |
| Risk if fails | `played_at` off by 1 hour during British Summer Time; acceptable for V1 but should be fixed |

### 9.4 Polling Cadence and ToS (VAL-HEARTFM-007)

| Field | Value |
|---|---|
| ID | VAL-HEARTFM-007 |
| Description | Review Heart FM / Global Radio terms of service and robots.txt to confirm automated polling of the last-played-songs page at 5-minute intervals is permissible. |
| Status | UNVALIDATED |
| Validated by | — |
| Validated at | — |
| Script | None — manual check only |
| Notes | Check https://www.heart.co.uk/robots.txt and Global Radio developer/ToS pages. 5-minute cadence is the same as BBC Radio 1. |
| Risk if fails | ToS violation; reduce cadence or switch to manual CSV |

---

## 10. Z100 New York (WHTZ) — iHeart Now-Playing (EXTRACT-2)

### 10.1 iHeart Station ID 614 — Live Validation (VAL-Z100-001)

| Field | Value |
|---|---|
| ID | VAL-Z100-001 |
| Description | Confirm that iHeart station_id=614 is the correct station ID for Z100 New York (WHTZ 100.3 FM). Fetch `https://api.iheart.com/api/v3/live-meta/stream/614/currentTrack` from the production server. Confirm HTTP 200 or 204, and that a 200 response contains `currentTrack` with `artist` and `title`. |
| Status | **FAILED — iHeart v3 live-meta API unavailable** |
| Validated by | val-live-endpoints.sh automated run |
| Validated at | 2026-06-05 |
| Script | `docs/passes/val-live-endpoints.sh --z100` |
| Notes | **HTTP 404. All `/api/v3/live-meta/stream/{id}` sub-paths return 404 including the base path. v2 station discovery returns id=1469 for WHTZ (not 614), but correcting the ID alone is insufficient while the API endpoint itself is unavailable. Do not enable `ENABLE_Z100_COLLECTOR`. Stream metadata (ICY) is the next path — see STREAM-METADATA-DISCOVERY-1.** |
| Risk if fails | Collector cannot operate; no automated Z100 data until a valid endpoint is found |

---

## 11. WKSC 103.5 Chicago — iHeart Now-Playing (EXTRACT-2)

### 11.1 iHeart Station ID 821 — Live Validation (VAL-WKSC-001)

| Field | Value |
|---|---|
| ID | VAL-WKSC-001 |
| Description | Confirm that iHeart station_id=821 is the correct station ID for WKSC 103.5 Chicago. Fetch `https://api.iheart.com/api/v3/live-meta/stream/821/currentTrack` from the production server. Confirm HTTP 200 or 204, and that a 200 response contains `currentTrack` with `artist` and `title`. |
| Status | **FAILED — iHeart v3 live-meta API unavailable** |
| Validated by | val-live-endpoints.sh automated run |
| Validated at | 2026-06-05 |
| Script | `docs/passes/val-live-endpoints.sh --wksc` |
| Notes | **HTTP 404. Same failure mode as VAL-Z100-001. v2 station discovery returns id=849 for WKSC (not 821), but API endpoint unavailability makes station ID correction moot. Do not enable `ENABLE_WKSC_COLLECTOR`. See STREAM-METADATA-DISCOVERY-1.** |
| Risk if fails | Collector cannot operate; no automated WKSC data until a valid endpoint is found |

---

## 12. iHeart Recently-Played Batch Fallback (EXTRACT-4)

### 12.1 iHeart Recently-Played Endpoint Reachability (VAL-IHEART-RECENT-001)

| Field | Value |
|---|---|
| ID | VAL-IHEART-RECENT-001 |
| Description | Confirm that the iHeart recently-played endpoint returns HTTP 200 (or 204) for all three covered stations: KIISFM (2501), Z100/WHTZ (614), WKSC (821). Fetch `https://api.iheart.com/api/v3/live-meta/stream/{id}/recentlyPlayed` for each station from the production server. Confirm HTTP 200 with a JSON body containing a `tracks` (or `recentTracks`) array, or HTTP 204. |
| Status | **FAILED — endpoint path does not exist** |
| Validated by | val-live-endpoints.sh automated run |
| Validated at | 2026-06-05 |
| Script | `docs/passes/val-live-endpoints.sh --iheart_recent` |
| Notes | **HTTP 404 for station 2501 (valid station). `/recentlyPlayed` sub-path was assumed, not verified. The entire `/api/v3/live-meta/stream/` API is unavailable. Do not enable `ENABLE_IHEART_RECENTLY_PLAYED`. A new endpoint must be discovered or stream metadata (ICY) used as the fallback instead.** |
| Risk if fails | Batch fallback collector cannot operate; do not enable |

---

## 13. Deferred Validations

### 8.1 Spotify Enrichment

| Field | Value |
|---|---|
| ID | VAL-DEFER-SPOTIFY-001 |
| Description | Validate Spotify API access, ISRC matching, artwork retrieval, and enrichment accuracy for V1 |
| Status | DEFERRED |
| Validated by | — |
| Validated at | — |
| Notes | Not MVP. Enrichment fields in schema must be nullable. Do not build Spotify integration in MVP. |

### 8.2 Rebrowser / Licensed Dataset

| Field | Value |
|---|---|
| ID | VAL-DEFER-LICENSED-001 |
| Description | Investigate licensed music monitoring dataset providers (e.g., Rebrowser, BDS, Luminate) as supplemental data sources for V1 |
| Status | DEFERRED |
| Validated by | — |
| Validated at | — |
| Notes | Not MVP. Cost implications significant. |

---

## 14. Operational Contracts

### 9.1 Broadcast Day Definition

| Field | Value |
|---|---|
| ID | VAL-OPS-001 |
| Description | Confirm with client whether radio broadcast day is midnight-to-midnight or uses a different start time (e.g., 05:00 or 06:00 local). Confirm per-station if different. |
| Status | UNVALIDATED |
| Validated by | — |
| Validated at | — |
| Notes | Default is midnight unless configured. station_broadcast_days table supports per-station configuration. Must be confirmed before Pass 13 (reporting). |
| Risk if fails | Reports group plays under wrong broadcast day |

### 9.2 Manual CSV Schema Contract

| Field | Value |
|---|---|
| ID | VAL-OPS-002 |
| Description | Confirm that the manual CSV import schema (station, report_date_local, title, artist, image, play_time_local, observed_play_count, rank, source_note) is acceptable to the client or operator |
| Status | UNVALIDATED |
| Validated by | — |
| Validated at | — |
| Notes | Must be confirmed before Pass 9 (manual import). Schema validation will enforce these columns. |
| Risk if fails | Manual imports fail validation; clients cannot submit data |

### 9.3 Corrected Report Policy

| Field | Value |
|---|---|
| ID | VAL-OPS-003 |
| Description | Confirm policy for when a report may be issued as "corrected": who approves corrections, whether corrected reports replace previous exports or are issued as additional versions, and what the client communication expectation is |
| Status | UNVALIDATED |
| Validated by | — |
| Validated at | — |
| Notes | Must be confirmed before Pass 14 (correction/versioning). |
| Risk if fails | Correction workflow built without client agreement |

---

## Validation Progress Summary

| Category | § | Total | Passed | Failed | Partial | Blocked | Deferred | Unvalidated |
|---|---|---|---|---|---|---|---|---|
| Nova Radiowave | 1 | 4 | 0 | 0 | 0 | 0 | 0 | 4 |
| Nova StreamTheWorld | 2 | 1 | 0 | 0 | 0 | 0 | 1 | 0 |
| KIIS iHeart now-playing | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 5 |
| KIIS iHeart top songs | 3.6 | 1 | 0 | 0 | 0 | 0 | 0 | 1 |
| KIIS Radiowave fallback | 4 | 1 | 0 | 0 | 0 | 0 | 0 | 1 |
| KIIS HTML fallback | 5 | 1 | 0 | 0 | 0 | 0 | 0 | 1 |
| Capital FM UK Online Radio Box | 6 | 8 | 0 | 0 | 0 | 0 | 0 | 8 |
| Capital manual | 7 | 1 | 0 | 0 | 0 | 0 | 0 | 1 |
| BBC Radio 1 | 8 | 2 | 0 | 0 | 0 | 1 | 0 | 1 |
| Heart FM UK | 9 | 4 | 0 | 0 | 0 | 0 | 0 | 4 |
| Z100 New York (WHTZ) | 10 | 1 | 0 | 0 | 0 | 0 | 0 | 1 |
| WKSC 103.5 Chicago | 11 | 1 | 0 | 0 | 0 | 0 | 0 | 1 |
| iHeart recently-played | 12 | 1 | 0 | 0 | 0 | 0 | 0 | 1 |
| Deferred | 13 | 2 | 0 | 0 | 0 | 0 | 2 | 0 |
| Operational contracts | 14 | 3 | 0 | 0 | 0 | 0 | 0 | 3 |
| **Total** | | **36** | **0** | **0** | **0** | **1** | **3** | **32** |

VAL-BBC1-006 is BLOCKED (manual ToS review). All other 31 non-deferred, non-blocked
validations are UNVALIDATED. No collector may be enabled until its VAL code is confirmed
in this register and in `docs/passes/val-live-endpoints.sh`.
