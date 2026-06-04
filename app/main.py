from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes.admin_overview import router as admin_overview_router
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
from app.core.admin_auth import AdminBasicAuthMiddleware
from app.core.logging_config import configure_logging
from app.core.settings import settings
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

    app.state.scheduler = None
    if settings.scheduler_enabled:
        scheduler = build_scheduler()
        scheduler.start()
        app.state.scheduler = scheduler
        logger.info("Scheduler started successfully")
    else:
        logger.info("Scheduler is disabled by configuration (SCHEDULER_ENABLED=false)")

    try:
        yield
    finally:
        if app.state.scheduler:
            app.state.scheduler.shutdown(wait=False)
            logger.info("Scheduler shut down successfully")
        await dispose_engine()


# Hide interactive API docs in production unless explicitly forced on.
_docs_enabled = settings.app_env != "production" or settings.enable_docs_in_production
_docs_url = "/docs" if _docs_enabled else None
_redoc_url = "/redoc" if _docs_enabled else None
_openapi_url = "/openapi.json" if _docs_enabled else None

app = FastAPI(
    title="Radio Music Intelligence & Automation System",
    version="0.1.0",
    lifespan=lifespan,
    docs_url=_docs_url,
    redoc_url=_redoc_url,
    openapi_url=_openapi_url,
)

# Optional HTTP Basic auth in front of /admin (no-op unless credentials set).
app.add_middleware(AdminBasicAuthMiddleware)

app.include_router(admin_overview_router)
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


@app.get("/", include_in_schema=False)
async def root() -> dict[str, object]:
    endpoints: dict[str, str] = {
        "health": "/health",
        "admin": "/admin",
    }
    if _docs_enabled:
        endpoints["api_docs"] = "/docs"
    return {
        "status": "ok",
        "service": "TenX Radar",
        "description": "Radio Music Intelligence & Automation System",
        "version": "0.1.0",
        "endpoints": endpoints,
        "components": {
            "scheduler": "stopped",
            "collectors": "disabled",
        },
    }


app.mount("/admin", StaticFiles(directory="app/static", html=True), name="admin")
