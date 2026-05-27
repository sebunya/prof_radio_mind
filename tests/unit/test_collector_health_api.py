"""Tests for GET /collector-runs/* endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


def _make_run(status: str = "completed") -> MagicMock:
    run = MagicMock()
    run.id = uuid.uuid4()
    run.station_id = uuid.uuid4()
    run.source_id = uuid.uuid4()
    run.status = status
    run.started_at = datetime(2025, 5, 27, 10, 0, tzinfo=UTC)
    run.completed_at = datetime(2025, 5, 27, 10, 1, tzinfo=UTC)
    run.rows_fetched = 100
    run.rows_parsed = 98
    run.rows_persisted = 95
    run.error_message = None
    run.created_at = datetime(2025, 5, 27, 10, 0, tzinfo=UTC)
    return run


def _make_mock_repo(runs=None, summary=None):
    repo = AsyncMock()
    runs = runs or []
    repo.list_page.return_value = (runs, len(runs))
    repo.summary.return_value = summary or {
        "last_completed_at": None,
        "last_completed_run_id": None,
        "runs_today": 0,
        "running_count": 0,
        "success_rate_24h": None,
        "last_failed_at": None,
        "last_error_message": None,
    }
    return repo


@pytest.fixture
def client():
    from app.infrastructure.database.session import get_db
    from app.main import app

    async def fake_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = fake_db
    yield TestClient(app)
    app.dependency_overrides.clear()


# ── GET /collector-runs/summary ──────────────────────────────────


def test_summary_returns_200(client: TestClient) -> None:
    with patch(
        "app.infrastructure.database.repositories.collector_run_repo.SQLCollectorRunRepository",
        return_value=_make_mock_repo(),
    ):
        r = client.get("/collector-runs/summary")
    assert r.status_code == 200
    body = r.json()
    assert "runs_today" in body
    assert "running_count" in body
    assert "success_rate_24h" in body


def test_summary_populates_fields(client: TestClient) -> None:
    summary = {
        "last_completed_at": "2025-05-27T10:00:00+00:00",
        "last_completed_run_id": str(uuid.uuid4()),
        "runs_today": 12,
        "running_count": 2,
        "success_rate_24h": 92,
        "last_failed_at": None,
        "last_error_message": None,
    }
    with patch(
        "app.infrastructure.database.repositories.collector_run_repo.SQLCollectorRunRepository",
        return_value=_make_mock_repo(summary=summary),
    ):
        r = client.get("/collector-runs/summary")
    assert r.status_code == 200
    body = r.json()
    assert body["runs_today"] == 12
    assert body["running_count"] == 2
    assert body["success_rate_24h"] == 92


# ── GET /collector-runs ───────────────────────────────────────────


def test_list_runs_empty(client: TestClient) -> None:
    with patch(
        "app.infrastructure.database.repositories.collector_run_repo.SQLCollectorRunRepository",
        return_value=_make_mock_repo([]),
    ):
        r = client.get("/collector-runs")
    assert r.status_code == 200
    assert r.json() == []
    assert r.headers["X-Total-Count"] == "0"


def test_list_runs_returns_items(client: TestClient) -> None:
    run = _make_run("completed")
    with patch(
        "app.infrastructure.database.repositories.collector_run_repo.SQLCollectorRunRepository",
        return_value=_make_mock_repo([run]),
    ):
        r = client.get("/collector-runs")
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["status"] == "completed"
    assert r.headers["X-Total-Count"] == "1"


def test_list_runs_pagination_params_forwarded(client: TestClient) -> None:
    repo = _make_mock_repo([])
    with patch(
        "app.infrastructure.database.repositories.collector_run_repo.SQLCollectorRunRepository",
        return_value=repo,
    ):
        r = client.get("/collector-runs?limit=10&offset=20&status=failed")
    assert r.status_code == 200
    repo.list_page.assert_called_once_with(
        status="failed", station_id=None, limit=10, offset=20
    )


def test_list_runs_invalid_limit_rejected(client: TestClient) -> None:
    with patch(
        "app.infrastructure.database.repositories.collector_run_repo.SQLCollectorRunRepository",
        return_value=_make_mock_repo([]),
    ):
        r = client.get("/collector-runs?limit=9999")
    assert r.status_code == 422


# ── GET /collector-runs/{run_id} ─────────────────────────────────


def test_get_run_not_found(client: TestClient) -> None:
    missing_id = uuid.uuid4()

    async def fake_get(model, run_id):
        return None

    with patch(
        "app.infrastructure.database.repositories.collector_run_repo.SQLCollectorRunRepository",
        return_value=_make_mock_repo(),
    ):
        client.app.dependency_overrides
        from app.infrastructure.database.session import get_db
        from app.main import app

        original_db = app.dependency_overrides.get(get_db)

        async def fake_db_with_get():
            sess = MagicMock()
            sess.get = AsyncMock(return_value=None)
            yield sess

        app.dependency_overrides[get_db] = fake_db_with_get
        r = client.get(f"/collector-runs/{missing_id}")
        if original_db:
            app.dependency_overrides[get_db] = original_db

    assert r.status_code == 404


# ── Rate limiting — middleware covers /collector-runs ─────────────


def test_rate_limit_429_after_threshold(client: TestClient) -> None:
    from app.core.rate_limiter import get_limiter

    # Exhaust the limiter for this IP
    limiter = get_limiter()
    for _ in range(limiter._max_requests + 5):
        limiter.is_allowed("testclient")

    with patch(
        "app.infrastructure.database.repositories.collector_run_repo.SQLCollectorRunRepository",
        return_value=_make_mock_repo(),
    ):
        r = client.get("/collector-runs/summary")
    assert r.status_code == 429
    assert "Retry-After" in r.headers
