"""Tests for all MVP API endpoints."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

_VALID_CSV = Path(__file__).parent.parent / "fixtures/csv/capital_fm_valid.csv"
_ERRORS_CSV = Path(__file__).parent.parent / "fixtures/csv/capital_fm_with_errors.csv"


@pytest.fixture
def client():
    from unittest.mock import AsyncMock, MagicMock, patch

    from app.domain.entities.station import Station
    from app.infrastructure.database.session import get_db

    async def fake_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = fake_db

    mock_stations = [
        Station(
            id=uuid.uuid4(),
            name="Nova 96.9",
            call_sign="NOVA969",
            frequency="96.9 FM",
            city="Sydney",
            country_code="AU",
            is_active=True,
        ),
        Station(
            id=uuid.uuid4(),
            name="KIIS-FM",
            call_sign="KIISFM",
            frequency="106.5 FM",
            city="Sydney",
            country_code="AU",
            is_active=True,
        ),
        Station(
            id=uuid.uuid4(),
            name="Capital FM UK",
            call_sign="CAPITALFM",
            frequency="95.8 FM",
            city="London",
            country_code="GB",
            is_active=True,
        ),
    ]
    mock_repo = AsyncMock()
    mock_repo.list_active.return_value = mock_stations

    patcher = patch(
        "app.infrastructure.database.repositories.station_repo.SQLStationRepository",
        return_value=mock_repo,
    )
    patcher.start()

    yield TestClient(app)

    patcher.stop()
    app.dependency_overrides.clear()



# --- GET / ---

def test_root_landing_200(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["service"] == "TenX Radar"
    assert body["endpoints"]["health"] == "/health"
    assert body["endpoints"]["admin"] == "/admin"
    assert body["endpoints"]["api_docs"] == "/docs"


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
    r = client.post(
        f"/manual-imports/{station_id}",
        files={"file": ("capital_fm_valid.csv", _VALID_CSV.read_bytes(), "text/csv")},
    )
    assert r.status_code == 201


def test_import_valid_csv_response_shape(client: TestClient) -> None:
    station_id = uuid.uuid4()
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
