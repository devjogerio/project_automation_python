import pytest
import asyncio
import sys
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Dict, Any, List
import tempfile
import json
from pathlib import Path

# Adicionar diretório raiz ao PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import all main modules for integration testing
from src.main import AutomationSystem
from src.utils.config import Config
from src.scraping.scraper import WebScraper
from src.rag.vector_store import VectorStore
from src.llm.router import LLMRouter
from src.assistant.virtual_assistant import VirtualAssistant
from src.sheets.sync_manager import GoogleSheetsSync


@pytest.fixture
def temp_config_dir():
    """Create temporary configuration directory"""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir) / "config"
        config_dir.mkdir(exist_ok=True)
        
        # Create test configuration files
        config_file = config_dir / "config.yaml"
        config_data = {
            "scraping": {
                "default_timeout": 30,
                "max_retries": 3,
                "user_agent": "TestBot/1.0",
                "respect_robots_txt": True
            },
            "llm": {
                "default_provider": "openai",
                "openai": {
                    "api_key": "test-openai-key",
                    "model": "gpt-3.5-turbo"
                },
                "llama": {
                    "model_path": "/tmp/test/llama-model.gguf",
                    "context_length": 4096
                }
            },
            "rag": {
                "vector_store_path": "/tmp/test/vector_store",
                "embedding_model": "all-MiniLM-L6-v2",
                "max_results": 5
            },
            "sheets": {
                "spreadsheet_id": "test-spreadsheet-id",
                "credentials_file": "/tmp/test/credentials.json"
            },
            "logging": {
                "level": "INFO",
                "file": "/tmp/test/logs/automation.log"
            }
        }
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        yield temp_dir


@pytest.fixture
def mock_services():
    """Create mock services for integration testing"""
    services = {}
    
    # Mock WebScraper
    scraper = Mock(spec=WebScraper)
    async def mock_scrape_url(url: str, selectors: Dict[str, str] = None) -> Dict[str, Any]:
        return {
            "url": url,
            "title": f"Title for {url}",
            "content": f"Content from {url}",
            "scraped_at": "2024-01-01T00:00:00Z",
            "status_code": 200,
            "error": None
        }
    scraper.scrape_url = AsyncMock(side_effect=mock_scrape_url)
    scraper.scrape_multiple = AsyncMock(return_value=[
        {"url": "https://example1.com", "title": "Example 1"},
        {"url": "https://example2.com", "title": "Example 2"}
    ])
    services['scraper'] = scraper
    
    # Mock VectorStore
    vector_store = Mock(spec=VectorStore)
    async def mock_search_similar(query: str, k: int = 5) -> List[Dict[str, Any]]:
        return [
            {"content": f"Similar content {i} for {query}", "metadata": {"score": 0.9 - i * 0.1}}
            for i in range(k)
        ]
    vector_store.search_similar = AsyncMock(side_effect=mock_search_similar)
    vector_store.add_documents = AsyncMock(return_value=True)
    vector_store.get_collection_stats = Mock(return_value={"documents": 100, "size_mb": 50.5})
    services['vector_store'] = vector_store
    
    # Mock LLMRouter
    llm_router = Mock(spec=LLMRouter)
    async def mock_generate_response(prompt: str, preferred_provider: str = None):
        from src.llm.router import LLMResponse
        return LLMResponse(
            content=f"Mock response to: {prompt[:50]}...",
            provider=preferred_provider or "openai",
            model="gpt-3.5-turbo",
            prompt_tokens=10,
            response_tokens=25,
            total_tokens=35
        )
    llm_router.generate_response = AsyncMock(side_effect=mock_generate_response)
    llm_router.select_provider = Mock(return_value="openai")
    services['llm_router'] = llm_router
    
    # Mock GoogleSheetsSync
    sheets_manager = Mock(spec=GoogleSheetsSync)
    sheets_manager.is_configured = Mock(return_value=True)
    sheets_manager.sync_scraping_data = AsyncMock(return_value=True)
    sheets_manager.sync_rag_data = AsyncMock(return_value=True)
    sheets_manager.sync_llm_interactions = AsyncMock(return_value=True)
    services['sheets_manager'] = sheets_manager
    
    return services


@pytest.fixture
def automation_system(temp_config_dir, mock_services):
    """Create automation system with mocked services"""
    with patch('src.main.WebScraper', return_value=mock_services['scraper']):
        with patch('src.main.VectorStore', return_value=mock_services['vector_store']):
            with patch('src.main.LLMRouter', return_value=mock_services['llm_router']):
                with patch('src.main.GoogleSheetsSync', return_value=mock_services['sheets_manager']):
                    system = AutomationSystem(
                        config_path=Path(temp_config_dir) / "config" / "config.yaml",
                        headless=True,
                        log_level="INFO"
                    )
                    yield system


class TestSystemIntegration:
    """Integration tests for the complete automation system"""
    
    def test_system_initialization(self, automation_system):
        """Test system initialization and component setup"""
        assert automation_system.config is not None
        assert automation_system.scraper is not None
        assert automation_system.vector_store is not None
        assert automation_system.llm_router is not None
        assert automation_system.assistant is not None
        assert automation_system.sheets_manager is not None
        assert automation_system.logger is not None
    
    def test_system_configuration_loading(self, automation_system):
        """Test configuration loading and validation"""
        config = automation_system.config
        assert hasattr(config, 'scraping_config')
        assert hasattr(config, 'llm_config')
        assert hasattr(config, 'rag_config')
        assert hasattr(config, 'sheets_config')
        assert hasattr(config, 'logging_config')
        
        # Verify specific configuration values
        assert config.scraping_config['default_timeout'] == 30
        assert config.llm_config['default_provider'] == 'openai'
        assert config.rag_config['max_results'] == 5
    
    @pytest.mark.asyncio
    async def test_scraping_to_vector_store_workflow(self, automation_system):
        """Test complete workflow from scraping to vector storage"""
        # Scrape a URL
        scrape_result = await automation_system.scraper.scrape_url("https://example.com")
        assert scrape_result['success'] is True
        assert scrape_result['content'] is not None
        
        # Store in vector database
        documents = [{
            "content": scrape_result['content'],
            "metadata": {
                "url": scrape_result['url'],
                "title": scrape_result['title'],
                "scraped_at": scrape_result['scraped_at']
            }
        }]
        
        store_result = await automation_system.vector_store.add_documents(documents)
        assert store_result is True
        
        # Search for the content
        search_results = await automation_system.vector_store.search_similar("example content", k=1)
        assert len(search_results) > 0
        assert 'example' in search_results[0]['content'].lower()
    
    @pytest.mark.asyncio
    async def test_assistant_conversation_workflow(self, automation_system):
        """Test complete assistant conversation workflow"""
        assistant = automation_system.assistant
        
        # Test greeting
        greeting_result = await assistant.process_message("Hello!")
        assert greeting_result['success'] is True
        assert greeting_result['intent_type'] == 'greeting'
        assert len(greeting_result['response']) > 0
        
        # Test scraping request
        scrape_result = await assistant.process_message("scrape https://python.org")
        assert scrape_result['success'] is True
        assert scrape_result['intent_type'] == 'scraping'
        assert 'scraped' in scrape_result['response'].lower() or 'content' in scrape_result['response'].lower()
        
        # Test RAG search
        rag_result = await assistant.process_message("search for Python documentation")
        assert rag_result['success'] is True
        assert rag_result['intent_type'] == 'rag_search'
        assert len(rag_result['response']) > 0
        
        # Test LLM query
        llm_result = await assistant.process_message("explain what Python is")
        assert llm_result['success'] is True
        assert llm_result['intent_type'] == 'llm_query'
        assert 'python' in llm_result['response'].lower()
    
    @pytest.mark.asyncio
    async def test_google_sheets_sync_workflow(self, automation_system):
        """Test Google Sheets synchronization workflow"""
        sheets_manager = automation_system.sheets_manager
        
        # Test scraping data sync
        scraping_data = {
            "url": "https://example.com",
            "title": "Example Page",
            "content": "Test content",
            "scraped_at": "2024-01-01T12:00:00Z"
        }
        
        sync_result = await sheets_manager.sync_scraping_data(scraping_data)
        assert sync_result is True
        
        # Test RAG data sync
        rag_data = {
            "query": "test query",
            "results": [
                {"content": "Result 1", "metadata": {"score": 0.9}},
                {"content": "Result 2", "metadata": {"score": 0.8}}
            ]
        }
        
        sync_result = await sheets_manager.sync_rag_data(rag_data)
        assert sync_result is True
        
        # Test LLM interaction sync
        llm_data = {
            "prompt": "test prompt",
            "response": "test response",
            "provider": "openai",
            "model": "gpt-3.5-turbo",
            "timestamp": "2024-01-01T12:00:00Z"
        }
        
        sync_result = await sheets_manager.sync_llm_interactions(llm_data)
        assert sync_result is True
    
    @pytest.mark.asyncio
    async def test_error_handling_across_modules(self, automation_system):
        """Test error handling across different modules"""
        # Test scraper error handling
        automation_system.scraper.scrape_url.side_effect = Exception("Network error")
        
        with pytest.raises(Exception):
            await automation_system.scraper.scrape_url("https://example.com")
        
        # Reset scraper
        automation_system.scraper.scrape_url.side_effect = None
        
        # Test LLM error handling
        automation_system.llm_router.generate_response.side_effect = Exception("API error")
        
        with pytest.raises(Exception):
            await automation_system.llm_router.generate_response("test prompt")
        
        # Reset LLM router
        automation_system.llm_router.generate_response.side_effect = None
    
    def test_system_status_reporting(self, automation_system):
        """Test system status reporting"""
        status = automation_system.get_system_status()
        
        assert isinstance(status, dict)
        assert 'components' in status
        assert 'config' in status
        assert 'performance' in status
        
        # Check component statuses
        components = status['components']
        assert 'scraper' in components
        assert 'vector_store' in components
        assert 'llm_router' in components
        assert 'assistant' in components
        assert 'sheets_manager' in components
        
        # Verify all components report status
        for component, component_status in components.items():
            assert 'status' in component_status
            assert component_status['status'] in ['operational', 'error', 'disabled']
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, automation_system):
        """Test concurrent operations across modules"""
        # Create multiple concurrent tasks
        tasks = [
            automation_system.scraper.scrape_url("https://example1.com"),
            automation_system.scraper.scrape_url("https://example2.com"),
            automation_system.vector_store.search_similar("test query"),
            automation_system.llm_router.generate_response("test prompt"),
            automation_system.assistant.process_message("Hello!")
        ]
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks)
        
        # Verify all tasks completed successfully
        assert len(results) == 5
        for result in results:
            assert result is not None
    
    def test_system_cleanup_and_shutdown(self, automation_system):
        """Test system cleanup and shutdown procedures"""
        # Get initial status
        initial_status = automation_system.get_system_status()
        assert initial_status['components']['assistant']['status'] == 'operational'
        
        # Shutdown system
        automation_system.shutdown()
        
        # Verify cleanup (assistant should be stopped)
        final_status = automation_system.get_system_status()
        assert final_status['components']['assistant']['status'] == 'disabled'


class TestPerformanceIntegration:
    """Performance and load testing for the system"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_memory_usage_during_operations(self, automation_system):
        """Test memory usage during intensive operations"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Perform multiple operations
        for i in range(10):
            await automation_system.scraper.scrape_url(f"https://example{i}.com")
            await automation_system.vector_store.search_similar(f"query {i}")
            await automation_system.llm_router.generate_response(f"prompt {i}")
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (< 100MB for 10 operations)
        assert memory_increase < 100
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_response_time_benchmarks(self, automation_system):
        """Test response time benchmarks"""
        import time
        
        # Benchmark scraping
        start_time = time.time()
        await automation_system.scraper.scrape_url("https://example.com")
        scrape_time = time.time() - start_time
        
        # Benchmark vector search
        start_time = time.time()
        await automation_system.vector_store.search_similar("benchmark query")
        search_time = time.time() - start_time
        
        # Benchmark LLM response
        start_time = time.time()
        await automation_system.llm_router.generate_response("benchmark prompt")
        llm_time = time.time() - start_time
        
        # Response times should be reasonable (adjust thresholds as needed)
        assert scrape_time < 5.0  # Should be fast with mocks
        assert search_time < 1.0   # Vector search should be very fast
        assert llm_time < 2.0      # LLM should be reasonably fast
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_high_load_conversation_handling(self, automation_system):
        """Test handling high load of conversation messages"""
        messages = [f"Message {i}" for i in range(20)]
        
        # Process all messages concurrently
        start_time = time.time()
        tasks = [automation_system.assistant.process_message(msg) for msg in messages]
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # All messages should be processed
        assert len(results) == len(messages)
        
        # Most should succeed (some might fail due to unknown intent)
        success_count = sum(1 for r in results if r.get('success', False))
        assert success_count >= len(messages) * 0.8  # At least 80% success rate
        
        # Total time should be reasonable (parallel processing)
        assert total_time < 10.0  # Should process in parallel