"""Base event data schemas."""
from datetime import datetime, timezone
from typing import List, Optional
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
