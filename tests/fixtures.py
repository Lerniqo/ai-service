"""Test fixtures for SageMaker inference testing."""

QUIZ_ATTEMPT_EVENT = {
    "eventType": "quiz_attempt",
    "userId": "user_123",
    "data": {
        "quiz_id": "quiz_456",
        "score": 85.5,
        "concepts": ["algebra", "geometry", "trigonometry"],
        "status": "completed",
        "created_at": "2025-10-10T10:00:00Z",
        "updated_at": "2025-10-10T10:30:00Z"
    },
    "createdAt": "2025-10-10T10:00:00Z"
}

VIDEO_WATCH_EVENT = {
    "eventType": "video_watch",
    "userId": "user_789",
    "data": {
        "userId": "user_789",
        "videoId": "video_101",
        "courseId": "course_202",
        "watchDuration": 450,
        "totalDuration": 600,
        "completed": False,
        "watchPercentage": 75.0,
        "created_at": "2025-10-10T11:00:00Z",
        "updated_at": "2025-10-10T11:15:00Z"
    },
    "createdAt": "2025-10-10T11:00:00Z"
}
