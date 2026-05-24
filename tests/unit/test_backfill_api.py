"""Tests for the historical backfill API endpoint."""

from __future__ import annotations

import io
import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


def _csv_bytes(rows: list[str], header: str = "artist,title,played_at") -> bytes:
    content = header + "\n" + "\n".join(rows)
    return content.encode("utf-8")


@pytest.fixture
def client():
    from app.infrastructure.database.session import get_db

    async def fake_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = fake_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def _db_patches():
    """Return (mock_play_repo, mock_review_repo, mock_session, factory_patch, play_patch, review_patch).

    The backfill handler calls: _factory()() where _factory = _get_factory.
    So _get_factory() must return a session-factory callable, and calling that must
    return an async context manager that yields the mock session.
    """
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_play_repo = AsyncMock()
    mock_play_repo.save = AsyncMock()
    mock_review_repo = AsyncMock()
    mock_review_repo.add = AsyncMock()

    @asynccontextmanager
    async def fake_ctx():
        yield mock_session

    # _get_factory() → session_factory; session_factory() → async_ctx_mgr
    session_factory = lambda: fake_ctx()  # noqa: E731

    return (
        mock_play_repo,
        mock_review_repo,
        mock_session,
        patch("app.infrastructure.database.session._get_factory", return_value=session_factory),
        patch("app.infrastructure.database.repositories.play_event_repo.SQLPlayEventRepository", return_value=mock_play_repo),
        patch("app.infrastructure.database.repositories.review_item_repo.SQLReviewItemRepository", return_value=mock_review_repo),
    )


def test_backfill_file_too_large_returns_413(client: TestClient) -> None:
    # Slightly over the 10 MB limit — size check fires before CSV parsing
    big_data = b"x" * (10 * 1024 * 1024 + 1)
    response = client.post(
        f"/backfill/{uuid.uuid4()}?broadcast_date=2026-05-24",
        files={"file": ("plays.csv", io.BytesIO(big_data), "text/csv")},
    )
    assert response.status_code == 413


def test_backfill_missing_played_at_column_returns_422(client: TestClient) -> None:
    csv_data = b"artist,title\nArtist,Song\n"
    response = client.post(
        f"/backfill/{uuid.uuid4()}?broadcast_date=2026-05-24",
        files={"file": ("plays.csv", io.BytesIO(csv_data), "text/csv")},
    )
    assert response.status_code == 422
    assert "played_at" in response.json()["detail"]


def test_backfill_empty_csv_no_headers_returns_422(client: TestClient) -> None:
    response = client.post(
        f"/backfill/{uuid.uuid4()}?broadcast_date=2026-05-24",
        files={"file": ("plays.csv", io.BytesIO(b""), "text/csv")},
    )
    assert response.status_code == 422


def test_backfill_all_invalid_rows_returns_422(client: TestClient) -> None:
    csv_data = _csv_bytes(
        [",,10:00:00", ",,11:00:00"],
        header="artist,title,played_at",
    )
    response = client.post(
        f"/backfill/{uuid.uuid4()}?broadcast_date=2026-05-24",
        files={"file": ("plays.csv", io.BytesIO(csv_data), "text/csv")},
    )
    assert response.status_code == 422


def test_backfill_valid_csv_returns_200(client: TestClient) -> None:
    station_id = uuid.uuid4()
    csv_data = _csv_bytes([
        "Taylor Swift,Shake It Off,10:30:00",
        "The Weeknd,Blinding Lights,11:00:00",
    ])

    mock_play_repo, mock_review_repo, _, factory_patch, play_patch, review_patch = _db_patches()

    with factory_patch, play_patch, review_patch:
        response = client.post(
            f"/backfill/{station_id}?broadcast_date=2026-05-24",
            files={"file": ("plays.csv", io.BytesIO(csv_data), "text/csv")},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["rows_submitted"] == 2
    assert body["rows_accepted"] == 2
    assert body["rows_rejected"] == 0
    assert body["station_id"] == str(station_id)
    assert body["broadcast_date"] == "2026-05-24"
    assert "review_item_id" in body


def test_backfill_duplicate_fingerprints_skipped(client: TestClient) -> None:
    csv_data = _csv_bytes([
        "Artist A,Song X,10:00:00",
        "Artist A,Song X,11:00:00",  # duplicate fingerprint
    ])

    mock_play_repo, mock_review_repo, _, factory_patch, play_patch, review_patch = _db_patches()

    with factory_patch, play_patch, review_patch:
        response = client.post(
            f"/backfill/{uuid.uuid4()}?broadcast_date=2026-05-24",
            files={"file": ("plays.csv", io.BytesIO(csv_data), "text/csv")},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["rows_submitted"] == 2
    assert body["rows_accepted"] == 1
    assert body["rows_rejected"] == 1


def test_backfill_invalid_played_at_rejected(client: TestClient) -> None:
    # Only one row with bad time, plus one valid row so we don't get 422
    csv_data = _csv_bytes([
        "Artist,Song,not-a-time",
        "Valid Artist,Valid Song,10:00:00",
    ])

    mock_play_repo, mock_review_repo, _, factory_patch, play_patch, review_patch = _db_patches()

    with factory_patch, play_patch, review_patch:
        response = client.post(
            f"/backfill/{uuid.uuid4()}?broadcast_date=2026-05-24",
            files={"file": ("plays.csv", io.BytesIO(csv_data), "text/csv")},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["rows_accepted"] == 1
    assert body["rows_rejected"] == 1
    assert any("invalid played_at" in r for r in body["rejection_reasons"])


def test_backfill_iso8601_played_at_accepted(client: TestClient) -> None:
    csv_data = _csv_bytes(["Artist,Song,2026-05-24T10:30:00"])

    mock_play_repo, mock_review_repo, _, factory_patch, play_patch, review_patch = _db_patches()

    with factory_patch, play_patch, review_patch:
        response = client.post(
            f"/backfill/{uuid.uuid4()}?broadcast_date=2026-05-24",
            files={"file": ("plays.csv", io.BytesIO(csv_data), "text/csv")},
        )

    assert response.status_code == 200
    assert response.json()["rows_accepted"] == 1


def test_backfill_saves_play_events_to_db(client: TestClient) -> None:
    csv_data = _csv_bytes([
        "Artist A,Song X,10:00:00",
        "Artist B,Song Y,11:00:00",
    ])

    mock_play_repo, mock_review_repo, _, factory_patch, play_patch, review_patch = _db_patches()

    with factory_patch, play_patch, review_patch:
        response = client.post(
            f"/backfill/{uuid.uuid4()}?broadcast_date=2026-05-24",
            files={"file": ("plays.csv", io.BytesIO(csv_data), "text/csv")},
        )

    assert response.status_code == 200
    assert mock_play_repo.save.call_count == 2


def test_backfill_creates_review_item(client: TestClient) -> None:
    csv_data = _csv_bytes(["Artist,Song,10:00:00"])

    mock_play_repo, mock_review_repo, _, factory_patch, play_patch, review_patch = _db_patches()

    with factory_patch, play_patch, review_patch:
        response = client.post(
            f"/backfill/{uuid.uuid4()}?broadcast_date=2026-05-24",
            files={"file": ("plays.csv", io.BytesIO(csv_data), "text/csv")},
        )

    assert response.status_code == 200
    mock_review_repo.add.assert_called_once()
