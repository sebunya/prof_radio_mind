"""add_spotify_columns_to_songs

Revision ID: c27859102bac
Revises: c4e2a1f9b8d7
Create Date: 2026-06-04 19:37:18.090642

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c27859102bac'
down_revision: Union[str, Sequence[str], None] = 'c4e2a1f9b8d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('songs', sa.Column('spotify_track_id', sa.String(length=255), nullable=True))
    op.add_column('songs', sa.Column('spotify_album_name', sa.String(length=512), nullable=True))
    op.add_column('songs', sa.Column('spotify_artist_name', sa.String(length=512), nullable=True))
    op.add_column('songs', sa.Column('spotify_popularity', sa.Integer(), nullable=True))
    op.add_column('songs', sa.Column('spotify_thumbnail_url', sa.String(length=512), nullable=True))
    op.add_column('songs', sa.Column('spotify_match_confidence', sa.Float(), nullable=True))
    op.add_column('songs', sa.Column('spotify_isrc', sa.String(length=12), nullable=True))
    op.add_column('songs', sa.Column('spotify_enriched_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('songs', 'spotify_enriched_at')
    op.drop_column('songs', 'spotify_isrc')
    op.drop_column('songs', 'spotify_match_confidence')
    op.drop_column('songs', 'spotify_thumbnail_url')
    op.drop_column('songs', 'spotify_popularity')
    op.drop_column('songs', 'spotify_artist_name')
    op.drop_column('songs', 'spotify_album_name')
    op.drop_column('songs', 'spotify_track_id')
