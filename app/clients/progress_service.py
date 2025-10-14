"""Client for interacting with the Progress Service."""
from __future__ import annotations

from typing import Any, Optional
import httpx

from .base_client import BaseClient

class ProgressServiceClient(BaseClient):
    """Client for the progress service.

    Environment variables (optional):
      - PROGRESS_SERVICE_BASE_URL
      - PROGRESS_SERVICE_SECRET
    """

    BASE_URL_ENV = "PROGRESS_SERVICE_BASE_URL"
    SECRET_ENV = "PROGRESS_SERVICE_SECRET"

    def __init__(
        self,
        base_url: Optional[str] = None,
        secret: Optional[str] = None,
        *,
        timeout: float = 10.0,
        client: Optional[httpx.AsyncClient] = None,
    ):
        super().__init__(base_url=base_url, secret=secret, timeout=timeout, client=client)

    async def get_student_interaction_history(self, student_id: str) -> Any:
        """Fetch a student's interaction history."""
        params = {"eventType": "QUESTION_ATTEMPT"}

        return await self._get(f"/events/user/{student_id}/stats", params=params)
