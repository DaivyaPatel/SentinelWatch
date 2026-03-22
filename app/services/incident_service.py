"""
Incident management service — CRUD, timeline, and statistics.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.incident import Incident, IncidentType, IncidentStatus
from app.schemas.incident import (
    IncidentCreate, IncidentUpdate,
    IncidentResponse, IncidentListResponse,
)


async def create_incident(
    db: AsyncSession, data: IncidentCreate
) -> IncidentResponse:
    """Create a new incident record from detection or manual report."""
    incident = Incident(
        incident_type=IncidentType(data.incident_type),
        severity=data.severity,
        latitude=data.latitude,
        longitude=data.longitude,
        description=data.description,
        confidence_score=data.confidence_score,
        detection_metadata=data.detection_metadata,
        source=data.source,
    )
    db.add(incident)
    await db.flush()
    await db.refresh(incident)

    logger.info(
        "Incident created: id={} type={} severity={}",
        incident.id, incident.incident_type, incident.severity,
    )
    return IncidentResponse.model_validate(incident)


async def get_incident_by_id(
    db: AsyncSession, incident_id: int
) -> IncidentResponse:
    """
    Fetch a single incident.

    Raises:
        ValueError: If not found.
    """
    result = await db.execute(
        select(Incident).where(Incident.id == incident_id)
    )
    incident = result.scalar_one_or_none()
    if incident is None:
        raise ValueError(f"Incident with id {incident_id} not found")
    return IncidentResponse.model_validate(incident)


async def list_incidents(
    db: AsyncSession,
    status: Optional[str] = None,
    incident_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> IncidentListResponse:
    """List incidents with optional filters and pagination."""
    query = select(Incident)
    count_query = select(func.count(Incident.id))

    if status:
        query = query.where(Incident.status == IncidentStatus(status))
        count_query = count_query.where(Incident.status == IncidentStatus(status))
    if incident_type:
        query = query.where(Incident.incident_type == IncidentType(incident_type))
        count_query = count_query.where(Incident.incident_type == IncidentType(incident_type))

    query = query.offset(skip).limit(limit).order_by(desc(Incident.created_at))
    result = await db.execute(query)
    incidents = result.scalars().all()

    total = (await db.execute(count_query)).scalar() or 0

    return IncidentListResponse(
        total=total,
        incidents=[IncidentResponse.model_validate(i) for i in incidents],
    )


async def update_incident(
    db: AsyncSession, incident_id: int, data: IncidentUpdate
) -> IncidentResponse:
    """
    Partially update an incident.

    Raises:
        ValueError: If not found.
    """
    result = await db.execute(
        select(Incident).where(Incident.id == incident_id)
    )
    incident = result.scalar_one_or_none()
    if incident is None:
        raise ValueError(f"Incident with id {incident_id} not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "status" and value is not None:
            new_status = IncidentStatus(value)
            setattr(incident, field, new_status)
            # Auto-set resolved_at when marking resolved
            if new_status in (IncidentStatus.RESOLVED, IncidentStatus.FALSE_ALARM):
                incident.resolved_at = datetime.now(timezone.utc)
        else:
            setattr(incident, field, value)

    await db.flush()
    await db.refresh(incident)

    logger.info("Incident updated: id={} fields={}", incident_id, list(update_data.keys()))
    return IncidentResponse.model_validate(incident)


async def get_active_incidents(db: AsyncSession) -> list[Incident]:
    """Get all active (non-resolved) incidents, ordered by severity desc."""
    result = await db.execute(
        select(Incident)
        .where(
            Incident.status.notin_([IncidentStatus.RESOLVED, IncidentStatus.FALSE_ALARM])
        )
        .order_by(desc(Incident.severity))
    )
    return list(result.scalars().all())


async def get_incident_stats(db: AsyncSession) -> dict:
    """Return aggregate statistics about incidents."""
    # Total counts by status
    status_counts = {}
    for s in IncidentStatus:
        count = (
            await db.execute(
                select(func.count(Incident.id)).where(Incident.status == s)
            )
        ).scalar() or 0
        status_counts[s.value] = count

    # Total counts by type
    type_counts = {}
    for t in IncidentType:
        count = (
            await db.execute(
                select(func.count(Incident.id)).where(Incident.incident_type == t)
            )
        ).scalar() or 0
        type_counts[t.value] = count

    total = (await db.execute(select(func.count(Incident.id)))).scalar() or 0

    return {
        "total_incidents": total,
        "by_status": status_counts,
        "by_type": type_counts,
    }


async def get_incident_timeline(
    db: AsyncSession, limit: int = 100
) -> list[IncidentResponse]:
    """Get a chronological timeline of recent incidents."""
    result = await db.execute(
        select(Incident).order_by(desc(Incident.created_at)).limit(limit)
    )
    incidents = result.scalars().all()
    return [IncidentResponse.model_validate(i) for i in incidents]
