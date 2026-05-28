"""Tests for the review queue API endpoints (DB-backed, mocked session)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.domain.entities.review_item import ReviewItem, ReviewItemStatus, ReviewItemType


def _make_item(
    item_type: ReviewItemType = ReviewItemType.DRIFT,
    title: str = "Test item",
) -> ReviewItem:
    return ReviewItem.create(item_type=item_type, title=title)


def _make_mock_repo(items: list[ReviewItem] | None = None) -> AsyncMock:
    items = items or []
    repo = AsyncMock()
    repo.list.return_value = items
    repo.list_page.return_value = (items, len(items))
    repo.get.side_effect = lambda item_id: next(
        (i for i in items if i.id == item_id), None
    )
    repo.add = AsyncMock()
    repo.update = AsyncMock()
    repo.count_pending.return_value = 0
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


# --- GET /review-items ---

def test_list_review_items_empty(client: TestClient) -> None:
    with patch(
        "app.api.routes.review.SQLReviewItemRepository",
        return_value=_make_mock_repo([]),
    ):
        r = client.get("/review-items")
    assert r.status_code == 200
    assert r.json() == []


def test_list_review_items_returns_added_item(client: TestClient) -> None:
    item = _make_item(title="Drift detected")
    with patch(
        "app.api.routes.review.SQLReviewItemRepository",
        return_value=_make_mock_repo([item]),
    ):
        r = client.get("/review-items")
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    assert items[0]["title"] == "Drift detected"
    assert items[0]["status"] == "pending"


def test_list_review_items_filter_by_status(client: TestClient) -> None:
    pending = _make_item(title="Pending item")
    mock_repo = _make_mock_repo([pending])

    with patch("app.api.routes.review.SQLReviewItemRepository", return_value=mock_repo):
        r = client.get("/review-items?status=pending")
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["title"] == "Pending item"


def test_list_review_items_invalid_status_returns_400(client: TestClient) -> None:
    with patch(
        "app.api.routes.review.SQLReviewItemRepository",
        return_value=_make_mock_repo([]),
    ):
        r = client.get("/review-items?status=bogus")
    assert r.status_code == 400


# --- GET /review-items/{item_id} ---

def test_get_review_item_found(client: TestClient) -> None:
    item = _make_item(title="Single item")
    with patch(
        "app.api.routes.review.SQLReviewItemRepository",
        return_value=_make_mock_repo([item]),
    ):
        r = client.get(f"/review-items/{item.id}")
    assert r.status_code == 200
    assert r.json()["id"] == str(item.id)
    assert r.json()["title"] == "Single item"


def test_get_review_item_not_found(client: TestClient) -> None:
    with patch(
        "app.api.routes.review.SQLReviewItemRepository",
        return_value=_make_mock_repo([]),
    ):
        r = client.get(f"/review-items/{uuid.uuid4()}")
    assert r.status_code == 404


# --- POST /review-items/{item_id}/resolve ---

def test_resolve_pending_item_returns_200(client: TestClient) -> None:
    item = _make_item()
    mock_repo = _make_mock_repo([item])

    def fake_update(updated_item: ReviewItem) -> None:
        items = [updated_item if i.id == updated_item.id else i for i in [item]]
        mock_repo.list.return_value = items

    mock_repo.update = AsyncMock(side_effect=fake_update)

    with patch("app.api.routes.review.SQLReviewItemRepository", return_value=mock_repo):
        r = client.post(
            f"/review-items/{item.id}/resolve",
            json={"resolved_by": "operator@example.com", "notes": "Confirmed correct"},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "reviewed"
    assert body["resolved_by"] == "operator@example.com"
    assert body["notes"] == "Confirmed correct"
    assert body["resolved_at"] is not None


def test_resolve_already_resolved_returns_409(client: TestClient) -> None:
    item = _make_item()
    item.resolve(resolved_by="first_operator")
    with patch(
        "app.api.routes.review.SQLReviewItemRepository",
        return_value=_make_mock_repo([item]),
    ):
        r = client.post(
            f"/review-items/{item.id}/resolve",
            json={"resolved_by": "second_operator"},
        )
    assert r.status_code == 409


def test_resolve_nonexistent_item_returns_404(client: TestClient) -> None:
    with patch(
        "app.api.routes.review.SQLReviewItemRepository",
        return_value=_make_mock_repo([]),
    ):
        r = client.post(
            f"/review-items/{uuid.uuid4()}/resolve",
            json={"resolved_by": "operator"},
        )
    assert r.status_code == 404


# --- POST /review-items/{item_id}/dismiss ---

def test_dismiss_pending_item_returns_200(client: TestClient) -> None:
    item = _make_item()
    with patch(
        "app.api.routes.review.SQLReviewItemRepository",
        return_value=_make_mock_repo([item]),
    ):
        r = client.post(
            f"/review-items/{item.id}/dismiss",
            json={"resolved_by": "operator@example.com"},
        )
    assert r.status_code == 200
    assert r.json()["status"] == "dismissed"


def test_dismiss_nonexistent_item_returns_404(client: TestClient) -> None:
    with patch(
        "app.api.routes.review.SQLReviewItemRepository",
        return_value=_make_mock_repo([]),
    ):
        r = client.post(
            f"/review-items/{uuid.uuid4()}/dismiss",
            json={"resolved_by": "operator"},
        )
    assert r.status_code == 404


# --- POST /review-items/{item_id}/escalate ---

def test_escalate_pending_item_returns_200(client: TestClient) -> None:
    item = _make_item()
    with patch(
        "app.api.routes.review.SQLReviewItemRepository",
        return_value=_make_mock_repo([item]),
    ):
        r = client.post(
            f"/review-items/{item.id}/escalate",
            json={"resolved_by": "senior_operator"},
        )
    assert r.status_code == 200
    assert r.json()["status"] == "escalated"


# --- Domain entity tests (no HTTP, no DB) ---

def test_review_item_create_is_pending() -> None:
    item = ReviewItem.create(item_type=ReviewItemType.DRIFT, title="Test")
    assert item.status == ReviewItemStatus.PENDING
    assert item.is_open is True


def test_review_item_resolve_closes_item() -> None:
    item = ReviewItem.create(item_type=ReviewItemType.PARSE_ERROR, title="Parse failed")
    item.resolve(resolved_by="ops@example.com", notes="Fixed upstream")
    assert item.status == ReviewItemStatus.REVIEWED
    assert item.is_open is False
    assert item.resolved_by == "ops@example.com"
    assert item.notes == "Fixed upstream"
    assert item.resolved_at is not None


def test_review_item_dismiss_closes_item() -> None:
    item = ReviewItem.create(item_type=ReviewItemType.LOW_CONFIDENCE, title="Low conf")
    item.dismiss(resolved_by="ops@example.com")
    assert item.status == ReviewItemStatus.DISMISSED
    assert item.is_open is False


def test_review_store_list_sorted_newest_first() -> None:
    from app.application.review.store import ReviewStore

    store = ReviewStore()
    a = ReviewItem.create(item_type=ReviewItemType.DRIFT, title="A")
    b = ReviewItem.create(item_type=ReviewItemType.DRIFT, title="B")
    store.add(a)
    store.add(b)
    listed = store.list()
    assert listed[0].title == "B"
    assert listed[1].title == "A"
