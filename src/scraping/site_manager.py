"""
Módulo de gerenciamento de sites e configurações de scraping.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from loguru import logger
from utils.config import config

@dataclass
class SiteConfig:
    """Configuração de um site para scraping."""
    name: str
    url: str
    enabled: bool = True
    scraping_type: str = 'static'  # static, dynamic, or both
    selectors: Optional[Dict[str, str]] = None
    wait_for: Optional[str] = None
    schema: Optional[Dict[str, str]] = None
    schedule: Optional[str] = None  # Cron expression
    max_pages: int = 10
    respect_robots_txt: bool = True
    custom_headers: Optional[Dict[str, str]] = None

class SiteManager:
    """Gerenciador de sites e configurações de scraping."""
    
    def __init__(self):
        self.config_file = config.base_dir / "config" / "sites.json"
        self.sites: Dict[str, SiteConfig] = {}
        self.load_sites()
    
    def load_sites(self):
        """Carrega configurações de sites do arquivo JSON."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    sites_data = json.load(f)
                    
                for site_name, site_data in sites_data.items():
                    self.sites[site_name] = SiteConfig(**site_data)
                
                logger.info(f"{len(self.sites)} sites carregados")
            except Exception as e:
                logger.error(f"Erro ao carregar sites: {e}")
                self._create_default_sites()
        else:
            logger.info("Arquivo de sites não encontrado, criando configurações padrão")
            self._create_default_sites()
    
    def _create_default_sites(self):
        """Cria configurações padrão de sites."""
        default_sites = {
            "exemplo_noticias": SiteConfig(
                name="exemplo_noticias",
                url="https://example-news.com",
                scraping_type="static",
                selectors={
                    "titulos": "h1, h2, h3",
                    "artigos": "article",
                    "datas": "time[datetime]",
                    "autores": ".author, .byline"
                },
                max_pages=5,
                schedule="0 9 * * *"  # 9h da manhã todos os dias
            ),
            "exemplo_produtos": SiteConfig(
                name="exemplo_produtos",
                url="https://example-shop.com",
                scraping_type="dynamic",
                wait_for=".product-grid",
                selectors={
                    "produtos": ".product-item",
                    "precos": ".price",
                    "nomes": ".product-name",
                    "imagens": ".product-image img"
                },
                max_pages=3,
                schedule="0 12 * * 1"  # Segundas às 12h
            )
        }
        
        self.sites = default_sites
        self.save_sites()
    
    def add_site(self, site_config: SiteConfig):
        """Adiciona um novo site."""
        self.sites[site_config.name] = site_config
        self.save_sites()
        logger.info(f"Site '{site_config.name}' adicionado")
    
    def remove_site(self, site_name: str):
        """Remove um site."""
        if site_name in self.sites:
            del self.sites[site_name]
            self.save_sites()
            logger.info(f"Site '{site_name}' removido")
        else:
            logger.warning(f"Site '{site_name}' não encontrado")
    
    def get_site(self, site_name: str) -> Optional[SiteConfig]:
        """Obtém configuração de um site."""
        return self.sites.get(site_name)
    
    def get_enabled_sites(self) -> List[SiteConfig]:
        """Obtém lista de sites habilitados."""
        return [site for site in self.sites.values() if site.enabled]
    
    def get_sites_by_schedule(self, schedule: str) -> List[SiteConfig]:
        """Obtém sites por agendamento."""
        return [site for site in self.sites.values() 
                if site.enabled and site.schedule == schedule]
    
    def update_site(self, site_name: str, **kwargs):
        """Atualiza configuração de um site."""
        if site_name in self.sites:
            site = self.sites[site_name]
            for key, value in kwargs.items():
                if hasattr(site, key):
                    setattr(site, key, value)
            self.save_sites()
            logger.info(f"Site '{site_name}' atualizado")
        else:
            logger.warning(f"Site '{site_name}' não encontrado")
    
    def save_sites(self):
        """Salva configurações de sites no arquivo JSON."""
        try:
            sites_data = {}
            for site_name, site_config in self.sites.items():
                sites_data[site_name] = asdict(site_config)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(sites_data, f, indent=2, ensure_ascii=False)
            
            logger.info("Configurações de sites salvas")
        except Exception as e:
            logger.error(f"Erro ao salvar sites: {e}")
    
    def list_sites(self) -> List[Dict[str, any]]:
        """Lista todos os sites com informações básicas."""
        return [
            {
                'name': site.name,
                'url': site.url,
                'enabled': site.enabled,
                'scraping_type': site.scraping_type,
                'schedule': site.schedule
            }
            for site in self.sites.values()
        ]
    
    def validate_site_config(self, site_config: SiteConfig) -> List[str]:
        """Valida configuração de um site."""
        errors = []
        
        if not site_config.name:
            errors.append("Nome do site é obrigatório")
        
        if not site_config.url:
            errors.append("URL do site é obrigatória")
        
        if site_config.scraping_type not in ['static', 'dynamic', 'both']:
            errors.append("Tipo de scraping deve ser 'static', 'dynamic' ou 'both'")
        
        if site_config.max_pages <= 0:
            errors.append("Número máximo de páginas deve ser maior que 0")
        
        return errors

# Instância global do gerenciador de sites
site_manager = SiteManager()
