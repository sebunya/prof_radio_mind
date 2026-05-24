"""Tests for input validation hardening and rate-limiter scaffold."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.rate_limiter import InMemoryRateLimiter

_VALID_CSV = Path(__file__).parent.parent / "fixtures/csv/capital_fm_valid.csv"


@pytest.fixture
def client() -> TestClient:
    from unittest.mock import AsyncMock, MagicMock

    from app.infrastructure.database.session import get_db
    from app.main import app

    async def fake_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = fake_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def reset_rate_limiter() -> None:
    from app.core.rate_limiter import get_limiter

    get_limiter().reset_all()


# --- InMemoryRateLimiter unit tests ---

def test_rate_limiter_allows_under_limit() -> None:
    limiter = InMemoryRateLimiter(max_requests=3, window_seconds=60)
    assert limiter.is_allowed("192.168.1.1") is True
    assert limiter.is_allowed("192.168.1.1") is True
    assert limiter.is_allowed("192.168.1.1") is True


def test_rate_limiter_blocks_over_limit() -> None:
    limiter = InMemoryRateLimiter(max_requests=2, window_seconds=60)
    limiter.is_allowed("10.0.0.1")
    limiter.is_allowed("10.0.0.1")
    assert limiter.is_allowed("10.0.0.1") is False


def test_rate_limiter_independent_keys() -> None:
    limiter = InMemoryRateLimiter(max_requests=1, window_seconds=60)
    limiter.is_allowed("ip_a")
    assert limiter.is_allowed("ip_a") is False
    # A different key is unaffected
    assert limiter.is_allowed("ip_b") is True


def test_rate_limiter_reset_clears_key() -> None:
    limiter = InMemoryRateLimiter(max_requests=1, window_seconds=60)
    limiter.is_allowed("10.0.0.2")
    limiter.reset("10.0.0.2")
    assert limiter.is_allowed("10.0.0.2") is True


def test_rate_limiter_window_expiry() -> None:
    limiter = InMemoryRateLimiter(max_requests=1, window_seconds=1)
    limiter.is_allowed("host")
    assert limiter.is_allowed("host") is False
    # Expire the window by patching time
    bucket = limiter._buckets["host"]
    limiter._buckets["host"] = [t - 2 for t in bucket]  # backdate by 2s
    assert limiter.is_allowed("host") is True


# --- Import endpoint security ---

def test_import_oversized_file_returns_413(client: TestClient) -> None:
    station_id = uuid.uuid4()
    big_csv = b"played_at,artist,title,source_type\n" + b"x" * (11 * 1024 * 1024)
    r = client.post(
        f"/manual-imports/{station_id}",
        files={"file": ("big.csv", big_csv, "text/csv")},
    )
    assert r.status_code == 413


def test_import_invalid_content_type_returns_400(client: TestClient) -> None:
    station_id = uuid.uuid4()
    r = client.post(
        f"/manual-imports/{station_id}",
        files={"file": ("data.csv", b"played_at,artist,title,source_type\n", "application/json")},
    )
    assert r.status_code == 400


# --- Review endpoint validation ---

def test_resolve_empty_resolved_by_returns_422(client: TestClient) -> None:
    import uuid

    r = client.post(
        f"/review-items/{uuid.uuid4()}/resolve",
        json={"resolved_by": ""},
    )
    assert r.status_code == 422


def test_resolve_too_long_resolved_by_returns_422(client: TestClient) -> None:
    import uuid

    r = client.post(
        f"/review-items/{uuid.uuid4()}/resolve",
        json={"resolved_by": "x" * 256},
    )
    assert r.status_code == 422


# --- Rate limiter integration via API ---

def test_rate_limited_endpoint_returns_429_when_exceeded(client: TestClient) -> None:
    from app.core.rate_limiter import get_limiter
    from app.core.settings import settings

    limiter = get_limiter()
    station_id = uuid.uuid4()

    # Exhaust the limit for testclient's loopback IP
    for _ in range(settings.rate_limit_rpm):
        limiter.is_allowed("testclient")

    r = client.post(
        f"/manual-imports/{station_id}",
        files={"file": ("test.csv", _VALID_CSV.read_bytes(), "text/csv")},
    )
    # TestClient uses "testclient" as host — already exhausted above
    assert r.status_code == 429
