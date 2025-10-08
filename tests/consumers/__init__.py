"""Unit tests for the event consumer."""
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from aiokafka.structs import ConsumerRecord
from pydantic import ValidationError

from app.consumers.event_consumer import EventConsumer, create_event_consumer
from app.schema.events import Event


@pytest.fixture
def event_consumer():
    """Create an EventConsumer instance for testing."""
    logger = Mock()
    return EventConsumer(logger=logger)


@pytest.fixture
def valid_event_message():
    """Create a valid Kafka message with event data."""
    message_value = {
        "event_type": "quiz.attempt.completed",
        "user_id": "user_123",
        "event_data": {
            "created_at": "2025-10-08T10:00:00Z",
            "updated_at": "2025-10-08T10:00:00Z",
            "quiz_id": "quiz_123",
            "score": 85.5,
            "concepts": ["algebra", "geometry"],
            "status": "completed"
        },
        "metadata": {"source": "test"}
    }
    
    # Create a mock ConsumerRecord
    message = MagicMock(spec=ConsumerRecord)
    message.value = message_value
    message.topic = "events"
    message.partition = 0
    message.offset = 100
    message.timestamp = 1696752000000
    
    return message


@pytest.fixture
def invalid_event_message():
    """Create an invalid Kafka message (missing required fields)."""
    message_value = {
        "event_type": "quiz.attempt.completed",
        # Missing user_id and event_data
    }
    
    message = MagicMock(spec=ConsumerRecord)
    message.value = message_value
    message.topic = "events"
    message.partition = 0
    message.offset = 101
    message.timestamp = 1696752000000
    
    return message


class TestEventConsumer:
    """Test suite for EventConsumer class."""
    
    def test_create_event_consumer(self):
        """Test creating an event consumer using factory function."""
        consumer = create_event_consumer()
        assert isinstance(consumer, EventConsumer)
        assert consumer.logger is not None
    
    def test_create_event_consumer_with_logger(self):
        """Test creating an event consumer with custom logger."""
        logger = Mock()
        consumer = create_event_consumer(logger=logger)
        assert consumer.logger is logger
    
    @pytest.mark.asyncio
    async def test_handle_event_with_valid_data(self, event_consumer, valid_event_message, capsys):
        """Test handling a valid event message."""
        await event_consumer.handle_event(valid_event_message)
        
        # Check that the event was printed
        captured = capsys.readouterr()
        assert "INCOMING EVENT" in captured.out
        assert "quiz.attempt.completed" in captured.out
        assert "user_123" in captured.out
    
    @pytest.mark.asyncio
    async def test_handle_event_with_invalid_data(self, event_consumer, invalid_event_message):
        """Test handling an invalid event message raises ValidationError."""
        with pytest.raises(ValidationError):
            await event_consumer.handle_event(invalid_event_message)
    
    @pytest.mark.asyncio
    async def test_process_event(self, event_consumer, capsys):
        """Test processing a validated event."""
        event_data = {
            "event_type": "quiz.attempt.completed",
            "user_id": "user_123",
            "event_data": {
                "created_at": "2025-10-08T10:00:00Z",
                "updated_at": "2025-10-08T10:00:00Z",
                "quiz_id": "quiz_123",
                "score": 85.5,
                "concepts": ["algebra", "geometry"],
                "status": "completed"
            }
        }
        
        event = Event(**event_data)
        await event_consumer._process_event(event)
        
        # Check that the event was printed correctly
        captured = capsys.readouterr()
        assert "📨 INCOMING EVENT" in captured.out
        assert "Event Type: quiz.attempt.completed" in captured.out
        assert "User ID: user_123" in captured.out
