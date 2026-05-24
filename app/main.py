from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.api.routes.imports import router as imports_router
from app.api.routes.review import router as review_router
from app.api.routes.stations import router as stations_router
from app.core.logging_config import configure_logging
from app.infrastructure.scheduler.scheduler import build_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    scheduler = build_scheduler()
    scheduler.start()
    app.state.scheduler = scheduler
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)


app = FastAPI(
    title="Radio Music Intelligence & Automation System",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(stations_router)
app.include_router(imports_router)
app.include_router(review_router)
