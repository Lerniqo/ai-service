"""
Kafka client service for publishing and consuming messages using aiokafka.

This module provides a comprehensive Kafka client with support for:
- Publishing messages to topics
- Subscribing to topics and consuming messages
- Consumer groups
- Batch processing
- Error handling and retries
- Graceful shutdown
"""

import asyncio
import json
import logging
from typing import Any, Callable, Dict, List, Optional, Set
from contextlib import asynccontextmanager

from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from aiokafka.errors import KafkaError, KafkaConnectionError
from aiokafka.structs import ConsumerRecord

from app.core.logging import log_with_extra


class KafkaClient:
    """
    Asynchronous Kafka client for publishing and consuming messages.
    
    This client provides methods for:
    - Publishing messages to Kafka topics
    - Subscribing to topics with callback handlers
    - Managing consumer groups
    - Batch message processing
    - Health checks
    """

    def __init__(
        self,
        bootstrap_servers: str,
        client_id: str = "ai-service",
        logger: Optional[logging.Logger] = None,
        producer_config: Optional[Dict[str, Any]] = None,
        consumer_config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the Kafka client.
        
        Args:
            bootstrap_servers: Comma-separated list of Kafka broker addresses
            client_id: Client identifier for this application
            logger: Logger instance for structured logging
            producer_config: Additional producer configuration
            consumer_config: Additional consumer configuration
        """
        self.bootstrap_servers = bootstrap_servers
        self.client_id = client_id
        self.logger = logger or logging.getLogger(__name__)
        
        self._producer: Optional[AIOKafkaProducer] = None
        self._consumers: Dict[str, AIOKafkaConsumer] = {}
        self._consumer_tasks: Dict[str, asyncio.Task] = {}
        self._is_running = False
        
        # Default configurations
        self._producer_config = {
            "client_id": client_id,
            "compression_type": "gzip",
            "acks": "all",
            **(producer_config or {})
        }
        
        self._consumer_config = {
            "client_id": client_id,
            "auto_offset_reset": "earliest",
            "enable_auto_commit": True,
            "auto_commit_interval_ms": 5000,
            **(consumer_config or {})
        }

    async def start(self) -> None:
        """
        Start the Kafka client and initialize the producer.
        
        Raises:
            KafkaConnectionError: If unable to connect to Kafka brokers
        """
        if self._is_running:
            log_with_extra(
                self.logger,
                "warning",
                "Kafka client is already running",
                client_id=self.client_id
            )
            return

        try:
            # Initialize producer
            self._producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                **self._producer_config
            )
            await self._producer.start()
            
            self._is_running = True
            
            log_with_extra(
                self.logger,
                "info",
                "Kafka client started successfully",
                bootstrap_servers=self.bootstrap_servers,
                client_id=self.client_id
            )
            
        except KafkaConnectionError as e:
            log_with_extra(
                self.logger,
                "error",
                f"Failed to connect to Kafka brokers: {str(e)}",
                bootstrap_servers=self.bootstrap_servers,
                error=str(e)
            )
            raise
        except Exception as e:
            log_with_extra(
                self.logger,
                "error",
                f"Error starting Kafka client: {str(e)}",
                error=str(e)
            )
            raise

    async def stop(self) -> None:
        """
        Stop the Kafka client and clean up resources.
        
        This will:
        - Stop all active consumers
        - Cancel consumer tasks
        - Stop the producer
        """
        if not self._is_running:
            return

        log_with_extra(
            self.logger,
            "info",
            "Stopping Kafka client",
            client_id=self.client_id
        )

        # Stop all consumer tasks
        for task_name, task in self._consumer_tasks.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    log_with_extra(
                        self.logger,
                        "info",
                        f"Consumer task cancelled",
                        task_name=task_name
                    )

        # Stop all consumers
        for topic, consumer in self._consumers.items():
            try:
                await consumer.stop()
                log_with_extra(
                    self.logger,
                    "info",
                    f"Consumer stopped",
                    topic=topic
                )
            except Exception as e:
                log_with_extra(
                    self.logger,
                    "error",
                    f"Error stopping consumer for topic {topic}: {str(e)}",
                    topic=topic,
                    error=str(e)
                )

        # Stop producer
        if self._producer:
            try:
                await self._producer.stop()
                log_with_extra(
                    self.logger,
                    "info",
                    "Producer stopped"
                )
            except Exception as e:
                log_with_extra(
                    self.logger,
                    "error",
                    f"Error stopping producer: {str(e)}",
                    error=str(e)
                )

        self._is_running = False
        self._consumers.clear()
        self._consumer_tasks.clear()

    async def publish(
        self,
        topic: str,
        message: Dict[str, Any],
        key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Publish a message to a Kafka topic.
        
        Args:
            topic: Topic name to publish to
            message: Message payload (will be JSON serialized)
            key: Optional message key for partitioning
            headers: Optional message headers
            
        Raises:
            RuntimeError: If the client is not started
            KafkaError: If publishing fails
        """
        if not self._is_running or not self._producer:
            raise RuntimeError("Kafka client is not started. Call start() first.")

        try:
            # Convert headers to bytes if provided
            kafka_headers = None
            if headers:
                kafka_headers = [(k, v.encode('utf-8')) for k, v in headers.items()]

            # Send message
            await self._producer.send(
                topic,
                value=message,
                key=key,
                headers=kafka_headers
            )
            
            log_with_extra(
                self.logger,
                "debug",
                f"Message published to topic",
                topic=topic,
                key=key,
                has_headers=headers is not None
            )
            
        except KafkaError as e:
            log_with_extra(
                self.logger,
                "error",
                f"Failed to publish message to topic {topic}: {str(e)}",
                topic=topic,
                error=str(e)
            )
            raise
        except Exception as e:
            log_with_extra(
                self.logger,
                "error",
                f"Unexpected error publishing message: {str(e)}",
                topic=topic,
                error=str(e)
            )
            raise

    async def publish_batch(
        self,
        topic: str,
        messages: List[Dict[str, Any]],
        keys: Optional[List[Optional[str]]] = None,
    ) -> None:
        """
        Publish multiple messages to a Kafka topic in a batch.
        
        Args:
            topic: Topic name to publish to
            messages: List of message payloads
            keys: Optional list of message keys (must match messages length)
            
        Raises:
            RuntimeError: If the client is not started
            ValueError: If keys length doesn't match messages length
            KafkaError: If publishing fails
        """
        if not self._is_running or not self._producer:
            raise RuntimeError("Kafka client is not started. Call start() first.")

        if keys and len(keys) != len(messages):
            raise ValueError("Keys list must have the same length as messages list")

        try:
            # Send all messages
            tasks = []
            for idx, message in enumerate(messages):
                key = keys[idx] if keys else None
                task = self._producer.send(topic, value=message, key=key)
                tasks.append(task)
            
            # Wait for all sends to complete
            await asyncio.gather(*tasks)
            
            log_with_extra(
                self.logger,
                "info",
                f"Batch published to topic",
                topic=topic,
                message_count=len(messages)
            )
            
        except KafkaError as e:
            log_with_extra(
                self.logger,
                "error",
                f"Failed to publish batch to topic {topic}: {str(e)}",
                topic=topic,
                message_count=len(messages),
                error=str(e)
            )
            raise

    async def subscribe(
        self,
        topics: List[str],
        group_id: str,
        handler: Callable[[ConsumerRecord], Any],
        auto_start: bool = True,
    ) -> str:
        """
        Subscribe to Kafka topics and process messages with a handler.
        
        Args:
            topics: List of topic names to subscribe to
            group_id: Consumer group ID
            handler: Async function to handle each message
            auto_start: Whether to start consuming immediately
            
        Returns:
            Consumer identifier for managing the subscription
            
        Raises:
            RuntimeError: If the client is not started
        """
        if not self._is_running:
            raise RuntimeError("Kafka client is not started. Call start() first.")

        consumer_id = f"{group_id}_{','.join(topics)}"
        
        try:
            # Create consumer
            consumer = AIOKafkaConsumer(
                *topics,
                bootstrap_servers=self.bootstrap_servers,
                group_id=group_id,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                key_deserializer=lambda k: k.decode('utf-8') if k else None,
                **self._consumer_config
            )
            
            await consumer.start()
            self._consumers[consumer_id] = consumer
            
            log_with_extra(
                self.logger,
                "info",
                f"Consumer created and subscribed",
                consumer_id=consumer_id,
                topics=topics,
                group_id=group_id
            )
            
            # Start consuming if auto_start is True
            if auto_start:
                task = asyncio.create_task(
                    self._consume_messages(consumer_id, consumer, handler)
                )
                self._consumer_tasks[consumer_id] = task
            
            return consumer_id
            
        except Exception as e:
            log_with_extra(
                self.logger,
                "error",
                f"Failed to subscribe to topics: {str(e)}",
                topics=topics,
                group_id=group_id,
                error=str(e)
            )
            raise

    async def _consume_messages(
        self,
        consumer_id: str,
        consumer: AIOKafkaConsumer,
        handler: Callable[[ConsumerRecord], Any],
    ) -> None:
        """
        Internal method to consume messages from Kafka.
        
        Args:
            consumer_id: Identifier for this consumer
            consumer: AIOKafkaConsumer instance
            handler: Message handler function
        """
        log_with_extra(
            self.logger,
            "info",
            f"Started consuming messages",
            consumer_id=consumer_id
        )
        
        try:
            async for message in consumer:
                try:
                    # Call the handler
                    result = handler(message)
                    if asyncio.iscoroutine(result):
                        await result
                    
                    log_with_extra(
                        self.logger,
                        "debug",
                        f"Message processed",
                        topic=message.topic,
                        partition=message.partition,
                        offset=message.offset,
                        consumer_id=consumer_id
                    )
                    
                except Exception as e:
                    log_with_extra(
                        self.logger,
                        "error",
                        f"Error processing message: {str(e)}",
                        topic=message.topic,
                        partition=message.partition,
                        offset=message.offset,
                        error=str(e),
                        consumer_id=consumer_id
                    )
                    # Continue processing other messages
                    
        except asyncio.CancelledError:
            log_with_extra(
                self.logger,
                "info",
                f"Consumer task cancelled",
                consumer_id=consumer_id
            )
            raise
        except Exception as e:
            log_with_extra(
                self.logger,
                "error",
                f"Fatal error in consumer loop: {str(e)}",
                consumer_id=consumer_id,
                error=str(e)
            )

    async def unsubscribe(self, consumer_id: str) -> None:
        """
        Unsubscribe and stop a specific consumer.
        
        Args:
            consumer_id: The consumer identifier returned by subscribe()
        """
        # Cancel the consumer task
        if consumer_id in self._consumer_tasks:
            task = self._consumer_tasks[consumer_id]
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            del self._consumer_tasks[consumer_id]

        # Stop the consumer
        if consumer_id in self._consumers:
            consumer = self._consumers[consumer_id]
            await consumer.stop()
            del self._consumers[consumer_id]
            
            log_with_extra(
                self.logger,
                "info",
                f"Consumer unsubscribed",
                consumer_id=consumer_id
            )

    async def get_topic_partitions(self, topic: str) -> Set[int]:
        """
        Get the partition IDs for a specific topic.
        
        Args:
            topic: Topic name
            
        Returns:
            Set of partition IDs
            
        Raises:
            RuntimeError: If the client is not started
        """
        if not self._is_running or not self._producer:
            raise RuntimeError("Kafka client is not started. Call start() first.")

        partitions = await self._producer.partitions_for(topic)
        return partitions or set()

    async def flush(self) -> None:
        """
        Flush all pending messages in the producer.
        
        This ensures all buffered messages are sent before returning.
        """
        if self._producer:
            await self._producer.flush()

    @property
    def is_running(self) -> bool:
        """Check if the Kafka client is currently running."""
        return self._is_running

    @property
    def active_consumers(self) -> List[str]:
        """Get list of active consumer IDs."""
        return list(self._consumers.keys())

    @asynccontextmanager
    async def managed_lifecycle(self):
        """
        Context manager for automatic lifecycle management.
        
        Usage:
            async with kafka_client.managed_lifecycle():
                await kafka_client.publish("topic", {"data": "value"})
        """
        await self.start()
        try:
            yield self
        finally:
            await self.stop()


# Singleton instance (optional)
_kafka_client_instance: Optional[KafkaClient] = None


def get_kafka_client(
    bootstrap_servers: Optional[str] = None,
    client_id: Optional[str] = None,
    logger: Optional[logging.Logger] = None,
) -> KafkaClient:
    """
    Get or create a singleton Kafka client instance.
    
    If parameters are not provided, they will be loaded from the application config.
    
    Args:
        bootstrap_servers: Kafka broker addresses (defaults to config.KAFKA_BOOTSTRAP_SERVERS)
        client_id: Client identifier (defaults to config.KAFKA_CLIENT_ID)
        logger: Logger instance (defaults to None)
        
    Returns:
        KafkaClient instance
    """
    global _kafka_client_instance
    
    if _kafka_client_instance is None:
        # Load from config if not provided
        if bootstrap_servers is None or client_id is None:
            from app.config import get_settings
            settings = get_settings()
            
            if bootstrap_servers is None:
                bootstrap_servers = settings.KAFKA_BOOTSTRAP_SERVERS
            if client_id is None:
                client_id = settings.KAFKA_CLIENT_ID
        
        _kafka_client_instance = KafkaClient(
            bootstrap_servers=bootstrap_servers,
            client_id=client_id,
            logger=logger
        )
    
    return _kafka_client_instance
