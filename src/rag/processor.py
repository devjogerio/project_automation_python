"""
Módulo de processamento RAG (Retrieval-Augmented Generation) com recuperação inteligente.
"""

import re
from typing import List, Dict, Optional, Any
from datetime import datetime
from loguru import logger

from .vector_store import vector_store


class RAGProcessor:
    """Processador RAG para recuperação e geração de contexto."""

    def __init__(self):
        self.vector_store = vector_store
        self.max_context_length = 4000  # Máximo de caracteres para contexto
        self.similarity_threshold = 0.7   # Limiar mínimo de similaridade
        self.max_retrieved_docs = 10      # Máximo de documentos a recuperar

    def process_query(self, query: str, context_filter: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Processa uma consulta RAG recuperando contexto relevante."""
        try:
            logger.info(f"Processando consulta RAG: '{query}'")

            # Limpa e prepara a consulta
            cleaned_query = self._clean_text(query)

            # Recupera documentos relevantes
            retrieved_docs = self._retrieve_relevant_docs(
                cleaned_query, context_filter)

            # Se não houver documentos relevantes, retorna mensagem informativa
            if not retrieved_docs:
                return {
                    'query': query,
                    'context': '',
                    'retrieved_documents': [],
                    'context_length': 0,
                    'message': 'Nenhum documento relevante encontrado para a consulta.'
                }

            # Constrói contexto a partir dos documentos recuperados
            context = self._build_context(retrieved_docs)

            # Analisa e categoriza o contexto
            context_analysis = self._analyze_context(context, query)

            result = {
                'query': query,
                'cleaned_query': cleaned_query,
                'context': context,
                'context_length': len(context),
                'retrieved_documents': retrieved_docs,
                'num_retrieved_docs': len(retrieved_docs),
                'context_analysis': context_analysis,
                'processing_time': datetime.now().isoformat()
            }

            logger.info(
                f"Consulta RAG processada: {len(retrieved_docs)} documentos recuperados")
            return result

        except Exception as e:
            logger.error(f"Erro ao processar consulta RAG: {e}")
            return {
                'query': query,
                'error': str(e),
                'context': '',
                'retrieved_documents': []
            }

    def _clean_text(self, text: str) -> str:
        """Limpa e normaliza texto."""
        # Remove espaços extras e caracteres especiais
        text = re.sub(r'\s+', ' ', text.strip())
        text = re.sub(r'[^\w\s.,!?;:()-]', '', text)

        # Remove palavras muito curtas (menos de 2 caracteres)
        words = text.split()
        cleaned_words = [word for word in words if len(word) > 2]

        return ' '.join(cleaned_words)

    def _retrieve_relevant_docs(self, query: str, context_filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Recupera documentos relevantes para a consulta."""
        try:
            # Realiza busca semântica
            search_results = self.vector_store.search(
                query=query,
                n_results=self.max_retrieved_docs,
                filter_metadata=context_filter
            )

            # Filtra por limiar de similaridade
            filtered_results = [
                doc for doc in search_results
                if doc['similarity_score'] >= self.similarity_threshold
            ]

            # Ordena por similaridade
            filtered_results.sort(
                key=lambda x: x['similarity_score'], reverse=True)

            logger.info(
                f"Documentos recuperados: {len(filtered_results)} de {len(search_results)}")
            return filtered_results

        except Exception as e:
            logger.error(f"Erro ao recuperar documentos: {e}")
            return []

    def _build_context(self, documents: List[Dict[str, Any]]) -> str:
        """Constrói contexto concatenando documentos relevantes."""
        context_parts = []
        current_length = 0

        for doc in documents:
            content = doc['content']

            # Verifica se adicionar este documento ultrapassa o limite
            if current_length + len(content) > self.max_context_length:
                # Adiciona parte do documento se couber
                remaining_space = self.max_context_length - current_length
                if remaining_space > 100:  # Mínimo de 100 caracteres
                    content_part = content[:remaining_space]
                    context_parts.append(content_part)
                    current_length += len(content_part)
                break

            context_parts.append(content)
            current_length += len(content)

        # Junta os pedaços de contexto
        context = '\n\n'.join(context_parts)

        logger.info(
            f"Contexto construído: {len(context)} caracteres de {len(documents)} documentos")
        return context

    def _analyze_context(self, context: str, query: str) -> Dict[str, Any]:
        """Analisa e categoriza o contexto recuperado."""
        try:
            # Estatísticas básicas
            word_count = len(context.split())
            char_count = len(context)

            # Identifica temas principais (palavras mais frequentes)
            words = re.findall(r'\b\w+\b', context.lower())
            word_freq = {}
            for word in words:
                if len(word) > 3:  # Ignora palavras curtas
                    word_freq[word] = word_freq.get(word, 0) + 1

            # Top 10 palavras mais frequentes
            top_words = sorted(word_freq.items(),
                               key=lambda x: x[1], reverse=True)[:10]

            # Identifica possíveis fontes/categorias
            sources = set()
            dates = set()

            # Tenta extrair datas
            date_patterns = [
                r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
                r'\d{2}/\d{2}/\d{4}',  # MM/DD/YYYY
                r'\d{2}-\d{2}-\d{4}',  # MM-DD-YYYY
            ]

            for pattern in date_patterns:
                found_dates = re.findall(pattern, context)
                dates.update(found_dates)

            analysis = {
                'word_count': word_count,
                'char_count': char_count,
                'top_keywords': [{'word': word, 'frequency': freq} for word, freq in top_words],
                'unique_sources': list(sources),
                'found_dates': list(dates),
                'relevance_score': self._calculate_relevance_score(context, query)
            }

            return analysis

        except Exception as e:
            logger.error(f"Erro ao analisar contexto: {e}")
            return {'error': str(e)}

    def _calculate_relevance_score(self, context: str, query: str) -> float:
        """Calcula pontuação de relevância entre contexto e consulta."""
        try:
            # Palavras-chave da consulta
            query_words = set(self._clean_text(query).lower().split())
            context_words = set(self._clean_text(context).lower().split())

            # Calcula sobreposição
            intersection = query_words.intersection(context_words)
            union = query_words.union(context_words)

            # Similaridade Jaccard
            jaccard_similarity = len(intersection) / len(union) if union else 0

            # Fator de cobertura da consulta
            query_coverage = len(intersection) / \
                len(query_words) if query_words else 0

            # Combina as métricas
            relevance_score = (jaccard_similarity * 0.6 + query_coverage * 0.4)

            return round(relevance_score, 3)

        except Exception as e:
            logger.error(f"Erro ao calcular relevância: {e}")
            return 0.0

    def generate_context_summary(self, context: str, max_length: int = 500) -> str:
        """Gera resumo do contexto recuperado."""
        try:
            # Divide o contexto em sentenças
            sentences = re.split(r'[.!?]+', context)
            sentences = [s.strip() for s in sentences if s.strip()]

            # Seleciona sentenças mais relevantes (primeiras e últimas)
            if len(sentences) <= 3:
                summary_sentences = sentences
            else:
                summary_sentences = [sentences[0], sentences[-1]]
                if len(sentences) > 2:
                    middle_idx = len(sentences) // 2
                    summary_sentences.insert(1, sentences[middle_idx])

            # Junta sentenças e limita tamanho
            summary = '. '.join(summary_sentences)
            if len(summary) > max_length:
                summary = summary[:max_length].rsplit(' ', 1)[0] + '...'

            return summary

        except Exception as e:
            logger.error(f"Erro ao gerar resumo: {e}")
            return context[:max_length] + '...' if len(context) > max_length else context

    def create_rag_context_for_llm(self, query: str, context_filter: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Cria contexto RAG otimizado para uso com LLM."""
        try:
            # Processa consulta RAG
            rag_result = self.process_query(query, context_filter)

            if 'error' in rag_result:
                return {
                    'context': '',
                    'sources': [],
                    'confidence': 0.0,
                    'error': rag_result['error']
                }

            # Formata contexto para LLM
            context_parts = [
                "=== CONTEXTO RECUPERADO ===",
                f"Consulta: {query}",
                f"Contexto recuperado de {rag_result['num_retrieved_docs']} documentos:",
                rag_result['context'],
                "\n=== ANÁLISE DO CONTEXTO ===",
                f"Relevância: {rag_result['context_analysis'].get('relevance_score', 0):.3f}",
                f"Tamanho: {rag_result['context_analysis'].get('word_count', 0)} palavras"
            ]

            # Adiciona fontes
            sources = []
            for doc in rag_result['retrieved_documents']:
                source_info = {
                    'id': doc['id'],
                    'source': doc['metadata'].get('source', 'unknown'),
                    'similarity_score': doc['similarity_score'],
                    'timestamp': doc['metadata'].get('timestamp', 'unknown')
                }
                sources.append(source_info)

            return {
                'context': '\n'.join(context_parts),
                'sources': sources,
                'confidence': rag_result['context_analysis'].get('relevance_score', 0),
                'raw_result': rag_result
            }

        except Exception as e:
            logger.error(f"Erro ao criar contexto RAG para LLM: {e}")
            return {
                'context': '',
                'sources': [],
                'confidence': 0.0,
                'error': str(e)
            }


# Instância global do processador RAG
rag_processor = RAGProcessor()
