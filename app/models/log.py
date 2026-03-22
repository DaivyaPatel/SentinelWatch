"""
SystemLog model — structured audit / event log.
"""

import enum
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Enum as SAEnum, JSON, Index,
)
from app.core.database import Base


class LogLevel(str, enum.Enum):
    """Log severity levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class SystemLog(Base):
    """
    Persists structured log entries for auditing and diagnostics.

    Attributes:
        id:         Auto-incrementing primary key.
        level:      Severity level.
        module:     Originating module / component name.
        action:     Short action tag (e.g. 'drone_dispatched').
        message:    Human-readable log message.
        metadata:   Arbitrary JSON payload for additional context.
        created_at: Timestamp (UTC).
    """

    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    level = Column(SAEnum(LogLevel), default=LogLevel.INFO, nullable=False)
    module = Column(String(100), nullable=False, index=True)
    action = Column(String(100), default="", nullable=False)
    message = Column(Text, default="")
    metadata = Column(JSON, default=dict)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Indexes
    __table_args__ = (
        Index("ix_system_logs_level_module", "level", "module"),
        Index("ix_system_logs_created", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<SystemLog id={self.id} level={self.level} module='{self.module}'>"
