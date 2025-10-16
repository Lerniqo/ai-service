# LLM Module Quick Start Guide

This guide will help you get started with the LLM module in the AI Service using Google Gemini.

## Prerequisites

- Python 3.9+
- Google Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))
- All dependencies installed

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 2: Configure Environment

1. Copy the example environment file:
```bash
cp .env.llm.example .env.development
```

2. Edit `.env.development` and add your Google API key:
```env
GOOGLE_API_KEY=your-actual-google-api-key-here
```

## Step 3: Load Initial Knowledge Base

Run the data loading script to populate the RAG system:

```bash
python -m app.llm.load_data
```

This will load sample educational content about Python, web development, and machine learning.

## Step 4: Start the Service

```bash
python run.py
```

Or using uvicorn directly:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Step 5: Test the Endpoints

### 1. Generate a Learning Path

```bash
curl -X POST "http://localhost:8000/api/llm/learning-path/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "goal": "Learn FastAPI web development",
    "current_level": "beginner",
    "available_time": "2 hours per day"
  }'
```

### 2. Generate Questions

```bash
curl -X POST "http://localhost:8000/api/llm/questions/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Python Data Structures",
    "num_questions": 5,
    "difficulty": "medium"
  }'
```

### 3. Chat with the AI Tutor

```bash
curl -X POST "http://localhost:8000/api/llm/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are Python decorators?",
    "session_id": "student_123",
    "detailed": true
  }'
```

### 4. Check Knowledge Base Stats

```bash
curl -X GET "http://localhost:8000/api/llm/knowledge-base/stats"
```

## Step 6: View API Documentation

Open your browser and visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Using Python Code

### Example 1: Generate Learning Path

```python
from app.llm.main import get_llm_service

llm_service = get_llm_service()

learning_path = llm_service.generate_learning_path(
    goal="Master Python async programming",
    current_level="intermediate",
    preferences={
        "focus": "practical examples",
        "topics": ["asyncio", "concurrent programming"]
    },
    available_time="1 hour per day"
)

print(f"Goal: {learning_path.goal}")
print(f"Total Duration: {learning_path.total_duration}")

for step in learning_path.steps:
    print(f"\nStep {step.step_number}: {step.title}")
    print(f"Duration: {step.estimated_duration}")
    print(f"Description: {step.description}")
```

### Example 2: Generate Questions

```python
from app.llm.main import get_llm_service

llm_service = get_llm_service()

questions = llm_service.generate_questions(
    topic="REST API Design",
    num_questions=10,
    question_types=["multiple_choice", "short_answer"],
    difficulty="medium",
    bloom_levels=["understand", "apply", "analyze"]
)

for q in questions.questions:
    print(f"\nQ{q.question_id}: {q.question_text}")
    print(f"Type: {q.question_type}")
    print(f"Difficulty: {q.difficulty}")
    
    if q.options:
        for opt in q.options:
            marker = "✓" if opt.is_correct else " "
            print(f"  [{marker}] {opt.option_id}. {opt.text}")
    
    print(f"Explanation: {q.explanation}")
```

### Example 3: Chatbot Conversation

```python
from app.llm.main import get_llm_service

llm_service = get_llm_service()
session_id = "student_001"

# First message
response1 = llm_service.chat(
    message="What is the difference between a list and a tuple in Python?",
    session_id=session_id
)
print(f"AI: {response1}")

# Follow-up question (uses conversation context)
response2 = llm_service.chat(
    message="Can you give me an example?",
    session_id=session_id
)
print(f"AI: {response2}")

# Get conversation history
history = llm_service.get_chat_history(session_id)
for msg in history:
    print(f"{msg['role']}: {msg['content']}")

# Clear when done
llm_service.clear_chat_history(session_id)
```

### Example 4: Load Custom Knowledge Base

```python
from app.llm.main import get_llm_service

llm_service = get_llm_service()

# Load from directory
result = llm_service.load_knowledge_base(
    directory_path="./data/course_materials"
)
print(f"Loaded {result['chunks_added']} chunks")

# Or load from text
texts = [
    "FastAPI is a modern web framework for Python...",
    "Pydantic provides data validation using Python type hints...",
    "Async/await syntax in Python allows for concurrent execution..."
]

metadatas = [
    {"source": "FastAPI Guide", "topic": "web"},
    {"source": "Pydantic Docs", "topic": "validation"},
    {"source": "Async Tutorial", "topic": "concurrency"}
]

result = llm_service.load_knowledge_base(
    texts=texts,
    metadatas=metadatas
)
print(f"Loaded {result['chunks_added']} chunks")
```

## Troubleshooting

### Issue: Import errors
**Solution**: Ensure all dependencies are installed:
```bash
pip install -r requirements.txt
```

### Issue: Google Gemini API errors
**Solution**: 
- Check your API key is correct at: https://makersuite.google.com/app/apikey
- Verify you have API access enabled
- Confirm the model name is valid (e.g., `gemini-1.5-flash`, `gemini-1.5-pro`)
- Check your API quota limits

### Issue: Vector store not persisting
**Solution**: 
- Check `VECTOR_STORE_PATH` is writable
- Ensure the directory exists or can be created
- For ChromaDB, verify it's installed: `pip install chromadb`

### Issue: Out of memory errors
**Solution**:
- Reduce `EMBEDDING_CHUNK_SIZE` in config
- Limit `RAG_TOP_K` to fewer documents
- Consider using FAISS instead of ChromaDB for larger datasets

## Next Steps

1. **Customize the Knowledge Base**: Add your own educational content
2. **Tune Parameters**: Adjust temperature, chunk size, etc. for your use case
3. **Integrate with Frontend**: Use the API endpoints in your web/mobile app
4. **Monitor Usage**: Track Google Gemini API usage and quotas
5. **Extend Agents**: Add custom agents for specific educational tasks

## Useful Resources

- [LangChain Documentation](https://python.langchain.com/)
- [Google Gemini API Documentation](https://ai.google.dev/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [ChromaDB Documentation](https://docs.trychroma.com/)
4. **Monitor Usage**: Track OpenAI API costs and usage
5. **Extend Agents**: Add custom agents for specific educational tasks

## Useful Resources

- [LangChain Documentation](https://python.langchain.com/)
- [Google Gemini API Documentation](https://ai.google.dev/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [ChromaDB Documentation](https://docs.trychroma.com/)

## Support

For issues or questions:
1. Check the main README: `app/llm/README.md`
2. Review the test file: `tests/test_llm.py`
3. Check logs for detailed error messages
4. Refer to LangChain and Google Gemini documentation for specific issues

Happy coding! 🚀
