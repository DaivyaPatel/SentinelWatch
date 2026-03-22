"""
Configuration module for the Urban Safety AI system.
Loads all settings from environment variables using Pydantic Settings.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    """
    Central configuration class. All values can be overridden via
    environment variables or a .env file in the project root.
    """

    # --- Application ---
    APP_NAME: str = "UrbanSafetyAI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # --- Database ---
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/urban_safety_db"

    # --- Redis ---
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- JWT ---
    JWT_SECRET_KEY: str = "change-me-in-production-super-secret-key"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # --- YOLO / AI ---
    YOLO_MODEL_PATH: str = "yolov8n.pt"
    YOLO_CONFIDENCE_THRESHOLD: float = 0.5

    # --- Drone Dispatch ---
    DRONE_BATTERY_THRESHOLD: int = 20       # Minimum battery % to dispatch
    MAX_DISPATCH_DISTANCE_KM: float = 50.0  # Maximum dispatch radius in km

    # --- Celery ---
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Return a cached Settings instance (read once from env)."""
    return Settings()
