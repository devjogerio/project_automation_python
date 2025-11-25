import os
import asyncio
from typing import Optional, Dict, Any
import httpx
from loguru import logger


class WahaClient:
    """Cliente WAHA (WhatsApp HTTP API) compatível com o sistema.

    Referência: Waha-Document (Quick Start / Dashboard / Swagger).

    - Autenticação via `X-API-KEY` (WAHA_API_KEY) do `.env`
    - Base URL: `WAHA_HOST` (ex.: `http://localhost:3000`)
    - Gerenciamento de sessões: criar, iniciar, parar, status
    - Envio de mensagens: texto, imagem
    - Recebimento: registro de Webhook (servidor do usuário deverá tratar)
    - Tratamento de erros com retry exponencial e reconexão
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout_seconds: int = 10,
    ):
        """Inicializa o cliente WAHA com base URL e API key."""
        self.base_url = (base_url or os.getenv("WAHA_HOST")
                         or "http://localhost:3000").rstrip("/")
        self.api_key = api_key or os.getenv("WAHA_API_KEY") or ""
        self.timeout = httpx.Timeout(timeout_seconds)

        if not self.api_key:
            logger.warning(
                "WAHA_API_KEY não configurada; "
                "chamadas autenticadas podem falhar"
            )

        logger.info("WAHA client configurado", base_url=self.base_url)

    async def _request(
        self,
        method: str,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        retries: int = 3,
    ) -> Dict[str, Any]:
        """Executa requisição HTTP com cabeçalho de autenticação
        e retry exponencial."""
        url = f"{self.base_url}{path}"
        headers = {"X-API-KEY": self.api_key} if self.api_key else {}
        backoff = 0.5
        last_exc: Optional[Exception] = None

        for attempt in range(retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.request(
                        method, url, headers=headers, json=json
                    )
                is_json = resp.headers.get(
                    "content-type", "").startswith("application/json")
                data = resp.json() if is_json else {"raw": resp.text}
                if resp.status_code >= 500:
                    # Retry em erro 5xx
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue
                if resp.status_code in (401, 403):
                    raise PermissionError(
                        "Autenticação WAHA falhou (verifique WAHA_API_KEY)"
                    )
                if resp.status_code >= 400:
                    raise RuntimeError(
                        f"WAHA error {resp.status_code}: {data}")
                return data
            except (httpx.TimeoutException, httpx.NetworkError) as e:
                last_exc = e
                await asyncio.sleep(backoff)
                backoff *= 2
            except Exception as e:
                raise e

        raise RuntimeError(
            f"Falha na requisição WAHA após retries: {last_exc}"
        )

    async def test_connection(self) -> bool:
        """Teste básico: acessa `/swagger` ou fallback `/dashboard`."""
        try:
            # Tenta /swagger
            await self._request(
                "GET", "/swagger", None, retries=1
            )
            return True
        except Exception:
            # Fallback para /dashboard
            try:
                await self._request("GET", "/dashboard", None, retries=1)
                return True
            except Exception as e:
                logger.error(f"Teste de conexão WAHA falhou: {e}")
                return False

    async def create_session(self, name: str) -> Dict[str, Any]:
        """Cria sessão WAHA (nome simples)."""
        payload = {"name": name}
        return await self._request("POST", "/api/sessions/create", payload)

    async def start_session(self, name: str) -> Dict[str, Any]:
        """Inicia sessão WAHA (abre WhatsApp Web)."""
        payload = {"name": name}
        return await self._request("POST", "/api/sessions/start", payload)

    async def stop_session(self, name: str) -> Dict[str, Any]:
        """Para sessão WAHA."""
        payload = {"name": name}
        return await self._request("POST", "/api/sessions/stop", payload)

    async def get_session_status(self, name: str) -> Dict[str, Any]:
        """Obtém status da sessão WAHA."""
        return await self._request("GET", f"/api/sessions/{name}/status")

    async def register_webhook(self, url: str) -> Dict[str, Any]:
        """Registra Webhook para receber mensagens/eventos do WAHA."""
        payload = {"hookUrl": url, "events": "*"}
        return await self._request("POST", "/api/webhook/register", payload)

    async def send_text(
        self,
        to: str,
        message: str,
        session: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Envia texto UTF-8 para um número."""
        payload = {"to": to, "text": message}
        if session:
            payload["session"] = session
        return await self._request("POST", "/api/messages/text", payload)

    async def send_image(
        self,
        to: str,
        image_url: Optional[str] = None,
        image_base64: Optional[str] = None,
        caption: Optional[str] = None,
        session: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Envia imagem (URL ou base64) com legenda opcional."""
        payload: Dict[str, Any] = {"to": to}
        if image_url:
            payload["imageUrl"] = image_url
        if image_base64:
            payload["imageBase64"] = image_base64
        if caption:
            payload["caption"] = caption
        if session:
            payload["session"] = session
        return await self._request(
            "POST",
            "/api/messages/image",
            payload,
        )

    async def reconnect(self) -> bool:
        """Tenta reconexão simples validando `/swagger`."""
        return await self.test_connection()


# Testes básicos de conexão (autoexec quando chamado como script)
if __name__ == "__main__":
    async def _run():
        client = WahaClient()
        ok = await client.test_connection()
        print({"connected": ok, "base_url": client.base_url})

    asyncio.run(_run())
