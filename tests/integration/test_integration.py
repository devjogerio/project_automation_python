import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
import tempfile
import json
from datetime import datetime

from src.main import AutomationSystem
from src.utils.config import Config
from src.scraping.scraper import WebScraper
from src.rag.vector_store import VectorStore
from src.llm.router import LLMRouter
from src.sheets.sync_manager import GoogleSheetsSync
from src.assistant.virtual_assistant import VirtualAssistant


class TestIntegration:
    """Testes de integração para o sistema completo de automação."""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Cria diretório temporário para configurações."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def mock_config(self, temp_config_dir):
        """Configuração mock para testes."""
        config = Config()
        config.base_dir = temp_config_dir
        config.config_dir = temp_config_dir / "config"
        config.data_dir = temp_config_dir / "data"
        config.logs_dir = temp_config_dir / "logs"
        
        # Cria diretórios necessários
        for dir_path in [config.config_dir, config.data_dir, config.logs_dir]:
            dir_path.mkdir(exist_ok=True)
        
        return config
    
    @pytest.fixture
    def automation_system(self, mock_config):
        """Sistema de automação para testes."""
        system = AutomationSystem()
        system.config = mock_config
        return system
    
    async def test_complete_workflow(self, automation_system):
        """Testa o fluxo completo de trabalho do sistema."""
        # Mock de dados de scraping
        mock_scraping_data = {
            'url': 'https://example.com',
            'title': 'Exemplo de Página',
            'content': 'Conteúdo de exemplo para teste',
            'links': ['https://example.com/page1', 'https://example.com/page2'],
            'metadata': {
                'scraped_at': datetime.now().isoformat(),
                'status_code': 200,
                'content_type': 'text/html'
            }
        }
        
        # Mock de resposta do LLM
        mock_llm_response = {
            'content': 'Análise do conteúdo: O texto parece ser sobre exemplo de teste.',
            'provider': 'openai',
            'model': 'gpt-3.5-turbo',
            'usage': {'prompt_tokens': 50, 'completion_tokens': 25, 'total_tokens': 75}
        }
        
        # Mock de dados do Google Sheets
        mock_sheets_data = {
            'spreadsheet_id': 'test_spreadsheet_id',
            'range': 'Dados!A1:D10',
            'values': [['URL', 'Título', 'Conteúdo', 'Data'], ['https://example.com', 'Exemplo', 'Conteúdo', '2024-01-01']]
        }
        
        with patch('src.scraping.scraper.WebScraper.scrape_url') as mock_scrape, \
             patch('src.llm.router.LLMRouter.generate_response') as mock_llm, \
             patch('src.sheets.sync_manager.GoogleSheetsSync.write_data') as mock_sheets_write, \
             patch('src.rag.vector_store.VectorStore.add_documents') as mock_vector_add:
            
            # Configura mocks
            mock_scrape.return_value = mock_scraping_data
            mock_llm.return_value = mock_llm_response
            mock_sheets_write.return_value = True
            mock_vector_add.return_value = True
            
            # Executa fluxo completo
            result = await automation_system.execute_workflow(
                url='https://example.com',
                analyze_content=True,
                store_in_vector=True,
                sync_to_sheets=True
            )
            
            # Verifica resultados
            assert result['success'] is True
            assert result['scraping_data'] == mock_scraping_data
            assert result['llm_analysis'] == mock_llm_response
            assert result['vector_stored'] is True
            assert result['sheets_synced'] is True
            
            # Verifica chamadas
            mock_scrape.assert_called_once_with('https://example.com')
            mock_llm.assert_called_once()
            mock_vector_add.assert_called_once()
            mock_sheets_write.assert_called_once()
    
    async def test_error_handling_workflow(self, automation_system):
        """Testa tratamento de erros no fluxo completo."""
        with patch('src.scraping.scraper.WebScraper.scrape_url') as mock_scrape:
            mock_scrape.return_value = {'error': 'Failed to fetch content', 'url': 'https://invalid.com'}
            
            result = await automation_system.execute_workflow(
                url='https://invalid.com',
                analyze_content=True
            )
            
            assert result['success'] is False
            assert 'error' in result
            assert result['error'] == 'Failed to fetch content'
    
    async def test_vector_search_integration(self, automation_system):
        """Testa integração de busca vetorial."""
        mock_documents = [
            {
                'id': 'doc1',
                'content': 'Python é uma linguagem de programação poderosa',
                'metadata': {'source': 'test', 'type': 'documentation'}
            },
            {
                'id': 'doc2', 
                'content': 'JavaScript é amplamente usado no desenvolvimento web',
                'metadata': {'source': 'test', 'type': 'documentation'}
            }
        ]
        
        mock_search_results = [
            {'id': 'doc1', 'score': 0.85, 'content': 'Python é uma linguagem de programação poderosa'},
            {'id': 'doc2', 'score': 0.72, 'content': 'JavaScript é amplamente usado no desenvolvimento web'}
        ]
        
        with patch('src.rag.vector_store.VectorStore.add_documents') as mock_add, \
             patch('src.rag.vector_store.VectorStore.search') as mock_search:
            
            mock_add.return_value = True
            mock_search.return_value = mock_search_results
            
            # Adiciona documentos
            await automation_system.vector_store.add_documents(mock_documents)
            
            # Busca por similaridade
            results = await automation_system.vector_store.search('linguagem de programação', k=2)
            
            assert len(results) == 2
            assert results[0]['score'] > 0.8
            mock_add.assert_called_once()
            mock_search.assert_called_once()
    
    async def test_assistant_integration(self, automation_system):
        """Testa integração do assistente virtual."""
        with patch('src.assistant.virtual_assistant.VirtualAssistant.process_message') as mock_process:
            mock_process.return_value = {
                'response': 'Posso ajudar você com análise de dados.',
                'intent': 'data_analysis',
                'confidence': 0.92,
                'context': {'user_id': 'test_user'}
            }
            
            response = await automation_system.assistant.process_message('Analise estes dados para mim')
            
            assert response['intent'] == 'data_analysis'
            assert response['confidence'] > 0.9
            assert 'response' in response
            mock_process.assert_called_once_with('Analise estes dados para mim')
    
    async def test_sheets_sync_integration(self, automation_system):
        """Testa integração com Google Sheets."""
        test_data = {
            'url': 'https://test.com',
            'title': 'Página de Teste',
            'content': 'Conteúdo de teste',
            'scraped_at': datetime.now().isoformat()
        }
        
        with patch('src.sheets.sync_manager.GoogleSheetsSync.is_configured') as mock_configured, \
             patch('src.sheets.sync_manager.GoogleSheetsSync.write_data') as mock_write:
            
            mock_configured.return_value = True
            mock_write.return_value = True
            
            success = await automation_system.sheets_sync.sync_scraping_data(test_data)
            
            assert success is True
            mock_configured.assert_called_once()
            mock_write.assert_called_once()
    
    async def test_concurrent_operations(self, automation_system):
        """Testa operações concorrentes no sistema."""
        urls = [
            'https://example1.com',
            'https://example2.com',
            'https://example3.com'
        ]
        
        mock_results = [
            {'url': url, 'title': f'Título {i}', 'content': f'Conteúdo {i}'}
            for i, url in enumerate(urls)
        ]
        
        with patch('src.scraping.scraper.WebScraper.scrape_url') as mock_scrape:
            mock_scrape.side_effect = mock_results
            
            # Executa scraping concorrente
            tasks = [automation_system.scraper.scrape_url(url) for url in urls]
            results = await asyncio.gather(*tasks)
            
            assert len(results) == 3
            for i, result in enumerate(results):
                assert result['url'] == urls[i]
                assert result['title'] == f'Título {i}'
            
            assert mock_scrape.call_count == 3
    
    async def test_data_pipeline_integration(self, automation_system):
        """Testa pipeline completo de processamento de dados."""
        # Dados brutos de scraping
        raw_data = {
            'url': 'https://techblog.com',
            'title': 'Artigo sobre IA',
            'content': 'Inteligência Artificial está revolucionando a tecnologia...',
            'metadata': {'scraped_at': datetime.now().isoformat()}
        }
        
        # Dados processados esperados
        processed_data = {
            'id': 'processed_1',
            'content': 'Inteligência Artificial está revolucionando a tecnologia...',
            'metadata': {
                'source': 'https://techblog.com',
                'title': 'Artigo sobre IA',
                'processed_at': datetime.now().isoformat(),
                'type': 'article'
            }
        }
        
        with patch('src.scraping.scraper.WebScraper.scrape_url') as mock_scrape, \
             patch('src.rag.vector_store.VectorStore.add_documents') as mock_vector, \
             patch('src.llm.router.LLMRouter.generate_response') as mock_llm:
            
            mock_scrape.return_value = raw_data
            mock_vector.return_value = True
            mock_llm.return_value = {
                'content': 'Análise: O artigo discute o impacto da IA na tecnologia.',
                'provider': 'openai',
                'model': 'gpt-3.5-turbo'
            }
            
            # Executa pipeline
            result = await automation_system.process_data_pipeline(
                url='https://techblog.com',
                store_vector=True,
                analyze_content=True
            )
            
            assert result['success'] is True
            assert 'scraping_data' in result
            assert 'vector_result' in result
            assert 'analysis' in result
            assert result['vector_result'] is True
            
            mock_scrape.assert_called_once()
            mock_vector.assert_called_once()
            mock_llm.assert_called_once()


@pytest.mark.asyncio
class TestSystemPerformance:
    """Testes de performance do sistema."""
    
    async def test_large_dataset_processing(self, automation_system):
        """Testa processamento de grande volume de dados."""
        # Cria dataset grande
        large_dataset = []
        for i in range(100):
            large_dataset.append({
                'id': f'doc_{i}',
                'content': f'Conteúdo do documento {i} ' * 50,  # Texto longo
                'metadata': {'source': f'source_{i % 10}', 'type': 'test'}
            })
        
        with patch('src.rag.vector_store.VectorStore.add_documents') as mock_add:
            mock_add.return_value = True
            
            # Processa em lotes
            batch_size = 10
            results = []
            
            for i in range(0, len(large_dataset), batch_size):
                batch = large_dataset[i:i + batch_size]
                result = await automation_system.vector_store.add_documents(batch)
                results.append(result)
            
            assert len(results) == 10  # 100 documentos / 10 por lote
            assert all(results)  # Todos os lotes processados com sucesso
            assert mock_add.call_count == 10
    
    async def test_memory_efficiency(self, automation_system):
        """Testa eficiência de memória durante operações."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Executa várias operações
        tasks = []
        for i in range(50):
            tasks.append(automation_system.scraper.scrape_url(f'https://example{i}.com'))
        
        # Mock para evitar requisições reais
        with patch('src.scraping.scraper.WebScraper.scrape_url') as mock_scrape:
            mock_scrape.return_value = {'url': 'test', 'content': 'test content'}
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Verifica se não houve vazamento significativo de memória
        assert memory_increase < 100  # Aumento menor que 100MB
        assert len(results) == 50


if __name__ == '__main__':
    pytest.main([__file__])