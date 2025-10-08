"""Event schemas for the AI service."""
from typing import Optional, Dict, Any, Union
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schema.event_data import EventDataBase, QuizAttemptData


class Event(BaseModel):
    """Base event schema that wraps all event types."""
    event_type: str = Field(..., description="Type of the event")
    event_data: Union[QuizAttemptData, EventDataBase] = Field(
        ...,
        description="Event-specific data payload"
    )
    user_id: str = Field(..., description="ID of the user associated with the event")
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional metadata for the event"
    )

    @field_validator('event_type')
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        """Validate that event_type is not empty."""
        if not v or not v.strip():
            raise ValueError("Event type cannot be empty")
        return v

    @field_validator('user_id')
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        """Validate that user_id is not empty."""
        if not v or not v.strip():
            raise ValueError("User ID cannot be empty")
        return v

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "event_type": "quiz.attempt.completed",
                "event_data": {
                    "created_at": "2025-10-08T10:00:00Z",
                    "updated_at": "2025-10-08T10:00:00Z",
                    "quiz_id": "quiz_123",
                    "score": 85.5,
                    "concepts": ["algebra", "geometry"],
                    "status": "completed"
                },
                "user_id": "user_456",
                "metadata": {
                    "source": "web_app",
                    "version": "1.0.0"
                }
            }
        }
    )


class QuizAttemptEvent(Event):
    """Specific event schema for quiz attempts."""
    event_data: QuizAttemptData = Field(
        ...,
        description="Quiz attempt specific data"
    )

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "event_type": "quiz.attempt.completed",
                "event_data": {
                    "created_at": "2025-10-08T10:00:00Z",
                    "updated_at": "2025-10-08T10:00:00Z",
                    "quiz_id": "quiz_123",
                    "score": 85.5,
                    "concepts": ["algebra", "geometry"],
                    "status": "completed"
                },
                "user_id": "user_456",
                "metadata": {
                    "source": "web_app"
                }
            }
        }
    )
