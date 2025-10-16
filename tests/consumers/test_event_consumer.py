"""Unit tests for the event consumer."""
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
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
    async def test_handle_event_with_valid_data(self, event_consumer, valid_event_message):
        """Test handling a valid event message."""
        # Mock the progress client and mastery score calculation
        with patch('app.consumers.event_consumer.get_mastery_scores') as mock_mastery, \
             patch.object(event_consumer.progress_client, 'get_student_interaction_history', new_callable=AsyncMock) as mock_history, \
             patch('app.consumers.event_consumer.get_kafka_client') as mock_kafka_client:
            
            # Setup mocks
            mock_history.return_value = {
                "stats": {
                    "latestEvents": []
                }
            }
            mock_mastery.return_value = {"skill1": 0.8}
            
            mock_kafka_instance = AsyncMock()
            mock_kafka_client.return_value = mock_kafka_instance
            
            # Change event type to QUESTION_ATTEMPT so it gets processed
            valid_event_message.value["event_type"] = "QUESTION_ATTEMPT"
            
            # Should not raise any exceptions
            await event_consumer.handle_event(valid_event_message)
            
            # Verify that the event was processed
            mock_history.assert_called_once_with("user_123")
            mock_mastery.assert_called_once()
            mock_kafka_instance.publish.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_event_with_invalid_data(self, event_consumer, invalid_event_message):
        """Test handling an invalid event message raises ValidationError."""
        with pytest.raises(ValidationError):
            await event_consumer.handle_event(invalid_event_message)
    
    @pytest.mark.asyncio
    async def test_process_event(self, event_consumer):
        """Test processing a validated event."""
        event_data = {
            "event_type": "QUESTION_ATTEMPT",
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
        
        # Mock the progress client and mastery score calculation
        with patch('app.consumers.event_consumer.get_mastery_scores') as mock_mastery, \
             patch.object(event_consumer.progress_client, 'get_student_interaction_history', new_callable=AsyncMock) as mock_history, \
             patch('app.consumers.event_consumer.get_kafka_client') as mock_kafka_client:
            
            # Setup mocks
            mock_history.return_value = {
                "stats": {
                    "latestEvents": []
                }
            }
            mock_mastery.return_value = {"skill1": 0.8}
            
            mock_kafka_instance = AsyncMock()
            mock_kafka_client.return_value = mock_kafka_instance
            
            await event_consumer._process_event(event)
            
            # Verify mastery scores were calculated and published
            mock_mastery.assert_called_once()
            mock_kafka_instance.publish.assert_called_once()
            
            # Verify the published message
            call_args = mock_kafka_instance.publish.call_args
            assert call_args[1]['topic'] == "mastery-scores"
            assert call_args[1]['message']['user_id'] == "user_123"
            assert 'mastery_score' in call_args[1]['message']
