"""
LLM Service Main Module

This module provides the main interface for LLM-powered AI services including:
- Learning path generation
- Question generation
- Conversational chatbot with RAG
"""

import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

from app.config import get_settings
from app.llm.rag import get_rag_service, RAGService
from app.llm.agents.learning_path import LearningPathAgent, LearningPath
from app.llm.agents.question_generator import QuestionGeneratorAgent, QuestionSet
from app.llm.agents.chatbot import ChatbotAgent, ChatbotResponse

logger = logging.getLogger(__name__)


class LLMService:
    """Main service for coordinating LLM agents and RAG operations."""
    
    def __init__(self):
        """Initialize the LLM service."""
        self.settings = get_settings()
        self.rag_service: RAGService = get_rag_service()
        
        # Lazy initialization of agents
        self._learning_path_agent: Optional[LearningPathAgent] = None
        self._question_generator_agent: Optional[QuestionGeneratorAgent] = None
        self._chatbot_sessions: Dict[str, ChatbotAgent] = {}
        
        logger.info("LLM Service initialized")
    
    @property
    def learning_path_agent(self) -> LearningPathAgent:
        """Get or create the learning path agent."""
        if self._learning_path_agent is None:
            self._learning_path_agent = LearningPathAgent()
        return self._learning_path_agent
    
    @property
    def question_generator_agent(self) -> QuestionGeneratorAgent:
        """Get or create the question generator agent."""
        if self._question_generator_agent is None:
            self._question_generator_agent = QuestionGeneratorAgent()
        return self._question_generator_agent
    
    def get_chatbot_agent(self, session_id: str = "default") -> ChatbotAgent:
        """
        Get or create a chatbot agent for a specific session.
        
        Args:
            session_id: Session identifier for conversation tracking
            
        Returns:
            ChatbotAgent instance for the session
        """
        if session_id not in self._chatbot_sessions:
            self._chatbot_sessions[session_id] = ChatbotAgent(session_id=session_id)
        return self._chatbot_sessions[session_id]
    
    # RAG Operations
    
    def load_knowledge_base(
        self,
        directory_path: Optional[str] = None,
        texts: Optional[List[str]] = None,
        metadatas: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Load data into the RAG knowledge base.
        
        Args:
            directory_path: Path to directory containing documents
            texts: List of text strings to load
            metadatas: Optional metadata for texts
            
        Returns:
            Dict with loading results
        """
        try:
            if directory_path:
                chunks_added = self.rag_service.load_documents_from_directory(
                    directory_path=directory_path
                )
                return {
                    "status": "success",
                    "method": "directory",
                    "chunks_added": chunks_added,
                    "source": directory_path
                }
            elif texts:
                chunks_added = self.rag_service.load_text_data(
                    texts=texts,
                    metadatas=metadatas
                )
                return {
                    "status": "success",
                    "method": "texts",
                    "chunks_added": chunks_added,
                    "texts_count": len(texts)
                }
            else:
                return {
                    "status": "error",
                    "message": "Either directory_path or texts must be provided"
                }
        except Exception as e:
            logger.error(f"Error loading knowledge base: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def get_knowledge_base_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the knowledge base.
        
        Returns:
            Dict with knowledge base statistics
        """
        try:
            stats = self.rag_service.get_collection_stats()
            return {
                "status": "success",
                **stats
            }
        except Exception as e:
            logger.error(f"Error getting knowledge base stats: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def clear_knowledge_base(self) -> Dict[str, str]:
        """
        Clear all data from the knowledge base.
        
        Returns:
            Dict with operation status
        """
        try:
            self.rag_service.clear_vector_store()
            return {
                "status": "success",
                "message": "Knowledge base cleared successfully"
            }
        except Exception as e:
            logger.error(f"Error clearing knowledge base: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    # Learning Path Operations
    
    def generate_learning_path(
        self,
        goal: str,
        current_level: str = "beginner",
        preferences: Optional[Dict[str, Any]] = None,
        available_time: str = "flexible"
    ) -> LearningPath:
        """
        Generate a personalized learning path.
        
        Args:
            goal: Learning goal or objective
            current_level: Current knowledge level
            preferences: Learning preferences
            available_time: Available time for learning
            
        Returns:
            LearningPath object
        """
        return self.learning_path_agent.generate_learning_path(
            goal=goal,
            current_level=current_level,
            preferences=preferences,
            available_time=available_time
        )
    
    async def agenerate_learning_path(
        self,
        goal: str,
        current_level: str = "beginner",
        preferences: Optional[Dict[str, Any]] = None,
        available_time: str = "flexible"
    ) -> LearningPath:
        """Async version of generate_learning_path."""
        return await self.learning_path_agent.agenerate_learning_path(
            goal=goal,
            current_level=current_level,
            preferences=preferences,
            available_time=available_time
        )
    
    # Question Generation Operations
    
    def generate_questions(
        self,
        topic: str,
        num_questions: int = 5,
        question_types: Optional[List[str]] = None,
        difficulty: str = "medium",
        bloom_levels: Optional[List[str]] = None,
        requirements: Optional[str] = None
    ) -> QuestionSet:
        """
        Generate educational questions.
        
        Args:
            topic: Topic to generate questions about
            num_questions: Number of questions
            question_types: Types of questions
            difficulty: Difficulty level
            bloom_levels: Bloom's taxonomy levels
            requirements: Additional requirements
            
        Returns:
            QuestionSet object
        """
        return self.question_generator_agent.generate_questions(
            topic=topic,
            num_questions=num_questions,
            question_types=question_types,
            difficulty=difficulty,
            bloom_levels=bloom_levels,
            requirements=requirements
        )
    
    async def agenerate_questions(
        self,
        topic: str,
        num_questions: int = 5,
        question_types: Optional[List[str]] = None,
        difficulty: str = "medium",
        bloom_levels: Optional[List[str]] = None,
        requirements: Optional[str] = None
    ) -> QuestionSet:
        """Async version of generate_questions."""
        return await self.question_generator_agent.agenerate_questions(
            topic=topic,
            num_questions=num_questions,
            question_types=question_types,
            difficulty=difficulty,
            bloom_levels=bloom_levels,
            requirements=requirements
        )
    
    # Chatbot Operations
    
    def chat(self, message: str, session_id: str = "default") -> str:
        """
        Send a message to the chatbot.
        
        Args:
            message: User's message
            session_id: Session identifier
            
        Returns:
            Chatbot's response
        """
        chatbot = self.get_chatbot_agent(session_id)
        return chatbot.chat(message)
    
    async def achat(self, message: str, session_id: str = "default") -> str:
        """Async version of chat."""
        chatbot = self.get_chatbot_agent(session_id)
        return await chatbot.achat(message)
    
    def chat_with_details(
        self,
        message: str,
        session_id: str = "default"
    ) -> ChatbotResponse:
        """
        Get detailed chatbot response with metadata.
        
        Args:
            message: User's message
            session_id: Session identifier
            
        Returns:
            ChatbotResponse with details
        """
        chatbot = self.get_chatbot_agent(session_id)
        return chatbot.chat_with_details(message)
    
    def get_chat_history(self, session_id: str = "default") -> List[Dict[str, str]]:
        """
        Get conversation history for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of messages
        """
        if session_id in self._chatbot_sessions:
            return self._chatbot_sessions[session_id].get_history()
        return []
    
    def clear_chat_history(self, session_id: str = "default"):
        """
        Clear conversation history for a session.
        
        Args:
            session_id: Session identifier
        """
        if session_id in self._chatbot_sessions:
            self._chatbot_sessions[session_id].clear_history()
    
    def close_chat_session(self, session_id: str):
        """
        Close and remove a chat session.
        
        Args:
            session_id: Session identifier
        """
        if session_id in self._chatbot_sessions:
            del self._chatbot_sessions[session_id]
            logger.info(f"Closed chat session: {session_id}")


# Global LLM service instance
_llm_service = None


def get_llm_service() -> LLMService:
    """Get or create the global LLM service instance."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
