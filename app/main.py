from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.backfill import router as backfill_router
from app.api.routes.charts import router as charts_router
from app.api.routes.health import router as health_router
from app.api.routes.imports import router as imports_router
from app.api.routes.playlist import router as playlist_router
from app.api.routes.proof_of_play import router as proof_of_play_router
from app.api.routes.reports import router as reports_router
from app.api.routes.review import router as review_router
from app.api.routes.sources import router as sources_router
from app.api.routes.stations import router as stations_router
from app.api.routes.webhooks import router as webhooks_router
from app.core.logging_config import configure_logging
from app.infrastructure.database.session import dispose_engine
from app.infrastructure.scheduler.scheduler import build_scheduler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()

    # Seed DB (idempotent — safe to run on every startup)
    try:
        from app.application.seeder import seed_database
        from app.infrastructure.database.session import _get_factory

        async with _get_factory()() as session:
            await seed_database(session)
    except Exception as exc:
        logger.warning("db_seed_failed error=%s (continuing without DB)", exc)

    scheduler = build_scheduler()
    scheduler.start()
    app.state.scheduler = scheduler

    try:
        yield
    finally:
        scheduler.shutdown(wait=False)
        await dispose_engine()


app = FastAPI(
    title="Radio Music Intelligence & Automation System",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(stations_router)
app.include_router(imports_router)
app.include_router(review_router)
app.include_router(reports_router)
app.include_router(sources_router)
app.include_router(playlist_router)
app.include_router(proof_of_play_router)
app.include_router(charts_router)
app.include_router(webhooks_router)
app.include_router(backfill_router)
