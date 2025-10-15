"""
LLM API Endpoints

FastAPI endpoints for LLM services including learning path generation,
question generation, and chatbot functionality.
"""

import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Body, Query
from pydantic import BaseModel, Field

from app.llm.main import get_llm_service
from app.llm.agents.learning_path import LearningPath
from app.llm.agents.question_generator import QuestionSet
from app.llm.agents.chatbot import ChatbotResponse
from app.clients.kafka_client import get_kafka_client
from app.schema.events import QuestionGenerationRequestEvent
from app.schema.event_data import QuestionGenerationRequestData
from app.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/llm", tags=["LLM Services"])


# Request/Response Models

class LoadKnowledgeBaseRequest(BaseModel):
    """Request to load data into knowledge base."""
    directory_path: Optional[str] = Field(None, description="Path to directory with documents")
    texts: Optional[List[str]] = Field(None, description="List of text strings to load")
    metadatas: Optional[List[Dict[str, Any]]] = Field(None, description="Metadata for texts")


class LearningPathRequest(BaseModel):
    """Request to generate a learning path."""
    user_id: str = Field(..., description="User ID")
    goal: str = Field(..., description="Learning goal or objective")
    current_level: str = Field(default="beginner", description="Current knowledge level")
    preferences: Optional[Dict[str, Any]] = Field(None, description="Learning preferences")
    available_time: str = Field(default="flexible", description="Available time for learning")


class QuestionGenerationRequest(BaseModel):
    """Request to generate questions."""
    topic: str = Field(..., description="Topic to generate questions about")
    num_questions: int = Field(default=5, ge=1, le=20, description="Number of questions")
    question_types: Optional[List[str]] = Field(
        default=None,
        description="Question types (multiple_choice, true_false, short_answer, essay)"
    )
    difficulty: str = Field(default="medium", description="Difficulty level (easy, medium, hard)")


class ContentServiceQuestionRequest(BaseModel):
    """Request from content service to generate questions."""
    request_id: str = Field(..., description="Unique identifier for this request")
    topic: str = Field(..., description="Topic to generate questions about")
    num_questions: int = Field(default=5, ge=1, le=50, description="Number of questions")
    question_types: Optional[List[str]] = Field(
        default=None,
        description="Question types (multiple_choice, true_false, short_answer, essay)"
    )
    difficulty: str = Field(default="medium", description="Difficulty level (easy, medium, hard)")
    content_id: Optional[str] = Field(None, description="ID of the content this relates to")
    user_id: Optional[str] = Field(None, description="User ID if personalized questions")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class ContentServiceQuestionResponse(BaseModel):
    """Response for content service question generation."""
    status: str = Field(..., description="Status of the request (accepted, processing, completed, failed)")
    request_id: str = Field(..., description="The request identifier")
    message: str = Field(..., description="Status message")


class ChatRequest(BaseModel):
    """Request to chat with the bot."""
    message: str = Field(..., description="User's message")
    session_id: str = Field(default="default", description="Session identifier")
    detailed: bool = Field(default=False, description="Return detailed response with metadata")


class ChatResponse(BaseModel):
    """Simple chat response."""
    message: str = Field(..., description="Chatbot's response")
    session_id: str = Field(..., description="Session identifier")


# Knowledge Base Endpoints

@router.post("/knowledge-base/load")
async def load_knowledge_base(request: LoadKnowledgeBaseRequest):
    """
    Load data into the RAG knowledge base.
    
    Provide either directory_path or texts (not both).
    """
    try:
        llm_service = get_llm_service()
        result = llm_service.load_knowledge_base(
            directory_path=request.directory_path,
            texts=request.texts,
            metadatas=request.metadatas
        )
        return result
    except Exception as e:
        logger.error(f"Error loading knowledge base: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge-base/stats")
async def get_knowledge_base_stats():
    """Get statistics about the knowledge base."""
    try:
        llm_service = get_llm_service()
        return llm_service.get_knowledge_base_stats()
    except Exception as e:
        logger.error(f"Error getting knowledge base stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/knowledge-base/clear")
async def clear_knowledge_base():
    """Clear all data from the knowledge base."""
    try:
        llm_service = get_llm_service()
        return llm_service.clear_knowledge_base()
    except Exception as e:
        logger.error(f"Error clearing knowledge base: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Learning Path Endpoints

@router.post("/learning-path/generate", response_model=LearningPath)
async def generate_learning_path(request: LearningPathRequest):
    """
    Generate a personalized learning path based on goals and preferences.
    """
    try:
        llm_service = get_llm_service()
        learning_path = await llm_service.agenerate_learning_path(
            user_id=request.user_id,
            goal=request.goal,
            current_level=request.current_level,
            preferences=request.preferences,
            available_time=request.available_time
        )
        return learning_path
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating learning path: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Question Generation Endpoints

@router.post("/questions/generate", response_model=QuestionSet)
async def generate_questions(request: QuestionGenerationRequest):
    """
    Generate educational questions for a topic.
    """
    try:
        llm_service = get_llm_service()
        question_set = await llm_service.agenerate_questions(
            topic=request.topic,
            num_questions=request.num_questions,
            question_types=request.question_types,
            difficulty=request.difficulty
        )
        return question_set
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating questions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Chatbot Endpoints

@router.post("/chat")
async def chat(request: ChatRequest):
    """
    Chat with the AI assistant.
    
    Set detailed=true to get response with sources and metadata.
    """
    try:
        llm_service = get_llm_service()
        
        if request.detailed:
            response = llm_service.chat_with_details(
                message=request.message,
                session_id=request.session_id
            )
            return {
                "session_id": request.session_id,
                **response.dict()
            }
        else:
            message = await llm_service.achat(
                message=request.message,
                session_id=request.session_id
            )
            return ChatResponse(
                message=message,
                session_id=request.session_id
            )
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat/history/{session_id}")
async def get_chat_history(session_id: str):
    """Get conversation history for a session."""
    try:
        llm_service = get_llm_service()
        history = llm_service.get_chat_history(session_id)
        return {
            "session_id": session_id,
            "history": history
        }
    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/chat/history/{session_id}")
async def clear_chat_history(session_id: str):
    """Clear conversation history for a session."""
    try:
        llm_service = get_llm_service()
        llm_service.clear_chat_history(session_id)
        return {
            "status": "success",
            "message": f"Chat history cleared for session: {session_id}"
        }
    except Exception as e:
        logger.error(f"Error clearing chat history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/chat/session/{session_id}")
async def close_chat_session(session_id: str):
    """Close and remove a chat session."""
    try:
        llm_service = get_llm_service()
        llm_service.close_chat_session(session_id)
        return {
            "status": "success",
            "message": f"Chat session closed: {session_id}"
        }
    except Exception as e:
        logger.error(f"Error closing chat session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Content Service Integration Endpoints (Kafka-based)

@router.post("/questions/generate", response_model=ContentServiceQuestionResponse)
async def generate_questions_for_content_service(
    request: ContentServiceQuestionRequest
):
    """
    Generate questions based on request from content service using Kafka.
    
    This endpoint receives a request from the content service, publishes it to Kafka,
    and immediately returns an acknowledgment. The question generation happens
    asynchronously via Kafka consumer, and results are published to the response topic.
    
    Flow:
    1. Content service sends request to this endpoint
    2. This endpoint validates and publishes request to Kafka
    3. Returns immediate acknowledgment
    4. Question generator consumer picks up the request
    5. Generates questions and publishes response to Kafka
    6. Content service consumes the response from Kafka
    """
    try:
        logger.info(f"Received question generation request {request.request_id} from content service")
        
        settings = get_settings()
        kafka_client = get_kafka_client()
        
        # Create request event
        request_data = QuestionGenerationRequestData(
            request_id=request.request_id,
            topic=request.topic,
            num_questions=request.num_questions,
            question_types=request.question_types,
            difficulty=request.difficulty,
            content_id=request.content_id,
            user_id=request.user_id,
            metadata=request.metadata
        )
        
        request_event = QuestionGenerationRequestEvent(
            event_type="question.generation.request",
            event_data=request_data,
            user_id=request.user_id or "content-service",
            metadata={
                "source": "content-service",
                "request_id": request.request_id
            }
        )
        
        # Publish request to Kafka
        await kafka_client.publish(
            topic=settings.KAFKA_QUESTION_REQUEST_TOPIC,
            message=request_event.dict(by_alias=True),
            key=request.request_id
        )
        
        logger.info(
            f"Question generation request {request.request_id} published to Kafka topic: {settings.KAFKA_QUESTION_REQUEST_TOPIC}"
        )
        
        return ContentServiceQuestionResponse(
            status="accepted",
            request_id=request.request_id,
            message=f"Question generation request accepted and queued. Generating {request.num_questions} questions for topic: {request.topic}"
        )
        
    except ValueError as e:
        logger.error(f"Validation error for request {request.request_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error accepting question generation request {request.request_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
