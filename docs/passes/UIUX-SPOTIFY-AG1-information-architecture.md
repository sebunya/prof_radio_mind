# UIUX-SPOTIFY-AG1 — Information Architecture Plan

The upgraded TenX Radar Admin Console is redesigned as a high-density, professional radio intelligence and operations portal. 

## 1. Sidebar Navigation
- **Dashboard Overview**: System health, global status indicators, and summary metrics.
- **Monitored Stations**: Stations list showing live DB records, and details on active sources.
- **Play Events**: Stream of captured songs, deduplication flags, and enrichment status.
- **Review Queue**: Pending review logs (drift, parsing, validation) with actions to resolve.
- **Spotify Metadata**: Integration configuration, readiness checks, and future data schema specifications.
- **Operations & Guardrails**: System configuration flags, migration state, security policies, and manual run guides.
- **Reports & Charts**: Station playback charts, artist counts, and export features.

---

## 2. Page Specifications & Content

### Page 1: Dashboard Overview
- **System Badges**:
  - **Environment Badge**: Displays `DEVELOPMENT`, `STAGING`, or `PRODUCTION` based on server settings.
  - **Global Health dot**: Indicates liveness of the API.
  - **Scheduler Status**: Shows whether `SCHEDULER_ENABLED` is true/false (Operational vs. Stopped).
- **Stat Cards**:
  - Active Stations Count
  - Active Webhooks Count
  - Pending Review Queue Size
  - Raw Payload Retention Policy (e.g. `Pruning: Off (Keep Forever)`)
- **Key Real-Time Streams**:
  - Recent Captured Tracks (raw text, timestamp, duplicate badge)
  - Recent Review Items

### Page 2: Stations & Sources
- **Table Columns**:
  - Call Sign, Name, Frequency, City, Country, Database ID (UUID).
- **Embedded Health View**:
  - Detailed lists of sources linked to each station.
  - Displays: Source Type (iHeart, Online Radio Box, Manual CSV), Base URL, Priority rank, Validation code (e.g. `VAL-CAPUK-ORB-001`), and Validation Timestamp.

### Page 3: Play Events Stream
- **Table Columns**:
  - Station Call Sign, Played At (UTC/Local), Raw Artist, Raw Title, Duplicate Status (labeled `DUPLICATE` or `UNIQUE`), Spotify Enrichment Status.
- **Empty & Stale States**:
  - Direct connection to `GET /api/admin/recent-events` showing real database records. Uses loading indicators and empty state diagrams.

### Page 4: Spotify Metadata Readiness
- **Credentials & Configurations**:
  - Client ID Status (`Configured` / `Missing`).
  - Client Secret Status (`Configured` / `Missing`).
  - Redirect URI matches (`https://tenxradar.com/api/auth/spotify/callback`).
  - Matching parameters: confidence threshold (`80%`), API URLs.
- **Spotify Enrichment Status Badge**:
  - Read-only indicator displaying `SPOTIFY_METADATA_ENRICHMENT_ENABLED` flag status (must show `DISABLED` by default).
- **Compliance Gating Notice**:
  - Displays the official application description to satisfy Spotify Developer policy.
  - Clearly explains the **Metadata-Only Boundary**: No Web Playback SDK, no audio preview playback, no downloads, no user OAuth login, and no playlist manipulation.

### Page 5: Operations & Guardrails
- **Config Variables Panel (Read-only)**:
  - `SCHEDULER_ENABLED`
  - `ENABLE_CAPITAL_COLLECTOR`
  - `ENABLE_NOVA_COLLECTOR`
  - `ENABLE_KIIS_COLLECTOR`
  - `ENABLE_NIGHTLY_RECONCILIATION`
  - `RAW_PAYLOAD_RETENTION_DAYS`
  - `ENABLE_DOCS_IN_PRODUCTION`
  - `ADMIN_BASIC_AUTH` configuration state.
- **Rollback & Dry Run Runbook Panel**:
  - Provides copy-paste command instructions for administrators to run dry runs manually in the terminal (e.g., `python -m app.tools.dry_run_capital`) or execute rollback scripts (`scripts/rollback-capital.sh`), ensuring operations remain text-only and safe from accidental triggers.
- **DB Migration State**:
  - Displays current Alembic migration tag (e.g., `c4e2a1f9b8d7`).

---

## 3. Data Compliance & Design Guardrails
- **No Action Buttons**: No sliders to turn on scrapers, toggle env flags, or wipe database rows.
- **UTC Clock**: A persistent UTC/local timezone visual indicator to prevent timestamp misalignment during airplay analysis.
- **Dense, Dark Mode Aesthetic**: Monochromatic tables, status badges (`success`, `warning`, `danger`), and clean typography matching Datadog/Sentry dashboard style.
