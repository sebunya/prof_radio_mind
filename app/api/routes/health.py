"""GET /health — liveness check with component status."""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.application.review.store import review_store
from app.domain.entities.review_item import ReviewItemStatus

router = APIRouter()

_SERVICE = "radio-music-intelligence"
_VERSION = "0.1.0"


class ComponentStatus(BaseModel):
    scheduler: str
    review_queue_pending: int


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    components: ComponentStatus


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    scheduler = getattr(request.app.state, "scheduler", None)
    scheduler_status = "running" if (scheduler and scheduler.running) else "stopped"
    pending_count = len(review_store.list(ReviewItemStatus.PENDING))

    return HealthResponse(
        status="ok",
        service=_SERVICE,
        version=_VERSION,
        components=ComponentStatus(
            scheduler=scheduler_status,
            review_queue_pending=pending_count,
        ),
    )
