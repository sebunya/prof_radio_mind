# Radio Music Intelligence & Automation System
# Validation Register
# Pass 0 — Initial State
# Last updated: 2026-05-24

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
| Status | UNVALIDATED |
| Validated by | — |
| Validated at | — |
| Notes | Must be confirmed before Pass 6 (Radiowave collector) |
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

---

## 4. KIIS-FM — Radiowave Fallback

### 4.1 Radiowave IDDS=5080 for KIIS

| Field | Value |
|---|---|
| ID | VAL-KIIS-RAD-001 |
| Description | Confirm whether Radiowave Monitor has a diary for KIIS-FM at IDDS=5080. Fetch the page, check it returns KIIS play data, confirm DOM selector compatibility with the Nova parser. |
| Status | UNVALIDATED |
| Validated by | — |
| Validated at | — |
| Notes | Reconciliation/fallback source only. Not the primary MVP source for KIIS. |
| Risk if fails | KIIS reconciliation has one fewer fallback option |

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

## 8. Deferred Validations

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

## 9. Operational Contracts

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

| Category | Total | Passed | Failed | Partial | Deferred | Unvalidated |
|---|---|---|---|---|---|---|
| Nova Radiowave | 4 | 0 | 0 | 0 | 0 | 4 |
| Nova StreamTheWorld | 1 | 0 | 0 | 0 | 1 | 0 |
| KIIS iHeart | 5 | 0 | 0 | 0 | 0 | 5 |
| KIIS Radiowave fallback | 1 | 0 | 0 | 0 | 0 | 1 |
| KIIS HTML fallback | 1 | 0 | 0 | 0 | 0 | 1 |
| Capital FM UK Online Radio Box | 8 | 0 | 0 | 0 | 0 | 8 |
| Capital manual | 1 | 0 | 0 | 0 | 0 | 1 |
| Deferred | 2 | 0 | 0 | 0 | 2 | 0 |
| Operational contracts | 3 | 0 | 0 | 0 | 0 | 3 |
| **Total** | **26** | **0** | **0** | **0** | **3** | **23** |

All 23 non-deferred validations must be addressed before their dependent passes can be declared complete.
