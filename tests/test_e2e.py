"""End-to-end tests for the AI service application.

These tests verify the complete application workflow including:
- Application startup and basic functionality
- Service client integrations
- Configuration management
- Error handling across the full stack
"""

import os
import pytest
import httpx
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from app.main import app
from app.config import get_settings
from app.clients import ContentServiceClient, ProgressServiceClient


class TestApplicationStartup:
    """Test application startup and basic functionality."""
    
    def test_app_starts_successfully(self):
        """Test that the FastAPI application starts and responds to requests."""
        with TestClient(app) as client:
            response = client.get("/")
            assert response.status_code == 200
            assert response.json() == {"message": "Welcome to MyApp!"}
    
    def test_app_health_check(self):
        """Test basic health check endpoint."""
        with TestClient(app) as client:
            response = client.get("/")
            assert response.status_code == 200
            assert "message" in response.json()
    
    def test_cors_configuration(self):
        """Test that CORS middleware is properly configured."""
        with TestClient(app) as client:
            response = client.options(
                "/",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": "Content-Type"
                }
            )
            assert response.status_code == 200


class TestConfigurationManagement:
    """Test configuration and environment handling."""
    
    def test_default_configuration(self):
        """Test that configuration values are loaded correctly."""
        settings = get_settings()
        # Use the actual configured app name
        assert settings.APP_NAME in ["MyApp", "MyApp Dev"]  # Allow both default and development names
        assert settings.APP_VERSION == "1.0.0"
        assert settings.HOST == "127.0.0.1"
        assert settings.PORT == 8000
    
    def test_environment_detection(self):
        """Test environment detection based on ENV variable."""
        with patch.dict(os.environ, {"ENV": "testing"}):
            # Clear the cache to force reload
            get_settings.cache_clear()
            settings = get_settings()
            assert settings.ENV == "testing"
            assert settings.is_testing is True
            assert settings.is_development is False
            assert settings.is_production is False
    
    def test_service_configuration(self):
        """Test service client configuration from environment."""
        test_env = {
            "CONTENT_SERVICE_BASE_URL": "https://content.test.com",
            "CONTENT_SERVICE_SECRET": "content-secret",
            "PROGRESS_SERVICE_BASE_URL": "https://progress.test.com",
            "PROGRESS_SERVICE_SECRET": "progress-secret"
        }
        
        with patch.dict(os.environ, test_env):
            get_settings.cache_clear()
            settings = get_settings()
            assert settings.CONTENT_SERVICE_BASE_URL == "https://content.test.com"
            assert settings.CONTENT_SERVICE_SECRET == "content-secret"
            assert settings.PROGRESS_SERVICE_BASE_URL == "https://progress.test.com"
            assert settings.PROGRESS_SERVICE_SECRET == "progress-secret"


class TestServiceIntegration:
    """Test end-to-end service client integration."""
    
    @pytest.mark.asyncio
    async def test_content_service_integration(self):
        """Test complete content service integration workflow."""
        # Mock the external service
        def mock_handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/concept-graph":
                return httpx.Response(200, json={
                    "nodes": [
                        {"id": 1, "name": "Mathematics", "type": "subject"},
                        {"id": 2, "name": "Algebra", "type": "topic"}
                    ],
                    "edges": [
                        {"from": 1, "to": 2, "relationship": "contains"}
                    ]
                })
            return httpx.Response(404, json={"error": "Not found"})
        
        transport = httpx.MockTransport(mock_handler)
        
        # Test the complete workflow
        async with httpx.AsyncClient(
            base_url="https://content.test.com",
            transport=transport,
            headers={"Authorization": "Bearer test-secret"}
        ) as http_client:
            content_client = ContentServiceClient(
                base_url="https://content.test.com",
                secret="test-secret",
                client=http_client
            )
            
            # Get concept graph
            concept_graph = await content_client.get_concept_graph()
            
            # Verify the response structure
            assert "nodes" in concept_graph
            assert "edges" in concept_graph
            assert len(concept_graph["nodes"]) == 2
            assert len(concept_graph["edges"]) == 1
            
            # Verify node structure
            math_node = concept_graph["nodes"][0]
            assert math_node["name"] == "Mathematics"
            assert math_node["type"] == "subject"
    
    @pytest.mark.asyncio
    async def test_progress_service_integration(self):
        """Test complete progress service integration workflow."""
        student_id = "student-123"
        
        # Mock the external service
        def mock_handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == f"/students/{student_id}/interaction-history":
                return httpx.Response(200, json={
                    "studentId": student_id,
                    "events": [
                        {
                            "timestamp": "2025-08-11T10:00:00Z",
                            "action": "view_concept",
                            "conceptId": 1,
                            "duration": 120
                        },
                        {
                            "timestamp": "2025-08-11T10:05:00Z",
                            "action": "complete_exercise",
                            "conceptId": 2,
                            "score": 85
                        }
                    ]
                })
            return httpx.Response(404, json={"error": "Student not found"})
        
        transport = httpx.MockTransport(mock_handler)
        
        # Test the complete workflow
        async with httpx.AsyncClient(
            base_url="https://progress.test.com",
            transport=transport,
            headers={"Authorization": "Bearer progress-secret"}
        ) as http_client:
            progress_client = ProgressServiceClient(
                base_url="https://progress.test.com",
                secret="progress-secret",
                client=http_client
            )
            
            # Get student interaction history
            history = await progress_client.get_student_interaction_history(student_id)
            
            # Verify the response structure
            assert history["studentId"] == student_id
            assert "events" in history
            assert len(history["events"]) == 2
            
            # Verify event structure
            first_event = history["events"][0]
            assert first_event["action"] == "view_concept"
            assert first_event["conceptId"] == 1
            assert first_event["duration"] == 120
            
            second_event = history["events"][1]
            assert second_event["action"] == "complete_exercise"
            assert second_event["score"] == 85
    
    @pytest.mark.asyncio
    async def test_multi_service_workflow(self):
        """Test a workflow that uses multiple services together."""
        student_id = "student-456"
        
        # Mock content service
        def content_handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/concept-graph":
                return httpx.Response(200, json={
                    "nodes": [{"id": 1, "name": "Python", "difficulty": "intermediate"}],
                    "edges": []
                })
            return httpx.Response(404)
        
        # Mock progress service
        def progress_handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == f"/students/{student_id}/interaction-history":
                return httpx.Response(200, json={
                    "studentId": student_id,
                    "events": [{"action": "start_learning", "conceptId": 1}]
                })
            return httpx.Response(404)
        
        content_transport = httpx.MockTransport(content_handler)
        progress_transport = httpx.MockTransport(progress_handler)
        
        # Test workflow using both services
        async with httpx.AsyncClient(base_url="https://content.test.com", transport=content_transport) as content_http:
            async with httpx.AsyncClient(base_url="https://progress.test.com", transport=progress_transport) as progress_http:
                
                # Initialize clients
                content_client = ContentServiceClient(
                    base_url="https://content.test.com",
                    client=content_http
                )
                progress_client = ProgressServiceClient(
                    base_url="https://progress.test.com",
                    client=progress_http
                )
                
                # Simulate a learning workflow
                # 1. Get available concepts
                concept_graph = await content_client.get_concept_graph()
                available_concepts = concept_graph["nodes"]
                
                # 2. Get student's learning history
                history = await progress_client.get_student_interaction_history(student_id)
                student_events = history["events"]
                
                # 3. Verify data consistency
                assert len(available_concepts) > 0
                assert len(student_events) > 0
                assert available_concepts[0]["name"] == "Python"
                assert student_events[0]["conceptId"] == 1


class TestErrorHandling:
    """Test error handling across the full application stack."""
    
    @pytest.mark.asyncio
    async def test_service_unavailable_handling(self):
        """Test handling when external services are unavailable."""
        def error_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Service unavailable")
        
        transport = httpx.MockTransport(error_handler)
        
        async with httpx.AsyncClient(base_url="https://content.test.com", transport=transport) as http_client:
            content_client = ContentServiceClient(
                base_url="https://content.test.com",
                client=http_client
            )
            
            # Should raise ServiceClientError for network issues
            with pytest.raises(Exception) as exc_info:
                await content_client.get_concept_graph()
            
            # Verify it's the expected error type
            assert "Network error" in str(exc_info.value) or "Service unavailable" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_service_error_response_handling(self):
        """Test handling of HTTP error responses from services."""
        def error_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, json={"error": "Internal server error", "details": "Database connection failed"})
        
        transport = httpx.MockTransport(error_handler)
        
        async with httpx.AsyncClient(base_url="https://progress.test.com", transport=transport) as http_client:
            progress_client = ProgressServiceClient(
                base_url="https://progress.test.com",
                client=http_client
            )
            
            # Should raise ServiceClientError for HTTP errors
            with pytest.raises(Exception) as exc_info:
                await progress_client.get_student_interaction_history("student-123")
            
            # Verify error details are preserved
            error = exc_info.value
            assert hasattr(error, 'status_code')
            assert error.status_code == 500
            assert hasattr(error, 'payload')
            assert error.payload["error"] == "Internal server error"
    
    def test_invalid_configuration_handling(self):
        """Test handling of invalid configuration."""
        with patch.dict(os.environ, {}, clear=True):
            get_settings.cache_clear()
            
            # Should still work with defaults
            settings = get_settings()
            assert settings.APP_NAME == "MyApp"
            
            # But service URLs should be None
            assert settings.CONTENT_SERVICE_BASE_URL is None
            assert settings.PROGRESS_SERVICE_BASE_URL is None


class TestPerformanceAndReliability:
    """Test performance characteristics and reliability."""
    
    @pytest.mark.asyncio
    async def test_concurrent_service_calls(self):
        """Test that multiple concurrent service calls work correctly."""
        call_count = 0
        
        def mock_handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            return httpx.Response(200, json={"call_number": call_count, "path": request.url.path})
        
        transport = httpx.MockTransport(mock_handler)
        
        async with httpx.AsyncClient(base_url="https://test.com", transport=transport) as http_client:
            content_client = ContentServiceClient(base_url="https://test.com", client=http_client)
            
            # Make multiple concurrent calls
            tasks = [content_client.get_concept_graph() for _ in range(5)]
            
            # Wait for all to complete
            import asyncio
            results = await asyncio.gather(*tasks)
            
            # Verify all calls completed successfully
            assert len(results) == 5
            assert call_count == 5
            
            # Each result should have a unique call number
            call_numbers = [result["call_number"] for result in results]
            assert len(set(call_numbers)) == 5  # All unique
    
    @pytest.mark.asyncio
    async def test_client_resource_cleanup(self):
        """Test that clients properly clean up resources."""
        # Create a client and ensure it can be closed properly
        content_client = ContentServiceClient(base_url="https://test.com")
        
        # Should not raise any errors
        await content_client.close()
        
        # Multiple closes should be safe
        await content_client.close()
    
    @pytest.mark.asyncio
    async def test_context_manager_resource_cleanup(self):
        """Test that context managers properly clean up resources."""
        def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"status": "ok"})
        
        transport = httpx.MockTransport(mock_handler)
        
        # Use context manager
        async with httpx.AsyncClient(base_url="https://test.com", transport=transport) as http_client:
            async with ContentServiceClient(base_url="https://test.com", client=http_client) as content_client:
                result = await content_client.get_concept_graph()
                assert result["status"] == "ok"
        
        # Context should have been cleaned up automatically
