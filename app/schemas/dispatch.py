"""
Dispatch & routing related Pydantic schemas.
"""

from typing import Optional
from pydantic import BaseModel, Field


class DispatchRequest(BaseModel):
    """POST /dispatch — request drone dispatch for an incident."""
    incident_id: int = Field(..., examples=[1])
    force_drone_id: Optional[int] = Field(
        default=None,
        description="Optionally force a specific drone (bypasses auto-selection).",
    )


class DispatchResponse(BaseModel):
    """Response from the dispatch engine."""
    success: bool
    incident_id: int
    assigned_drone_id: Optional[int] = None
    drone_name: Optional[str] = None
    distance_km: Optional[float] = None
    estimated_eta_seconds: Optional[float] = None
    message: str


class Waypoint(BaseModel):
    """A single GPS waypoint in a route."""
    latitude: float
    longitude: float
    altitude: float = 50.0
    order: int


class RouteResponse(BaseModel):
    """Planned route from drone position to incident location."""
    drone_id: int
    incident_id: int
    waypoints: list[Waypoint]
    total_distance_km: float
    estimated_time_seconds: float
    geofence_clear: bool
    rerouted: bool = False
    message: str


class GeofenceCheckRequest(BaseModel):
    """POST /geofencing/check — validate a coordinate against no-fly zones."""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class GeofenceCheckResponse(BaseModel):
    """Response from geofence check."""
    is_restricted: bool
    zone_name: Optional[str] = None
    zone_id: Optional[int] = None
    message: str


class NoFlyZoneCreate(BaseModel):
    """POST /geofencing/zones — create a no-fly zone."""
    name: str = Field(..., max_length=200, examples=["Airport Zone A"])
    description: str = Field(default="", examples=["International airport restricted airspace"])
    center_lat: float = Field(..., ge=-90, le=90, examples=[28.5665])
    center_lon: float = Field(..., ge=-180, le=180, examples=[77.1031])
    radius_km: float = Field(..., gt=0, examples=[5.0])


class NoFlyZoneResponse(BaseModel):
    """Standard no-fly zone response."""
    id: int
    name: str
    description: str
    center_lat: float
    center_lon: float
    radius_km: float
    is_active: bool

    model_config = {"from_attributes": True}
