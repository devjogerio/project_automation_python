import sys
from pathlib import Path
import pytest


def test_api_health():
    """Valida /api/v1/health."""
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from api.server import create_app
        from fastapi.testclient import TestClient
    except Exception:
        pytest.skip("FastAPI não disponível")

    app = create_app()
    client = TestClient(app)
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "ok"

