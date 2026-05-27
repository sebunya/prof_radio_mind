"""Tests for all MVP API endpoints."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

_VALID_CSV = Path(__file__).parent.parent / "fixtures/csv/capital_fm_valid.csv"
_ERRORS_CSV = Path(__file__).parent.parent / "fixtures/csv/capital_fm_with_errors.csv"


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


class _MockDbSession:
    """Context manager that stubs the DB session factory + repo constructors used by imports."""

    def __enter__(self):
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        @asynccontextmanager
        async def _fake_ctx():
            yield mock_session

        session_factory = lambda: _fake_ctx()  # noqa: E731
        mock_repo = AsyncMock()
        mock_repo.save = AsyncMock()

        # imports.py binds these at module level, so patch where they're *used*
        self._patches = [
            patch("app.api.routes.imports._get_session_factory",
                  return_value=session_factory),
            patch("app.api.routes.imports.SQLCollectorRunRepository",
                  return_value=mock_repo),
            patch("app.api.routes.imports.SQLPlayEventRepository",
                  return_value=mock_repo),
        ]
        for p in self._patches:
            p.start()
        return self

    def __exit__(self, *_):
        for p in self._patches:
            p.stop()


def _mock_db_session():
    return _MockDbSession()


# --- GET /health ---

def test_health_200(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# --- GET /stations ---

def test_list_stations_200(client: TestClient) -> None:
    r = client.get("/stations")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_list_stations_contains_nova(client: TestClient) -> None:
    r = client.get("/stations")
    call_signs = [s["call_sign"] for s in r.json()]
    assert "NOVA969" in call_signs


def test_list_stations_contains_kiis(client: TestClient) -> None:
    r = client.get("/stations")
    call_signs = [s["call_sign"] for s in r.json()]
    assert "KIISFM" in call_signs


def test_list_stations_contains_capital(client: TestClient) -> None:
    r = client.get("/stations")
    call_signs = [s["call_sign"] for s in r.json()]
    assert "CAPITALFM" in call_signs


def test_station_has_required_fields(client: TestClient) -> None:
    r = client.get("/stations")
    station = r.json()[0]
    assert "call_sign" in station
    assert "name" in station
    assert "frequency" in station


# --- POST /manual-imports/{station_id} ---

def test_import_valid_csv_returns_201(client: TestClient) -> None:
    station_id = uuid.uuid4()
    with _mock_db_session():
        r = client.post(
            f"/manual-imports/{station_id}",
            files={"file": ("capital_fm_valid.csv", _VALID_CSV.read_bytes(), "text/csv")},
        )
    assert r.status_code == 201


def test_import_valid_csv_response_shape(client: TestClient) -> None:
    station_id = uuid.uuid4()
    with _mock_db_session():
        r = client.post(
            f"/manual-imports/{station_id}",
            files={"file": ("capital_fm_valid.csv", _VALID_CSV.read_bytes(), "text/csv")},
        )
    body = r.json()
    assert "batch_id" in body
    assert "imported_rows" in body
    assert body["imported_rows"] == 5


def test_import_csv_with_errors_returns_201_partial(client: TestClient) -> None:
    station_id = uuid.uuid4()
    with _mock_db_session():
        r = client.post(
            f"/manual-imports/{station_id}",
            files={"file": ("errors.csv", _ERRORS_CSV.read_bytes(), "text/csv")},
        )
    assert r.status_code == 201
    body = r.json()
    assert body["error_rows"] > 0
    assert body["imported_rows"] > 0


def test_import_non_csv_returns_400(client: TestClient) -> None:
    station_id = uuid.uuid4()
    r = client.post(
        f"/manual-imports/{station_id}",
        files={"file": ("data.txt", b"not a csv", "text/plain")},
    )
    assert r.status_code == 400


def test_import_empty_file_returns_400(client: TestClient) -> None:
    station_id = uuid.uuid4()
    r = client.post(
        f"/manual-imports/{station_id}",
        files={"file": ("empty.csv", b"", "text/csv")},
    )
    assert r.status_code == 400


def test_import_missing_columns_returns_422(client: TestClient) -> None:
    station_id = uuid.uuid4()
    bad_csv = b"artist,title\nDoja Cat,Paint The Town Red\n"
    r = client.post(
        f"/manual-imports/{station_id}",
        files={"file": ("bad.csv", bad_csv, "text/csv")},
    )
    assert r.status_code == 422
