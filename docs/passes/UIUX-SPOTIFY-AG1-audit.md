# UIUX-SPOTIFY-AG1 — Pre-Implementation Audit Report

## 1. Branch Base and REF-0 State Detection
- **Base Branch Used**: `feat/uiux-spotify-ag1` branched from `main`.
- **REF-0 Status**: Fully present on `main` and merged via PR #6. All required safety components (Alembic URL-encoded config parser escape, Capital rollback script, dry-run python tool, raw payload pruning script, scheduler fingerprint-based deduplication, neutral HTTP client framing, docs gating logic, and Basic Auth middleware) are verified in place.

## 2. Production Safety Snapshot
A remote snapshot of the Hetzner production server (`178.105.238.18`) was performed on 2026-06-04.
- **Git HEAD on Production**: Up to date with origin/main (`29b748a`).
- **Active Safety Switches**:
  - `SCHEDULER_ENABLED=false`
  - `ENABLE_CAPITAL_COLLECTOR=false`
  - `ENABLE_NOVA_COLLECTOR=false`
  - `ENABLE_KIIS_COLLECTOR=false`
  - `ENABLE_NIGHTLY_RECONCILIATION=false`
- **Application Health**:
  - Root `/` returns: status `ok`, scheduler `stopped`, collectors `disabled`.
  - `/health` returns: status `ok`, pending review items `0`.
- **Conclusion**: Production is frozen, stable, and completely safe. No live automated loops or scrapers are running.

## 3. Current UI and API Audit
- **Current UI**:
  - The admin dashboard is a Single Page Application (SPA) located at `/admin/` (serves `app/static/index.html`).
  - Styled with custom CSS (`app.css`) and uses modular JS views (`dashboard.js`, `stations.js`, `review.js`, `reports.js`, `playlist.js`, `aria-charts.js`, `webhooks.js`, `backfill.js`) dynamically loaded via hash routing.
  - The stations view currently displays hardcoded source badges ("Radiowave", "iHeart", "Manual CSV") for all stations, which does not reflect the database-driven configuration.
  - The station ID displays as `—` because the station models are seeds read from a static Python array, lacking database UUID integration on the client side.
- **Current APIs**:
  - `/health`: returns liveness and system summary.
  - `/stations`: lists station seeds from a static `STATION_SEEDS` list. Doesn't read from the DB.
  - `/review-items`: manages human review queue lifecycle.
  - `/reports`: handles station, PDF reports, and master spreadsheets.
  - `/playlist`: provides playlist recommendations/rotation metrics.
  - `/charts/aria`: handles ARIA chart metadata ingestion.
  - `/webhooks`: push subscriptions.
  - `/backfill`: processes CSV imports.

## 4. Current Database & Enrichment Readiness Audit
- **Database Schema**:
  - Active tables: `stations`, `sources`, `play_events`, `no_track_events`, `review_items`, `collector_runs`, `reports`, `users`, `source_validations`, `source_route_priorities`.
  - The `songs` table contains fields for `isrc` and `label`, and `play_events` contains `raw_label` and `is_duplicate`.
  - **Missing Spotify Fields**: No tables or columns exist for storing Spotify-specific identifiers (`spotify_track_id`, `spotify_artist_id`, etc.) or matching metadata (such as `match_confidence_score` or `enrichment_status`).
- **Enrichment Services**:
  - Only `app/application/enrichment/musicbrainz.py` exists, which provides unauthenticated ISRC and label lookups with respect to rate limits (1 req/sec).
  - No Spotify backend Client Credentials implementation exists.
- **Compliance Boundary**:
  - Web API usage is strictly metadata-only. TenX Radar does not stream, download, redistribute, or sell Spotify audio content.

## 5. Information Architecture & Operations
- **Data Available for Dashboards**: Active stations list, review queue metrics, webhook subscriptions, and overall app health.
- **Data Missing**: True source configuration status, validation history, latest play events stream, collector logs, and Spotify integration parameters.
- **Operational Safety Metrics**: The dashboard must display all safety switches (`SCHEDULER_ENABLED`, collector status) as read-only indicators. No operational control elements (buttons to prune, rollback, or activate automation) should be present in the UI.

## 6. Safe Scope for UIUX-SPOTIFY-AG1
- **Safely Implementable Now**:
  1. Add new read-only API endpoints for administrator monitoring:
     - `GET /api/admin/overview`: aggregates status flags, environment settings, and basic metrics.
     - `GET /api/admin/sources`: lists real database-driven source configurations, priorities, and validation status.
     - `GET /api/admin/recent-events`: streams the 10 most recently captured tracks.
     - `GET /api/admin/collector-runs`: lists the history of collector runs.
     - `GET /api/admin/spotify-readiness`: exposes credentials status and settings.
  2. Upgrade the UI:
     - Introduce a dark-themed, data-dense layout with refined typography (Google Fonts - Inter/Outfit) and micro-animations.
     - Build a dedicated "Operations & Safety" page detailing the status of the environment, safety switches, Basic Auth, Docs gating, payload retention, and dry-run execution instructions.
     - Upgrade "Stations" to load live database configurations instead of static mocks.
     - Add a "Spotify Metadata" view showcasing compliance boundaries, required fields, and credentials status.
- **Deferred Work (Future Passes)**:
  - Database migrations for Spotify schema updates.
  - Implementation of the `SpotifyClient` Client Credentials fetch mechanism.
  - Active enrichment loops and playlist sync.
