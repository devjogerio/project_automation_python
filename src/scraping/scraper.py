"""
Módulo de web scraping com tratamento robusto de erros e respeito a robots.txt.
"""

import time
import random
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from urllib.robotparser import RobotFileParser
from typing import List, Dict, Optional, Union
import asyncio
import aiohttp
from loguru import logger
from utils.config import config

class WebScraper:
    """Classe principal para web scraping com tratamento de erros."""
    
    def __init__(self):
        self.delay = config.get('scraping.delay_seconds', 1)
        self.max_retries = config.get('scraping.max_retries', 3)
        self.user_agent = config.get('scraping.user_agent', 'AutomationBot/1.0')
        self.timeout = config.get('scraping.timeout', 30)
        self.respect_robots = config.get('scraping.respect_robots_txt', True)
        
        # Configuração de headers
        self.headers = {
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Cache de robots.txt
        self.robots_cache = {}
    
    def _can_fetch(self, url: str) -> bool:
        """Verifica se pode fazer scraping da URL respeitando robots.txt."""
        if not self.respect_robots:
            return True
        
        try:
            parsed_url = urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

            if base_url not in self.robots_cache:
                robots_url = urljoin(base_url, '/robots.txt')
                rfp = RobotFileParser()
                rfp.set_url(robots_url)
                try:
                    rfp.read()
                    self.robots_cache[base_url] = rfp
                except Exception as e:
                    logger.warning(f"Erro ao acessar robots.txt de {base_url}: {e}")
                    self.robots_cache[base_url] = None

            parser = self.robots_cache.get(base_url)
            if parser:
                return parser.can_fetch(self.user_agent, parsed_url.path or '/')

            return True
            
        except Exception as e:
            logger.error(f"Erro ao verificar robots.txt para {url}: {e}")
            return True
    
    def _make_request_with_retry(self, url: str, method: str = 'GET', **kwargs) -> Optional[requests.Response]:
        """Faz requisição HTTP com retry automático."""
        for attempt in range(self.max_retries):
            try:
                if not self._can_fetch(url):
                    logger.warning(f"Acesso negado por robots.txt: {url}")
                    return None
                
                # Adiciona delay entre tentativas
                if attempt > 0:
                    wait_time = self.delay * (2 ** attempt) + random.uniform(0, 1)
                    logger.info(f"Aguardando {wait_time:.1f}s antes da tentativa {attempt + 1}")
                    time.sleep(wait_time)
                
                response = requests.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    timeout=self.timeout,
                    **kwargs
                )
                
                if response.status_code == 200:
                    logger.success(f"Requisição bem-sucedida: {url}")
                    return response
                elif response.status_code in [429, 503, 504]:  # Rate limit ou servidor ocupado
                    logger.warning(f"Tentativa {attempt + 1} falhou (status {response.status_code}): {url}")
                    continue
                else:
                    logger.error(f"Erro HTTP {response.status_code}: {url}")
                    return response
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Erro na tentativa {attempt + 1} para {url}: {e}")
                if attempt == self.max_retries - 1:
                    logger.error(f"Todas as tentativas falharam para {url}")
                    return None
        
        return None
    
    def scrape_static_content(self, url: str, selectors: Optional[Dict[str, str]] = None) -> Dict[str, any]:
        """Faz scraping de conteúdo estático usando BeautifulSoup."""
        logger.info(f"Iniciando scraping estático: {url}")
        
        response = self._make_request_with_retry(url)
        if not response:
            return {'error': 'Failed to fetch content', 'url': url}
        
        try:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove scripts e styles
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Extrai dados básicos
            data = {
                'url': url,
                'title': soup.find('title').get_text().strip() if soup.find('title') else '',
                'meta_description': '',
                'headings': [],
                'links': [],
                'images': [],
                'text_content': '',
                'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Meta descrição
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                data['meta_description'] = meta_desc.get('content', '')
            
            # Headings
            for heading_tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                headings = soup.find_all(heading_tag)
                for heading in headings:
                    data['headings'].append({
                        'level': heading_tag,
                        'text': heading.get_text().strip()
                    })
            
            # Links
            for link in soup.find_all('a', href=True):
                data['links'].append({
                    'text': link.get_text().strip(),
                    'href': urljoin(url, link['href'])
                })
            
            # Imagens
            for img in soup.find_all('img', src=True):
                data['images'].append({
                    'alt': img.get('alt', ''),
                    'src': urljoin(url, img['src'])
                })
            
            # Conteúdo de texto principal
            text_content = soup.get_text()
            lines = [line.strip() for line in text_content.splitlines()]
            data['text_content'] = ' '.join(line for line in lines if line)
            
            # Seletores personalizados
            if selectors:
                for name, selector in selectors.items():
                    elements = soup.select(selector)
                    data[name] = [elem.get_text().strip() for elem in elements]
            
            logger.success(f"Scraping estático concluído: {url}")
            return data
            
        except Exception as e:
            logger.error(f"Erro ao processar conteúdo de {url}: {e}")
            return {'error': str(e), 'url': url}
    
    def scrape_dynamic_content(self, url: str, wait_for: Optional[str] = None, timeout: int = 10) -> Dict[str, any]:
        """Faz scraping de conteúdo dinâmico usando Selenium."""
        logger.info(f"Iniciando scraping dinâmico: {url}")
        
        if not self._can_fetch(url):
            logger.warning(f"Acesso negado por robots.txt: {url}")
            return {'error': 'Access denied by robots.txt', 'url': url}
        
        # Configuração do Chrome
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument(f'--user-agent={self.user_agent}')
        
        driver = None
        try:
            driver = webdriver.Chrome(options=chrome_options)
            driver.set_page_load_timeout(self.timeout)
            
            # Carrega a página
            driver.get(url)
            
            # Aguarda elemento específico se necessário
            if wait_for:
                WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, wait_for))
                )
            
            # Aguarda carregamento adicional
            time.sleep(self.delay)
            
            # Extrai dados
            data = {
                'url': url,
                'title': driver.title,
                'page_source': driver.page_source,
                'current_url': driver.current_url,
                'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            logger.success(f"Scraping dinâmico concluído: {url}")
            return data
            
        except TimeoutException:
            logger.error(f"Timeout ao carregar {url}")
            return {'error': 'Timeout loading page', 'url': url}
        except WebDriverException as e:
            logger.error(f"Erro do WebDriver ao processar {url}: {e}")
            return {'error': str(e), 'url': url}
        except Exception as e:
            logger.error(f"Erro inesperado ao processar {url}: {e}")
            return {'error': str(e), 'url': url}
        finally:
            if driver:
                driver.quit()
    
    async def scrape_multiple_urls(self, urls: List[str], selectors: Optional[Dict[str, str]] = None) -> List[Dict[str, any]]:
        """Faz scraping de múltiplas URLs de forma assíncrona."""
        logger.info(f"Iniciando scraping de {len(urls)} URLs")
        
        async def fetch_url(session: aiohttp.ClientSession, url: str) -> Dict[str, any]:
            try:
                if not self._can_fetch(url):
                    return {'error': 'Access denied by robots.txt', 'url': url}
                
                async with session.get(url, headers=self.headers, timeout=self.timeout) as response:
                    if response.status == 200:
                        content = await response.text()
                        soup = BeautifulSoup(content, 'html.parser')
                        
                        # Processa conteúdo similar ao método síncrono
                        data = {
                            'url': url,
                            'title': soup.find('title').get_text().strip() if soup.find('title') else '',
                            'text_content': soup.get_text().strip(),
                            'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S')
                        }
                        
                        if selectors:
                            for name, selector in selectors.items():
                                elements = soup.select(selector)
                                data[name] = [elem.get_text().strip() for elem in elements]
                        
                        return data
                    else:
                        return {'error': f'HTTP {response.status}', 'url': url}
                        
            except Exception as e:
                logger.error(f"Erro ao buscar {url}: {e}")
                return {'error': str(e), 'url': url}
        
        async with aiohttp.ClientSession() as session:
            tasks = [fetch_url(session, url) for url in urls]
            results = await asyncio.gather(*tasks)
        
        logger.success(f"Scraping assíncrono concluído: {len(results)} resultados")
        return results
    
    def extract_structured_data(self, url: str, schema: Dict[str, str]) -> Dict[str, any]:
        """Extrai dados estruturados baseado em schema JSON-LD ou microdados."""
        logger.info(f"Extraindo dados estruturados de: {url}")
        
        response = self._make_request_with_retry(url)
        if not response:
            return {'error': 'Failed to fetch content', 'url': url}
        
        try:
            soup = BeautifulSoup(response.content, 'html.parser')
            data = {'url': url, 'structured_data': {}, 'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S')}
            
            # Busca por JSON-LD
            json_ld_scripts = soup.find_all('script', type='application/ld+json')
            for script in json_ld_scripts:
                try:
                    import json
                    ld_data = json.loads(script.string)
                    if isinstance(ld_data, dict):
                        data['structured_data'].update(ld_data)
                except json.JSONDecodeError:
                    continue
            
            # Busca por microdados
            microdata_items = soup.find_all(attrs={'itemscope': True})
            for item in microdata_items:
                item_type = item.get('itemtype', '')
                if item_type:
                    properties = {}
                    for prop in item.find_all(attrs={'itemprop': True}):
                        prop_name = prop.get('itemprop')
                        prop_value = prop.get_text().strip() or prop.get('content', '')
                        if prop_name and prop_value:
                            properties[prop_name] = prop_value
                    
                    if properties:
                        if item_type not in data['structured_data']:
                            data['structured_data'][item_type] = []
                        data['structured_data'][item_type].append(properties)
            
            # Aplica schema personalizado se fornecido
            if schema:
                custom_data = {}
                for field, selector in schema.items():
                    elements = soup.select(selector)
                    custom_data[field] = [elem.get_text().strip() for elem in elements]
                data['custom_schema'] = custom_data
            
            logger.success(f"Dados estruturados extraídos de: {url}")
            return data
            
        except Exception as e:
            logger.error(f"Erro ao extrair dados estruturados de {url}: {e}")
            return {'error': str(e), 'url': url}

# Instância global do scraper
scraper = WebScraper()
