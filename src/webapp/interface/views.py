import os
from typing import Dict, Any
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import HttpRequest, HttpResponse
import httpx

from .forms import SendTextForm, SessionForm


def _auth_headers() -> Dict[str, str]:
    """Headers de autenticação para chamar WAHA com JWT de serviço."""
    token = settings.SERVICE_JWT_TOKEN or os.getenv("SERVICE_JWT_TOKEN", "")
    return {"Authorization": f"Bearer {token}"} if token else {}


def home(request: HttpRequest) -> HttpResponse:
    """Página inicial com navegação básica."""
    return render(request, "interface/home.html", {})


@login_required
def send_text_view(request: HttpRequest) -> HttpResponse:
    """Renderiza e processa o formulário de envio de texto."""
    if request.method == "POST":
        form = SendTextForm(request.POST)
        if form.is_valid():
            payload = {"to": form.cleaned_data["to"], "message": form.cleaned_data["message"]}
            url = f"{settings.WAHA_BASE_URL}/whatsapp/text"
            r = httpx.post(url, json=payload, headers=_auth_headers(), timeout=10)
            context = {"form": form, "response": r.json(), "status": r.status_code}
            return render(request, "interface/send_text.html", context)
    else:
        form = SendTextForm()
    return render(request, "interface/send_text.html", {"form": form})


@login_required
def sessions_manage_view(request: HttpRequest) -> HttpResponse:
    """Renderiza e processa operações de sessão WAHA."""
    result: Dict[str, Any] = {}
    status_code = None
    if request.method == "POST":
        form = SessionForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data["name"]
            action = form.cleaned_data["action"]
            url = {
                "create": f"{settings.WAHA_BASE_URL}/whatsapp/session/create",
                "start": f"{settings.WAHA_BASE_URL}/whatsapp/session/start",
                "stop": f"{settings.WAHA_BASE_URL}/whatsapp/session/stop",
            }.get(action)
            if action == "status":
                url = f"{settings.WAHA_BASE_URL}/whatsapp/session/{name}/status"
                r = httpx.get(url, headers=_auth_headers(), timeout=10)
            else:
                r = httpx.post(url, json={"name": name}, headers=_auth_headers(), timeout=10)
            result = r.json()
            status_code = r.status_code
            return render(request, "interface/sessions.html", {"form": form, "response": result, "status": status_code})
    else:
        form = SessionForm()
    return render(request, "interface/sessions.html", {"form": form})

