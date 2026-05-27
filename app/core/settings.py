from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

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

    # S3 / Hetzner Object Storage (leave blank to use local filesystem)
    s3_endpoint_url: str = ""       # e.g. https://fsn1.your-objectstorage.com
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""
    s3_bucket_name: str = "rmias-raw-payloads"
    s3_region: str = "eu-central-1"


settings = Settings()
