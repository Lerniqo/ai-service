"""Schema package for event and data models."""
from app.schema.event_data import EventDataBase, QuizAttemptData
from app.schema.events import Event, QuizAttemptEvent

__all__ = [
    "EventDataBase",
    "QuizAttemptData",
    "Event",
    "QuizAttemptEvent",
]
