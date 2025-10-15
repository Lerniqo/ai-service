# Fix for Pydantic ChatGoogleGenerativeAI Model Definition Error - Production

## Problem

Multiple production errors occurring with the same root cause:

```
Error processing learning goal: `ChatGoogleGenerativeAI` is not fully defined; 
you should define `BaseCache`, then call `ChatGoogleGenerativeAI.model_rebuild()`.
```

This error was occurring in:
- Learning goal processing
- Question generation 
- Chatbot interactions

## Root Cause

The issue is a **Pydantic v2 model initialization problem** with LangChain's `ChatGoogleGenerativeAI`. The class has forward references to `BaseCache` that must be resolved before the class can be instantiated. In production:

1. **Race Condition**: Kafka consumers start immediately after FastAPI startup
2. **Lazy Loading**: Agent classes lazily import `ChatGoogleGenerativeAI` when first needed
3. **Missing Dependencies**: `BaseCache` wasn't imported before `ChatGoogleGenerativeAI`
4. **Incomplete Model**: Pydantic model wasn't rebuilt to resolve forward references

## Solution

Implemented a **multi-layered defense strategy**:

### 1. Pre-Initialization at Startup (Primary Fix)

Created `app/llm/init.py` module that:
- Imports `BaseCache` first
- Imports `ChatGoogleGenerativeAI`
- Calls `model_rebuild()` before any agents are created
- Provides logging for debugging

**File: `app/llm/init.py`**

```python
def initialize_langchain_models():
    """
    Pre-initialize LangChain models to resolve Pydantic forward references.
    Called during application startup to ensure models are ready before consumers start.
    """
    # Import BaseCache first
    from langchain_core.caches import BaseCache
    
    # Import ChatGoogleGenerativeAI
    from langchain_google_genai import ChatGoogleGenerativeAI
    
    # Rebuild Pydantic model
    ChatGoogleGenerativeAI.model_rebuild()
```

**File: `app/main.py`**

Modified startup event to call initialization:

```python
@app.on_event("startup")
async def startup_event():
    # Pre-initialize LangChain models BEFORE starting Kafka consumers
    logger.info("Pre-initializing LangChain models...")
    langchain_init_success = initialize_langchain_models()
    
    # Then start Kafka consumers...
```

### 2. Enhanced Agent Initialization (Defense in Depth)

Updated all three agent files to:
- Import `BaseCache` with fallbacks for different LangChain versions
- Call `model_rebuild()` **before** assigning to globals
- Add comprehensive error logging
- Include retry logic with `BaseModel.model_rebuild()`

**Files Updated:**
- `app/llm/agents/learning_path.py`
- `app/llm/agents/question_generator.py`
- `app/llm/agents/chatbot.py`

**Changes in each agent's `_ensure_langchain_loaded()` function:**

```python
def _ensure_langchain_loaded():
    global ChatGoogleGenerativeAI, ...
    if ChatGoogleGenerativeAI is None:
        # Import BaseCache first with fallback
        try:
            from langchain_core.caches import BaseCache
        except ImportError:
            from langchain.cache import BaseCache
        
        # Import ChatGoogleGenerativeAI
        from langchain_google_genai import ChatGoogleGenerativeAI as _ChatGoogleGenerativeAI
        
        # Rebuild BEFORE assigning to globals
        try:
            _ChatGoogleGenerativeAI.model_rebuild()
            logger.info("model_rebuild() completed successfully")
        except Exception as e:
            logger.error(f"Failed to rebuild: {e}")
            # Retry with BaseModel rebuild
            from pydantic import BaseModel
            BaseModel.model_rebuild()
            _ChatGoogleGenerativeAI.model_rebuild()
        
        globals()['ChatGoogleGenerativeAI'] = _ChatGoogleGenerativeAI
```

### 3. Existing Lazy Initialization (Already in Place)

The `LearningGoalConsumer` already uses lazy initialization:

```python
class LearningGoalConsumer:
    def __init__(self):
        self._learning_path_agent: Optional[LearningPathAgent] = None
    
    @property
    def learning_path_agent(self) -> LearningPathAgent:
        if self._learning_path_agent is None:
            self._learning_path_agent = LearningPathAgent()
        return self._learning_path_agent
```

## Benefits of This Approach

1. **Startup Pre-initialization**: Models are built once at startup, not on first use
2. **Better Logging**: Can see exactly where initialization succeeds or fails
3. **Fail-Fast**: If initialization fails at startup, it's logged immediately
4. **Defense in Depth**: Even if startup initialization fails, agents have their own fallback
5. **Production Ready**: Works with different LangChain versions (fallback imports)
6. **No Breaking Changes**: Existing lazy initialization patterns preserved

## Verification

After deploying this fix, check logs for:

```
✅ "Pre-initializing LangChain models..."
✅ "✓ BaseCache imported from langchain_core.caches"
✅ "✓ ChatGoogleGenerativeAI imported"
✅ "✓ ChatGoogleGenerativeAI.model_rebuild() completed successfully"
✅ "🎉 LangChain models pre-initialization completed successfully"
```

If you see these messages, the models are properly initialized before any consumers start.

## Testing

1. **Local Testing**: Start the service and check startup logs
2. **Integration Test**: Send a learning goal event and verify no Pydantic errors
3. **Production Deploy**: Monitor logs for successful initialization messages
4. **Error Monitoring**: Confirm no more "not fully defined" errors

## Files Changed

1. **New File**: `app/llm/init.py` - Pre-initialization module
2. **Modified**: `app/main.py` - Added startup initialization call
3. **Modified**: `app/llm/agents/learning_path.py` - Enhanced error handling
4. **Modified**: `app/llm/agents/question_generator.py` - Enhanced error handling
5. **Modified**: `app/llm/agents/chatbot.py` - Enhanced error handling

## Rollback Plan

If this fix causes issues:

1. Remove the `initialize_langchain_models()` call from `app/main.py`
2. Revert to previous versions of the three agent files
3. The lazy initialization in consumers will still work (though may have the original issue)

## Additional Notes

- This fix addresses a known issue with Pydantic v2 and LangChain
- The issue is more prevalent in production due to different import timing
- Pre-initialization ensures consistent behavior across environments
- The fix is compatible with existing code patterns (no breaking changes)
