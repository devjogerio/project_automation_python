"""
Assistente virtual com reconhecimento de intenções e geração de respostas contextualizadas.
"""

import re
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from loguru import logger

from llm.router import llm_router
from rag.processor import rag_processor
from rag.vector_store import vector_store
from scraping.orchestrator import scraping_orchestrator
from sheets.sync_manager import sheets_sync


class IntentType(Enum):
    """Tipos de intenções do assistente."""
    GREETING = "greeting"
    SCRAPING_CONTROL = "scraping_control"
    DATA_QUERY = "data_query"
    RAG_QUERY = "rag_query"
    SYSTEM_INFO = "system_info"
    CONFIGURATION = "configuration"
    HELP = "help"
    UNKNOWN = "unknown"


@dataclass
class Intent:
    """Representa uma intenção detectada."""
    type: IntentType
    confidence: float
    entities: Dict[str, Any]
    original_text: str


class IntentRecognizer:
    """Reconhecedor de intenções com base em padrões e ML."""

    def __init__(self):
        self.patterns = {
            IntentType.GREETING: [
                r'\b(ol[áa]|oi|hello|hi|bom dia|boa tarde|boa noite)\b',
                r'\b(como vai|tudo bem|tudo certo)\b'
            ],
            IntentType.SCRAPING_CONTROL: [
                r'\b(scrap|scraping|extrair|coletar|buscar)\b.*\b(dados|informa[çc][õo]es|sites?)\b',
                r'\b(iniciar|come[çc]ar|parar|parar|status)\b.*\b(scraping|scraper)\b',
                r'\b(scrap)\b.*\b(site|url|p[áa]gina)\b'
            ],
            IntentType.DATA_QUERY: [
                r'\b(consultar|buscar|procurar|encontrar|listar)\b.*\b(dados|informa[çc][õo]es|resultados)\b',
                r'\b(o que|qual|quais|quantos)\b.*\b(coletado|extra[íi]do|encontrado)\b',
                r'\b(mostrar|exibir|apresentar)\b.*\b(dados|resultados)\b'
            ],
            IntentType.RAG_QUERY: [
                r'\b(sobre|sobre a|sobre o|acerca de|relativo a)\b',
                r'\b(o que [ée]|qual [ée]|explique|descreva|defina)\b',
                r'\b(buscar|procurar|encontrar)\b.*\b(informa[çc][õo]es|conte[úu]do|documentos?)\b'
            ],
            IntentType.SYSTEM_INFO: [
                r'\b(status|estado|informa[çc][õo]es?)\b.*\b(sistema|configura[çc][õa]o)\b',
                r'\b(como|quais)\b.*\b(configurado|configura[çc][õo]es)\b',
                r'\b(estat[íi]sticas|m[ée]tricas|dados)\b.*\b(sistema)\b'
            ],
            IntentType.CONFIGURATION: [
                r'\b(configurar|mudar|alterar|atualizar)\b.*\b(configura[çc][õa]o|par[^a]metro)\b',
                r'\b(adicionar|remover|editar)\b.*\b(site|url|configura[çc][õa]o)\b',
                r'\b(mudar|alterar)\b.*\b(modelo|llm|ia)\b'
            ],
            IntentType.HELP: [
                r'\b(ajuda|help|comandos|instru[çc][õo]es)\b',
                r'\b(como|o que|qual)\b.*\b(fazer|usar|utilizar)\b',
                r'\b(explicar|explica[çc][ãa]o|tutorial)\b'
            ]
        }

    def recognize_intent(self, text: str) -> Intent:
        """Reconhece intenção no texto."""
        text_lower = text.lower().strip()

        # Análise por padrões
        intent_scores = {}

        for intent_type, patterns in self.patterns.items():
            max_score = 0
            for pattern in patterns:
                matches = re.findall(pattern, text_lower, re.IGNORECASE)
                if matches:
                    # Pontuação baseada no número de matches e tamanho do padrão
                    score = len(matches) * (len(pattern) / 100)
                    max_score = max(max_score, score)

            if max_score > 0:
                intent_scores[intent_type] = max_score

        # Se não encontrou padrões, usa análise de palavras-chave
        if not intent_scores:
            intent_scores = self._keyword_analysis(text_lower)

        # Seleciona intenção com maior pontuação
        if intent_scores:
            best_intent = max(intent_scores, key=intent_scores.get)
            # Normaliza confiança
            confidence = min(intent_scores[best_intent] / 2.0, 1.0)
        else:
            best_intent = IntentType.UNKNOWN
            confidence = 0.0

        # Extrai entidades
        entities = self._extract_entities(text)

        return Intent(
            type=best_intent,
            confidence=confidence,
            entities=entities,
            original_text=text
        )

    def _keyword_analysis(self, text: str) -> Dict[IntentType, float]:
        """Análise por palavras-chave quando padrões falham."""
        keywords = {
            IntentType.GREETING: ['ola', 'oi', 'bom', 'boa', 'tarde', 'noite'],
            IntentType.SCRAPING_CONTROL: ['scrap', 'extrair', 'coletar', 'site'],
            IntentType.DATA_QUERY: ['dados', 'informacao', 'resultado', 'mostrar'],
            IntentType.RAG_QUERY: ['sobre', 'explicar', 'definir', 'descrever'],
            IntentType.SYSTEM_INFO: ['status', 'sistema', 'configuracao'],
            IntentType.CONFIGURATION: ['configurar', 'mudar', 'adicionar'],
            IntentType.HELP: ['ajuda', 'comando', 'como', 'instrucao']
        }

        scores = {}
        for intent_type, words in keywords.items():
            score = sum(1 for word in words if word in text)
            if score > 0:
                scores[intent_type] = score

        return scores

    def _extract_entities(self, text: str) -> Dict[str, Any]:
        """Extrai entidades do texto."""
        entities = {}

        # URLs
        urls = re.findall(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text)
        if urls:
            entities['urls'] = urls

        # Números
        numbers = re.findall(r'\b\d+\b', text)
        if numbers:
            entities['numbers'] = [int(n) for n in numbers]

        # Palavras específicas de sites/modelos
        site_keywords = ['site', 'url', 'página', 'página']
        for keyword in site_keywords:
            if keyword in text.lower():
                entities['has_site_keyword'] = True
                break

        # Modelos LLM
        llm_keywords = ['gpt', 'llama', 'openai', 'modelo']
        for keyword in llm_keywords:
            if keyword in text.lower():
                entities['has_llm_keyword'] = True
                entities['mentioned_llm'] = keyword
                break

        return entities


class VirtualAssistant:
    """Assistente virtual principal."""

    def __init__(self):
        self.intent_recognizer = IntentRecognizer()
        self.conversation_history = []
        self.max_history_length = 10

        # Respostas padrão por intenção
        self.default_responses = {
            IntentType.GREETING: [
                "Olá! Sou seu assistente de automação. Como posso ajudar você hoje?",
                "Oi! Estou aqui para ajudar com scraping de dados, consultas e configurações.",
                "Bom dia! Em que posso ser útil para você?"
            ],
            IntentType.HELP: [
                "Posso ajudar você com:\n• Controle de scraping de sites\n• Consultas aos dados coletados\n• Busca semântica em documentos\n• Configurações do sistema\n\nO que você gostaria de fazer?",
                "Comandos disponíveis:\n• 'Iniciar scraping' - Executa coleta de dados\n• 'Mostrar dados' - Exibe informações coletadas\n• 'Buscar sobre [assunto]' - Consulta RAG\n• 'Status do sistema' - Informações do sistema"
            ],
            IntentType.UNKNOWN: [
                "Não entendi sua pergunta. Pode reformular ou digitar 'ajuda' para ver os comandos disponíveis?",
                "Desculpe, não consegui identificar sua intenção. Tente ser mais específico ou digite 'ajuda'."
            ]
        }

    async def process_message(self, message: str, user_id: str = "default") -> Dict[str, Any]:
        """Processa mensagem do usuário."""
        logger.info(f"Processando mensagem de {user_id}: {message}")

        try:
            # Adiciona ao histórico
            self._add_to_history(user_id, "user", message)

            # Reconhece intenção
            intent = self.intent_recognizer.recognize_intent(message)
            logger.info(
                f"Intenção detectada: {intent.type.value} (confiança: {intent.confidence:.2f})")

            # Processa intenção
            response = await self._process_intent(intent, message, user_id)

            # Adiciona resposta ao histórico
            self._add_to_history(user_id, "assistant", response['text'])

            # Adiciona metadados
            response.update({
                'timestamp': datetime.now().isoformat(),
                'user_id': user_id,
                'intent': {
                    'type': intent.type.value,
                    'confidence': intent.confidence,
                    'entities': intent.entities
                }
            })

            logger.info(f"Resposta gerada para {user_id}")
            return response

        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {e}")
            return {
                'text': "Desculpe, ocorreu um erro ao processar sua mensagem. Tente novamente.",
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'user_id': user_id
            }

    async def _process_intent(self, intent: Intent, message: str, user_id: str) -> Dict[str, Any]:
        """Processa intenção detectada."""

        if intent.type == IntentType.GREETING:
            return await self._handle_greeting(intent)

        elif intent.type == IntentType.HELP:
            return await self._handle_help(intent)

        elif intent.type == IntentType.SCRAPING_CONTROL:
            return await self._handle_scraping_control(message, intent)

        elif intent.type == IntentType.DATA_QUERY:
            return await self._handle_data_query(message, intent)

        elif intent.type == IntentType.RAG_QUERY:
            return await self._handle_rag_query(message, intent)

        elif intent.type == IntentType.SYSTEM_INFO:
            return await self._handle_system_info(intent)

        elif intent.type == IntentType.CONFIGURATION:
            return await self._handle_configuration(message, intent)

        else:  # IntentType.UNKNOWN
            return await self._handle_unknown(intent)

    async def _handle_greeting(self, intent: Intent) -> Dict[str, Any]:
        """Lida com saudações."""
        import random
        response_text = random.choice(
            self.default_responses[IntentType.GREETING])

        return {
            'text': response_text,
            'type': 'greeting',
            'confidence': intent.confidence
        }

    async def _handle_help(self, intent: Intent) -> Dict[str, Any]:
        """Lida com pedidos de ajuda."""
        import random
        response_text = random.choice(self.default_responses[IntentType.HELP])

        return {
            'text': response_text,
            'type': 'help',
            'confidence': intent.confidence
        }

    async def _handle_scraping_control(self, message: str, intent: Intent) -> Dict[str, Any]:
        """Lida com controle de scraping."""
        try:
            # Detecta ação específica
            if any(word in message.lower() for word in ['iniciar', 'começar', 'executar', 'rodar']):
                # Inicia scraping
                result = scraping_orchestrator.scrape_all_enabled_sites()

                success_count = sum(
                    1 for r in result.values() if 'error' not in r)
                total_count = len(result)

                response_text = f"Scraping iniciado com sucesso!\n"
                response_text += f"Sites processados: {success_count}/{total_count}\n"

                if success_count < total_count:
                    response_text += f"⚠️ {total_count - success_count} sites com erros"

                return {
                    'text': response_text,
                    'type': 'scraping_start',
                    'data': result,
                    'confidence': intent.confidence
                }

            elif any(word in message.lower() for word in ['status', 'estado', 'situação']):
                # Mostra status do scraping
                status = scraping_orchestrator.get_scheduler_status()

                response_text = "📊 Status do Sistema de Scraping:\n"
                response_text += f"Agendador: {'Ativo' if status['is_running'] else 'Parado'}\n"
                response_text += f"Jobs ativos: {status['active_jobs']}\n"

                if status['jobs']:
                    response_text += "Jobs configurados:\n"
                    for job in status['jobs']:
                        response_text += f"• {job['job_func']} - {job['unit']}\n"

                return {
                    'text': response_text,
                    'type': 'scraping_status',
                    'data': status,
                    'confidence': intent.confidence
                }

            else:
                return {
                    'text': "Comandos de scraping disponíveis:\n• 'Iniciar scraping' - Executa coleta de dados\n• 'Status do scraping' - Mostra informações do sistema",
                    'type': 'scraping_help',
                    'confidence': intent.confidence
                }

        except Exception as e:
            logger.error(f"Erro ao processar controle de scraping: {e}")
            return {
                'text': f"Erro ao processar comando de scraping: {str(e)}",
                'type': 'scraping_error',
                'error': str(e),
                'confidence': intent.confidence
            }

    async def _handle_data_query(self, message: str, intent: Intent) -> Dict[str, Any]:
        """Lida com consultas de dados."""
        try:
            # Busca no banco vetorial por dados coletados
            query = message.replace('mostrar', '').replace(
                'dados', '').replace('informações', '').strip()

            if not query or len(query) < 3:
                return {
                    'text': "Por favor, especifique o que você gostaria de consultar. Ex: 'Mostrar dados sobre política' ou 'Quais sites foram coletados?'",
                    'type': 'data_query_help',
                    'confidence': intent.confidence
                }

            # Realiza busca no RAG
            rag_result = rag_processor.process_query(query)

            if rag_result['retrieved_documents']:
                doc_count = len(rag_result['retrieved_documents'])
                avg_similarity = sum(
                    doc['similarity_score'] for doc in rag_result['retrieved_documents']) / doc_count

                response_text = f"📊 Encontrei {doc_count} documentos relevantes:\n"
                response_text += f"Similaridade média: {avg_similarity:.2f}\n\n"

                # Mostra resumo dos principais resultados
                for i, doc in enumerate(rag_result['retrieved_documents'][:3]):
                    source = doc['metadata'].get('source', 'desconhecido')
                    timestamp = doc['metadata'].get(
                        'timestamp', 'desconhecido')
                    preview = doc['content'][:100] + \
                        "..." if len(doc['content']) > 100 else doc['content']

                    response_text += f"{i+1}. Fonte: {source}\n"
                    response_text += f"   Data: {timestamp}\n"
                    response_text += f"   Preview: {preview}\n\n"

                if doc_count > 3:
                    response_text += f"... e mais {doc_count - 3} documentos"

                return {
                    'text': response_text,
                    'type': 'data_query_result',
                    'data': rag_result,
                    'confidence': intent.confidence
                }
            else:
                return {
                    'text': f"Não encontrei dados relevantes para '{query}'. Tente reformular sua pergunta ou verifique se os dados foram coletados.",
                    'type': 'data_query_empty',
                    'confidence': intent.confidence
                }

        except Exception as e:
            logger.error(f"Erro ao processar consulta de dados: {e}")
            return {
                'text': f"Erro ao consultar dados: {str(e)}",
                'type': 'data_query_error',
                'error': str(e),
                'confidence': intent.confidence
            }

    async def _handle_rag_query(self, message: str, intent: Intent) -> Dict[str, Any]:
        """Lida com consultas RAG (busca semântica)."""
        try:
            # Extrai o tema da consulta
            query = message

            # Remove palavras comuns de consulta
            for word in ['sobre', 'sobre a', 'sobre o', 'acerca de', 'relativo a']:
                query = query.replace(word, '').strip()

            if len(query) < 3:
                return {
                    'text': "Por favor, seja mais específico sobre o que você gostaria de saber.",
                    'type': 'rag_query_help',
                    'confidence': intent.confidence
                }

            # Realiza consulta RAG
            rag_result = rag_processor.process_query(query)

            if rag_result['retrieved_documents']:
                # Gera resumo contextualizado
                context_summary = rag_processor.generate_context_summary(
                    rag_result['context'],
                    max_length=800
                )

                doc_count = len(rag_result['retrieved_documents'])
                confidence = rag_result['context_analysis'].get(
                    'relevance_score', 0)

                response_text = f"📚 Informações sobre '{query}':\n\n"
                response_text += f"{context_summary}\n\n"
                response_text += f"📊 Contexto baseado em {doc_count} documentos\n"
                response_text += f"📈 Relevância: {confidence:.2f}\n"

                # Adiciona fontes se disponíveis
                sources = set()
                for doc in rag_result['retrieved_documents'][:3]:
                    source = doc['metadata'].get('source', 'desconhecido')
                    sources.add(source)

                if sources:
                    response_text += f"📄 Fontes: {', '.join(sources)}"

                return {
                    'text': response_text,
                    'type': 'rag_query_result',
                    'data': rag_result,
                    'confidence': intent.confidence
                }
            else:
                return {
                    'text': f"Não encontrei informações relevantes sobre '{query}' no banco de dados. Tente reformular ou aguarde novos dados serem coletados.",
                    'type': 'rag_query_empty',
                    'confidence': intent.confidence
                }

        except Exception as e:
            logger.error(f"Erro ao processar consulta RAG: {e}")
            return {
                'text': f"Erro ao processar consulta: {str(e)}",
                'type': 'rag_query_error',
                'error': str(e),
                'confidence': intent.confidence
            }

    async def _handle_system_info(self, intent: Intent) -> Dict[str, Any]:
        """Lida com pedidos de informações do sistema."""
        try:
            # Coleta informações do sistema

            llm_stats = llm_router.get_provider_stats()
            rag_stats = vector_store.get_collection_stats() if vector_store else {
                'error': 'VectorStore indisponível'}

            response_text = "📊 Informações do Sistema:\n\n"

            # Status LLM
            response_text += "🤖 Provedores LLM:\n"
            for provider, stats in llm_stats.items():
                status = "✅" if stats['is_available'] else "❌"
                response_text += f"{status} {provider}: {stats['request_count']} requisições"
                if stats['request_count'] > 0:
                    response_text += f" (taxa de sucesso: {stats['success_rate']:.1%})"
                response_text += "\n"

            # Status RAG
            response_text += f"\n📚 Banco Vetorial:\n"
            response_text += f"Documentos: {rag_stats.get('total_documents', 0)}\n"
            response_text += f"Coleção: {rag_stats.get('collection_name', 'N/A')}\n"

            # Status Scraping
            scraping_status = scraping_orchestrator.get_scheduler_status()
            response_text += f"\n🕷️ Scraping:\n"
            response_text += f"Agendador: {'Ativo' if scraping_status['is_running'] else 'Parado'}\n"
            response_text += f"Jobs ativos: {scraping_status['active_jobs']}\n"

            # Cache
            cache_stats = llm_router.get_cache_stats()
            response_text += f"\n💾 Cache LLM:\n"
            response_text += f"Tamanho: {cache_stats['size']}/{cache_stats['max_size']}\n"
            response_text += f"Uso: {cache_stats['usage_percentage']:.1f}%\n"

            return {
                'text': response_text,
                'type': 'system_info',
                'data': {
                    'llm_stats': llm_stats,
                    'rag_stats': rag_stats,
                    'scraping_status': scraping_status,
                    'cache_stats': cache_stats
                },
                'confidence': intent.confidence
            }

        except Exception as e:
            logger.error(f"Erro ao obter informações do sistema: {e}")
            return {
                'text': f"Erro ao obter informações do sistema: {str(e)}",
                'type': 'system_info_error',
                'error': str(e),
                'confidence': intent.confidence
            }

    async def _handle_configuration(self, message: str, intent: Intent) -> Dict[str, Any]:
        """Lida com comandos de configuração."""
        return {
            'text': "Configurações podem ser ajustadas através da interface gráfica ou editando os arquivos de configuração. Digite 'ajuda' para ver os comandos disponíveis.",
            'type': 'configuration_info',
            'confidence': intent.confidence
        }

    async def _handle_unknown(self, intent: Intent) -> Dict[str, Any]:
        """Lida com intenções desconhecidas."""
        import random
        response_text = random.choice(
            self.default_responses[IntentType.UNKNOWN])

        return {
            'text': response_text,
            'type': 'unknown_intent',
            'confidence': intent.confidence
        }

    def _add_to_history(self, user_id: str, role: str, content: str):
        """Adiciona mensagem ao histórico."""
        entry = {
            'user_id': user_id,
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat()
        }

        self.conversation_history.append(entry)

        # Mantém histórico limitado
        if len(self.conversation_history) > self.max_history_length:
            self.conversation_history.pop(0)

    def get_conversation_history(self, user_id: str = "default", limit: int = 10) -> List[Dict[str, Any]]:
        """Obtém histórico de conversa para um usuário."""
        user_history = [
            entry for entry in self.conversation_history
            if entry['user_id'] == user_id
        ]

        return user_history[-limit:] if limit > 0 else user_history

    def clear_conversation_history(self, user_id: str = None):
        """Limpa histórico de conversa."""
        if user_id:
            self.conversation_history = [
                entry for entry in self.conversation_history
                if entry['user_id'] != user_id
            ]
        else:
            self.conversation_history.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Obtém estatísticas do assistente."""
        total_interactions = len(self.conversation_history)
        user_interactions = {}

        for entry in self.conversation_history:
            user_id = entry['user_id']
            if user_id not in user_interactions:
                user_interactions[user_id] = 0
            user_interactions[user_id] += 1

        return {
            'total_interactions': total_interactions,
            'unique_users': len(user_interactions),
            'user_breakdown': user_interactions,
            'history_size': len(self.conversation_history),
            'max_history_length': self.max_history_length
        }


# Instância global do assistente
virtual_assistant = VirtualAssistant()
