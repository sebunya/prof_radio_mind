"""GET /api/admin/overview — read-only operational state for the admin console.

Returns system configuration flags without exposing secrets.
Secrets (DATABASE_URL, API_KEY, SMTP credentials, admin password) are never included.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.settings import settings

router = APIRouter(prefix="/api/admin", tags=["admin"])


class CollectorFlags(BaseModel):
    capital: bool
    nova: bool
    kiis: bool
    nightly_reconciliation: bool


class AdminOverviewResponse(BaseModel):
    environment: str
    is_production: bool
    scheduler_enabled: bool
    docs_exposed: bool
    admin_auth_enabled: bool
    raw_payload_retention_days: int
    retention_enabled: bool
    dedup_enabled: bool
    collector_flags: CollectorFlags


@router.get("/overview", response_model=AdminOverviewResponse)
async def admin_overview() -> AdminOverviewResponse:
    is_prod = settings.app_env == "production"
    docs_exposed = not is_prod or settings.enable_docs_in_production
    admin_auth = bool(
        settings.admin_basic_auth_user and settings.admin_basic_auth_password
    )

    return AdminOverviewResponse(
        environment=settings.app_env,
        is_production=is_prod,
        scheduler_enabled=settings.scheduler_enabled,
        docs_exposed=docs_exposed,
        admin_auth_enabled=admin_auth,
        raw_payload_retention_days=settings.raw_payload_retention_days,
        retention_enabled=settings.raw_payload_retention_days > 0,
        dedup_enabled=True,
        collector_flags=CollectorFlags(
            capital=settings.enable_capital_collector,
            nova=settings.enable_nova_collector,
            kiis=settings.enable_kiis_collector,
            nightly_reconciliation=settings.enable_nightly_reconciliation,
        ),
    )
