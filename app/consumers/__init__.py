"""Kafka consumers for the AI service."""

from app.consumers.event_consumer import EventConsumer, create_event_consumer
from app.consumers.learning_goal_consumer import LearningGoalConsumer, create_learning_goal_consumer

__all__ = [
    "EventConsumer",
    "create_event_consumer",
    "LearningGoalConsumer",
    "create_learning_goal_consumer",
]
