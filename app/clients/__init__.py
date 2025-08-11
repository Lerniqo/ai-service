"""Service client modules for internal API communication.

This module provides HTTP clients for communicating with other internal services:
- ContentServiceClient: For accessing content and concept graph data
- ProgressServiceClient: For accessing student progress and interaction history
- BaseClient: Base class providing common functionality for service clients
"""

from .base_client import BaseClient, ServiceClientError
from .content_service import ContentServiceClient
from .progress_service import ProgressServiceClient

__all__ = [
    "BaseClient",
    "ServiceClientError", 
    "ContentServiceClient",
    "ProgressServiceClient",
]