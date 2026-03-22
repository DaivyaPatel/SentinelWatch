"""
Drone-related Pydantic schemas.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------
class DroneCreate(BaseModel):
    """POST /drones — register a new drone."""
    name: str = Field(..., min_length=1, max_length=100, examples=["Drone-Alpha-01"])
    model: str = Field(default="Generic-UAV", max_length=100, examples=["DJI-Matrice-300"])
    latitude: float = Field(..., ge=-90, le=90, examples=[28.6139])
    longitude: float = Field(..., ge=-180, le=180, examples=[77.2090])
    battery_level: float = Field(default=100.0, ge=0, le=100, examples=[95.0])


class DroneUpdate(BaseModel):
    """PATCH /drones/{id} — partial update."""
    name: Optional[str] = Field(default=None, max_length=100)
    model: Optional[str] = Field(default=None, max_length=100)
    status: Optional[str] = Field(
        default=None,
        pattern="^(idle|dispatched|returning|charging|maintenance|offline)$",
    )
    is_active: Optional[bool] = None


class DroneTelemetry(BaseModel):
    """PUT /drones/{id}/telemetry — real-time telemetry update from drone."""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    altitude: float = Field(default=0.0, ge=0)
    speed: float = Field(default=0.0, ge=0)
    battery_level: float = Field(..., ge=0, le=100)


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------
class DroneResponse(BaseModel):
    """Standard drone response."""
    id: int
    name: str
    model: str
    battery_level: float
    latitude: float
    longitude: float
    altitude: float
    speed: float
    status: str
    is_active: bool
    last_heartbeat: datetime
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DroneListResponse(BaseModel):
    """Response for listing drones."""
    total: int
    drones: list[DroneResponse]
