"""
Urban Safety AI — FastAPI Application Entry Point.

This is the main application module that:
  1. Creates the FastAPI app with metadata.
  2. Registers all API routers.
  3. Sets up CORS, logging, and startup/shutdown events.
  4. Creates database tables on startup.
  5. Provides a health check endpoint.
"""

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.core.config import get_settings
from app.core.database import engine, Base
from app.core.logging_config import setup_logging

# Import all models so Base.metadata knows about them
from app.models import user, drone, incident, alert, log, geofence  # noqa: F401

# Import routers
from app.routers import (
    auth,
    drones,
    incidents,
    alerts,
    detection,
    dispatch,
    geofencing,
    dashboard,
    websockets,
)

settings = get_settings()

# Track app start time for health check uptime
_start_time: float = 0.0


# ---------------------------------------------------------------------------
# Lifespan — startup and shutdown hooks
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles application startup and shutdown."""
    global _start_time

    # ── STARTUP ──
    setup_logging()
    logger.info("🚀 {} v{} starting up...", settings.APP_NAME, settings.APP_VERSION)

    # Create all tables (in production, use Alembic migrations instead)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Database tables created/verified")

    _start_time = time.time()
    logger.info("✅ Application ready")

    yield

    # ── SHUTDOWN ──
    logger.info("🛑 {} shutting down...", settings.APP_NAME)
    await engine.dispose()
    logger.info("✅ Database connections closed")


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "AI-Powered Urban Safety System with Autonomous Drone Dispatch.\n\n"
        "Features:\n"
        "- 🔍 YOLOv8-based incident detection (fire, accidents, suspicious activity)\n"
        "- 🚁 Intelligent drone fleet management and dispatch\n"
        "- 📡 Real-time WebSocket communication\n"
        "- 🗺️ Geofence-aware route planning\n"
        "- 🔐 JWT authentication with role-based access\n"
        "- 📊 Dashboard APIs with statistics and timelines"
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS middleware
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],             # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Register routers under /api/v1 prefix
# ---------------------------------------------------------------------------
API_PREFIX = settings.API_V1_PREFIX

app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(drones.router, prefix=API_PREFIX)
app.include_router(incidents.router, prefix=API_PREFIX)
app.include_router(alerts.router, prefix=API_PREFIX)
app.include_router(detection.router, prefix=API_PREFIX)
app.include_router(dispatch.router, prefix=API_PREFIX)
app.include_router(geofencing.router, prefix=API_PREFIX)
app.include_router(dashboard.router, prefix=API_PREFIX)

# WebSocket routes don't get a prefix (they use /ws/...)
app.include_router(websockets.router)


# ---------------------------------------------------------------------------
# Health check endpoint
# ---------------------------------------------------------------------------
@app.get(
    "/health",
    tags=["System"],
    summary="Health check",
    response_model=dict,
)
async def health_check():
    """Returns system health status and uptime."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "uptime_seconds": round(time.time() - _start_time, 2),
    }


@app.get(
    "/",
    tags=["System"],
    summary="Root",
    include_in_schema=False,
)
async def root():
    """Root redirect to docs."""
    return {
        "message": f"Welcome to {settings.APP_NAME} v{settings.APP_VERSION}",
        "docs": "/docs",
        "health": "/health",
    }
