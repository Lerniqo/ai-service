"""
Chatbot Agent

LangChain agent for conversational AI assistance with RAG capabilities.
Provides intelligent responses to student queries using retrieved context.
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
MessagesPlaceholder = None
ConversationBufferMemory = None
HumanMessage = None
AIMessage = None
SystemMessage = None
RunnablePassthrough = None
RunnableLambda = None

def _ensure_langchain_loaded():
    """Lazy load langchain modules."""
    global ChatGoogleGenerativeAI, ChatPromptTemplate, MessagesPlaceholder, ConversationBufferMemory
    global HumanMessage, AIMessage, SystemMessage, RunnablePassthrough, RunnableLambda
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
        from langchain.prompts import ChatPromptTemplate as _ChatPromptTemplate, MessagesPlaceholder as _MessagesPlaceholder
        from langchain.memory import ConversationBufferMemory as _ConversationBufferMemory
        from langchain.schema import HumanMessage as _HumanMessage, AIMessage as _AIMessage, SystemMessage as _SystemMessage
        from langchain.schema.runnable import RunnablePassthrough as _RunnablePassthrough, RunnableLambda as _RunnableLambda
        
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
        globals()['MessagesPlaceholder'] = _MessagesPlaceholder
        globals()['ConversationBufferMemory'] = _ConversationBufferMemory
        globals()['HumanMessage'] = _HumanMessage
        globals()['AIMessage'] = _AIMessage
        globals()['SystemMessage'] = _SystemMessage
        globals()['RunnablePassthrough'] = _RunnablePassthrough
        globals()['RunnableLambda'] = _RunnableLambda


# Output schema for chatbot response
class ChatbotResponse(BaseModel):
    """Response from the chatbot."""
    message: str = Field(description="The chatbot's response message")
    sources: List[str] = Field(default=[], description="Sources used to generate the response")
    confidence: str = Field(description="Confidence level: high, medium, low")
    follow_up_suggestions: List[str] = Field(default=[], description="Suggested follow-up questions")


class ChatbotAgent:
    """Conversational agent with RAG capabilities."""
    
    def __init__(self, session_id: Optional[str] = None):
        """
        Initialize the chatbot agent.
        
        Args:
            session_id: Optional session identifier for conversation tracking
        """
        _ensure_langchain_loaded()  # Ensure langchain is loaded
        
        self.settings = get_settings()
        self.rag_service = get_rag_service()
        self.session_id = session_id or "default"
        
        if not self.settings.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY not configured")
        
        self.llm = ChatGoogleGenerativeAI(
            model=self.settings.LLM_MODEL,
            temperature=0.7,
            max_output_tokens=self.settings.LLM_MAX_TOKENS,
            google_api_key=self.settings.GOOGLE_API_KEY
        )
        
        # Initialize conversation memory
        self.memory = ConversationBufferMemory(
            return_messages=True,
            memory_key="chat_history"
        )
        
        # Create the prompt template
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a helpful, knowledgeable AI tutor and learning assistant.
Your role is to help students understand concepts, answer questions, and guide their learning journey.

Guidelines for your responses:
1. Be clear, concise, and educational
2. Break down complex concepts into understandable parts
3. Use examples and analogies when helpful
4. Encourage critical thinking by asking follow-up questions
5. Admit when you're not certain and suggest where to find more information
6. Be supportive and encouraging
7. Use the provided context to give accurate, relevant information

Context from knowledge base:
{context}

If the context doesn't contain relevant information, rely on your general knowledge but indicate when you're doing so.
"""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}")
        ])
        
        logger.info(f"Chatbot Agent initialized for session: {self.session_id}")
    
    def _get_context(self, question: str) -> str:
        """Get relevant context from RAG for the question."""
        try:
            retriever = self.rag_service.get_retriever(k=3)
            context_docs = retriever.get_relevant_documents(question)
            
            if context_docs:
                context_parts = []
                for i, doc in enumerate(context_docs, 1):
                    source = doc.metadata.get("source", f"Document {i}")
                    context_parts.append(f"[Source {i}: {source}]\n{doc.page_content}")
                return "\n\n".join(context_parts)
            else:
                return "No specific context available from the knowledge base."
        except Exception as e:
            logger.warning(f"Could not retrieve context from RAG: {e}")
            return "No context available from the knowledge base."
    
    def chat(self, message: str) -> str:
        """
        Send a message and get a response.
        
        Args:
            message: User's message/question
            
        Returns:
            Chatbot's response
        """
        logger.info(f"Processing message: {message[:50]}...")
        
        # Get relevant context
        context = self._get_context(message)
        
        # Get chat history
        chat_history = self.memory.load_memory_variables({})
        
        # Create the chain
        chain = (
            {
                "question": RunnablePassthrough(),
                "context": lambda _: context,
                "chat_history": lambda _: chat_history.get("chat_history", [])
            }
            | self.prompt
            | self.llm
        )
        
        # Get response
        response = chain.invoke(message)
        response_text = response.content
        
        # Save to memory
        self.memory.save_context(
            {"input": message},
            {"output": response_text}
        )
        
        logger.info("Generated response")
        return response_text
    
    async def achat(self, message: str) -> str:
        """
        Async version of chat.
        
        Args:
            message: User's message/question
            
        Returns:
            Chatbot's response
        """
        logger.info(f"Async processing message: {message[:50]}...")
        
        # Get relevant context
        try:
            retriever = self.rag_service.get_retriever(k=3)
            context_docs = await retriever.aget_relevant_documents(message)
            
            if context_docs:
                context_parts = []
                for i, doc in enumerate(context_docs, 1):
                    source = doc.metadata.get("source", f"Document {i}")
                    context_parts.append(f"[Source {i}: {source}]\n{doc.page_content}")
                context = "\n\n".join(context_parts)
            else:
                context = "No specific context available from the knowledge base."
        except Exception as e:
            logger.warning(f"Could not retrieve context from RAG: {e}")
            context = "No context available from the knowledge base."
        
        # Get chat history
        chat_history = self.memory.load_memory_variables({})
        
        # Create the chain
        chain = (
            {
                "question": RunnablePassthrough(),
                "context": lambda _: context,
                "chat_history": lambda _: chat_history.get("chat_history", [])
            }
            | self.prompt
            | self.llm
        )
        
        # Get response
        response = await chain.ainvoke(message)
        response_text = response.content
        
        # Save to memory
        self.memory.save_context(
            {"input": message},
            {"output": response_text}
        )
        
        logger.info("Generated response")
        return response_text
    
    def chat_with_details(self, message: str) -> ChatbotResponse:
        """
        Get a detailed response with metadata.
        
        Args:
            message: User's message/question
            
        Returns:
            ChatbotResponse with message, sources, and suggestions
        """
        logger.info(f"Processing detailed chat message: {message[:50]}...")
        
        # Get relevant context with sources
        try:
            retriever = self.rag_service.get_retriever(k=3)
            context_docs = retriever.get_relevant_documents(message)
            
            sources = []
            context_parts = []
            for i, doc in enumerate(context_docs, 1):
                source = doc.metadata.get("source", f"Document {i}")
                sources.append(source)
                context_parts.append(f"[Source {i}: {source}]\n{doc.page_content}")
            context = "\n\n".join(context_parts) if context_parts else "No context available."
        except Exception as e:
            logger.warning(f"Could not retrieve context from RAG: {e}")
            context = "No context available."
            sources = []
        
        # Get chat history
        chat_history = self.memory.load_memory_variables({})
        
        # Create the chain
        chain = (
            {
                "question": RunnablePassthrough(),
                "context": lambda _: context,
                "chat_history": lambda _: chat_history.get("chat_history", [])
            }
            | self.prompt
            | self.llm
        )
        
        # Get response
        response = chain.invoke(message)
        response_text = response.content
        
        # Save to memory
        self.memory.save_context(
            {"input": message},
            {"output": response_text}
        )
        
        # Determine confidence based on context availability
        confidence = "high" if sources else "medium"
        
        # Generate follow-up suggestions (simplified)
        follow_ups = self._generate_follow_ups(message, response_text)
        
        return ChatbotResponse(
            message=response_text,
            sources=sources,
            confidence=confidence,
            follow_up_suggestions=follow_ups
        )
    
    def _generate_follow_ups(self, question: str, response: str) -> List[str]:
        """Generate follow-up question suggestions."""
        # Simple heuristic-based follow-ups
        # In a production system, this could use another LLM call
        follow_ups = []
        
        if "?" in response:
            follow_ups.append("Could you explain that in more detail?")
        
        if len(response) > 200:
            follow_ups.append("Can you give me a simple example?")
        
        follow_ups.append("What are the practical applications of this?")
        
        return follow_ups[:3]
    
    def clear_history(self):
        """Clear conversation history."""
        self.memory.clear()
        logger.info(f"Cleared conversation history for session: {self.session_id}")
    
    def get_history(self) -> List[Dict[str, str]]:
        """
        Get conversation history.
        
        Returns:
            List of message dictionaries with 'role' and 'content'
        """
        chat_history = self.memory.load_memory_variables({}).get("chat_history", [])
        
        history = []
        for msg in chat_history:
            if isinstance(msg, HumanMessage):
                history.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                history.append({"role": "assistant", "content": msg.content})
        
        return history
