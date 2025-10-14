"""Client for interacting with the Content Service."""
from __future__ import annotations

from typing import Any

from .base_client import BaseClient

class ContentServiceClient(BaseClient):
    """Client for the content service.

    Environment variables (optional):
      - CONTENT_SERVICE_BASE_URL
      - CONTENT_SERVICE_SECRET
    """

    BASE_URL_ENV = "CONTENT_SERVICE_BASE_URL"
    SECRET_ENV = "CONTENT_SERVICE_SECRET"

    async def get_concept_graph(self) -> Any:
        """Fetch the concept graph from the content service."""
        return await self._get("/concept-graph")
    
