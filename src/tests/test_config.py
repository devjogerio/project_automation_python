"""
Testes unitários para o módulo de configuração.
"""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.utils.config import Config

class TestConfig:
    """Testes para a classe Config."""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Cria diretório temporário para configurações."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def config(self, temp_config_dir):
        """Cria instância de config para testes."""
        with patch('src.utils.config.Path') as mock_path:
            mock_path.return_value.parent.parent = temp_config_dir
            mock_path.return_value.parent = temp_config_dir / "src"
            mock_path.return_value = temp_config_dir / "src" / "utils"
            
            config = Config()
            config.base_dir = temp_config_dir
            config.config_dir = temp_config_dir / "config"
            config.data_dir = temp_config_dir / "data"
            config.logs_dir = temp_config_dir / "logs"
            
            yield config
    
    def test_config_initialization(self, config):
        """Testa inicialização da configuração."""
        assert config is not None
        assert hasattr(config, 'base_dir')
        assert hasattr(config, 'settings')
        assert isinstance(config.settings, dict)
    
    def test_create_directories(self, config):
        """Testa criação de diretórios."""
        config._create_directories()
        
        assert config.config_dir.exists()
        assert config.data_dir.exists()
        assert config.logs_dir.exists()
    
    def test_get_config_value(self, config):
        """Testa obtenção de valores de configuração."""
        # Testa valor existente
        config.settings['test'] = {'nested': 'value'}
        assert config.get('test.nested') == 'value'
        
        # Testa valor inexistente
        assert config.get('nonexistent.key') is None
        assert config.get('nonexistent.key', 'default') == 'default'
    
    def test_set_config_value(self, config):
        """Testa definição de valores de configuração."""
        config.set('new.key', 'new_value')
        assert config.get('new.key') == 'new_value'
        
        # Testa atualização
        config.set('new.key', 'updated_value')
        assert config.get('new.key') == 'updated_value'
    
    def test_save_and_load_config(self, config):
        """Testa salvamento e carregamento de configuração."""
        # Adiciona configurações de teste
        config.set('test.section', {'key': 'value'})
        config.set('test.number', 42)
        
        # Salva configuração
        config.save_config()
        
        # Verifica que arquivo foi criado
        config_file = config.config_dir / "config.yaml"
        assert config_file.exists()
        
        # Cria nova instância e carrega configuração
        new_config = Config()
        new_config.base_dir = config.base_dir
        new_config.config_dir = config.config_dir
        new_config.data_dir = config.data_dir
        new_config.logs_dir = config.logs_dir
        
        # Carrega configurações
        loaded_settings = new_config._load_settings()
        
        # Verifica que configurações foram carregadas
        assert 'test' in loaded_settings
        assert loaded_settings['test']['section']['key'] == 'value'
        assert loaded_settings['test']['number'] == 42
    
    def test_default_settings(self, config):
        """Testa configurações padrão."""
        settings = config._load_settings()
        
        # Verifica seções padrão existem
        assert 'scraping' in settings
        assert 'llm' in settings
        assert 'rag' in settings
        assert 'sheets' in settings
        assert 'monitoring' in settings
        assert 'performance' in settings
        
        # Verifica valores padrão
        assert settings['scraping']['delay_seconds'] > 0
        assert settings['scraping']['max_retries'] > 0
        assert isinstance(settings['scraping']['respect_robots_txt'], bool)
    
    def test_environment_variables_override(self, config):
        """Testa sobrescrita por variáveis de ambiente."""
        with patch.dict(os.environ, {'SCRAPING_DELAY_SECONDS': '5'}):
            settings = config._load_settings()
            assert settings['scraping']['delay_seconds'] == 5
    
    def test_invalid_config_file(self, config):
        """Testa tratamento de arquivo de configuração inválido."""
        # Cria arquivo YAML inválido
        config_file = config.config_dir / "config.yaml"
        config_file.write_text("invalid: yaml: content: [")
        
        # Deve usar configurações padrão
        settings = config._load_settings()
        assert 'scraping' in settings  # Configurações padrão devem estar presentes

if __name__ == "__main__":
    pytest.main([__file__, "-v"])