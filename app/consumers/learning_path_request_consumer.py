"""
Learning Path Request Consumer for handling learning path generation requests from Kafka.

This module provides functionality to:
- Subscribe to the 'learning_path.request' Kafka topic
- Validate incoming requests using Pydantic schemas
- Generate learning paths using the LLM
- Publish responses to the 'learning_path.response' topic
"""

import logging
from typing import Optional
from aiokafka.structs import ConsumerRecord
from pydantic import ValidationError

from app.clients.kafka_client import get_kafka_client
from app.llm.main import get_llm_service
from app.schema.events import LearningPathRequestEvent, LearningPathResponseEvent
from app.schema.event_data import LearningPathResponseData
from app.core.logging import log_with_extra
from app.config import get_settings


class LearningPathRequestConsumer:
    """
    Consumer for handling learning path generation requests from Kafka.
    
    This consumer listens to learning path requests, processes them
    using the LLM service, and publishes the results back to Kafka.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the learning path request consumer.
        
        Args:
            logger: Logger instance for structured logging
        """
        self.logger = logger or logging.getLogger(__name__)
        self.settings = get_settings()
        self.kafka_client = get_kafka_client()
        self.llm_service = get_llm_service()
        
        log_with_extra(
            self.logger,
            "info",
            "LearningPathRequestConsumer initialized"
        )

    async def handle_request(self, message: ConsumerRecord) -> None:
        """
        Handle incoming learning path generation request messages from Kafka.
        
        This method:
        1. Extracts and validates the message
        2. Generates learning path using the LLM
        3. Publishes the response to the response topic
        
        Args:
            message: Kafka ConsumerRecord containing the request data
        """
        request_id = None
        try:
            # Extract message data
            event_data = message.value
            
            log_with_extra(
                self.logger,
                "debug",
                "Received learning path generation request",
                topic=message.topic,
                partition=message.partition,
                offset=message.offset
            )
            
            # Validate request event
            try:
                validated_event = LearningPathRequestEvent(**event_data)
                request_id = validated_event.event_data.request_id
                
                log_with_extra(
                    self.logger,
                    "info",
                    "Learning path generation request validated",
                    request_id=request_id,
                    user_id=validated_event.event_data.user_id,
                    goal=validated_event.event_data.goal
                )
                
                # Process the request
                await self._process_request(validated_event)
                
            except ValidationError as e:
                log_with_extra(
                    self.logger,
                    "error",
                    "Learning path generation request validation failed",
                    validation_errors=e.errors(),
                    event_data=event_data
                )
                raise
                
        except Exception as e:
            log_with_extra(
                self.logger,
                "error",
                f"Error handling learning path generation request: {str(e)}",
                request_id=request_id,
                error=str(e)
            )
            
            # Try to send error response if we have a request_id
            if request_id:
                await self._send_error_response(request_id, str(e))

    async def _process_request(self, event: LearningPathRequestEvent) -> None:
        """
        Process a learning path generation request and send response.
        
        Args:
            event: Validated learning path generation request event
        """
        request_data = event.event_data
        request_id = request_data.request_id
        
        try:
            log_with_extra(
                self.logger,
                "info",
                "Generating learning path",
                request_id=request_id,
                user_id=request_data.user_id,
                goal=request_data.goal
            )
            
            # Generate learning path using LLM service
            learning_path = await self.llm_service.agenerate_learning_path(
                user_id=request_data.user_id,
                goal=request_data.goal,
                current_level=request_data.current_level,
                preferences=request_data.preferences,
                available_time=request_data.available_time
            )
            
            # Create response event
            response_data = LearningPathResponseData(
                request_id=request_id,
                status="completed",
                user_id=request_data.user_id,
                goal=request_data.goal,
                learning_path=learning_path.model_dump(mode='json'),
                metadata=request_data.metadata
            )
            
            response_event = LearningPathResponseEvent(
                event_type="learning_path.response",
                event_data=response_data,
                user_id="ai-service",
                metadata={
                    "source": "ai-service",
                    "request_id": request_id
                }
            )
            
            # Publish response to Kafka
            await self.kafka_client.publish(
                topic=self.settings.KAFKA_LEARNING_PATH_RESPONSE_TOPIC,
                message=response_event.model_dump(mode='json', by_alias=True),
                key=request_id
            )
            
            log_with_extra(
                self.logger,
                "info",
                "Learning path generation completed and response published",
                request_id=request_id,
                user_id=request_data.user_id,
                response_topic=self.settings.KAFKA_LEARNING_PATH_RESPONSE_TOPIC
            )
            
        except Exception as e:
            log_with_extra(
                self.logger,
                "error",
                f"Error processing learning path generation request: {str(e)}",
                request_id=request_id,
                error=str(e)
            )
            await self._send_error_response(
                request_id, 
                str(e), 
                user_id=request_data.user_id,
                metadata=request_data.metadata
            )

    async def _send_error_response(
        self, 
        request_id: str, 
        error_message: str,
        user_id: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> None:
        """
        Send an error response to the response topic.
        
        Args:
            request_id: The request identifier
            error_message: The error message to send
            user_id: The user ID for the request
            metadata: Optional metadata from the request
        """
        try:
            response_data = LearningPathResponseData(
                request_id=request_id,
                status="failed",
                user_id=user_id or "unknown",
                goal=None,
                learning_path=None,
                error=error_message,
                metadata=metadata
            )
            
            response_event = LearningPathResponseEvent(
                event_type="learning_path.response",
                event_data=response_data,
                user_id="ai-service",
                metadata={
                    "source": "ai-service",
                    "request_id": request_id,
                    "error": True
                }
            )
            
            await self.kafka_client.publish(
                topic=self.settings.KAFKA_LEARNING_PATH_RESPONSE_TOPIC,
                message=response_event.model_dump(mode='json', by_alias=True),
                key=request_id
            )
            
            log_with_extra(
                self.logger,
                "info",
                "Error response published",
                request_id=request_id,
                response_topic=self.settings.KAFKA_LEARNING_PATH_RESPONSE_TOPIC
            )
            
        except Exception as e:
            log_with_extra(
                self.logger,
                "error",
                f"Failed to send error response: {str(e)}",
                request_id=request_id,
                error=str(e)
            )


def create_learning_path_request_consumer(logger: Optional[logging.Logger] = None) -> LearningPathRequestConsumer:
    """
    Factory function to create a LearningPathRequestConsumer instance.
    
    Args:
        logger: Logger instance for structured logging
        
    Returns:
        LearningPathRequestConsumer instance
    """
    return LearningPathRequestConsumer(logger=logger)
