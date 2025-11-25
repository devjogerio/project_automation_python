"""
Testes unitários para o módulo de web scraping.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.scraping.scraper import WebScraper
from src.scraping.site_manager import SiteManager, SiteConfig
from src.scraping.orchestrator import ScrapingOrchestrator

class TestWebScraper:
    """Testes para a classe WebScraper."""
    
    @pytest.fixture
    def scraper(self):
        """Cria instância de WebScraper para testes."""
        with patch('src.scraping.scraper.config'):
            scraper = WebScraper()
            scraper.delay = 0.1  # Reduz delay para testes
            scraper.max_retries = 2
            scraper.user_agent = "TestBot/1.0"
            scraper.timeout = 10
            scraper.respect_robots = False  # Desabilita para testes
            return scraper
    
    def test_scraper_initialization(self, scraper):
        """Testa inicialização do scraper."""
        assert scraper is not None
        assert scraper.delay == 0.1
        assert scraper.max_retries == 2
        assert scraper.user_agent == "TestBot/1.0"
    
    @patch('requests.get')
    def test_make_request_with_retry_success(self, mock_get, scraper):
        """Testa requisição com retry - sucesso na primeira tentativa."""
        # Mock response bem-sucedido
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        result = scraper._make_request_with_retry("http://example.com")
        
        assert result is not None
        assert result.status_code == 200
        mock_get.assert_called_once()
    
    @patch('requests.get')
    def test_make_request_with_retry_failure(self, mock_get, scraper):
        """Testa requisição com retry - falha em todas as tentativas."""
        # Mock response com erro
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        result = scraper._make_request_with_retry("http://example.com")
        
        assert result is not None
        assert result.status_code == 404
        assert mock_get.call_count == 1  # Não deve fazer retry para 404
    
    @patch('requests.get')
    def test_scrape_static_content_success(self, mock_get, scraper):
        """Testa scraping de conteúdo estático com sucesso."""
        # Mock HTML response
        html_content = """
        <html>
            <head><title>Test Page</title></head>
            <body>
                <h1>Main Title</h1>
                <h2>Subtitle</h2>
                <p>Some content here.</p>
                <a href="/link1">Link 1</a>
                <img src="/image1.jpg" alt="Image 1">
            </body>
        </html>
        """
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = html_content.encode('utf-8')
        mock_get.return_value = mock_response
        
        result = scraper.scrape_static_content("http://example.com")
        
        assert 'error' not in result
        assert result['title'] == "Test Page"
        assert len(result['headings']) == 2
        assert len(result['links']) == 1
        assert len(result['images']) == 1
        assert 'Some content here' in result['text_content']
    
    @patch('requests.get')
    def test_scrape_static_content_with_selectors(self, mock_get, scraper):
        """Testa scraping com seletores personalizados."""
        html_content = """
        <html>
            <body>
                <div class="article">
                    <h1>Article Title</h1>
                    <p class="author">John Doe</p>
                    <p class="date">2023-01-01</p>
                </div>
            </body>
        </html>
        """
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = html_content.encode('utf-8')
        mock_get.return_value = mock_response
        
        selectors = {
            'articles': '.article',
            'authors': '.author',
            'dates': '.date'
        }
        
        result = scraper.scrape_static_content("http://example.com", selectors)
        
        assert 'error' not in result
        assert 'articles' in result
        assert 'authors' in result
        assert 'dates' in result
        assert len(result['articles']) == 1
        assert result['authors'][0] == "John Doe"
        assert result['dates'][0] == "2023-01-01"
    
    def test_extract_structured_data_json_ld(self, scraper):
        """Testa extração de dados estruturados JSON-LD."""
        html_content = """
        <html>
            <head>
                <script type="application/ld+json">
                {
                    "@context": "https://schema.org",
                    "@type": "Article",
                    "headline": "Test Article",
                    "author": {
                        "@type": "Person",
                        "name": "John Doe"
                    },
                    "datePublished": "2023-01-01"
                }
                </script>
            </head>
            <body>
                <h1>Regular Content</h1>
            </body>
        </html>
        """
        
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = html_content.encode('utf-8')
            mock_get.return_value = mock_response
            
            result = scraper.extract_structured_data("http://example.com", {})
            
            assert 'error' not in result
            assert 'structured_data' in result
            assert '@type' in result['structured_data']
            assert result['structured_data']['@type'] == 'Article'

class TestSiteManager:
    """Testes para a classe SiteManager."""
    
    @pytest.fixture
    def site_manager(self):
        """Cria instância de SiteManager para testes."""
        with patch('src.scraping.site_manager.config'):
            with patch('pathlib.Path.exists', return_value=False):
                manager = SiteManager()
                manager.config_file = Path("/tmp/test_sites.json")
                return manager
    
    def test_site_config_creation(self):
        """Testa criação de configuração de site."""
        site_config = SiteConfig(
            name="test_site",
            url="http://example.com",
            enabled=True,
            scraping_type="static"
        )
        
        assert site_config.name == "test_site"
        assert site_config.url == "http://example.com"
        assert site_config.enabled is True
        assert site_config.scraping_type == "static"
    
    def test_site_manager_initialization(self, site_manager):
        """Testa inicialização do gerenciador de sites."""
        assert site_manager is not None
        assert hasattr(site_manager, 'sites')
        assert isinstance(site_manager.sites, dict)
    
    def test_add_site(self, site_manager):
        """Testa adição de novo site."""
        site_config = SiteConfig(
            name="new_site",
            url="http://newsite.com",
            enabled=True
        )
        
        site_manager.add_site(site_config)
        
        assert "new_site" in site_manager.sites
        assert site_manager.sites["new_site"].name == "new_site"
    
    def test_remove_site(self, site_manager):
        """Testa remoção de site."""
        # Adiciona site primeiro
        site_config = SiteConfig(
            name="site_to_remove",
            url="http://remove.com",
            enabled=True
        )
        site_manager.add_site(site_config)
        
        # Remove site
        site_manager.remove_site("site_to_remove")
        
        assert "site_to_remove" not in site_manager.sites
    
    def test_get_enabled_sites(self, site_manager):
        """Testa obtenção de sites habilitados."""
        # Adiciona sites de teste
        site_manager.add_site(SiteConfig("enabled1", "http://1.com", enabled=True))
        site_manager.add_site(SiteConfig("disabled1", "http://2.com", enabled=False))
        site_manager.add_site(SiteConfig("enabled2", "http://3.com", enabled=True))
        
        enabled_sites = site_manager.get_enabled_sites()
        
        assert len(enabled_sites) == 2
        assert all(site.enabled for site in enabled_sites)
        assert all(site.name in ["enabled1", "enabled2"] for site in enabled_sites)
    
    def test_validate_site_config(self, site_manager):
        """Testa validação de configuração de site."""
        # Config válida
        valid_config = SiteConfig("valid", "http://valid.com", scraping_type="static")
        errors = site_manager.validate_site_config(valid_config)
        assert len(errors) == 0
        
        # Config inválida - sem nome
        invalid_config = SiteConfig("", "http://invalid.com")
        errors = site_manager.validate_site_config(invalid_config)
        assert len(errors) > 0
        assert any("Nome do site é obrigatório" in error for error in errors)
        
        # Config inválida - tipo de scraping inválido
        invalid_config2 = SiteConfig("invalid", "http://invalid.com", scraping_type="invalid")
        errors = site_manager.validate_site_config(invalid_config2)
        assert len(errors) > 0
        assert any("Tipo de scraping deve ser" in error for error in errors)

class TestScrapingOrchestrator:
    """Testes para a classe ScrapingOrchestrator."""
    
    @pytest.fixture
    def orchestrator(self):
        """Cria instância de ScrapingOrchestrator para testes."""
        with patch('src.scraping.orchestrator.config'):
            with patch('src.scraping.orchestrator.site_manager'):
                with patch('src.scraping.orchestrator.vector_store'):
                    with patch('src.scraping.orchestrator.sheets_sync'):
                        orchestrator = ScrapingOrchestrator()
                        orchestrator.max_workers = 2
                        return orchestrator
    
    def test_orchestrator_initialization(self, orchestrator):
        """Testa inicialização do orquestrador."""
        assert orchestrator is not None
        assert hasattr(orchestrator, 'scraper')
        assert hasattr(orchestrator, 'max_workers')
        assert orchestrator.max_workers == 2
    
    def test_scraping_completed_site(self, orchestrator):
        """Testa processamento de resultado de scraping bem-sucedido."""
        # Mock site
        site = SiteConfig("test_site", "http://test.com", enabled=True)
        
        # Mock resultado de scraping
        result = {
            'url': 'http://test.com',
            'title': 'Test Page',
            'content': 'Test content'
        }
        
        # Não deve lançar exceção
        orchestrator._process_scraping_result(site, result)
    
    def test_get_scheduler_status(self, orchestrator):
        """Testa obtenção de status do agendador."""
        status = orchestrator.get_scheduler_status()
        
        assert isinstance(status, dict)
        assert 'is_running' in status
        assert 'active_jobs' in status
        assert 'jobs' in status
        assert isinstance(status['jobs'], list)
    
    @patch('src.scraping.orchestrator.scraping_orchestrator.scrape_site')
    def test_scrape_multiple_sites(self, mock_scrape_site, orchestrator):
        """Testa scraping de múltiplos sites."""
        # Mock resultados
        mock_scrape_site.return_value = {'url': 'test', 'content': 'test'}
        
        site_names = ['site1', 'site2', 'site3']
        
        # Mock site_manager
        with patch('src.scraping.orchestrator.site_manager') as mock_site_manager:
            mock_site_manager.get_site.return_value = SiteConfig("test", "http://test.com")
            
            results = orchestrator.scrape_multiple_sites(site_names)
            
            assert isinstance(results, dict)
            assert len(results) == 3
            assert all(site in results for site in site_names)

@pytest.mark.asyncio
class TestAsyncScraping:
    """Testes assíncronos de scraping."""
    
    @pytest.fixture
    def scraper(self):
        """Cria instância de WebScraper para testes assíncronos."""
        with patch('src.scraping.scraper.config'):
            scraper = WebScraper()
            scraper.delay = 0.1
            scraper.max_retries = 2
            scraper.user_agent = "TestBot/1.0"
            scraper.timeout = 10
            scraper.respect_robots = False
            return scraper
    
    async def test_scrape_multiple_urls(self, scraper):
        """Testa scraping assíncrono de múltiplas URLs."""
        urls = [
            "http://example1.com",
            "http://example2.com",
            "http://example3.com"
        ]
        
        with patch('aiohttp.ClientSession') as mock_session:
            # Mock response
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.text = asyncio.coroutine(lambda: "<html><body>Test</body></html>")
            
            mock_get = MagicMock()
            mock_get.return_value.__aenter__ = asyncio.coroutine(lambda: mock_response)
            
            mock_session_instance = MagicMock()
            mock_session_instance.get = mock_get
            mock_session.return_value.__aenter__ = asyncio.coroutine(lambda: mock_session_instance)
            
            results = await scraper.scrape_multiple_urls(urls)
            
            assert len(results) == 3
            assert all('url' in result for result in results)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])