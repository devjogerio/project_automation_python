"""
Módulo de orquestração de scraping com agendamento e monitoramento.
"""

import asyncio
import schedule
import time
from datetime import datetime
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from loguru import logger

from .scraper import WebScraper
from .site_manager import site_manager, SiteConfig
from utils.config import config
from rag.vector_store import vector_store
from sheets.sync_manager import sheets_sync

class ScrapingOrchestrator:
    """Orquestrador de scraping com agendamento e monitoramento."""
    
    def __init__(self):
        self.scraper = WebScraper()
        self.max_workers = config.get('performance.max_workers', 4)
        self.is_running = False
        self.jobs = []
        
        # Configura agendamentos
        self._setup_schedules()
    
    def _setup_schedules(self):
        """Configura agendamentos baseados nas configurações dos sites."""
        # Limpa agendamentos anteriores
        schedule.clear()
        
        # Obtém sites com agendamento
        sites = site_manager.get_enabled_sites()
        
        for site in sites:
            if site.schedule:
                self._add_schedule(site)
    
    def _add_schedule(self, site: SiteConfig):
        """Adiciona agendamento para um site."""
        try:
            # Parse cron expression simples (ex: "0 9 * * *")
            parts = site.schedule.split()
            if len(parts) == 5:
                minute, hour, day, month, weekday = parts
                
                if minute != '*' and hour != '*':
                    # Agendamento diário em horário específico (formato HH:MM)
                    hhmm = f"{int(hour):02d}:{int(minute):02d}"
                    schedule.every().day.at(hhmm).do(
                        self.scrape_site, site.name
                    ).tag(site.name)
                    
                    logger.info(f"Agendamento configurado para {site.name}: {site.schedule}")
                else:
                    logger.warning(f"Formato de agendamento não suportado: {site.schedule}")
            else:
                logger.warning(f"Formato de agendamento inválido: {site.schedule}")
                
        except Exception as e:
            logger.error(f"Erro ao configurar agendamento para {site.name}: {e}")
    
    def scrape_site(self, site_name: str) -> Dict[str, any]:
        """Executa scraping de um site específico."""
        logger.info(f"Iniciando scraping do site: {site_name}")
        
        site = site_manager.get_site(site_name)
        if not site:
            logger.error(f"Site '{site_name}' não encontrado")
            return {'error': 'Site not found', 'site': site_name}
        
        if not site.enabled:
            logger.warning(f"Site '{site_name}' está desabilitado")
            return {'error': 'Site disabled', 'site': site_name}
        
        try:
            # Executa scraping baseado no tipo
            if site.scraping_type == 'static':
                result = self.scraper.scrape_static_content(site.url, site.selectors)
            elif site.scraping_type == 'dynamic':
                result = self.scraper.scrape_dynamic_content(site.url, site.wait_for)
            else:  # both
                result_static = self.scraper.scrape_static_content(site.url, site.selectors)
                result_dynamic = self.scraper.scrape_dynamic_content(site.url, site.wait_for)
                result = {
                    'static': result_static,
                    'dynamic': result_dynamic,
                    'scraped_at': datetime.now().isoformat()
                }
            
            # Processa e armazena resultados
            if 'error' not in result:
                self._process_scraping_result(site, result)
                logger.success(f"Scraping concluído para {site_name}")
            else:
                logger.error(f"Erro no scraping de {site_name}: {result['error']}")
            
            return result
            
        except Exception as e:
            logger.error(f"Erro ao executar scraping de {site_name}: {e}")
            return {'error': str(e), 'site': site_name}
    
    def _process_scraping_result(self, site: SiteConfig, result: Dict[str, any]):
        """Processa e armazena resultados do scraping."""
        try:
            # Adiciona metadados
            processed_data = {
                'site_name': site.name,
                'site_url': site.url,
                'scraping_type': site.scraping_type,
                'scraped_at': datetime.now().isoformat(),
                'data': result
            }
            
            # Armazena no banco vetorial
            if vector_store:
                vector_store.add_document(
                    content=str(processed_data),
                    metadata=processed_data,
                    source=f"scraping_{site.name}"
                )
            
            # Sincroniza com Google Sheets
            if sheets_sync and sheets_sync.is_configured():
                sheets_sync.sync_scraping_data(processed_data)
            
            logger.info(f"Resultados processados e armazenados para {site.name}")
            
        except Exception as e:
            logger.error(f"Erro ao processar resultados de {site.name}: {e}")
    
    def scrape_multiple_sites(self, site_names: List[str]) -> Dict[str, any]:
        """Executa scraping de múltiplos sites em paralelo."""
        logger.info(f"Iniciando scraping de {len(site_names)} sites")
        
        results = {}
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submete tarefas
            future_to_site = {
                executor.submit(self.scrape_site, site_name): site_name
                for site_name in site_names
            }
            
            # Coleta resultados
            for future in as_completed(future_to_site):
                site_name = future_to_site[future]
                try:
                    result = future.result()
                    results[site_name] = result
                except Exception as e:
                    logger.error(f"Erro ao executar scraping de {site_name}: {e}")
                    results[site_name] = {'error': str(e), 'site': site_name}
        
        logger.info(f"Scraping paralelo concluído: {len(results)} resultados")
        return results
    
    def scrape_all_enabled_sites(self) -> Dict[str, any]:
        """Executa scraping de todos os sites habilitados."""
        enabled_sites = site_manager.get_enabled_sites()
        site_names = [site.name for site in enabled_sites]
        
        return self.scrape_multiple_sites(site_names)
    
    def start_scheduler(self):
        """Inicia o agendador de scraping."""
        if self.is_running:
            logger.warning("Agendador já está em execução")
            return
        
        self.is_running = True
        logger.info("Agendador de scraping iniciado")
        
        try:
            while self.is_running:
                schedule.run_pending()
                time.sleep(60)  # Verifica a cada minuto
                
        except KeyboardInterrupt:
            logger.info("Agendador interrompido pelo usuário")
            self.stop_scheduler()
        except Exception as e:
            logger.error(f"Erro no agendador: {e}")
            self.stop_scheduler()
    
    def stop_scheduler(self):
        """Para o agendador de scraping."""
        self.is_running = False
        schedule.clear()
        logger.info("Agendador de scraping parado")
    
    def get_scheduler_status(self) -> Dict[str, any]:
        """Obtém status do agendador."""
        jobs = schedule.get_jobs()
        
        return {
            'is_running': self.is_running,
            'active_jobs': len(jobs),
            'jobs': [
                {
                    'job_func': job.job_func.__name__ if hasattr(job.job_func, '__name__') else str(job.job_func),
                    'interval': job.interval,
                    'unit': job.unit,
                    'at_time': str(job.at_time) if job.at_time else None,
                    'tags': job.tags
                }
                for job in jobs
            ]
        }
    
    def run_scheduler_async(self):
        """Executa o agendador de forma assíncrona."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_in_executor(None, self.start_scheduler)
        except Exception as e:
            logger.error(f"Erro ao executar agendador assíncrono: {e}")
        finally:
            loop.close()

# Instância global do orquestrador
scraping_orchestrator = ScrapingOrchestrator()
