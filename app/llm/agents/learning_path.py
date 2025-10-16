"""
Learning Path Agent

LangChain agent for generating personalized learning paths based on student data
and learning objectives.
"""

from email.mime import message
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from app.config import get_settings
from app.llm.rag import get_rag_service
from app.clients.content_service import ContentServiceClient
from app.clients.kafka_client import get_kafka_client

logger = logging.getLogger(__name__)

# Lazy imports to avoid loading heavy ML libraries at startup
ChatGoogleGenerativeAI = None
ChatPromptTemplate = None
PydanticOutputParser = None
RunnablePassthrough = None

def _ensure_langchain_loaded():
    """Lazy load langchain modules."""
    global ChatGoogleGenerativeAI, ChatPromptTemplate, PydanticOutputParser, RunnablePassthrough
    if ChatGoogleGenerativeAI is None:
        # Import all cache-related dependencies BEFORE importing ChatGoogleGenerativeAI
        # This resolves Pydantic forward references
        try:
            from langchain_core.caches import BaseCache
            from langchain_core.language_models.base import BaseLanguageModel
            from langchain_core.language_models.chat_models import BaseChatModel
            logger.debug("BaseCache and BaseLanguageModel imported successfully")
            
            # Rebuild base models first
            try:
                BaseCache.model_rebuild()
                logger.debug("BaseCache.model_rebuild() completed")
            except Exception as e:
                logger.debug(f"BaseCache rebuild not needed or failed: {e}")
                
            try:
                BaseLanguageModel.model_rebuild()
                logger.debug("BaseLanguageModel.model_rebuild() completed")
            except Exception as e:
                logger.debug(f"BaseLanguageModel rebuild not needed or failed: {e}")
                
            try:
                BaseChatModel.model_rebuild()
                logger.debug("BaseChatModel.model_rebuild() completed")
            except Exception as e:
                logger.debug(f"BaseChatModel rebuild not needed or failed: {e}")
                
        except ImportError as e:
            logger.warning(f"Could not import base models from langchain_core: {e}")
            try:
                from langchain.cache import BaseCache
                logger.debug("BaseCache imported from langchain.cache")
                try:
                    BaseCache.model_rebuild()
                    logger.debug("BaseCache.model_rebuild() completed")
                except Exception as e2:
                    logger.debug(f"BaseCache rebuild not needed or failed: {e2}")
            except ImportError as e2:
                logger.warning(f"Could not import BaseCache from langchain.cache either: {e2}")
        
        # Now import ChatGoogleGenerativeAI
        from langchain_google_genai import ChatGoogleGenerativeAI as _ChatGoogleGenerativeAI
        from langchain.prompts import ChatPromptTemplate as _ChatPromptTemplate
        from langchain.output_parsers import PydanticOutputParser as _PydanticOutputParser
        from langchain.schema.runnable import RunnablePassthrough as _RunnablePassthrough
        
        # CRITICAL: Call model_rebuild() BEFORE assigning to globals
        # This ensures the Pydantic model is fully defined before use
        try:
            logger.debug("Attempting to rebuild ChatGoogleGenerativeAI Pydantic model...")
            _ChatGoogleGenerativeAI.model_rebuild()
            logger.info("ChatGoogleGenerativeAI.model_rebuild() completed successfully")
        except Exception as e:
            logger.error(f"Failed to rebuild ChatGoogleGenerativeAI model: {e}", exc_info=True)
            # Try to rebuild all base models
            try:
                from pydantic import BaseModel
                BaseModel.model_rebuild()
                _ChatGoogleGenerativeAI.model_rebuild()
                logger.info("ChatGoogleGenerativeAI.model_rebuild() succeeded after rebuilding BaseModel")
            except Exception as e2:
                logger.error(f"Second attempt to rebuild failed: {e2}", exc_info=True)
        
        globals()['ChatGoogleGenerativeAI'] = _ChatGoogleGenerativeAI
        globals()['ChatPromptTemplate'] = _ChatPromptTemplate
        globals()['PydanticOutputParser'] = _PydanticOutputParser
        globals()['RunnablePassthrough'] = _RunnablePassthrough


# Output schema for learning path
class LearningStep(BaseModel):
    """A single step in a learning path."""
    step_number: int = Field(description="Sequential number of this step")
    title: str = Field(description="Title of the learning step")
    description: str = Field(description="Detailed description of what to learn")
    estimated_duration: str = Field(description="Estimated time to complete (e.g., '2 hours', '3 days')")
    resources: List[str] = Field(description="List of recommended resources or topics")
    prerequisites: List[str] = Field(default=[], description="Prerequisites for this step")


class LearningPath(BaseModel):
    """Complete learning path with multiple steps."""
    goal: str = Field(description="Overall learning goal")
    difficulty_level: str = Field(description="Difficulty level (beginner, intermediate, advanced)")
    total_duration: str = Field(description="Total estimated duration")
    steps: List[LearningStep] = Field(description="Ordered list of learning steps")


class LearningPathAgent:
    """Agent for generating personalized learning paths."""
    
    def __init__(self):
        """Initialize the learning path agent."""
        _ensure_langchain_loaded()  # Ensure langchain is loaded
        
        self.settings = get_settings()
        self.rag_service = get_rag_service()
        self.content_client = ContentServiceClient()
        self.kafka_client = None  # Will be initialized when needed
        
        if not self.settings.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY not configured")
        
        self.llm = ChatGoogleGenerativeAI(
            model=self.settings.LLM_MODEL,
            temperature=self.settings.LLM_TEMPERATURE,
            max_output_tokens=self.settings.LLM_MAX_TOKENS,
            google_api_key=self.settings.GOOGLE_API_KEY
        )
        
        self.output_parser = PydanticOutputParser(pydantic_object=LearningPath)
        
        # Create the prompt template
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert educational consultant who creates personalized learning paths.
Your task is to generate a comprehensive, well-structured learning path that helps students achieve their learning goals.

Consider the following when creating the learning path:
1. Break down complex topics into manageable steps
2. Order steps logically from foundational to advanced concepts
3. Provide realistic time estimates based on available time
4. Include diverse learning resources
5. Ensure prerequisites are clear
6. Consider the user's current skill level and mastery scores
7. Adapt difficulty based on current level
8. Account for time constraints when estimating durations

Current Skill Level: {current_level}
Available Time: {available_time}
User Preferences: {preferences}

User's Mastery Scores:
{mastery_scores}

Available Resources:
{available_resources}

Use the following context from the knowledge base to inform your recommendations:
{context}

{format_instructions}"""),
            ("human", """Create a personalized learning path for the following:

Learning Goal: {goal}

Generate a detailed learning path that will help achieve this goal based on the user's current level ({current_level}), available time ({available_time}), mastery scores, and available resources.""")
        ])
        
        logger.info("Learning Path Agent initialized")
    
    async def _get_kafka_client(self):
        """Get or initialize Kafka client."""
        if self.kafka_client is None:
            self.kafka_client = get_kafka_client()
        return self.kafka_client
    
    async def generate_learning_path(
        self,
        user_id: str,
        goal: str,
        current_level: Optional[str] = "beginner",
        preferences: Optional[Dict[str, Any]] = None,
        available_time: Optional[str] = "flexible",
    ) -> LearningPath:
        """
        Generate a personalized learning path.
        
        Args:
            user_id: The user's unique identifier
            goal: The learning goal or objective
            current_level: Current skill level (beginner, intermediate, advanced)
            preferences: User preferences for learning path generation
            available_time: Available time for learning
            
        Returns:
            LearningPath object with structured steps
        """
        logger.info(f"Generating learning path for user {user_id}, goal: {goal}, level: {current_level}")
        
        # Fetch user's mastery scores and available resources from content service
        try:
            mastery_scores = await self.content_client.get_user_mastery_score(user_id)
            available_resources = await self.content_client.get_available_resources(user_id)
            logger.info(f"Fetched mastery scores and resources for user {user_id}")
        except Exception as e:
            logger.warning(f"Could not fetch user data from content service: {e}")
            mastery_scores = {}
            available_resources = []
        
        # Get relevant context from RAG
        try:
            retriever = self.rag_service.get_retriever(k=5)
            context_docs = await retriever.aget_relevant_documents(goal)
            context = "\n\n".join([doc.page_content for doc in context_docs])
        except Exception as e:
            logger.warning(f"Could not retrieve context from RAG: {e}")
            context = "No additional context available."
        
        # Format data for prompt
        preferences_str = str(preferences) if preferences else "No specific preferences"
        mastery_scores_str = str(mastery_scores) if mastery_scores else "No mastery score data available"
        resources_str = str(available_resources) if available_resources else "No specific resources available"
        
        # Create the chain
        chain = (
            {
                "user_id": RunnablePassthrough(),
                "goal": lambda _: goal,
                "current_level": lambda _: current_level or "beginner",
                "available_time": lambda _: available_time or "flexible",
                "preferences": lambda _: preferences_str,
                "mastery_scores": lambda _: mastery_scores_str,
                "available_resources": lambda _: resources_str,
                "context": lambda _: context,
                "format_instructions": lambda _: self.output_parser.get_format_instructions()
            }
            | self.prompt
            | self.llm
            | self.output_parser
        )
        
        # Generate learning path
        learning_path = await chain.ainvoke(user_id)
        logger.info(f"Generated learning path with {len(learning_path.steps)} steps for user {user_id}")
        
        # Publish to Kafka learning_path topic
        try:
            kafka_client = await self._get_kafka_client()
            await kafka_client.publish(
                topic="learning_path",
                message={
                    "user_id": user_id,
                    "learning_goal": goal,
                    "learning_path": learning_path.model_dump(),
                    "mastery_scores": mastery_scores,
                    "available_resources": available_resources
                },
                key=user_id
            )
            logger.info(f"Published learning path to Kafka for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to publish learning path to Kafka: {e}")
        
        return learning_path
