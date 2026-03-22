"""
Alert model — system-generated notifications tied to incidents.
"""

import enum
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime,
    Enum as SAEnum, ForeignKey, Index,
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class AlertPriority(str, enum.Enum):
    """Alert urgency levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Alert(Base):
    """
    Represents a notification generated when an incident is detected
    or its status changes.

    Attributes:
        id:           Auto-incrementing primary key.
        incident_id:  FK to the associated incident.
        priority:     Urgency level.
        title:        Short headline.
        message:      Detailed alert body.
        is_read:      Whether an operator has acknowledged the alert.
        created_at:   Timestamp (UTC).
    """

    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    incident_id = Column(Integer, ForeignKey("incidents.id"), nullable=False, index=True)
    priority = Column(SAEnum(AlertPriority), default=AlertPriority.MEDIUM, nullable=False)
    title = Column(String(200), nullable=False)
    message = Column(Text, default="")
    is_read = Column(Boolean, default=False, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    incident = relationship("Incident", back_populates="alerts", lazy="selectin")

    # Indexes
    __table_args__ = (
        Index("ix_alerts_priority_read", "priority", "is_read"),
        Index("ix_alerts_created", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Alert id={self.id} priority={self.priority} read={self.is_read}>"
