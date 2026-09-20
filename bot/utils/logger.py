"""
Structured logging configuration using loguru.
"""

import sys
from pathlib import Path
from typing import Optional

from loguru import logger

from bot.config import get_settings


def setup_logger():
    """
    Configure loguru logger with structured logging.
    """
    settings = get_settings()
    
    # Remove default handler
    logger.remove()
    
    # Console handler with color and formatting
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.log_level,
        colorize=True,
        backtrace=True,
        diagnose=True,
    )
    
    # File handler for all logs
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    logger.add(
        log_dir / "reyex_{time:YYYY-MM-DD}.log",
        rotation="00:00",  # New file at midnight
        retention="30 days",  # Keep logs for 30 days
        compression="zip",  # Compress old logs
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=settings.log_level,
        backtrace=True,
        diagnose=True,
    )
    
    # Separate error log file
    logger.add(
        log_dir / "errors_{time:YYYY-MM-DD}.log",
        rotation="00:00",
        retention="90 days",
        compression="zip",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="ERROR",
        backtrace=True,
        diagnose=True,
    )
    
    # JSON log file for structured parsing (useful for log aggregators)
    logger.add(
        log_dir / "structured_{time:YYYY-MM-DD}.json",
        rotation="00:00",
        retention="30 days",
        compression="zip",
        format="{message}",  # Loguru will serialize as JSON
        level=settings.log_level,
        serialize=True,  # Enable JSON serialization
    )
    
    # Set up Sentry integration if DSN is provided
    if settings.sentry_dsn:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.loguru import LoguruIntegration
            
            sentry_sdk.init(
                dsn=settings.sentry_dsn,
                integrations=[LoguruIntegration()],
                traces_sample_rate=1.0,
                profiles_sample_rate=1.0,
            )
            logger.info("Sentry integration enabled")
        except ImportError:
            logger.warning("Sentry SDK not installed, skipping Sentry integration")
        except Exception as e:
            logger.error(f"Failed to initialize Sentry: {e}")
    
    logger.info(f"Logger configured with level: {settings.log_level}")


def get_logger(name: Optional[str] = None):
    """
    Get a logger instance with optional name context.
    
    Args:
        name: Optional name for the logger context
        
    Returns:
        loguru logger instance
    """
    if name:
        return logger.bind(name=name)
    return logger


# Auto-setup on import
setup_logger()
