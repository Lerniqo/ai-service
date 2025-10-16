"""
Question Generator Agent

LangChain agent for generating educational questions based on topics and difficulty levels.
"""

import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from app.config import get_settings
from app.llm.rag import get_rag_service

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


# Output schema for questions
class QuestionOption(BaseModel):
    """A single answer option for multiple choice questions."""
    option_id: str = Field(description="Option identifier (A, B, C, D)")
    text: str = Field(description="Option text")
    is_correct: bool = Field(description="Whether this is the correct answer")


class Question(BaseModel):
    """A single educational question."""
    question_id: int = Field(description="Unique identifier for the question")
    question_type: str = Field(description="Type: multiple_choice, true_false, short_answer, essay")
    question_text: str = Field(description="The question text")
    options: Optional[List[QuestionOption]] = Field(default=None, description="Answer options for MCQ")
    correct_answer: str = Field(description="The correct answer or key points")
    explanation: str = Field(description="Explanation of the correct answer")
    difficulty: str = Field(description="Difficulty level: easy, medium, hard")
    concepts: List[str] = Field(description="Concepts being tested")


class QuestionSet(BaseModel):
    """A set of generated questions."""
    topic: str = Field(description="Overall topic")
    total_questions: int = Field(description="Total number of questions")
    questions: List[Question] = Field(description="List of questions")


class QuestionGeneratorAgent:
    """Agent for generating educational questions."""
    
    def __init__(self):
        """Initialize the question generator agent."""
        _ensure_langchain_loaded()  # Ensure langchain is loaded
        
        self.settings = get_settings()
        self.rag_service = get_rag_service()
        
        if not self.settings.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY not configured")
        
        self.llm = ChatGoogleGenerativeAI(
            model=self.settings.LLM_MODEL,
            temperature=0.8,  # Higher temperature for more creative questions
            max_output_tokens=self.settings.LLM_MAX_TOKENS,
            google_api_key=self.settings.GOOGLE_API_KEY
        )
        
        self.output_parser = PydanticOutputParser(pydantic_object=QuestionSet)
        
        # Create the prompt template
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert educational content creator specializing in assessment design.
Your task is to generate high-quality, pedagogically sound questions that effectively assess student understanding.

Follow these principles when creating questions:
1. Ensure questions are clear, unambiguous, and properly formatted
2. Match difficulty to the specified level
3. Align questions with appropriate Bloom's taxonomy levels
4. For multiple choice: Create plausible distractors that reveal common misconceptions
5. For all types: Provide thorough explanations that teach, not just verify
6. Cover different aspects of the topic comprehensively
7. Avoid trick questions or unnecessarily complex wording

Use the following context from the knowledge base to inform your questions:
{context}

{format_instructions}"""),
            ("human", """Generate educational questions for the following:

Topic: {topic}
Number of Questions: {num_questions}
Question Types: {question_types}
Difficulty Level: {difficulty}

Create a comprehensive set of questions that effectively assess understanding of this topic.""")
        ])
        
        logger.info("Question Generator Agent initialized")
    
    def generate_questions(
        self,
        topic: str,
        num_questions: int = 5,
        question_types: Optional[List[str]] = None,
        difficulty: str = "medium",
    ) -> QuestionSet:
        """
        Generate educational questions for a topic.
        
        Args:
            topic: Topic to generate questions about
            num_questions: Number of questions to generate
            question_types: List of question types (default: ["multiple_choice"])
            difficulty: Difficulty level (easy, medium, hard)
            
        Returns:
            QuestionSet object with generated questions
        """
        logger.info(f"Generating {num_questions} questions for topic: {topic}")
        
        # Default values
        if question_types is None:
            question_types = ["multiple_choice"]
        
        # Get relevant context from RAG
        try:
            retriever = self.rag_service.get_retriever(k=5)
            context_docs = retriever.get_relevant_documents(topic)
            context = "\n\n".join([doc.page_content for doc in context_docs])
        except Exception as e:
            logger.warning(f"Could not retrieve context from RAG: {e}")
            context = "No additional context available."
        
        # Create the chain
        chain = (
            {
                "topic": RunnablePassthrough(),
                "num_questions": lambda _: str(num_questions),
                "question_types": lambda _: ", ".join(question_types),
                "difficulty": lambda _: difficulty,
                "context": lambda _: context,
                "format_instructions": lambda _: self.output_parser.get_format_instructions()
            }
            | self.prompt
            | self.llm
            | self.output_parser
        )
        
        # Generate questions
        question_set = chain.invoke(topic)
        logger.info(f"Generated {len(question_set.questions)} questions")
        
        return question_set
    
    async def agenerate_questions(
        self,
        topic: str,
        num_questions: int = 5,
        question_types: Optional[List[str]] = None,
        difficulty: str = "medium",
    ) -> QuestionSet:
        """
        Async version of generate_questions.
        
        Args:
            topic: Topic to generate questions about
            num_questions: Number of questions to generate
            question_types: List of question types
            difficulty: Difficulty level
            
        Returns:
            QuestionSet object with generated questions
        """
        logger.info(f"Async generating {num_questions} questions for topic: {topic}")
        
        # Default values
        if question_types is None:
            question_types = ["multiple_choice"]
        
        # Get relevant context from RAG
        try:
            retriever = self.rag_service.get_retriever(k=5)
            context_docs = await retriever.aget_relevant_documents(topic)
            context = "\n\n".join([doc.page_content for doc in context_docs])
        except Exception as e:
            logger.warning(f"Could not retrieve context from RAG: {e}")
            context = "No additional context available."
        
        # Create the chain
        chain = (
            {
                "topic": RunnablePassthrough(),
                "num_questions": lambda _: str(num_questions),
                "question_types": lambda _: ", ".join(question_types),
                "difficulty": lambda _: difficulty,
                "context": lambda _: context,
                "format_instructions": lambda _: self.output_parser.get_format_instructions()
            }
            | self.prompt
            | self.llm
            | self.output_parser
        )
        
        # Generate questions
        question_set = await chain.ainvoke(topic)
        logger.info(f"Generated {len(question_set.questions)} questions")
        
        return question_set
