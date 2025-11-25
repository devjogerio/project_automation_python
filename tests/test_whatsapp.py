import asyncio
from unittest.mock import AsyncMock, patch
from src.whatsapp.waha_client import WahaClient


def test_waha_connection_success():
    """Valida teste de conexão com WAHA via /swagger."""
    client = WahaClient(base_url="http://localhost:3000", api_key="test-key")

    async def fake_request(method, path, json=None, retries=1):
        return {"ok": True}
    with patch.object(
        WahaClient,
        "_request",
        new=AsyncMock(side_effect=fake_request),
    ):
        assert asyncio.run(client.test_connection()) is True


def test_waha_send_text_payload():
    """Verifica envio de texto com construção de payload mínima."""
    client = WahaClient(base_url="http://localhost:3000", api_key="test-key")
    called = {}

    async def fake_post(method, path, json=None, retries=3):
        called["method"] = method
        called["path"] = path
        called["json"] = json
        return {"success": True}

    with patch.object(
        WahaClient,
        "_request",
        new=AsyncMock(side_effect=fake_post),
    ):
        res = asyncio.run(client.send_text("5511999999999", "Olá"))
        assert res["success"] is True
        assert called["method"] == "POST"
        assert called["path"] == "/api/messages/text"
        assert called["json"]["to"].isdigit()
        assert called["json"]["text"] == "Olá"
