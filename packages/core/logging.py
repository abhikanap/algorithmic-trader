"""Logging configuration using structlog."""

import logging
import logging.config
import os
import sys
from pathlib import Path
from typing import Any, Dict

import structlog
import yaml

from .config import settings


def setup_logging() -> None:
    """Set up structured logging configuration."""
    
    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Load logging configuration
    logging_config_path = settings.config_path / "logging.yaml"
    
    if logging_config_path.exists():
        with open(logging_config_path, "r") as f:
            config = yaml.safe_load(f)
        logging.config.dictConfig(config)
    else:
        # Fallback configuration
        logging.basicConfig(
            level=getattr(logging, settings.log_level.upper()),
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler("logs/app.log"),
            ]
        )
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.JSONRenderer() if not settings.debug else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level.upper())
        ),
        logger_factory=structlog.WriteLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


# Initialize logging on import
setup_logging()
