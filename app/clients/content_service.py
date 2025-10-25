"""Client for interacting with the Content Service."""
from __future__ import annotations

from typing import Any, List, Dict

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
    
    async def get_available_resources(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Fetch available learning resources for a user.
        
        Args:
            user_id: The user's unique identifier
            
        Returns:
            List of available resources with metadata
        """
        return await self._get(f"/users/{user_id}/resources")
    
    async def get_user_mastery_score(self, user_id: str) -> Dict[str, Any]:
        """
        Fetch the user's mastery scores across different concepts/skills.
        
        Args:
            user_id: The user's unique identifier
            
        Returns:
            Dictionary containing mastery scores and related metrics
        """
        return await self._get(f"/users/{user_id}/mastery-scores")
    
    async def send_generated_questions(self, request_id: str, questions_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send generated questions back to the content service.
        
        Args:
            request_id: The unique identifier for the question generation request
            questions_data: The generated questions data to send
            
        Returns:
            Response from the content service confirming receipt
        """
        return await self._post(f"/questions/generated/{request_id}", json=questions_data)

