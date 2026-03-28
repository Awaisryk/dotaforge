"""Structured logging configuration for DotaForge."""

import sys
from pathlib import Path

import structlog


def configure_logging():
    """Configure structured logging for the application."""
    
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Check debug mode (try to get from settings, default to False)
    try:
        from src.config import get_settings
        settings = get_settings()
        debug_mode = settings.debug
    except Exception:
        # Settings not loaded yet or error, use defaults
        debug_mode = False
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if not debug_mode 
            else structlog.dev.ConsoleRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Set up file logging
    import logging
    
    # Create file handler
    from datetime import datetime
    log_file = log_dir / f"dotaforge-{datetime.now().strftime('%Y-%m-%d')}.log"
    
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG if debug_mode else logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if debug_mode else logging.INFO)
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if debug_mode else logging.INFO)
    root_logger.handlers = [file_handler, console_handler]
    
    # Get the configured logger
    logger = structlog.get_logger("dotaforge")
    
    logger.info(
        "Logging configured",
        log_level="DEBUG" if debug_mode else "INFO",
        log_file=str(log_file),
        structured=not debug_mode
    )
    
    return logger


# Get logger instance
logger = configure_logging()
