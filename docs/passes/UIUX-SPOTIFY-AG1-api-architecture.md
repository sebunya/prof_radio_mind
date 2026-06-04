# UIUX-SPOTIFY-AG1 — API Architecture Plan

To support a premium admin dashboard while maintaining strict production safety, this pass designs an API-first approach with clear boundaries between read-only monitoring and future operations.

## 1. Existing APIs to Reuse
- **`GET /health`**: Liveness check, returns scheduler execution status.
- **`GET /review-items`**: Fetches the list of all review queue entries.
- **`GET /webhooks`**: Lists active push webhook subscriptions.

## 2. New Safe, Read-Only Admin APIs (Add Now)
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

### `GET /api/admin/sources`
- **Purpose**: Provides detailed configurations, priority mappings, and latest validation results for all active station sources.
- **Response Schema**:
  ```json
  [
    {
      "id": "uuid-string",
      "station_id": "uuid-string",
      "station_call_sign": "CAPITALFM",
      "source_type": "online_radio_box",
      "name": "Capital FM UK Online Radio Box Candidate",
      "base_url": "https://onlineradiobox.com/uk/capitalfmuk/",
      "is_active": true,
      "priority": 1,
      "latest_validation": {
        "status": "validated",
        "validated_at": "2026-06-04T12:00:00Z",
        "validation_code": "VAL-CAPUK-ORB-001",
        "response_status_code": 200
      }
    }
  ]
  ```

### `GET /api/admin/recent-events`
- **Purpose**: Provides a stream of the 10 most recently captured raw play events to demonstrate live capture verification.
- **Response Schema**:
  ```json
  [
    {
      "id": "uuid-string",
      "station_name": "Capital FM UK",
      "station_call_sign": "CAPITALFM",
      "raw_artist": "Sabrina Carpenter",
      "raw_title": "Espresso",
      "played_at": "2026-06-04T18:45:00Z",
      "is_duplicate": false,
      "fingerprint": "a9b8c7d6..."
    }
  ]
  ```

### `GET /api/admin/collector-runs`
- **Purpose**: Exposes the execution history of station collectors (success rate, durations, failures) for operations monitoring.
- **Response Schema**:
  ```json
  [
    {
      "id": "uuid-string",
      "collector_name": "online_radio_box",
      "station_call_sign": "CAPITALFM",
      "status": "completed",
      "duration_seconds": 1.45,
      "error_count": 0,
      "started_at": "2026-06-04T18:30:00Z"
    }
  ]
  ```

### `GET /api/admin/spotify-readiness`
- **Purpose**: Checks configuration parameters and presence of Spotify credentials without revealing them.
- **Response Schema**:
  ```json
  {
    "client_id_configured": true,
    "client_secret_configured": true,
    "redirect_uri": "https://tenxradar.com/api/auth/spotify/callback",
    "api_base_url": "https://api.spotify.com/v1",
    "token_url": "https://accounts.spotify.com/api/token",
    "enrichment_enabled_flag": false,
    "match_confidence_threshold": 0.80,
    "request_timeout_seconds": 10,
    "max_retries": 2,
    "token_cache_seconds": 3300
  }
  ```

## 3. Operations Gating & Restrictions

### Strict Prohibitions (Do Not Implement Now)
- **No toggle API routes**: No `POST /api/admin/scheduler/toggle` or similar mutations.
- **No trigger buttons/endpoints**: No endpoints to manually trigger pruning, dry-runs, or databases rollbacks.
- **Secret mask rules**: `client_secret_configured` returns a Boolean check (`bool(settings.spotify_client_secret)`). The raw client secret string is **never** returned to the client.

## 4. Future Spotify Enrichment APIs (Next Passes)
When live enrichment is enabled, the API structure will expand to support:
- `POST /api/admin/spotify/enrich`: Manually trigger metadata enrichment for a specific `play_event` id.
- `POST /api/admin/spotify/callback`: Spotify OAuth callback for playlist sync operations requiring user auth (Authorization Code flow).
