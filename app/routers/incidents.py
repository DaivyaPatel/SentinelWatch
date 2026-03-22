"""
Incident management router — CRUD, timeline, and statistics.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.websocket_manager import ws_manager
from app.models.user import User
from app.schemas.incident import (
    IncidentCreate, IncidentUpdate,
    IncidentResponse, IncidentListResponse,
)
from app.schemas.alert import AlertCreate
from app.services import incident_service, alert_service, dispatch_service

router = APIRouter(prefix="/incidents", tags=["Incident Management"])


@router.post(
    "",
    response_model=IncidentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Report a new incident",
)
async def create_incident(
    data: IncidentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Report a new incident. Automatically:
    1. Creates the incident record.
    2. Generates an alert.
    3. Attempts auto-dispatch if severity ≥ 7.
    4. Broadcasts via WebSocket.
    """
    incident = await incident_service.create_incident(db, data)

    # Auto-generate alert
    priority = "critical" if data.severity >= 8 else "high" if data.severity >= 6 else "medium"
    await alert_service.create_alert(
        db,
        AlertCreate(
            incident_id=incident.id,
            priority=priority,
            title=f"{data.incident_type.upper()} detected — Severity {data.severity}",
            message=data.description or f"Incident detected at ({data.latitude}, {data.longitude})",
        ),
    )

    # Broadcast incident creation
    await ws_manager.broadcast(
        {
            "event": "new_incident",
            "data": incident.model_dump(mode="json"),
        },
        channel="incidents",
    )

    # Auto-dispatch for high-severity incidents
    if data.severity >= 7:
        dispatch_result = await dispatch_service.auto_dispatch_for_incident(db, incident.id)
        if dispatch_result.success:
            # Refresh incident to get updated assigned_drone_id
            incident = await incident_service.get_incident_by_id(db, incident.id)

    return incident


@router.get(
    "",
    response_model=IncidentListResponse,
    summary="List incidents",
)
async def list_incidents(
    status_filter: Optional[str] = None,
    type_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List incidents with optional filters and pagination."""
    return await incident_service.list_incidents(
        db, status_filter, type_filter, skip, limit,
    )


@router.get(
    "/stats",
    summary="Get incident statistics",
)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return aggregate incident statistics by type and status."""
    return await incident_service.get_incident_stats(db)


@router.get(
    "/timeline",
    response_model=list[IncidentResponse],
    summary="Get incident timeline",
)
async def get_timeline(
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a chronological timeline of recent incidents."""
    return await incident_service.get_incident_timeline(db, limit)


@router.get(
    "/{incident_id}",
    response_model=IncidentResponse,
    summary="Get incident details",
)
async def get_incident(
    incident_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetch a single incident by ID."""
    try:
        return await incident_service.get_incident_by_id(db, incident_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch(
    "/{incident_id}",
    response_model=IncidentResponse,
    summary="Update an incident",
)
async def update_incident(
    incident_id: int,
    data: IncidentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an incident's status, severity, or assignment."""
    try:
        incident = await incident_service.update_incident(db, incident_id, data)
        # Broadcast update
        await ws_manager.broadcast(
            {
                "event": "incident_updated",
                "data": incident.model_dump(mode="json"),
            },
            channel="incidents",
        )
        return incident
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
