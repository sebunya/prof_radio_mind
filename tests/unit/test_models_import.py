"""Verify all Phase A–E SQLAlchemy models are importable and have expected tablenames."""

from app.infrastructure.database.models import (
    Alert,
    Artist,
    AuditLog,
    CollectorRun,
    DailyReport,
    Error,
    Export,
    NoTrackEventDB,
    PlayEventDB,
    RawPayload,
    ReportVersion,
    ReviewItem,
    Role,
    Song,
    Source,
    SourceRoutePriority,
    SourceValidation,
    Station,
    StationBroadcastDay,
    StationMarket,
    SystemSetting,
    User,
    WebhookSubscriptionDB,
)


def test_phase_a_model_tablenames() -> None:
    expected = {
        Role: "roles",
        User: "users",
        Station: "stations",
        StationMarket: "station_markets",
        StationBroadcastDay: "station_broadcast_days",
        Source: "sources",
        SourceValidation: "source_validations",
        SourceRoutePriority: "source_route_priorities",
        CollectorRun: "collector_runs",
        RawPayload: "raw_payloads",
        Error: "errors",
        Alert: "alerts",
        AuditLog: "audit_logs",
        SystemSetting: "system_settings",
    }
    for model, tablename in expected.items():
        assert model.__tablename__ == tablename, f"{model.__name__}: expected {tablename}"


def test_phase_a_model_count() -> None:
    from app.infrastructure.database.models import __all__ as all_models

    assert len(all_models) == 23  # 14 Phase A + 5 Phase B + 3 Phase C + 1 Phase E


def test_phase_b_model_tablenames() -> None:
    expected = {
        Artist: "artists",
        Song: "songs",
        PlayEventDB: "play_events",
        NoTrackEventDB: "no_track_events",
        ReviewItem: "review_items",
    }
    for model, tablename in expected.items():
        assert model.__tablename__ == tablename, f"{model.__name__}: expected {tablename}"


def test_phase_c_model_tablenames() -> None:
    expected = {
        DailyReport: "daily_reports",
        ReportVersion: "report_versions",
        Export: "exports",
    }
    for model, tablename in expected.items():
        assert model.__tablename__ == tablename, f"{model.__name__}: expected {tablename}"


def test_phase_e_model_tablenames() -> None:
    expected = {
        WebhookSubscriptionDB: "webhook_subscriptions",
    }
    for model, tablename in expected.items():
        assert model.__tablename__ == tablename, f"{model.__name__}: expected {tablename}"


def test_raw_payload_has_sha256_column() -> None:
    cols = {c.name for c in RawPayload.__table__.columns}
    assert "sha256" in cols
    assert "storage_path" in cols


def test_collector_run_has_status_column() -> None:
    cols = {c.name for c in CollectorRun.__table__.columns}
    assert "status" in cols
    assert "error_message" in cols


def test_all_models_have_created_at() -> None:
    from app.infrastructure.database import models as models_module
    from app.infrastructure.database.models import __all__ as all_model_names

    for name in all_model_names:
        model = getattr(models_module, name)
        cols = {c.name for c in model.__table__.columns}
        assert "created_at" in cols, f"{name} missing created_at"


def test_timestamps_are_timezone_aware() -> None:
    import sqlalchemy as sa

    for model, col_name in [
        (CollectorRun, "created_at"),
        (RawPayload, "fetched_at"),
        (Station, "updated_at"),
    ]:
        col = model.__table__.c[col_name]
        assert isinstance(col.type, sa.DateTime), f"{model.__name__}.{col_name} not DateTime"
        assert col.type.timezone, f"{model.__name__}.{col_name} must be timezone=True"
