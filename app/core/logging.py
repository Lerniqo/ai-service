"""
Structured JSON logging configuration for the AI Service.

This module provides structured JSON logging that outputs to stdout,
which is essential for observability in containerized environments.
It also provides colorized console logging for better development experience.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from rich.console import Console
from rich.logging import RichHandler
from rich.text import Text
from rich.highlighter import ReprHighlighter


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
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add extra fields if present
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)

        return json.dumps(log_entry, indent=2)


class ColorizedConsoleFormatter(logging.Formatter):
    """Custom formatter with colors and enhanced readability for console output."""
    
    # Color codes for different log levels
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'

    def __init__(self, service_name: str = "ai-service"):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record with colors and enhanced structure."""
        # Get timestamp
        timestamp = datetime.fromtimestamp(
            record.created, tz=timezone.utc
        ).strftime("%Y-%m-%d %H:%M:%S")
        
        # Get color for log level
        color = self.COLORS.get(record.levelname, '')
        
        # Format the main log line
        formatted_message = (
            f"{self.DIM}[{timestamp}]{self.RESET} "
            f"{color}{self.BOLD}{record.levelname:8}{self.RESET} "
            f"{self.BOLD}{self.service_name}{self.RESET} "
            f"{self.DIM}({record.module}:{record.lineno}){self.RESET} "
            f"→ {record.getMessage()}"
        )
        
        # Add exception info if present
        if record.exc_info:
            formatted_message += f"\n{self.COLORS['ERROR']}Exception:{self.RESET}\n"
            formatted_message += self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, 'extra_fields') and record.extra_fields:
            formatted_message += f"\n{self.DIM}Extra fields:{self.RESET}"
            for key, value in record.extra_fields.items():
                formatted_message += f"\n  {self.DIM}├─{self.RESET} {key}: {value}"
        
        return formatted_message


def configure_logging(
    service_name: str = "ai-service", 
    log_level: str = "INFO", 
    format_type: str = "console",
    enable_rich: bool = True
) -> logging.Logger:
    """
    Configure logging for the application with multiple formatting options.
    
    Args:
        service_name: Name of the service for logging context
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: Type of formatting - 'json', 'console', or 'rich'
        enable_rich: Whether to use Rich formatting (only applies to console mode)
    
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(service_name)
    logger.setLevel(getattr(logging, log_level.upper()))

    # Remove any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    if format_type == "rich" and enable_rich:
        # Use Rich handler for beautiful console output
        console = Console(stderr=False)
        handler = RichHandler(
            console=console,
            show_time=True,
            show_level=True,
            show_path=True,
            markup=True,
            rich_tracebacks=True,
            tracebacks_show_locals=True
        )
        handler.setLevel(getattr(logging, log_level.upper()))
        
    elif format_type == "console":
        # Use colorized console formatter
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(getattr(logging, log_level.upper()))
        formatter = ColorizedConsoleFormatter(service_name=service_name)
        handler.setFormatter(formatter)
        
    else:  # json format
        # Use structured JSON formatter
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


def get_default_logger(format_type: str = "console") -> logging.Logger:
    """
    Get a default configured logger for the AI service.
    
    Args:
        format_type: Type of formatting - 'json', 'console', or 'rich'
    
    Returns:
        Configured logger instance
    """
    return configure_logging(format_type=format_type)


def log_request(logger: logging.Logger, method: str, path: str, status_code: int, 
                duration_ms: float, **extra_fields: Any) -> None:
    """
    Log HTTP request information with structured data.
    
    Args:
        logger: The logger instance
        method: HTTP method
        path: Request path
        status_code: HTTP status code
        duration_ms: Request duration in milliseconds
        **extra_fields: Additional fields to include in the log
    """
    log_with_extra(
        logger, 
        "info", 
        f"{method} {path} - {status_code} ({duration_ms:.2f}ms)",
        http_method=method,
        path=path,
        status_code=status_code,
        duration_ms=duration_ms,
        **extra_fields
    )


def log_event(logger: logging.Logger, event_type: str, event_data: Dict[str, Any], 
              **extra_fields: Any) -> None:
    """
    Log event information with structured data.
    
    Args:
        logger: The logger instance
        event_type: Type of event
        event_data: Event data
        **extra_fields: Additional fields to include in the log
    """
    log_with_extra(
        logger,
        "info",
        f"Processing event: {event_type}",
        event_type=event_type,
        event_data=event_data,
        **extra_fields
    )
