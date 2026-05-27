"""Tests for API key authentication."""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


def _mock_import_db():
    """Stub out the DB session factory used by the imports route."""
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()

    @asynccontextmanager
    async def _fake_ctx():
        yield mock_session

    sf = lambda: _fake_ctx()  # noqa: E731
    mock_repo = AsyncMock()
    mock_repo.save = AsyncMock()
    return (
        patch("app.api.routes.imports._get_session_factory", return_value=sf),
        patch("app.api.routes.imports.SQLCollectorRunRepository", return_value=mock_repo),
        patch("app.api.routes.imports.SQLPlayEventRepository", return_value=mock_repo),
    )


@pytest.fixture(autouse=True)
def reset_rate_limiter() -> None:
    from app.core.rate_limiter import get_limiter

    get_limiter().reset_all()


@pytest.fixture
def client() -> TestClient:
    from app.main import app

    return TestClient(app)


def test_auth_disabled_when_api_key_empty(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When API_KEY setting is empty, all requests pass through."""
    monkeypatch.setattr("app.core.settings.settings.api_key", "")
    monkeypatch.setattr("app.core.auth.settings.api_key", "")
    r = client.get("/stations")
    assert r.status_code == 200


def test_auth_allows_valid_key(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    import uuid
    from pathlib import Path

    monkeypatch.setattr("app.core.settings.settings.api_key", "secret-key-123")
    monkeypatch.setattr("app.core.auth.settings.api_key", "secret-key-123")

    csv_bytes = (Path(__file__).parent.parent / "fixtures/csv/capital_fm_valid.csv").read_bytes()
    station_id = uuid.uuid4()
    p1, p2, p3 = _mock_import_db()
    with p1, p2, p3:
        r = client.post(
            f"/manual-imports/{station_id}",
            files={"file": ("test.csv", csv_bytes, "text/csv")},
            headers={"X-API-Key": "secret-key-123"},
        )
    assert r.status_code == 201


def test_auth_rejects_wrong_key(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    import uuid

    monkeypatch.setattr("app.core.settings.settings.api_key", "secret-key-123")
    monkeypatch.setattr("app.core.auth.settings.api_key", "secret-key-123")

    r = client.post(
        f"/manual-imports/{uuid.uuid4()}",
        files={"file": ("test.csv", b"played_at,artist,title,source_type\n", "text/csv")},
        headers={"X-API-Key": "wrong-key"},
    )
    assert r.status_code == 401


def test_auth_rejects_missing_key(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    import uuid

    monkeypatch.setattr("app.core.settings.settings.api_key", "secret-key-123")
    monkeypatch.setattr("app.core.auth.settings.api_key", "secret-key-123")

    r = client.post(
        f"/manual-imports/{uuid.uuid4()}",
        files={"file": ("test.csv", b"played_at,artist,title,source_type\n", "text/csv")},
    )
    assert r.status_code == 401


def test_seeder_derives_correct_nova_source_id() -> None:
    """Seeder and scheduler must produce identical IDs for NOVA radiowave source."""
    import uuid

    from app.application.seeder import source_id_for, station_id_for

    # These must match the scheduler constants
    assert station_id_for("NOVA969") == uuid.uuid5(uuid.NAMESPACE_DNS, "station.NOVA969")
    assert source_id_for("NOVA969", "radiowave") == uuid.uuid5(
        uuid.NAMESPACE_DNS, "source.NOVA969.radiowave"
    )
    assert station_id_for("KIISFM") == uuid.uuid5(uuid.NAMESPACE_DNS, "station.KIISFM")
    assert source_id_for("KIISFM", "iheart") == uuid.uuid5(
        uuid.NAMESPACE_DNS, "source.KIISFM.iheart"
    )
