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
    rate_limit_rpm: int = 30  # requests per minute per IP on rate-limited endpoints


settings = Settings()
