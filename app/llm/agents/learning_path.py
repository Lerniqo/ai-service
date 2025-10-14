"""
Learning Path Agent

LangChain agent for generating personalized learning paths based on student data
and learning objectives.
"""

import logging
from typing import List, Dict, Any, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from langchain.schema.runnable import RunnablePassthrough
from pydantic import BaseModel, Field
from app.config import get_settings
from app.llm.rag import get_rag_service

logger = logging.getLogger(__name__)


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
        self.settings = get_settings()
        self.rag_service = get_rag_service()
        
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
3. Provide realistic time estimates
4. Include diverse learning resources
5. Ensure prerequisites are clear

Use the following context from the knowledge base to inform your recommendations:
{context}

{format_instructions}"""),
            ("human", """Create a personalized learning path for the following:

Learning Goal: {goal}
Current Level: {current_level}
Preferences: {preferences}
Available Time: {available_time}

Generate a detailed learning path that will help achieve this goal.""")
        ])
        
        logger.info("Learning Path Agent initialized")
    
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
            goal: The learning goal or objective
            current_level: Current knowledge level (beginner, intermediate, advanced)
            preferences: Optional dict with learning preferences (topics, formats, etc.)
            available_time: Available time for learning (e.g., "2 hours/day", "weekends only")
            
        Returns:
            LearningPath object with structured steps
        """
        logger.info(f"Generating learning path for goal: {goal}")
        
        # Get relevant context from RAG
        try:
            retriever = self.rag_service.get_retriever(k=5)
            context_docs = retriever.get_relevant_documents(goal)
            context = "\n\n".join([doc.page_content for doc in context_docs])
        except Exception as e:
            logger.warning(f"Could not retrieve context from RAG: {e}")
            context = "No additional context available."
        
        # Format preferences
        preferences_str = str(preferences) if preferences else "No specific preferences"
        
        # Create the chain
        chain = (
            {
                "goal": RunnablePassthrough(),
                "current_level": lambda _: current_level,
                "preferences": lambda _: preferences_str,
                "available_time": lambda _: available_time,
                "context": lambda _: context,
                "format_instructions": lambda _: self.output_parser.get_format_instructions()
            }
            | self.prompt
            | self.llm
            | self.output_parser
        )
        
        # Generate learning path
        learning_path = chain.invoke(goal)
        logger.info(f"Generated learning path with {len(learning_path.steps)} steps")
        
        return learning_path
    
    async def agenerate_learning_path(
        self,
        goal: str,
        current_level: str = "beginner",
        preferences: Optional[Dict[str, Any]] = None,
        available_time: str = "flexible"
    ) -> LearningPath:
        """
        Async version of generate_learning_path.
        
        Args:
            goal: The learning goal or objective
            current_level: Current knowledge level (beginner, intermediate, advanced)
            preferences: Optional dict with learning preferences (topics, formats, etc.)
            available_time: Available time for learning
            
        Returns:
            LearningPath object with structured steps
        """
        logger.info(f"Async generating learning path for goal: {goal}")
        
        # Get relevant context from RAG
        try:
            retriever = self.rag_service.get_retriever(k=5)
            context_docs = await retriever.aget_relevant_documents(goal)
            context = "\n\n".join([doc.page_content for doc in context_docs])
        except Exception as e:
            logger.warning(f"Could not retrieve context from RAG: {e}")
            context = "No additional context available."
        
        # Format preferences
        preferences_str = str(preferences) if preferences else "No specific preferences"
        
        # Create the chain
        chain = (
            {
                "goal": RunnablePassthrough(),
                "current_level": lambda _: current_level,
                "preferences": lambda _: preferences_str,
                "available_time": lambda _: available_time,
                "context": lambda _: context,
                "format_instructions": lambda _: self.output_parser.get_format_instructions()
            }
            | self.prompt
            | self.llm
            | self.output_parser
        )
        
        # Generate learning path
        learning_path = await chain.ainvoke(goal)
        logger.info(f"Generated learning path with {len(learning_path.steps)} steps")
        
        return learning_path
