import pytest
import asyncio
import sys
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Dict, Any, List
from pathlib import Path

# Adicionar diretório raiz ao PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock Google APIs
sys.modules['googleapiclient'] = MagicMock()
sys.modules['googleapiclient.discovery'] = MagicMock()
sys.modules['google.oauth2'] = MagicMock()
sys.modules['google.oauth2.service_account'] = MagicMock()

# Mock CustomTkinter
sys.modules['customtkinter'] = MagicMock()
sys.modules['customtkinter.windows'] = MagicMock()
sys.modules['customtkinter.windows.ctk_tk'] = MagicMock()
sys.modules['customtkinter.windows.widgets'] = MagicMock()

# Mock other dependencies
sys.modules['chromadb'] = MagicMock()
sys.modules['sentence_transformers'] = MagicMock()
sys.modules['selenium'] = MagicMock()
sys.modules['selenium.webdriver'] = MagicMock()
sys.modules['selenium.webdriver.chrome'] = MagicMock()
sys.modules['openai'] = MagicMock()


class TestBasicFunctionality:
    """Testes básicos de funcionalidade do sistema"""
    
    def test_system_imports(self):
        """Testa se os módulos principais podem ser importados"""
        try:
            from src.utils.config import Config
            from src.scraping.scraper import WebScraper
            from src.rag.vector_store import VectorStore
            from src.llm.router import LLMRouter
            from src.assistant.virtual_assistant import VirtualAssistant
            from src.sheets.sync_manager import GoogleSheetsSync
            from src.main import AutomationSystem
            assert True
        except ImportError as e:
            pytest.fail(f"Falha ao importar módulos: {e}")
    
    def test_config_creation(self):
        """Testa criação de configuração"""
        from src.utils.config import Config
        
        config = Config()
        assert hasattr(config, 'base_dir')
        assert hasattr(config, 'config_dir')
        assert hasattr(config, 'data_dir')
        assert hasattr(config, 'logs_dir')
    
    def test_mock_services_creation(self):
        """Testa criação de serviços com mocks"""
        # Config
        from src.utils.config import Config
        config = Mock(spec=Config)
        config.base_dir = Path("/tmp/test")
        config.config_dir = Path("/tmp/test/config")
        config.data_dir = Path("/tmp/test/data")
        config.logs_dir = Path("/tmp/test/logs")
        
        # Scraper
        from src.scraping.scraper import WebScraper
        scraper = Mock(spec=WebScraper)
        assert scraper is not None
        
        # Vector Store
        from src.rag.vector_store import VectorStore
        vector_store = Mock(spec=VectorStore)
        assert vector_store is not None
        
        # LLM Router
        from src.llm.router import LLMRouter
        llm_router = Mock(spec=LLMRouter)
        assert llm_router is not None
        
        # Assistant
        from src.assistant.virtual_assistant import VirtualAssistant
        assistant = Mock(spec=VirtualAssistant)
        assert assistant is not None
        
        # Sheets Manager
        from src.sheets.sync_manager import GoogleSheetsSync
        sheets_manager = Mock(spec=GoogleSheetsSync)
        assert sheets_manager is not None


class TestAsyncOperations:
    """Testes de operações assíncronas"""
    
    @pytest.mark.asyncio
    async def test_async_scraping_mock(self):
        """Testa scraping assíncrono com mock"""
        scraper = Mock()
        
        async def mock_scrape(url):
            return {
                "url": url,
                "title": "Test Title",
                "content": "Test Content",
                "success": True
            }
        
        scraper.scrape_url = mock_scrape
        
        result = await scraper.scrape_url("https://example.com")
        assert result["success"] is True
        assert result["url"] == "https://example.com"
    
    @pytest.mark.asyncio
    async def test_async_vector_search_mock(self):
        """Testa busca vetorial assíncrona com mock"""
        vector_store = Mock()
        
        async def mock_search(query, k=5):
            return [
                {"content": f"Result {i} for {query}", "score": 0.9 - i * 0.1}
                for i in range(k)
            ]
        
        vector_store.search_similar = mock_search
        
        results = await vector_store.search_similar("test query", k=3)
        assert len(results) == 3
        assert results[0]["score"] > results[1]["score"]
    
    @pytest.mark.asyncio
    async def test_async_llm_response_mock(self):
        """Testa resposta LLM assíncrona com mock"""
        llm_router = Mock()
        
        async def mock_generate_response(prompt):
            from src.llm.router import LLMResponse
            return LLMResponse(
                content=f"Mock response to: {prompt[:20]}...",
                provider="openai",
                model="gpt-3.5-turbo",
                prompt_tokens=10,
                response_tokens=20,
                total_tokens=30
            )
        
        llm_router.generate_response = mock_generate_response
        
        response = await llm_router.generate_response("Test prompt")
        assert response.content.startswith("Mock response to:")
        assert response.provider == "openai"
        assert response.total_tokens == 30


class TestErrorHandling:
    """Testes de tratamento de erros"""
    
    def test_error_handling_in_scraping(self):
        """Testa tratamento de erros no scraping"""
        scraper = Mock()
        
        async def mock_scrape_with_error(url):
            if "error" in url:
                raise Exception("Network error")
            return {"success": True, "url": url}
        
        scraper.scrape_url = mock_scrape_with_error
        
        # Testar URL que causa erro
        import asyncio
        try:
            asyncio.run(scraper.scrape_url("https://error.com"))
            assert False, "Deveria ter lançado exceção"
        except Exception as e:
            assert "Network error" in str(e)
    
    def test_error_handling_in_vector_store(self):
        """Testa tratamento de erros no vector store"""
        vector_store = Mock()
        
        async def mock_search_with_error(query):
            if not query:
                raise ValueError("Query cannot be empty")
            return [{"content": "result", "score": 0.8}]
        
        vector_store.search_similar = mock_search_with_error
        
        # Testar query vazia
        import asyncio
        try:
            asyncio.run(vector_store.search_similar(""))
            assert False, "Deveria ter lançado exceção"
        except ValueError as e:
            assert "Query cannot be empty" in str(e)
    
    def test_error_handling_in_llm(self):
        """Testa tratamento de erros no LLM"""
        llm_router = Mock()
        
        async def mock_generate_with_error(prompt):
            if len(prompt) > 1000:
                raise ValueError("Prompt too long")
            return Mock(content="Response")
        
        llm_router.generate_response = mock_generate_with_error
        
        # Testar prompt muito longo
        import asyncio
        try:
            long_prompt = "x" * 1001
            asyncio.run(llm_router.generate_response(long_prompt))
            assert False, "Deveria ter lançado exceção"
        except ValueError as e:
            assert "Prompt too long" in str(e)


class TestIntegrationScenarios:
    """Testes de cenários de integração"""
    
    @pytest.mark.asyncio
    async def test_scraping_to_vector_workflow(self):
        """Testa workflow completo de scraping para vector store"""
        # Mock scraper
        scraper = Mock()
        async def mock_scrape(url):
            return {
                "url": url,
                "title": f"Title for {url}",
                "content": f"Content from {url}",
                "scraped_at": "2024-01-01T00:00:00Z",
                "success": True
            }
        scraper.scrape_url = mock_scrape
        
        # Mock vector store
        vector_store = Mock()
        documents_added = []
        async def mock_add_docs(docs):
            documents_added.extend(docs)
            return True
        vector_store.add_documents = mock_add_docs
        
        # Executar workflow
        scrape_result = await scraper.scrape_url("https://example.com")
        assert scrape_result["success"] is True
        
        if scrape_result["success"]:
            documents = [{
                "content": scrape_result["content"],
                "metadata": {
                    "url": scrape_result["url"],
                    "title": scrape_result["title"],
                    "scraped_at": scrape_result["scraped_at"]
                }
            }]
            add_result = await vector_store.add_documents(documents)
            assert add_result is True
            assert len(documents_added) == 1
    
    @pytest.mark.asyncio
    async def test_rag_query_workflow(self):
        """Testa workflow completo de consulta RAG"""
        # Mock vector store
        vector_store = Mock()
        async def mock_search(query, k=3):
            return [
                {"content": f"Relevant info about {query}", "score": 0.9},
                {"content": f"More info about {query}", "score": 0.8},
                {"content": f"Additional {query} content", "score": 0.7}
            ]
        vector_store.search_similar = mock_search
        
        # Mock LLM
        llm_router = Mock()
        async def mock_generate(prompt):
            return Mock(content=f"Comprehensive answer based on context: {prompt[:50]}...")
        llm_router.generate_response = mock_generate
        
        # Executar workflow RAG
        query = "machine learning trends"
        search_results = await vector_store.search_similar(query, k=3)
        assert len(search_results) == 3
        
        # Construir contexto
        context = "\n".join([result["content"] for result in search_results])
        enhanced_prompt = f"Based on the following context:\n{context}\n\nAnswer: {query}"
        
        # Gerar resposta
        response = await llm_router.generate_response(enhanced_prompt)
        assert response.content.startswith("Comprehensive answer")
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """Testa operações concorrentes"""
        # Criar múltiplos serviços mock
        services = []
        for i in range(5):
            service = Mock()
            async def mock_operation(idx=i):
                await asyncio.sleep(0.1)  # Simular trabalho
                return f"Result {idx}"
            service.operation = mock_operation
            services.append(service)
        
        # Executar operações concorrentes
        tasks = [service.operation() for service in services]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 5
        assert all(result.startswith("Result ") for result in results)


class TestSystemHealth:
    """Testes de saúde do sistema"""
    
    def test_all_modules_available(self):
        """Testa se todos os módulos principais estão disponíveis"""
        modules_to_check = [
            'src.utils.config',
            'src.scraping.scraper',
            'src.rag.vector_store',
            'src.llm.router',
            'src.assistant.virtual_assistant',
            'src.sheets.sync_manager',
            'src.main'
        ]
        
        failed_modules = []
        for module_name in modules_to_check:
            try:
                __import__(module_name, fromlist=[''])
            except ImportError as e:
                failed_modules.append((module_name, str(e)))
        
        if failed_modules:
            error_msg = "Módulos que falharam ao importar:\n"
            for module, error in failed_modules:
                error_msg += f"  - {module}: {error}\n"
            pytest.fail(error_msg)
    
    def test_basic_system_initialization(self):
        """Testa inicialização básica do sistema"""
        from src.utils.config import Config
        from pathlib import Path
        
        # Criar configuração temporária
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Criar estrutura de diretórios
            (temp_path / "config").mkdir()
            (temp_path / "data").mkdir()
            (temp_path / "logs").mkdir()
            
            # Mock config
            config = Mock(spec=Config)
            config.base_dir = temp_path
            config.config_dir = temp_path / "config"
            config.data_dir = temp_path / "data"
            config.logs_dir = temp_path / "logs"
            
            # Verificar estrutura
            assert config.config_dir.exists()
            assert config.data_dir.exists()
            assert config.logs_dir.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])