from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base


class Station(Base):
    __tablename__ = "stations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    call_sign: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    frequency: Mapped[str | None] = mapped_column(String(16), nullable=True)
    city: Mapped[str | None] = mapped_column(String(128), nullable=True)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False, default="AU")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    markets: Mapped[list[StationMarket]] = relationship("StationMarket", back_populates="station")
    broadcast_days: Mapped[list[StationBroadcastDay]] = relationship(
        "StationBroadcastDay", back_populates="station"
    )


class StationMarket(Base):
    __tablename__ = "station_markets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    station_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stations.id", ondelete="CASCADE"), nullable=False
    )
    market_name: Mapped[str] = mapped_column(String(128), nullable=False)
    region_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    station: Mapped[Station] = relationship("Station", back_populates="markets")


class StationBroadcastDay(Base):
    __tablename__ = "station_broadcast_days"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    station_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stations.id", ondelete="CASCADE"), nullable=False
    )
    # Day of week: 0=Monday, 6=Sunday (ISO weekday - 1)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    # Broadcast day start hour (local time, 0-23); typically 6 for 6am
    start_hour: Mapped[int] = mapped_column(Integer, nullable=False, default=6)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    station: Mapped[Station] = relationship("Station", back_populates="broadcast_days")
