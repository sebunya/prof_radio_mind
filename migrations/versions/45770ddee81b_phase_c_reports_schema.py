"""phase_c_reports_schema

Revision ID: 45770ddee81b
Revises: 2fa7e19610e8
Create Date: 2026-05-24 00:00:00.000000

Phase C tables:
  daily_reports, report_versions, exports
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "45770ddee81b"
down_revision: str | None = "2fa7e19610e8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- daily_reports ---
    op.create_table(
        "daily_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("station_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "confidence_level",
            sa.String(16),
            nullable=False,
            server_default=sa.text("'medium'"),
        ),
        sa.Column(
            "confidence_score",
            sa.Numeric(5, 4),
            nullable=False,
            server_default=sa.text("0.0"),
        ),
        sa.Column("total_plays", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("unique_songs", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("source_coverage", postgresql.JSONB, nullable=True),
        sa.Column("is_corrected", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("correction_note", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["station_id"], ["stations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_daily_reports_report_date", "daily_reports", ["report_date"])
    op.create_index(
        "ix_daily_reports_station_date",
        "daily_reports",
        ["station_id", "report_date"],
    )

    # --- report_versions ---
    op.create_table(
        "report_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("daily_report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer, nullable=False, server_default=sa.text("1")),
        sa.Column("snapshot", postgresql.JSONB, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("change_note", sa.Text, nullable=True),
        sa.ForeignKeyConstraint(["daily_report_id"], ["daily_reports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- exports ---
    op.create_table(
        "exports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("daily_report_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("export_type", sa.String(32), nullable=False),
        sa.Column("export_version", sa.Integer, nullable=False, server_default=sa.text("1")),
        sa.Column("format", sa.String(16), nullable=False, server_default=sa.text("'csv'")),
        sa.Column(
            "status", sa.String(16), nullable=False, server_default=sa.text("'pending'")
        ),
        sa.Column("storage_path", sa.Text, nullable=True),
        sa.Column("byte_size", sa.Integer, nullable=True),
        sa.Column("sha256", sa.String(64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["daily_report_id"], ["daily_reports.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("exports")
    op.drop_table("report_versions")
    op.drop_index("ix_daily_reports_station_date", table_name="daily_reports")
    op.drop_index("ix_daily_reports_report_date", table_name="daily_reports")
    op.drop_table("daily_reports")
