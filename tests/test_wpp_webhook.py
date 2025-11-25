import os
import hmac
import hashlib
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def app_with_secret():
    os.environ["WEBHOOK_SECRET"] = "topsecret"
    from src.api.waha_api import create_app
    return create_app()


def test_webhook_valid_signature(app_with_secret):
    client = TestClient(app_with_secret)
    body = {"event": "message", "data": {"text": "hello"}}
    raw = b'{"event": "message", "data": {"text": "hello"}}'
    sig = hmac.new(b"topsecret", raw, hashlib.sha256).hexdigest()

    r = client.post(
        "/whatsapp/webhook/events",
        data=raw,
        headers={"Content-Type": "application/json", "X-Signature": sig},
    )
    assert r.status_code == 200
    assert r.json().get("ok") is True


def test_webhook_invalid_signature(app_with_secret):
    client = TestClient(app_with_secret)
    raw = b'{"event": "message", "data": {"text": "hello"}}'
    r = client.post(
        "/whatsapp/webhook/events",
        data=raw,
        headers={"Content-Type": "application/json", "X-Signature": "bad"},
    )
    assert r.status_code == 401
