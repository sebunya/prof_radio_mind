"""phase_b_events_schema

Revision ID: 2fa7e19610e8
Revises: ade166ae8d36
Create Date: 2026-05-24 00:00:00.000000

Phase B tables:
  artists, songs, play_events, no_track_events, review_items
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "2fa7e19610e8"
down_revision: str | None = "ade166ae8d36"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- artists ---
    op.create_table(
        "artists",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("name_normalised", sa.String(512), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_artists_name_normalised", "artists", ["name_normalised"])

    # --- songs ---
    op.create_table(
        "songs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("artist_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("title_normalised", sa.String(512), nullable=False),
        sa.Column("label", sa.String(255), nullable=True),
        sa.Column("isrc", sa.String(12), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
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
        sa.ForeignKeyConstraint(["artist_id"], ["artists.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_songs_title_normalised", "songs", ["title_normalised"])

    # --- play_events ---
    op.create_table(
        "play_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("station_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("collector_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("artist_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("song_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("raw_artist", sa.String(512), nullable=False),
        sa.Column("raw_title", sa.String(512), nullable=False),
        sa.Column("raw_label", sa.String(255), nullable=True),
        sa.Column("played_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_event_id", sa.String(255), nullable=True),
        sa.Column("fingerprint", sa.String(64), nullable=True),
        sa.Column("attribution", sa.String(64), nullable=True),
        sa.Column("is_duplicate", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["artist_id"], ["artists.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["collector_run_id"], ["collector_runs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["song_id"], ["songs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["station_id"], ["stations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_play_events_played_at", "play_events", ["played_at"])
    op.create_index(
        "ix_play_events_station_played_at",
        "play_events",
        ["station_id", "played_at"],
    )

    # --- no_track_events ---
    op.create_table(
        "no_track_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("station_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("collector_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.String(64), nullable=False),
        sa.Column("raw_http_status", sa.Integer, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["collector_run_id"], ["collector_runs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["station_id"], ["stations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_no_track_events_observed_at", "no_track_events", ["observed_at"])

    # --- review_items ---
    op.create_table(
        "review_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("item_type", sa.String(64), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("collector_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("station_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["collector_run_id"], ["collector_runs.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["station_id"], ["stations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("review_items")
    op.drop_index("ix_no_track_events_observed_at", table_name="no_track_events")
    op.drop_table("no_track_events")
    op.drop_index("ix_play_events_station_played_at", table_name="play_events")
    op.drop_index("ix_play_events_played_at", table_name="play_events")
    op.drop_table("play_events")
    op.drop_index("ix_songs_title_normalised", table_name="songs")
    op.drop_table("songs")
    op.drop_index("ix_artists_name_normalised", table_name="artists")
    op.drop_table("artists")
