"""
NoFlyZone model — defines geofenced restricted areas.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, Index,
)
from app.core.database import Base


class NoFlyZone(Base):
    """
    Circular geofenced areas where drones must not enter.

    Attributes:
        id:           Auto-incrementing primary key.
        name:         Human-readable label (e.g. 'Airport Zone A').
        description:  Optional notes.
        center_lat:   Centre latitude of the no-fly zone.
        center_lon:   Centre longitude of the no-fly zone.
        radius_km:    Radius in kilometres.
        is_active:    Whether the zone is currently enforced.
        created_at:   Record creation timestamp (UTC).
    """

    __tablename__ = "no_fly_zones"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(200), unique=True, nullable=False, index=True)
    description = Column(Text, default="")
    center_lat = Column(Float, nullable=False)
    center_lon = Column(Float, nullable=False)
    radius_km = Column(Float, nullable=False, default=1.0)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Indexes
    __table_args__ = (
        Index("ix_nfz_location", "center_lat", "center_lon"),
    )

    def __repr__(self) -> str:
        return f"<NoFlyZone id={self.id} name='{self.name}' radius={self.radius_km}km>"
