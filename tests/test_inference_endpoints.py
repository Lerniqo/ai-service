"""Tests for unified inference endpoints exposed by FastAPI app."""

import os

# Ensure the app loads testing configuration (disables external Kafka brokers)
os.environ.setdefault("ENV", "testing")

from fastapi.testclient import TestClient

from app.main import app


def test_ping_endpoint_returns_200():
    with TestClient(app) as client:
        response = client.get("/ping")
        assert response.status_code == 200


def test_invocations_endpoint_happy_path():
    payload = {
        "eventType": "quiz_attempt",
        "userId": "user-123",
        "data": {
            "quiz_id": "quiz-456",
            "score": 87.5,
            "concepts": ["algebra", "geometry"],
            "status": "completed",
        },
    }

    with TestClient(app) as client:
        response = client.post("/invocations", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "processed"
    assert body["event_type"] == payload["eventType"]
    assert body["user_id"] == payload["userId"]
    assert body["analysis"]["quiz_metrics"]["quiz_id"] == payload["data"]["quiz_id"]


def test_invocations_endpoint_rejects_invalid_payload():
    with TestClient(app) as client:
        response = client.post("/invocations", json={"invalid": "data"})

    assert response.status_code == 400
    assert "Invalid event data" in response.json()["detail"]


def test_predict_alias_uses_same_handler():
    payload = {
        "eventType": "video_watch",
        "userId": "user-789",
        "data": {
            "videoId": "vid-123",
            "watchPercentage": 92.0,
            "completed": True,
        },
    }

    with TestClient(app) as client:
        response = client.post("/api/ai-service/predict", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["analysis"]["video_metrics"]["video_id"] == payload["data"]["videoId"]
