# UIUX-METADATA-AG1C — Information Architecture Plan

The upgraded TenX Radar Admin Console is redesigned as a high-density, professional radio intelligence and operations portal.

## 1. Sidebar Navigation
- **Dashboard Overview**: System health, global status indicators, metadata enrichment overview, and summary metrics.
- **Monitored Stations**: Stations list showing live DB records, and details on active sources.
- **Play Events**: Stream of captured songs, deduplication flags, and enrichment status.
- **Review Queue**: Pending review logs (drift, parsing, validation) with actions to resolve.
- **Metadata Enrichment** [UPDATED]: Integration configuration, provider readiness checks, and resolved metadata schema boundaries.
- **Operations & Guardrails**: System configuration flags, migration state, security policies, and manual run guides.
- **Reports & Charts**: Station playback charts, artist counts, and export features.

---

## 2. Page Specifications & Content

### Page 1: Dashboard Overview
- **System Badges**: Environment badge, global health dot, and collector switches.
- **Stat Cards**: Active Stations, Pending Reviews, Active Webhooks, and System status indicators.
- **Metadata Enrichment Overview** [NEW]: Card detailing readiness statuses (Configured vs Not Configured) and roles for MusicBrainz, Spotify, and Cover Art Archive.
- **Key Real-Time Streams**: Recent Captured Tracks and Recent Review Items.

### Page 4: Metadata Enrichment Console [UPDATED]
- **Three Provider Readiness Cards**:
  - **MusicBrainz**: Configured status, User-Agent parameters, rate limit (1 req/sec), format (`json`), and compliance authority statement.
  - **Spotify**: Configured status (client ID/secret presence flags), redirect URI (`https://tenxradar.com/api/auth/spotify/callback`), and catalogue context details.
  - **Cover Art Archive**: Base URL status, and linkage to MusicBrainz Release MBID.
- **TenX Radar Resolved Metadata Layer**:
  - Explanation of matching responsibilities (airplay capture, normalizations, local caching, matching score weights, and exceptions).
  - Visualization of matching states (`matched_auto`, `matched_manual`, `candidate_review`, `no_match`, `ambiguous`, `metadata_conflict`).
- **Compliance & Provider Guardrails Boundary**:
  - Outlines raw capture preservation and provider restrictions.
  - Displays strict legal switches (NO Streaming, NO Downloads, NO Playlist Scraping, NO Audio Playback).
