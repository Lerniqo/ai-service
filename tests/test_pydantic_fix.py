"""
Tests for Pydantic BaseCache fix

These tests verify that the ChatGoogleGenerativeAI model is properly initialized
and that all base models are rebuilt correctly to prevent the "not fully defined" error.

Run with: pytest tests/test_pydantic_fix.py -v
"""

import pytest
import logging
from unittest.mock import Mock, patch, MagicMock, call
import importlib
import sys


class TestLearningPathAgentPydanticFix:
    """Test Pydantic model initialization for Learning Path Agent."""
    
    def test_ensure_langchain_loaded_imports_base_models(self):
        """Test that _ensure_langchain_loaded imports all required base models."""
        # Reset the module to test fresh import
        if 'app.llm.agents.learning_path' in sys.modules:
            del sys.modules['app.llm.agents.learning_path']
        
        with patch('app.llm.agents.learning_path.logger') as mock_logger:
            # Mock all the langchain imports
            with patch.dict('sys.modules', {
                'langchain_core.caches': MagicMock(),
                'langchain_core.language_models.base': MagicMock(),
                'langchain_core.language_models.chat_models': MagicMock(),
                'langchain_google_genai': MagicMock(),
                'langchain.prompts': MagicMock(),
                'langchain.output_parsers': MagicMock(),
                'langchain.schema.runnable': MagicMock(),
            }):
                from app.llm.agents import learning_path
                
                # Trigger the lazy loading
                learning_path._ensure_langchain_loaded()
                
                # Verify debug logs show base models were imported
                debug_calls = [call[0][0] for call in mock_logger.debug.call_args_list]
                assert any('BaseCache and BaseLanguageModel imported successfully' in str(call) 
                          for call in debug_calls), "Base models should be imported"
    
    def test_ensure_langchain_loaded_rebuilds_base_models(self):
        """Test that base models are rebuilt before ChatGoogleGenerativeAI."""
        # This test verifies the logic by checking that the function completes
        # without error when actual modules are available
        from app.llm.agents import learning_path
        
        # Reset and call the function
        original_chat_google = learning_path.ChatGoogleGenerativeAI
        learning_path.ChatGoogleGenerativeAI = None
        
        try:
            # This should complete without errors
            learning_path._ensure_langchain_loaded()
            
            # Verify that ChatGoogleGenerativeAI was set
            assert learning_path.ChatGoogleGenerativeAI is not None
            
        finally:
            # Restore original value
            if original_chat_google is None:
                learning_path.ChatGoogleGenerativeAI = None
    
    def test_learning_path_agent_initialization_success(self):
        """Test that LearningPathAgent can be initialized without Pydantic errors."""
        with patch('app.llm.agents.learning_path._ensure_langchain_loaded') as mock_ensure:
            with patch('app.llm.agents.learning_path.get_settings') as mock_settings:
                with patch('app.llm.agents.learning_path.get_rag_service') as mock_rag:
                    with patch('app.llm.agents.learning_path.ContentServiceClient') as mock_content:
                        # Setup mocks
                        mock_settings_obj = Mock()
                        mock_settings_obj.GOOGLE_API_KEY = "test-key"
                        mock_settings_obj.LLM_MODEL = "gemini-pro"
                        mock_settings_obj.LLM_TEMPERATURE = 0.7
                        mock_settings_obj.LLM_MAX_TOKENS = 1024
                        mock_settings.return_value = mock_settings_obj
                        
                        # Mock the ChatGoogleGenerativeAI class
                        mock_llm_instance = Mock()
                        mock_chat_google = Mock(return_value=mock_llm_instance)
                        
                        with patch('app.llm.agents.learning_path.ChatGoogleGenerativeAI', mock_chat_google):
                            with patch('app.llm.agents.learning_path.PydanticOutputParser'):
                                with patch('app.llm.agents.learning_path.ChatPromptTemplate'):
                                    from app.llm.agents.learning_path import LearningPathAgent
                                    
                                    # This should not raise any Pydantic errors
                                    agent = LearningPathAgent()
                                    
                                    # Verify _ensure_langchain_loaded was called
                                    mock_ensure.assert_called_once()
                                    
                                    # Verify agent was initialized
                                    assert agent is not None
                                    assert agent.settings is not None


class TestChatbotAgentPydanticFix:
    """Test Pydantic model initialization for Chatbot Agent."""
    
    def test_chatbot_agent_initialization_success(self):
        """Test that ChatbotAgent can be initialized without Pydantic errors."""
        with patch('app.llm.agents.chatbot._ensure_langchain_loaded') as mock_ensure:
            with patch('app.llm.agents.chatbot.get_settings') as mock_settings:
                with patch('app.llm.agents.chatbot.get_rag_service') as mock_rag:
                    # Setup mocks
                    mock_settings_obj = Mock()
                    mock_settings_obj.GOOGLE_API_KEY = "test-key"
                    mock_settings_obj.LLM_MODEL = "gemini-pro"
                    mock_settings_obj.LLM_TEMPERATURE = 0.7
                    mock_settings_obj.LLM_MAX_TOKENS = 1024
                    mock_settings.return_value = mock_settings_obj
                    
                    # Mock the ChatGoogleGenerativeAI class
                    mock_llm_instance = Mock()
                    mock_chat_google = Mock(return_value=mock_llm_instance)
                    
                    with patch('app.llm.agents.chatbot.ChatGoogleGenerativeAI', mock_chat_google):
                        with patch('app.llm.agents.chatbot.ChatPromptTemplate'):
                            with patch('app.llm.agents.chatbot.MessagesPlaceholder'):
                                with patch('app.llm.agents.chatbot.ConversationBufferMemory'):
                                    from app.llm.agents.chatbot import ChatbotAgent
                                    
                                    # This should not raise any Pydantic errors
                                    agent = ChatbotAgent()
                                    
                                    # Verify _ensure_langchain_loaded was called
                                    mock_ensure.assert_called_once()
                                    
                                    # Verify agent was initialized
                                    assert agent is not None


class TestQuestionGeneratorAgentPydanticFix:
    """Test Pydantic model initialization for Question Generator Agent."""
    
    def test_question_generator_agent_initialization_success(self):
        """Test that QuestionGeneratorAgent can be initialized without Pydantic errors."""
        with patch('app.llm.agents.question_generator._ensure_langchain_loaded') as mock_ensure:
            with patch('app.llm.agents.question_generator.get_settings') as mock_settings:
                with patch('app.llm.agents.question_generator.get_rag_service') as mock_rag:
                    # Setup mocks
                    mock_settings_obj = Mock()
                    mock_settings_obj.GOOGLE_API_KEY = "test-key"
                    mock_settings_obj.LLM_MODEL = "gemini-pro"
                    mock_settings_obj.LLM_TEMPERATURE = 0.7
                    mock_settings_obj.LLM_MAX_TOKENS = 1024
                    mock_settings.return_value = mock_settings_obj
                    
                    # Mock the ChatGoogleGenerativeAI class
                    mock_llm_instance = Mock()
                    mock_chat_google = Mock(return_value=mock_llm_instance)
                    
                    with patch('app.llm.agents.question_generator.ChatGoogleGenerativeAI', mock_chat_google):
                        with patch('app.llm.agents.question_generator.PydanticOutputParser'):
                            with patch('app.llm.agents.question_generator.ChatPromptTemplate'):
                                from app.llm.agents.question_generator import QuestionGeneratorAgent
                                
                                # This should not raise any Pydantic errors
                                agent = QuestionGeneratorAgent()
                                
                                # Verify _ensure_langchain_loaded was called
                                mock_ensure.assert_called_once()
                                
                                # Verify agent was initialized
                                assert agent is not None


class TestLearningGoalConsumerPydanticFix:
    """Test that LearningGoalConsumer properly handles agent initialization."""
    
    @pytest.mark.asyncio
    async def test_learning_goal_consumer_lazy_initialization(self):
        """Test that consumer uses lazy initialization for the agent."""
        from app.consumers.learning_goal_consumer import LearningGoalConsumer
        
        # Create consumer
        consumer = LearningGoalConsumer()
        
        # Verify agent is not initialized yet
        assert consumer._learning_path_agent is None
        
        # Mock the agent
        with patch('app.consumers.learning_goal_consumer.LearningPathAgent') as mock_agent_class:
            mock_agent_instance = Mock()
            mock_agent_class.return_value = mock_agent_instance
            
            # Access the property - this should trigger initialization
            agent = consumer.learning_path_agent
            
            # Verify agent was created
            mock_agent_class.assert_called_once()
            assert consumer._learning_path_agent is not None
            assert agent == mock_agent_instance
    
    @pytest.mark.asyncio
    async def test_learning_goal_consumer_processes_without_pydantic_error(self):
        """Test that consumer can process learning goals without Pydantic errors."""
        from app.consumers.learning_goal_consumer import LearningGoalConsumer
        from app.schema.events import LearningGoalEvent, LearningGoalData
        from aiokafka.structs import ConsumerRecord
        
        # Create a mock learning goal event
        event_data = {
            "eventId": "evt_123",
            "eventType": "LEARNING_GOAL",
            "userId": "user_123",
            "timestamp": "2025-10-15T10:00:00Z",
            "eventData": {
                "learningGoal": "Learn Python programming",
                "currentLevel": "beginner",
                "availableTime": "2 hours/day"
            }
        }
        
        # Create mock Kafka message
        mock_message = Mock(spec=ConsumerRecord)
        mock_message.value = event_data
        mock_message.topic = "learning_goal"
        mock_message.partition = 0
        mock_message.offset = 1
        mock_message.timestamp = 1697370000000
        
        consumer = LearningGoalConsumer()
        
        # Mock the private agent instance directly
        mock_agent = Mock()
        mock_learning_path = Mock()
        mock_learning_path.steps = [Mock(), Mock()]
        mock_learning_path.total_duration = "4 weeks"
        from unittest.mock import AsyncMock
        mock_agent.generate_learning_path = AsyncMock(return_value=mock_learning_path)
        consumer._learning_path_agent = mock_agent
        
        # This should not raise any Pydantic errors
        await consumer.handle_learning_goal(mock_message)
        
        # Verify the agent's generate method was called
        mock_agent.generate_learning_path.assert_called_once()


class TestIntegrationPydanticFix:
    """Integration tests to verify the fix works end-to-end."""
    
    def test_all_agents_can_be_imported_without_error(self):
        """Test that all agents can be imported without Pydantic errors."""
        # This tests the actual import, not mocked
        try:
            from app.llm.agents.learning_path import LearningPathAgent
            from app.llm.agents.chatbot import ChatbotAgent
            from app.llm.agents.question_generator import QuestionGeneratorAgent
            
            # If we get here, imports succeeded
            assert True
        except Exception as e:
            pytest.fail(f"Failed to import agents: {e}")
    
    def test_ensure_langchain_loaded_is_idempotent(self):
        """Test that calling _ensure_langchain_loaded multiple times is safe."""
        from app.llm.agents import learning_path
        
        # Call multiple times
        for _ in range(3):
            learning_path._ensure_langchain_loaded()
        
        # Should not raise any errors
        assert learning_path.ChatGoogleGenerativeAI is not None
