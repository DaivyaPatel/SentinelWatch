"""
Seed data script — populates the database with initial dummy data.

Usage:
    python -m scripts.seed_data

Creates:
  - 1 admin user + 1 operator user
  - 5 sample drones
  - 3 sample incidents
  - 2 no-fly zones
"""

import asyncio
from datetime import datetime, timezone

from app.core.database import async_session_factory, engine, Base
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.models.drone import Drone, DroneStatus
from app.models.incident import Incident, IncidentType, IncidentStatus
from app.models.alert import Alert, AlertPriority
from app.models.geofence import NoFlyZone

# Import all models to register them
from app.models import user, drone, incident, alert, log, geofence  # noqa


async def seed():
    """Populate the database with sample data."""

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as db:
        # ── Check if already seeded ──
        from sqlalchemy import select, func
        count = (await db.execute(select(func.count(User.id)))).scalar() or 0
        if count > 0:
            print("⚠️  Database already has data — skipping seed. Drop tables first to re-seed.")
            return

        # ── Users ──
        admin = User(
            username="admin",
            email="admin@urbansafety.ai",
            hashed_password=hash_password("admin123"),
            role=UserRole.ADMIN,
        )
        operator = User(
            username="operator_01",
            email="operator@urbansafety.ai",
            hashed_password=hash_password("operator123"),
            role=UserRole.OPERATOR,
        )
        db.add_all([admin, operator])
        await db.flush()
        print("✅ Users created: admin (admin123), operator_01 (operator123)")

        # ── Drones ──
        drones_data = [
            Drone(
                name="Drone-Alpha-01",
                model="DJI-Matrice-300",
                battery_level=95.0,
                latitude=28.6139,
                longitude=77.2090,
                status=DroneStatus.IDLE,
            ),
            Drone(
                name="Drone-Beta-02",
                model="DJI-Matrice-300",
                battery_level=82.5,
                latitude=28.6280,
                longitude=77.2170,
                status=DroneStatus.IDLE,
            ),
            Drone(
                name="Drone-Gamma-03",
                model="Skydio-X2",
                battery_level=67.0,
                latitude=28.5921,
                longitude=77.2290,
                status=DroneStatus.IDLE,
            ),
            Drone(
                name="Drone-Delta-04",
                model="Skydio-X2",
                battery_level=45.0,
                latitude=28.6350,
                longitude=77.1980,
                status=DroneStatus.CHARGING,
            ),
            Drone(
                name="Drone-Echo-05",
                model="Autel-Evo-II",
                battery_level=12.0,
                latitude=28.6100,
                longitude=77.2300,
                status=DroneStatus.MAINTENANCE,
            ),
        ]
        db.add_all(drones_data)
        await db.flush()
        print(f"✅ Drones created: {len(drones_data)} drones")

        # ── Incidents ──
        incidents_data = [
            Incident(
                incident_type=IncidentType.FIRE,
                severity=8,
                latitude=28.6200,
                longitude=77.2150,
                status=IncidentStatus.DETECTED,
                description="Fire detected near commercial district — smoke visible",
                confidence_score=0.92,
                detection_metadata={
                    "detections": [
                        {"label": "fire", "confidence": 0.92, "bbox": [120, 80, 350, 290]}
                    ]
                },
                source="camera_001",
            ),
            Incident(
                incident_type=IncidentType.ACCIDENT,
                severity=6,
                latitude=28.6300,
                longitude=77.2050,
                status=IncidentStatus.CONFIRMED,
                description="Vehicle collision at intersection — 2 cars involved",
                confidence_score=0.85,
                source="camera_015",
            ),
            Incident(
                incident_type=IncidentType.CROWD_ANOMALY,
                severity=5,
                latitude=28.6100,
                longitude=77.2250,
                status=IncidentStatus.DETECTED,
                description="Unusual crowd gathering near public park",
                confidence_score=0.78,
                source="camera_008",
            ),
        ]
        db.add_all(incidents_data)
        await db.flush()
        print(f"✅ Incidents created: {len(incidents_data)} incidents")

        # ── Alerts ──
        alerts_data = [
            Alert(
                incident_id=1,
                priority=AlertPriority.CRITICAL,
                title="FIRE detected — Severity 8",
                message="Fire detected near commercial district. Immediate drone dispatch recommended.",
            ),
            Alert(
                incident_id=2,
                priority=AlertPriority.HIGH,
                title="ACCIDENT detected — Severity 6",
                message="Vehicle collision at intersection. Emergency services notified.",
            ),
            Alert(
                incident_id=3,
                priority=AlertPriority.MEDIUM,
                title="CROWD ANOMALY detected — Severity 5",
                message="Unusual crowd gathering detected near public park.",
            ),
        ]
        db.add_all(alerts_data)
        await db.flush()
        print(f"✅ Alerts created: {len(alerts_data)} alerts")

        # ── No-Fly Zones ──
        zones_data = [
            NoFlyZone(
                name="Delhi Airport Zone",
                description="Indira Gandhi International Airport restricted airspace",
                center_lat=28.5665,
                center_lon=77.1031,
                radius_km=5.0,
            ),
            NoFlyZone(
                name="Government Complex Zone",
                description="Central government buildings restricted area",
                center_lat=28.6143,
                center_lon=77.1994,
                radius_km=2.0,
            ),
        ]
        db.add_all(zones_data)
        await db.flush()
        print(f"✅ No-fly zones created: {len(zones_data)} zones")

        await db.commit()
        print("\n🎉 Seed data loaded successfully!")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("Login credentials:")
        print("  Admin    → admin / admin123")
        print("  Operator → operator_01 / operator123")


if __name__ == "__main__":
    asyncio.run(seed())
