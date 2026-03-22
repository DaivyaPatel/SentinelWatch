"""
Geofencing service — validates coordinates against no-fly zones.
"""

import math
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.geofence import NoFlyZone
from app.schemas.dispatch import (
    GeofenceCheckResponse, NoFlyZoneCreate, NoFlyZoneResponse,
)
from app.services.dispatch_service import haversine_km


async def check_geofence(
    db: AsyncSession,
    latitude: float,
    longitude: float,
) -> GeofenceCheckResponse:
    """
    Check if a coordinate falls within any active no-fly zone.

    Returns:
        GeofenceCheckResponse with restriction status and zone details.
    """
    result = await db.execute(
        select(NoFlyZone).where(NoFlyZone.is_active == True)
    )
    zones = result.scalars().all()

    for zone in zones:
        distance = haversine_km(latitude, longitude, zone.center_lat, zone.center_lon)
        if distance <= zone.radius_km:
            logger.warning(
                "Geofence violation: ({}, {}) inside zone '{}' (distance={:.2f}km, radius={:.2f}km)",
                latitude, longitude, zone.name, distance, zone.radius_km,
            )
            return GeofenceCheckResponse(
                is_restricted=True,
                zone_name=zone.name,
                zone_id=zone.id,
                message=f"Coordinate is inside no-fly zone '{zone.name}'",
            )

    return GeofenceCheckResponse(
        is_restricted=False,
        message="Coordinate is clear of all no-fly zones",
    )


async def check_path_geofence(
    db: AsyncSession,
    waypoints: list[tuple[float, float]],
) -> tuple[bool, Optional[str]]:
    """
    Check if any waypoint in a path crosses a no-fly zone.

    Args:
        waypoints: List of (lat, lon) tuples.

    Returns:
        (is_clear, zone_name): True if path is clear, zone_name if blocked.
    """
    result = await db.execute(
        select(NoFlyZone).where(NoFlyZone.is_active == True)
    )
    zones = result.scalars().all()

    for lat, lon in waypoints:
        for zone in zones:
            distance = haversine_km(lat, lon, zone.center_lat, zone.center_lon)
            if distance <= zone.radius_km:
                return False, zone.name

    return True, None


async def create_no_fly_zone(
    db: AsyncSession, data: NoFlyZoneCreate
) -> NoFlyZoneResponse:
    """
    Create a new no-fly zone.

    Raises:
        ValueError: If zone name already exists.
    """
    existing = await db.execute(
        select(NoFlyZone).where(NoFlyZone.name == data.name)
    )
    if existing.scalar_one_or_none():
        raise ValueError(f"No-fly zone '{data.name}' already exists")

    zone = NoFlyZone(
        name=data.name,
        description=data.description,
        center_lat=data.center_lat,
        center_lon=data.center_lon,
        radius_km=data.radius_km,
    )
    db.add(zone)
    await db.flush()
    await db.refresh(zone)

    logger.info("No-fly zone created: id={} name='{}'", zone.id, zone.name)
    return NoFlyZoneResponse.model_validate(zone)


async def list_no_fly_zones(
    db: AsyncSession, active_only: bool = True
) -> list[NoFlyZoneResponse]:
    """List all no-fly zones."""
    query = select(NoFlyZone)
    if active_only:
        query = query.where(NoFlyZone.is_active == True)
    result = await db.execute(query.order_by(NoFlyZone.id))
    zones = result.scalars().all()
    return [NoFlyZoneResponse.model_validate(z) for z in zones]


async def delete_no_fly_zone(db: AsyncSession, zone_id: int) -> None:
    """
    Soft-delete a no-fly zone (deactivate).

    Raises:
        ValueError: If zone not found.
    """
    result = await db.execute(select(NoFlyZone).where(NoFlyZone.id == zone_id))
    zone = result.scalar_one_or_none()
    if zone is None:
        raise ValueError(f"No-fly zone with id {zone_id} not found")

    zone.is_active = False
    await db.flush()
    logger.info("No-fly zone deactivated: id={}", zone_id)
