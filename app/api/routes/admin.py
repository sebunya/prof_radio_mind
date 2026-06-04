"""Admin API routes for read-only system telemetry and operations monitoring."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import settings
from app.infrastructure.database.models.collector_runs import CollectorRun
from app.infrastructure.database.models.events import PlayEventDB
from app.infrastructure.database.models.events import ReviewItem as ReviewItemModel
from app.infrastructure.database.models.sources import (
    Source as SourceModel,
)
from app.infrastructure.database.models.sources import (
    SourceRoutePriority,
    SourceValidation,
)
from app.infrastructure.database.models.stations import Station as StationModel
from app.infrastructure.database.session import get_db

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ── Schemas ───────────────────────────────────────────────────────────

class OverviewStats(BaseModel):
    active_stations: int
    total_sources: int
    pending_reviews: int
    active_webhooks: int


class OverviewResponse(BaseModel):
    app_env: str
    scheduler_enabled: bool
    enable_capital_collector: bool
    enable_nova_collector: bool
    enable_kiis_collector: bool
    enable_nightly_reconciliation: bool
    raw_payload_retention_days: int
    enable_docs_in_production: bool
    admin_basic_auth_configured: bool
    stats: OverviewStats


class OperationsResponse(BaseModel):
    app_env: str
    scheduler_enabled: bool
    enable_capital_collector: bool
    enable_nova_collector: bool
    enable_kiis_collector: bool
    enable_nightly_reconciliation: bool
    raw_payload_retention_days: int
    enable_docs_in_production: bool
    admin_basic_auth_configured: bool
    db_migration_version: str


class RecentEventResponse(BaseModel):
    id: str
    station_name: str
    station_call_sign: str
    raw_artist: str
    raw_title: str
    played_at: datetime
    is_duplicate: bool
    fingerprint: str | None


class SourceHealthResponse(BaseModel):
    id: str
    station_id: str
    station_call_sign: str
    source_type: str
    name: str
    base_url: str | None
    is_active: bool
    priority: int
    latest_validation_status: str | None
    latest_validation_code: str | None
    latest_validated_at: datetime | None
    latest_response_status_code: int | None


class ReviewSummaryResponse(BaseModel):
    pending: int
    reviewed: int
    dismissed: int
    escalated: int


class EnrichmentSummaryResponse(BaseModel):
    spotify_metadata_enrichment_enabled: bool
    counts: dict[str, int]


class SpotifyReadinessResponse(BaseModel):
    client_id_configured: bool
    client_secret_configured: bool
    redirect_uri: str
    api_base_url: str
    token_url: str
    enrichment_enabled_flag: bool
    match_confidence_threshold: float
    request_timeout_seconds: int
    max_retries: int
    token_cache_seconds: int


class ProviderDetail(BaseModel):
    role: str
    configured: bool
    enabled: bool
    base_url_configured: bool | None = None
    user_agent_configured: bool | None = None
    rate_limit_per_second: int | None = None
    default_format: str | None = None
    client_id_configured: bool | None = None
    client_secret_configured: bool | None = None
    redirect_uri_configured: bool | None = None
    requires_musicbrainz_release_mbid: bool | None = None
    live_calls_enabled: bool


class ProvidersMap(BaseModel):
    musicbrainz: ProviderDetail
    spotify: ProviderDetail
    cover_art_archive: ProviderDetail


class ComplianceBoundary(BaseModel):
    radio_capture_source: str
    musicbrainz: str
    spotify: str
    cover_art_archive: str
    no_streaming: bool
    no_downloads: bool
    no_playlist_scraping: bool
    no_playback: bool


class MetadataReadinessResponse(BaseModel):
    status: str
    mode: str
    providers: ProvidersMap
    compliance_boundary: ComplianceBoundary


class CollectorRunResponse(BaseModel):
    id: str
    collector_name: str
    station_call_sign: str
    status: str
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None


# ── Routes ────────────────────────────────────────────────────────────

@router.get("/overview", response_model=OverviewResponse)
async def get_overview(session: AsyncSession = Depends(get_db)) -> OverviewResponse:
    active_stations = 0
    total_sources = 0
    pending_reviews = 0
    try:
        # 1. Count active stations
        stations_q = (
            select(func.count())
            .select_from(StationModel)
            .where(StationModel.is_active.is_(True))
        )
        active_stations = (await session.execute(stations_q)).scalar() or 0

        # 2. Count active sources
        sources_q = (
            select(func.count())
            .select_from(SourceModel)
            .where(SourceModel.is_active.is_(True))
        )
        total_sources = (await session.execute(sources_q)).scalar() or 0

        # 3. Count pending reviews
        reviews_q = (
            select(func.count())
            .select_from(ReviewItemModel)
            .where(ReviewItemModel.status == "pending")
        )
        pending_reviews = (await session.execute(reviews_q)).scalar() or 0
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("admin_overview_db_error: %s", e)

    # 4. Count active webhooks from the Webhook Store (in-memory subscription cache)
    active_webhooks = 0
    try:
        from app.application.webhooks.service import webhook_store
        active_webhooks = len(webhook_store._subs)
    except Exception:
        pass

    auth_configured = bool(settings.admin_basic_auth_user) and bool(
        settings.admin_basic_auth_password
    )

    return OverviewResponse(
        app_env=settings.app_env,
        scheduler_enabled=settings.scheduler_enabled,
        enable_capital_collector=settings.enable_capital_collector,
        enable_nova_collector=settings.enable_nova_collector,
        enable_kiis_collector=settings.enable_kiis_collector,
        enable_nightly_reconciliation=settings.enable_nightly_reconciliation,
        raw_payload_retention_days=settings.raw_payload_retention_days,
        enable_docs_in_production=settings.enable_docs_in_production,
        admin_basic_auth_configured=auth_configured,
        stats=OverviewStats(
            active_stations=active_stations,
            total_sources=total_sources,
            pending_reviews=pending_reviews,
            active_webhooks=active_webhooks,
        )
    )


@router.get("/operations", response_model=OperationsResponse)
async def get_operations() -> OperationsResponse:
    auth_configured = bool(settings.admin_basic_auth_user) and bool(
        settings.admin_basic_auth_password
    )
    # Statically match version tag or load dynamically if version in config.
    # Current alembic version tag is c4e2a1f9b8d7.
    return OperationsResponse(
        app_env=settings.app_env,
        scheduler_enabled=settings.scheduler_enabled,
        enable_capital_collector=settings.enable_capital_collector,
        enable_nova_collector=settings.enable_nova_collector,
        enable_kiis_collector=settings.enable_kiis_collector,
        enable_nightly_reconciliation=settings.enable_nightly_reconciliation,
        raw_payload_retention_days=settings.raw_payload_retention_days,
        enable_docs_in_production=settings.enable_docs_in_production,
        admin_basic_auth_configured=auth_configured,
        db_migration_version="c4e2a1f9b8d7"
    )


@router.get("/recent-events", response_model=list[RecentEventResponse])
async def get_recent_events(
    session: AsyncSession = Depends(get_db),
) -> list[RecentEventResponse]:
    try:
        stmt = (
            select(PlayEventDB, StationModel)
            .join(StationModel, PlayEventDB.station_id == StationModel.id)
            .order_by(PlayEventDB.played_at.desc())
            .limit(10)
        )
        result = await session.execute(stmt)
        rows = result.all()

        return [
            RecentEventResponse(
                id=str(event.id),
                station_name=station.name,
                station_call_sign=station.call_sign,
                raw_artist=event.raw_artist,
                raw_title=event.raw_title,
                played_at=event.played_at,
                is_duplicate=event.is_duplicate,
                fingerprint=event.fingerprint,
            )
            for event, station in rows
        ]
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("admin_recent_events_db_error: %s", e)
        return []


@router.get("/source-health", response_model=list[SourceHealthResponse])
async def get_source_health(
    session: AsyncSession = Depends(get_db),
) -> list[SourceHealthResponse]:
    try:
        # Query all active sources
        stmt = (
            select(SourceModel, StationModel)
            .join(StationModel, SourceModel.station_id == StationModel.id)
            .order_by(StationModel.call_sign, SourceModel.source_type)
        )
        result = await session.execute(stmt)
        rows = result.all()

        health_list = []
        for source, station in rows:
            # Load priority
            p_stmt = select(SourceRoutePriority.priority).where(
                SourceRoutePriority.source_id == source.id,
                SourceRoutePriority.is_active.is_(True)
            ).limit(1)
            priority = (await session.execute(p_stmt)).scalar() or 99

            # Load latest validation run
            val_stmt = (
                select(SourceValidation)
                .where(SourceValidation.source_id == source.id)
                .order_by(SourceValidation.validated_at.desc())
                .limit(1)
            )
            val = (await session.execute(val_stmt)).scalar_one_or_none()

            st = source.source_type
            src_type = st if isinstance(st, str) else st.value

            health_list.append(
                SourceHealthResponse(
                    id=str(source.id),
                    station_id=str(source.station_id),
                    station_call_sign=station.call_sign,
                    source_type=src_type,
                    name=source.name,
                    base_url=source.base_url,
                    is_active=source.is_active,
                    priority=priority,
                    latest_validation_status=val.status if val else None,
                    latest_validation_code=val.validation_code if val else None,
                    latest_validated_at=val.validated_at if val else None,
                    latest_response_status_code=val.response_status_code if val else None,
                )
            )

        return health_list
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("admin_source_health_db_error: %s", e)
        return []


@router.get("/review-summary", response_model=ReviewSummaryResponse)
async def get_review_summary(
    session: AsyncSession = Depends(get_db),
) -> ReviewSummaryResponse:
    try:
        stmt = select(ReviewItemModel.status, func.count()).group_by(ReviewItemModel.status)
        rows = (await session.execute(stmt)).all()
        counts: dict[str, int] = {str(status): int(count) for status, count in rows}

        return ReviewSummaryResponse(
            pending=counts.get("pending", 0),
            reviewed=counts.get("reviewed", 0),
            dismissed=counts.get("dismissed", 0),
            escalated=counts.get("escalated", 0),
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("admin_review_summary_db_error: %s", e)
        return ReviewSummaryResponse(pending=0, reviewed=0, dismissed=0, escalated=0)


@router.get("/enrichment-status", response_model=EnrichmentSummaryResponse)
async def get_enrichment_status(
    session: AsyncSession = Depends(get_db),
) -> EnrichmentSummaryResponse:
    total_plays = 0
    try:
        # Since there are no Spotify columns in the database yet, we report counts
        # under the 'disabled' or 'pending' state strictly representing the DB.
        total_q = select(func.count()).select_from(PlayEventDB)
        total_plays = (await session.execute(total_q)).scalar() or 0
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("admin_enrichment_status_db_error: %s", e)

    return EnrichmentSummaryResponse(
        spotify_metadata_enrichment_enabled=settings.spotify_metadata_enrichment_enabled,
        counts={
            "not_configured": total_plays,
            "disabled": 0,
            "pending": 0,
            "matched": 0,
            "failed": 0
        }
    )


@router.get("/spotify-readiness", response_model=SpotifyReadinessResponse)
async def get_spotify_readiness() -> SpotifyReadinessResponse:
    return SpotifyReadinessResponse(
        client_id_configured=bool(settings.spotify_client_id),
        client_secret_configured=bool(settings.spotify_client_secret),
        redirect_uri=settings.spotify_redirect_uri,
        api_base_url=settings.spotify_api_base_url,
        token_url=settings.spotify_token_url,
        enrichment_enabled_flag=settings.spotify_metadata_enrichment_enabled,
        match_confidence_threshold=settings.spotify_match_confidence_threshold,
        request_timeout_seconds=settings.spotify_request_timeout_seconds,
        max_retries=settings.spotify_max_retries,
        token_cache_seconds=settings.spotify_token_cache_seconds,
    )


@router.get("/metadata-readiness", response_model=MetadataReadinessResponse)
async def get_metadata_readiness() -> MetadataReadinessResponse:
    mb_configured = bool(settings.musicbrainz_api_base_url and settings.musicbrainz_user_agent)
    sp_configured = bool(settings.spotify_client_id and settings.spotify_client_secret)
    caa_configured = bool(settings.cover_art_archive_base_url)

    return MetadataReadinessResponse(
        status="disabled",
        mode="readiness_only",
        providers=ProvidersMap(
            musicbrainz=ProviderDetail(
                role="open_canonical_identity",
                configured=mb_configured,
                enabled=settings.musicbrainz_metadata_enrichment_enabled,
                base_url_configured=bool(settings.musicbrainz_api_base_url),
                user_agent_configured=bool(settings.musicbrainz_user_agent),
                rate_limit_per_second=settings.musicbrainz_rate_limit_per_second,
                default_format=settings.musicbrainz_default_format,
                live_calls_enabled=False
            ),
            spotify=ProviderDetail(
                role="commercial_catalogue_context",
                configured=sp_configured,
                enabled=settings.spotify_metadata_enrichment_enabled,
                client_id_configured=bool(settings.spotify_client_id),
                client_secret_configured=bool(settings.spotify_client_secret),
                redirect_uri_configured=bool(settings.spotify_redirect_uri),
                live_calls_enabled=False
            ),
            cover_art_archive=ProviderDetail(
                role="cover_art_fallback",
                configured=caa_configured,
                enabled=False,
                base_url_configured=bool(settings.cover_art_archive_base_url),
                requires_musicbrainz_release_mbid=True,
                live_calls_enabled=False
            )
        ),
        compliance_boundary=ComplianceBoundary(
            radio_capture_source="TenX Radar monitored station sources",
            musicbrainz="canonical music identity and disambiguation only",
            spotify="catalogue metadata and platform reference only",
            cover_art_archive="release artwork reference only",
            no_streaming=True,
            no_downloads=True,
            no_playlist_scraping=True,
            no_playback=True
        )
    )


@router.get("/collector-runs", response_model=list[CollectorRunResponse])
async def get_collector_runs(
    session: AsyncSession = Depends(get_db),
) -> list[CollectorRunResponse]:
    try:
        stmt = (
            select(CollectorRun, StationModel)
            .join(StationModel, CollectorRun.station_id == StationModel.id)
            .order_by(CollectorRun.created_at.desc())
            .limit(10)
        )
        result = await session.execute(stmt)
        rows = result.all()

        return [
            CollectorRunResponse(
                id=str(run.id),
                # Status represents name if custom metadata is absent
                collector_name=run.status,
                station_call_sign=station.call_sign,
                status=run.status,
                error_message=run.error_message,
                started_at=run.started_at,
                completed_at=run.completed_at,
            )
            for run, station in rows
        ]
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("admin_collector_runs_db_error: %s", e)
        return []
