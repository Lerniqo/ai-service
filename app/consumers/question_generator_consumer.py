"""
Question Generation Consumer for handling question generation requests from Kafka.

This module provides functionality to:
- Subscribe to the 'question.generation.request' Kafka topic
- Validate incoming requests using Pydantic schemas
- Generate questions using the LLM
- Publish responses to the 'question.generation.response' topic
"""

import logging
from typing import Optional
from aiokafka.structs import ConsumerRecord
from pydantic import ValidationError

from app.clients.kafka_client import get_kafka_client
from app.llm.main import get_llm_service
from app.schema.events import QuestionGenerationRequestEvent, QuestionGenerationResponseEvent
from app.schema.event_data import QuestionGenerationResponseData
from app.core.logging import log_with_extra
from app.config import get_settings


class QuestionGeneratorConsumer:
    """
    Consumer for handling question generation requests from Kafka.
    
    This consumer listens to question generation requests, processes them
    using the LLM service, and publishes the results back to Kafka.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the question generator consumer.
        
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
            "QuestionGeneratorConsumer initialized"
        )

    async def handle_request(self, message: ConsumerRecord) -> None:
        """
        Handle incoming question generation request messages from Kafka.
        
        This method:
        1. Extracts and validates the message
        2. Generates questions using the LLM
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
                "Received question generation request",
                topic=message.topic,
                partition=message.partition,
                offset=message.offset
            )
            
            # Validate request event
            try:
                validated_event = QuestionGenerationRequestEvent(**event_data)
                request_id = validated_event.event_data.request_id
                
                log_with_extra(
                    self.logger,
                    "info",
                    "Question generation request validated",
                    request_id=request_id,
                    topic=validated_event.event_data.topic,
                    num_questions=validated_event.event_data.num_questions
                )
                
                # Process the request
                await self._process_request(validated_event)
                
            except ValidationError as e:
                log_with_extra(
                    self.logger,
                    "error",
                    "Question generation request validation failed",
                    validation_errors=e.errors(),
                    event_data=event_data
                )
                raise
                
        except Exception as e:
            log_with_extra(
                self.logger,
                "error",
                f"Error handling question generation request: {str(e)}",
                request_id=request_id,
                error=str(e)
            )
            
            # Try to send error response if we have a request_id
            if request_id:
                await self._send_error_response(request_id, str(e))

    async def _process_request(self, event: QuestionGenerationRequestEvent) -> None:
        """
        Process a question generation request and send response.
        
        Args:
            event: Validated question generation request event
        """
        request_data = event.event_data
        request_id = request_data.request_id
        
        try:
            log_with_extra(
                self.logger,
                "info",
                "Generating questions",
                request_id=request_id,
                topic=request_data.topic,
                num_questions=request_data.num_questions
            )
            
            # Generate questions using LLM service
            question_set = await self.llm_service.agenerate_questions(
                topic=request_data.topic,
                num_questions=request_data.num_questions,
                question_types=request_data.question_types,
                difficulty=request_data.difficulty
            )
            
            # Create response event
            response_data = QuestionGenerationResponseData(
                request_id=request_id,
                status="completed",
                topic=question_set.topic,
                total_questions=question_set.total_questions,
                questions=[q.model_dump(mode='json') for q in question_set.questions],
                content_id=request_data.content_id,
                user_id=request_data.user_id,
                metadata=request_data.metadata
            )
            
            response_event = QuestionGenerationResponseEvent(
                event_type="question.generation.response",
                event_data=response_data,
                user_id="ai-service",
                metadata={
                    "source": "ai-service",
                    "request_id": request_id
                }
            )
            
            # Publish response to Kafka
            await self.kafka_client.publish(
                topic=self.settings.KAFKA_QUESTION_RESPONSE_TOPIC,
                message=response_event.model_dump(mode='json', by_alias=True),
                key=request_id
            )
            
            log_with_extra(
                self.logger,
                "info",
                "Question generation completed and response published",
                request_id=request_id,
                total_questions=question_set.total_questions,
                response_topic=self.settings.KAFKA_QUESTION_RESPONSE_TOPIC
            )
            
        except Exception as e:
            log_with_extra(
                self.logger,
                "error",
                f"Error processing question generation request: {str(e)}",
                request_id=request_id,
                error=str(e)
            )
            await self._send_error_response(request_id, str(e), request_data.metadata)

    async def _send_error_response(
        self, 
        request_id: str, 
        error_message: str,
        metadata: Optional[dict] = None
    ) -> None:
        """
        Send an error response to the response topic.
        
        Args:
            request_id: The request identifier
            error_message: The error message
            metadata: Optional metadata to include
        """
        try:
            response_data = QuestionGenerationResponseData(
                request_id=request_id,
                status="failed",
                error=error_message,
                metadata=metadata
            )
            
            response_event = QuestionGenerationResponseEvent(
                event_type="question.generation.response",
                event_data=response_data,
                user_id="ai-service",
                metadata={
                    "source": "ai-service",
                    "request_id": request_id,
                    "error": True
                }
            )
            
            await self.kafka_client.publish(
                topic=self.settings.KAFKA_QUESTION_RESPONSE_TOPIC,
                message=response_event.model_dump(mode='json', by_alias=True),
                key=request_id
            )
            
            log_with_extra(
                self.logger,
                "info",
                "Error response published",
                request_id=request_id,
                response_topic=self.settings.KAFKA_QUESTION_RESPONSE_TOPIC
            )
            
        except Exception as e:
            log_with_extra(
                self.logger,
                "error",
                f"Failed to send error response: {str(e)}",
                request_id=request_id,
                error=str(e)
            )


def create_question_generator_consumer(logger: Optional[logging.Logger] = None) -> QuestionGeneratorConsumer:
    """
    Factory function to create a QuestionGeneratorConsumer instance.
    
    Args:
        logger: Logger instance for structured logging
        
    Returns:
        QuestionGeneratorConsumer instance
    """
    return QuestionGeneratorConsumer(logger=logger)
