"""Tests for the base client functionality."""
import os
import pytest
import httpx
from unittest.mock import patch

from app.clients.base_client import BaseClient, ServiceClientError

pytestmark = pytest.mark.asyncio


class MockBaseClient(BaseClient):
    """Test client implementation for testing BaseClient functionality."""
    
    BASE_URL_ENV = "TEST_SERVICE_BASE_URL"
    SECRET_ENV = "TEST_SERVICE_SECRET"


async def test_base_client_initialization_with_params():
    """Test BaseClient initialization with direct parameters."""
    client = MockBaseClient(base_url="https://test.example.com", secret="test-secret")
    
    assert client.base_url == "https://test.example.com"
    assert client.secret == "test-secret"
    
    await client.close()


async def test_base_client_initialization_without_base_url_raises_error():
    """Test BaseClient initialization without base_url raises ValueError."""
    with pytest.raises(ValueError, match="base_url is required"):
        MockBaseClient()


async def test_base_client_get_success():
    """Test successful GET request."""
    base_url = "https://test.example.com"
    secret = "test-secret"
    
    def handler(request: httpx.Request) -> httpx.Response:
        # The headers will be set on the client, not on individual requests
        # when using an external client
        assert request.url.path == "/test-endpoint"
        return httpx.Response(200, json={"message": "success"})

    transport = httpx.MockTransport(handler)
    # Create client with headers for auth
    headers = {"Authorization": f"Bearer {secret}"} if secret else {}
    async with httpx.AsyncClient(base_url=base_url, transport=transport, headers=headers) as http_client:
        client = MockBaseClient(base_url=base_url, secret=secret, client=http_client)
        result = await client._get("/test-endpoint")
        assert result == {"message": "success"}


async def test_base_client_get_non_json_response():
    """Test GET request that returns non-JSON response."""
    base_url = "https://test.example.com"
    
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content="plain text response", headers={"content-type": "text/plain"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(base_url=base_url, transport=transport) as http_client:
        client = MockBaseClient(base_url=base_url, client=http_client)
        result = await client._get("/test-endpoint")
        assert result == "plain text response"


async def test_base_client_get_http_error():
    """Test GET request with HTTP error response."""
    base_url = "https://test.example.com"
    
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "Not found"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(base_url=base_url, transport=transport) as http_client:
        client = MockBaseClient(base_url=base_url, client=http_client)
        
        with pytest.raises(ServiceClientError) as exc_info:
            await client._get("/not-found")
        
        assert exc_info.value.status_code == 404
        assert exc_info.value.payload == {"error": "Not found"}


async def test_base_client_get_network_error():
    """Test GET request with network error."""
    base_url = "https://test.example.com"
    
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection failed")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(base_url=base_url, transport=transport) as http_client:
        client = MockBaseClient(base_url=base_url, client=http_client)
        
        with pytest.raises(ServiceClientError, match="Network error calling service"):
            await client._get("/test-endpoint")


async def test_base_client_context_manager():
    """Test BaseClient as async context manager."""
    base_url = "https://test.example.com"
    
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"message": "success"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(base_url=base_url, transport=transport) as http_client:
        async with MockBaseClient(base_url=base_url, client=http_client) as client:
            result = await client._get("/test-endpoint")
            assert result == {"message": "success"}


@patch('app.config.get_settings')
async def test_base_client_env_var_resolution(mock_get_settings):
    """Test BaseClient environment variable resolution through settings."""
    # Mock settings object
    mock_settings = type('MockSettings', (), {
        'TEST_SERVICE_BASE_URL': 'https://env.example.com',
        'TEST_SERVICE_SECRET': 'env-secret'
    })()
    mock_get_settings.return_value = mock_settings
    
    client = MockBaseClient()
    
    assert client.base_url == "https://env.example.com"
    assert client.secret == "env-secret"
    
    await client.close()
