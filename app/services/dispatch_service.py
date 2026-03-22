"""
Intelligent Dispatch Engine — assigns drones to incidents using
Haversine distance, battery thresholds, and priority-based allocation.
"""

import math
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.drone import Drone, DroneStatus
from app.models.incident import Incident, IncidentStatus
from app.schemas.dispatch import DispatchRequest, DispatchResponse
from app.core.config import get_settings
from app.core.websocket_manager import ws_manager

settings = get_settings()


# ---------------------------------------------------------------------------
# Haversine distance calculation
# ---------------------------------------------------------------------------
def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points on Earth.

    Args:
        lat1, lon1: Coordinates of point A (degrees).
        lat2, lon2: Coordinates of point B (degrees).

    Returns:
        Distance in kilometres.
    """
    R = 6371.0  # Earth radius in km
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def estimate_eta_seconds(distance_km: float, speed_ms: float = 15.0) -> float:
    """
    Estimate time of arrival in seconds.

    Args:
        distance_km: Distance to travel (km).
        speed_ms:    Average drone speed in m/s (default 15 m/s ≈ 54 km/h).

    Returns:
        Estimated travel time in seconds.
    """
    if speed_ms <= 0:
        return float("inf")
    distance_m = distance_km * 1000
    return round(distance_m / speed_ms, 1)


# ---------------------------------------------------------------------------
# Drone scoring for dispatch
# ---------------------------------------------------------------------------
def _score_drone(
    drone: Drone,
    incident: Incident,
    max_distance: float,
) -> float:
    """
    Score a drone for dispatch to an incident. Lower score = better candidate.

    Scoring factors:
        1. Distance (normalised 0-1, weight 0.5)
        2. Battery (inverse, weight 0.3)
        3. Incident severity bonus (weight 0.2)
    """
    distance = haversine_km(
        drone.latitude, drone.longitude,
        incident.latitude, incident.longitude,
    )

    # Reject if beyond max dispatch range
    if distance > max_distance:
        return float("inf")

    # Reject if battery below threshold
    if drone.battery_level < settings.DRONE_BATTERY_THRESHOLD:
        return float("inf")

    # Normalised distance score (0 = closest, 1 = farthest)
    distance_score = distance / max_distance

    # Battery score (higher battery = lower score)
    battery_score = 1.0 - (drone.battery_level / 100.0)

    # Severity adjustment — high-severity incidents get a dispatch bonus
    severity_bonus = (10 - incident.severity) / 10.0 * 0.1

    return (distance_score * 0.5) + (battery_score * 0.3) + severity_bonus


# ---------------------------------------------------------------------------
# Main dispatch function
# ---------------------------------------------------------------------------
async def dispatch_drone(
    db: AsyncSession,
    request: DispatchRequest,
) -> DispatchResponse:
    """
    Assign the best available drone to an incident.

    Algorithm:
        1. Verify the incident exists and needs a drone.
        2. If force_drone_id is provided, use that drone directly.
        3. Otherwise, score all available drones and pick the best.
        4. Update drone status to DISPATCHED, incident status to DISPATCHED.
        5. Broadcast updates via WebSocket.

    Edge cases handled:
        - No drones available → returns failure with message.
        - All drones too far / low battery → returns fallback message.
        - Incident already has a drone assigned → returns info message.
    """
    # 1. Get the incident
    result = await db.execute(
        select(Incident).where(Incident.id == request.incident_id)
    )
    incident = result.scalar_one_or_none()
    if incident is None:
        return DispatchResponse(
            success=False,
            incident_id=request.incident_id,
            message=f"Incident {request.incident_id} not found",
        )

    # Check if already dispatched
    if incident.assigned_drone_id is not None:
        return DispatchResponse(
            success=False,
            incident_id=request.incident_id,
            assigned_drone_id=incident.assigned_drone_id,
            message="Incident already has a drone assigned",
        )

    # 2. Force-assign a specific drone if requested
    if request.force_drone_id is not None:
        drone_result = await db.execute(
            select(Drone).where(Drone.id == request.force_drone_id)
        )
        drone = drone_result.scalar_one_or_none()
        if drone is None:
            return DispatchResponse(
                success=False,
                incident_id=request.incident_id,
                message=f"Forced drone {request.force_drone_id} not found",
            )
        if drone.status != DroneStatus.IDLE:
            return DispatchResponse(
                success=False,
                incident_id=request.incident_id,
                message=f"Forced drone {drone.name} is not idle (status={drone.status.value})",
            )
    else:
        # 3. Auto-select: get all available drones and score them
        available = await db.execute(
            select(Drone).where(
                Drone.status == DroneStatus.IDLE,
                Drone.is_active == True,
                Drone.battery_level >= settings.DRONE_BATTERY_THRESHOLD,
            )
        )
        drones = list(available.scalars().all())

        if not drones:
            logger.warning(
                "No drones available for incident id={} severity={}",
                incident.id, incident.severity,
            )
            return DispatchResponse(
                success=False,
                incident_id=request.incident_id,
                message=(
                    "No drones available — all drones are either busy, offline, "
                    "or have insufficient battery"
                ),
            )

        # Score and rank
        scored = [
            (d, _score_drone(d, incident, settings.MAX_DISPATCH_DISTANCE_KM))
            for d in drones
        ]
        scored = [(d, s) for d, s in scored if s != float("inf")]

        if not scored:
            logger.warning(
                "All drones out of range or low battery for incident id={}",
                incident.id,
            )
            return DispatchResponse(
                success=False,
                incident_id=request.incident_id,
                message=(
                    "No suitable drones found — all candidates are either "
                    "too far away or have insufficient battery"
                ),
            )

        scored.sort(key=lambda x: x[1])
        drone = scored[0][0]

    # 4. Assign drone
    distance = haversine_km(
        drone.latitude, drone.longitude,
        incident.latitude, incident.longitude,
    )
    eta = estimate_eta_seconds(distance)

    drone.status = DroneStatus.DISPATCHED
    incident.assigned_drone_id = drone.id
    incident.status = IncidentStatus.DISPATCHED

    await db.flush()

    logger.info(
        "Drone dispatched: drone_id={} → incident_id={} distance={:.2f}km eta={:.0f}s",
        drone.id, incident.id, distance, eta,
    )

    # 5. Broadcast via WebSocket
    dispatch_event = {
        "event": "drone_dispatched",
        "data": {
            "drone_id": drone.id,
            "drone_name": drone.name,
            "incident_id": incident.id,
            "distance_km": round(distance, 2),
            "eta_seconds": eta,
        },
    }
    await ws_manager.broadcast(dispatch_event, channel="drones")
    await ws_manager.broadcast(dispatch_event, channel="incidents")

    return DispatchResponse(
        success=True,
        incident_id=incident.id,
        assigned_drone_id=drone.id,
        drone_name=drone.name,
        distance_km=round(distance, 2),
        estimated_eta_seconds=eta,
        message=f"Drone '{drone.name}' dispatched successfully",
    )


async def auto_dispatch_for_incident(
    db: AsyncSession, incident_id: int
) -> DispatchResponse:
    """
    Convenience wrapper: auto-dispatch a drone for a new incident.
    Called internally after incident creation if severity is high enough.
    """
    return await dispatch_drone(
        db,
        DispatchRequest(incident_id=incident_id),
    )
