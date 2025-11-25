"""
Módulo de banco vetorial RAG com ChromaDB para armazenamento e busca semântica.
"""

import os
import json
import uuid
from typing import List, Dict, Optional, Any
from datetime import datetime
import re
from pathlib import Path

from typing import TYPE_CHECKING
from loguru import logger
from utils.config import config
import os
from collections import Counter
import math
try:
    import chromadb
    from chromadb.config import Settings
    from chromadb.utils import embedding_functions
    _CHROMA_AVAILABLE = True
except Exception:
    _CHROMA_AVAILABLE = False

class VectorStore:
    """Classe principal para gerenciamento do banco vetorial RAG."""
    
    def __init__(self):
        self.persist_directory = config.get('rag.persist_directory', 'data/chromadb')
        self.collection_name = config.get('rag.collection_name', 'automation_data')
        self.embedding_model = config.get('rag.embedding_model', 'sentence-transformers/all-MiniLM-L6-v2')
        
        # Cria diretório de persistência
        Path(self.persist_directory).mkdir(parents=True, exist_ok=True)
        
        # Inicializa cliente ChromaDB
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Inicializa função de embedding
        if os.getenv('OPENAI_API_KEY'):
            try:
                self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
                    api_key=os.getenv('OPENAI_API_KEY'),
                    model_name=os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small')
                )
            except Exception:
                self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name=self.embedding_model
                )
        else:
            self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=self.embedding_model
            )
        
        # Obtém ou cria coleção
        self.collection = self._get_or_create_collection()
        
        logger.info(f"VectorStore inicializado com coleção '{self.collection_name}'")
    
    def _get_or_create_collection(self) -> Any:
        """Obtém ou cria a coleção de documentos."""
        try:
            return self.client.get_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function
            )
        except Exception:
            logger.info(f"Criando nova coleção '{self.collection_name}'")
            return self.client.create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function,
                metadata={
                    "hnsw:space": "cosine",
                    "hnsw:construction_ef": 100,
                    "hnsw:M": 16
                }
            )
    
    def add_document(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        source: str = "unknown",
        document_id: Optional[str] = None
    ) -> str:
        """Adiciona um documento ao banco vetorial."""
        try:
            # Gera ID único se não fornecido
            if not document_id:
                document_id = str(uuid.uuid4())
            
            # Prepara metadados
            doc_metadata = {
                'source': source,
                'timestamp': datetime.now().isoformat(),
                'content_length': len(content),
                'content_type': 'text'
            }
            
            if metadata:
                doc_metadata.update(metadata)
            
            # Adiciona documento à coleção
            self.collection.add(
                documents=[content],
                metadatas=[doc_metadata],
                ids=[document_id]
            )
            
            logger.info(f"Documento adicionado: {document_id} (fonte: {source})")
            return document_id
            
        except Exception as e:
            logger.error(f"Erro ao adicionar documento: {e}")
            raise
    
    def add_documents_batch(
        self,
        contents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        sources: Optional[List[str]] = None,
        document_ids: Optional[List[str]] = None
    ) -> List[str]:
        """Adiciona múltiplos documentos em lote."""
        try:
            batch_size = 100  # Tamanho do lote para processamento
            all_ids = []
            
            # Prepara listas de dados
            if not document_ids:
                document_ids = [str(uuid.uuid4()) for _ in contents]
            
            if not metadatas:
                metadatas = [{} for _ in contents]
            
            if not sources:
                sources = ['unknown'] * len(contents)
            
            # Processa em lotes
            for i in range(0, len(contents), batch_size):
                batch_end = min(i + batch_size, len(contents))
                
                batch_contents = contents[i:batch_end]
                batch_ids = document_ids[i:batch_end]
                batch_metadatas = []
                
                for j, (content, metadata, source) in enumerate(
                    zip(batch_contents, metadatas[i:batch_end], sources[i:batch_end])
                ):
                    doc_metadata = {
                        'source': source,
                        'timestamp': datetime.now().isoformat(),
                        'content_length': len(content),
                        'content_type': 'text'
                    }
                    doc_metadata.update(metadata)
                    batch_metadatas.append(doc_metadata)
                
                # Adiciona lote à coleção
                self.collection.add(
                    documents=batch_contents,
                    metadatas=batch_metadatas,
                    ids=batch_ids
                )
                
                all_ids.extend(batch_ids)
                logger.info(f"Lote de {len(batch_contents)} documentos adicionado")
            
            logger.success(f"{len(all_ids)} documentos adicionados em lote")
            return all_ids
            
        except Exception as e:
            logger.error(f"Erro ao adicionar documentos em lote: {e}")
            raise
    
    def search(
        self,
        query: str,
        n_results: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None,
        source_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Realiza busca semântica nos documentos."""
        try:
            # Prepara filtros
            where_clause = {}
            if filter_metadata:
                where_clause.update(filter_metadata)
            if source_filter:
                where_clause['source'] = source_filter
            
            # Realiza busca
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_clause if where_clause else None
            )
            
            # Processa resultados
            processed_results = []
            
            if results['documents'] and results['documents'][0]:
                for i, (document, metadata, distance, id_) in enumerate(zip(
                    results['documents'][0],
                    results['metadatas'][0],
                    results['distances'][0],
                    results['ids'][0]
                )):
                    processed_results.append({
                        'id': id_,
                        'content': document,
                        'metadata': metadata,
                        'similarity_score': 1 - distance,  # Converte distância para similaridade
                        'rank': i + 1
                    })
            
            logger.info(f"Busca realizada: '{query}' - {len(processed_results)} resultados")
            return processed_results
            
        except Exception as e:
            logger.error(f"Erro ao realizar busca: {e}")
            return []
    
    def search_by_metadata(
        self,
        metadata_filter: Dict[str, Any],
        n_results: int = 100
    ) -> List[Dict[str, Any]]:
        """Busca documentos por metadados."""
        try:
            results = self.collection.get(
                where=metadata_filter,
                limit=n_results
            )
            
            processed_results = []
            if results['documents']:
                for document, metadata, id_ in zip(
                    results['documents'],
                    results['metadatas'],
                    results['ids']
                ):
                    processed_results.append({
                        'id': id_,
                        'content': document,
                        'metadata': metadata
                    })
            
            logger.info(f"Busca por metadados realizada: {len(processed_results)} resultados")
            return processed_results
            
        except Exception as e:
            logger.error(f"Erro ao buscar por metadados: {e}")
            return []
    
    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Obtém um documento específico por ID."""
        try:
            result = self.collection.get(
                ids=[document_id]
            )
            
            if result['documents'] and result['documents'][0]:
                return {
                    'id': document_id,
                    'content': result['documents'][0],
                    'metadata': result['metadatas'][0]
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao obter documento {document_id}: {e}")
            return None
    
    def update_document(
        self,
        document_id: str,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Atualiza um documento existente."""
        try:
            updates = {}
            
            if content:
                updates['documents'] = [content]
            
            if metadata:
                # Obtém metadados existentes
                existing_doc = self.get_document(document_id)
                if existing_doc:
                    updated_metadata = existing_doc['metadata'].copy()
                    updated_metadata.update(metadata)
                    updated_metadata['updated_at'] = datetime.now().isoformat()
                    updates['metadatas'] = [updated_metadata]
            
            if updates:
                self.collection.update(
                    ids=[document_id],
                    **updates
                )
                logger.info(f"Documento {document_id} atualizado")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Erro ao atualizar documento {document_id}: {e}")
            return False
    
    def delete_document(self, document_id: str) -> bool:
        """Remove um documento do banco vetorial."""
        try:
            self.collection.delete(
                ids=[document_id]
            )
            logger.info(f"Documento {document_id} removido")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao remover documento {document_id}: {e}")
            return False
    
    def delete_by_source(self, source: str) -> int:
        """Remove todos os documentos de uma fonte específica."""
        try:
            # Busca documentos da fonte
            documents = self.search_by_metadata({'source': source})
            
            if documents:
                document_ids = [doc['id'] for doc in documents]
                self.collection.delete(ids=document_ids)
                logger.info(f"{len(document_ids)} documentos da fonte '{source}' removidos")
                return len(document_ids)
            
            return 0
            
        except Exception as e:
            logger.error(f"Erro ao remover documentos da fonte '{source}': {e}")
            return 0
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Obtém estatísticas da coleção."""
        try:
            count = self.collection.count()
            
            # Obtém amostra de metadados para análise
            sample = self.collection.get(limit=10)
            
            sources = {}
            if sample['metadatas']:
                for metadata in sample['metadatas']:
                    source = metadata.get('source', 'unknown')
                    sources[source] = sources.get(source, 0) + 1
            
            return {
                'total_documents': count,
                'collection_name': self.collection_name,
                'embedding_model': self.embedding_model,
                'persist_directory': self.persist_directory,
                'sample_sources': sources,
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {e}")
            return {'error': str(e)}
    
    def create_backup(self, backup_name: str) -> str:
        """Cria backup da coleção."""
        try:
            backup_dir = Path(self.persist_directory) / "backups"
            backup_dir.mkdir(exist_ok=True)
            
            backup_path = backup_dir / f"{backup_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Exporta todos os documentos
            all_docs = self.collection.get()
            
            backup_data = {
                'collection_name': self.collection_name,
                'embedding_model': self.embedding_model,
                'created_at': datetime.now().isoformat(),
                'documents': []
            }
            
            if all_docs['documents']:
                for doc, metadata, id_ in zip(
                    all_docs['documents'],
                    all_docs['metadatas'],
                    all_docs['ids']
                ):
                    backup_data['documents'].append({
                        'id': id_,
                        'content': doc,
                        'metadata': metadata
                    })
            
            # Salva backup
            backup_file = backup_path.with_suffix('.json')
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Backup criado: {backup_file}")
            return str(backup_file)
            
        except Exception as e:
            logger.error(f"Erro ao criar backup: {e}")
            raise
    
    def restore_backup(self, backup_file: str) -> bool:
        """Restaura coleção a partir de backup."""
        try:
            with open(backup_file, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            # Limpa coleção atual
            self.client.delete_collection(self.collection_name)
            
            # Recria coleção
            self.collection = self._get_or_create_collection()
            
            # Restaura documentos
            documents = backup_data.get('documents', [])
            if documents:
                contents = [doc['content'] for doc in documents]
                metadatas = [doc['metadata'] for doc in documents]
                ids = [doc['id'] for doc in documents]
                
                self.add_documents_batch(contents, metadatas, ids=ids)
            
            logger.info(f"Backup restaurado de: {backup_file}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao restaurar backup: {e}")
            return False

class SimpleVectorStore:
    """Implementação simples de banco vetorial em memória sem dependências externas."""

    def __init__(self):
        self.documents: Dict[str, Dict[str, Any]] = {}
        self.vocab: Counter = Counter()
        self.index: Dict[str, Counter] = {}
        self.collection_name = 'memory_collection'
        self.embedding_model = 'bag-of-words'
        self.persist_directory = 'memory'

    def _tokenize(self, text: str) -> List[str]:
        """Tokeniza texto em palavras simples."""
        return [t.lower() for t in re.findall(r"\b\w+\b", text)]

    def _vectorize(self, text: str) -> Counter:
        """Converte texto em vetor de contagem de termos."""
        tokens = self._tokenize(text)
        c = Counter(tokens)
        self.vocab.update(tokens)
        return c

    def _cosine(self, a: Counter, b: Counter) -> float:
        """Calcula similaridade de cosseno entre dois vetores."""
        intersection = set(a) & set(b)
        num = sum(a[t] * b[t] for t in intersection)
        denom_a = math.sqrt(sum(v * v for v in a.values()))
        denom_b = math.sqrt(sum(v * v for v in b.values()))
        if denom_a == 0 or denom_b == 0:
            return 0.0
        return num / (denom_a * denom_b)

    def add_document(self, content: str, metadata: Optional[Dict[str, Any]] = None, source: str = "unknown", document_id: Optional[str] = None) -> str:
        """Adiciona documento ao índice em memória."""
        doc_id = document_id or str(uuid.uuid4())
        self.documents[doc_id] = {
            'content': content,
            'metadata': {
                'source': source,
                'timestamp': datetime.now().isoformat(),
                **(metadata or {})
            }
        }
        self.index[doc_id] = self._vectorize(content)
        return doc_id

    def add_documents_batch(self, contents: List[str], metadatas: Optional[List[Dict[str, Any]]] = None, sources: Optional[List[str]] = None, document_ids: Optional[List[str]] = None) -> List[str]:
        """Adiciona múltiplos documentos."""
        ids = []
        for i, content in enumerate(contents):
            md = metadatas[i] if metadatas and i < len(metadatas) else {}
            src = sources[i] if sources and i < len(sources) else 'unknown'
            did = document_ids[i] if document_ids and i < len(document_ids) else None
            ids.append(self.add_document(content, md, src, did))
        return ids

    def search(self, query: str, n_results: int = 10, filter_metadata: Optional[Dict[str, Any]] = None, source_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Busca por similaridade usando cosseno em bag-of-words."""
        qv = self._vectorize(query)
        results: List[Dict[str, Any]] = []
        for did, vec in self.index.items():
            meta = self.documents[did]['metadata']
            if source_filter and meta.get('source') != source_filter:
                continue
            if filter_metadata and not all(meta.get(k) == v for k, v in filter_metadata.items()):
                continue
            score = self._cosine(qv, vec)
            if score > 0:
                results.append({
                    'id': did,
                    'content': self.documents[did]['content'],
                    'metadata': meta,
                    'similarity_score': score
                })
        results.sort(key=lambda x: x['similarity_score'], reverse=True)
        return results[:n_results]

    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Obtém documento por ID."""
        doc = self.documents.get(document_id)
        if not doc:
            return None
        return {'id': document_id, **doc}

    def update_document(self, document_id: str, content: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Atualiza documento em memória."""
        if document_id not in self.documents:
            return False
        if content:
            self.documents[document_id]['content'] = content
            self.index[document_id] = self._vectorize(content)
        if metadata:
            self.documents[document_id]['metadata'].update(metadata)
        return True

    def delete_document(self, document_id: str) -> bool:
        """Remove documento."""
        if document_id in self.documents:
            del self.documents[document_id]
            self.index.pop(document_id, None)
            return True
        return False

    def get_collection_stats(self) -> Dict[str, Any]:
        """Estatísticas básicas."""
        return {
            'total_documents': len(self.documents),
            'collection_name': self.collection_name,
            'embedding_model': self.embedding_model,
            'persist_directory': self.persist_directory,
            'sample_sources': {},
            'last_updated': datetime.now().isoformat()
        }

    def create_backup(self, backup_name: str) -> str:
        """Cria backup simples em JSON."""
        backup_dir = Path('data/backups')
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = backup_dir / f"{backup_name}.json"
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(self.documents, f, indent=2, ensure_ascii=False)
        return str(backup_path)

    def restore_backup(self, backup_file: str) -> bool:
        """Restaura backup simples."""
        try:
            with open(backup_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.documents = data
            self.index = {did: self._vectorize(doc['content']) for did, doc in data.items()}
            return True
        except Exception:
            return False

# Instância global do banco vetorial
try:
    if _CHROMA_AVAILABLE:
        vector_store = VectorStore()
    else:
        logger.warning("ChromaDB indisponível; usando SimpleVectorStore em memória")
        vector_store = SimpleVectorStore()
except Exception as e:
    logger.warning(f"Falha ao inicializar VectorStore: {e}; usando SimpleVectorStore")
    vector_store = SimpleVectorStore()
