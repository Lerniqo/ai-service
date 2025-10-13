"""Client for interacting with the Progress Service."""
from __future__ import annotations

from typing import Any

from .base_client import BaseClient

class ProgressServiceClient(BaseClient):
    """Client for the progress service.

    Environment variables (optional):
      - PROGRESS_SERVICE_BASE_URL
      - PROGRESS_SERVICE_SECRET
    """

    BASE_URL_ENV = "PROGRESS_SERVICE_BASE_URL"
    SECRET_ENV = "PROGRESS_SERVICE_SECRET"

    async def get_student_interaction_history(self, student_id: str) -> Any:
        """Fetch a student's interaction history."""
        return await self._get(f"/events/user/{student_id}/interactions?eventType=QUESTION_ATTEMPT&limit=100")
