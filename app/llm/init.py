"""
LLM Initialization Module

Pre-initializes LangChain dependencies to avoid Pydantic model definition issues.
This should be called during application startup to ensure all models are properly built.
"""

import logging

logger = logging.getLogger(__name__)

_initialized = False


def initialize_langchain_models():
    """
    Pre-initialize LangChain models to resolve Pydantic forward references.
    
    This function should be called during application startup to ensure that
    ChatGoogleGenerativeAI and other LangChain models are properly initialized
    before any consumers or agents try to use them.
    
    Returns:
        bool: True if initialization was successful, False otherwise
    """
    global _initialized
    
    if _initialized:
        logger.debug("LangChain models already initialized, skipping")
        return True
    
    try:
        logger.info("Pre-initializing LangChain models to resolve Pydantic dependencies...")
        
        # Step 1: Import BaseCache first to resolve forward references
        try:
            from langchain_core.caches import BaseCache
            logger.debug("✓ BaseCache imported from langchain_core.caches")
        except ImportError as e:
            logger.warning(f"Could not import BaseCache from langchain_core.caches: {e}")
            try:
                from langchain.cache import BaseCache
                logger.debug("✓ BaseCache imported from langchain.cache (fallback)")
            except ImportError as e2:
                logger.error(f"Could not import BaseCache from either location: {e2}")
                # Continue anyway, might still work
        
        # Step 2: Import ChatGoogleGenerativeAI
        from langchain_google_genai import ChatGoogleGenerativeAI
        logger.debug("✓ ChatGoogleGenerativeAI imported")
        
        # Step 3: Rebuild the Pydantic model
        try:
            ChatGoogleGenerativeAI.model_rebuild()
            logger.info("✓ ChatGoogleGenerativeAI.model_rebuild() completed successfully")
        except Exception as e:
            logger.error(f"Failed to rebuild ChatGoogleGenerativeAI model: {e}", exc_info=True)
            # Try alternative approach
            try:
                from pydantic import BaseModel
                BaseModel.model_rebuild()
                ChatGoogleGenerativeAI.model_rebuild()
                logger.info("✓ ChatGoogleGenerativeAI.model_rebuild() succeeded after rebuilding BaseModel")
            except Exception as e2:
                logger.error(f"Second attempt to rebuild failed: {e2}", exc_info=True)
                return False
        
        # Step 4: Import other commonly used LangChain components
        try:
            from langchain.prompts import ChatPromptTemplate
            from langchain.output_parsers import PydanticOutputParser
            from langchain.schema.runnable import RunnablePassthrough
            logger.debug("✓ Additional LangChain components imported")
        except ImportError as e:
            logger.warning(f"Could not import some LangChain components: {e}")
        
        _initialized = True
        logger.info("🎉 LangChain models pre-initialization completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to pre-initialize LangChain models: {e}", exc_info=True)
        return False


def is_initialized() -> bool:
    """Check if LangChain models have been initialized."""
    return _initialized
