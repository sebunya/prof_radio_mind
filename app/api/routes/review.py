"""Review queue API — list and resolve items flagged for human review."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.application.review.store import review_store
from app.domain.entities.review_item import ReviewItemStatus

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


class ResolveRequest(BaseModel):
    resolved_by: str
    notes: str | None = None


class DismissRequest(BaseModel):
    resolved_by: str
    notes: str | None = None


class EscalateRequest(BaseModel):
    resolved_by: str
    notes: str | None = None


def _to_response(item: object) -> ReviewItemResponse:
    from app.domain.entities.review_item import ReviewItem

    assert isinstance(item, ReviewItem)
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


@router.get("", response_model=list[ReviewItemResponse])
def list_review_items(
    status: str | None = Query(default=None, description="Filter by status"),
) -> list[ReviewItemResponse]:
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
    return [_to_response(i) for i in review_store.list(filter_status)]


@router.get("/{item_id}", response_model=ReviewItemResponse)
def get_review_item(item_id: uuid.UUID) -> ReviewItemResponse:
    item = review_store.get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Review item {item_id} not found")
    return _to_response(item)


@router.post("/{item_id}/resolve", response_model=ReviewItemResponse)
def resolve_review_item(item_id: uuid.UUID, body: ResolveRequest) -> ReviewItemResponse:
    item = review_store.get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Review item {item_id} not found")
    if not item.is_open:
        raise HTTPException(
            status_code=409,
            detail=f"Review item {item_id} is already {item.status.value}",
        )
    item.resolve(resolved_by=body.resolved_by, notes=body.notes)
    review_store.update(item)
    return _to_response(item)


@router.post("/{item_id}/dismiss", response_model=ReviewItemResponse)
def dismiss_review_item(item_id: uuid.UUID, body: DismissRequest) -> ReviewItemResponse:
    item = review_store.get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Review item {item_id} not found")
    if not item.is_open:
        raise HTTPException(
            status_code=409,
            detail=f"Review item {item_id} is already {item.status.value}",
        )
    item.dismiss(resolved_by=body.resolved_by, notes=body.notes)
    review_store.update(item)
    return _to_response(item)


@router.post("/{item_id}/escalate", response_model=ReviewItemResponse)
def escalate_review_item(item_id: uuid.UUID, body: EscalateRequest) -> ReviewItemResponse:
    item = review_store.get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Review item {item_id} not found")
    if not item.is_open:
        raise HTTPException(
            status_code=409,
            detail=f"Review item {item_id} is already {item.status.value}",
        )
    item.escalate(resolved_by=body.resolved_by, notes=body.notes)
    review_store.update(item)
    return _to_response(item)
