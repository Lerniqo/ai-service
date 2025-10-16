# Question Generation System - Kafka Implementation Summary

## 🎯 Overview

Successfully migrated the question generation system from HTTP-based communication to **Kafka-based event streaming** for improved scalability, reliability, and fault tolerance.

## 🏗️ Architecture

```
┌─────────────────┐
│ Content Service │
└────────┬────────┘
         │ HTTP POST
         ▼
┌──────────────────────────────────────┐
│   AI Service API Endpoint            │
│   /llm/questions/generate-for-...    │
└────────┬─────────────────────────────┘
         │ Publish Event
         ▼
┌──────────────────────────────────────┐
│   Kafka Topic                         │
│   question.request                    │
└────────┬─────────────────────────────┘
         │ Consume
         ▼
┌──────────────────────────────────────┐
│   Question Generator Consumer         │
│   (AI Service)                        │
└────────┬─────────────────────────────┘
         │ Generate Questions
         ▼
┌──────────────────────────────────────┐
│   LLM Service (Google Gemini)         │
└────────┬─────────────────────────────┘
         │ Questions Generated
         ▼
┌──────────────────────────────────────┐
│   Kafka Topic                         │
│   question.response                   │
└────────┬─────────────────────────────┘
         │ Consume
         ▼
┌──────────────────────────────────────┐
│   Content Service Consumer            │
└──────────────────────────────────────┘
```

## 📦 Components Created/Modified

### 1. **Event Schemas** (`app/schema/event_data.py`)
- ✅ `QuestionGenerationRequestData` - Request event data structure
- ✅ `QuestionGenerationResponseData` - Response event data structure

### 2. **Event Wrappers** (`app/schema/events.py`)
- ✅ `QuestionGenerationRequestEvent` - Full request event with metadata
- ✅ `QuestionGenerationResponseEvent` - Full response event with metadata

### 3. **Configuration** (`app/config.py`)
- ✅ `KAFKA_QUESTION_REQUEST_TOPIC` - Request topic name (default: `question.request`)
- ✅ `KAFKA_QUESTION_RESPONSE_TOPIC` - Response topic name (default: `question.response`)

### 4. **Consumer** (`app/consumers/question_generator_consumer.py`)
- ✅ `QuestionGeneratorConsumer` - Consumes requests, generates questions, publishes responses
- ✅ Handles errors and publishes failure events
- ✅ Structured logging for monitoring

### 5. **API Endpoint** (`app/api/llm.py`)
- ✅ Modified to publish to Kafka instead of HTTP callbacks
- ✅ Immediate acknowledgment response
- ✅ Async/non-blocking operation

### 6. **Startup Registration** (`app/main.py`)
- ✅ Registered question generator consumer
- ✅ Auto-subscribes to request topic on startup
- ✅ Graceful shutdown handling

## 🔄 Message Flow

### Request Flow
1. **Content Service** → HTTP POST to `/llm/questions/generate-for-content-service`
2. **AI Service API** → Validates request
3. **AI Service API** → Publishes `QuestionGenerationRequestEvent` to Kafka
4. **AI Service API** → Returns HTTP 200 with "accepted" status
5. **Question Generator Consumer** → Picks up message from Kafka
6. **LLM Service** → Generates questions
7. **Question Generator Consumer** → Publishes `QuestionGenerationResponseEvent` to Kafka
8. **Content Service** → Consumes response from Kafka

### Event Structure

#### Request Event
```json
{
  "eventId": "evt_qgen_request_123",
  "eventType": "question.generation.request",
  "eventData": {
    "request_id": "req-123",
    "topic": "Python Loops",
    "num_questions": 5,
    "difficulty": "medium"
  },
  "userId": "content-service"
}
```

#### Response Event (Success)
```json
{
  "eventId": "evt_qgen_response_123",
  "eventType": "question.generation.response",
  "eventData": {
    "request_id": "req-123",
    "status": "completed",
    "questions": [...],
    "total_questions": 5
  },
  "userId": "ai-service"
}
```

## ✨ Benefits of Kafka Implementation

| Feature | HTTP Implementation | Kafka Implementation |
|---------|-------------------|---------------------|
| **Scalability** | Limited by HTTP connections | Infinite horizontal scaling |
| **Reliability** | Lost if service down | Persisted, can replay |
| **Decoupling** | Tight coupling | Loose coupling |
| **Fault Tolerance** | Fails if target unavailable | Queued and processed later |
| **Load Balancing** | Manual implementation | Built-in consumer groups |
| **Monitoring** | Custom metrics needed | Kafka metrics included |
| **Backpressure** | HTTP timeouts | Consumer lag monitoring |
| **Retry Logic** | Manual implementation | Kafka retry/DLQ patterns |

## 🚀 Deployment Checklist

- [ ] Kafka cluster is running and accessible
- [ ] Topics created:
  - [ ] `question.request`
  - [ ] `question.response`
- [ ] Environment variables configured:
  - [ ] `KAFKA_BOOTSTRAP_SERVERS`
  - [ ] `KAFKA_QUESTION_REQUEST_TOPIC=question.request`
  - [ ] `KAFKA_QUESTION_RESPONSE_TOPIC=question.response`
  - [ ] `GOOGLE_API_KEY`
- [ ] AI Service deployed and consuming from question.request topic
- [ ] Content Service configured to:
  - [ ] Send requests via HTTP endpoint
  - [ ] Consume from question.response topic
- [ ] Monitoring configured for:
  - [ ] Consumer lag
  - [ ] Processing latency
  - [ ] Error rates

## 🧪 Testing

### 1. Test Kafka Topics
```bash
# List topics
kafka-topics.sh --list --bootstrap-server localhost:9092

# Create topics if needed
kafka-topics.sh --create --topic question.request \
  --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1

kafka-topics.sh --create --topic question.response \
  --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1
```

### 2. Test API Endpoint
```bash
curl -X POST "http://localhost:8000/llm/questions/generate-for-content-service" \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "test-123",
    "topic": "Python Basics",
    "num_questions": 3,
    "difficulty": "easy"
  }'
```

### 3. Monitor Kafka Messages
```bash
# Watch request topic
kafka-console-consumer.sh --topic question.request \
  --bootstrap-server localhost:9092 --from-beginning

# Watch response topic
kafka-console-consumer.sh --topic question.response \
  --bootstrap-server localhost:9092 --from-beginning
```

### 4. Check Consumer Group
```bash
kafka-consumer-groups.sh --describe \
  --group ai-service-question-generator-consumer \
  --bootstrap-server localhost:9092
```

## 📊 Monitoring

### Key Metrics
- **Request Rate**: Messages/sec to request topic
- **Processing Time**: Time from request to response
- **Success Rate**: Completed vs failed responses
- **Consumer Lag**: Messages waiting to be processed
- **Error Rate**: Failed question generations

### Log Patterns
```
[INFO] Received question generation request req-123 from content service
[INFO] Question generation request req-123 published to Kafka topic: question.generation.request
[INFO] Received question generation request - request_id: req-123, topic: Python Loops
[INFO] Generating questions - request_id: req-123, num_questions: 5
[INFO] Question generation completed and response published - request_id: req-123
```

## 🔧 Configuration Options

### Kafka Consumer Settings
```python
# In app/clients/kafka_client.py
consumer_config = {
    "auto_offset_reset": "earliest",  # Start from beginning if no offset
    "enable_auto_commit": True,        # Auto-commit offsets
    "auto_commit_interval_ms": 5000,   # Commit every 5 seconds
    "max_poll_records": 100,           # Max messages per poll
}
```

### Topic Configuration
```bash
# Increase partitions for parallel processing
kafka-topics.sh --alter --topic question \
  --partitions 10 --bootstrap-server localhost:9092

# Set retention (7 days)
kafka-configs.sh --alter --topic question \
  --add-config retention.ms=604800000 --bootstrap-server localhost:9092
```

## 🎓 Next Steps

1. **Implement Content Service Consumer** to consume from response topic
2. **Add Dead Letter Queue** for failed messages
3. **Implement Idempotency** to handle duplicate requests
4. **Add Metrics** (Prometheus/Grafana) for monitoring
5. **Configure Alerts** for consumer lag and errors
6. **Load Testing** to determine optimal partition count
7. **Add Circuit Breakers** for LLM API failures

## 📚 Documentation

- **API Documentation**: `QUESTION_GENERATION_ENDPOINT.md`
- **Kafka Setup**: Kafka official documentation
- **Event Schemas**: See `app/schema/events.py` and `app/schema/event_data.py`
- **Consumer Implementation**: See `app/consumers/question_generator_consumer.py`

## 🔗 Related Files

- `app/schema/event_data.py` - Event data models
- `app/schema/events.py` - Event wrapper models
- `app/consumers/question_generator_consumer.py` - Consumer implementation
- `app/api/llm.py` - API endpoint
- `app/main.py` - Consumer registration
- `app/config.py` - Configuration
- `QUESTION_GENERATION_ENDPOINT.md` - Detailed API documentation
