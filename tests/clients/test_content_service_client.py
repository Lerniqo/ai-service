import os
import pytest
import httpx

from app.clients.content_service import ContentServiceClient

pytestmark = pytest.mark.asyncio

async def test_get_concept_graph_returns_data():
    base_url = "https://content.example.com"
    secret = "secret-token"
    os.environ["CONTENT_SERVICE_BASE_URL"] = base_url
    os.environ["CONTENT_SERVICE_SECRET"] = secret

    def handler(request: httpx.Request) -> httpx.Response:  # synchronous handler allowed
        assert request.url.path == "/concept-graph"
        return httpx.Response(200, json={"nodes": 5})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(base_url=base_url, transport=transport) as http_client:
        client = ContentServiceClient(base_url=base_url, secret=secret, client=http_client)
        data = await client.get_concept_graph()
        assert data == {"nodes": 5}
