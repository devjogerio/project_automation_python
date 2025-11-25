import os
import jwt
import pytest
from fastapi.testclient import TestClient


class FakeWaha:
    async def create_session(self, name):
        return {"name": name, "status": "created"}

    async def start_session(self, name):
        return {"name": name, "status": "started"}

    async def stop_session(self, name):
        return {"name": name, "status": "stopped"}

    async def get_session_status(self, name):
        return {"name": name, "status": "ready"}

    async def register_webhook(self, url):
        return {"hookUrl": url, "events": "*", "status": "ok"}


def make_token(secret="dev", alg="HS256"):
    return jwt.encode({"sub": "tester"}, secret, algorithm=alg)


@pytest.fixture
def app():
    os.environ["JWT_SECRET"] = "dev"
    os.environ["JWT_ALG"] = "HS256"
    from src.api.waha_api import create_app
    app = create_app()
    app.state.wpp_client = FakeWaha()
    return app


def test_session_create(app):
    client = TestClient(app)
    token = make_token()
    r = client.post(
        "/whatsapp/session/create",
        json={"name": "sessao1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["success"] is True


def test_session_start_stop_status(app):
    client = TestClient(app)
    token = make_token()
    r1 = client.post(
        "/whatsapp/session/start",
        json={"name": "sessao1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r1.status_code == 200

    r2 = client.get(
        "/whatsapp/session/sessao1/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 200
    assert r2.json()["result"]["status"] == "ready"

    r3 = client.post(
        "/whatsapp/session/stop",
        json={"name": "sessao1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r3.status_code == 200


def test_webhook_register(app):
    client = TestClient(app)
    token = make_token()
    r = client.post(
        "/whatsapp/webhook/register",
        json={"url": "https://example.com/webhook"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["result"]["hookUrl"] == "https://example.com/webhook"
