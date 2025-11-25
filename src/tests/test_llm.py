"""
Testes unitários para o módulo de LLMs.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime

from src.llm.router import (
    LLMResponse, BaseLLMProvider, OpenAIProvider, 
    LlamaProvider, LLMCache, LLMRouter
)

class TestLLMResponse:
    """Testes para a classe LLMResponse."""
    
    def test_llm_response_creation(self):
        """Testa criação de resposta LLM."""
        response = LLMResponse(
            content="Test response",
            model="gpt-3.5-turbo",
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            response_time=1.5,
            cached=False
        )
        
        assert response.content == "Test response"
        assert response.model == "gpt-3.5-turbo"
        assert response.usage["total_tokens"] == 30
        assert response.response_time == 1.5
        assert response.cached is False

class TestBaseLLMProvider:
    """Testes para a classe BaseLLMProvider."""
    
    @pytest.fixture
    def provider(self):
        """Cria instância de BaseLLMProvider para testes."""
        return BaseLLMProvider("TestProvider", "test-model")
    
    def test_provider_initialization(self, provider):
        """Testa inicialização do provedor."""
        assert provider.name == "TestProvider"
        assert provider.model_name == "test-model"
        assert provider.is_available is False
        assert provider.request_count == 0
        assert provider.error_count == 0
    
    def test_update_stats_success(self, provider):
        """Testa atualização de estatísticas - sucesso."""
        provider.update_stats(True, 1.5)
        
        assert provider.request_count == 1
        assert provider.error_count == 0
        assert provider.total_response_time == 1.5
    
    def test_update_stats_failure(self, provider):
        """Testa atualização de estatísticas - falha."""
        provider.update_stats(False, 1.0)
        
        assert provider.request_count == 1
        assert provider.error_count == 1
        assert provider.total_response_time == 1.0
    
    def test_get_stats(self, provider):
        """Testa obtenção de estatísticas."""
        # Adiciona algumas estatísticas
        provider.update_stats(True, 1.0)
        provider.update_stats(True, 2.0)
        provider.update_stats(False, 0.5)
        
        stats = provider.get_stats()
        
        assert stats['name'] == "TestProvider"
        assert stats['model_name'] == "test-model"
        assert stats['is_available'] is False
        assert stats['request_count'] == 3
        assert stats['error_count'] == 1
        assert stats['success_rate'] == 2/3
        assert stats['avg_response_time'] == 1.5  # (1.0 + 2.0) / 2

class TestLLMCache:
    """Testes para a classe LLMCache."""
    
    @pytest.fixture
    def cache(self):
        """Cria instância de LLMCache para testes."""
        return LLMCache(max_size=100, ttl_hours=1)
    
    def test_cache_initialization(self, cache):
        """Testa inicialização do cache."""
        assert cache is not None
        assert cache.max_size == 100
        assert cache.ttl.total_seconds() == 3600  # 1 hora
        assert len(cache.cache) == 0
    
    def test_generate_key(self, cache):
        """Testa geração de chave de cache."""
        key1 = cache._generate_key("prompt test", "model1", temperature=0.7)
        key2 = cache._generate_key("prompt test", "model1", temperature=0.7)
        key3 = cache._generate_key("prompt test", "model2", temperature=0.7)
        key4 = cache._generate_key("prompt test", "model1", temperature=0.8)
        
        assert key1 == key2  # Mesmos parâmetros = mesma chave
        assert key1 != key3  # Modelo diferente
        assert key1 != key4  # Parâmetro diferente
    
    def test_cache_set_and_get(self, cache):
        """Testa armazenamento e recuperação de cache."""
        response = LLMResponse(
            content="Cached response",
            model="test-model",
            usage={"total_tokens": 10},
            response_time=1.0
        )
        
        # Armazena no cache
        cache.set("test prompt", "test-model", response, temperature=0.7)
        
        # Recupera do cache
        cached_response = cache.get("test prompt", "test-model", temperature=0.7)
        
        assert cached_response is not None
        assert cached_response.content == "Cached response"
        assert cached_response.cached is True
    
    def test_cache_miss(self, cache):
        """Testa miss do cache."""
        response = cache.get("nonexistent prompt", "test-model")
        assert response is None
    
    def test_cache_expiration(self, cache):
        """Testa expiração de cache."""
        import datetime as dt
        
        # Mock datetime para simular expiração
        with patch('datetime.datetime') as mock_datetime:
            # Tempo inicial
            mock_datetime.now.return_value = dt.datetime(2023, 1, 1, 10, 0, 0)
            
            response = LLMResponse(
                content="Cached response",
                model="test-model",
                usage={"total_tokens": 10},
                response_time=1.0
            )
            
            cache.set("test prompt", "test-model", response)
            
            # Tempo futuro (mais que TTL)
            mock_datetime.now.return_value = dt.datetime(2023, 1, 1, 12, 0, 1)
            
            cached_response = cache.get("test prompt", "test-model")
            assert cached_response is None  # Deve ter expirado
    
    def test_cache_size_limit(self, cache):
        """Testa limite de tamanho do cache."""
        cache.max_size = 3  # Reduz para testar
        
        # Adiciona itens até o limite
        for i in range(3):
            response = LLMResponse(
                content=f"Response {i}",
                model="test-model",
                usage={"total_tokens": i},
                response_time=1.0
            )
            cache.set(f"prompt {i}", "test-model", response)
        
        assert len(cache.cache) == 3
        
        # Adiciona um item extra (deve remover o mais antigo)
        response = LLMResponse(
            content="Extra response",
            model="test-model",
            usage={"total_tokens": 999},
            response_time=1.0
        )
        cache.set("extra prompt", "test-model", response)
        
        assert len(cache.cache) == 3  # Ainda deve ter 3
        
        # O primeiro item deve ter sido removido
        first_response = cache.get("prompt 0", "test-model")
        assert first_response is None
    
    def test_cache_clear(self, cache):
        """Testa limpeza do cache."""
        # Adiciona alguns itens
        response = LLMResponse(
            content="Test response",
            model="test-model",
            usage={"total_tokens": 10},
            response_time=1.0
        )
        cache.set("test prompt", "test-model", response)
        
        assert len(cache.cache) > 0
        
        # Limpa cache
        cache.clear()
        
        assert len(cache.cache) == 0
        assert len(cache.access_order) == 0
    
    def test_cache_stats(self, cache):
        """Testa estatísticas do cache."""
        # Adiciona alguns itens
        for i in range(5):
            response = LLMResponse(
                content=f"Response {i}",
                model="test-model",
                usage={"total_tokens": i},
                response_time=1.0
            )
            cache.set(f"prompt {i}", "test-model", response)
        
        stats = cache.get_stats()
        
        assert stats['size'] == 5
        assert stats['max_size'] == 100
        assert stats['ttl_hours'] == 1
        assert stats['usage_percentage'] == 5.0

class TestLLMRouter:
    """Testes para a classe LLMRouter."""
    
    @pytest.fixture
    def router(self):
        """Cria instância de LLMRouter para testes."""
        with patch('src.llm.router.OpenAIProvider') as mock_openai:
            with patch('src.llm.router.LlamaProvider') as mock_llama:
                with patch('src.llm.router.config'):
                    # Mock provedores disponíveis
                    mock_openai_instance = Mock()
                    mock_openai_instance.is_available = True
                    mock_openai.return_value = mock_openai_instance
                    
                    mock_llama_instance = Mock()
                    mock_llama_instance.is_available = False
                    mock_llama.return_value = mock_llama_instance
                    
                    router = LLMRouter()
                    router.providers = {
                        'openai': mock_openai_instance,
                        'llama': mock_llama_instance
                    }
                    
                    return router
    
    def test_router_initialization(self, router):
        """Testa inicialização do roteador."""
        assert router is not None
        assert hasattr(router, 'providers')
        assert hasattr(router, 'cache')
        assert isinstance(router.cache, LLMCache)
        assert router.fallback_enabled is True
    
    def test_select_provider_available(self, router):
        """Testa seleção de provedor disponível."""
        provider = router.select_provider("test prompt")
        
        assert provider is not None
        assert provider.is_available is True
    
    def test_select_provider_preferred(self, router):
        """Testa seleção de provedor preferido."""
        provider = router.select_provider("test prompt", preferred_provider="openai")
        
        assert provider is not None
        assert provider.is_available is True
    
    def test_select_provider_unavailable_preferred(self, router):
        """Testa seleção quando provedor preferido não está disponível."""
        provider = router.select_provider("test prompt", preferred_provider="llama")
        
        # Deve selecionar outro provedor disponível
        assert provider is not None
        assert provider.is_available is True
        assert provider != router.providers['llama']  # Não deve ser o LLaMA indisponível
    
    @pytest.mark.asyncio
    async def test_generate_response_with_cache(self, router):
        """Testa geração de resposta com cache."""
        # Mock cache hit
        cached_response = LLMResponse(
            content="Cached response",
            model="test-model",
            usage={"total_tokens": 10},
            response_time=0.1,
            cached=True
        )
        
        router.cache.get = Mock(return_value=cached_response)
        
        response = await router.generate_response("test prompt", use_cache=True)
        
        assert response is not None
        assert response.cached is True
        assert response.content == "Cached response"
    
    @pytest.mark.asyncio
    async def test_generate_response_no_cache(self, router):
        """Testa geração de resposta sem cache."""
        # Mock cache miss
        router.cache.get = Mock(return_value=None)
        
        # Mock resposta do provedor
        mock_response = LLMResponse(
            content="Generated response",
            model="test-model",
            usage={"total_tokens": 20},
            response_time=1.0
        )
        
        mock_provider = router.providers['openai']
        mock_provider.generate_response = AsyncMock(return_value=mock_response)
        
        response = await router.generate_response("test prompt", use_cache=True)
        
        assert response is not None
        assert response.content == "Generated response"
        assert response.cached is False
    
    @pytest.mark.asyncio
    async def test_generate_response_with_fallback(self, router):
        """Testa geração de resposta com fallback."""
        # Mock cache miss
        router.cache.get = Mock(return_value=None)
        
        # Mock erro no provedor principal
        mock_provider = router.providers['openai']
        mock_provider.generate_response = AsyncMock(side_effect=Exception("Provider error"))
        
        # Mock resposta de fallback
        mock_fallback_response = LLMResponse(
            content="Fallback response",
            model="fallback-model",
            usage={"total_tokens": 15},
            response_time=2.0
        )
        
        # Adiciona outro provedor como fallback
        mock_fallback_provider = Mock()
        mock_fallback_provider.is_available = True
        mock_fallback_provider.generate_response = AsyncMock(return_value=mock_fallback_response)
        router.providers['fallback'] = mock_fallback_provider
        
        response = await router.generate_response("test prompt")
        
        assert response is not None
        assert response.content == "Fallback response"
    
    def test_get_provider_stats(self, router):
        """Testa obtenção de estatísticas de provedores."""
        stats = router.get_provider_stats()
        
        assert isinstance(stats, dict)
        assert 'openai' in stats
        assert 'llama' in stats
        
        for provider_name, provider_stats in stats.items():
            assert 'name' in provider_stats
            assert 'is_available' in provider_stats
            assert 'request_count' in provider_stats
    
    def test_get_available_providers(self, router):
        """Testa obtenção de provedores disponíveis."""
        available = router.get_available_providers()
        
        assert isinstance(available, list)
        assert 'openai' in available
        assert 'llama' not in available  # Está indisponível nos testes
    
    def test_clear_cache(self, router):
        """Testa limpeza de cache."""
        # Adiciona item ao cache
        response = LLMResponse(
            content="Test response",
            model="test-model",
            usage={"total_tokens": 10},
            response_time=1.0
        )
        router.cache.set("test", "model", response)
        
        assert router.cache.get_stats()['size'] > 0
        
        # Limpa cache
        router.clear_cache()
        
        assert router.cache.get_stats()['size'] == 0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])