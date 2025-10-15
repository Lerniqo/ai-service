"""Base event data schemas."""
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field, field_validator


class EventDataBase(BaseModel):
    """Base class for all event data schemas."""
    created_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the event was created"
    )
    updated_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the event was last updated"
    )

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "created_at": "2025-10-08T10:00:00Z",
                "updated_at": "2025-10-08T10:00:00Z"
            }
        }
    )


class QuizAttemptData(EventDataBase):
    """Schema for quiz attempt event data."""
    quiz_id: str = Field(..., description="ID of the quiz being attempted")
    score: Optional[float] = Field(
        None,
        ge=0,
        le=100,
        description="Score achieved in the quiz (0-100)"
    )
    concepts: List[str] = Field(
        ...,
        min_length=1,
        description="List of concepts covered in the quiz"
    )
    status: str = Field(
        ...,
        description="Current status of the quiz attempt"
    )

    @field_validator('status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate that status is one of the allowed values."""
        allowed_statuses = {'pending', 'completed', 'abandoned'}
        if v not in allowed_statuses:
            raise ValueError(f"Status must be one of {allowed_statuses}, got '{v}'")
        return v

    @field_validator('concepts')
    @classmethod
    def validate_concepts(cls, v: List[str]) -> List[str]:
        """Validate that concepts list is not empty and contains valid strings."""
        if not v:
            raise ValueError("Concepts list cannot be empty")
        if any(not concept.strip() for concept in v):
            raise ValueError("Concepts cannot contain empty strings")
        return v

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "created_at": "2025-10-08T10:00:00Z",
                "updated_at": "2025-10-08T10:00:00Z",
                "quiz_id": "quiz_123",
                "score": 85.5,
                "concepts": ["algebra", "geometry", "trigonometry"],
                "status": "completed"
            }
        }
    )


class VideoWatchData(EventDataBase):
    """Schema for video watch event data."""
    userId: str = Field(..., description="ID of the user watching the video")
    videoId: str = Field(..., description="ID of the video being watched")
    courseId: str = Field(..., description="ID of the course the video belongs to")
    watchDuration: int = Field(..., ge=0, description="Duration watched in seconds")
    totalDuration: int = Field(..., ge=0, description="Total video duration in seconds")
    completed: bool = Field(..., description="Whether the video was completed")
    watchPercentage: float = Field(..., ge=0, le=100, description="Percentage of video watched")

    @field_validator('watchPercentage')
    @classmethod
    def validate_watch_percentage(cls, v: float) -> float:
        """Validate that watch percentage is within valid range."""
        if v < 0 or v > 100:
            raise ValueError("Watch percentage must be between 0 and 100")
        return v

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "created_at": "2025-10-08T10:00:00Z",
                "updated_at": "2025-10-08T10:00:00Z",
                "userId": "test-user-456",
                "videoId": "video-789",
                "courseId": "course-123",
                "watchDuration": 120,
                "totalDuration": 300,
                "completed": False,
                "watchPercentage": 40
            }
        }
    )


class QuestionGenerationRequestData(EventDataBase):
    """Schema for question generation request event data."""
    request_id: str = Field(..., description="Unique identifier for this request")
    topic: str = Field(..., description="Topic to generate questions about")
    num_questions: int = Field(default=5, ge=1, le=50, description="Number of questions")
    question_types: Optional[List[str]] = Field(
        default=None,
        description="Question types (multiple_choice, true_false, short_answer, essay)"
    )
    difficulty: str = Field(default="medium", description="Difficulty level (easy, medium, hard)")
    content_id: Optional[str] = Field(None, description="ID of the content this relates to")
    user_id: Optional[str] = Field(None, description="User ID if personalized questions")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")

    @field_validator('difficulty')
    @classmethod
    def validate_difficulty(cls, v: str) -> str:
        """Validate that difficulty is one of the allowed values."""
        allowed_difficulties = {'easy', 'medium', 'hard'}
        if v.lower() not in allowed_difficulties:
            raise ValueError(f"Difficulty must be one of {allowed_difficulties}, got '{v}'")
        return v.lower()

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "created_at": "2025-10-15T10:00:00Z",
                "updated_at": "2025-10-15T10:00:00Z",
                "request_id": "req-123",
                "topic": "Python Loops",
                "num_questions": 5,
                "question_types": ["multiple_choice"],
                "difficulty": "medium",
                "content_id": "content-456",
                "user_id": "user-789"
            }
        }
    )


class QuestionGenerationResponseData(EventDataBase):
    """Schema for question generation response event data."""
    request_id: str = Field(..., description="The request identifier this response belongs to")
    status: str = Field(..., description="Status: completed, failed")
    topic: Optional[str] = Field(None, description="Topic of generated questions")
    total_questions: Optional[int] = Field(None, description="Total number of questions generated")
    questions: Optional[List[Dict[str, Any]]] = Field(None, description="List of generated questions")
    content_id: Optional[str] = Field(None, description="ID of the content this relates to")
    user_id: Optional[str] = Field(None, description="User ID if personalized questions")
    error: Optional[str] = Field(None, description="Error message if status is failed")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")

    @field_validator('status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate that status is one of the allowed values."""
        allowed_statuses = {'completed', 'failed'}
        if v.lower() not in allowed_statuses:
            raise ValueError(f"Status must be one of {allowed_statuses}, got '{v}'")
        return v.lower()

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "created_at": "2025-10-15T10:00:00Z",
                "updated_at": "2025-10-15T10:00:00Z",
                "request_id": "req-123",
                "status": "completed",
                "topic": "Python Loops",
                "total_questions": 5,
                "questions": [],
                "content_id": "content-456",
                "user_id": "user-789"
            }
        }
    )
