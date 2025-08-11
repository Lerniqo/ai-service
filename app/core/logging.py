"""
Structured JSON logging configuration for the AI Service.

This module provides structured JSON logging that outputs to stdout,
which is essential for observability in containerized environments.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict


class StructuredJSONFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON logs."""

    def __init__(self, service_name: str = "ai-service"):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as structured JSON."""
        log_entry = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "service_name": self.service_name,
            "log_level": record.levelname,
            "message": record.getMessage()
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add extra fields if present
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)

        return json.dumps(log_entry)


def configure_logging(service_name: str = "ai-service", log_level: str = "INFO") -> logging.Logger:
    """
    Configure structured JSON logging for the application.
    
    Args:
        service_name: Name of the service for logging context
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(service_name)
    logger.setLevel(getattr(logging, log_level.upper()))

    # Remove any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create stdout handler with structured JSON formatter
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, log_level.upper()))
    
    formatter = StructuredJSONFormatter(service_name=service_name)
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    
    # Prevent duplicate logs
    logger.propagate = False

    return logger


def log_with_extra(logger: logging.Logger, level: str, message: str, **extra_fields: Any) -> None:
    """
    Log a message with additional structured fields.
    
    Args:
        logger: The logger instance
        level: Log level (info, error, warning, debug)
        message: Log message
        **extra_fields: Additional fields to include in the log
    """
    log_func = getattr(logger, level.lower())
    
    # Create a custom LogRecord with extra fields
    record = logger.makeRecord(
        logger.name, 
        getattr(logging, level.upper()), 
        __file__, 
        0, 
        message, 
        (), 
        None
    )
    record.extra_fields = extra_fields
    
    logger.handle(record)
