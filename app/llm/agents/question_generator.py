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
    
    def __init__(self, 
                 temperature: float = 0.7,
                 top_k: int = 40,
                 top_p: float = 0.95,
                 max_output_tokens: Optional[int] = None):
        """Initialize the question generator agent.
        
        Args:
            temperature: Controls randomness (0.0-1.0). Higher = more creative
            top_k: Limits vocabulary to top K tokens. Lower = more focused
            top_p: Nucleus sampling parameter. Lower = more focused
            max_output_tokens: Maximum tokens in response
        """
        _ensure_langchain_loaded()  # Ensure langchain is loaded
        
        self.settings = get_settings()
        self.rag_service = get_rag_service()
        
        if not self.settings.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY not configured")
        
        # Store generation parameters for different modes
        self.generation_params = {
            'temperature': temperature,
            'top_k': top_k,
            'top_p': top_p,
            'max_output_tokens': max_output_tokens or self.settings.LLM_MAX_TOKENS
        }
        
        self.llm = ChatGoogleGenerativeAI(
            model=self.settings.LLM_MODEL,
            temperature=self.generation_params['temperature'],
            top_k=self.generation_params['top_k'],
            top_p=self.generation_params['top_p'],
            max_output_tokens=self.generation_params['max_output_tokens'],
            google_api_key=self.settings.GOOGLE_API_KEY
        )
        
        self.output_parser = PydanticOutputParser(pydantic_object=QuestionSet)
        
        # Create the prompt template
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert educational content creator specializing in assessment design.
Your task is to generate high-quality, pedagogically sound questions that effectively assess student understanding.
Be creative and varied in your question formulation while maintaining educational rigor.

Follow these principles when creating questions:
1. Ensure questions are clear, unambiguous, and properly formatted
2. Match difficulty to the specified level
3. Align questions with appropriate Bloom's taxonomy levels
4. For multiple choice: Create plausible distractors that reveal common misconceptions
5. For all types: Provide thorough explanations that teach, not just verify
6. Cover different aspects of the topic comprehensively
7. Avoid trick questions or unnecessarily complex wording
8. Vary question phrasing, structure, and approach to maintain engagement
9. Use diverse scenarios, examples, and contexts when appropriate
10. Balance between different cognitive levels (remember, understand, apply, analyze, evaluate, create)

Creative Guidelines:
- Use varied question stems and formats
- Incorporate different perspectives and real-world applications
- Mix abstract concepts with concrete examples
- Vary the complexity and depth of explanations
- Create questions that spark curiosity and deeper thinking

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
        
        logger.info(f"Question Generator Agent initialized with params: {self.generation_params}")
    
    def update_generation_params(self, **kwargs):
        """Update generation parameters and reinitialize LLM if needed.
        
        Args:
            temperature: Controls randomness (0.0-1.0)
            top_k: Limits vocabulary to top K tokens
            top_p: Nucleus sampling parameter
            max_output_tokens: Maximum tokens in response
        """
        updated = False
        for param, value in kwargs.items():
            if param in self.generation_params and self.generation_params[param] != value:
                self.generation_params[param] = value
                updated = True
        
        if updated:
            logger.info(f"Updating generation params: {self.generation_params}")
            self.llm = ChatGoogleGenerativeAI(
                model=self.settings.LLM_MODEL,
                temperature=self.generation_params['temperature'],
                top_k=self.generation_params['top_k'],
                top_p=self.generation_params['top_p'],
                max_output_tokens=self.generation_params['max_output_tokens'],
                google_api_key=self.settings.GOOGLE_API_KEY
            )
    
    def set_creativity_mode(self, mode: str = "balanced"):
        """Set predefined creativity modes for question generation.
        
        Args:
            mode: One of 'conservative', 'balanced', 'creative', 'highly_creative'
        """
        modes = {
            'conservative': {
                'temperature': 0.3,
                'top_k': 20,
                'top_p': 0.8
            },
            'balanced': {
                'temperature': 0.7,
                'top_k': 40,
                'top_p': 0.95
            },
            'creative': {
                'temperature': 0.9,
                'top_k': 60,
                'top_p': 0.98
            },
            'highly_creative': {
                'temperature': 1.0,
                'top_k': 80,
                'top_p': 1.0
            }
        }
        
        if mode not in modes:
            raise ValueError(f"Unknown mode: {mode}. Available modes: {list(modes.keys())}")
        
        self.update_generation_params(**modes[mode])
        logger.info(f"Set creativity mode to: {mode}")
    
    def get_generation_params(self) -> Dict[str, Any]:
        """Get current generation parameters."""
        return self.generation_params.copy()
    
    def generate_questions(
        self,
        topic: str,
        num_questions: int = 5,
        question_types: Optional[List[str]] = None,
        difficulty: str = "medium",
        creativity_mode: Optional[str] = None,
        **generation_kwargs
    ) -> QuestionSet:
        """
        Generate educational questions for a topic.
        
        Args:
            topic: Topic to generate questions about
            num_questions: Number of questions to generate
            question_types: List of question types (default: ["multiple_choice"])
            difficulty: Difficulty level (easy, medium, hard)
            creativity_mode: Predefined creativity mode ('conservative', 'balanced', 'creative', 'highly_creative')
            **generation_kwargs: Additional generation parameters (temperature, top_k, top_p, max_output_tokens)
            
        Returns:
            QuestionSet object with generated questions
        """
        logger.info(f"Generating {num_questions} questions for topic: {topic}")
        
        # Apply creativity mode if specified
        if creativity_mode:
            self.set_creativity_mode(creativity_mode)
        
        # Apply any additional generation parameters
        if generation_kwargs:
            self.update_generation_params(**generation_kwargs)
        
        # Default values
        if question_types is None:
            question_types = ["multiple_choice"]
        
        # Log current generation parameters
        logger.info(f"Using generation parameters: {self.generation_params}")
        
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
        creativity_mode: Optional[str] = None,
        **generation_kwargs
    ) -> QuestionSet:
        """
        Async version of generate_questions.
        
        Args:
            topic: Topic to generate questions about
            num_questions: Number of questions to generate
            question_types: List of question types
            difficulty: Difficulty level
            creativity_mode: Predefined creativity mode
            **generation_kwargs: Additional generation parameters
            
        Returns:
            QuestionSet object with generated questions
        """
        logger.info(f"Async generating {num_questions} questions for topic: {topic}")
        
        # Apply creativity mode if specified
        if creativity_mode:
            self.set_creativity_mode(creativity_mode)
        
        # Apply any additional generation parameters
        if generation_kwargs:
            self.update_generation_params(**generation_kwargs)
        
        # Default values
        if question_types is None:
            question_types = ["multiple_choice"]
        
        # Log current generation parameters
        logger.info(f"Using generation parameters: {self.generation_params}")
        
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
