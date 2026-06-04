"""Unit tests for read-only admin console endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.settings import settings
from app.infrastructure.database.session import get_db
from app.main import app


def _mock_session(execute_result: MagicMock | None = None) -> AsyncMock:
    session = AsyncMock()
    default_result = MagicMock()
    default_result.scalar.return_value = 0
    default_result.scalar_one_or_none.return_value = None
    default_result.scalars.return_value.all.return_value = []
    default_result.all.return_value = []
    session.execute = AsyncMock(return_value=execute_result or default_result)
    return session


@pytest.fixture
def client_with_db():
    session = _mock_session()

    async def fake_db():
        yield session

    app.dependency_overrides[get_db] = fake_db
    yield TestClient(app), session
    app.dependency_overrides.clear()


# --- GET /api/admin/overview ---

def test_overview_200(client_with_db) -> None:
    client, session = client_with_db

    # Mock return values for counts
    mock_result = MagicMock()
    mock_result.scalar.side_effect = [3, 6, 2, 0]  # stations, sources, reviews, webhooks
    session.execute = AsyncMock(return_value=mock_result)

    r = client.get("/api/admin/overview")
    assert r.status_code == 200
    body = r.json()
    assert body["app_env"] == settings.app_env
    assert body["stats"]["active_stations"] == 3
    assert body["stats"]["total_sources"] == 6
    assert body["stats"]["pending_reviews"] == 2


# --- GET /api/admin/operations ---

def test_operations_200(client_with_db) -> None:
    client, _ = client_with_db
    r = client.get("/api/admin/operations")
    assert r.status_code == 200
    body = r.json()
    assert "scheduler_enabled" in body
    assert "raw_payload_retention_days" in body
    assert body["db_migration_version"] == "c4e2a1f9b8d7"


# --- GET /api/admin/recent-events ---

def test_recent_events_200(client_with_db) -> None:
    client, session = client_with_db

    # Mock the return list of recent events
    mock_event = MagicMock()
    mock_event.id = uuid.uuid4()
    mock_event.raw_artist = "Sabrina Carpenter"
    mock_event.raw_title = "Espresso"
    mock_event.played_at = datetime.now(UTC)
    mock_event.is_duplicate = False
    mock_event.fingerprint = "abcdef123"

    mock_station = MagicMock()
    mock_station.name = "Capital FM UK"
    mock_station.call_sign = "CAPITALFM"

    mock_result = MagicMock()
    mock_result.all.return_value = [(mock_event, mock_station)]
    session.execute = AsyncMock(return_value=mock_result)

    r = client.get("/api/admin/recent-events")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["raw_artist"] == "Sabrina Carpenter"
    assert body[0]["station_call_sign"] == "CAPITALFM"


# --- GET /api/admin/source-health ---

def test_source_health_200(client_with_db) -> None:
    client, session = client_with_db

    # Mock the return list of sources and their relations
    mock_source = MagicMock()
    mock_source.id = uuid.uuid4()
    mock_source.station_id = uuid.uuid4()
    mock_source.source_type = "iheart"
    mock_source.name = "KIIS iHeart source"
    mock_source.base_url = "https://api.iheart.com"
    mock_source.is_active = True

    mock_station = MagicMock()
    mock_station.call_sign = "KIISFM"

    mock_result_sources = MagicMock()
    mock_result_sources.all.return_value = [(mock_source, mock_station)]

    # execute side effects:
    # 1. Sources query
    # 2. Priority query
    # 3. Validation query
    mock_priority = MagicMock()
    mock_priority.scalar.return_value = 1

    mock_validation = MagicMock()
    mock_validation_row = MagicMock()
    mock_validation_row.status = "validated"
    mock_validation_row.validation_code = "VAL-KIIS-001"
    mock_validation_row.validated_at = datetime.now(UTC)
    mock_validation_row.response_status_code = 200
    mock_validation.scalar_one_or_none.return_value = mock_validation_row

    session.execute = AsyncMock(side_effect=[
        mock_result_sources,
        mock_priority,
        mock_validation
    ])

    r = client.get("/api/admin/source-health")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["station_call_sign"] == "KIISFM"
    assert body[0]["priority"] == 1
    assert body[0]["latest_validation_status"] == "validated"


# --- GET /api/admin/review-summary ---

def test_review_summary_200(client_with_db) -> None:
    client, session = client_with_db

    mock_result = MagicMock()
    mock_result.all.return_value = [("pending", 3), ("reviewed", 5)]
    session.execute = AsyncMock(return_value=mock_result)

    r = client.get("/api/admin/review-summary")
    assert r.status_code == 200
    body = r.json()
    assert body["pending"] == 3
    assert body["reviewed"] == 5
    assert body["dismissed"] == 0
    assert body["escalated"] == 0


# --- GET /api/admin/enrichment-status ---

def test_enrichment_status_200(client_with_db) -> None:
    client, session = client_with_db

    mock_result = MagicMock()
    mock_result.scalar.return_value = 42  # total songs captured
    session.execute = AsyncMock(return_value=mock_result)

    r = client.get("/api/admin/enrichment-status")
    assert r.status_code == 200
    body = r.json()
    expected_enabled = settings.spotify_metadata_enrichment_enabled
    assert body["spotify_metadata_enrichment_enabled"] == expected_enabled
    assert body["counts"]["not_configured"] == 0
    assert body["counts"]["pending"] == 42
    assert body["counts"]["matched"] == 42
    assert body["counts"]["failed"] == 42


# --- GET /api/admin/spotify-readiness ---

def test_spotify_readiness_200(client_with_db, monkeypatch) -> None:
    client, _ = client_with_db

    # Override settings for testing
    monkeypatch.setattr(settings, "spotify_client_id", "my-client-id")
    monkeypatch.setattr(settings, "spotify_client_secret", "super-secret-key-do-not-reveal")

    r = client.get("/api/admin/spotify-readiness")
    assert r.status_code == 200
    body = r.json()
    assert body["client_id_configured"] is True
    assert body["client_secret_configured"] is True
    # The client secret must NOT be in the body
    assert "client_secret" not in body
    assert "super-secret-key" not in str(body)


# --- GET /api/admin/collector-runs ---

def test_collector_runs_200(client_with_db) -> None:
    client, session = client_with_db

    mock_run = MagicMock()
    mock_run.id = uuid.uuid4()
    mock_run.status = "completed"
    mock_run.error_message = None
    mock_run.started_at = datetime.now(UTC)
    mock_run.completed_at = datetime.now(UTC)

    mock_station = MagicMock()
    mock_station.call_sign = "CAPITALFM"

    mock_result = MagicMock()
    mock_result.all.return_value = [(mock_run, mock_station)]
    session.execute = AsyncMock(return_value=mock_result)

    r = client.get("/api/admin/collector-runs")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["status"] == "completed"
    assert body[0]["station_call_sign"] == "CAPITALFM"
