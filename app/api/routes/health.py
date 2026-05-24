"""GET /health — liveness check with component status."""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

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
async def health(request: Request) -> HealthResponse:
    scheduler = getattr(request.app.state, "scheduler", None)
    scheduler_status = "running" if (scheduler and scheduler.running) else "stopped"

    pending_count = 0
    try:
        from app.infrastructure.database.repositories.review_item_repo import (
            SQLReviewItemRepository,
        )
        from app.infrastructure.database.session import _get_factory

        async with _get_factory()() as session:
            repo = SQLReviewItemRepository(session)
            pending_count = await repo.count_pending()
    except Exception:
        pass

    return HealthResponse(
        status="ok",
        service=_SERVICE,
        version=_VERSION,
        components=ComponentStatus(
            scheduler=scheduler_status,
            review_queue_pending=pending_count,
        ),
    )
