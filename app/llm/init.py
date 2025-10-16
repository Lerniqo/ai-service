"""
LLM Initialization Module

Pre-initializes LangChain dependencies to avoid Pydantic model definition issues.
This should be called during application startup to ensure all models are properly built.
"""

import logging
import os

logger = logging.getLogger(__name__)

_initialized = False

# Force early initialization by importing base classes
try:
    # Import BaseCache BEFORE any other LangChain imports
    try:
        from langchain_core.caches import BaseCache
        BaseCache.model_rebuild()
    except:
        pass
    
    try:
        from langchain_core.language_models.base import BaseLanguageModel
        from langchain_core.language_models.chat_models import BaseChatModel
        BaseLanguageModel.model_rebuild()
        BaseChatModel.model_rebuild()
    except:
        pass
    
    # Import and rebuild ChatGoogleGenerativeAI immediately
    from langchain_google_genai import ChatGoogleGenerativeAI
    ChatGoogleGenerativeAI.model_rebuild()
    logger.debug("Module-level ChatGoogleGenerativeAI.model_rebuild() completed")
except Exception as e:
    logger.debug(f"Module-level initialization skipped: {e}")


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
        
        # Step 1: Import and rebuild BaseCache and related models FIRST
        cache_imported = False
        try:
            from langchain_core.caches import BaseCache
            logger.debug("✓ BaseCache imported from langchain_core.caches")
            cache_imported = True
        except ImportError as e:
            logger.warning(f"Could not import BaseCache from langchain_core.caches: {e}")
            try:
                from langchain.cache import BaseCache
                logger.debug("✓ BaseCache imported from langchain.cache (fallback)")
                cache_imported = True
            except ImportError as e2:
                logger.warning(f"Could not import BaseCache from either location: {e2}")
        
        # Rebuild BaseCache if imported
        if cache_imported:
            try:
                BaseCache.model_rebuild()
                logger.debug("✓ BaseCache.model_rebuild() completed")
            except Exception as e:
                logger.debug(f"BaseCache rebuild skipped: {e}")
        
        # Import and rebuild base language models
        try:
            from langchain_core.language_models.base import BaseLanguageModel
            from langchain_core.language_models.chat_models import BaseChatModel
            logger.debug("✓ BaseLanguageModel and BaseChatModel imported")
            
            try:
                BaseLanguageModel.model_rebuild()
                logger.debug("✓ BaseLanguageModel.model_rebuild() completed")
            except Exception as e:
                logger.debug(f"BaseLanguageModel rebuild skipped: {e}")
            
            try:
                BaseChatModel.model_rebuild()
                logger.debug("✓ BaseChatModel.model_rebuild() completed")
            except Exception as e:
                logger.debug(f"BaseChatModel rebuild skipped: {e}")
        except ImportError as e:
            logger.warning(f"Could not import base language models: {e}")
        
        # Step 2: Import ChatGoogleGenerativeAI
        from langchain_google_genai import ChatGoogleGenerativeAI
        logger.debug("✓ ChatGoogleGenerativeAI imported")
        
        # Step 3: Rebuild the Pydantic model MULTIPLE TIMES if needed
        rebuild_success = False
        for attempt in range(3):
            try:
                ChatGoogleGenerativeAI.model_rebuild()
                logger.info(f"✓ ChatGoogleGenerativeAI.model_rebuild() completed successfully (attempt {attempt + 1})")
                rebuild_success = True
                break
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} to rebuild ChatGoogleGenerativeAI failed: {e}")
                if attempt == 2:
                    logger.error(f"Failed to rebuild ChatGoogleGenerativeAI model after 3 attempts: {e}", exc_info=True)
        
        if not rebuild_success:
            logger.error("Could not rebuild ChatGoogleGenerativeAI - LLM features may not work")
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
