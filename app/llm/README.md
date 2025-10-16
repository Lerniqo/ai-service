# LLM Module Documentation

This module provides LangChain-based AI agents for educational AI services including learning path generation, question generation, and conversational chatbot with RAG (Retrieval-Augmented Generation).

## Features

### 1. RAG (Retrieval-Augmented Generation)
- Vector store-based knowledge retrieval using ChromaDB or FAISS
- Document loading from directories or text data
- Semantic search for relevant context
- Support for multiple document types (text, JSON, CSV)

### 2. Learning Path Agent
- Generate personalized learning paths based on goals
- Considers student's current level and preferences
- Provides step-by-step learning roadmap with time estimates
- Uses RAG to incorporate domain knowledge

### 3. Question Generator Agent
- Generate educational questions with multiple types:
  - Multiple choice questions (MCQ)
  - True/False
  - Short answer
  - Essay questions
- Aligned with Bloom's taxonomy levels
- Adjustable difficulty levels
- Includes explanations and correct answers

### 4. Chatbot Agent
- Conversational AI tutor with context awareness
- Session-based conversation memory
- RAG-enhanced responses with source citations
- Follow-up question suggestions
- Multi-session support

## Setup

### 1. Install Dependencies

The required dependencies are already added to `requirements.txt`:

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Add the following to your `.env.development` or `.env.production`:

```env
# Google Gemini API Configuration
GOOGLE_API_KEY=your-google-api-key-here

# LLM Model Settings
LLM_MODEL=gemini-1.5-flash  # or gemini-1.5-pro, gemini-pro
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000

# Embedding Configuration
EMBEDDING_MODEL=models/embedding-001
EMBEDDING_CHUNK_SIZE=1000
EMBEDDING_CHUNK_OVERLAP=200

# Vector Store Configuration
VECTOR_STORE_TYPE=chroma  # or faiss
VECTOR_STORE_PATH=./data/vector_store
VECTOR_STORE_COLLECTION=learning_content

# RAG Configuration
RAG_TOP_K=5
RAG_SCORE_THRESHOLD=0.7
```

### 3. Load Initial Data (RAG)

Run the data loading script to populate the knowledge base:

```bash
python -m app.llm.load_data
```

Or use the API endpoint:

```bash
curl -X POST "http://localhost:8000/api/llm/knowledge-base/load" \
  -H "Content-Type: application/json" \
  -d '{
    "texts": ["Your learning content here..."],
    "metadatas": [{"source": "tutorial", "category": "programming"}]
  }'
```

## API Endpoints

### Knowledge Base Management

#### Load Knowledge Base
```http
POST /api/llm/knowledge-base/load
Content-Type: application/json

{
  "directory_path": "/path/to/documents",  // OR
  "texts": ["text1", "text2"],
  "metadatas": [{"source": "doc1"}, {"source": "doc2"}]
}
```

#### Get Knowledge Base Stats
```http
GET /api/llm/knowledge-base/stats
```

#### Clear Knowledge Base
```http
DELETE /api/llm/knowledge-base/clear
```

### Learning Path Generation

#### Generate Learning Path
```http
POST /api/llm/learning-path/generate
Content-Type: application/json

{
  "goal": "Learn Python web development",
  "current_level": "beginner",
  "preferences": {
    "topics": ["FastAPI", "databases"],
    "learning_style": "hands-on"
  },
  "available_time": "2 hours per day"
}
```

Response:
```json
{
  "goal": "Learn Python web development",
  "difficulty_level": "beginner",
  "total_duration": "8 weeks",
  "steps": [
    {
      "step_number": 1,
      "title": "Python Fundamentals",
      "description": "Learn basic Python syntax...",
      "estimated_duration": "2 weeks",
      "resources": ["Python.org tutorials", "Codecademy"],
      "prerequisites": []
    }
  ]
}
```

### Question Generation

#### Generate Questions
```http
POST /api/llm/questions/generate
Content-Type: application/json

{
  "topic": "Python Data Structures",
  "num_questions": 5,
  "question_types": ["multiple_choice", "short_answer"],
  "difficulty": "medium",
  "bloom_levels": ["understand", "apply"],
  "requirements": "Focus on practical applications"
}
```

Response:
```json
{
  "topic": "Python Data Structures",
  "total_questions": 5,
  "questions": [
    {
      "question_id": 1,
      "question_type": "multiple_choice",
      "question_text": "Which data structure...",
      "options": [
        {"option_id": "A", "text": "List", "is_correct": true},
        {"option_id": "B", "text": "Tuple", "is_correct": false}
      ],
      "correct_answer": "A",
      "explanation": "Lists are mutable...",
      "difficulty": "medium",
      "topic": "Python Data Structures",
      "bloom_level": "understand"
    }
  ]
}
```

### Chatbot

#### Chat
```http
POST /api/llm/chat
Content-Type: application/json

{
  "message": "What are Python decorators?",
  "session_id": "user_123",
  "detailed": false
}
```

Simple Response:
```json
{
  "message": "Python decorators are...",
  "session_id": "user_123"
}
```

Detailed Response (when `detailed: true`):
```json
{
  "session_id": "user_123",
  "message": "Python decorators are...",
  "sources": ["Python Guide", "Advanced Python Tutorial"],
  "confidence": "high",
  "follow_up_suggestions": [
    "Can you show me an example?",
    "What are common use cases?"
  ]
}
```

#### Get Chat History
```http
GET /api/llm/chat/history/{session_id}
```

#### Clear Chat History
```http
DELETE /api/llm/chat/history/{session_id}
```

#### Close Chat Session
```http
DELETE /api/llm/chat/session/{session_id}
```

## Python Usage

### Using the LLM Service Directly

```python
from app.llm.main import get_llm_service

# Get service instance
llm_service = get_llm_service()

# Generate learning path
learning_path = llm_service.generate_learning_path(
    goal="Master machine learning",
    current_level="intermediate",
    preferences={"focus": "practical projects"}
)

# Generate questions
questions = llm_service.generate_questions(
    topic="Neural Networks",
    num_questions=10,
    difficulty="hard"
)

# Chat
response = llm_service.chat(
    message="Explain backpropagation",
    session_id="student_123"
)
```

### Using Individual Agents

```python
from app.llm.agents.learning_path import LearningPathAgent
from app.llm.agents.question_generator import QuestionGeneratorAgent
from app.llm.agents.chatbot import ChatbotAgent

# Learning Path Agent
lp_agent = LearningPathAgent()
path = lp_agent.generate_learning_path(
    goal="Learn FastAPI",
    current_level="beginner"
)

# Question Generator Agent
qg_agent = QuestionGeneratorAgent()
questions = qg_agent.generate_questions(
    topic="REST APIs",
    num_questions=5
)

# Chatbot Agent
chatbot = ChatbotAgent(session_id="session_1")
response = chatbot.chat("What is an API?")
history = chatbot.get_history()
```

## Architecture

```
app/llm/
├── __init__.py              # Module exports
├── main.py                  # Main LLM service orchestrator
├── rag.py                   # RAG implementation
├── load_data.py            # Data loading utilities
├── agents/
│   ├── __init__.py
│   ├── learning_path.py    # Learning path generation agent
│   ├── question_generator.py  # Question generation agent
│   └── chatbot.py          # Conversational agent
```

## Data Flow

1. **RAG Setup**: Documents are loaded → Embedded → Stored in vector database
2. **Query Processing**: User query → Retrieve relevant context → Generate response
3. **Agent Execution**: Request → Get RAG context → LLM processing → Structured output

## Best Practices

1. **Knowledge Base**:
   - Load domain-specific content for better responses
   - Update regularly with new learning materials
   - Use metadata for better organization

2. **Learning Paths**:
   - Provide clear, specific goals
   - Include current skill level for appropriate difficulty
   - Specify time constraints for realistic planning

3. **Question Generation**:
   - Mix question types for comprehensive assessment
   - Align with learning objectives
   - Use appropriate Bloom's taxonomy levels

4. **Chatbot**:
   - Use unique session IDs per student
   - Clear session history when starting new topics
   - Use detailed responses when sources are important

## Troubleshooting

### Import Errors
The lint errors shown are expected until the packages are installed. Run:
```bash
pip install -r requirements.txt
```

### Google Gemini API Errors
- Verify `GOOGLE_API_KEY` is set correctly
- Get your API key from: https://makersuite.google.com/app/apikey
- Check API quota and usage limits
- Ensure model names are valid (e.g., `gemini-1.5-flash`, `gemini-1.5-pro`)

### Vector Store Issues
- Ensure `VECTOR_STORE_PATH` directory is writable
- For ChromaDB, install: `pip install chromadb`
- For FAISS, install: `pip install faiss-cpu`

### Memory Issues
- Reduce `EMBEDDING_CHUNK_SIZE` for large documents
- Limit `RAG_TOP_K` for faster retrieval
- Use `FAISS` for larger datasets (more memory efficient)

## Future Enhancements

- [ ] Support for multiple LLM providers (OpenAI, Anthropic, Azure)
- [ ] Advanced RAG techniques (HyDE, Self-RAG)
- [ ] Caching for faster responses
- [ ] Evaluation metrics for generated content
- [ ] Multi-language support
- [ ] Integration with learning analytics

## License

This module is part of the AI Service project.
