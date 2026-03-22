"""
Incident-related Pydantic schemas.
"""

from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------
class IncidentCreate(BaseModel):
    """POST /incidents — create a new incident."""
    incident_type: str = Field(
        ...,
        pattern="^(fire|accident|suspicious_activity|crowd_anomaly|vandalism|other)$",
        examples=["fire"],
    )
    severity: int = Field(..., ge=1, le=10, examples=[8])
    latitude: float = Field(..., ge=-90, le=90, examples=[28.6139])
    longitude: float = Field(..., ge=-180, le=180, examples=[77.2090])
    description: str = Field(default="", examples=["Fire detected near intersection"])
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0, examples=[0.92])
    detection_metadata: dict[str, Any] = Field(default_factory=dict)
    source: str = Field(default="unknown", examples=["camera_001"])


class IncidentUpdate(BaseModel):
    """PATCH /incidents/{id} — update an existing incident."""
    status: Optional[str] = Field(
        default=None,
        pattern="^(detected|confirmed|dispatched|in_progress|resolved|false_alarm)$",
    )
    severity: Optional[int] = Field(default=None, ge=1, le=10)
    description: Optional[str] = None
    assigned_drone_id: Optional[int] = None


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------
class IncidentResponse(BaseModel):
    """Standard incident response."""
    id: int
    incident_type: str
    severity: int
    latitude: float
    longitude: float
    status: str
    description: str
    confidence_score: float
    detection_metadata: dict[str, Any]
    source: str
    assigned_drone_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime]

    model_config = {"from_attributes": True}


class IncidentListResponse(BaseModel):
    """Response for listing incidents."""
    total: int
    incidents: list[IncidentResponse]


class DetectionResult(BaseModel):
    """Single detection result from AI inference."""
    label: str
    confidence: float
    bbox: list[float]  # [x1, y1, x2, y2]
    incident_type: str


class DetectionResponse(BaseModel):
    """Response from the detection endpoint."""
    detections: list[DetectionResult]
    total_detections: int
    incident_created: bool
    incident_id: Optional[int] = None
