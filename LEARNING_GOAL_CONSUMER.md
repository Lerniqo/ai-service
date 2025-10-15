# Learning Goal Consumer

This module implements a Kafka consumer that processes learning goal events and generates personalized learning paths using an LLM-based agent.

## Overview

The Learning Goal Consumer listens to the `learning_goal` Kafka topic, processes incoming learning goal events, and generates personalized learning paths based on:
- User's learning goal
- Current knowledge level
- Available resources from the content service
- User's mastery scores
- Learning preferences and available time

## Architecture

```
learning_goal topic → LearningGoalConsumer → LearningPathAgent → learning_path topic
                                                     ↓
                                            ContentServiceClient
                                            - Fetch resources
                                            - Fetch mastery scores
```

## Components

### 1. Event Schema (`app/schema/events.py`)

#### LearningGoalData
```python
{
    "learningGoal": "Learn Python programming",
    "currentLevel": "beginner",  # beginner, intermediate, advanced
    "preferences": {
        "format": "video",
        "topics": ["basics", "data structures"]
    },
    "availableTime": "2 hours/day"
}
```

#### LearningGoalEvent
```python
{
    "eventId": "evt_abc123def",
    "eventType": "LEARNING_GOAL",
    "eventData": { ... },  # LearningGoalData
    "userId": "user_789",
    "metadata": {
        "source": "web_app",
        "version": "1.0.0"
    }
}
```

### 2. Learning Goal Consumer (`app/consumers/learning_goal_consumer.py`)

The consumer:
1. Validates incoming messages against the `LearningGoalEvent` schema
2. Extracts user ID and learning goal information
3. Passes the data to the `LearningPathAgent` for processing
4. Logs all operations for observability

### 3. Learning Path Agent (`app/llm/agents/learning_path.py`)

The agent:
1. Accepts `user_id` and `learning_goal` as inputs
2. Fetches available resources from the content service
3. Retrieves user's mastery scores from the content service
4. Generates a personalized learning path using an LLM (Google Gemini)
5. Publishes the generated learning path to the `learning_path` Kafka topic

#### Updated Method Signature
```python
async def generate_learning_path(
    user_id: str,
    goal: str,
    current_level: str = "beginner",
    preferences: Optional[Dict[str, Any]] = None,
    available_time: str = "flexible"
) -> LearningPath
```

### 4. Content Service Client (`app/clients/content_service.py`)

New methods added:
```python
# Fetch available resources for a user
async def get_available_resources(user_id: str) -> List[Dict[str, Any]]

# Fetch user's mastery scores
async def get_user_mastery_score(user_id: str) -> Dict[str, Any]
```

## Kafka Topics

### Input Topic: `learning_goal`
- **Purpose**: Receives learning goal requests from users
- **Consumer Group**: `ai-service-learning-goal-consumer`
- **Message Format**: `LearningGoalEvent` (JSON)

### Output Topic: `learning_path`
- **Purpose**: Publishes generated learning paths
- **Producer**: `LearningPathAgent`
- **Message Format**:
```python
{
    "user_id": "user_789",
    "learning_goal": "Learn Python programming",
    "learning_path": {
        "goal": "...",
        "difficulty_level": "beginner",
        "total_duration": "4 weeks",
        "steps": [
            {
                "step_number": 1,
                "title": "Python Basics",
                "description": "...",
                "estimated_duration": "1 week",
                "resources": [...],
                "prerequisites": []
            },
            ...
        ]
    },
    "mastery_scores": { ... },
    "available_resources": [ ... ]
}
```

## Usage

### Starting the Service

The consumer is automatically registered and started when the FastAPI application starts:

```python
# In app/main.py
@app.on_event("startup")
async def startup_event():
    # ... Kafka client initialization ...
    
    # Initialize learning goal consumer
    learning_goal_consumer = create_learning_goal_consumer(logger=logger)
    
    # Subscribe to learning_goal topic
    await kafka_client.subscribe(
        topics=["learning_goal"],
        group_id="ai-service-learning-goal-consumer",
        handler=learning_goal_consumer.handle_learning_goal,
        auto_start=True
    )
```

### Publishing a Learning Goal Event

To test the consumer, publish a message to the `learning_goal` topic:

```python
from app.clients.kafka_client import get_kafka_client

kafka_client = get_kafka_client()
await kafka_client.start()

await kafka_client.send(
    topic="learning_goal",
    value={
        "eventId": "evt_test123",
        "eventType": "LEARNING_GOAL",
        "eventData": {
            "learningGoal": "Learn Python programming",
            "currentLevel": "beginner",
            "preferences": {
                "format": "video",
                "topics": ["basics", "OOP"]
            },
            "availableTime": "2 hours/day"
        },
        "userId": "user_123",
        "metadata": {
            "source": "test",
            "version": "1.0.0"
        }
    },
    key="user_123"
)
```

### Using Kafka CLI

```bash
# Produce a test message
echo '{
  "eventId": "evt_test123",
  "eventType": "LEARNING_GOAL",
  "eventData": {
    "learningGoal": "Learn Python programming",
    "currentLevel": "beginner",
    "availableTime": "2 hours/day"
  },
  "userId": "user_123"
}' | kafka-console-producer --broker-list localhost:9092 --topic learning_goal

# Consume from the output topic
kafka-console-consumer --bootstrap-server localhost:9092 \
  --topic learning_path \
  --from-beginning \
  --property print.key=true
```

## Configuration

Environment variables required:

```env
# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_CLIENT_ID=ai-service

# Content Service
CONTENT_SERVICE_BASE_URL=http://localhost:3001
CONTENT_SERVICE_SECRET=your_secret_here

# LLM Configuration
GOOGLE_API_KEY=your_google_api_key
LLM_MODEL=gemini-1.5-flash
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000
```

## Error Handling

The consumer implements comprehensive error handling:

1. **Validation Errors**: Invalid events are logged and rejected
2. **Content Service Errors**: Gracefully handles service unavailability
3. **LLM Errors**: Logs failures in path generation
4. **Kafka Publishing Errors**: Logs but doesn't fail the processing

All errors are logged with structured logging for observability.

## Monitoring

Key log events to monitor:

```
INFO: LearningGoalConsumer initialized with LearningPathAgent
INFO: Learning goal event validated successfully
INFO: Processing learning goal (user_id, learning_goal)
INFO: Successfully generated and published learning path
ERROR: Learning goal event validation failed
ERROR: Error processing learning goal
```

## Testing

Example test case:

```python
import pytest
from app.consumers.learning_goal_consumer import create_learning_goal_consumer
from app.schema.events import LearningGoalEvent

@pytest.mark.asyncio
async def test_learning_goal_consumer():
    consumer = create_learning_goal_consumer()
    
    # Create mock message
    event = LearningGoalEvent(
        eventType="LEARNING_GOAL",
        eventData={
            "learningGoal": "Learn Python",
            "currentLevel": "beginner"
        },
        userId="test_user"
    )
    
    # Process event
    await consumer._process_learning_goal(event)
    
    # Assert learning path was generated and published
    # ... assertions ...
```

## Future Enhancements

1. **Caching**: Cache mastery scores and resources to reduce API calls
2. **Batch Processing**: Process multiple learning goals in parallel
3. **Fallback Strategies**: Provide default learning paths when services are unavailable
4. **Progress Tracking**: Integrate with progress service to track learning path completion
5. **A/B Testing**: Generate multiple learning paths and track effectiveness
