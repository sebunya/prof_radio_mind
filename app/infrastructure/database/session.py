"""Async SQLAlchemy session factory — lazy engine creation.

The engine is created on first use so that importing app.main in tests
that don't need a real database does not trigger a connection attempt.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

_engine: AsyncEngine | None = None
_factory: async_sessionmaker[AsyncSession] | None = None


def _get_engine() -> AsyncEngine:
    global _engine, _factory
    if _engine is None:
        from app.core.settings import settings

        _engine = create_async_engine(
            settings.database_url,
            echo=False,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
        )
        _factory = async_sessionmaker(_engine, expire_on_commit=False, class_=AsyncSession)
    return _engine


def _get_factory() -> async_sessionmaker[AsyncSession]:
    _get_engine()
    assert _factory is not None
    return _factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields a committed-or-rolled-back AsyncSession."""
    async with _get_factory()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def dispose_engine() -> None:
    """Gracefully close all pooled connections (call in lifespan shutdown)."""
    global _engine, _factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _factory = None
