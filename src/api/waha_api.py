"""
API RESTful de WhatsApp baseada em FastAPI, com autenticação JWT e rate limit.

Endpoints principais:
- POST `/whatsapp/text`
- POST `/whatsapp/image`
- POST `/whatsapp/ptt`
- POST `/whatsapp/thumb`
"""

import os
import time
import asyncio
from typing import Optional, Dict, Any
from uuid import uuid4

import jwt
from fastapi import FastAPI, Depends, HTTPException, Header, Request
from pydantic import BaseModel, Field, field_validator
from loguru import logger
from pathlib import Path
from datetime import datetime
from typing import Tuple
try:
    from src.utils.config import config
except Exception:
    from utils.config import config  # type: ignore

try:
    from src.whatsapp.waha_client import WahaClient
except Exception:
    WahaClient = None  # type: ignore


class JWTAuth:
    def __init__(self) -> None:
        self.secret = os.getenv("JWT_SECRET", "")
        self.alg = os.getenv("JWT_ALG", "HS256")

    def _extract_token(self, authorization: Optional[str]) -> str:
        if not authorization:
            raise HTTPException(
                status_code=401, detail="Authorization header ausente")
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(
                status_code=401, detail="Formato de Authorization inválido")
        return parts[1]

    def require(self, authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
        if not self.secret:
            raise HTTPException(
                status_code=500, detail="JWT_SECRET não configurado")
        token = self._extract_token(authorization)
        try:
            payload = jwt.decode(token, self.secret, algorithms=[self.alg])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expirado")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Token inválido")


class RateLimiter:
    def __init__(self, limit_per_minute: Optional[int] = None) -> None:
        self.limit = int(os.getenv("RATE_LIMIT_PER_MINUTE",
                         str(limit_per_minute or 60)))
        self._store: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def allow(self, identity: str) -> bool:
        now = int(time.time())
        window = now // 60
        async with self._lock:
            entry = self._store.get(identity)
            if entry and entry["window"] == window:
                if entry["count"] >= self.limit:
                    return False
                entry["count"] += 1
                return True
            self._store[identity] = {"window": window, "count": 1}
            return True


def get_identity(payload: Dict[str, Any], request: Request) -> str:
    return str(payload.get("sub")) if payload.get("sub") else request.client.host


class TextMessageRequest(BaseModel):
    to: str = Field(..., description="Telefone destino em formato E.164 brasileiro: +55XXXXXXXXXXX")
    message: str = Field(..., min_length=1, description="Texto da mensagem")
    session: Optional[str] = Field(
        None, description="Nome da sessão WAHA (opcional)")

    @field_validator("to")
    def validate_phone(cls, v: str) -> str:
        import re
        pattern = re.compile(r"^\+?55\d{10,11}$")
        if not pattern.match(v):
            raise ValueError(
                "Telefone inválido. Use formato +5511XXXXXXXX ou 5511XXXXXXXX")
        return v


class ImageMessageRequest(BaseModel):
    to: str = Field(..., description="Telefone destino (+55...) ou 55...")
    image_url: Optional[str] = Field(None, description="URL da imagem")
    image_base64: Optional[str] = Field(
        None, description="Conteúdo da imagem em base64")
    caption: Optional[str] = Field(None, description="Legenda opcional")
    session: Optional[str] = Field(None, description="Sessão WAHA (opcional)")

    @field_validator("to")
    def validate_phone(cls, v: str) -> str:
        import re
        if not re.match(r"^\+?55\d{10,11}$", v):
            raise ValueError("Telefone inválido")
        return v


class PttRequest(BaseModel):
    to: str = Field(..., description="Telefone destino (+55...) ou 55...")
    audio_base64: str = Field(..., description="Conteúdo de áudio em base64")
    session: Optional[str] = Field(None, description="Sessão WAHA (opcional)")

    @field_validator("to")
    def validate_phone(cls, v: str) -> str:
        import re
        if not re.match(r"^\+?55\d{10,11}$", v):
            raise ValueError("Telefone inválido")
        return v


class ThumbRequest(BaseModel):
    to: str = Field(..., description="Telefone destino (+55...) ou 55...")
    url: str = Field(..., description="URL do link a ser enviado")
    title: str = Field(..., description="Título do link")
    description: str = Field(..., description="Descrição do link")
    image_base64: Optional[str] = Field(
        None, description="Thumbnail em base64 (opcional)")
    session: Optional[str] = Field(None, description="Sessão WAHA (opcional)")

    @field_validator("to")
    def validate_phone(cls, v: str) -> str:
        import re
        if not re.match(r"^\+?55\d{10,11}$", v):
            raise ValueError("Telefone inválido")
        return v


def create_app() -> FastAPI:
    app = FastAPI(title="WhatsApp API (WAHA)", version="1.0.0")

    auth = JWTAuth()
    rate_limiter = RateLimiter()
    app.state.rate_limiter = rate_limiter

    if WahaClient is not None:
        app.state.wpp_client = WahaClient()
    else:
        app.state.wpp_client = None

    @app.middleware("http")
    async def add_request_id_logging(request: Request, call_next):
        """Middleware que injeta `X-Request-ID` e loga duração da requisição."""
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        start = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            f"{request.method} {request.url.path} rid={request_id} dur={duration_ms:.2f}ms status={response.status_code}"
        )
        return response

    # ----------------------
    # Endpoints de Sessão
    # ----------------------

    class SessionRequest(BaseModel):
        """Payload para operações de sessão WAHA."""
        name: str = Field(..., min_length=3, max_length=32,
                          description="Nome simples da sessão")

        @field_validator("name")
        def validate_name(cls, v: str) -> str:
            import re
            if not re.match(r"^[a-zA-Z0-9_\-]{3,32}$", v):
                raise ValueError("Nome de sessão inválido")
            return v

    class WebhookRequest(BaseModel):
        """Payload para registro de webhook WAHA."""
        url: str = Field(...,
                         description="URL pública para receber eventos do WAHA")

    @app.post("/whatsapp/session/create")
    async def session_create(req: SessionRequest, payload: Dict[str, Any] = Depends(auth.require), request: Request = None):
        """Cria uma sessão WAHA pelo nome especificado."""
        identity = get_identity(payload, request)
        if not await app.state.rate_limiter.allow(identity):
            raise HTTPException(status_code=429, detail="Rate limit excedido")
        try:
            # type: ignore
            result = await app.state.wpp_client.create_session(req.name)
            return {"success": True, "result": result}
        except Exception as e:
            logger.error(f"Erro ao criar sessão: {e}")
            raise HTTPException(
                status_code=500, detail="Erro interno ao criar sessão")

    @app.post("/whatsapp/session/start")
    async def session_start(req: SessionRequest, payload: Dict[str, Any] = Depends(auth.require), request: Request = None):
        """Inicia uma sessão WAHA pelo nome."""
        identity = get_identity(payload, request)
        if not await app.state.rate_limiter.allow(identity):
            raise HTTPException(status_code=429, detail="Rate limit excedido")
        try:
            # type: ignore
            result = await app.state.wpp_client.start_session(req.name)
            return {"success": True, "result": result}
        except Exception as e:
            logger.error(f"Erro ao iniciar sessão: {e}")
            raise HTTPException(
                status_code=500, detail="Erro interno ao iniciar sessão")

    @app.post("/whatsapp/session/stop")
    async def session_stop(req: SessionRequest, payload: Dict[str, Any] = Depends(auth.require), request: Request = None):
        """Para uma sessão WAHA pelo nome."""
        identity = get_identity(payload, request)
        if not await app.state.rate_limiter.allow(identity):
            raise HTTPException(status_code=429, detail="Rate limit excedido")
        try:
            # type: ignore
            result = await app.state.wpp_client.stop_session(req.name)
            return {"success": True, "result": result}
        except Exception as e:
            logger.error(f"Erro ao parar sessão: {e}")
            raise HTTPException(
                status_code=500, detail="Erro interno ao parar sessão")

    @app.get("/whatsapp/session/{name}/status")
    async def session_status(name: str, payload: Dict[str, Any] = Depends(auth.require), request: Request = None):
        """Obtém status de uma sessão WAHA pelo nome."""
        identity = get_identity(payload, request)
        if not await app.state.rate_limiter.allow(identity):
            raise HTTPException(status_code=429, detail="Rate limit excedido")
        try:
            # type: ignore
            result = await app.state.wpp_client.get_session_status(name)
            return {"success": True, "result": result}
        except Exception as e:
            logger.error(f"Erro ao obter status da sessão: {e}")
            raise HTTPException(
                status_code=500, detail="Erro interno ao obter status da sessão")

    @app.post("/whatsapp/webhook/register")
    async def webhook_register(req: WebhookRequest, payload: Dict[str, Any] = Depends(auth.require), request: Request = None):
        """Registra webhook do WAHA para eventos (mensagens, status, etc.)."""
        identity = get_identity(payload, request)
        if not await app.state.rate_limiter.allow(identity):
            raise HTTPException(status_code=429, detail="Rate limit excedido")
        try:
            # type: ignore
            result = await app.state.wpp_client.register_webhook(req.url)
            return {"success": True, "result": result}
        except Exception as e:
            logger.error(f"Erro ao registrar webhook: {e}")
            raise HTTPException(
                status_code=500, detail="Erro interno ao registrar webhook")

    # ----------------------
    # Webhook inbound (eventos do WAHA)
    # ----------------------

    @app.post("/whatsapp/webhook/events")
    async def webhook_events(request: Request):
        """Recebe eventos do WAHA. Valida assinatura HMAC e persiste evento.

        Persistência:
        - Se `AWS_S3_BUCKET` e `boto3` disponíveis, salva em S3: `webhooks/<timestamp>_<rid>.json`
        - Caso contrário, salva localmente em `data/webhooks/<timestamp>_<rid>.json`
        """
        try:
            body_bytes = await request.body()
            secret = os.getenv("WEBHOOK_SECRET", "")
            signature = request.headers.get("X-Signature", "")
            request_id = request.headers.get("X-Request-ID") or str(uuid4())

            if secret:
                import hmac
                import hashlib
                expected = hmac.new(secret.encode("utf-8"),
                                    body_bytes, hashlib.sha256).hexdigest()
                if not hmac.compare_digest(signature or "", expected):
                    raise HTTPException(
                        status_code=401, detail="Assinatura inválida")

            payload = await request.json()
            # Persiste evento
            stored, location = await _persist_webhook_event(body_bytes, request_id)
            logger.info(
                f"Webhook evento recebido: keys={list(payload.keys())} stored={stored} location={location}")
            return {"ok": True, "stored": stored, "location": location}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erro ao processar webhook: {e}")
            raise HTTPException(
                status_code=500, detail="Erro interno ao processar webhook")

    async def _persist_webhook_event(body: bytes, request_id: str) -> Tuple[bool, str]:
        """Persiste o corpo do webhook em S3 (se possível) ou localmente.

        Retorna tupla `(stored, location)` indicando sucesso e caminho/chave.
        """
        ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
        filename = f"{ts}_{request_id}.json"
        bucket = os.getenv("AWS_S3_BUCKET", "")
        # Tenta S3
        if bucket:
            try:
                import boto3  # type: ignore
                s3 = boto3.client("s3")
                key = f"webhooks/{filename}"
                s3.put_object(Bucket=bucket, Key=key, Body=body)
                return True, f"s3://{bucket}/{key}"
            except Exception as e:
                logger.warning(
                    f"Falha ao salvar webhook no S3: {e}. Usando armazenamento local.")
        # Local
        try:
            base_dir: Path = config.data_dir if hasattr(
                config, "data_dir") else Path("data")
            target = base_dir / "webhooks"
            target.mkdir(parents=True, exist_ok=True)
            path = target / filename
            path.write_bytes(body)
            return True, str(path)
        except Exception as e:
            logger.error(f"Falha ao salvar webhook localmente: {e}")
            return False, ""

    @app.post("/whatsapp/text")
    async def send_text(req: TextMessageRequest, payload: Dict[str, Any] = Depends(auth.require), request: Request = None):
        identity = get_identity(payload, request)
        allowed = await app.state.rate_limiter.allow(identity)
        if not allowed:
            raise HTTPException(status_code=429, detail="Rate limit excedido")

        try:
            client = app.state.wpp_client
            # type: ignore
            result = await client.send_text(req.to, req.message)
            return {"success": True, "result": result}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erro ao enviar texto: {e}")
            raise HTTPException(
                status_code=500, detail="Erro interno ao enviar texto")

    @app.post("/whatsapp/image")
    async def send_image(req: ImageMessageRequest, payload: Dict[str, Any] = Depends(auth.require), request: Request = None):
        identity = get_identity(payload, request)
        allowed = await app.state.rate_limiter.allow(identity)
        if not allowed:
            raise HTTPException(status_code=429, detail="Rate limit excedido")

        try:
            client = app.state.wpp_client
            if not (req.image_url or req.image_base64):
                raise HTTPException(
                    status_code=400, detail="Informe 'image_url' ou 'image_base64'")
            # type: ignore
            result = await client.send_image(req.to, req.image_url, req.image_base64, req.caption)
            return {"success": True, "result": result}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erro ao enviar imagem: {e}")
            raise HTTPException(
                status_code=500, detail="Erro interno ao enviar imagem")

    @app.post("/whatsapp/ptt")
    async def send_ptt(req: PttRequest, payload: Dict[str, Any] = Depends(auth.require), request: Request = None):
        identity = get_identity(payload, request)
        allowed = await app.state.rate_limiter.allow(identity)
        if not allowed:
            raise HTTPException(status_code=429, detail="Rate limit excedido")

        try:
            client = app.state.wpp_client
            # type: ignore
            result = await client.send_ptt_base64(req.to, req.audio_base64)
            return {"success": True, "result": result}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erro ao enviar PTT: {e}")
            raise HTTPException(
                status_code=500, detail="Erro interno ao enviar PTT")

    @app.post("/whatsapp/thumb")
    async def send_thumb(req: ThumbRequest, payload: Dict[str, Any] = Depends(auth.require), request: Request = None):
        identity = get_identity(payload, request)
        allowed = await app.state.rate_limiter.allow(identity)
        if not allowed:
            raise HTTPException(status_code=429, detail="Rate limit excedido")

        try:
            client = app.state.wpp_client
            result = await client.send_message_with_thumb(
                req.to, req.url, req.title, req.description, req.image_base64
            )  # type: ignore
            return {"success": True, "result": result}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erro ao enviar thumb: {e}")
            raise HTTPException(
                status_code=500, detail="Erro interno ao enviar thumb")

    return app
