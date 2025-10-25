"""
Test script to verify LLM endpoint works correctly.
This should be run locally before deploying to ensure the Pydantic fix is working.
"""

import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_initialization():
    """Test that LangChain models can be initialized correctly."""
    logger.info("=" * 80)
    logger.info("Testing LangChain Initialization")
    logger.info("=" * 80)
    
    try:
        # Test the initialization module
        from app.llm.init import initialize_langchain_models
        
        logger.info("Calling initialize_langchain_models()...")
        success = initialize_langchain_models()
        
        if not success:
            logger.error("❌ initialize_langchain_models() returned False")
            return False
        
        logger.info("✓ initialize_langchain_models() succeeded")
        return True
        
    except Exception as e:
        logger.error(f"❌ Exception during initialization: {e}", exc_info=True)
        return False


def test_learning_path_agent():
    """Test that the LearningPathAgent can be instantiated."""
    logger.info("\n" + "=" * 80)
    logger.info("Testing LearningPathAgent Instantiation")
    logger.info("=" * 80)
    
    try:
        from app.llm.agents.learning_path import LearningPathAgent
        
        logger.info("Creating LearningPathAgent instance...")
        agent = LearningPathAgent()
        
        logger.info("✓ LearningPathAgent instantiated successfully")
        logger.info(f"  - LLM Model: {agent.llm.model}")
        logger.info(f"  - Temperature: {agent.settings.LLM_TEMPERATURE}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to instantiate LearningPathAgent: {e}", exc_info=True)
        return False


def test_generate_learning_path():
    """Test that ChatGoogleGenerativeAI can be instantiated without Pydantic errors."""
    logger.info("\n" + "=" * 80)
    logger.info("Testing ChatGoogleGenerativeAI Instantiation")
    logger.info("=" * 80)
    
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        from app.config import get_settings
        
        settings = get_settings()
        
        logger.info("Creating ChatGoogleGenerativeAI instance...")
        llm = ChatGoogleGenerativeAI(
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_output_tokens=settings.LLM_MAX_TOKENS,
            google_api_key=settings.GOOGLE_API_KEY
        )
        
        logger.info("✓ ChatGoogleGenerativeAI instantiated successfully")
        logger.info(f"  - Model: {llm.model}")
        logger.info(f"  - Temperature: {llm.temperature}")
        logger.info("✓ No Pydantic errors - fix is working!")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to instantiate ChatGoogleGenerativeAI: {e}", exc_info=True)
        return False


def main():
    """Run all tests."""
    logger.info("Starting LLM Endpoint Tests\n")
    
    tests = [
        ("Initialization", test_initialization),
        ("Agent Instantiation", test_learning_path_agent),
        ("ChatGoogleGenerativeAI Instantiation", test_generate_learning_path)
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error(f"Test '{test_name}' crashed: {e}", exc_info=True)
            results[test_name] = False
    
    # Print summary
    logger.info("\n" + "=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "❌ FAIL"
        logger.info(f"{status} - {test_name}")
    
    all_passed = all(results.values())
    
    logger.info("\n" + "=" * 80)
    if all_passed:
        logger.info("🎉 ALL TESTS PASSED - Ready to deploy!")
    else:
        logger.error("❌ SOME TESTS FAILED - DO NOT deploy yet!")
    logger.info("=" * 80)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
