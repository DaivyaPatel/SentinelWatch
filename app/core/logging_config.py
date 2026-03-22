"""
Structured logging configuration using Loguru.
Provides console + rotating file output with JSON formatting.
"""

import sys
from loguru import logger

from app.core.config import get_settings

settings = get_settings()


def setup_logging() -> None:
    """
    Configure Loguru logger:
      - Console output with color
      - Rotating file output (10 MB per file, keep 7 days)
    """
    # Remove default handler
    logger.remove()

    # Console handler — coloured, human-readable
    logger.add(
        sys.stdout,
        level="DEBUG" if settings.DEBUG else "INFO",
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> — "
            "<level>{message}</level>"
        ),
        colorize=True,
    )

    # File handler — JSON format, auto-rotated
    logger.add(
        "logs/urban_safety_{time:YYYY-MM-DD}.log",
        level="INFO",
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        serialize=True,     # JSON output for log aggregation
        enqueue=True,       # Thread-safe async writes
    )

    logger.info("Logging initialised — debug={}", settings.DEBUG)
