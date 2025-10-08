"""Event schemas for the AI service."""
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schema.event_data import EventDataBase, QuizAttemptData, VideoWatchData


class Event(BaseModel):
    """Base event schema that wraps all event types."""
    eventId: str = Field(..., description="Unique identifier for the event")
    eventType: str = Field(..., description="Type of the event")
    eventData: EventDataBase = Field(
        ...,
        description="Event-specific data payload"
    )
    userId: str = Field(..., description="ID of the user associated with the event")
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional metadata for the event"
    )

    @field_validator('eventId')
    @classmethod
    def validate_event_id(cls, v: str) -> str:
        """Validate that eventId is not empty."""
        if not v or not v.strip():
            raise ValueError("Event ID cannot be empty")
        return v

    @field_validator('eventType')
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        """Validate that eventType is not empty."""
        if not v or not v.strip():
            raise ValueError("Event type cannot be empty")
        return v

    @field_validator('userId')
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        """Validate that userId is not empty."""
        if not v or not v.strip():
            raise ValueError("User ID cannot be empty")
        return v

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "eventId": "evt_123456789",
                "eventType": "quiz.attempt.completed",
                "eventData": {
                    "created_at": "2025-10-08T10:00:00Z",
                    "updated_at": "2025-10-08T10:00:00Z",
                    "quiz_id": "quiz_123",
                    "score": 85.5,
                    "concepts": ["algebra", "geometry"],
                    "status": "completed"
                },
                "userId": "user_456",
                "metadata": {
                    "source": "web_app",
                    "version": "1.0.0"
                }
            }
        }
    )


class QuizAttemptEvent(Event):
    """Specific event schema for quiz attempts."""
    eventData: QuizAttemptData = Field(
        ...,
        description="Quiz attempt specific data"
    )

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "eventId": "evt_123456789",
                "eventType": "quiz.attempt.completed",
                "eventData": {
                    "created_at": "2025-10-08T10:00:00Z",
                    "updated_at": "2025-10-08T10:00:00Z",
                    "quiz_id": "quiz_123",
                    "score": 85.5,
                    "concepts": ["algebra", "geometry"],
                    "status": "completed"
                },
                "userId": "user_456",
                "metadata": {
                    "source": "web_app"
                }
            }
        }
    )


class VideoWatchEvent(Event):
    """Specific event schema for video watch events."""
    eventData: VideoWatchData = Field(
        ...,
        description="Video watch specific data"
    )

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "eventId": "evt_987654321",
                "eventType": "VIDEO_WATCH",
                "eventData": {
                    "created_at": "2025-10-08T10:00:00Z",
                    "updated_at": "2025-10-08T10:00:00Z",
                    "userId": "test-user-456",
                    "videoId": "video-789",
                    "courseId": "course-123",
                    "watchDuration": 120,
                    "totalDuration": 300,
                    "completed": False,
                    "watchPercentage": 40
                },
                "userId": "test-user-456",
                "metadata": {
                    "userAgent": "Mozilla/5.0 (Chrome/91.0)",
                    "sessionId": "session-456",
                    "playbackSpeed": 1,
                    "quality": "720p"
                }
            }
        }
    )
