"""
Drone model — represents an autonomous drone in the fleet.
"""

import enum
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    Enum as SAEnum, Index,
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class DroneStatus(str, enum.Enum):
    """Operational states for a drone."""
    IDLE = "idle"
    DISPATCHED = "dispatched"
    RETURNING = "returning"
    CHARGING = "charging"
    MAINTENANCE = "maintenance"
    OFFLINE = "offline"


class Drone(Base):
    """
    Stores drone fleet data including telemetry and operational status.

    Attributes:
        id:              Auto-incrementing primary key.
        name:            Human-readable label (e.g. 'Drone-Alpha-01').
        model:           Hardware model identifier.
        battery_level:   Current battery percentage (0-100).
        latitude:        Current GPS latitude.
        longitude:       Current GPS longitude.
        altitude:        Current altitude in metres.
        speed:           Current speed in m/s.
        status:          Operational state enum.
        is_active:       Whether the drone is registered as active.
        last_heartbeat:  Timestamp of last telemetry ping.
        created_at:      Record creation timestamp (UTC).
        updated_at:      Last modification timestamp (UTC).
    """

    __tablename__ = "drones"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    model = Column(String(100), default="Generic-UAV", nullable=False)
    battery_level = Column(Float, default=100.0, nullable=False)
    latitude = Column(Float, nullable=False, default=0.0)
    longitude = Column(Float, nullable=False, default=0.0)
    altitude = Column(Float, default=0.0, nullable=False)
    speed = Column(Float, default=0.0, nullable=False)
    status = Column(SAEnum(DroneStatus), default=DroneStatus.IDLE, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    last_heartbeat = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    incidents = relationship("Incident", back_populates="assigned_drone", lazy="selectin")

    # Indexes for dispatch queries
    __table_args__ = (
        Index("ix_drones_status_battery", "status", "battery_level"),
        Index("ix_drones_location", "latitude", "longitude"),
    )

    def __repr__(self) -> str:
        return f"<Drone id={self.id} name='{self.name}' status={self.status} battery={self.battery_level}%>"
