"""
Módulo de integração com Google Sheets para sincronização de dados.
"""

import os
import json
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path
from loguru import logger

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    logger.warning("Google API libraries não disponíveis")

from utils.config import config

class GoogleSheetsSync:
    """Sincronizador de dados com Google Sheets."""
    
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    
    def __init__(self):
        self.credentials_path = config.get('sheets.credentials_path', 'config/google_sheets_credentials.json')
        self.spreadsheet_id = config.get('sheets.spreadsheet_id')
        self.token_path = 'config/token.json'
        
        self.service = None
        self._configured = False
        
        if GOOGLE_AVAILABLE:
            self._initialize_service()
    
    def _initialize_service(self):
        """Inicializa serviço Google Sheets."""
        try:
            creds = None
            
            # Carrega token existente
            if os.path.exists(self.token_path):
                creds = Credentials.from_authorized_user_file(self.token_path, self.SCOPES)
            
            # Se não há credenciais válidas, faz autenticação
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not os.path.exists(self.credentials_path):
                        logger.warning(f"Arquivo de credenciais não encontrado: {self.credentials_path}")
                        return
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, self.SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                
                # Salva token para uso futuro
                with open(self.token_path, 'w') as token:
                    token.write(creds.to_json())
            
            # Cria serviço
            self.service = build('sheets', 'v4', credentials=creds)
            self._configured = True
            logger.info("Google Sheets service inicializado com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao inicializar Google Sheets service: {e}")
            self._configured = False
    
    def is_configured(self) -> bool:
        """Verifica se o serviço está configurado."""
        return bool(self._configured and self.service is not None and self.spreadsheet_id)
    
    def create_spreadsheet(self, title: str) -> Optional[str]:
        """Cria uma nova planilha."""
        if not self.service:
            logger.error("Serviço Google Sheets não configurado")
            return None
        
        try:
            spreadsheet = {
                'properties': {
                    'title': title
                }
            }
            
            spreadsheet = self.service.spreadsheets().create(
                body=spreadsheet,
                fields='spreadsheetId'
            ).execute()
            
            spreadsheet_id = spreadsheet.get('spreadsheetId')
            logger.info(f"Planilha criada: {spreadsheet_id}")
            
            # Atualiza configuração
            config.set('sheets.spreadsheet_id', spreadsheet_id)
            config.save_config()
            self.spreadsheet_id = spreadsheet_id
            
            return spreadsheet_id
            
        except HttpError as e:
            logger.error(f"Erro ao criar planilha: {e}")
            return None
    
    def create_sheet(self, sheet_name: str, headers: List[str]) -> bool:
        """Cria uma nova aba na planilha."""
        if not self.is_configured():
            logger.error("Google Sheets não configurado")
            return False
        
        try:
            # Verifica se aba já existe
            existing_sheets = self.get_sheet_names()
            if sheet_name in existing_sheets:
                logger.info(f"Aba '{sheet_name}' já existe")
                return True
            
            # Cria nova aba
            request_body = {
                'requests': [{
                    'addSheet': {
                        'properties': {
                            'title': sheet_name,
                            'gridProperties': {
                                'rowCount': 1000,
                                'columnCount': 26
                            }
                        }
                    }
                }]
            }
            
            response = self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body=request_body
            ).execute()
            
            # Adiciona headers
            if headers:
                self.update_sheet_data(sheet_name, [headers], start_row=1)
            
            logger.info(f"Aba '{sheet_name}' criada com sucesso")
            return True
            
        except HttpError as e:
            logger.error(f"Erro ao criar aba '{sheet_name}': {e}")
            return False
    
    def get_sheet_names(self) -> List[str]:
        """Obtém nomes de todas as abas."""
        if not self.is_configured():
            return []
        
        try:
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()
            
            sheets = spreadsheet.get('sheets', [])
            return [sheet['properties']['title'] for sheet in sheets]
            
        except HttpError as e:
            logger.error(f"Erro ao obter nomes das abas: {e}")
            return []
    
    def update_sheet_data(self, sheet_name: str, data: List[List[Any]], start_row: int = 1) -> bool:
        """Atualiza dados de uma aba."""
        if not self.is_configured():
            logger.error("Google Sheets não configurado")
            return False
        
        try:
            # Converte dados para formato adequado
            values = []
            for row in data:
                formatted_row = []
                for cell in row:
                    if isinstance(cell, (dict, list)):
                        formatted_row.append(json.dumps(cell, ensure_ascii=False))
                    elif isinstance(cell, datetime):
                        formatted_row.append(cell.strftime('%Y-%m-%d %H:%M:%S'))
                    else:
                        formatted_row.append(str(cell))
                values.append(formatted_row)
            
            # Determina range baseado nos dados
            num_rows = len(values)
            num_cols = max(len(row) for row in values) if values else 1
            
            range_name = f"{sheet_name}!A{start_row}:{chr(64 + num_cols)}{start_row + num_rows - 1}"
            
            body = {
                'values': values
            }
            
            result = self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            
            updated_cells = result.get('updatedCells', 0)
            logger.info(f"Dados atualizados em '{sheet_name}': {updated_cells} células")
            return True
            
        except HttpError as e:
            logger.error(f"Erro ao atualizar dados da aba '{sheet_name}': {e}")
            return False
    
    def append_sheet_data(self, sheet_name: str, data: List[List[Any]]) -> bool:
        """Adiciona dados ao final de uma aba."""
        if not self.is_configured():
            logger.error("Google Sheets não configurado")
            return False
        
        try:
            # Converte dados para formato adequado
            values = []
            for row in data:
                formatted_row = []
                for cell in row:
                    if isinstance(cell, (dict, list)):
                        formatted_row.append(json.dumps(cell, ensure_ascii=False))
                    elif isinstance(cell, datetime):
                        formatted_row.append(cell.strftime('%Y-%m-%d %H:%M:%S'))
                    else:
                        formatted_row.append(str(cell))
                values.append(formatted_row)
            
            body = {
                'values': values
            }
            
            result = self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range=f"{sheet_name}!A:A",
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
            
            updated_cells = result.get('updates', {}).get('updatedCells', 0)
            logger.info(f"Dados adicionados à aba '{sheet_name}': {updated_cells} células")
            return True
            
        except HttpError as e:
            logger.error(f"Erro ao adicionar dados à aba '{sheet_name}': {e}")
            return False
    
    def get_sheet_data(self, sheet_name: str, range_name: Optional[str] = None) -> Optional[List[List[Any]]]:
        """Obtém dados de uma aba."""
        if not self.is_configured():
            logger.error("Google Sheets não configurado")
            return None
        
        try:
            if range_name:
                range_full = f"{sheet_name}!{range_name}"
            else:
                range_full = sheet_name
            
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_full
            ).execute()
            
            values = result.get('values', [])
            logger.info(f"Dados obtidos da aba '{sheet_name}': {len(values)} linhas")
            return values
            
        except HttpError as e:
            logger.error(f"Erro ao obter dados da aba '{sheet_name}': {e}")
            return None
    
    def sync_scraping_data(self, data: Dict[str, Any]) -> bool:
        """Sincroniza dados de scraping."""
        if not self.is_configured():
            logger.error("Google Sheets não configurado")
            return False
        
        try:
            sheet_name = "Scraping_Data"
            
            # Cria aba se não existir
            if sheet_name not in self.get_sheet_names():
                headers = [
                    'Timestamp', 'Site Name', 'Site URL', 'Scraping Type',
                    'Status', 'Error Message', 'Data Preview'
                ]
                self.create_sheet(sheet_name, headers)
            
            # Prepara dados para sincronização
            timestamp = data.get('scraped_at', datetime.now().isoformat())
            site_name = data.get('site_name', 'unknown')
            site_url = data.get('site_url', '')
            scraping_type = data.get('scraping_type', 'unknown')
            
            # Verifica se houve erro
            has_error = 'error' in data.get('data', {})
            error_message = data.get('data', {}).get('error', '') if has_error else ''
            
            # Preview dos dados (primeiros 200 caracteres)
            data_preview = str(data.get('data', ''))[:200] + '...' if len(str(data.get('data', ''))) > 200 else str(data.get('data', ''))
            
            # Adiciona linha de dados
            row_data = [
                timestamp,
                site_name,
                site_url,
                scraping_type,
                'Error' if has_error else 'Success',
                error_message,
                data_preview
            ]
            
            return self.append_sheet_data(sheet_name, [row_data])
            
        except Exception as e:
            logger.error(f"Erro ao sincronizar dados de scraping: {e}")
            return False
    
    def sync_rag_data(self, query: str, results: List[Dict[str, Any]]) -> bool:
        """Sincroniza dados de consultas RAG."""
        if not self.is_configured():
            logger.error("Google Sheets não configurado")
            return False
        
        try:
            sheet_name = "RAG_Queries"
            
            # Cria aba se não existir
            if sheet_name not in self.get_sheet_names():
                headers = [
                    'Timestamp', 'Query', 'Num Results', 'Avg Similarity',
                    'Context Length', 'Top Source', 'Confidence Score'
                ]
                self.create_sheet(sheet_name, headers)
            
            if not results:
                return True
            
            # Calcula estatísticas
            avg_similarity = sum(doc.get('similarity_score', 0) for doc in results) / len(results)
            total_context_length = sum(len(doc.get('content', '')) for doc in results)
            top_source = results[0].get('metadata', {}).get('source', 'unknown') if results else 'unknown'
            confidence_score = results[0].get('similarity_score', 0) if results else 0
            
            # Adiciona linha de dados
            row_data = [
                datetime.now().isoformat(),
                query,
                len(results),
                round(avg_similarity, 3),
                total_context_length,
                top_source,
                round(confidence_score, 3)
            ]
            
            return self.append_sheet_data(sheet_name, [row_data])
            
        except Exception as e:
            logger.error(f"Erro ao sincronizar dados RAG: {e}")
            return False
    
    def create_dashboard_sheet(self) -> bool:
        """Cria aba de dashboard com estatísticas."""
        if not self.is_configured():
            logger.error("Google Sheets não configurado")
            return False
        
        try:
            sheet_name = "Dashboard"
            
            # Cria aba se não existir
            if sheet_name not in self.get_sheet_names():
                headers = [
                    'Metric', 'Value', 'Last Updated'
                ]
                self.create_sheet(sheet_name, headers)
            
            # Prepara dados do dashboard
            dashboard_data = [
                ['Total Scraping Runs', '0', datetime.now().isoformat()],
                ['Successful Scrapings', '0', datetime.now().isoformat()],
                ['Failed Scrapings', '0', datetime.now().isoformat()],
                ['Total RAG Queries', '0', datetime.now().isoformat()],
                ['Average RAG Confidence', '0', datetime.now().isoformat()],
                ['Last Sync', datetime.now().isoformat(), datetime.now().isoformat()]
            ]
            
            return self.update_sheet_data(sheet_name, dashboard_data, start_row=2)
            
        except Exception as e:
            logger.error(f"Erro ao criar dashboard: {e}")
            return False
    
    def update_dashboard(self, stats: Dict[str, Any]) -> bool:
        """Atualiza dashboard com estatísticas."""
        if not self.is_configured():
            return False
        
        try:
            sheet_name = "Dashboard"
            
            # Prepara dados atualizados
            dashboard_data = [
                ['Total Scraping Runs', str(stats.get('total_scraping_runs', 0)), datetime.now().isoformat()],
                ['Successful Scrapings', str(stats.get('successful_scrapings', 0)), datetime.now().isoformat()],
                ['Failed Scrapings', str(stats.get('failed_scrapings', 0)), datetime.now().isoformat()],
                ['Total RAG Queries', str(stats.get('total_rag_queries', 0)), datetime.now().isoformat()],
                ['Average RAG Confidence', str(round(stats.get('avg_rag_confidence', 0), 3)), datetime.now().isoformat()],
                ['Last Sync', datetime.now().isoformat(), datetime.now().isoformat()]
            ]
            
            return self.update_sheet_data(sheet_name, dashboard_data, start_row=2)
            
        except Exception as e:
            logger.error(f"Erro ao atualizar dashboard: {e}")
            return False

# Instância global do sincronizador
sheets_sync = GoogleSheetsSync()
