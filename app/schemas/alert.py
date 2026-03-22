"""
Alert-related Pydantic schemas.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------
class AlertCreate(BaseModel):
    """POST /alerts — create an alert (typically system-generated)."""
    incident_id: int = Field(..., examples=[1])
    priority: str = Field(
        default="medium",
        pattern="^(low|medium|high|critical)$",
        examples=["high"],
    )
    title: str = Field(..., max_length=200, examples=["Fire Detected - Sector 7"])
    message: str = Field(default="", examples=["High-confidence fire detected at camera_003"])


class AlertUpdate(BaseModel):
    """PATCH /alerts/{id} — mark as read, etc."""
    is_read: Optional[bool] = None
    priority: Optional[str] = Field(
        default=None,
        pattern="^(low|medium|high|critical)$",
    )


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------
class AlertResponse(BaseModel):
    """Standard alert response."""
    id: int
    incident_id: int
    priority: str
    title: str
    message: str
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertListResponse(BaseModel):
    """Response for listing alerts."""
    total: int
    alerts: list[AlertResponse]
