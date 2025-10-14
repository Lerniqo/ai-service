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
    bloom_levels: Optional[List[str]] = Field(
        default=None,
        description="Bloom's taxonomy levels"
    )
    requirements: Optional[str] = Field(None, description="Additional requirements")


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
            difficulty=request.difficulty,
            bloom_levels=request.bloom_levels,
            requirements=request.requirements
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
