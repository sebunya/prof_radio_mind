"""Tests for the review queue API endpoints."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.application.review.store import ReviewStore
from app.domain.entities.review_item import ReviewItem, ReviewItemStatus, ReviewItemType


@pytest.fixture(autouse=True)
def isolated_store(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace the module-level review_store with a fresh instance per test."""
    fresh = ReviewStore()
    monkeypatch.setattr("app.application.review.store.review_store", fresh)
    monkeypatch.setattr("app.api.routes.review.review_store", fresh)


@pytest.fixture
def client() -> TestClient:
    from app.main import app

    return TestClient(app)


def _make_item(
    item_type: ReviewItemType = ReviewItemType.DRIFT,
    title: str = "Test item",
) -> ReviewItem:
    return ReviewItem.create(item_type=item_type, title=title)


# --- GET /review-items ---

def test_list_review_items_empty(client: TestClient) -> None:
    r = client.get("/review-items")
    assert r.status_code == 200
    assert r.json() == []


def test_list_review_items_returns_added_item(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.api.routes import review as review_module

    item = _make_item(title="Drift detected")
    review_module.review_store.add(item)

    r = client.get("/review-items")
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    assert items[0]["title"] == "Drift detected"
    assert items[0]["status"] == "pending"


def test_list_review_items_filter_by_status(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.api.routes import review as review_module

    pending = _make_item(title="Pending item")
    resolved = _make_item(title="Resolved item")
    resolved.resolve(resolved_by="operator")
    review_module.review_store.add(pending)
    review_module.review_store.add(resolved)

    r = client.get("/review-items?status=pending")
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["title"] == "Pending item"


def test_list_review_items_invalid_status_returns_400(client: TestClient) -> None:
    r = client.get("/review-items?status=bogus")
    assert r.status_code == 400


# --- GET /review-items/{item_id} ---

def test_get_review_item_found(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.api.routes import review as review_module

    item = _make_item(title="Single item")
    review_module.review_store.add(item)

    r = client.get(f"/review-items/{item.id}")
    assert r.status_code == 200
    assert r.json()["id"] == str(item.id)
    assert r.json()["title"] == "Single item"


def test_get_review_item_not_found(client: TestClient) -> None:
    r = client.get(f"/review-items/{uuid.uuid4()}")
    assert r.status_code == 404


# --- POST /review-items/{item_id}/resolve ---

def test_resolve_pending_item_returns_200(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.api.routes import review as review_module

    item = _make_item()
    review_module.review_store.add(item)

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


def test_resolve_already_resolved_returns_409(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.api.routes import review as review_module

    item = _make_item()
    item.resolve(resolved_by="first_operator")
    review_module.review_store.add(item)

    r = client.post(
        f"/review-items/{item.id}/resolve",
        json={"resolved_by": "second_operator"},
    )
    assert r.status_code == 409


def test_resolve_nonexistent_item_returns_404(client: TestClient) -> None:
    r = client.post(
        f"/review-items/{uuid.uuid4()}/resolve",
        json={"resolved_by": "operator"},
    )
    assert r.status_code == 404


# --- POST /review-items/{item_id}/dismiss ---

def test_dismiss_pending_item_returns_200(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.api.routes import review as review_module

    item = _make_item()
    review_module.review_store.add(item)

    r = client.post(
        f"/review-items/{item.id}/dismiss",
        json={"resolved_by": "operator@example.com"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "dismissed"


def test_dismiss_nonexistent_item_returns_404(client: TestClient) -> None:
    r = client.post(
        f"/review-items/{uuid.uuid4()}/dismiss",
        json={"resolved_by": "operator"},
    )
    assert r.status_code == 404


# --- POST /review-items/{item_id}/escalate ---

def test_escalate_pending_item_returns_200(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.api.routes import review as review_module

    item = _make_item()
    review_module.review_store.add(item)

    r = client.post(
        f"/review-items/{item.id}/escalate",
        json={"resolved_by": "senior_operator"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "escalated"


# --- Domain entity tests ---

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
    store = ReviewStore()
    a = ReviewItem.create(item_type=ReviewItemType.DRIFT, title="A")
    b = ReviewItem.create(item_type=ReviewItemType.DRIFT, title="B")
    store.add(a)
    store.add(b)
    listed = store.list()
    # Newest first — b was created after a
    assert listed[0].title == "B"
    assert listed[1].title == "A"
