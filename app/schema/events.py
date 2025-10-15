"""Event schemas for the AI service."""
from typing import Optional, Dict, Any
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schema.event_data import (
    EventDataBase, 
    QuizAttemptData, 
    VideoWatchData,
    QuestionGenerationRequestData,
    QuestionGenerationResponseData
)


class LearningGoalData(EventDataBase):
    """Data structure for learning goal."""
    learning_goal: str = Field(..., alias="learningGoal", description="The learning goal or objective")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "learningGoal": "Learn Python programming",
            }
        }
    )


class Event(BaseModel):
    """Base event schema that wraps all event types."""
    event_id: str = Field(
        default_factory=lambda: f"evt_{uuid4().hex}",
        alias="eventId",
        description="Unique identifier for the event"
    )
    event_type: str = Field(..., alias="eventType", description="Type of the event")
    event_data: EventDataBase = Field(
        ...,
        alias="eventData",
        description="Event-specific data payload"
    )
    user_id: str = Field(..., alias="userId", description="ID of the user associated with the event")
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional metadata for the event"
    )

    @field_validator('event_id')
    @classmethod
    def validate_event_id(cls, v: str) -> str:
        """Validate that event_id is not empty."""
        if not v or not v.strip():
            raise ValueError("Event ID cannot be empty")
        return v

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
    event_data: QuizAttemptData = Field(
        ...,
        alias="eventData",
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
    event_data: VideoWatchData = Field(
        ...,
        alias="eventData",
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


class LearningGoalEvent(Event):
    """Specific event schema for learning goal submissions."""
    event_data: LearningGoalData = Field(
        ...,
        alias="eventData",
        description="Learning goal specific data"
    )

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "eventId": "evt_abc123def",
                "eventType": "LEARNING_GOAL",
                "eventData": {
                    "learningGoal": "Learn Python programming",
                },
                "userId": "user_789",
                "metadata": {
                    "source": "web_app",
                    "version": "1.0.0"
                }
            }
        }
    )


class QuestionGenerationRequestEvent(Event):
    """Event schema for question generation requests."""
    event_data: QuestionGenerationRequestData = Field(
        ...,
        alias="eventData",
        description="Question generation request data"
    )

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "eventId": "evt_qgen_request_123",
                "eventType": "question.generation.request",
                "eventData": {
                    "request_id": "req-123",
                    "topic": "Python Loops",
                    "num_questions": 5,
                    "question_types": ["multiple_choice"],
                    "difficulty": "medium",
                    "content_id": "content-456",
                    "user_id": "user-789"
                },
                "userId": "content-service",
                "metadata": {
                    "source": "content-service",
                    "version": "1.0.0"
                }
            }
        }
    )


class QuestionGenerationResponseEvent(Event):
    """Event schema for question generation responses."""
    event_data: QuestionGenerationResponseData = Field(
        ...,
        alias="eventData",
        description="Question generation response data"
    )

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "eventId": "evt_qgen_response_123",
                "eventType": "question.generation.response",
                "eventData": {
                    "request_id": "req-123",
                    "status": "completed",
                    "topic": "Python Loops",
                    "total_questions": 5,
                    "questions": [],
                    "content_id": "content-456",
                    "user_id": "user-789"
                },
                "userId": "ai-service",
                "metadata": {
                    "source": "ai-service",
                    "version": "1.0.0"
                }
            }
        }
    )
