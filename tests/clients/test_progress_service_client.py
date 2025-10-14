import os
import pytest
import httpx

from app.clients.progress_service import ProgressServiceClient

pytestmark = pytest.mark.asyncio

async def test_get_student_interaction_history_returns_data():
    base_url = "https://progress.example.com"
    secret = "progress-secret"
    os.environ["PROGRESS_SERVICE_BASE_URL"] = base_url
    os.environ["PROGRESS_SERVICE_SECRET"] = secret

    student_id = "student123"

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == f"/events/user/{student_id}/stats"
        assert str(request.url.params.get("eventType")) == "QUESTION_ATTEMPT"
        return httpx.Response(200, json={"studentId": student_id, "events": []})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(base_url=base_url, transport=transport) as http_client:
        client = ProgressServiceClient(base_url=base_url, secret=secret, client=http_client)
        data = await client.get_student_interaction_history(student_id)
        assert data == {"studentId": student_id, "events": []}
