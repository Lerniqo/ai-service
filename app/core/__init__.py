"""
Core module containing shared utilities for the AI Service application.

This module includes:
- Logging configuration
- Exception handlers
- Other core utilities
"""

from .logging import configure_logging, log_with_extra, StructuredJSONFormatter
from .exceptions import http_exception_handler, general_exception_handler

__all__ = [
    "configure_logging",
    "log_with_extra", 
    "StructuredJSONFormatter",
    "http_exception_handler",
    "general_exception_handler",
]
