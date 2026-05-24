"""In-memory ReviewStore — MVP replacement for DB-backed persistence.

Swapped out for a SQLAlchemy repository in Pass 22 when the async DB session
is wired. All write operations are safe for single-process async use.
"""

from __future__ import annotations

import uuid

from app.domain.entities.review_item import ReviewItem, ReviewItemStatus


class ReviewStore:
    """Thread-safe in-memory store for ReviewItems."""

    def __init__(self) -> None:
        self._items: dict[uuid.UUID, ReviewItem] = {}

    def add(self, item: ReviewItem) -> None:
        self._items[item.id] = item

    def get(self, item_id: uuid.UUID) -> ReviewItem | None:
        return self._items.get(item_id)

    def list(self, status: ReviewItemStatus | None = None) -> list[ReviewItem]:
        items = list(self._items.values())
        if status is not None:
            items = [i for i in items if i.status == status]
        return sorted(items, key=lambda i: i.created_at, reverse=True)

    def update(self, item: ReviewItem) -> None:
        self._items[item.id] = item

    def __len__(self) -> int:
        return len(self._items)


# Module-level singleton shared across the process.
review_store = ReviewStore()
