"""
Event consumer for handling events from Kafka 'events' topic.

This module provides functionality to:
- Subscribe to the 'events' Kafka topic
- Validate incoming events using Pydantic schemas
- Process events asynchronously in the background
"""

import logging
from typing import Optional
from aiokafka.structs import ConsumerRecord
from pydantic import ValidationError

from app.schema.events import Event
from app.core.logging import log_with_extra


class EventConsumer:
    """
    Consumer for handling events from the Kafka 'events' topic.
    
    This consumer validates incoming events using Pydantic schemas
    and processes them asynchronously.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the event consumer.
        
        Args:
            logger: Logger instance for structured logging
        """
        self.logger = logger or logging.getLogger(__name__)
        log_with_extra(
            self.logger,
            "info",
            "EventConsumer initialized"
        )

    async def handle_event(self, message: ConsumerRecord) -> None:
        """
        Handle incoming event messages from Kafka.
        
        This method:
        1. Extracts the message value
        2. Validates it against the Event Pydantic schema
        3. Processes the validated event (currently just prints it)
        
        Args:
            message: Kafka ConsumerRecord containing the event data
            
        Raises:
            ValidationError: If the event data doesn't match the schema
        """
        try:
            # Extract message data
            event_data = message.value
            
            log_with_extra(
                self.logger,
                "debug",
                "Received event message",
                topic=message.topic,
                partition=message.partition,
                offset=message.offset,
                timestamp=message.timestamp
            )
            
            # Validate event data using Pydantic schema
            try:
                validated_event = Event(**event_data)
                
                log_with_extra(
                    self.logger,
                    "info",
                    "Event validated successfully",
                    event_type=validated_event.event_type,
                    user_id=validated_event.user_id,
                    offset=message.offset
                )
                
                # Process the event (for now, just print it)
                await self._process_event(validated_event)
                
            except ValidationError as e:
                log_with_extra(
                    self.logger,
                    "error",
                    "Event validation failed",
                    validation_errors=e.errors(),
                    event_data=event_data,
                    offset=message.offset
                )
                raise
                
        except Exception as e:
            log_with_extra(
                self.logger,
                "error",
                f"Error handling event: {str(e)}",
                error=str(e),
                error_type=type(e).__name__,
                offset=message.offset
            )
            # Re-raise to let the Kafka client handle it
            raise

    async def _process_event(self, event: Event) -> None:
        """
        Process a validated event.
        
        Currently this just prints the event data. In the future, this can be
        extended to perform actual business logic based on the event type.
        
        Args:
            event: Validated Event object
        """
        print("\n" + "="*80)
        print("📨 INCOMING EVENT")
        print("="*80)
        print(f"Event Type: {event.event_type}")
        print(f"User ID: {event.user_id}")
        print(f"Event Data: {event.event_data.model_dump()}")
        if event.metadata:
            print(f"Metadata: {event.metadata}")
        print("="*80 + "\n")
        
        log_with_extra(
            self.logger,
            "info",
            "Event processed successfully",
            event_type=event.event_type,
            user_id=event.user_id
        )


def create_event_consumer(logger: Optional[logging.Logger] = None) -> EventConsumer:
    """
    Factory function to create an EventConsumer instance.
    
    Args:
        logger: Optional logger instance
        
    Returns:
        EventConsumer instance
    """
    return EventConsumer(logger=logger)
