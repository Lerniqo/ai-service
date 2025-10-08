# Event Schemas

This module contains Pydantic schemas for events in the AI service, matching the TypeScript/Mongoose schemas from the progress service.

## Structure

```
app/schema/
├── __init__.py          # Package exports
├── event_data.py        # Event data schemas (EventDataBase, QuizAttemptData)
├── events.py            # Event wrapper schemas (Event, QuizAttemptEvent)
└── README.md           # This file
```

## Usage Examples

### Creating a Quiz Attempt Event

```python
from datetime import datetime
from app.schema import QuizAttemptEvent, QuizAttemptData

# Create event data
event_data = QuizAttemptData(
    created_at=datetime.now(),
    updated_at=datetime.now(),
    quiz_id="quiz_123",
    score=85.5,
    concepts=["algebra", "geometry", "trigonometry"],
    status="completed"
)

# Create the event
event = QuizAttemptEvent(
    event_type="quiz.attempt.completed",
    event_data=event_data,
    user_id="user_456",
    metadata={
        "source": "web_app",
        "version": "1.0.0"
    }
)

# Serialize to dict
event_dict = event.model_dump()

# Serialize to JSON
event_json = event.model_dump_json()
```

### Parsing Events from JSON

```python
from app.schema import QuizAttemptEvent

# Parse from JSON string
json_string = '{"event_type": "quiz.attempt.completed", ...}'
event = QuizAttemptEvent.model_validate_json(json_string)

# Parse from dict
event_dict = {"event_type": "quiz.attempt.completed", ...}
event = QuizAttemptEvent.model_validate(event_dict)
```

### Generic Event Handling

```python
from app.schema import Event

# Use generic Event class when event type is unknown
event = Event(
    event_type="quiz.attempt.started",
    event_data=event_data,
    user_id="user_456"
)
```

## Schema Details

### EventDataBase

Base class for all event data. Contains common fields:
- `created_at`: DateTime (required)
- `updated_at`: DateTime (required)

### QuizAttemptData

Extends `EventDataBase` with quiz-specific fields:
- `quiz_id`: str (required)
- `score`: float (optional, 0-100)
- `concepts`: List[str] (required, min 1 item)
- `status`: str (required, one of: 'pending', 'completed', 'abandoned')

### Event

Generic event wrapper:
- `event_type`: str (required)
- `event_data`: Union[QuizAttemptData, EventDataBase] (required)
- `user_id`: str (required)
- `metadata`: Dict[str, Any] (optional)

### QuizAttemptEvent

Specific event for quiz attempts (extends Event):
- `event_data`: QuizAttemptData (required, strictly typed)

## Validation

All schemas include comprehensive validation:
- Required field checks
- Type validation
- Range validation (e.g., score 0-100)
- Custom validators (e.g., status enum, non-empty concepts)
- Empty string prevention

## Testing

Run the test suite:
```bash
source venv/bin/activate
python -m pytest tests/schema/test_events.py -v
```
