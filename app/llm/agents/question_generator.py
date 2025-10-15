"""
Question Generator Agent

LangChain agent for generating educational questions based on topics and difficulty levels.
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
Bloom's Levels: {bloom_levels}
Additional Requirements: {requirements}

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
            bloom_levels: Target Bloom's taxonomy levels
            requirements: Additional requirements or constraints
            
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
        bloom_levels: Optional[List[str]] = None,
        requirements: Optional[str] = None
    ) -> QuestionSet:
        """
        Async version of generate_questions.
        
        Args:
            topic: Topic to generate questions about
            num_questions: Number of questions to generate
            question_types: List of question types
            difficulty: Difficulty level
            bloom_levels: Target Bloom's taxonomy levels
            requirements: Additional requirements
            
        Returns:
            QuestionSet object with generated questions
        """
        logger.info(f"Async generating {num_questions} questions for topic: {topic}")
        
        # Default values
        if question_types is None:
            question_types = ["multiple_choice"]
        if bloom_levels is None:
            bloom_levels = ["understand", "apply", "analyze"]
        if requirements is None:
            requirements = "No additional requirements"
        
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
