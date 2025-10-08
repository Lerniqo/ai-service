"""
Unit tests for the Kafka client service.
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from aiokafka.structs import ConsumerRecord

from app.clients.kafka_client import KafkaClient, get_kafka_client


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    return MagicMock()


@pytest.fixture
def kafka_client(mock_logger):
    """Create a KafkaClient instance for testing."""
    return KafkaClient(
        bootstrap_servers="localhost:9092",
        client_id="test-client",
        logger=mock_logger
    )


@pytest.mark.asyncio
class TestKafkaClientLifecycle:
    """Test Kafka client lifecycle management."""

    async def test_start_client_success(self, kafka_client):
        """Test successfully starting the Kafka client."""
        with patch('app.clients.kafka_client.AIOKafkaProducer') as mock_producer_class:
            mock_producer = AsyncMock()
            mock_producer_class.return_value = mock_producer
            
            await kafka_client.start()
            
            assert kafka_client.is_running is True
            mock_producer.start.assert_called_once()

    async def test_start_client_already_running(self, kafka_client, mock_logger):
        """Test starting client when already running."""
        with patch('app.clients.kafka_client.AIOKafkaProducer') as mock_producer_class:
            mock_producer = AsyncMock()
            mock_producer_class.return_value = mock_producer
            
            await kafka_client.start()
            await kafka_client.start()  # Second start
            
            # Should only start once
            assert mock_producer.start.call_count == 1

    async def test_start_client_connection_error(self, kafka_client):
        """Test handling connection error when starting client."""
        from aiokafka.errors import KafkaConnectionError
        
        with patch('app.clients.kafka_client.AIOKafkaProducer') as mock_producer_class:
            mock_producer = AsyncMock()
            mock_producer.start.side_effect = KafkaConnectionError("Connection failed")
            mock_producer_class.return_value = mock_producer
            
            with pytest.raises(KafkaConnectionError):
                await kafka_client.start()
            
            assert kafka_client.is_running is False

    async def test_stop_client(self, kafka_client):
        """Test stopping the Kafka client."""
        with patch('app.clients.kafka_client.AIOKafkaProducer') as mock_producer_class:
            mock_producer = AsyncMock()
            mock_producer_class.return_value = mock_producer
            
            await kafka_client.start()
            await kafka_client.stop()
            
            assert kafka_client.is_running is False
            mock_producer.stop.assert_called_once()

    async def test_stop_client_not_running(self, kafka_client):
        """Test stopping client when not running."""
        # Should not raise an error
        await kafka_client.stop()
        assert kafka_client.is_running is False

    async def test_managed_lifecycle(self, kafka_client):
        """Test the managed lifecycle context manager."""
        with patch('app.clients.kafka_client.AIOKafkaProducer') as mock_producer_class:
            mock_producer = AsyncMock()
            mock_producer_class.return_value = mock_producer
            
            async with kafka_client.managed_lifecycle():
                assert kafka_client.is_running is True
            
            assert kafka_client.is_running is False
            mock_producer.start.assert_called_once()
            mock_producer.stop.assert_called_once()


@pytest.mark.asyncio
class TestKafkaClientPublish:
    """Test Kafka message publishing."""

    async def test_publish_message_success(self, kafka_client):
        """Test successfully publishing a message."""
        with patch('app.clients.kafka_client.AIOKafkaProducer') as mock_producer_class:
            mock_producer = AsyncMock()
            mock_producer_class.return_value = mock_producer
            
            await kafka_client.start()
            
            message = {"event": "test", "data": "value"}
            await kafka_client.publish("test-topic", message, key="test-key")
            
            mock_producer.send.assert_called_once()
            call_args = mock_producer.send.call_args
            assert call_args[0][0] == "test-topic"
            assert call_args[1]["key"] == "test-key"

    async def test_publish_message_with_headers(self, kafka_client):
        """Test publishing a message with headers."""
        with patch('app.clients.kafka_client.AIOKafkaProducer') as mock_producer_class:
            mock_producer = AsyncMock()
            mock_producer_class.return_value = mock_producer
            
            await kafka_client.start()
            
            message = {"data": "value"}
            headers = {"correlation-id": "123", "source": "test"}
            await kafka_client.publish("test-topic", message, headers=headers)
            
            call_args = mock_producer.send.call_args
            assert call_args[1]["headers"] is not None

    async def test_publish_message_not_started(self, kafka_client):
        """Test publishing when client not started."""
        message = {"data": "value"}
        
        with pytest.raises(RuntimeError, match="not started"):
            await kafka_client.publish("test-topic", message)

    async def test_publish_batch_success(self, kafka_client):
        """Test successfully publishing a batch of messages."""
        with patch('app.clients.kafka_client.AIOKafkaProducer') as mock_producer_class:
            mock_producer = AsyncMock()
            mock_producer.send.return_value = asyncio.Future()
            mock_producer.send.return_value.set_result(None)
            mock_producer_class.return_value = mock_producer
            
            await kafka_client.start()
            
            messages = [
                {"event": "test1"},
                {"event": "test2"},
                {"event": "test3"}
            ]
            keys = ["key1", "key2", "key3"]
            
            await kafka_client.publish_batch("test-topic", messages, keys=keys)
            
            assert mock_producer.send.call_count == 3

    async def test_publish_batch_keys_mismatch(self, kafka_client):
        """Test batch publish with mismatched keys length."""
        with patch('app.clients.kafka_client.AIOKafkaProducer') as mock_producer_class:
            mock_producer = AsyncMock()
            mock_producer_class.return_value = mock_producer
            
            await kafka_client.start()
            
            messages = [{"event": "test1"}, {"event": "test2"}]
            keys = ["key1"]  # Wrong length
            
            with pytest.raises(ValueError, match="same length"):
                await kafka_client.publish_batch("test-topic", messages, keys=keys)

    async def test_flush(self, kafka_client):
        """Test flushing pending messages."""
        with patch('app.clients.kafka_client.AIOKafkaProducer') as mock_producer_class:
            mock_producer = AsyncMock()
            mock_producer_class.return_value = mock_producer
            
            await kafka_client.start()
            await kafka_client.flush()
            
            mock_producer.flush.assert_called_once()


@pytest.mark.asyncio
class TestKafkaClientSubscribe:
    """Test Kafka message subscription and consumption."""

    async def test_subscribe_success(self, kafka_client):
        """Test successfully subscribing to topics."""
        with patch('app.clients.kafka_client.AIOKafkaProducer') as mock_producer_class, \
             patch('app.clients.kafka_client.AIOKafkaConsumer') as mock_consumer_class:
            
            mock_producer = AsyncMock()
            mock_producer_class.return_value = mock_producer
            
            mock_consumer = AsyncMock()
            mock_consumer_class.return_value = mock_consumer
            
            await kafka_client.start()
            
            async def handler(message):
                pass
            
            consumer_id = await kafka_client.subscribe(
                topics=["test-topic"],
                group_id="test-group",
                handler=handler,
                auto_start=False
            )
            
            assert consumer_id in kafka_client.active_consumers
            mock_consumer.start.assert_called_once()

    async def test_subscribe_auto_start(self, kafka_client):
        """Test subscribing with auto-start enabled."""
        with patch('app.clients.kafka_client.AIOKafkaProducer') as mock_producer_class, \
             patch('app.clients.kafka_client.AIOKafkaConsumer') as mock_consumer_class:
            
            mock_producer = AsyncMock()
            mock_producer_class.return_value = mock_producer
            
            mock_consumer = AsyncMock()
            mock_consumer.__aiter__ = AsyncMock(return_value=iter([]))
            mock_consumer_class.return_value = mock_consumer
            
            await kafka_client.start()
            
            async def handler(message):
                pass
            
            consumer_id = await kafka_client.subscribe(
                topics=["test-topic"],
                group_id="test-group",
                handler=handler,
                auto_start=True
            )
            
            assert consumer_id in kafka_client._consumer_tasks

    async def test_subscribe_not_started(self, kafka_client):
        """Test subscribing when client not started."""
        async def handler(message):
            pass
        
        with pytest.raises(RuntimeError, match="not started"):
            await kafka_client.subscribe(
                topics=["test-topic"],
                group_id="test-group",
                handler=handler
            )

    async def test_unsubscribe(self, kafka_client):
        """Test unsubscribing from topics."""
        with patch('app.clients.kafka_client.AIOKafkaProducer') as mock_producer_class, \
             patch('app.clients.kafka_client.AIOKafkaConsumer') as mock_consumer_class:
            
            mock_producer = AsyncMock()
            mock_producer_class.return_value = mock_producer
            
            mock_consumer = AsyncMock()
            mock_consumer_class.return_value = mock_consumer
            
            await kafka_client.start()
            
            async def handler(message):
                pass
            
            consumer_id = await kafka_client.subscribe(
                topics=["test-topic"],
                group_id="test-group",
                handler=handler,
                auto_start=False
            )
            
            await kafka_client.unsubscribe(consumer_id)
            
            assert consumer_id not in kafka_client.active_consumers
            mock_consumer.stop.assert_called_once()

    async def test_consume_messages_handler_called(self, kafka_client):
        """Test that message handler is called for each message."""
        mock_message = MagicMock(spec=ConsumerRecord)
        mock_message.topic = "test-topic"
        mock_message.partition = 0
        mock_message.offset = 1
        mock_message.value = {"event": "test"}
        
        handler_called = asyncio.Event()
        received_message = None
        
        async def handler(message):
            nonlocal received_message
            received_message = message
            handler_called.set()
        
        with patch('app.clients.kafka_client.AIOKafkaProducer') as mock_producer_class, \
             patch('app.clients.kafka_client.AIOKafkaConsumer') as mock_consumer_class:
            
            mock_producer = AsyncMock()
            mock_producer_class.return_value = mock_producer
            
            # Create an async iterator that yields one message then stops
            async def mock_aiter():
                yield mock_message
                # Stop iteration to prevent infinite loop
                await asyncio.sleep(0.1)
            
            mock_consumer = AsyncMock()
            mock_consumer.__aiter__ = lambda self: mock_aiter()
            mock_consumer_class.return_value = mock_consumer
            
            await kafka_client.start()
            
            consumer_id = await kafka_client.subscribe(
                topics=["test-topic"],
                group_id="test-group",
                handler=handler,
                auto_start=True
            )
            
            # Wait for handler to be called
            await asyncio.wait_for(handler_called.wait(), timeout=1.0)
            
            assert received_message is not None
            assert received_message.value == {"event": "test"}


@pytest.mark.asyncio
class TestKafkaClientUtilities:
    """Test utility methods."""

    async def test_get_topic_partitions(self, kafka_client):
        """Test getting topic partitions."""
        with patch('app.clients.kafka_client.AIOKafkaProducer') as mock_producer_class:
            mock_producer = AsyncMock()
            mock_producer.partitions_for.return_value = {0, 1, 2}
            mock_producer_class.return_value = mock_producer
            
            await kafka_client.start()
            
            partitions = await kafka_client.get_topic_partitions("test-topic")
            
            assert partitions == {0, 1, 2}
            mock_producer.partitions_for.assert_called_once_with("test-topic")

    async def test_active_consumers_property(self, kafka_client):
        """Test the active_consumers property."""
        with patch('app.clients.kafka_client.AIOKafkaProducer') as mock_producer_class, \
             patch('app.clients.kafka_client.AIOKafkaConsumer') as mock_consumer_class:
            
            mock_producer = AsyncMock()
            mock_producer_class.return_value = mock_producer
            
            mock_consumer = AsyncMock()
            mock_consumer_class.return_value = mock_consumer
            
            await kafka_client.start()
            
            async def handler(message):
                pass
            
            consumer_id = await kafka_client.subscribe(
                topics=["test-topic"],
                group_id="test-group",
                handler=handler,
                auto_start=False
            )
            
            active = kafka_client.active_consumers
            assert consumer_id in active


class TestKafkaClientSingleton:
    """Test singleton pattern."""

    def test_get_kafka_client_singleton(self, mock_logger):
        """Test that get_kafka_client returns singleton instance."""
        # Reset the singleton
        import app.clients.kafka_client as kafka_module
        kafka_module._kafka_client_instance = None
        
        client1 = get_kafka_client("localhost:9092", "test-client", mock_logger)
        client2 = get_kafka_client("localhost:9092", "test-client", mock_logger)
        
        assert client1 is client2

    def test_get_kafka_client_with_config(self, mock_logger):
        """Test that get_kafka_client loads from config when params not provided."""
        # Reset the singleton
        import app.clients.kafka_client as kafka_module
        kafka_module._kafka_client_instance = None
        
        with patch('app.config.get_settings') as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.KAFKA_BOOTSTRAP_SERVERS = "config-server:9092"
            mock_settings.KAFKA_CLIENT_ID = "config-client"
            mock_get_settings.return_value = mock_settings
            
            client = get_kafka_client(logger=mock_logger)
            
            assert client.bootstrap_servers == "config-server:9092"
            assert client.client_id == "config-client"
            
    def test_get_kafka_client_override_config(self, mock_logger):
        """Test that explicit params override config."""
        # Reset the singleton
        import app.clients.kafka_client as kafka_module
        kafka_module._kafka_client_instance = None
        
        with patch('app.config.get_settings') as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.KAFKA_BOOTSTRAP_SERVERS = "config-server:9092"
            mock_settings.KAFKA_CLIENT_ID = "config-client"
            mock_get_settings.return_value = mock_settings
            
            client = get_kafka_client(
                bootstrap_servers="override-server:9092",
                client_id="override-client",
                logger=mock_logger
            )
            
            assert client.bootstrap_servers == "override-server:9092"
            assert client.client_id == "override-client"
