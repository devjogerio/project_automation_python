import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def app_local_storage(tmp_path):
    # Garante sem S3
    os.environ.pop("AWS_S3_BUCKET", None)
    os.environ.pop("WEBHOOK_SECRET", None)
    # Ajusta data_dir para um diretório temporário, se possível
    from src.api.waha_api import create_app
    app = create_app()
    try:
        from utils.config import config
        config.data_dir = tmp_path  # type: ignore
    except Exception:
        pass
    return app


def test_webhook_persist_local(app_local_storage, tmp_path):
    client = TestClient(app_local_storage)
    raw = b'{"event":"message","data":{"text":"hello"}}'
    r = client.post(
        "/whatsapp/webhook/events",
        data=raw,
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body.get("stored") is True
    loc = body.get("location")
    assert loc
    p = Path(loc)
    assert p.exists()
