# UIUX-METADATA-AG1C — Metadata Enrichment Readiness Correction Report

This pass successfully corrects the metadata readiness framing from a Spotify-only context to a comprehensive, multi-provider "Metadata Enrichment Readiness" layer. It outlines how MusicBrainz, Spotify, Cover Art Archive, and TenX Radar's resolved matching intelligence complete each other to establish a robust metadata system.

## 1. Backend Router & Telemetry Endpoints
The dedicated read-only admin router (`app/api/routes/admin.py`) has been updated to support a unified provider metadata structure:

- **`GET /api/admin/metadata-readiness` [NEW]**: Exposes the readiness status of the complementary metadata providers:
  - **MusicBrainz**: The open canonical music authority layer (identifying recordings, artists, MBIDs, aliases, works, release groups, and ISRCs).
  - **Spotify**: The commercial catalogue context layer (track/artist/album IDs, Spotify URIs, platform artwork, popularity signals, and commercial reference links).
  - **Cover Art Archive**: The artwork fallback layer (pulling release cover images linked to MusicBrainz Release MBIDs).
  - **Compliance Boundary**: Strictly enforces safety switches (gated to readiness only, zero streaming, zero downloads, zero user OAuth/login, and raw capture source preservation).
- **`GET /api/admin/enrichment-status`**: Returns database play event status (all tracks reported as `not_configured` in accordance with the current empty schema).
- **`GET /api/admin/spotify-readiness`**: Retained for backward-compatibility to check Spotify-specific credential settings (masked Client ID/Secret check).

*No endpoint has been added that mutates databases, runs scrapers, triggers automated collection runs, or makes external provider network calls.*

---

## 2. UI/UX Page Implementations
The front-end administrative interface was refactored:
1. **Dashboard Overview**: Exposes a "Metadata Enrichment Readiness" summary panel representing the statuses of MusicBrainz, Spotify, and Cover Art Archive providers.
2. **Metadata Enrichment Console**:
   - Renders distinct cards detailing the role, guardrails, and readiness switches for **MusicBrainz**, **Spotify**, and **Cover Art Archive**.
   - Added a section detailing the **TenX Radar Resolved Metadata Layer** (explaining capture, normalization, matching scoring, and manual review queues).
   - Lists future planned matching states (`matched_auto`, `matched_manual`, `candidate_review`, `no_match`, `ambiguous`, `metadata_conflict`).
3. **Operations & Safety**: Updated to display global and provider-level enrichment switches (all set to disabled), and includes a reference panel highlighting operational provider rules.

---

## 3. Future Pass Recommendations

### `METADATA-1` — MusicBrainz Canonical Identity Foundation
* **Goal**: Implement MusicBrainz metadata lookup as the primary backend enrichment provider because it serves as the open canonical music authority (offering stable MBIDs, ISRCs, aliases, and variant disambiguation).

### `METADATA-2` — Spotify Catalogue Context Foundation
* **Goal**: Integrate Spotify API lookups as a secondary commercial context layer to grab streaming metadata, popularity signals, and catalogue URLs after the core MusicBrainz identity layer is designed.

### `METADATA-3` — Unified Metadata Matching Engine
* **Goal**: Design a matching orchestrator that combines TenX airplay normalization, MusicBrainz recordings, Spotify context, confidence weights, and manual review queue overrides.
