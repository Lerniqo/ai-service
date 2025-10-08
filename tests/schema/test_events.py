"""Tests for event schemas."""
import pytest
from datetime import datetime
from pydantic import ValidationError

from app.schema import Event, QuizAttemptEvent, QuizAttemptData, EventDataBase


class TestEventDataBase:
    """Tests for EventDataBase schema."""

    def test_event_data_base_valid(self):
        """Test valid EventDataBase creation."""
        data = EventDataBase(
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        assert data.created_at is not None
        assert data.updated_at is not None


class TestQuizAttemptData:
    """Tests for QuizAttemptData schema."""

    def test_quiz_attempt_data_valid(self):
        """Test valid QuizAttemptData creation."""
        data = QuizAttemptData(
            created_at=datetime.now(),
            updated_at=datetime.now(),
            quiz_id="quiz_123",
            score=85.5,
            concepts=["algebra", "geometry"],
            status="completed"
        )
        assert data.quiz_id == "quiz_123"
        assert data.score == 85.5
        assert data.concepts == ["algebra", "geometry"]
        assert data.status == "completed"

    def test_quiz_attempt_data_without_score(self):
        """Test QuizAttemptData creation without optional score."""
        data = QuizAttemptData(
            created_at=datetime.now(),
            updated_at=datetime.now(),
            quiz_id="quiz_123",
            concepts=["algebra"],
            status="pending"
        )
        assert data.score is None
        assert data.status == "pending"

    def test_quiz_attempt_data_invalid_status(self):
        """Test QuizAttemptData with invalid status."""
        with pytest.raises(ValidationError) as exc_info:
            QuizAttemptData(
                created_at=datetime.now(),
                updated_at=datetime.now(),
                quiz_id="quiz_123",
                concepts=["algebra"],
                status="invalid_status"
            )
        assert "Status must be one of" in str(exc_info.value)

    def test_quiz_attempt_data_invalid_score_too_high(self):
        """Test QuizAttemptData with score > 100."""
        with pytest.raises(ValidationError) as exc_info:
            QuizAttemptData(
                created_at=datetime.now(),
                updated_at=datetime.now(),
                quiz_id="quiz_123",
                score=150,
                concepts=["algebra"],
                status="completed"
            )
        assert "less than or equal to 100" in str(exc_info.value)

    def test_quiz_attempt_data_invalid_score_negative(self):
        """Test QuizAttemptData with negative score."""
        with pytest.raises(ValidationError) as exc_info:
            QuizAttemptData(
                created_at=datetime.now(),
                updated_at=datetime.now(),
                quiz_id="quiz_123",
                score=-10,
                concepts=["algebra"],
                status="completed"
            )
        assert "greater than or equal to 0" in str(exc_info.value)

    def test_quiz_attempt_data_empty_concepts(self):
        """Test QuizAttemptData with empty concepts list."""
        with pytest.raises(ValidationError) as exc_info:
            QuizAttemptData(
                created_at=datetime.now(),
                updated_at=datetime.now(),
                quiz_id="quiz_123",
                concepts=[],
                status="completed"
            )
        # Pydantic min_length validator triggers before custom validator
        assert "at least 1 item" in str(exc_info.value)

    def test_quiz_attempt_data_concepts_with_empty_strings(self):
        """Test QuizAttemptData with empty string in concepts."""
        with pytest.raises(ValidationError) as exc_info:
            QuizAttemptData(
                created_at=datetime.now(),
                updated_at=datetime.now(),
                quiz_id="quiz_123",
                concepts=["algebra", ""],
                status="completed"
            )
        assert "Concepts cannot contain empty strings" in str(exc_info.value)


class TestEvent:
    """Tests for Event schema."""

    def test_event_valid_with_quiz_attempt_data(self):
        """Test valid Event creation with QuizAttemptData."""
        event_data = QuizAttemptData(
            created_at=datetime.now(),
            updated_at=datetime.now(),
            quiz_id="quiz_123",
            score=85.5,
            concepts=["algebra", "geometry"],
            status="completed"
        )
        event = Event(
            event_type="quiz.attempt.completed",
            event_data=event_data,
            user_id="user_456"
        )
        assert event.event_type == "quiz.attempt.completed"
        assert event.user_id == "user_456"
        assert event.event_data.quiz_id == "quiz_123"

    def test_event_with_metadata(self):
        """Test Event creation with metadata."""
        event_data = QuizAttemptData(
            created_at=datetime.now(),
            updated_at=datetime.now(),
            quiz_id="quiz_123",
            concepts=["algebra"],
            status="pending"
        )
        event = Event(
            event_type="quiz.attempt.started",
            event_data=event_data,
            user_id="user_456",
            metadata={"source": "web_app", "version": "1.0.0"}
        )
        assert event.metadata is not None
        assert event.metadata["source"] == "web_app"
        assert event.metadata["version"] == "1.0.0"

    def test_event_invalid_empty_event_type(self):
        """Test Event with empty event_type."""
        event_data = QuizAttemptData(
            created_at=datetime.now(),
            updated_at=datetime.now(),
            quiz_id="quiz_123",
            concepts=["algebra"],
            status="pending"
        )
        with pytest.raises(ValidationError) as exc_info:
            Event(
                event_type="",
                event_data=event_data,
                user_id="user_456"
            )
        assert "Event type cannot be empty" in str(exc_info.value)

    def test_event_invalid_empty_user_id(self):
        """Test Event with empty user_id."""
        event_data = QuizAttemptData(
            created_at=datetime.now(),
            updated_at=datetime.now(),
            quiz_id="quiz_123",
            concepts=["algebra"],
            status="pending"
        )
        with pytest.raises(ValidationError) as exc_info:
            Event(
                event_type="quiz.attempt.started",
                event_data=event_data,
                user_id=""
            )
        assert "User ID cannot be empty" in str(exc_info.value)


class TestQuizAttemptEvent:
    """Tests for QuizAttemptEvent schema."""

    def test_quiz_attempt_event_valid(self):
        """Test valid QuizAttemptEvent creation."""
        event_data = QuizAttemptData(
            created_at=datetime.now(),
            updated_at=datetime.now(),
            quiz_id="quiz_123",
            score=85.5,
            concepts=["algebra", "geometry"],
            status="completed"
        )
        event = QuizAttemptEvent(
            event_type="quiz.attempt.completed",
            event_data=event_data,
            user_id="user_456"
        )
        assert event.event_type == "quiz.attempt.completed"
        assert isinstance(event.event_data, QuizAttemptData)
        assert event.event_data.quiz_id == "quiz_123"

    def test_quiz_attempt_event_serialization(self):
        """Test QuizAttemptEvent JSON serialization."""
        event_data = QuizAttemptData(
            created_at=datetime.now(),
            updated_at=datetime.now(),
            quiz_id="quiz_123",
            score=90.0,
            concepts=["python", "fastapi"],
            status="completed"
        )
        event = QuizAttemptEvent(
            event_type="quiz.attempt.completed",
            event_data=event_data,
            user_id="user_789",
            metadata={"ip": "192.168.1.1"}
        )
        
        # Test model_dump
        event_dict = event.model_dump()
        assert event_dict["event_type"] == "quiz.attempt.completed"
        assert event_dict["user_id"] == "user_789"
        assert event_dict["event_data"]["quiz_id"] == "quiz_123"
        assert event_dict["metadata"]["ip"] == "192.168.1.1"
        
        # Test model_dump_json
        event_json = event.model_dump_json()
        assert "quiz.attempt.completed" in event_json
        assert "user_789" in event_json
