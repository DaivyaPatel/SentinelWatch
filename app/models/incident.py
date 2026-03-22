"""
Incident model — represents a detected urban safety event.
"""

import enum
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime,
    Enum as SAEnum, ForeignKey, Index, JSON,
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class IncidentType(str, enum.Enum):
    """Categories of detectable incidents."""
    FIRE = "fire"
    ACCIDENT = "accident"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    CROWD_ANOMALY = "crowd_anomaly"
    VANDALISM = "vandalism"
    OTHER = "other"


class IncidentStatus(str, enum.Enum):
    """Lifecycle states of an incident."""
    DETECTED = "detected"
    CONFIRMED = "confirmed"
    DISPATCHED = "dispatched"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    FALSE_ALARM = "false_alarm"


class Incident(Base):
    """
    Records detected incidents with location, severity, and AI metadata.

    Attributes:
        id:                 Auto-incrementing primary key.
        incident_type:      Classification category.
        severity:           Priority score 1 (low) – 10 (critical).
        latitude / longitude: GPS coordinates of the event.
        status:             Current lifecycle state.
        description:        Free-text notes.
        confidence_score:   AI detection confidence (0.0 – 1.0).
        detection_metadata: Raw AI output (bounding boxes, labels, etc.).
        source:             Feed source identifier (e.g. camera ID).
        assigned_drone_id:  FK to the drone dispatched to the scene (nullable).
        created_at:         Timestamp of detection (UTC).
        updated_at:         Last update timestamp (UTC).
        resolved_at:        Timestamp when marked resolved (nullable).
    """

    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    incident_type = Column(SAEnum(IncidentType), nullable=False, index=True)
    severity = Column(Integer, nullable=False, default=5)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    status = Column(SAEnum(IncidentStatus), default=IncidentStatus.DETECTED, nullable=False, index=True)
    description = Column(Text, default="")
    confidence_score = Column(Float, default=0.0)

    # Raw AI detection metadata (bounding boxes, labels, frame info)
    detection_metadata = Column(JSON, default=dict)

    # Source identifier (camera/drone feed ID)
    source = Column(String(200), default="unknown")

    # FK → Drone assigned to this incident
    assigned_drone_id = Column(Integer, ForeignKey("drones.id"), nullable=True)

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
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    assigned_drone = relationship("Drone", back_populates="incidents", lazy="selectin")
    alerts = relationship("Alert", back_populates="incident", cascade="all, delete-orphan", lazy="selectin")

    # Indexes
    __table_args__ = (
        Index("ix_incidents_type_status", "incident_type", "status"),
        Index("ix_incidents_severity", "severity"),
        Index("ix_incidents_location", "latitude", "longitude"),
        Index("ix_incidents_created", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<Incident id={self.id} type={self.incident_type} "
            f"severity={self.severity} status={self.status}>"
        )
