import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

# Import all models so their metadata is registered on Base
import app.infrastructure.database.models  # noqa: F401
from app.infrastructure.database.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Override sqlalchemy.url from DATABASE_URL env var (sync driver for Alembic)
# asyncpg cannot be used synchronously by Alembic; use psycopg2 URL format for migrations
_raw_url = os.environ.get("DATABASE_URL", config.get_main_option("sqlalchemy.url", ""))
# Alembic needs a sync driver; replace asyncpg with psycopg2 if present
_sync_url = _raw_url.replace("postgresql+asyncpg://", "postgresql://")
# configparser uses % for interpolation — escape literal % (e.g. from URL-encoded passwords)
config.set_main_option("sqlalchemy.url", _sync_url.replace("%", "%%"))


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(
        config.get_main_option("sqlalchemy.url", ""),
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
