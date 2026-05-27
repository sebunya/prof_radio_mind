from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes.backfill import router as backfill_router
from app.api.routes.charts import router as charts_router
from app.api.routes.email_reports import router as email_reports_router
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
from app.core.settings import settings
from app.infrastructure.database.session import dispose_engine
from app.infrastructure.scheduler.scheduler import build_scheduler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()

    # ── Production security guard ─────────────────────────────────────────
    if settings.app_env == "production" and not settings.api_key:
        logger.critical(
            "SECURITY: APP_ENV=production but API_KEY is not set — "
            "all protected endpoints are publicly accessible! Set API_KEY immediately."
        )

    # ── Seed DB (idempotent) ──────────────────────────────────────────────
    try:
        from app.application.seeder import seed_database
        from app.infrastructure.database.session import _get_factory

        async with _get_factory()() as session:
            await seed_database(session)
    except Exception as exc:
        logger.warning("db_seed_failed error=%s (continuing without DB)", exc)

    # ── Load webhook subscriptions from DB into in-memory store ──────────
    try:
        from app.application.webhooks.service import webhook_store
        from app.infrastructure.database.session import _get_factory as _sf

        async with _sf()() as session:
            await webhook_store.load_from_db(session)
    except Exception as exc:
        logger.warning("webhook_store_load_failed error=%s (starting with empty store)", exc)

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

# ── CORS ──────────────────────────────────────────────────────────────────────
# Explicit origins should be set via CORS_ORIGINS env var in production.
# Defaults to allow all (*) which is fine for the admin-only scenario where
# the frontend is served from the same origin.
_cors_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins if _cors_origins else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)


# ── Security headers ──────────────────────────────────────────────────────────
@app.middleware("http")
async def add_security_headers(request: Request, call_next: object) -> Response:
    response: Response = await call_next(request)  # type: ignore[operator]
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # Allow inline scripts/styles (required for onclick handlers and Chart.js CDN)
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "font-src 'self'"
    )
    return response


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
app.include_router(email_reports_router)

app.mount(
    "/admin",
    StaticFiles(directory=Path(__file__).parent / "static", html=True),
    name="admin",
)
