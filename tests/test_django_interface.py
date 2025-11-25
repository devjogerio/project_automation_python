import os
import sys
from pathlib import Path
import pytest

# Configura ambiente Django
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "webapp.webapp.settings")

import django
django.setup()

from django.test import Client


@pytest.mark.django_db
def test_home_view(client: Client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"Interface Web" in r.content


@pytest.mark.django_db
def test_send_text_view_requires_login(client: Client):
    r = client.get("/messages/text")
    assert r.status_code in (302, 301)


@pytest.mark.django_db
def test_sessions_manage_view_requires_login(client: Client):
    r = client.get("/sessions/manage")
    assert r.status_code in (302, 301)
