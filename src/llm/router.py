"""Integração multi-LLM com roteamento e cache."""

import os
import json
import time
import hashlib
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from dataclasses import dataclass
from loguru import logger

from openai import OpenAI
# Importação do cliente Bedrock
from aws.bedrock_client import BedrockClient
# Importação do LangChain movida para inicialização do provedor LLaMA

from utils.config import config

@dataclass
class LLMResponse:
    """Resposta de LLM normalizada."""
    content: str
    model: str
    usage: Dict[str, int]
    response_time: float
    cached: bool = False
    metadata: Optional[Dict[str, Any]] = None

class BaseLLMProvider(ABC):
    """Base para provedores de LLM."""
    
    def __init__(self, name: str, model_name: str):
        self.name = name
        self.model_name = model_name
        self.is_available = False
        self.last_error = None
        self.request_count = 0
        self.error_count = 0
        self.total_response_time = 0.0
    
    @abstractmethod
    async def generate_response(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """Gera resposta do provedor."""
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Retorna metadados do modelo."""
        pass
    
    def update_stats(self, success: bool, response_time: float):
        """Atualiza métricas internas."""
        self.request_count += 1
        if success:
            self.total_response_time += response_time
        else:
            self.error_count += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna métricas do provedor."""
        avg_response_time = (self.total_response_time / max(1, self.request_count - self.error_count))
        
        return {
            'name': self.name,
            'model_name': self.model_name,
            'is_available': self.is_available,
            'request_count': self.request_count,
            'error_count': self.error_count,
            'success_rate': (self.request_count - self.error_count) / max(1, self.request_count),
            'avg_response_time': avg_response_time,
            'last_error': self.last_error
        }

class OpenAIProvider(BaseLLMProvider):
    """Provedor OpenAI."""
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__("OpenAI", "gpt-3.5-turbo")
        
        try:
            import os
            self.api_key = api_key or os.getenv('OPENAI_API_KEY')
            if not self.api_key:
                raise ValueError("OpenAI API key não configurada")
            
            self.client = OpenAI(api_key=self.api_key)
            self.is_available = True
            logger.info("OpenAI provider inicializado com sucesso")
            
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Erro ao inicializar OpenAI provider: {e}")
    
    async def generate_response(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """Gera resposta via OpenAI Chat."""
        start_time = time.time()
        
        try:
            messages = [
                {"role": "system", "content": "Você é um assistente útil e prestativo."},
                {"role": "user", "content": prompt}
            ]
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )
            
            response_time = time.time() - start_time
            
            result = LLMResponse(
                content=response.choices[0].message.content,
                model=self.model_name,
                usage={
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                },
                response_time=response_time,
                metadata={
                    'finish_reason': response.choices[0].finish_reason,
                    'system_fingerprint': response.system_fingerprint
                }
            )
            
            self.update_stats(True, response_time)
            logger.info(f"OpenAI resposta gerada em {response_time:.2f}s")
            return result
            
        except Exception as e:
            response_time = time.time() - start_time
            self.update_stats(False, response_time)
            self.last_error = str(e)
            logger.error(f"Erro ao gerar resposta OpenAI: {e}")
            raise
    
    def get_model_info(self) -> Dict[str, Any]:
        """Metadados do OpenAI."""
        return {
            'provider': 'OpenAI',
            'model_name': self.model_name,
            'max_tokens': 4096,
            'supports_system_messages': True,
            'supports_functions': True,
            'supports_vision': False
        }

class LlamaProvider(BaseLLMProvider):
    """Provedor LLaMA (local)."""
    
    def __init__(self, model_path: Optional[str] = None):
        super().__init__("LLaMA", "llama-2-7b-chat")
        
        try:
            # Importa LangChain dinamicamente para evitar falha na carga do módulo
            try:
                from langchain.llms import LlamaCpp
                from langchain.callbacks.manager import CallbackManager
                from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
            except Exception as e:
                raise RuntimeError(f"Dependências do LangChain não disponíveis: {e}")

            self.model_path = model_path or config.get('llama_model_path')
            if not self.model_path or not os.path.exists(self.model_path):
                raise ValueError(f"LLaMA model não encontrado em: {self.model_path}")
            
            # Configura callback manager
            callback_manager = CallbackManager([StreamingStdOutCallbackHandler()])
            
            # Inicializa modelo LLaMA
            self.llm = LlamaCpp(
                model_path=self.model_path,
                n_ctx=config.get('llama_context_length', 4096),
                max_tokens=1000,
                temperature=0.7,
                callback_manager=callback_manager,
                verbose=False,
                n_gpu_layers=0,  # CPU-only por padrão
                n_batch=512,
                f16_kv=True,
                use_mlock=False
            )
            
            self.is_available = True
            logger.info(f"LLaMA provider inicializado com modelo: {self.model_path}")
            
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Erro ao inicializar LLaMA provider: {e}")
    
    async def generate_response(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """Gera resposta via LLaMA local."""
        start_time = time.time()
        
        try:
            # Formata prompt para LLaMA
            formatted_prompt = f"### Human: {prompt}\n### Assistant:"
            
            # Gera resposta
            response = self.llm(
                formatted_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )
            
            response_time = time.time() - start_time
            
            # Extrai conteúdo da resposta
            if isinstance(response, dict):
                content = response.get('choices', [{}])[0].get('text', '')
                usage = response.get('usage', {})
            else:
                content = str(response)
                usage = {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
            
            result = LLMResponse(
                content=content.strip(),
                model=self.model_name,
                usage=usage,
                response_time=response_time
            )
            
            self.update_stats(True, response_time)
            logger.info(f"LLaMA resposta gerada em {response_time:.2f}s")
            return result
            
        except Exception as e:
            response_time = time.time() - start_time
            self.update_stats(False, response_time)
            self.last_error = str(e)
            logger.error(f"Erro ao gerar resposta LLaMA: {e}")
            raise
    
    def get_model_info(self) -> Dict[str, Any]:
        """Metadados do LLaMA."""
        return {
            'provider': 'LLaMA',
            'model_name': self.model_name,
            'max_tokens': config.get('llama_context_length', 4096),
            'supports_system_messages': False,
            'supports_functions': False,
            'supports_vision': False,
            'is_local': True
        }

class BedrockProvider(BaseLLMProvider):
    """Provedor Amazon Bedrock."""

    def __init__(self, region: Optional[str] = None, model_id: Optional[str] = None):
        super().__init__("Bedrock", model_id or os.getenv("BEDROCK_MODEL_ID", ""))

        try:
            self.client = BedrockClient(region_name=region, model_id=model_id)
            # CloudWatch opcional
            self._cw = None
            try:
                from utils.config import config as _cfg
                enable_monitoring = _cfg.get('monitoring.enable_monitoring', True)
                if enable_monitoring:
                    import boto3  # type: ignore
                    self._cw = boto3.client('cloudwatch', region_name=self.client.region)
            except Exception:
                self._cw = None
            if not self.client.is_configured():
                raise RuntimeError(
                    f"Bedrock não configurado (region={self.client.region}, model_id={self.client.model_id})"
                )
            self.is_available = True
            logger.info(
                f"Bedrock provider inicializado na região {self.client.region} com modelo {self.client.model_id}"
            )
        except Exception as e:
            self.last_error = str(e)
            logger.warning(f"Bedrock provider indisponível: {e}")

    async def generate_response(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """Gera resposta usando Amazon Bedrock."""
        start_time = time.time()

        try:
            # Delegado ao BedrockClient
            result = self.client.generate_text(prompt=prompt, max_tokens=max_tokens)

            if result.get("error"):
                raise RuntimeError(result["error"])

            # Parsing por família de modelos com fallback
            raw_response = result.get("response")
            content = ""
            usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

            try:
                # Parsing específico por família de modelos
                model_id = (self.client.model_id or self.model_name or "").lower()
                if isinstance(raw_response, dict):
                    # Anthropic (Claude)
                    if "anthropic" in model_id:
                        # Estrutura comum: {content: [{type: 'text', text: '...'}], usage: {input_tokens, output_tokens}}
                        items = raw_response.get("content") or raw_response.get("messages") or []
                        if isinstance(items, list) and items:
                            first = items[0]
                            content = first.get("text") or first.get("content") or ""
                        usage_data = raw_response.get("usage") or {}
                        usage["prompt_tokens"] = usage_data.get("input_tokens", 0)
                        usage["completion_tokens"] = usage_data.get("output_tokens", 0)
                    # Cohere
                    elif "cohere" in model_id:
                        gens = raw_response.get("generations") or raw_response.get("generation") or []
                        if isinstance(gens, list) and gens:
                            content = gens[0].get("text") or gens[0].get("content") or ""
                        usage_data = raw_response.get("usage") or {}
                        usage["prompt_tokens"] = usage_data.get("prompt_tokens", 0)
                        usage["completion_tokens"] = usage_data.get("generation_tokens", 0)
                    # Titan (Amazon)
                    elif "titan" in model_id or "amazon" in model_id:
                        results = raw_response.get("results") or []
                        if isinstance(results, list) and results:
                            content = results[0].get("outputText") or results[0].get("text") or ""
                        usage_data = raw_response.get("usage") or {}
                        usage["prompt_tokens"] = usage_data.get("inputTokens", 0)
                        usage["completion_tokens"] = usage_data.get("outputTokens", 0)
                    else:
                        # Fallback para campos comuns
                        content = (
                            raw_response.get("outputText")
                            or raw_response.get("generation")
                            or raw_response.get("output")
                            or raw_response.get("text")
                            or ""
                        )
                        usage_data = raw_response.get("usage") or {}
                        for k in ("prompt_tokens", "inputTokens"):
                            usage["prompt_tokens"] = usage_data.get(k, usage["prompt_tokens"])
                        for k in ("completion_tokens", "outputTokens"):
                            usage["completion_tokens"] = usage_data.get(k, usage["completion_tokens"])
                else:
                    content = str(raw_response)
            except Exception:
                content = str(raw_response)

            response_time = time.time() - start_time
            result_obj = LLMResponse(
                content=str(content).strip(),
                model=self.model_name or self.client.model_id,
                usage=usage,
                response_time=response_time,
                metadata={"region": self.client.region}
            )

            # Atualiza tokens totais
            result_obj.usage["total_tokens"] = result_obj.usage.get("prompt_tokens", 0) + result_obj.usage.get("completion_tokens", 0)

            # Métricas CloudWatch (opcional)
            try:
                if self._cw is not None:
                    self._cw.put_metric_data(
                        Namespace="ProjectAutomation/LLM",
                        MetricData=[
                            {"MetricName": "Latency", "Unit": "Milliseconds", "Value": response_time * 1000},
                            {"MetricName": "Requests", "Unit": "Count", "Value": 1},
                            {"MetricName": "Success", "Unit": "Count", "Value": 1},
                        ],
                    )
            except Exception:
                pass

            self.update_stats(True, response_time)
            logger.info(f"Bedrock resposta gerada em {response_time:.2f}s")
            return result_obj

        except Exception as e:
            response_time = time.time() - start_time
            try:
                if self._cw is not None:
                    self._cw.put_metric_data(
                        Namespace="ProjectAutomation/LLM",
                        MetricData=[
                            {"MetricName": "Latency", "Unit": "Milliseconds", "Value": response_time * 1000},
                            {"MetricName": "Requests", "Unit": "Count", "Value": 1},
                            {"MetricName": "Errors", "Unit": "Count", "Value": 1},
                        ],
                    )
            except Exception:
                pass
            self.update_stats(False, response_time)
            self.last_error = str(e)
            logger.error(f"Erro ao gerar resposta Bedrock: {e}")
            raise

    def get_model_info(self) -> Dict[str, Any]:
        """Obtém informações do modelo Bedrock."""
        return {
            'provider': 'Bedrock',
            'model_name': self.model_name or self.client.model_id,
            'max_tokens': 4096,
            'supports_system_messages': True,
            'supports_functions': False,
            'supports_vision': False,
            'region': getattr(self.client, 'region', None)
        }

class SageMakerProvider(BaseLLMProvider):
    """Provedor AWS SageMaker Endpoint."""

    def __init__(self, endpoint_name: Optional[str] = None, region: Optional[str] = None):
        super().__init__("SageMaker", "sagemaker-endpoint")
        try:
            self.endpoint_name = endpoint_name or os.getenv("SAGEMAKER_ENDPOINT_NAME", "")
            self.region = region or os.getenv("AWS_REGION") or "us-east-1"
            import boto3  # type: ignore
            self._rt = boto3.client("sagemaker-runtime", region_name=self.region)
            if not self.endpoint_name:
                raise RuntimeError("SageMaker endpoint não configurado")
            self.is_available = True
            logger.info(f"SageMaker provider inicializado com endpoint {self.endpoint_name}")
        except Exception as e:
            self._rt = None
            self.last_error = str(e)
            logger.warning(f"SageMaker provider indisponível: {e}")

    async def generate_response(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """Gera resposta usando endpoint SageMaker."""
        start_time = time.time()
        try:
            if not (self._rt and self.is_available):
                raise RuntimeError("SageMaker não configurado")
            payload = json.dumps({"prompt": prompt, "max_tokens": max_tokens})
            resp = self._rt.invoke_endpoint(
                EndpointName=self.endpoint_name,
                ContentType="application/json",
                Body=payload,
            )
            content = ""
            usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            try:
                body = resp.get("Body")
                data = body.read() if hasattr(body, "read") else body
                if isinstance(data, (bytes, bytearray)):
                    data = data.decode("utf-8", errors="ignore")
                parsed = json.loads(data)
                content = parsed.get("text") or parsed.get("output") or parsed.get("generation") or ""
                usage_data = parsed.get("usage") or {}
                usage["prompt_tokens"] = usage_data.get("prompt_tokens", 0)
                usage["completion_tokens"] = usage_data.get("completion_tokens", 0)
            except Exception:
                content = ""
            rt = time.time() - start_time
            result = LLMResponse(
                content=str(content).strip(),
                model=self.model_name,
                usage=usage,
                response_time=rt,
                metadata={"endpoint": self.endpoint_name, "region": self.region},
            )
            result.usage["total_tokens"] = result.usage["prompt_tokens"] + result.usage["completion_tokens"]
            self.update_stats(True, rt)
            logger.info(f"SageMaker resposta gerada em {rt:.2f}s")
            return result
        except Exception as e:
            rt = time.time() - start_time
            self.update_stats(False, rt)
            self.last_error = str(e)
            logger.error(f"Erro ao gerar resposta SageMaker: {e}")
            raise

    def get_model_info(self) -> Dict[str, Any]:
        """Obtém informações do endpoint SageMaker."""
        return {
            'provider': 'SageMaker',
            'model_name': self.model_name,
            'endpoint': getattr(self, 'endpoint_name', None),
            'region': getattr(self, 'region', None),
            'supports_system_messages': False,
            'supports_functions': False,
            'supports_vision': False,
        }

class LambdaProvider(BaseLLMProvider):
    """Provedor AWS Lambda invocando função de LLM."""

    def __init__(self, function_name: Optional[str] = None, region: Optional[str] = None):
        super().__init__("Lambda", "lambda-llm")
        try:
            self.function_name = function_name or os.getenv("LAMBDA_FUNCTION_NAME", "")
            self.region = region or os.getenv("AWS_REGION") or "us-east-1"
            import boto3  # type: ignore
            self._lambda = boto3.client("lambda", region_name=self.region)
            if not self.function_name:
                raise RuntimeError("Lambda function não configurada")
            self.is_available = True
            logger.info(f"Lambda provider inicializado com função {self.function_name}")
        except Exception as e:
            self._lambda = None
            self.last_error = str(e)
            logger.warning(f"Lambda provider indisponível: {e}")

    async def generate_response(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """Gera resposta chamando função Lambda."""
        start_time = time.time()
        try:
            if not (self._lambda and self.is_available):
                raise RuntimeError("Lambda não configurado")
            payload = json.dumps({"prompt": prompt, "max_tokens": max_tokens})
            resp = self._lambda.invoke(
                FunctionName=self.function_name,
                InvocationType="RequestResponse",
                Payload=payload,
            )
            content = ""
            usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            try:
                pl = resp.get("Payload")
                data = pl.read() if hasattr(pl, "read") else pl
                if isinstance(data, (bytes, bytearray)):
                    data = data.decode("utf-8", errors="ignore")
                parsed = json.loads(data)
                content = parsed.get("text") or parsed.get("output") or parsed.get("generation") or ""
                usage_data = parsed.get("usage") or {}
                usage["prompt_tokens"] = usage_data.get("prompt_tokens", 0)
                usage["completion_tokens"] = usage_data.get("completion_tokens", 0)
            except Exception:
                content = ""
            rt = time.time() - start_time
            result = LLMResponse(
                content=str(content).strip(),
                model=self.model_name,
                usage=usage,
                response_time=rt,
                metadata={"function": self.function_name, "region": self.region},
            )
            result.usage["total_tokens"] = result.usage["prompt_tokens"] + result.usage["completion_tokens"]
            self.update_stats(True, rt)
            logger.info(f"Lambda resposta gerada em {rt:.2f}s")
            return result
        except Exception as e:
            rt = time.time() - start_time
            self.update_stats(False, rt)
            self.last_error = str(e)
            logger.error(f"Erro ao gerar resposta Lambda: {e}")
            raise

    def get_model_info(self) -> Dict[str, Any]:
        """Obtém informações da função Lambda."""
        return {
            'provider': 'Lambda',
            'model_name': self.model_name,
            'function': getattr(self, 'function_name', None),
            'region': getattr(self, 'region', None),
            'supports_system_messages': False,
            'supports_functions': False,
            'supports_vision': False,
        }

class AnthropicProvider(BaseLLMProvider):
    """Provedor Anthropic (Claude)."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        super().__init__("Anthropic", model or "claude-3-opus-20240229")
        try:
            self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY") or config.get("llm.anthropic_api_key")
            if not self.api_key:
                raise RuntimeError("Anthropic API key não configurada")
            try:
                import anthropic  # type: ignore
                self._client = anthropic.Anthropic(api_key=self.api_key)
                self.is_available = True
                logger.info("Anthropic provider inicializado")
            except Exception as e:
                raise RuntimeError(f"Dependência anthropic ausente: {e}")
        except Exception as e:
            self._client = None
            self.last_error = str(e)
            logger.warning(f"Anthropic provider indisponível: {e}")

    async def generate_response(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7, **kwargs) -> LLMResponse:
        """Gera resposta via Claude."""
        start = time.time()
        try:
            if not (self._client and self.is_available):
                raise RuntimeError("Anthropic não configurado")
            # Claude usa messages API
            resp = self._client.messages.create(
                model=self.model_name,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
            )
            content = ""
            usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            try:
                if getattr(resp, "content", None):
                    # content é lista de partes; pega texto
                    parts = resp.content
                    if isinstance(parts, list) and parts:
                        first = parts[0]
                        content = getattr(first, "text", "") or first.get("text", "")
                usage_data = getattr(resp, "usage", None) or {}
                usage["prompt_tokens"] = usage_data.get("input_tokens", 0)
                usage["completion_tokens"] = usage_data.get("output_tokens", 0)
            except Exception:
                content = str(resp)
            rt = time.time() - start
            out = LLMResponse(content=str(content).strip(), model=self.model_name, usage=usage, response_time=rt)
            out.usage["total_tokens"] = out.usage["prompt_tokens"] + out.usage["completion_tokens"]
            self.update_stats(True, rt)
            logger.info(f"Anthropic resposta gerada em {rt:.2f}s")
            return out
        except Exception as e:
            rt = time.time() - start
            self.update_stats(False, rt)
            self.last_error = str(e)
            logger.error(f"Erro Anthropic: {e}")
            raise

    def get_model_info(self) -> Dict[str, Any]:
        """Metadados do Anthropic."""
        return {
            "provider": "Anthropic",
            "model_name": self.model_name,
            "supports_system_messages": True,
            "supports_functions": False,
            "supports_vision": False,
        }

class GeminiProvider(BaseLLMProvider):
    """Provedor Google Gemini."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        super().__init__("Gemini", model or "gemini-1.5-pro")
        try:
            self.api_key = api_key or os.getenv("GEMINI_API_KEY") or config.get("llm.gemini_api_key")
            if not self.api_key:
                raise RuntimeError("Gemini API key não configurada")
            try:
                import google.generativeai as genai  # type: ignore
                genai.configure(api_key=self.api_key)
                self._model = genai.GenerativeModel(self.model_name)
                self.is_available = True
                logger.info("Gemini provider inicializado")
            except Exception as e:
                raise RuntimeError(f"Dependência google-generativeai ausente: {e}")
        except Exception as e:
            self._model = None
            self.last_error = str(e)
            logger.warning(f"Gemini provider indisponível: {e}")

    async def generate_response(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7, **kwargs) -> LLMResponse:
        """Gera resposta via Gemini."""
        start = time.time()
        try:
            if not (self._model and self.is_available):
                raise RuntimeError("Gemini não configurado")
            resp = self._model.generate_content(prompt)
            content = getattr(resp, "text", None) or getattr(resp, "candidates", [{}])[0].get("content", "")
            usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            rt = time.time() - start
            out = LLMResponse(content=str(content).strip(), model=self.model_name, usage=usage, response_time=rt)
            self.update_stats(True, rt)
            logger.info(f"Gemini resposta gerada em {rt:.2f}s")
            return out
        except Exception as e:
            rt = time.time() - start
            self.update_stats(False, rt)
            self.last_error = str(e)
            logger.error(f"Erro Gemini: {e}")
            raise

    def get_model_info(self) -> Dict[str, Any]:
        """Metadados do Gemini."""
        return {
            "provider": "Gemini",
            "model_name": self.model_name,
            "supports_system_messages": True,
            "supports_functions": False,
            "supports_vision": True,
        }

class LLMCache:
    """Cache de respostas."""
    
    def __init__(self, max_size: int = 1000, ttl_hours: int = 24):
        self.cache = {}
        self.max_size = max_size
        self.ttl = timedelta(hours=ttl_hours)
        self.access_order = []
    
    def _generate_key(self, prompt: str, model: str, **kwargs) -> str:
        """Gera chave única."""
        cache_data = {
            'prompt': prompt,
            'model': model,
            'kwargs': kwargs
        }
        cache_string = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_string.encode()).hexdigest()
    
    def get(self, prompt: str, model: str, **kwargs) -> Optional[LLMResponse]:
        """Busca no cache."""
        key = self._generate_key(prompt, model, **kwargs)
        
        if key in self.cache:
            entry = self.cache[key]
            
            # Verifica se não expirou
            if datetime.now() - entry['timestamp'] < self.ttl:
                # Atualiza ordem de acesso
                self.access_order.remove(key)
                self.access_order.append(key)
                
                logger.debug(f"Cache hit para {model}: {key[:8]}...")
                cached_response = entry['response']
                cached_response.cached = True
                return cached_response
            else:
                # Remove entrada expirada
                del self.cache[key]
                self.access_order.remove(key)
        
        return None
    
    def set(self, prompt: str, model: str, response: LLMResponse, **kwargs):
        """Salva no cache."""
        key = self._generate_key(prompt, model, **kwargs)
        
        # Remove entrada mais antiga se cache estiver cheio
        if len(self.cache) >= self.max_size and key not in self.cache:
            oldest_key = self.access_order.pop(0)
            del self.cache[oldest_key]
        
        # Armazena nova entrada
        self.cache[key] = {
            'response': response,
            'timestamp': datetime.now()
        }
        
        if key not in self.access_order:
            self.access_order.append(key)
        
        logger.debug(f"Cache set para {model}: {key[:8]}...")
    
    def clear(self):
        """Limpa o cache."""
        self.cache.clear()
        self.access_order.clear()
        logger.info("Cache limpo")
    
    def get_stats(self) -> Dict[str, Any]:
        """Métricas do cache."""
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'ttl_hours': self.ttl.total_seconds() / 3600,
            'usage_percentage': (len(self.cache) / self.max_size) * 100
        }

class LLMRouter:
    """Roteador multi-LLM com fallback e cache."""
    
    def __init__(self):
        self.providers: Dict[str, BaseLLMProvider] = {}
        self.cache = LLMCache(
            max_size=config.get('llm.cache_size', 1000)
        )
        self.fallback_enabled = True
        self.default_provider_name: Optional[str] = config.get('llm.preferred_provider')
        
        # Inicializa provedores
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Registra provedores disponíveis."""
        # OpenAI
        try:
            openai_provider = OpenAIProvider()
            if openai_provider.is_available:
                self.providers['openai'] = openai_provider
                logger.info("OpenAI provider registrado")
        except Exception as e:
            logger.warning(f"OpenAI provider não disponível: {e}")
        
        # LLaMA
        try:
            llama_provider = LlamaProvider()
            if llama_provider.is_available:
                self.providers['llama'] = llama_provider
                logger.info("LLaMA provider registrado")
        except Exception as e:
            logger.warning(f"LLaMA provider não disponível: {e}")

        # Bedrock
        try:
            bedrock_provider = BedrockProvider()
            if bedrock_provider.is_available:
                self.providers['bedrock'] = bedrock_provider
                logger.info("Bedrock provider registrado")
        except Exception as e:
            logger.warning(f"Bedrock provider não disponível: {e}")

        # SageMaker
        try:
            sm_provider = SageMakerProvider()
            if sm_provider.is_available:
                self.providers['sagemaker'] = sm_provider
                logger.info("SageMaker provider registrado")
        except Exception as e:
            logger.warning(f"SageMaker provider não disponível: {e}")

        # Lambda
        try:
            lambda_provider = LambdaProvider()
            if lambda_provider.is_available:
                self.providers['lambda'] = lambda_provider
                logger.info("Lambda provider registrado")
        except Exception as e:
            logger.warning(f"Lambda provider não disponível: {e}")

        # Anthropic (Claude)
        try:
            claude = AnthropicProvider()
            if claude.is_available:
                self.providers['anthropic'] = claude
                logger.info("Anthropic provider registrado")
        except Exception as e:
            logger.warning(f"Anthropic provider não disponível: {e}")

        # Gemini
        try:
            gem = GeminiProvider()
            if gem.is_available:
                self.providers['gemini'] = gem
                logger.info("Gemini provider registrado")
        except Exception as e:
            logger.warning(f"Gemini provider não disponível: {e}")
        
        if not self.providers:
            logger.warning("Nenhum provedor LLM disponível; recursos de LLM ficarão indisponíveis")
            self.fallback_enabled = False
        else:
            # Se não há preferido definido, usa o primeiro disponível como padrão
            if not self.default_provider_name:
                for name, provider in self.providers.items():
                    if provider.is_available:
                        self.default_provider_name = name
                        break
    
    def select_provider(self, prompt: str, preferred_provider: Optional[str] = None, **kwargs) -> BaseLLMProvider:
        """Seleciona provedor conforme preferência e métricas."""
        # Se provedor preferido está disponível, use-o
        if preferred_provider and preferred_provider in self.providers:
            provider = self.providers[preferred_provider]
            if provider.is_available:
                return provider
        # Usa provedor padrão da configuração, se disponível
        if self.default_provider_name and self.default_provider_name in self.providers:
            default_p = self.providers[self.default_provider_name]
            if default_p.is_available:
                return default_p
        
        # Seleção baseada em disponibilidade e desempenho
        available_providers = [
            provider for provider in self.providers.values()
            if provider.is_available
        ]
        
        if not available_providers:
            raise RuntimeError("Nenhum provedor disponível")
        
        # Ordena por taxa de sucesso e tempo de resposta médio
        available_providers.sort(
            key=lambda p: (p.get_stats()['success_rate'], -p.get_stats()['avg_response_time']),
            reverse=True
        )
        
        return available_providers[0]
    
    async def generate_response(
        self,
        prompt: str,
        preferred_provider: Optional[str] = None,
        use_cache: bool = True,
        **kwargs
    ) -> LLMResponse:
        """Gera resposta usando o provedor selecionado."""
        
        # Verifica cache primeiro
        if use_cache:
            for provider_name, provider in self.providers.items():
                cached_response = self.cache.get(prompt, provider.model_name, **kwargs)
                if cached_response:
                    logger.info(f"Resposta obtida do cache: {provider_name}")
                    return cached_response
        
        # Seleciona provedor
        provider = self.select_provider(prompt, preferred_provider, **kwargs)
        
        try:
            # Gera resposta
            response = await provider.generate_response(prompt, **kwargs)
            
            # Armazena no cache
            if use_cache:
                self.cache.set(prompt, provider.model_name, response, **kwargs)
            
            return response
            
        except Exception as e:
            logger.error(f"Erro com provedor {provider.name}: {e}")
            
            # Tenta fallback se habilitado
            if self.fallback_enabled:
                fallback_providers = [
                    p for p in self.providers.values()
                    if p.is_available and p != provider
                ]
                
                if fallback_providers:
                    fallback = fallback_providers[0]
                    logger.info(f"Tentando fallback com {fallback.name}")
                    return await fallback.generate_response(prompt, **kwargs)
            
            raise
    
    def get_provider_stats(self) -> Dict[str, Any]:
        """Métricas de provedores."""
        stats = {}
        for name, provider in self.providers.items():
            stats[name] = provider.get_stats()
        
        return stats
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Métricas do cache."""
        return self.cache.get_stats()
    
    def clear_cache(self):
        """Limpa respostas em cache."""
        self.cache.clear()
    
    def get_available_providers(self) -> List[str]:
        """Lista provedores ativos."""
        return [
            name for name, provider in self.providers.items()
            if provider.is_available
        ]
    
    def get_model_info(self) -> Dict[str, Any]:
        """Metadados de todos os modelos."""
        info = {}
        for name, provider in self.providers.items():
            info[name] = provider.get_model_info()
        
        return info

# Instância global do roteador LLM
llm_router = LLMRouter()
