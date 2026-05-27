"""GET /health — liveness check with component status."""

from __future__ import annotations

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel
from sqlalchemy import text

router = APIRouter()

_SERVICE = "radio-music-intelligence"
_VERSION = "0.1.0"


class ComponentStatus(BaseModel):
    scheduler: str
    database: str
    review_queue_pending: int


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    components: ComponentStatus


@router.get("/health", response_model=HealthResponse)
async def health(request: Request, response: Response) -> HealthResponse:
    scheduler = getattr(request.app.state, "scheduler", None)
    scheduler_status = "running" if (scheduler and scheduler.running) else "stopped"

    # ── Database connectivity check ───────────────────────────────────────
    db_status = "ok"
    pending_count = 0
    try:
        from app.infrastructure.database.repositories.review_item_repo import (
            SQLReviewItemRepository,
        )
        from app.infrastructure.database.session import _get_factory

        async with _get_factory()() as session:
            # Verify DB is reachable
            await session.execute(text("SELECT 1"))
            repo = SQLReviewItemRepository(session)
            pending_count = await repo.count_pending()
    except Exception as exc:
        db_status = f"error: {exc}"

    # Return 503 if DB is down — probes and load balancers can use this
    overall_status = "ok" if db_status == "ok" else "degraded"
    if overall_status != "ok":
        response.status_code = 503

    return HealthResponse(
        status=overall_status,
        service=_SERVICE,
        version=_VERSION,
        components=ComponentStatus(
            scheduler=scheduler_status,
            database=db_status,
            review_queue_pending=pending_count,
        ),
    )
