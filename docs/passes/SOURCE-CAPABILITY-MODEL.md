# Source Capability Model

**Date:** 2026-06-05  
**Status:** Design spec — no code changes in this pass  
**Purpose:** Define the data schema, lifecycle, and classification rules for all capture sources

---

## 1. Source Tier Taxonomy

```python
class SourceTier(IntEnum):
    OFFICIAL_API          = 1   # Broadcaster-issued or permissioned API
    PUBLIC_WEB_METADATA   = 2   # Public page with track data in raw HTML
    STREAM_METADATA       = 3   # ICY/HLS/DASH timed metadata from public stream
    AUDIO_FINGERPRINT     = 4   # Short-sample acoustic ID via commercial API
    LICENSED_THIRD_PARTY  = 5   # Commercial radio monitoring data vendor
    ENRICHMENT_ONLY       = 6   # MusicBrainz, Spotify — never a capture source
```

## 2. Source Type Taxonomy (extended from current SourceType enum)

Current types in codebase:
```
RADIOWAVE, IHEART, ONLINE_RADIO_BOX, MANUAL_CSV, UNKNOWN,
BBC_SOUNDS, HEART_LAST_PLAYED
```

Extended taxonomy (to add as new `SourceType` values when implementing):

```python
class SourceType(StrEnum):
    # --- Tier 1: Official APIs ---
    BBC_SOUNDS          = "bbc_sounds"          # BBC RMS API
    OFFICIAL_STATION_API= "official_station_api" # Direct broadcaster API (generic)

    # --- Tier 2: Public Web Metadata ---
    RADIOWAVE           = "radiowave"           # Radiowave diary (radiowave.com.au / radiowavemonitor.com)
    IHEART              = "iheart"              # iHeart live-meta API (currently broken)
    ONLINE_RADIO_BOX    = "online_radio_box"    # onlineradiobox.com scraper
    HEART_LAST_PLAYED   = "heart_last_played"   # heart.co.uk scraper
    PUBLIC_PAGE         = "public_page"         # Generic public page scraper

    # --- Tier 3: Stream Metadata ---
    STREAM_ICY          = "stream_icy"          # ICY/Shoutcast stream header metadata
    STREAM_HLS          = "stream_hls"          # HLS ID3 timed metadata
    STREAM_DASH         = "stream_dash"         # DASH event stream timed metadata

    # --- Tier 4: Audio Fingerprinting ---
    FINGERPRINT_ACRCLOUD = "fingerprint_acrcloud"  # ACRCloud Broadcast Monitoring API
    FINGERPRINT_AUDD     = "fingerprint_audd"      # AudD music recognition API
    FINGERPRINT_ACOUSTID = "fingerprint_acoustid"  # AcoustID open fingerprinting

    # --- Tier 5: Licensed Data ---
    LICENSED_VENDOR     = "licensed_vendor"     # Radio Monitor, BDS, Luminate, etc.

    # --- Fallback ---
    MANUAL_CSV          = "manual_csv"          # Operator-uploaded CSV
    UNKNOWN             = "unknown"
```

## 3. Compliance Status

```python
class ComplianceStatus(StrEnum):
    APPROVED         = "approved"          # ToS/legal reviewed and cleared
    PENDING_REVIEW   = "pending_review"    # Review in progress
    BLOCKED          = "blocked"           # ToS prohibits or legal risk identified
    UNKNOWN          = "unknown"           # Not yet assessed (default for new sources)
```

**Rule:** No source may be enabled in production with `compliance_status != "approved"`.

## 4. Source Capability Record (full schema)

This extends the existing `Source` entity. The fields below represent the authoritative
source-of-truth for each source's capabilities, constraints, and current state.

```python
@dataclass
class SourceCapability:
    # Identity
    source_id:              uuid.UUID
    station_id:             uuid.UUID
    source_type:            SourceType
    source_tier:            SourceTier

    # Configuration
    base_url:               str | None
    config:                 dict | None          # e.g., {"station_id": "614", "idds": "11129"}

    # Compliance & legal
    compliance_status:      ComplianceStatus     # default: UNKNOWN
    tos_review_ref:         str | None           # VAL code for ToS review
    robots_txt_checked:     bool                 # robots.txt inspected
    requires_permission:    bool                 # True if broadcaster approval needed
    disabled_reason:        str | None           # Human-readable if status=BLOCKED

    # Collection characteristics
    reliability_tier:       int                  # 1 (highest) to 5
    requires_audio_capture: bool                 # True for T4 fingerprinting
    expected_cadence_s:     int | None           # Expected polling interval (seconds)
    expected_latency_ms:    int | None           # Expected response time

    # Validation state
    validation_status:      str                  # UNVALIDATED / PASSED / FAILED
    validation_ref:         str | None           # VAL code reference
    parser_status:          str                  # NOT_BUILT / BUILT / TESTED / FAILING
    fixture_path:           str | None           # Path to test fixture

    # Retention policy
    retention_policy:       RetentionPolicy

    # Current health (updated by health monitor)
    is_active:              bool                 # False = disabled
    last_healthy_at:        datetime | None
    consecutive_failures:   int
    failure_class:          str | None           # From taxonomy
```

## 5. Retention Policy Schema

```python
@dataclass
class RetentionPolicy:
    source_id:              uuid.UUID
    store_raw_payload:      bool    # Store HTTP response bytes (metadata/HTML only, never audio)
    store_audio:            bool    # MUST always be False
    raw_payload_max_days:   int     # 0 = keep forever (subject to settings.raw_payload_retention_days)
    track_event_max_days:   int     # 0 = keep forever
    fingerprint_store:      bool    # Store derived fingerprint hash
    fingerprint_max_days:   int
    notes:                  str | None
```

**Hard constraint:** `store_audio` must always be `False`. Any source configuration with
`requires_audio_capture = True` must also ensure the audio is discarded before the raw
payload is stored. Only the derived fingerprint hash may be retained.

## 6. Source Health Record Schema

Updated by each collector run:

```python
@dataclass
class SourceHealthRecord:
    source_id:              uuid.UUID
    # Recent history (last 20 runs)
    http_status_history:    list[int]            # e.g., [200, 200, 404, 200, ...]
    parser_success_history: list[bool]           # True = parsed ≥1 track
    tracks_per_run:         list[int]            # Track counts
    latency_ms_history:     list[float]
    # Aggregates
    consecutive_failures:   int
    parser_success_rate:    float                # Computed from history
    avg_tracks_per_run:     float
    avg_latency_ms:         float
    # Last events
    last_successful_at:     datetime | None
    last_failed_at:         datetime | None
    last_failure_class:     str | None           # From taxonomy in plan §7
    # Drift
    selector_version:       str | None           # Hash of expected selectors (HTML sources)
    selector_last_verified: datetime | None
    # State
    health_state:           str                  # HEALTHY / DEGRADED / UNHEALTHY / FAILED / DISABLED
    next_review_at:         datetime | None
```

## 7. Current Source Inventory (all stations)

| Station | Source ID key | Type | Tier | Compliance | Val status | Health |
|---|---|---|---|---|---|---|
| NOVA969 | `source.NOVA969.radiowave` | RADIOWAVE | T2 | UNKNOWN | UNVALIDATED | UNKNOWN |
| NOVA969 | `source.NOVA969.manual_csv` | MANUAL_CSV | — | N/A | N/A | ALWAYS_AVAILABLE |
| KIISFM | `source.KIISFM.iheart` | IHEART | T2→BLOCKED | UNKNOWN | FAILED | FAILED — API gone |
| KIISFM | `source.KIISFM.manual_csv` | MANUAL_CSV | — | N/A | N/A | ALWAYS_AVAILABLE |
| CAPITALFM | `source.CAPITALFM.online_radio_box` | ONLINE_RADIO_BOX | T2 | UNKNOWN | UNVALIDATED | UNKNOWN |
| CAPITALFM | `source.CAPITALFM.manual_csv` | MANUAL_CSV | — | N/A | N/A | ALWAYS_AVAILABLE |
| BBCRADIO1 | `source.BBCRADIO1.bbc_sounds` | BBC_SOUNDS | T1 | PENDING_REVIEW | PASSED (endpoint) | BLOCKED — ToS pending |
| BBCRADIO1 | `source.BBCRADIO1.manual_csv` | MANUAL_CSV | — | N/A | N/A | ALWAYS_AVAILABLE |
| HEARTFMUK | `source.HEARTFMUK.heart_last_played` | HEART_LAST_PLAYED | T2 | UNKNOWN | FAILED — selector drift | REPAIR NEEDED |
| HEARTFMUK | `source.HEARTFMUK.manual_csv` | MANUAL_CSV | — | N/A | N/A | ALWAYS_AVAILABLE |
| WHTZ | `source.WHTZ.iheart` | IHEART | T2→BLOCKED | UNKNOWN | FAILED | FAILED — API gone |
| WHTZ | `source.WHTZ.manual_csv` | MANUAL_CSV | — | N/A | N/A | ALWAYS_AVAILABLE |
| WKSC | `source.WKSC.iheart` | IHEART | T2→BLOCKED | UNKNOWN | FAILED | FAILED — API gone |
| WKSC | `source.WKSC.manual_csv` | MANUAL_CSV | — | N/A | N/A | ALWAYS_AVAILABLE |
| KIIS1027 | `source.KIIS1027.radiowave` | RADIOWAVE | T2 | UNKNOWN | FAILED — 0 rows | FAILED |
| KIIS1027 | `source.KIIS1027.manual_csv` | MANUAL_CSV | — | N/A | N/A | ALWAYS_AVAILABLE |

**Pending sources (to add once validated):**

| Station | Type | Tier | Trigger |
|---|---|---|---|
| All 8 stations | STREAM_ICY | T3 | STREAM-METADATA-DISCOVERY-1 |
| HEARTFMUK | HEART_LAST_PLAYED (repaired) | T2 | HEART-HTML-PARSER-FIX-1 |
| CAPITALFM | ONLINE_RADIO_BOX | T2 | VAL-CAPUK-ORB-001 |

## 8. Source Lifecycle States

```
PLANNED → DISCOVERY → FIXTURE_CREATED → TESTED → VALIDATED → APPROVED → ACTIVE
                                                                         ↓
                                                                       DEGRADED
                                                                         ↓
                                                                       UNHEALTHY
                                                                         ↓
                                                                       FAILED
                                                                         ↓
                                                                       DISABLED (permanent)
```

**Transitions:**
- `PLANNED → DISCOVERY`: Source URL/path identified; not yet fetched live
- `DISCOVERY → FIXTURE_CREATED`: One real response captured and saved as fixture
- `FIXTURE_CREATED → TESTED`: Unit tests pass against fixture
- `TESTED → VALIDATED`: VAL-* script passes on production server
- `VALIDATED → APPROVED`: Compliance review recorded (ToS, robots.txt, legal)
- `APPROVED → ACTIVE`: Enable flag set `true` in `.env.production`
- `ACTIVE → DEGRADED`: ≥2 consecutive failures
- `DEGRADED → UNHEALTHY`: ≥5 consecutive failures
- `UNHEALTHY → FAILED`: ≥10 failures or compliance_blocked
- `FAILED → DISABLED`: Permanent — operator decision or `source_not_supported` classification

## 9. Source Capability Requirements by Tier

### T1 — Official / Permissioned API
- `requires_permission: true`
- `compliance_status` must be `approved` before `ACTIVE`
- `tos_review_ref` required
- Station ID must be verified against official documentation

### T2 — Public Web Metadata
- `robots_txt_checked: true` required before `APPROVED`
- `compliance_status` assessed (not every page is freely scrapable)
- Selector version hash tracked; drift detection implemented
- Fixture must come from a real page capture, not a synthetic document
- Parser must raise `ValueError` (not return empty) on selector absence

### T3 — Stream Metadata
- No audio stored (`store_audio: false`, `retention_policy.store_audio = false`)
- Max bytes read: 64 KB (existing implementation cap)
- One connection per station at a time
- Disconnect after metadata extracted
- ICY metadata is part of the public broadcast signal; no additional permission needed
  beyond what TuneIn, RadioGarden, and similar services already do

### T4 — Audio Fingerprinting
- `requires_audio_capture: true`
- `store_audio: false` — audio MUST be discarded after fingerprint computed
- `fingerprint_store: true` allowed — only the derived hash/fingerprint
- Commercial API terms reviewed and recorded
- Max sample duration: provider-defined (typically 3–10 seconds)
- Short retention for fingerprint: 30-day maximum recommended

### T5 — Licensed Data
- Contract terms reviewed
- Coverage documented in STATION-COVERAGE-MATRIX.md
- Redistribution restrictions enforced at API layer
- Rate limits and quotas tracked
