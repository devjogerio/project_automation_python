"""
Testes unitários para o módulo RAG (Retrieval-Augmented Generation).
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.rag.vector_store import VectorStore
from src.rag.processor import RAGProcessor

class TestVectorStore:
    """Testes para a classe VectorStore."""
    
    @pytest.fixture
    def vector_store(self):
        """Cria instância de VectorStore para testes."""
        with patch('src.rag.vector_store.chromadb.PersistentClient'):
            with patch('src.rag.vector_store.embedding_functions.SentenceTransformerEmbeddingFunction'):
                with patch('src.rag.vector_store.config'):
                    store = VectorStore()
                    store.collection = Mock()
                    return store
    
    def test_vector_store_initialization(self, vector_store):
        """Testa inicialização do banco vetorial."""
        assert vector_store is not None
        assert hasattr(vector_store, 'collection')
        assert hasattr(vector_store, 'embedding_function')
    
    def test_add_document(self, vector_store):
        """Testa adição de documento."""
        content = "Test document content"
        metadata = {"source": "test", "type": "document"}
        
        result = vector_store.add_document(content, metadata, "test_source")
        
        assert isinstance(result, str)
        assert len(result) > 0  # UUID
        
        # Verifica que collection.add foi chamado
        vector_store.collection.add.assert_called_once()
        call_args = vector_store.collection.add.call_args
        
        assert 'documents' in call_args[1]
        assert 'metadatas' in call_args[1]
        assert 'ids' in call_args[1]
        assert call_args[1]['documents'] == [content]
    
    def test_add_documents_batch(self, vector_store):
        """Testa adição de múltiplos documentos em lote."""
        contents = ["Doc 1", "Doc 2", "Doc 3"]
        metadatas = [{"id": 1}, {"id": 2}, {"id": 3}]
        sources = ["source1", "source2", "source3"]
        
        result = vector_store.add_documents_batch(contents, metadatas, sources)
        
        assert isinstance(result, list)
        assert len(result) == 3
        
        # Verifica que collection.add foi chamado
        vector_store.collection.add.assert_called_once()
    
    def test_search(self, vector_store):
        """Testa busca semântica."""
        # Mock resultado da busca
        vector_store.collection.query.return_value = {
            'documents': [["Result 1", "Result 2"]],
            'metadatas': [[{"source": "test1"}, {"source": "test2"}]],
            'distances': [[0.1, 0.2]],
            'ids': [["id1", "id2"]]
        }
        
        results = vector_store.search("test query", n_results=2)
        
        assert isinstance(results, list)
        assert len(results) == 2
        
        # Verifica estrutura dos resultados
        for result in results:
            assert 'id' in result
            assert 'content' in result
            assert 'metadata' in result
            assert 'similarity_score' in result
            assert 'rank' in result
            assert result['similarity_score'] >= 0
            assert result['similarity_score'] <= 1
    
    def test_search_by_metadata(self, vector_store):
        """Testa busca por metadados."""
        # Mock resultado
        vector_store.collection.get.return_value = {
            'documents': ["Doc 1", "Doc 2"],
            'metadatas': [{"source": "test1"}, {"source": "test2"}],
            'ids': ["id1", "id2"]
        }
        
        results = vector_store.search_by_metadata({"source": "test1"})
        
        assert isinstance(results, list)
        assert len(results) == 2
        
        # Verifica que collection.get foi chamado com filtros
        vector_store.collection.get.assert_called_once_with(
            where={"source": "test1"},
            limit=100
        )
    
    def test_get_document(self, vector_store):
        """Testa obtenção de documento específico."""
        # Mock resultado
        vector_store.collection.get.return_value = {
            'documents': ["Document content"],
            'metadatas': [{"source": "test"}],
            'ids': ["doc_id"]
        }
        
        result = vector_store.get_document("doc_id")
        
        assert result is not None
        assert result['id'] == "doc_id"
        assert result['content'] == "Document content"
        assert result['metadata']['source'] == "test"
    
    def test_update_document(self, vector_store):
        """Testa atualização de documento."""
        # Mock documento existente
        vector_store.get_document.return_value = {
            'id': 'doc_id',
            'content': 'Old content',
            'metadata': {'source': 'test', 'timestamp': '2023-01-01'}
        }
        
        result = vector_store.update_document("doc_id", "New content", {"updated": True})
        
        assert result is True
        vector_store.collection.update.assert_called_once()
    
    def test_delete_document(self, vector_store):
        """Testa remoção de documento."""
        result = vector_store.delete_document("doc_id")
        
        assert result is True
        vector_store.collection.delete.assert_called_once_with(ids=["doc_id"])
    
    def test_get_collection_stats(self, vector_store):
        """Testa obtenção de estatísticas da coleção."""
        vector_store.collection.count.return_value = 42
        vector_store.collection.get.return_value = {
            'documents': ["Doc 1", "Doc 2"],
            'metadatas': [{"source": "test1"}, {"source": "test2"}],
            'ids': ["id1", "id2"]
        }
        
        stats = vector_store.get_collection_stats()
        
        assert isinstance(stats, dict)
        assert stats['total_documents'] == 42
        assert 'collection_name' in stats
        assert 'embedding_model' in stats
        assert 'sample_sources' in stats

class TestRAGProcessor:
    """Testes para a classe RAGProcessor."""
    
    @pytest.fixture
    def rag_processor(self):
        """Cria instância de RAGProcessor para testes."""
        with patch('src.rag.processor.rag_processor'):
            processor = RAGProcessor()
            processor.vector_store = Mock()
            return processor
    
    def test_rag_processor_initialization(self, rag_processor):
        """Testa inicialização do processador RAG."""
        assert rag_processor is not None
        assert hasattr(rag_processor, 'vector_store')
        assert hasattr(rag_processor, 'max_context_length')
        assert hasattr(rag_processor, 'similarity_threshold')
        assert rag_processor.max_context_length == 4000
        assert rag_processor.similarity_threshold == 0.7
    
    def test_clean_text(self, rag_processor):
        """Testa limpeza de texto."""
        dirty_text = "  This   is   a   test  !  @#$%^&*()  "
        cleaned = rag_processor._clean_text(dirty_text)
        
        assert isinstance(cleaned, str)
        assert len(cleaned) > 0
        assert "  " not in cleaned  # Sem espaços múltiplos
    
    def test_retrieve_relevant_docs(self, rag_processor):
        """Testa recuperação de documentos relevantes."""
        # Mock resultados da busca
        mock_results = [
            {
                'id': 'doc1',
                'content': 'Relevant content 1',
                'metadata': {'source': 'test'},
                'similarity_score': 0.9
            },
            {
                'id': 'doc2',
                'content': 'Relevant content 2',
                'metadata': {'source': 'test'},
                'similarity_score': 0.8
            },
            {
                'id': 'doc3',
                'content': 'Less relevant content',
                'metadata': {'source': 'test'},
                'similarity_score': 0.5  # Abaixo do limiar
            }
        ]
        
        rag_processor.vector_store.search.return_value = mock_results
        
        results = rag_processor._retrieve_relevant_docs("test query")
        
        assert isinstance(results, list)
        assert len(results) == 2  # Apenas documentos acima do limiar
        assert all(doc['similarity_score'] >= 0.7 for doc in results)
    
    def test_build_context(self, rag_processor):
        """Testa construção de contexto."""
        documents = [
            {
                'content': 'First document content. This is the first document.',
                'similarity_score': 0.9
            },
            {
                'content': 'Second document content. This is the second document.',
                'similarity_score': 0.8
            }
        ]
        
        context = rag_processor._build_context(documents)
        
        assert isinstance(context, str)
        assert len(context) > 0
        assert 'First document content' in context
        assert 'Second document content' in context
        assert len(context) <= rag_processor.max_context_length
    
    def test_analyze_context(self, rag_processor):
        """Testa análise de contexto."""
        context = "This is a test context about Python programming. Python is a great language."
        query = "What is Python?"
        
        analysis = rag_processor._analyze_context(context, query)
        
        assert isinstance(analysis, dict)
        assert 'word_count' in analysis
        assert 'char_count' in analysis
        assert 'top_keywords' in analysis
        assert 'relevance_score' in analysis
        assert analysis['word_count'] > 0
        assert analysis['char_count'] > 0
        assert 0 <= analysis['relevance_score'] <= 1
    
    def test_calculate_relevance_score(self, rag_processor):
        """Testa cálculo de pontuação de relevância."""
        context = "Python programming language tutorial guide"
        query = "Python tutorial"
        
        score = rag_processor._calculate_relevance_score(context, query)
        
        assert isinstance(score, float)
        assert 0 <= score <= 1
        assert score > 0  # Deve ter alguma relevância
    
    def test_generate_context_summary(self, rag_processor):
        """Testa geração de resumo de contexto."""
        context = "This is the first sentence. This is the second sentence. This is the third sentence."
        
        summary = rag_processor.generate_context_summary(context, max_length=50)
        
        assert isinstance(summary, str)
        assert len(summary) <= 60  # Um pouco mais que 50 por causa das reticências
        assert len(summary) > 0
    
    def test_process_query_success(self, rag_processor):
        """Testa processamento completo de consulta - sucesso."""
        # Mock documentos recuperados
        mock_docs = [
            {
                'id': 'doc1',
                'content': 'Relevant information about the query.',
                'metadata': {'source': 'test'},
                'similarity_score': 0.85
            }
        ]
        
        rag_processor._retrieve_relevant_docs = Mock(return_value=mock_docs)
        rag_processor._build_context = Mock(return_value="Relevant context")
        rag_processor._analyze_context = Mock(return_value={'relevance_score': 0.8})
        
        result = rag_processor.process_query("test query")
        
        assert isinstance(result, dict)
        assert 'query' in result
        assert 'context' in result
        assert 'retrieved_documents' in result
        assert 'context_analysis' in result
        assert result['query'] == "test query"
        assert len(result['retrieved_documents']) == 1
        assert result['context'] == "Relevant context"
    
    def test_process_query_no_results(self, rag_processor):
        """Testa processamento de consulta sem resultados."""
        rag_processor._retrieve_relevant_docs = Mock(return_value=[])
        
        result = rag_processor.process_query("nonexistent query")
        
        assert isinstance(result, dict)
        assert 'query' in result
        assert 'context' in result
        assert 'message' in result
        assert result['context'] == ''
        assert 'Nenhum documento relevante encontrado' in result['message']
    
    def test_create_rag_context_for_llm(self, rag_processor):
        """Testa criação de contexto RAG para uso com LLM."""
        # Mock processamento de consulta
        mock_result = {
            'query': 'test query',
            'context': 'Relevant context',
            'num_retrieved_docs': 2,
            'retrieved_documents': [
                {
                    'id': 'doc1',
                    'metadata': {'source': 'test1'},
                    'similarity_score': 0.9
                },
                {
                    'id': 'doc2',
                    'metadata': {'source': 'test2'},
                    'similarity_score': 0.8
                }
            ],
            'context_analysis': {
                'relevance_score': 0.85
            }
        }
        
        rag_processor.process_query = Mock(return_value=mock_result)
        
        result = rag_processor.create_rag_context_for_llm("test query")
        
        assert isinstance(result, dict)
        assert 'context' in result
        assert 'sources' in result
        assert 'confidence' in result
        assert 'raw_result' in result
        assert result['confidence'] == 0.85
        assert len(result['sources']) == 2
        assert '=== CONTEXTO RECUPERADO ===' in result['context']

if __name__ == "__main__":
    pytest.main([__file__, "-v"])