# Question Generation with Kafka Integration

## Overview

This system allows the Content Service to request question generation from the AI Service using **Kafka** for asynchronous, scalable message-based communication. The AI Service generates questions using an LLM and publishes the results back to Kafka for the Content Service to consume.

## Architecture

```
Content Service → API Endpoint → Kafka Topic (Request)
                                      ↓
                                Question Generator Consumer
                                      ↓
                                  LLM Service
                                      ↓
                                Kafka Topic (Response)
                                      ↓
                                Content Service Consumer
```

## Kafka Topics

- **Request Topic**: `question.request` (configurable via `KAFKA_QUESTION_REQUEST_TOPIC`)
- **Response Topic**: `question.response` (configurable via `KAFKA_QUESTION_RESPONSE_TOPIC`)

## Flow

1. **Content Service** sends HTTP POST request to AI Service endpoint
2. **AI Service** validates request and publishes to Kafka request topic
3. **AI Service** returns immediate acknowledgment (HTTP 200)
4. **Question Generator Consumer** picks up message from Kafka
5. **LLM generates** questions asynchronously
6. **AI Service** publishes response to Kafka response topic
7. **Content Service** consumes response from Kafka

## Benefits of Kafka Integration

✅ **Scalability**: Multiple consumers can process requests in parallel  
✅ **Reliability**: Messages are persisted and can be replayed  
✅ **Decoupling**: Services communicate asynchronously  
✅ **Fault Tolerance**: If AI Service is down, requests are queued  
✅ **Load Balancing**: Kafka handles distribution across consumers  
✅ **Monitoring**: Easy to track message flow and processing status

## API Endpoint

**POST** `/llm/questions/generate-for-content-service`

### Purpose
Entry point for Content Service to submit question generation requests. The endpoint validates the request and publishes it to Kafka.

## Request Schema (HTTP)

```json
{
  "request_id": "unique-request-id-123",
  "topic": "Introduction to Python Programming",
  "num_questions": 10,
  "question_types": ["multiple_choice", "true_false"],
  "difficulty": "medium",
  "content_id": "content-456",
  "user_id": "user-789",
  "metadata": {
    "course_id": "python-101",
    "module": "basics"
  }
}
```

### Request Fields

- `request_id` (required): Unique identifier for tracking this request
- `topic` (required): The topic to generate questions about
- `num_questions` (optional, default=5): Number of questions to generate (1-50)
- `question_types` (optional): List of question types. Options:
  - `"multiple_choice"`
  - `"true_false"`
  - `"short_answer"`
  - `"essay"`
- `difficulty` (optional, default="medium"): Difficulty level (`"easy"`, `"medium"`, `"hard"`)
- `content_id` (optional): ID of the content this relates to
- `user_id` (optional): User ID if personalized questions are needed
- `metadata` (optional): Additional metadata to pass through

## Response Schema (HTTP - Immediate)

```json
{
  "status": "accepted",
  "request_id": "unique-request-id-123",
  "message": "Question generation request accepted and queued. Generating 10 questions for topic: Introduction to Python Programming"
}
```

## Kafka Event Schemas

### Request Event (Published to Kafka)

**Topic**: `question.request`  
**Event Type**: `question.generation.request`

```json
{
  "eventId": "evt_qgen_request_123",
  "eventType": "question.generation.request",
  "eventData": {
    "created_at": "2025-10-15T10:00:00Z",
    "updated_at": "2025-10-15T10:00:00Z",
    "request_id": "req-123",
    "topic": "Python Loops",
    "num_questions": 5,
    "question_types": ["multiple_choice"],
    "difficulty": "medium",
    "content_id": "content-456",
    "user_id": "user-789",
    "metadata": {
      "course_id": "python-101"
    }
  },
  "userId": "content-service",
  "metadata": {
    "source": "content-service",
    "request_id": "req-123"
  }
}
```

### Response Event (Published to Kafka)

**Topic**: `question.response`  
**Event Type**: `question.generation.response`

#### Success Response

```json
{
  "eventId": "evt_qgen_response_123",
  "eventType": "question.generation.response",
  "eventData": {
    "created_at": "2025-10-15T10:05:00Z",
    "updated_at": "2025-10-15T10:05:00Z",
    "request_id": "req-123",
    "status": "completed",
    "topic": "Python Loops",
    "total_questions": 5,
    "questions": [
      {
        "question_id": 1,
        "question_type": "multiple_choice",
        "question_text": "What keyword is used to start a for loop in Python?",
        "options": [
          {"option_id": "A", "text": "for", "is_correct": true},
          {"option_id": "B", "text": "loop", "is_correct": false},
          {"option_id": "C", "text": "while", "is_correct": false},
          {"option_id": "D", "text": "iterate", "is_correct": false}
        ],
        "correct_answer": "for",
        "explanation": "Python uses the 'for' keyword to start a for loop.",
        "difficulty": "easy",
        "concepts": ["loops", "syntax", "keywords"]
      }
      // ... more questions
    ],
    "content_id": "content-456",
    "user_id": "user-789",
    "metadata": {
      "course_id": "python-101"
    }
  },
  "userId": "ai-service",
  "metadata": {
    "source": "ai-service",
    "request_id": "req-123"
  }
}
```

#### Error Response

```json
{
  "eventId": "evt_qgen_response_456",
  "eventType": "question.generation.response",
  "eventData": {
    "created_at": "2025-10-15T10:05:00Z",
    "updated_at": "2025-10-15T10:05:00Z",
    "request_id": "req-123",
    "status": "failed",
    "error": "LLM service unavailable",
    "metadata": {
      "course_id": "python-101"
    }
  },
  "userId": "ai-service",
  "metadata": {
    "source": "ai-service",
    "request_id": "req-123",
    "error": true
  }
}
```

## Environment Configuration

### AI Service Configuration

```bash
# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_CLIENT_ID=ai-service
KAFKA_QUESTION_REQUEST_TOPIC=question.request
KAFKA_QUESTION_RESPONSE_TOPIC=question.response

# LLM Configuration
GOOGLE_API_KEY=your-google-api-key
LLM_MODEL=gemini-1.5-flash
```

### Content Service Configuration

The Content Service needs to:
1. Produce messages to `question.generation.request` topic
2. Consume messages from `question.generation.response` topic
3. Handle both `completed` and `failed` status responses

## Example Usage

### From Content Service (Python with Kafka)

```python
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
import json
import httpx

# Option 1: Via HTTP Endpoint (Recommended)
async def request_questions_via_http():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://ai-service:8000/llm/questions/generate-for-content-service",
            json={
                "request_id": "req-123",
                "topic": "Python Loops",
                "num_questions": 5,
                "question_types": ["multiple_choice"],
                "difficulty": "medium",
                "content_id": "content-789"
            }
        )
        return response.json()
    # Response: {"status": "accepted", "request_id": "req-123", ...}

# Option 2: Direct Kafka Publish (Advanced)
async def request_questions_via_kafka():
    producer = AIOKafkaProducer(
        bootstrap_servers='localhost:9092',
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    await producer.start()
    
    request_event = {
        "eventId": "evt_req_123",
        "eventType": "question.generation.request",
        "eventData": {
            "request_id": "req-123",
            "topic": "Python Loops",
            "num_questions": 5,
            "question_types": ["multiple_choice"],
            "difficulty": "medium"
        },
        "userId": "content-service"
    }
    
    await producer.send(
        "question.request",
        value=request_event,
        key=b"req-123"
    )
    await producer.stop()

# Consume responses from Kafka
async def consume_question_responses():
    consumer = AIOKafkaConsumer(
        "question.response",
        bootstrap_servers='localhost:9092',
        group_id='content-service-consumer',
        value_deserializer=lambda m: json.loads(m.decode('utf-8'))
    )
    await consumer.start()
    
    try:
        async for message in consumer:
            event = message.value
            request_id = event['eventData']['request_id']
            status = event['eventData']['status']
            
            if status == 'completed':
                questions = event['eventData']['questions']
                print(f"Received {len(questions)} questions for {request_id}")
                # Process questions...
            elif status == 'failed':
                error = event['eventData']['error']
                print(f"Question generation failed for {request_id}: {error}")
                
    finally:
        await consumer.stop()
```

### Using curl (HTTP Endpoint)

```bash
curl -X POST "http://localhost:8000/llm/questions/generate-for-content-service" \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "req-123",
    "topic": "Python Loops",
    "num_questions": 5,
    "question_types": ["multiple_choice"],
    "difficulty": "medium"
  }'
```

## Question Schema Details

Each generated question has the following structure:

- `question_id`: Unique identifier within the set
- `question_type`: Type of question (multiple_choice, true_false, short_answer, essay)
- `question_text`: The actual question text
- `options`: List of answer options (for MCQ/true-false, null for others)
  - `option_id`: Identifier (A, B, C, D, etc.)
  - `text`: Option text
  - `is_correct`: Boolean indicating if this is the correct answer
- `correct_answer`: The correct answer or key points
- `explanation`: Detailed explanation of the correct answer
- `difficulty`: Difficulty level of this specific question
- `concepts`: List of concepts being tested

## Error Handling

### HTTP Endpoint Errors

- **400 Bad Request**: Invalid request parameters (validation failed)
- **500 Internal Server Error**: Error publishing to Kafka or internal error

### Kafka Message Errors

If question generation fails during processing:
- Status `"failed"` is published to response topic
- Error message included in `error` field
- Original metadata preserved for correlation

### Retries and Dead Letter Queue

Configure Kafka consumer with retry logic:
- Failed messages can be retried automatically
- Configure max retries and backoff
- Use dead letter topic for permanently failed messages

## Monitoring and Logging

### Logs to Monitor

**AI Service logs:**
- Request received and validated
- Message published to Kafka request topic
- Consumer picked up request
- Question generation started/completed
- Response published to Kafka

**Key log fields:**
- `request_id`: Correlate requests and responses
- `topic`: Question topic
- `num_questions`: Number requested
- `status`: Processing status
- `kafka_topic`: Which Kafka topic was used

### Metrics to Track

- Request acceptance rate
- Question generation latency
- Kafka publish/consume rates
- Error rates by type
- Consumer lag (messages waiting to be processed)

## Advanced Features

### Consumer Scaling

Run multiple instances of the AI Service:
- Kafka consumer group ensures each message is processed once
- Load is automatically distributed
- Horizontal scaling for high throughput

### Message Ordering

- Messages with same `request_id` key go to same partition
- Ensures ordered processing if needed
- Configure partition count for parallelism

### Idempotency

- Use `request_id` to prevent duplicate processing
- Check if request already processed before starting
- Cache recent responses for quick replies

## Troubleshooting

### Request Not Being Processed

1. Check Kafka is running: `kafka-topics.sh --list --bootstrap-server localhost:9092`
2. Verify topic exists: Should see `question.generation.request` and `question.generation.response`
3. Check consumer is running: Look for subscription logs in AI Service
4. Monitor consumer lag: `kafka-consumer-groups.sh --describe --group ai-service-question-generator-consumer`

### No Response Received

1. Check Content Service is consuming from response topic
2. Verify `request_id` matches between request and response
3. Check for errors in AI Service logs
4. Look for messages in response topic: `kafka-console-consumer.sh --topic question.generation.response`

### Performance Issues

1. Increase number of partitions for parallel processing
2. Run multiple AI Service instances
3. Adjust consumer batch size and fetch settings
4. Monitor LLM API rate limits and quotas
