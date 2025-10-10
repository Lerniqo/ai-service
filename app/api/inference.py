"""
Inference endpoints exposed via the main FastAPI application.

This module consolidates the SageMaker-specific endpoints with the core API so
that the same FastAPI server can serve both inference traffic and any
additional REST endpoints (e.g. via API Gateway).
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from pydantic import ValidationError

from app.schema.events import Event

router = APIRouter()


def _get_logger(request: Request) -> logging.Logger:
    """Fetch the application logger attached to the FastAPI instance."""
    app_logger = getattr(request.app.state, "logger", None)
    if isinstance(app_logger, logging.Logger):
        return app_logger
    return logging.getLogger("ai-service")


@router.get("/ping", response_class=Response)
async def ping(request: Request) -> Response:
    """Health check endpoint compatible with SageMaker expectations."""
    logger = _get_logger(request)
    try:
        logger.info("Health check ping received")
        return Response(status_code=200)
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.error("Health check failed", extra={"error": str(exc)})
        return Response(status_code=503)


@router.post("/invocations")
async def invocations(request: Request) -> JSONResponse:
    """Main inference endpoint required by SageMaker and API Gateway."""
    logger = _get_logger(request)

    content_type = request.headers.get("Content-Type", "application/json")
    if content_type != "application/json":
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported content type: {content_type}. Expected application/json",
        )

    try:
        payload = await request.body()
        data = json.loads(payload.decode("utf-8"))
    except json.JSONDecodeError as exc:
        logger.error("JSON decode error", extra={"error": str(exc)})
        raise HTTPException(status_code=400, detail="Invalid JSON in request body") from exc

    logger.info("Received inference request", extra={"content_type": content_type})

    # Backwards compatibility: accept legacy payloads using `data` instead of `eventData`
    normalized_payload = data.copy()
    if "eventData" not in normalized_payload and "data" in normalized_payload:
        normalized_payload = {
            **normalized_payload,
            "eventData": normalized_payload.pop("data"),
        }

    event_data_payload: Dict[str, Any] = normalized_payload.get("eventData", {}) or {}

    try:
        event = Event(**normalized_payload)
    except ValidationError as exc:
        logger.error("Event validation failed", extra={"errors": exc.errors()})
        raise HTTPException(status_code=400, detail=f"Invalid event data: {exc.errors()}") from exc

    logger.info(
        "Event validated successfully",
        extra={"event_type": event.event_type, "user_id": event.user_id},
    )

    try:
        result = await process_event_inference(event, event_data_payload, logger=logger)
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.error("Inference error", exc_info=True, extra={"error": str(exc)})
        raise HTTPException(status_code=500, detail=f"Inference failed: {str(exc)}") from exc

    return JSONResponse(content=result, status_code=200, media_type="application/json")


@router.post("/api/ai-service/predict")
async def predict(request: Request) -> JSONResponse:
    """API Gateway-friendly alias that reuses the SageMaker handler."""
    return await invocations(request)


async def process_event_inference(
    event: Event,
    event_data_payload: Dict[str, Any],
    logger: logging.Logger | None = None,
) -> Dict[str, Any]:
    """Process event and generate inference results."""
    logger = logger or logging.getLogger("ai-service")

    def _pick_value(*keys: str) -> Any:
        for key in keys:
            if key in event_data_payload:
                return event_data_payload[key]
        return None

    timestamp_value = _pick_value("created_at", "createdAt")
    if timestamp_value is None and getattr(event.event_data, "created_at", None):
        timestamp_value = event.event_data.created_at
    if hasattr(timestamp_value, "isoformat"):
        timestamp_value = timestamp_value.isoformat()

    result: Dict[str, Any] = {
        "status": "processed",
        "event_type": event.event_type,
        "user_id": event.user_id,
        "timestamp": timestamp_value,
        "analysis": {
            "received": True,
            "validated": True,
            "event_summary": f"Event {event.event_type} for user {event.user_id}",
        },
    }

    if event.event_type == "quiz_attempt":
        concepts = _pick_value("concepts") or []
        result["analysis"]["quiz_metrics"] = {
            "quiz_id": _pick_value("quiz_id", "quizId"),
            "score": _pick_value("score"),
            "concepts_count": len(concepts) if isinstance(concepts, list) else None,
            "status": _pick_value("status"),
        }
    elif event.event_type == "video_watch":
        result["analysis"]["video_metrics"] = {
            "video_id": _pick_value("video_id", "videoId"),
            "watch_percentage": _pick_value("watch_percentage", "watchPercentage"),
            "completed": _pick_value("completed"),
        }

    logger.info("Inference completed", extra={"result": result})
    return result
