# DateTime JSON Serialization Fix

## Date: October 16, 2025

## Issue
AI service was throwing the error:
```
"error": "Object of type datetime is not JSON serializable"
```

This occurred when publishing Kafka messages because Pydantic's `.dict()` method doesn't automatically serialize `datetime` objects to JSON-compatible strings.

## Root Cause

The `EventDataBase` class in `app/schema/event_data.py` includes `created_at` and `updated_at` fields of type `datetime`. When using Pydantic v2's `.dict()` method, datetime objects remain as Python datetime instances, which cannot be serialized to JSON by the standard `json` library.

## Solution

Replaced all instances of `.dict()` with `.model_dump(mode='json')` when publishing to Kafka. The `mode='json'` parameter ensures that all non-JSON-serializable types (like datetime) are automatically converted to JSON-compatible formats (ISO 8601 strings for datetime).

## Changes Made

### 1. Learning Path Request Consumer
**File:** `app/consumers/learning_path_request_consumer.py`

- Line 151: Changed `learning_path.dict()` to `learning_path.model_dump(mode='json')`
- Line 168: Changed `response_event.dict(by_alias=True)` to `response_event.model_dump(mode='json', by_alias=True)`
- Line 237: Changed `response_event.dict(by_alias=True)` to `response_event.model_dump(mode='json', by_alias=True)` (error response)

### 2. Question Generator Consumer
**File:** `app/consumers/question_generator_consumer.py`

- Line 150: Changed `[q.dict() for q in question_set.questions]` to `[q.model_dump(mode='json') for q in question_set.questions]`
- Line 169: Changed `response_event.dict(by_alias=True)` to `response_event.model_dump(mode='json', by_alias=True)`
- Line 227: Changed `response_event.dict(by_alias=True)` to `response_event.model_dump(mode='json', by_alias=True)` (error response)

### 3. LLM API Endpoints
**File:** `app/api/llm.py`

- Line 206: Changed `request_event.dict(by_alias=True)` to `request_event.model_dump(mode='json', by_alias=True)` (learning path endpoint)
- Line 387: Changed `request_event.dict(by_alias=True)` to `request_event.model_dump(mode='json', by_alias=True)` (question generation endpoint)

## Pydantic v2 Migration Notes

### `.dict()` vs `.model_dump()`
- **Pydantic v1**: Used `.dict()`
- **Pydantic v2**: Uses `.model_dump()` (`.dict()` is deprecated but still works)

### `mode='json'` Parameter
When `mode='json'` is specified:
- `datetime` objects are serialized to ISO 8601 strings
- `Decimal` objects are converted to floats
- `UUID` objects are converted to strings
- Other non-JSON types are properly handled

### Example Transformation
**Before:**
```python
response_event.dict(by_alias=True)
# Results in: {'created_at': datetime.datetime(2025, 10, 16, ...)}
```

**After:**
```python
response_event.model_dump(mode='json', by_alias=True)
# Results in: {'created_at': '2025-10-16T10:30:00Z'}
```

## Testing Recommendations

1. **Test Learning Path Generation**
   - Request a learning path via API
   - Verify message is published to Kafka without errors
   - Verify response is received and processed correctly

2. **Test Question Generation**
   - Request question generation via API
   - Verify message is published to Kafka without errors
   - Verify response is received with properly serialized datetime fields

3. **Test Error Scenarios**
   - Trigger an error in learning path generation
   - Verify error response is published correctly
   - Check that datetime fields in error responses are serialized

4. **Verify Kafka Messages**
   - Inspect messages in Kafka topics
   - Confirm datetime fields are ISO 8601 strings
   - Verify all fields maintain proper structure

## Impact

✅ **Fixed Issues:**
- Eliminated "Object of type datetime is not JSON serializable" errors
- Proper datetime serialization in all Kafka messages
- Consistent JSON format across all events

✅ **No Breaking Changes:**
- Internal change only (no API changes)
- Content service receives properly formatted JSON
- All existing functionality preserved

## Files Modified

1. `app/consumers/learning_path_request_consumer.py`
2. `app/consumers/question_generator_consumer.py`
3. `app/api/llm.py`

## Notes

- The `app/schema/event_data.py` file was not modified as the datetime fields are correct
- The `model_dump(mode='json')` approach is the recommended Pydantic v2 way to serialize models for JSON
- This fix applies to all Kafka message publishing, ensuring consistent serialization
- The `by_alias=True` parameter ensures field names use their alias (e.g., `eventId` instead of `event_id`)
