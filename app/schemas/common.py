"""
Shared / common Pydantic schemas used across the application.
"""

from pydantic import BaseModel
from typing import Optional, Any


class HealthResponse(BaseModel):
    """GET /health response."""
    status: str = "ok"
    version: str
    uptime_seconds: float


class MessageResponse(BaseModel):
    """Generic message response."""
    message: str
    detail: Optional[str] = None


class PaginationParams(BaseModel):
    """Query parameters for paginated endpoints."""
    skip: int = 0
    limit: int = 50


class PaginatedResponse(BaseModel):
    """Wrapper for paginated list responses."""
    total: int
    skip: int
    limit: int
    items: list[Any]
