"""
Módulo de configuração e gerenciamento do sistema de automação.
"""

import os
import yaml
from pathlib import Path
from dotenv import load_dotenv
from loguru import logger
from typing import Dict, Any, Optional

# Carrega variáveis de ambiente
load_dotenv()

class Config:
    """Classe de configuração do sistema."""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.config_dir = self.base_dir / "config"
        self.data_dir = self.base_dir / "data"
        self.logs_dir = self.base_dir / "logs"
        
        # Cria diretórios necessários
        self._create_directories()
        
        # Configuração de logging
        self._setup_logging()
        
        # Carrega configurações
        self.settings = self._load_settings()
    
    def _create_directories(self):
        """Cria diretórios necessários."""
        for directory in [self.config_dir, self.data_dir, self.logs_dir]:
            directory.mkdir(exist_ok=True)
    
    def _setup_logging(self):
        """Configura o sistema de logging."""
        log_level = os.getenv("LOG_LEVEL", "INFO")
        log_file = self.logs_dir / "automation.log"
        
        logger.remove()  # Remove handler padrão
        logger.add(
            log_file,
            rotation=os.getenv("LOG_ROTATION", "10 MB"),
            level=log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}"
        )
        logger.add(
            lambda msg: print(msg, end=""),
            level=log_level,
            format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
        )
    
    def _load_settings(self) -> Dict[str, Any]:
        """Carrega configurações do arquivo YAML ou usa padrões."""
        config_file = self.config_dir / "config.yaml"
        
        default_settings = {
            "scraping": {
                "delay_seconds": int(os.getenv("SCRAPING_DELAY_SECONDS", "1")),
                "max_retries": int(os.getenv("MAX_RETRIES", "3")),
                "user_agent": os.getenv("USER_AGENT", "AutomationBot/1.0"),
                "respect_robots_txt": True,
                "timeout": int(os.getenv("TIMEOUT_SECONDS", "30"))
            },
            "llm": {
                "openai_api_key": os.getenv("OPENAI_API_KEY"),
                "llama_model_path": os.getenv("LLAMA_MODEL_PATH"),
                "llama_context_length": int(os.getenv("LLAMA_CONTEXT_LENGTH", "4096")),
                "cache_size": int(os.getenv("CACHE_SIZE", "1000")),
                "preferred_provider": os.getenv("LLM_PREFERRED_PROVIDER"),
                "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY"),
                "gemini_api_key": os.getenv("GEMINI_API_KEY")
            },
            "rag": {
                "persist_directory": os.getenv("CHROMA_PERSIST_DIRECTORY", str(self.data_dir / "chromadb")),
                "collection_name": os.getenv("CHROMA_COLLECTION_NAME", "automation_data"),
                "embedding_model": "sentence-transformers/all-MiniLM-L6-v2"
            },
            "sheets": {
                "credentials_path": os.getenv("GOOGLE_SHEETS_CREDENTIALS_PATH", str(self.config_dir / "google_sheets_credentials.json")),
                "spreadsheet_id": os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID")
            },
            "monitoring": {
                "enable_monitoring": os.getenv("ENABLE_MONITORING", "true").lower() == "true",
                "metrics_port": int(os.getenv("METRICS_PORT", "8000")),
                "alert_email": os.getenv("ALERT_EMAIL")
            },
            "performance": {
                "max_workers": int(os.getenv("MAX_WORKERS", "4")),
                "cache_ttl": 3600
            }
        }
        
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    file_settings = yaml.safe_load(f)
                    # Mescla configurações
                    default_settings.update(file_settings)
                    logger.info("Configurações carregadas de config.yaml")
            except Exception as e:
                logger.warning(f"Erro ao carregar config.yaml: {e}. Usando configurações padrão.")
        
        return default_settings
    
    def get(self, key: str, default: Any = None) -> Any:
        """Obtém uma configuração específica."""
        keys = key.split('.')
        value = self.settings
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any):
        """Define uma configuração específica."""
        keys = key.split('.')
        target = self.settings
        
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        
        target[keys[-1]] = value
        logger.info(f"Configuração {key} atualizada para {value}")
    
    def save_config(self):
        """Salva configurações no arquivo YAML."""
        config_file = self.config_dir / "config.yaml"
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.dump(self.settings, f, default_flow_style=False, allow_unicode=True)
            logger.info("Configurações salvas em config.yaml")
        except Exception as e:
            logger.error(f"Erro ao salvar configurações: {e}")

# Instância global de configuração
config = Config()
