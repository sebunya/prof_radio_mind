"""Review queue API — list and resolve items flagged for human review."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_api_key
from app.domain.entities.review_item import ReviewItem, ReviewItemStatus
from app.infrastructure.database.repositories.review_item_repo import SQLReviewItemRepository
from app.infrastructure.database.session import get_db

router = APIRouter(prefix="/review-items", tags=["review"])


class ReviewItemResponse(BaseModel):
    id: str
    status: str
    item_type: str
    title: str
    description: str | None
    collector_run_id: str | None
    station_id: str | None
    resolved_at: datetime | None
    resolved_by: str | None
    notes: str | None
    created_at: datetime


class ReviewActionRequest(BaseModel):
    resolved_by: str = Field(min_length=1, max_length=255)
    notes: str | None = Field(default=None, max_length=2000)


def _to_response(item: ReviewItem) -> ReviewItemResponse:
    return ReviewItemResponse(
        id=str(item.id),
        status=item.status.value,
        item_type=item.item_type.value,
        title=item.title,
        description=item.description,
        collector_run_id=str(item.collector_run_id) if item.collector_run_id else None,
        station_id=str(item.station_id) if item.station_id else None,
        resolved_at=item.resolved_at,
        resolved_by=item.resolved_by,
        notes=item.notes,
        created_at=item.created_at,
    )


async def _fetch_open_item(
    item_id: uuid.UUID, repo: SQLReviewItemRepository
) -> ReviewItem:
    """Load a review item and assert it exists and is still open."""
    item = await repo.get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Review item {item_id} not found")
    if not item.is_open:
        raise HTTPException(
            status_code=409,
            detail=f"Review item {item_id} is already {item.status.value}",
        )
    return item


@router.get("", response_model=list[ReviewItemResponse], dependencies=[Depends(require_api_key)])
async def list_review_items(
    response: Response,
    status: str | None = Query(default=None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=200, description="Max items to return"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    session: AsyncSession = Depends(get_db),
) -> list[ReviewItemResponse]:
    """List review items.  Total count is in the ``X-Total-Count`` response header."""
    filter_status: ReviewItemStatus | None = None
    if status is not None:
        try:
            filter_status = ReviewItemStatus(status)
        except ValueError:
            valid = [s.value for s in ReviewItemStatus]
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status '{status}'. Valid values: {valid}",
            )
    repo = SQLReviewItemRepository(session)
    items, total = await repo.list_page(filter_status, limit=limit, offset=offset)
    response.headers["X-Total-Count"] = str(total)
    return [_to_response(i) for i in items]


@router.get(
    "/{item_id}",
    response_model=ReviewItemResponse,
    dependencies=[Depends(require_api_key)],
)
async def get_review_item(
    item_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> ReviewItemResponse:
    repo = SQLReviewItemRepository(session)
    item = await repo.get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Review item {item_id} not found")
    return _to_response(item)


@router.post(
    "/{item_id}/resolve",
    response_model=ReviewItemResponse,
    dependencies=[Depends(require_api_key)],
)
async def resolve_review_item(
    item_id: uuid.UUID,
    body: ReviewActionRequest,
    session: AsyncSession = Depends(get_db),
) -> ReviewItemResponse:
    repo = SQLReviewItemRepository(session)
    item = await _fetch_open_item(item_id, repo)
    item.resolve(resolved_by=body.resolved_by, notes=body.notes)
    await repo.update(item)
    return _to_response(item)


@router.post(
    "/{item_id}/dismiss",
    response_model=ReviewItemResponse,
    dependencies=[Depends(require_api_key)],
)
async def dismiss_review_item(
    item_id: uuid.UUID,
    body: ReviewActionRequest,
    session: AsyncSession = Depends(get_db),
) -> ReviewItemResponse:
    repo = SQLReviewItemRepository(session)
    item = await _fetch_open_item(item_id, repo)
    item.dismiss(resolved_by=body.resolved_by, notes=body.notes)
    await repo.update(item)
    return _to_response(item)


@router.post(
    "/{item_id}/escalate",
    response_model=ReviewItemResponse,
    dependencies=[Depends(require_api_key)],
)
async def escalate_review_item(
    item_id: uuid.UUID,
    body: ReviewActionRequest,
    session: AsyncSession = Depends(get_db),
) -> ReviewItemResponse:
    repo = SQLReviewItemRepository(session)
    item = await _fetch_open_item(item_id, repo)
    item.escalate(resolved_by=body.resolved_by, notes=body.notes)
    await repo.update(item)
    return _to_response(item)
