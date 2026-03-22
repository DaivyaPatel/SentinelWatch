"""
Drone management service — CRUD operations and telemetry updates.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.drone import Drone, DroneStatus
from app.schemas.drone import (
    DroneCreate, DroneUpdate, DroneTelemetry,
    DroneResponse, DroneListResponse,
)


async def create_drone(db: AsyncSession, data: DroneCreate) -> DroneResponse:
    """
    Register a new drone in the fleet.

    Raises:
        ValueError: If drone name already exists.
    """
    existing = await db.execute(
        select(Drone).where(Drone.name == data.name)
    )
    if existing.scalar_one_or_none():
        raise ValueError(f"Drone with name '{data.name}' already exists")

    drone = Drone(
        name=data.name,
        model=data.model,
        latitude=data.latitude,
        longitude=data.longitude,
        battery_level=data.battery_level,
    )
    db.add(drone)
    await db.flush()
    await db.refresh(drone)

    logger.info("Drone registered: id={} name='{}'", drone.id, drone.name)
    return DroneResponse.model_validate(drone)


async def get_drone_by_id(db: AsyncSession, drone_id: int) -> DroneResponse:
    """
    Fetch a single drone by its ID.

    Raises:
        ValueError: If drone not found.
    """
    result = await db.execute(select(Drone).where(Drone.id == drone_id))
    drone = result.scalar_one_or_none()
    if drone is None:
        raise ValueError(f"Drone with id {drone_id} not found")
    return DroneResponse.model_validate(drone)


async def list_drones(
    db: AsyncSession,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> DroneListResponse:
    """List drones with optional status filter and pagination."""
    query = select(Drone).where(Drone.is_active == True)
    if status:
        query = query.where(Drone.status == DroneStatus(status))
    query = query.offset(skip).limit(limit).order_by(Drone.id)

    result = await db.execute(query)
    drones = result.scalars().all()

    # Get total count
    count_query = select(func.count(Drone.id)).where(Drone.is_active == True)
    if status:
        count_query = count_query.where(Drone.status == DroneStatus(status))
    total = (await db.execute(count_query)).scalar() or 0

    return DroneListResponse(
        total=total,
        drones=[DroneResponse.model_validate(d) for d in drones],
    )


async def update_drone(
    db: AsyncSession, drone_id: int, data: DroneUpdate
) -> DroneResponse:
    """
    Partially update a drone record.

    Raises:
        ValueError: If drone not found.
    """
    result = await db.execute(select(Drone).where(Drone.id == drone_id))
    drone = result.scalar_one_or_none()
    if drone is None:
        raise ValueError(f"Drone with id {drone_id} not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "status" and value is not None:
            setattr(drone, field, DroneStatus(value))
        else:
            setattr(drone, field, value)

    await db.flush()
    await db.refresh(drone)

    logger.info("Drone updated: id={} fields={}", drone_id, list(update_data.keys()))
    return DroneResponse.model_validate(drone)


async def update_telemetry(
    db: AsyncSession, drone_id: int, data: DroneTelemetry
) -> DroneResponse:
    """
    Update real-time telemetry data for a drone.

    Raises:
        ValueError: If drone not found.
    """
    result = await db.execute(select(Drone).where(Drone.id == drone_id))
    drone = result.scalar_one_or_none()
    if drone is None:
        raise ValueError(f"Drone with id {drone_id} not found")

    drone.latitude = data.latitude
    drone.longitude = data.longitude
    drone.altitude = data.altitude
    drone.speed = data.speed
    drone.battery_level = data.battery_level
    drone.last_heartbeat = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(drone)

    logger.debug(
        "Telemetry updated: drone_id={} pos=({}, {}) battery={}%",
        drone_id, data.latitude, data.longitude, data.battery_level,
    )
    return DroneResponse.model_validate(drone)


async def get_available_drones(
    db: AsyncSession, min_battery: float = 20.0
) -> list[Drone]:
    """
    Get drones that are idle and have sufficient battery for dispatch.
    Returns raw ORM objects for use by the dispatch engine.
    """
    result = await db.execute(
        select(Drone).where(
            Drone.status == DroneStatus.IDLE,
            Drone.is_active == True,
            Drone.battery_level >= min_battery,
        )
    )
    return list(result.scalars().all())


async def delete_drone(db: AsyncSession, drone_id: int) -> None:
    """
    Soft-delete a drone (set is_active=False).

    Raises:
        ValueError: If drone not found.
    """
    result = await db.execute(select(Drone).where(Drone.id == drone_id))
    drone = result.scalar_one_or_none()
    if drone is None:
        raise ValueError(f"Drone with id {drone_id} not found")

    drone.is_active = False
    await db.flush()
    logger.info("Drone soft-deleted: id={}", drone_id)
