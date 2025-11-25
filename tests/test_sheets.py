import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Dict, Any, List
import json

# Mock Google API clients before importing
import sys
from unittest.mock import MagicMock
from pathlib import Path

# Adicionar diretório raiz ao PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

# Create mock modules for Google APIs
mock_google_modules = {
    'google': MagicMock(),
    'google.auth': MagicMock(),
    'googleapiclient': MagicMock(),
    'googleapiclient.discovery': MagicMock(),
    'google.oauth2': MagicMock(),
    'google.oauth2.service_account': MagicMock()
}

# Setup mocks before importing our modules
for name, module in mock_google_modules.items():
    sys.modules[name] = module

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
def mock_sheets_service():
    """Mock Google Sheets service"""
    service = Mock()
    service.spreadsheets = Mock()
    service.spreadsheets.return_value = service.spreadsheets
    service.spreadsheets.values = Mock()
    service.spreadsheets.values.return_value = service.spreadsheets.values
    return service


@pytest.fixture
def sheets_manager(mock_config, mock_sheets_service):
    """Create GoogleSheetsSync instance with mocked service"""
    with patch('googleapiclient.discovery.build', return_value=mock_sheets_service):
        with patch('google.oauth2.service_account.Credentials.from_service_account_file'):
            manager = GoogleSheetsSync(mock_config)
            manager.service = mock_sheets_service
            yield manager


class TestGoogleSheetsSync:
    """Test cases for Google Sheets synchronization"""
    
    def test_initialization(self, mock_config):
        """Test proper initialization"""
        # Mock the GoogleSheetsSync to avoid Google API dependencies
        with patch('src.sheets.sync_manager.GoogleSheetsSync.__init__', return_value=None):
            manager = GoogleSheetsSync.__new__(GoogleSheetsSync)
            manager.config = mock_config
            manager.service = None
            manager.spreadsheet_id = None
            
            assert manager.config == mock_config
            assert manager.service is None
            assert manager.spreadsheet_id is None
    
    def test_is_configured(self, sheets_manager):
        """Test configuration check"""
        # Not configured initially
        assert not sheets_manager.is_configured()
        
        # Configure and check again
        sheets_manager.spreadsheet_id = "test_spreadsheet_id"
        assert sheets_manager.is_configured()
    
    def test_configure_with_credentials_file(self, sheets_manager):
        """Test configuration with credentials file"""
        with patch('pathlib.Path.exists', return_value=True):
            with patch('google.oauth2.service_account.Credentials.from_service_account_file') as mock_creds:
                mock_creds.return_value = Mock()
                
                result = sheets_manager.configure(
                    spreadsheet_id="test_id",
                    credentials_file="/path/to/credentials.json"
                )
                
                assert result is True
                assert sheets_manager.spreadsheet_id == "test_id"
                mock_creds.assert_called_once()
    
    def test_configure_with_credentials_data(self, sheets_manager):
        """Test configuration with credentials data dict"""
        with patch('pathlib.Path.exists', return_value=False):
            with patch('json.loads') as mock_json:
                with patch('google.oauth2.service_account.Credentials.from_service_account_info') as mock_creds:
                    mock_creds.return_value = Mock()
                    
                    credentials_data = {"type": "service_account", "project_id": "test"}
                    result = sheets_manager.configure(
                        spreadsheet_id="test_id",
                        credentials_data=credentials_data
                    )
                    
                    assert result is True
                    assert sheets_manager.spreadsheet_id == "test_id"
                    mock_creds.assert_called_once()
    
    def test_configure_failure(self, sheets_manager):
        """Test configuration failure handling"""
        with patch('pathlib.Path.exists', return_value=False):
            result = sheets_manager.configure(spreadsheet_id="test_id")
            assert result is False
    
    def test_sync_scraping_data_not_configured(self, sheets_manager):
        """Test sync when not configured"""
        result = sheets_manager.sync_scraping_data({"test": "data"})
        assert result is False
    
    def test_sync_scraping_data_success(self, sheets_manager):
        """Test successful data sync"""
        sheets_manager.spreadsheet_id = "test_spreadsheet_id"
        
        # Mock the execute method
        mock_execute = Mock()
        mock_execute.execute.return_value = {"values": []}
        
        sheets_manager.service.spreadsheets.values.get.return_value = mock_execute
        
        # Mock the update method
        mock_update = Mock()
        mock_update.execute.return_value = {"updatedCells": 5}
        sheets_manager.service.spreadsheets.values.update.return_value = mock_update
        
        test_data = {
            "url": "https://example.com",
            "title": "Test Title",
            "content": "Test content",
            "scraped_at": "2024-01-01T00:00:00Z"
        }
        
        result = sheets_manager.sync_scraping_data(test_data)
        assert result is True
        
        # Verify the update was called with correct parameters
        sheets_manager.service.spreadsheets.values.update.assert_called_once()
        call_args = sheets_manager.service.spreadsheets.values.update.call_args
        assert call_args[1]['spreadsheetId'] == "test_spreadsheet_id"
        assert 'values' in call_args[1]['body']
    
    def test_sync_scraping_data_with_existing_data(self, sheets_manager):
        """Test data sync when data already exists"""
        sheets_manager.spreadsheet_id = "test_spreadsheet_id"
        
        # Mock existing data
        mock_execute = Mock()
        mock_execute.execute.return_value = {
            "values": [
                ["URL", "Title", "Content", "Scraped At"],
                ["https://existing.com", "Existing", "Content", "2024-01-01"]
            ]
        }
        sheets_manager.service.spreadsheets.values.get.return_value = mock_execute
        
        # Mock the update method
        mock_update = Mock()
        mock_update.execute.return_value = {"updatedCells": 5}
        sheets_manager.service.spreadsheets.values.update.return_value = mock_update
        
        test_data = {
            "url": "https://new.com",
            "title": "New Title",
            "content": "New content",
            "scraped_at": "2024-01-02T00:00:00Z"
        }
        
        result = sheets_manager.sync_scraping_data(test_data)
        assert result is True
    
    def test_sync_rag_data(self, sheets_manager):
        """Test RAG data synchronization"""
        sheets_manager.spreadsheet_id = "test_spreadsheet_id"
        
        # Mock the execute method
        mock_execute = Mock()
        mock_execute.execute.return_value = {"values": []}
        sheets_manager.service.spreadsheets.values.get.return_value = mock_execute
        
        # Mock the update method
        mock_update = Mock()
        mock_update.execute.return_value = {"updatedCells": 3}
        sheets_manager.service.spreadsheets.values.update.return_value = mock_update
        
        test_data = {
            "query": "test query",
            "results": [
                {"content": "result1", "metadata": {"score": 0.9}},
                {"content": "result2", "metadata": {"score": 0.8}}
            ]
        }
        
        result = sheets_manager.sync_rag_data(test_data)
        assert result is True
    
    def test_sync_llm_interactions(self, sheets_manager):
        """Test LLM interaction sync"""
        sheets_manager.spreadsheet_id = "test_spreadsheet_id"
        
        # Mock the execute method
        mock_execute = Mock()
        mock_execute.execute.return_value = {"values": []}
        sheets_manager.service.spreadsheets.values.get.return_value = mock_execute
        
        # Mock the update method
        mock_update = Mock()
        mock_update.execute.return_value = {"updatedCells": 4}
        sheets_manager.service.spreadsheets.values.update.return_value = mock_update
        
        test_data = {
            "prompt": "test prompt",
            "response": "test response",
            "provider": "openai",
            "model": "gpt-3.5-turbo",
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
        result = sheets_manager.sync_llm_interactions(test_data)
        assert result is True
    
    def test_batch_sync_operations(self, sheets_manager):
        """Test batch synchronization of multiple operations"""
        sheets_manager.spreadsheet_id = "test_spreadsheet_id"
        
        # Mock the execute method
        mock_execute = Mock()
        mock_execute.execute.return_value = {"values": []}
        sheets_manager.service.spreadsheets.values.get.return_value = mock_execute
        
        # Mock the batch update method
        mock_batch_update = Mock()
        mock_batch_update.execute.return_value = {"replies": [{}, {}]}
        sheets_manager.service.spreadsheets.values.batchUpdate.return_value = mock_batch_update
        
        operations = [
            {
                "type": "scraping",
                "data": {"url": "https://example1.com", "title": "Title 1", "content": "Content 1"}
            },
            {
                "type": "rag",
                "data": {"query": "query1", "results": [{"content": "result1"}]}
            }
        ]
        
        result = sheets_manager.batch_sync_operations(operations)
        assert result is True
        
        # Verify batch update was called
        sheets_manager.service.spreadsheets.values.batchUpdate.assert_called_once()
    
    def test_error_handling_api_errors(self, sheets_manager):
        """Test error handling for API errors"""
        sheets_manager.spreadsheet_id = "test_spreadsheet_id"
        
        # Mock API error
        mock_execute = Mock()
        mock_execute.execute.side_effect = Exception("API Error")
        sheets_manager.service.spreadsheets.values.get.return_value = mock_execute
        
        test_data = {"url": "https://example.com", "title": "Test"}
        result = sheets_manager.sync_scraping_data(test_data)
        assert result is False
    
    def test_error_handling_network_errors(self, sheets_manager):
        """Test error handling for network errors"""
        sheets_manager.spreadsheet_id = "test_spreadsheet_id"
        
        # Mock network timeout
        mock_execute = Mock()
        mock_execute.execute.side_effect = TimeoutError("Network timeout")
        sheets_manager.service.spreadsheets.values.get.return_value = mock_execute
        
        test_data = {"url": "https://example.com", "title": "Test"}
        result = sheets_manager.sync_scraping_data(test_data)
        assert result is False
    
    def test_data_validation(self, sheets_manager):
        """Test data validation before sync"""
        sheets_manager.spreadsheet_id = "test_spreadsheet_id"
        
        # Test with invalid data
        result = sheets_manager.sync_scraping_data(None)
        assert result is False
        
        result = sheets_manager.sync_scraping_data({})
        assert result is False
        
        # Test with valid minimal data
        mock_execute = Mock()
        mock_execute.execute.return_value = {"values": []}
        sheets_manager.service.spreadsheets.values.get.return_value = mock_execute
        
        mock_update = Mock()
        mock_update.execute.return_value = {"updatedCells": 1}
        sheets_manager.service.spreadsheets.values.update.return_value = mock_update
        
        result = sheets_manager.sync_scraping_data({"url": "https://example.com"})
        assert result is True
    
    def test_async_sync_operations(self, sheets_manager):
        """Test async versions of sync operations"""
        sheets_manager.spreadsheet_id = "test_spreadsheet_id"
        
        # Mock the execute method
        mock_execute = Mock()
        mock_execute.execute.return_value = {"values": []}
        sheets_manager.service.spreadsheets.values.get.return_value = mock_execute
        
        # Mock the update method
        mock_update = Mock()
        mock_update.execute.return_value = {"updatedCells": 5}
        sheets_manager.service.spreadsheets.values.update.return_value = mock_update
        
        test_data = {
            "url": "https://example.com",
            "title": "Test Title",
            "content": "Test content",
            "scraped_at": "2024-01-01T00:00:00Z"
        }
        
        # Test async sync
        async def test_async():
            result = await sheets_manager.async_sync_scraping_data(test_data)
            return result
        
        result = asyncio.run(test_async())
        assert result is True


class TestGoogleSheetsIntegration:
    """Integration tests for Google Sheets functionality"""
    
    @pytest.mark.integration
    def test_full_sync_workflow(self, sheets_manager):
        """Test complete sync workflow"""
        sheets_manager.spreadsheet_id = "test_spreadsheet_id"
        
        # Mock all Google API calls
        mock_get = Mock()
        mock_get.execute.return_value = {"values": []}
        sheets_manager.service.spreadsheets.values.get.return_value = mock_get
        
        mock_update = Mock()
        mock_update.execute.return_value = {"updatedCells": 10}
        sheets_manager.service.spreadsheets.values.update.return_value = mock_update
        
        # Test scraping data sync
        scraping_data = {
            "url": "https://example.com",
            "title": "Example Page",
            "content": "This is example content",
            "scraped_at": "2024-01-01T12:00:00Z"
        }
        
        result = sheets_manager.sync_scraping_data(scraping_data)
        assert result is True
        
        # Test RAG data sync
        rag_data = {
            "query": "What is machine learning?",
            "results": [
                {"content": "Machine learning is a subset of AI", "metadata": {"score": 0.95}},
                {"content": "It involves training algorithms", "metadata": {"score": 0.87}}
            ]
        }
        
        result = sheets_manager.sync_rag_data(rag_data)
        assert result is True
        
        # Test LLM interaction sync
        llm_data = {
            "prompt": "Explain quantum computing",
            "response": "Quantum computing uses quantum bits...",
            "provider": "openai",
            "model": "gpt-4",
            "timestamp": "2024-01-01T12:05:00Z"
        }
        
        result = sheets_manager.sync_llm_interactions(llm_data)
        assert result is True
    
    @pytest.mark.integration
    def test_error_recovery_workflow(self, sheets_manager):
        """Test error recovery in sync workflow"""
        sheets_manager.spreadsheet_id = "test_spreadsheet_id"
        
        # First call fails with network error
        mock_get_fail = Mock()
        mock_get_fail.execute.side_effect = [Exception("Network error"), {"values": []}]
        sheets_manager.service.spreadsheets.values.get.return_value = mock_get_fail
        
        # Second call succeeds
        mock_update = Mock()
        mock_update.execute.return_value = {"updatedCells": 5}
        sheets_manager.service.spreadsheets.values.update.return_value = mock_update
        
        test_data = {"url": "https://example.com", "title": "Test"}
        
        # First attempt should fail
        result = sheets_manager.sync_scraping_data(test_data)
        assert result is False
        
        # Simulate retry after error recovery
        mock_get_fail.execute.side_effect = None
        result = sheets_manager.sync_scraping_data(test_data)
        assert result is True


# Cleanup after tests - remove mock modules
for name in list(mock_google_modules.keys()):
    if name in sys.modules:
        del sys.modules[name]