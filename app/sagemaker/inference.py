"""
SageMaker-compatible inference handlers.

This module provides the required endpoints for AWS SageMaker:
- /ping: Health check endpoint
- /invocations: Main inference endpoint

SageMaker expects specific response formats and behaviors.
"""

import json
import logging
from typing import Any, Dict
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.schema.events import Event
from app.core.logging import configure_logging

# Initialize logger for SageMaker inference
logger = configure_logging(
    service_name="sagemaker-inference",
    log_level="INFO",
    format_type="json"
)

# Create SageMaker-compatible FastAPI app
sagemaker_app = FastAPI(
    title="AI Service - SageMaker Inference",
    description="AWS SageMaker compatible inference endpoints",
    version="1.0.0"
)


@sagemaker_app.get("/ping")
async def ping():
    """
    Health check endpoint required by SageMaker.
    
    SageMaker uses this endpoint to determine if the container is ready
    to accept inference requests. It should return 200 when the model
    is loaded and ready.
    
    Returns:
        200 OK if the service is healthy
        503 Service Unavailable if not ready
    """
    try:
        # Add any health checks here (e.g., model loaded, dependencies available)
        logger.info("Health check ping received")
        return Response(status_code=200)
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return Response(status_code=503)


@sagemaker_app.post("/invocations")
async def invocations(request: Request):
    """
    Main inference endpoint required by SageMaker.
    
    This endpoint receives inference requests from SageMaker and returns
    predictions. It supports JSON input/output.
    
    Expected input format:
    {
        "eventType": "quiz_attempt",
        "userId": "user_123",
        "data": {
            "quiz_id": "quiz_456",
            "score": 85.5,
            "concepts": ["algebra", "geometry"],
            "status": "completed"
        }
    }
    
    Returns:
        JSON response with inference results
    """
    try:
        # Get content type
        content_type = request.headers.get("Content-Type", "application/json")
        
        if content_type != "application/json":
            raise HTTPException(
                status_code=415,
                detail=f"Unsupported content type: {content_type}. Expected application/json"
            )
        
        # Parse request body
        body = await request.body()
        data = json.loads(body.decode("utf-8"))
        
        logger.info(f"Received inference request", extra={"content_type": content_type})
        
        # Validate input using Event schema
        try:
            event = Event(**data)
            logger.info(
                f"Event validated successfully",
                extra={
                    "event_type": event.eventType,
                    "user_id": event.userId
                }
            )
        except ValidationError as e:
            logger.error(f"Event validation failed", extra={"errors": e.errors()})
            raise HTTPException(
                status_code=400,
                detail=f"Invalid event data: {e.errors()}"
            )
        
        # Process the event and generate inference results
        result = await process_event_inference(event)
        
        # Return results in SageMaker-compatible format
        return JSONResponse(
            content=result,
            status_code=200,
            media_type="application/json"
        )
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid JSON in request body")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Inference error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Inference failed: {str(e)}")


async def process_event_inference(event: Event) -> Dict[str, Any]:
    """
    Process event and generate inference results.
    
    This is where your AI/ML inference logic would go.
    For now, it returns a simple acknowledgment and event analysis.
    
    Args:
        event: Validated event data
        
    Returns:
        Dictionary containing inference results
    """
    # TODO: Replace with actual AI/ML inference logic
    # This could include:
    # - Loading a trained model
    # - Preprocessing the event data
    # - Running inference
    # - Postprocessing results
    
    result = {
        "status": "processed",
        "event_type": event.eventType,
        "user_id": event.userId,
        "timestamp": event.createdAt.isoformat() if event.createdAt else None,
        "analysis": {
            "received": True,
            "validated": True,
            "event_summary": f"Event {event.eventType} for user {event.userId}"
        }
    }
    
    # Event-type specific processing
    if event.eventType == "quiz_attempt":
        result["analysis"]["quiz_metrics"] = {
            "quiz_id": event.data.quiz_id,
            "score": event.data.score,
            "concepts_count": len(event.data.concepts),
            "status": event.data.status
        }
    elif event.eventType == "video_watch":
        result["analysis"]["video_metrics"] = {
            "video_id": event.data.videoId,
            "watch_percentage": event.data.watchPercentage,
            "completed": event.data.completed
        }
    
    logger.info("Inference completed", extra={"result": result})
    return result


# Optional: Add custom exception handlers
@sagemaker_app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with proper logging."""
    logger.error(
        f"HTTP {exc.status_code}: {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "path": request.url.path
        }
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )


@sagemaker_app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(
        f"Unhandled exception: {str(exc)}",
        extra={"path": request.url.path},
        exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )
