# UIUX-METADATA-AG1C — API Architecture Plan

To support a premium admin dashboard while maintaining strict production safety, this pass designs an API-first approach with clear boundaries between read-only monitoring and future operations, reflecting a multi-provider metadata model.

## 1. Existing APIs to Reuse
- **`GET /health`**: Liveness check, returns scheduler execution status.
- **`GET /review-items`**: Fetches the list of all review queue entries.
- **`GET /webhooks`**: Lists active push webhook subscriptions.

## 2. New Safe, Read-Only Admin APIs (Added)
These endpoints are placed under a new `admin` tags router (`app/api/routes/admin.py`) mounted under `/api/admin`. They do not mutate database state, execute external network requests, or expose server secrets.

### `GET /api/admin/overview`
- **Purpose**: Aggregates environment flags, scheduler switches, safety options, and high-level counts.
- **Response Schema**:
  ```json
  {
    "app_env": "production",
    "scheduler_enabled": false,
    "enable_capital_collector": false,
    "enable_nova_collector": false,
    "enable_kiis_collector": false,
    "enable_nightly_reconciliation": false,
    "raw_payload_retention_days": 0,
    "enable_docs_in_production": false,
    "admin_basic_auth_configured": true,
    "stats": {
      "active_stations": 3,
      "total_sources": 6,
      "pending_reviews": 0,
      "active_webhooks": 0
    }
  }
  ```

### `GET /api/admin/metadata-readiness` [NEW]
- **Purpose**: Returns configuration checks and readiness state for all external music metadata providers (MusicBrainz, Spotify, and Cover Art Archive) alongside the compliance boundaries.
- **Response Schema**:
  ```json
  {
    "status": "disabled",
    "mode": "readiness_only",
    "providers": {
      "musicbrainz": {
        "role": "open_canonical_identity",
        "configured": true,
        "enabled": false,
        "base_url_configured": true,
        "user_agent_configured": true,
        "rate_limit_per_second": 1,
        "default_format": "json",
        "live_calls_enabled": false
      },
      "spotify": {
        "role": "commercial_catalogue_context",
        "configured": false,
        "enabled": false,
        "client_id_configured": false,
        "client_secret_configured": false,
        "redirect_uri_configured": true,
        "live_calls_enabled": false
      },
      "cover_art_archive": {
        "role": "cover_art_fallback",
        "configured": true,
        "enabled": false,
        "base_url_configured": true,
        "requires_musicbrainz_release_mbid": true,
        "live_calls_enabled": false
      }
    },
    "compliance_boundary": {
      "radio_capture_source": "TenX Radar monitored station sources",
      "musicbrainz": "canonical music identity and disambiguation only",
      "spotify": "catalogue metadata and platform reference only",
      "cover_art_archive": "release artwork reference only",
      "no_streaming": true,
      "no_downloads": true,
      "no_playlist_scraping": true,
      "no_playback": true
    }
  }
  ```

### `GET /api/admin/spotify-readiness` (Backward Compatible)
- **Purpose**: Checks configuration parameters and presence of Spotify credentials without revealing them.

## 3. Operations Gating & Restrictions
- **No toggle API routes**: No scheduler/collector mutation APIs.
- **Secret mask rules**: Secret config flags are returned as simple Booleans. Raw credential secrets are **never** returned to client-side code.
