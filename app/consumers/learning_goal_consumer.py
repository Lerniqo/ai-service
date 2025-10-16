"""
Learning Goal consumer for handling learning goal events from Kafka 'learning_goal' topic.

This module provides functionality to:
- Subscribe to the 'learning_goal' Kafka topic
- Validate incoming learning goal events using Pydantic schemas
- Process events using the LearningPathAgent to generate personalized learning paths
- Publish the generated learning paths to the 'learning_path' Kafka topic
"""

import logging
from typing import Optional
from aiokafka.structs import ConsumerRecord
from pydantic import ValidationError

from app.clients.kafka_client import get_kafka_client
from app.schema.events import LearningGoalEvent
from app.llm.agents.learning_path import LearningPathAgent
from app.core.logging import log_with_extra


class LearningGoalConsumer:
    """
    Consumer for handling learning goal events from the Kafka 'learning_goal' topic.
    
    This consumer validates incoming learning goal events using Pydantic schemas,
    processes them using the LearningPathAgent, and publishes the results.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the learning goal consumer.
        
        Args:
            logger: Logger instance for structured logging
        """
        self.logger = logger or logging.getLogger(__name__)
        # Lazy initialization to avoid Pydantic model definition issues
        self._learning_path_agent: Optional[LearningPathAgent] = None
        log_with_extra(
            self.logger,
            "info",
            "LearningGoalConsumer initialized (agent will be created on first use)"
        )
    
    @property
    def learning_path_agent(self) -> LearningPathAgent:
        """Get or create the learning path agent (lazy initialization)."""
        if self._learning_path_agent is None:
            self._learning_path_agent = LearningPathAgent()
            log_with_extra(
                self.logger,
                "info",
                "LearningPathAgent created"
            )
        return self._learning_path_agent

    async def handle_learning_goal(self, message: ConsumerRecord) -> None:
        """
        Handle incoming learning goal messages from Kafka.
        
        This method:
        1. Extracts the message value
        2. Validates it against the LearningGoalEvent Pydantic schema
        3. Processes the validated event using LearningPathAgent
        4. Publishes the generated learning path to Kafka
        
        Args:
            message: Kafka ConsumerRecord containing the learning goal data
            
        Raises:
            ValidationError: If the learning goal data doesn't match the schema
        """
        try:
            # Extract message data
            event_data = message.value
            
            log_with_extra(
                self.logger,
                "debug",
                "Received learning goal message",
                topic=message.topic,
                partition=message.partition,
                offset=message.offset,
                timestamp=message.timestamp
            )
            
            # Validate event data using Pydantic schema
            try:
                validated_event = LearningGoalEvent(**event_data)
                
                log_with_extra(
                    self.logger,
                    "info",
                    "Learning goal event validated successfully",
                    event_type=validated_event.event_type,
                    user_id=validated_event.user_id,
                    learning_goal=validated_event.event_data.learning_goal,
                    offset=message.offset
                )
                
                # Process the learning goal event
                await self._process_learning_goal(validated_event)
                
            except ValidationError as e:
                log_with_extra(
                    self.logger,
                    "error",
                    "Learning goal event validation failed",
                    validation_errors=e.errors(),
                    event_data=event_data,
                    offset=message.offset
                )
                raise
                
        except Exception as e:
            log_with_extra(
                self.logger,
                "error",
                f"Error handling learning goal event: {str(e)}",
                error=str(e),
                error_type=type(e).__name__,
                offset=message.offset
            )
            # Re-raise to let the Kafka client handle it
            raise

    async def _process_learning_goal(self, event: LearningGoalEvent) -> None:
        """
        Process a validated learning goal event.
        
        This method uses the LearningPathAgent to:
        1. Fetch user's mastery scores and available resources from content service
        2. Generate a personalized learning path
        3. Publish the learning path to Kafka 'learning_path' topic
        
        Args:
            event: Validated LearningGoalEvent object
        """
        try:
            log_with_extra(
                self.logger,
                "info",
                "Processing learning goal",
                user_id=event.user_id,
                learning_goal=event.event_data.learning_goal,
                current_level=event.event_data.current_level
            )
            
            # Generate learning path using the agent
            learning_path = await self.learning_path_agent.generate_learning_path(
                user_id=event.user_id,
                goal=event.event_data.learning_goal,
                current_level=event.event_data.current_level,
                preferences=event.event_data.preferences,
                available_time=event.event_data.available_time
            )
            
            log_with_extra(
                self.logger,
                "info",
                "Successfully generated and published learning path",
                user_id=event.user_id,
                learning_goal=event.event_data.learning_goal,
                num_steps=len(learning_path.steps),
                total_duration=learning_path.total_duration
            )
            
        except Exception as e:
            log_with_extra(
                self.logger,
                "error",
                f"Error processing learning goal: {str(e)}",
                user_id=event.user_id,
                learning_goal=event.event_data.learning_goal,
                error=str(e),
                error_type=type(e).__name__
            )
            raise


def create_learning_goal_consumer(logger: Optional[logging.Logger] = None) -> LearningGoalConsumer:
    """
    Factory function to create a LearningGoalConsumer instance.
    
    Args:
        logger: Optional logger instance
        
    Returns:
        LearningGoalConsumer instance
    """
    return LearningGoalConsumer(logger=logger)
