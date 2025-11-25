import pytest
import asyncio
import sys
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Dict, Any, List, Optional
import json
from pathlib import Path

# Adicionar diretório raiz ao PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock modules before importing
sys.modules['customtkinter'] = MagicMock()
sys.modules['customtkinter.windows'] = MagicMock()
sys.modules['customtkinter.windows.ctk_tk'] = MagicMock()
sys.modules['customtkinter.windows.widgets'] = MagicMock()

from src.assistant.virtual_assistant import VirtualAssistant, IntentRecognizer, ConversationManager
from src.assistant.intents import IntentHandler, BaseIntent
from src.llm.router import LLMRouter, LLMResponse
from src.rag.vector_store import VectorStore
from src.scraping.scraper import WebScraper
from src.sheets.sync_manager import GoogleSheetsSync
from src.utils.config import Config


@pytest.fixture
def mock_config():
    """Mock configuration"""
    config = Mock(spec=Config)
    config.base_dir = "/tmp/test"
    config.config_dir = "/tmp/test/config"
    config.data_dir = "/tmp/test/data"
    config.logs_dir = "/tmp/test/logs"
    return config


@pytest.fixture
def mock_llm_router():
    """Mock LLM router"""
    router = Mock(spec=LLMRouter)
    
    async def mock_generate_response(prompt: str, preferred_provider: Optional[str] = None) -> LLMResponse:
        return LLMResponse(
            content=f"Mock response to: {prompt}",
            provider="openai",
            model="gpt-3.5-turbo",
            prompt_tokens=10,
            response_tokens=20,
            total_tokens=30
        )
    
    router.generate_response = AsyncMock(side_effect=mock_generate_response)
    router.select_provider = Mock(return_value="openai")
    return router


@pytest.fixture
def mock_vector_store():
    """Mock vector store"""
    store = Mock(spec=VectorStore)
    
    async def mock_search_similar(query: str, k: int = 5) -> List[Dict[str, Any]]:
        return [
            {"content": f"Similar content {i} for {query}", "metadata": {"score": 0.9 - i * 0.1}}
            for i in range(k)
        ]
    
    store.search_similar = AsyncMock(side_effect=mock_search_similar)
    store.add_documents = AsyncMock(return_value=True)
    return store


@pytest.fixture
def mock_scraper():
    """Mock web scraper"""
    scraper = Mock(spec=WebScraper)
    
    async def mock_scrape_url(url: str, selectors: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        return {
            "url": url,
            "title": f"Title for {url}",
            "content": f"Content from {url}",
            "scraped_at": "2024-01-01T00:00:00Z",
            "selectors": selectors or {}
        }
    
    scraper.scrape_url = AsyncMock(side_effect=mock_scrape_url)
    scraper.scrape_multiple = AsyncMock(return_value=[
        {"url": "https://example1.com", "title": "Title 1"},
        {"url": "https://example2.com", "title": "Title 2"}
    ])
    return scraper


@pytest.fixture
def mock_sheets_manager():
    """Mock Google Sheets manager"""
    sheets = Mock(spec=GoogleSheetsSync)
    sheets.is_configured = Mock(return_value=True)
    sheets.sync_scraping_data = AsyncMock(return_value=True)
    sheets.sync_rag_data = AsyncMock(return_value=True)
    sheets.sync_llm_interactions = AsyncMock(return_value=True)
    return sheets


@pytest.fixture
def intent_recognizer(mock_llm_router):
    """Create intent recognizer with mocked LLM"""
    recognizer = IntentRecognizer(mock_llm_router)
    return recognizer


@pytest.fixture
def conversation_manager(mock_llm_router, mock_vector_store):
    """Create conversation manager with mocked dependencies"""
    manager = ConversationManager(mock_llm_router, mock_vector_store)
    return manager


@pytest.fixture
def virtual_assistant(mock_config, mock_llm_router, mock_vector_store, mock_scraper, mock_sheets_manager):
    """Create virtual assistant with mocked dependencies"""
    assistant = VirtualAssistant(
        config=mock_config,
        llm_router=mock_llm_router,
        vector_store=mock_vector_store,
        scraper=mock_scraper,
        sheets_manager=mock_sheets_manager
    )
    return assistant


class TestIntentRecognizer:
    """Test cases for Intent Recognizer"""
    
    def test_initialization(self, mock_llm_router):
        """Test proper initialization"""
        recognizer = IntentRecognizer(mock_llm_router)
        assert recognizer.llm_router == mock_llm_router
        assert recognizer.intent_patterns is not None
    
    def test_recognize_intent_scraping(self, intent_recognizer):
        """Test scraping intent recognition"""
        test_cases = [
            "scrape https://example.com",
            "extract data from https://test.com",
            "get content from website",
            "collect information from URL"
        ]
        
        for message in test_cases:
            intent = intent_recognizer.recognize_intent(message)
            assert intent["type"] == "scraping"
            assert "confidence" in intent
            assert intent["confidence"] > 0.5
    
    def test_recognize_intent_rag_search(self, intent_recognizer):
        """Test RAG search intent recognition"""
        test_cases = [
            "search for information about machine learning",
            "find documents about Python programming",
            "what do you know about artificial intelligence",
            "search in my documents"
        ]
        
        for message in test_cases:
            intent = intent_recognizer.recognize_intent(message)
            assert intent["type"] == "rag_search"
            assert "confidence" in intent
            assert intent["confidence"] > 0.5
    
    def test_recognize_intent_llm_query(self, intent_recognizer):
        """Test LLM query intent recognition"""
        test_cases = [
            "explain quantum computing",
            "what is the capital of France",
            "help me write a Python function",
            "generate a summary of this text"
        ]
        
        for message in test_cases:
            intent = intent_recognizer.recognize_intent(message)
            assert intent["type"] == "llm_query"
            assert "confidence" in intent
            assert intent["confidence"] > 0.5
    
    def test_recognize_intent_greeting(self, intent_recognizer):
        """Test greeting intent recognition"""
        test_cases = [
            "hello",
            "hi there",
            "good morning",
            "hey, how are you"
        ]
        
        for message in test_cases:
            intent = intent_recognizer.recognize_intent(message)
            assert intent["type"] == "greeting"
            assert "confidence" in intent
            assert intent["confidence"] > 0.5
    
    def test_recognize_intent_unknown(self, intent_recognizer):
        """Test unknown intent recognition"""
        test_cases = [
            "asdfghjkl",
            "random text with no meaning",
            "",
            "   "
        ]
        
        for message in test_cases:
            intent = intent_recognizer.recognize_intent(message)
            assert intent["type"] == "unknown"
            assert "confidence" in intent
            assert intent["confidence"] < 0.5
    
    def test_extract_entities_url(self, intent_recognizer):
        """Test URL entity extraction"""
        message = "scrape https://example.com and https://test.com"
        entities = intent_recognizer.extract_entities(message)
        assert "urls" in entities
        assert len(entities["urls"]) == 2
        assert "https://example.com" in entities["urls"]
        assert "https://test.com" in entities["urls"]
    
    def test_extract_entities_keywords(self, intent_recognizer):
        """Test keyword extraction"""
        message = "search for machine learning and artificial intelligence"
        entities = intent_recognizer.extract_entities(message)
        assert "keywords" in entities
        assert "machine learning" in entities["keywords"]
        assert "artificial intelligence" in entities["keywords"]
    
    def test_intent_confidence_scoring(self, intent_recognizer):
        """Test confidence scoring for intents"""
        # Clear intent should have high confidence
        intent = intent_recognizer.recognize_intent("scrape https://example.com")
        assert intent["confidence"] > 0.8
        
        # Ambiguous intent should have lower confidence
        intent = intent_recognizer.recognize_intent("do something with data")
        assert intent["confidence"] < 0.7


class TestConversationManager:
    """Test cases for Conversation Manager"""
    
    def test_initialization(self, mock_llm_router, mock_vector_store):
        """Test proper initialization"""
        manager = ConversationManager(mock_llm_router, mock_vector_store)
        assert manager.llm_router == mock_llm_router
        assert manager.vector_store == mock_vector_store
        assert manager.conversation_history == []
        assert manager.context_window == 10
    
    def test_add_message_to_history(self, conversation_manager):
        """Test adding messages to conversation history"""
        conversation_manager.add_message("user", "Hello, how are you?")
        conversation_manager.add_message("assistant", "I'm doing well, thank you!")
        
        assert len(conversation_manager.conversation_history) == 2
        assert conversation_manager.conversation_history[0]["role"] == "user"
        assert conversation_manager.conversation_history[0]["content"] == "Hello, how are you?"
        assert conversation_manager.conversation_history[1]["role"] == "assistant"
        assert conversation_manager.conversation_history[1]["content"] == "I'm doing well, thank you!"
    
    def test_get_conversation_context(self, conversation_manager):
        """Test getting conversation context"""
        # Add multiple messages
        for i in range(15):
            conversation_manager.add_message("user" if i % 2 == 0 else "assistant", f"Message {i}")
        
        context = conversation_manager.get_conversation_context()
        assert len(context) == 10  # Should be limited by context_window
        assert context[0]["content"] == "Message 5"  # Should start from the 5th message
        assert context[-1]["content"] == "Message 14"  # Should end with the last message
    
    @pytest.mark.asyncio
    async def test_generate_contextual_response(self, conversation_manager):
        """Test generating contextual response"""
        # Add conversation history
        conversation_manager.add_message("user", "What is Python?")
        conversation_manager.add_message("assistant", "Python is a programming language.")
        conversation_manager.add_message("user", "What are its main features?")
        
        response = await conversation_manager.generate_contextual_response("What are its main features?")
        
        assert isinstance(response, str)
        assert len(response) > 0
        assert "Mock response to:" in response
    
    def test_clear_conversation_history(self, conversation_manager):
        """Test clearing conversation history"""
        conversation_manager.add_message("user", "Hello")
        conversation_manager.add_message("assistant", "Hi there")
        
        assert len(conversation_manager.conversation_history) == 2
        
        conversation_manager.clear_conversation_history()
        assert len(conversation_manager.conversation_history) == 0
    
    def test_set_context_window(self, conversation_manager):
        """Test setting context window size"""
        conversation_manager.set_context_window(5)
        assert conversation_manager.context_window == 5
        
        # Add more messages than context window
        for i in range(10):
            conversation_manager.add_message("user", f"Message {i}")
        
        context = conversation_manager.get_conversation_context()
        assert len(context) == 5
    
    @pytest.mark.asyncio
    async def test_enhance_prompt_with_context(self, conversation_manager):
        """Test prompt enhancement with conversation context"""
        conversation_manager.add_message("user", "Explain machine learning")
        conversation_manager.add_message("assistant", "Machine learning is a subset of AI")
        conversation_manager.add_message("user", "What about deep learning?")
        
        enhanced_prompt = await conversation_manager.enhance_prompt_with_context("What about deep learning?")
        
        assert isinstance(enhanced_prompt, str)
        assert "Machine learning is a subset of AI" in enhanced_prompt
        assert "What about deep learning?" in enhanced_prompt


class TestVirtualAssistant:
    """Test cases for Virtual Assistant"""
    
    def test_initialization(self, virtual_assistant):
        """Test proper initialization"""
        assert virtual_assistant.config is not None
        assert virtual_assistant.llm_router is not None
        assert virtual_assistant.vector_store is not None
        assert virtual_assistant.scraper is not None
        assert virtual_assistant.sheets_manager is not None
        assert virtual_assistant.intent_recognizer is not None
        assert virtual_assistant.conversation_manager is not None
        assert virtual_assistant.is_running is False
    
    @pytest.mark.asyncio
    async def test_process_greeting_intent(self, virtual_assistant):
        """Test processing greeting intent"""
        result = await virtual_assistant.process_message("Hello!")
        
        assert isinstance(result, dict)
        assert result["success"] is True
        assert result["intent_type"] == "greeting"
        assert "response" in result
        assert len(result["response"]) > 0
        assert "greeting" in result["response"].lower() or "hello" in result["response"].lower()
    
    @pytest.mark.asyncio
    async def test_process_scraping_intent(self, virtual_assistant):
        """Test processing scraping intent"""
        result = await virtual_assistant.process_message("scrape https://example.com")
        
        assert isinstance(result, dict)
        assert result["success"] is True
        assert result["intent_type"] == "scraping"
        assert "response" in result
        assert "scraped" in result["response"].lower() or "content" in result["response"].lower()
        
        # Verify scraper was called
        virtual_assistant.scraper.scrape_url.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_rag_search_intent(self, virtual_assistant):
        """Test processing RAG search intent"""
        result = await virtual_assistant.process_message("search for information about Python programming")
        
        assert isinstance(result, dict)
        assert result["success"] is True
        assert result["intent_type"] == "rag_search"
        assert "response" in result
        assert len(result["response"]) > 0
        
        # Verify vector store was called
        virtual_assistant.vector_store.search_similar.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_llm_query_intent(self, virtual_assistant):
        """Test processing LLM query intent"""
        result = await virtual_assistant.process_message("explain quantum computing")
        
        assert isinstance(result, dict)
        assert result["success"] is True
        assert result["intent_type"] == "llm_query"
        assert "response" in result
        assert len(result["response"]) > 0
        assert "quantum" in result["response"].lower()
        
        # Verify LLM router was called
        virtual_assistant.llm_router.generate_response.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_unknown_intent(self, virtual_assistant):
        """Test processing unknown intent"""
        result = await virtual_assistant.process_message("asdfghjkl")
        
        assert isinstance(result, dict)
        assert result["success"] is True
        assert result["intent_type"] == "unknown"
        assert "response" in result
        assert len(result["response"]) > 0
        assert "understand" in result["response"].lower() or "clarify" in result["response"].lower()
    
    @pytest.mark.asyncio
    async def test_process_message_with_error(self, virtual_assistant):
        """Test error handling during message processing"""
        # Make scraper raise an exception
        virtual_assistant.scraper.scrape_url.side_effect = Exception("Scraping error")
        
        result = await virtual_assistant.process_message("scrape https://example.com")
        
        assert isinstance(result, dict)
        assert result["success"] is False
        assert "error" in result
        assert "Scraping error" in result["error"]
    
    def test_start_assistant(self, virtual_assistant):
        """Test starting the assistant"""
        virtual_assistant.start()
        assert virtual_assistant.is_running is True
    
    def test_stop_assistant(self, virtual_assistant):
        """Test stopping the assistant"""
        virtual_assistant.start()
        assert virtual_assistant.is_running is True
        
        virtual_assistant.stop()
        assert virtual_assistant.is_running is False
    
    def test_get_assistant_status(self, virtual_assistant):
        """Test getting assistant status"""
        status = virtual_assistant.get_status()
        
        assert isinstance(status, dict)
        assert "is_running" in status
        assert "conversation_length" in status
        assert "vector_store_status" in status
        assert "sheets_configured" in status
    
    @pytest.mark.asyncio
    async def test_conversation_context_persistence(self, virtual_assistant):
        """Test that conversation context is maintained across messages"""
        # First message
        result1 = await virtual_assistant.process_message("What is Python?")
        assert result1["success"] is True
        
        # Second message that references the first
        result2 = await virtual_assistant.process_message("Tell me more about its features")
        assert result2["success"] is True
        
        # Verify conversation history has both messages
        assert len(virtual_assistant.conversation_manager.conversation_history) >= 2
    
    @pytest.mark.asyncio
    async def test_sheets_sync_integration(self, virtual_assistant):
        """Test that successful operations sync to Google Sheets"""
        # Process a message that should trigger sheets sync
        result = await virtual_assistant.process_message("scrape https://example.com")
        
        assert result["success"] is True
        
        # Verify sheets sync was called (if configured)
        if virtual_assistant.sheets_manager.is_configured():
            virtual_assistant.sheets_manager.sync_scraping_data.assert_called_once()
    
    def test_reset_conversation(self, virtual_assistant):
        """Test resetting conversation history"""
        virtual_assistant.conversation_manager.add_message("user", "Hello")
        virtual_assistant.conversation_manager.add_message("assistant", "Hi")
        
        assert len(virtual_assistant.conversation_manager.conversation_history) == 2
        
        virtual_assistant.reset_conversation()
        assert len(virtual_assistant.conversation_manager.conversation_history) == 0
    
    @pytest.mark.asyncio
    async def test_concurrent_message_processing(self, virtual_assistant):
        """Test handling concurrent messages"""
        messages = [
            "Hello",
            "scrape https://example1.com",
            "search for Python tutorials",
            "explain machine learning"
        ]
        
        # Process messages concurrently
        tasks = [virtual_assistant.process_message(msg) for msg in messages]
        results = await asyncio.gather(*tasks)
        
        # All messages should be processed successfully
        assert len(results) == len(messages)
        for result in results:
            assert isinstance(result, dict)
            assert "success" in result
            assert "response" in result


class TestIntentHandlers:
    """Test cases for Intent Handlers"""
    
    def test_base_intent_initialization(self):
        """Test base intent handler initialization"""
        base_intent = BaseIntent()
        assert hasattr(base_intent, 'process')
        assert hasattr(base_intent, 'get_name')
        assert base_intent.get_name() == "base"
    
    @pytest.mark.asyncio
    async def test_intent_handler_registration(self, virtual_assistant):
        """Test registering custom intent handlers"""
        class CustomIntentHandler(BaseIntent):
            def get_name(self):
                return "custom"
            
            async def process(self, message: str, entities: Dict[str, Any]) -> Dict[str, Any]:
                return {
                    "success": True,
                    "response": "Custom intent processed",
                    "data": {"original_message": message}
                }
        
        # Register custom handler
        virtual_assistant.register_intent_handler("custom", CustomIntentHandler())
        
        # Test processing with custom intent
        result = await virtual_assistant._process_intent({"type": "custom"}, "test message")
        assert result["success"] is True
        assert result["response"] == "Custom intent processed"


class TestVirtualAssistantIntegration:
    """Integration tests for Virtual Assistant"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_conversation_workflow(self, virtual_assistant):
        """Test complete conversation workflow"""
        conversation_flow = [
            ("Hello!", "greeting"),
            ("scrape https://python.org", "scraping"),
            ("search for Python documentation", "rag_search"),
            ("explain what you found", "llm_query"),
            ("Goodbye!", "greeting")
        ]
        
        results = []
        for message, expected_intent in conversation_flow:
            result = await virtual_assistant.process_message(message)
            results.append(result)
            
            assert result["success"] is True
            assert result["intent_type"] == expected_intent
            assert len(result["response"]) > 0
        
        # Verify conversation history was maintained
        assert len(virtual_assistant.conversation_manager.conversation_history) > 0
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self, virtual_assistant):
        """Test error recovery during conversation"""
        # First, make scraper fail
        virtual_assistant.scraper.scrape_url.side_effect = Exception("Temporary error")
        
        # Try scraping - should fail
        result1 = await virtual_assistant.process_message("scrape https://example.com")
        assert result1["success"] is False
        
        # Fix the scraper
        virtual_assistant.scraper.scrape_url.side_effect = None
        virtual_assistant.scraper.scrape_url = AsyncMock(return_value={
            "url": "https://example.com",
            "title": "Example",
            "content": "Content",
            "scraped_at": "2024-01-01T00:00:00Z"
        })
        
        # Try again - should succeed
        result2 = await virtual_assistant.process_message("scrape https://example.com")
        assert result2["success"] is True
    
    @pytest.mark.integration
    def test_assistant_lifecycle(self, virtual_assistant):
        """Test assistant start/stop lifecycle"""
        # Start assistant
        virtual_assistant.start()
        assert virtual_assistant.is_running is True
        status = virtual_assistant.get_status()
        assert status["is_running"] is True
        
        # Stop assistant
        virtual_assistant.stop()
        assert virtual_assistant.is_running is False
        status = virtual_assistant.get_status()
        assert status["is_running"] is False