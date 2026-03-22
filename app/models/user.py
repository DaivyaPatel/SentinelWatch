"""
User model — represents system operators and administrators.
"""

import enum
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Enum as SAEnum, Index
)
from app.core.database import Base


class UserRole(str, enum.Enum):
    """Allowed user roles."""
    ADMIN = "admin"
    OPERATOR = "operator"


class User(Base):
    """
    Stores user credentials and profile information.

    Attributes:
        id:              Auto-incrementing primary key.
        username:        Unique login name.
        email:           Unique email address.
        hashed_password: Bcrypt-hashed password.
        role:            'admin' or 'operator'.
        is_active:       Soft-delete / deactivation flag.
        created_at:      Record creation timestamp (UTC).
        updated_at:      Last modification timestamp (UTC).
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SAEnum(UserRole), default=UserRole.OPERATOR, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

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

    # Composite index for common lookups
    __table_args__ = (
        Index("ix_users_role_active", "role", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} username='{self.username}' role={self.role}>"
