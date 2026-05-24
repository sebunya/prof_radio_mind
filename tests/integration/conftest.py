"""Integration test fixtures — require a real PostgreSQL database.

These tests are SKIPPED by default unless the environment variable
RMIAS_INTEGRATION_TESTS=1 is set and a live database is reachable via
DATABASE_URL (or the default postgresql+asyncpg://rmias:rmias@localhost:5432/rmias_test).

To run locally:
    docker run -d -e POSTGRES_DB=rmias_test -e POSTGRES_USER=rmias \\
               -e POSTGRES_PASSWORD=rmias -p 5432:5432 postgres:16-alpine
    RMIAS_INTEGRATION_TESTS=1 pytest tests/integration/ -v
"""

from __future__ import annotations

import os

import pytest

_ENABLED = os.getenv("RMIAS_INTEGRATION_TESTS", "0") == "1"

skip_if_no_db = pytest.mark.skipif(
    not _ENABLED,
    reason="Set RMIAS_INTEGRATION_TESTS=1 and ensure PostgreSQL is running",
)


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="session")
async def db_engine():  # type: ignore[return]
    """Create a test database engine and run all Alembic migrations."""
    if not _ENABLED:
        pytest.skip("integration tests disabled")

    import os

    from sqlalchemy.ext.asyncio import create_async_engine

    test_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://rmias:rmias@localhost:5432/rmias_test",
    )
    engine = create_async_engine(test_url, echo=False)

    # Apply migrations via Alembic
    import subprocess

    subprocess.run(
        ["alembic", "upgrade", "head"],
        env={**os.environ, "DATABASE_URL": test_url.replace("postgresql+asyncpg://", "postgresql://")},
        check=True,
    )

    yield engine

    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):  # type: ignore[return]
    """Provide a transactional session that rolls back after each test."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    factory = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        yield session
        await session.rollback()
