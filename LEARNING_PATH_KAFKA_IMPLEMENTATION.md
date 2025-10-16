# Learning Path Kafka Implementation Summary

## Overview
Successfully migrated the learning path generation functionality to use Kafka messaging system. The system now receives requests via the `learning_path.request` topic and publishes responses to the `learning_path.response` topic.

## Changes Made

### 1. Event Data Schemas (`app/schema/event_data.py`)
- **Added `LearningPathRequestData`**: Schema for learning path generation request events
  - Fields: `request_id`, `user_id`, `goal`, `current_level`, `preferences`, `available_time`, `metadata`
  - Validates `current_level` (beginner, intermediate, advanced)
  
- **Added `LearningPathResponseData`**: Schema for learning path generation response events
  - Fields: `request_id`, `status`, `user_id`, `goal`, `learning_path`, `error`, `metadata`
  - Validates `status` (completed, failed)

### 2. Event Schemas (`app/schema/events.py`)
- **Added `LearningPathRequestEvent`**: Event wrapper for learning path requests
  - Event type: `learning_path.request`
  - Contains `LearningPathRequestData` as event_data
  
- **Added `LearningPathResponseEvent`**: Event wrapper for learning path responses
  - Event type: `learning_path.response`
  - Contains `LearningPathResponseData` as event_data

### 3. Configuration (`app/config.py`)
- **Added Kafka topic configurations**:
  - `KAFKA_LEARNING_PATH_REQUEST_TOPIC`: Default `"learning_path.request"`
  - `KAFKA_LEARNING_PATH_RESPONSE_TOPIC`: Default `"learning_path.response"`

### 4. Consumer Implementation (`app/consumers/learning_path_request_consumer.py`)
- **Created `LearningPathRequestConsumer`**: New consumer class to handle learning path generation requests
  - Subscribes to `learning_path.request` topic
  - Validates incoming events using Pydantic schemas
  - Generates learning paths using LLM service
  - Publishes responses to `learning_path.response` topic
  - Handles errors and publishes error responses

- **Key Methods**:
  - `handle_request()`: Main handler for incoming Kafka messages
  - `_process_request()`: Processes validated requests and generates learning paths
  - `_send_error_response()`: Sends error responses when processing fails

### 5. API Endpoint Updates (`app/api/llm.py`)
- **Added Request/Response Models**:
  - `ContentServiceLearningPathRequest`: HTTP request model for learning path generation
  - `ContentServiceLearningPathResponse`: HTTP response model with status and message
  
- **Updated `/llm/learning-path/generate` endpoint**:
  - Now publishes requests to Kafka instead of processing directly
  - Returns immediate acknowledgment (status: "accepted")
  - HTTP endpoint is optional - primary flow is via Kafka

### 6. Main Application Registration (`app/main.py`)
- **Imported consumer factory**: `create_learning_path_request_consumer`
- **Added global consumer variable**: `learning_path_request_consumer`
- **Registered consumer in startup event**:
  - Subscribes to `learning_path.request` topic
  - Consumer group: `ai-service-learning-path-request-consumer`
  - Handler: `learning_path_request_consumer.handle_request`

## Kafka Flow

### Request Flow
1. Content service publishes message to `learning_path.request` topic
2. `LearningPathRequestConsumer` picks up the message
3. Message is validated against `LearningPathRequestEvent` schema
4. Learning path is generated using LLM service
5. Response is published to `learning_path.response` topic

### Message Format

#### Request Message (learning_path.request)
```json
{
  "eventId": "evt_lp_request_123",
  "eventType": "learning_path.request",
  "eventData": {
    "request_id": "lp-req-123",
    "user_id": "user-789",
    "goal": "Learn Python programming",
    "current_level": "beginner",
    "preferences": {"learning_style": "visual"},
    "available_time": "2 hours per day"
  },
  "userId": "user-789",
  "metadata": {
    "source": "content-service"
  }
}
```

#### Response Message (learning_path.response)
```json
{
  "eventId": "evt_lp_response_123",
  "eventType": "learning_path.response",
  "eventData": {
    "request_id": "lp-req-123",
    "status": "completed",
    "user_id": "user-789",
    "goal": "Learn Python programming",
    "learning_path": {
      // Generated learning path data
    }
  },
  "userId": "ai-service",
  "metadata": {
    "source": "ai-service",
    "request_id": "lp-req-123"
  }
}
```

#### Error Response
```json
{
  "eventId": "evt_lp_response_456",
  "eventType": "learning_path.response",
  "eventData": {
    "request_id": "lp-req-456",
    "status": "failed",
    "user_id": "user-789",
    "error": "Error message here"
  },
  "userId": "ai-service",
  "metadata": {
    "source": "ai-service",
    "request_id": "lp-req-456",
    "error": true
  }
}
```

## Configuration Environment Variables

Add these to your `.env` files:

```bash
# Kafka Learning Path Topics
KAFKA_LEARNING_PATH_REQUEST_TOPIC=learning_path.request
KAFKA_LEARNING_PATH_RESPONSE_TOPIC=learning_path.response
```

## Testing

### Test Consumer
The consumer will automatically start when the application starts. Monitor logs for:
- Consumer initialization: `"LearningPathRequestConsumer initialized"`
- Subscription success: `"Successfully subscribed to learning path request Kafka topic"`

### Send Test Message
Use your Kafka producer or the HTTP endpoint to send a test request:

```bash
# Via HTTP (which publishes to Kafka)
curl -X POST http://localhost:8000/llm/learning-path/generate \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "test-123",
    "user_id": "user-456",
    "goal": "Learn Python",
    "current_level": "beginner",
    "available_time": "2 hours/day"
  }'
```

## Notes
- The HTTP endpoint is now optional and mainly serves as a convenient way to publish to Kafka
- The actual processing happens asynchronously via the Kafka consumer
- Error handling publishes failed responses to the response topic
- All messages use Pydantic validation for data integrity
- Consumer group ensures horizontal scaling capability
