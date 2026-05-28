from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    # Public-facing base URL used to build absolute links in outgoing emails
    # (e.g. unsubscribe links).  No trailing slash.
    # Example: https://rmias.shopgoldplus.com
    base_url: str = ""

    database_url: str = "postgresql+asyncpg://rmias:rmias@db:5432/rmias"
    raw_payload_storage_path: str = "/data/raw_payloads"

    # Security
    max_upload_bytes: int = 10 * 1024 * 1024  # 10 MB
    rate_limit_rpm: int = 30
    api_key: str = ""  # empty = auth disabled (dev); set in production
    # Comma-separated allowed CORS origins. Empty = allow all (*) — acceptable when
    # the admin frontend and API share the same origin. Set explicitly in production.
    cors_origins: str = ""

    # Proxy rotation — comma-separated list of proxy URLs (http:// or socks5://)
    # Example: http://user:pass@proxy1:8080,socks5://proxy2:1080
    proxy_urls: str = ""

    # Email / SMTP — leave smtp_host blank to disable email sending (dry-run logs to stdout)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_use_tls: bool = True
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "reports@rmias.example.com"
    smtp_from_name: str = "RMIAS Radio Reports"

    # Trend alert thresholds — used by the nightly trend-alert scheduler job
    # song.trending fires when a song reaches this many plays in 7 days for
    # the first time (i.e. was below threshold the prior 7 days).
    trend_plays_threshold: int = 50
    # song.new_entry fires when a brand-new song (zero plays last week) reaches
    # this many plays in its first 7-day window.
    trend_new_entry_plays: int = 10

    # Sentry — leave sentry_dsn blank to disable (safe default)
    sentry_dsn: str = ""
    # Fraction of transactions sent to Sentry for performance monitoring (0–1).
    # 0.1 = 10 % sampled — good production default.  1.0 = everything (dev only).
    sentry_traces_sample_rate: float = 0.1

    # S3 / Hetzner Object Storage (leave blank to use local filesystem)
    s3_endpoint_url: str = ""       # e.g. https://fsn1.your-objectstorage.com
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""
    s3_bucket_name: str = "rmias-raw-payloads"
    s3_region: str = "eu-central-1"


settings = Settings()
