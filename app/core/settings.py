from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    database_url: str = "postgresql+asyncpg://rmias:rmias@db:5432/rmias"
    raw_payload_storage_path: str = "/data/raw_payloads"

    # Scheduler gating
    scheduler_enabled: bool = False
    enable_nova_collector: bool = False
    enable_kiis_collector: bool = False
    enable_capital_collector: bool = False
    enable_nightly_reconciliation: bool = False

    # Security
    max_upload_bytes: int = 10 * 1024 * 1024  # 10 MB
    rate_limit_rpm: int = 30
    api_key: str = ""  # empty = auth disabled (dev); set in production

    # Interactive API docs — disabled automatically when app_env == "production"
    # unless explicitly forced on.
    enable_docs_in_production: bool = False

    # Optional HTTP Basic auth in front of the /admin SPA.
    # Both must be set to enable; empty (default) leaves /admin open so the
    # live route is never broken by a partial configuration.
    admin_basic_auth_user: str = ""
    admin_basic_auth_password: str = ""

    # Raw payload retention — files older than this many days are pruned by the
    # retention job/script. 0 (default) disables pruning entirely.
    raw_payload_retention_days: int = 0

    # Proxy rotation — comma-separated list of proxy URLs (http:// or socks5://)
    # Example: http://user:pass@proxy1:8080,socks5://proxy2:1080
    proxy_urls: str = ""

    # S3 / Hetzner Object Storage (leave blank to use local filesystem)
    s3_endpoint_url: str = ""       # e.g. https://fsn1.your-objectstorage.com
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""
    s3_bucket_name: str = "rmias-raw-payloads"
    s3_region: str = "eu-central-1"

    # Spotify Integration
    spotify_client_id: str = ""
    spotify_client_secret: str = ""
    spotify_redirect_uri: str = "https://tenxradar.com/api/auth/spotify/callback"
    spotify_api_base_url: str = "https://api.spotify.com/v1"
    spotify_token_url: str = "https://accounts.spotify.com/api/token"
    spotify_metadata_enrichment_enabled: bool = False
    spotify_match_confidence_threshold: float = 0.80
    spotify_request_timeout_seconds: int = 10
    spotify_max_retries: int = 2
    spotify_token_cache_seconds: int = 3300


settings = Settings()
