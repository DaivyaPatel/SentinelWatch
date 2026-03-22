"""
Routing service — basic path planning with geofence-aware rerouting.

Implements simple waypoint generation (straight-line with intermediate points)
and dynamic rerouting when paths cross no-fly zones.
"""

import math
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.services.dispatch_service import haversine_km, estimate_eta_seconds
from app.services.geofencing_service import check_path_geofence
from app.schemas.dispatch import Waypoint, RouteResponse


def _generate_waypoints(
    start_lat: float, start_lon: float,
    end_lat: float, end_lon: float,
    num_intermediate: int = 5,
    altitude: float = 50.0,
) -> list[Waypoint]:
    """
    Generate a straight-line path with evenly-spaced intermediate waypoints.

    Args:
        start_lat, start_lon: Start coordinates.
        end_lat, end_lon:     End coordinates.
        num_intermediate:     Number of intermediate waypoints.
        altitude:             Flight altitude in metres.

    Returns:
        List of Waypoint objects (start + intermediates + end).
    """
    waypoints = []
    total_points = num_intermediate + 2  # include start and end

    for i in range(total_points):
        fraction = i / (total_points - 1)
        lat = start_lat + fraction * (end_lat - start_lat)
        lon = start_lon + fraction * (end_lon - start_lon)
        waypoints.append(Waypoint(
            latitude=round(lat, 6),
            longitude=round(lon, 6),
            altitude=altitude,
            order=i,
        ))

    return waypoints


def _reroute_around_zone(
    waypoints: list[Waypoint],
    zone_lat: float,
    zone_lon: float,
    zone_radius_km: float,
) -> list[Waypoint]:
    """
    Simple rerouting: offset waypoints that fall inside a no-fly zone
    by pushing them radially outward to the zone boundary + buffer.

    This is a basic implementation — production systems would use
    proper path-planning algorithms (A*, RRT, etc.).
    """
    buffer_km = 0.5  # Extra clearance beyond zone boundary
    rerouted = []

    for wp in waypoints:
        dist = haversine_km(wp.latitude, wp.longitude, zone_lat, zone_lon)
        if dist < zone_radius_km + buffer_km:
            # Push the waypoint radially outward
            bearing = math.atan2(
                wp.longitude - zone_lon,
                wp.latitude - zone_lat,
            )
            push_dist_deg = (zone_radius_km + buffer_km) / 111.0  # Rough km→deg
            new_lat = zone_lat + push_dist_deg * math.cos(bearing)
            new_lon = zone_lon + push_dist_deg * math.sin(bearing)
            rerouted.append(Waypoint(
                latitude=round(new_lat, 6),
                longitude=round(new_lon, 6),
                altitude=wp.altitude,
                order=wp.order,
            ))
        else:
            rerouted.append(wp)

    return rerouted


async def plan_route(
    db: AsyncSession,
    drone_id: int,
    drone_lat: float,
    drone_lon: float,
    incident_id: int,
    incident_lat: float,
    incident_lon: float,
) -> RouteResponse:
    """
    Plan a route from a drone's current position to an incident location.

    Steps:
        1. Generate straight-line waypoints.
        2. Check for geofence violations.
        3. Reroute if necessary.
        4. Calculate total distance and ETA.
    """
    # 1. Generate initial path
    waypoints = _generate_waypoints(
        drone_lat, drone_lon,
        incident_lat, incident_lon,
    )

    rerouted = False

    # 2. Check geofence
    wp_tuples = [(wp.latitude, wp.longitude) for wp in waypoints]
    is_clear, zone_name = await check_path_geofence(db, wp_tuples)

    if not is_clear and zone_name:
        logger.info("Path crosses no-fly zone '{}' — rerouting", zone_name)

        # Get zone details for rerouting
        from app.models.geofence import NoFlyZone
        from sqlalchemy import select

        result = await db.execute(
            select(NoFlyZone).where(NoFlyZone.name == zone_name)
        )
        zone = result.scalar_one_or_none()

        if zone:
            waypoints = _reroute_around_zone(
                waypoints,
                zone.center_lat, zone.center_lon, zone.radius_km,
            )
            rerouted = True

    # 3. Calculate total distance
    total_distance = 0.0
    for i in range(len(waypoints) - 1):
        total_distance += haversine_km(
            waypoints[i].latitude, waypoints[i].longitude,
            waypoints[i + 1].latitude, waypoints[i + 1].longitude,
        )
    total_distance = round(total_distance, 3)

    # 4. ETA
    eta = estimate_eta_seconds(total_distance)

    # Determine geofence clearance on final route
    final_tuples = [(wp.latitude, wp.longitude) for wp in waypoints]
    final_clear, _ = await check_path_geofence(db, final_tuples)

    message = "Route planned successfully"
    if rerouted:
        message = f"Route rerouted to avoid no-fly zone '{zone_name}'"
    if not final_clear:
        message += " (WARNING: rerouted path may still clip restricted airspace)"

    return RouteResponse(
        drone_id=drone_id,
        incident_id=incident_id,
        waypoints=waypoints,
        total_distance_km=total_distance,
        estimated_time_seconds=eta,
        geofence_clear=final_clear,
        rerouted=rerouted,
        message=message,
    )
