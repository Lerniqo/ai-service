"""
Tests for LLM module

Run with: pytest tests/test_llm.py -v
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from app.llm.main import LLMService, get_llm_service
from app.llm.rag import RAGService
from app.llm.agents.learning_path import LearningPathAgent, LearningPath
from app.llm.agents.question_generator import QuestionGeneratorAgent, QuestionSet
from app.llm.agents.chatbot import ChatbotAgent


class TestRAGService:
    """Tests for RAG service."""
    
    @patch('app.llm.rag.OpenAIEmbeddings')
    @patch('app.llm.rag.Chroma')
    def test_rag_initialization(self, mock_chroma, mock_embeddings):
        """Test RAG service initialization."""
        rag_service = RAGService()
        assert rag_service.embeddings is None
        assert rag_service.vector_store is None
        
        # Initialize
        rag_service._initialize_embeddings()
        assert rag_service.embeddings is not None
    
    @patch('app.llm.rag.OpenAIEmbeddings')
    @patch('app.llm.rag.Chroma')
    def test_load_text_data(self, mock_chroma, mock_embeddings):
        """Test loading text data into RAG."""
        rag_service = RAGService()
        
        texts = ["Sample text 1", "Sample text 2"]
        metadatas = [{"source": "test1"}, {"source": "test2"}]
        
        # Mock the vector store
        mock_vs = Mock()
        mock_vs.add_documents = Mock(return_value=None)
        mock_chroma.return_value = mock_vs
        
        # This would normally add to vector store
        # In test, we just verify the flow works
        with patch.object(rag_service, '_initialize_vector_store'):
            with patch.object(rag_service.text_splitter, 'split_documents', return_value=[Mock(), Mock()]):
                rag_service.vector_store = mock_vs
                result = rag_service.load_text_data(texts, metadatas)
                assert result == 2


class TestLearningPathAgent:
    """Tests for Learning Path Agent."""
    
    @patch('app.llm.agents.learning_path.ChatOpenAI')
    @patch('app.llm.agents.learning_path.get_rag_service')
    def test_agent_initialization(self, mock_rag, mock_llm):
        """Test learning path agent initialization."""
        mock_rag.return_value = Mock()
        agent = LearningPathAgent()
        assert agent.llm is not None
        assert agent.prompt is not None
    
    @patch('app.llm.agents.learning_path.ChatOpenAI')
    @patch('app.llm.agents.learning_path.get_rag_service')
    def test_generate_learning_path(self, mock_rag, mock_llm):
        """Test learning path generation."""
        # Mock RAG service
        mock_rag_instance = Mock()
        mock_retriever = Mock()
        mock_retriever.get_relevant_documents.return_value = []
        mock_rag_instance.get_retriever.return_value = mock_retriever
        mock_rag.return_value = mock_rag_instance
        
        # Mock LLM response
        mock_llm_instance = Mock()
        mock_llm.return_value = mock_llm_instance
        
        agent = LearningPathAgent()
        
        # This would normally call the LLM
        # In production, you'd need a valid API key
        # For testing, we verify the setup is correct
        assert agent.learning_path_agent is not None


class TestQuestionGeneratorAgent:
    """Tests for Question Generator Agent."""
    
    @patch('app.llm.agents.question_generator.ChatOpenAI')
    @patch('app.llm.agents.question_generator.get_rag_service')
    def test_agent_initialization(self, mock_rag, mock_llm):
        """Test question generator agent initialization."""
        mock_rag.return_value = Mock()
        agent = QuestionGeneratorAgent()
        assert agent.llm is not None
        assert agent.prompt is not None
        assert agent.output_parser is not None


class TestChatbotAgent:
    """Tests for Chatbot Agent."""
    
    @patch('app.llm.agents.chatbot.ChatOpenAI')
    @patch('app.llm.agents.chatbot.get_rag_service')
    def test_agent_initialization(self, mock_rag, mock_llm):
        """Test chatbot agent initialization."""
        mock_rag.return_value = Mock()
        agent = ChatbotAgent(session_id="test_session")
        assert agent.session_id == "test_session"
        assert agent.llm is not None
        assert agent.memory is not None
    
    @patch('app.llm.agents.chatbot.ChatOpenAI')
    @patch('app.llm.agents.chatbot.get_rag_service')
    def test_chat_history(self, mock_rag, mock_llm):
        """Test chat history management."""
        mock_rag.return_value = Mock()
        agent = ChatbotAgent()
        
        # Initially empty
        history = agent.get_history()
        assert len(history) == 0
        
        # Clear history
        agent.clear_history()
        history = agent.get_history()
        assert len(history) == 0


class TestLLMService:
    """Tests for main LLM Service."""
    
    def test_service_initialization(self):
        """Test LLM service initialization."""
        service = LLMService()
        assert service.rag_service is not None
        assert service._learning_path_agent is None
        assert service._question_generator_agent is None
        assert len(service._chatbot_sessions) == 0
    
    @patch('app.llm.main.LearningPathAgent')
    def test_lazy_agent_loading(self, mock_agent):
        """Test lazy loading of agents."""
        service = LLMService()
        
        # Agent not created yet
        assert service._learning_path_agent is None
        
        # Access agent
        agent = service.learning_path_agent
        
        # Now it should be created
        assert service._learning_path_agent is not None
    
    @patch('app.llm.main.ChatbotAgent')
    def test_chatbot_session_management(self, mock_chatbot):
        """Test chatbot session management."""
        mock_chatbot.return_value = Mock()
        service = LLMService()
        
        # Get chatbot for session
        chatbot1 = service.get_chatbot_agent("session1")
        assert "session1" in service._chatbot_sessions
        
        # Get same session again
        chatbot2 = service.get_chatbot_agent("session1")
        assert chatbot1 is chatbot2
        
        # Get different session
        chatbot3 = service.get_chatbot_agent("session2")
        assert "session2" in service._chatbot_sessions
        assert chatbot3 is not chatbot1
    
    def test_knowledge_base_operations(self):
        """Test knowledge base operations."""
        service = LLMService()
        
        # Test stats
        stats = service.get_knowledge_base_stats()
        assert "status" in stats


@pytest.mark.integration
class TestLLMIntegration:
    """Integration tests requiring API keys."""
    
    @pytest.mark.skipif(
        not pytest.config.getoption("--run-integration"),
        reason="Requires --run-integration flag and API keys"
    )
    def test_full_learning_path_generation(self):
        """Test full learning path generation with real API."""
        service = get_llm_service()
        
        learning_path = service.generate_learning_path(
            goal="Learn Python basics",
            current_level="beginner"
        )
        
        assert isinstance(learning_path, LearningPath)
        assert len(learning_path.steps) > 0
        assert learning_path.goal is not None
    
    @pytest.mark.skipif(
        not pytest.config.getoption("--run-integration"),
        reason="Requires --run-integration flag and API keys"
    )
    def test_full_question_generation(self):
        """Test full question generation with real API."""
        service = get_llm_service()
        
        questions = service.generate_questions(
            topic="Python variables",
            num_questions=3
        )
        
        assert isinstance(questions, QuestionSet)
        assert len(questions.questions) == 3
    
    @pytest.mark.skipif(
        not pytest.config.getoption("--run-integration"),
        reason="Requires --run-integration flag and API keys"
    )
    def test_full_chatbot_conversation(self):
        """Test full chatbot conversation with real API."""
        service = get_llm_service()
        
        response = service.chat(
            message="What is Python?",
            session_id="test_integration"
        )
        
        assert isinstance(response, str)
        assert len(response) > 0
        
        # Check history
        history = service.get_chat_history("test_integration")
        assert len(history) > 0


def pytest_addoption(parser):
    """Add custom pytest options."""
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests that require API keys"
    )
