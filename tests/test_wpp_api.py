import os
import jwt
import asyncio
from fastapi.testclient import TestClient

from src.api.waha_api import create_app


class MockClient:
    """Cliente mock para substituir WppConnectClient nos testes."""

    async def send_text(self, to, message):
        return {"to": to, "message": message, "status": "ok"}

    async def send_image(self, to, image_url, image_base64, caption):
        return {"to": to, "image_url": image_url, "caption": caption, "status": "ok"}

    async def send_list(self, to, title, items):
        return {"to": to, "title": title, "items": items, "status": "ok"}

    async def send_buttons(self, to, text, buttons):
        return {"to": to, "text": text, "buttons": buttons, "status": "ok"}

    async def send_ptt_base64(self, to, audio_base64):
        return {"to": to, "audio_base64": audio_base64, "status": "ok"}

    async def send_message_with_thumb(self, to, url, title, description, image_base64=None):
        return {"to": to, "url": url, "title": title, "description": description, "image_base64": image_base64, "status": "ok"}


def make_token(secret="test_secret", alg="HS256"):
    return jwt.encode({"sub": "tester"}, secret, algorithm=alg)


def setup_app(rate_limit=100):
    os.environ["JWT_SECRET"] = "test_secret"
    os.environ["JWT_ALG"] = "HS256"
    os.environ["RATE_LIMIT_PER_MINUTE"] = str(rate_limit)
    app = create_app()
    app.state.wpp_client = MockClient()
    return app


def test_auth_required():
    app = setup_app()
    client = TestClient(app)
    resp = client.post("/whatsapp/text", json={"to": "5511999999999", "message": "oi"})
    assert resp.status_code == 401


def test_send_text_success():
    app = setup_app()
    client = TestClient(app)
    token = make_token()
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post("/whatsapp/text", json={"to": "5511999999999", "message": "Olá 👋"}, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["result"]["message"] == "Olá 👋"


def test_validation_phone_invalid():
    app = setup_app()
    client = TestClient(app)
    token = make_token()
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post("/whatsapp/text", json={"to": "123", "message": "oi"}, headers=headers)
    assert resp.status_code == 422


def test_image_requires_source():
    app = setup_app()
    client = TestClient(app)
    token = make_token()
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post("/whatsapp/image", json={"to": "5511999999999"}, headers=headers)
    assert resp.status_code == 400


def test_rate_limit_exceeded():
    app = setup_app(rate_limit=1)
    client = TestClient(app)
    token = make_token()
    headers = {"Authorization": f"Bearer {token}"}
    # Primeira requisição deve passar
    r1 = client.post("/whatsapp/text", json={"to": "5511999999999", "message": "oi"}, headers=headers)
    assert r1.status_code == 200
    # Segunda na mesma janela deve bloquear
    r2 = client.post("/whatsapp/text", json={"to": "5511999999999", "message": "oi2"}, headers=headers)
    assert r2.status_code == 429


def test_send_ptt_success():
    app = setup_app()
    client = TestClient(app)
    token = make_token()
    headers = {"Authorization": f"Bearer {token}"}
    audio_b64 = "QmFzZTY0QXVkaW8="
    resp = client.post("/whatsapp/ptt", json={"to": "5511999999999", "audio_base64": audio_b64}, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True


def test_send_thumb_success():
    app = setup_app()
    client = TestClient(app)
    token = make_token()
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post(
        "/whatsapp/thumb",
        json={"to": "5511999999999", "url": "https://example.com", "title": "Exemplo", "description": "Desc"},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
