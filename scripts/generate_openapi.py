"""Gera arquivos OpenAPI (JSON e YAML) a partir da aplicação FastAPI.

Uso:
    python scripts/generate_openapi.py

O script importa `create_app` de `src.api.waha_api`, chama `app.openapi()`
e enriquece o dicionário com metadados adicionais (servers, contato, tags,
securitySchemes e exemplos). Em seguida escreve `docs/openapi.json` e
`docs/openapi.yaml`.
"""
import yaml
import json
from pathlib import Path
import os
import sys

# Garante que src/ seja importável quando o script for executado a partir do
# diretório raiz do projeto (ex.: CI, ambiente local sem instalar package)
root = Path(__file__).resolve().parents[1]
src_path = str(root / "src")
sys.path.insert(0, str(root))
sys.path.insert(0, src_path)

try:
    from src.api.waha_api import create_app
except Exception:
    # Permite executar o script a partir do repositório sem instalar o pacote
    from api.waha_api import create_app  # type: ignore


def enrich_openapi(spec: dict) -> dict:
    # Info / contact
    spec.setdefault("openapi", "3.0.0")
    info = spec.setdefault("info", {})
    info.setdefault("title", "WhatsApp API (WAHA)")
    info.setdefault("version", "1.0.0")
    info.setdefault(
        "description", "API RESTful para interação com WAHA (envio de mensagens, sessões e webhooks).")
    info.setdefault("contact", {
        "name": "Project Automation Team",
        "email": "dev+project_automation@example.com",
        "url": "https://github.com/devjogerio/project_automation_python"
    })

    # Servers
    spec.setdefault("servers", [
        {"url": "https://api.example.com/v1", "description": "Produção"},
        {"url": "https://staging.api.example.com/v1", "description": "Homologação"},
        {"url": "http://localhost:8000", "description": "Desenvolvimento"},
    ])

    # Security schemes (JWT bearer)
    comp = spec.setdefault("components", {})
    security = comp.setdefault("securitySchemes", {})
    security.setdefault("bearerAuth", {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "Autenticação via JWT. Header: Authorization: Bearer <token>"
    })

    # Default global security optionally (commented out by default)
    # spec.setdefault("security", [{"bearerAuth": []}])

    # Tags e exemplos por endpoint
    tags = spec.setdefault("tags", [
        {"name": "sessions",
            "description": "Operações sobre sessões WAHA (criar/iniciar/parar/status)"},
        {"name": "messages",
            "description": "Envio de mensagens (texto, imagem, ptt, thumb)"},
        {"name": "webhooks",
            "description": "Registro e recebimento de eventos (webhooks)"},
    ])

    # Examples para os principais paths conhecidos
    paths = spec.setdefault("paths", {})

    def set_example(path, method, example_obj):
        try:
            content = paths[path][method]["requestBody"]["content"]["application/json"]
            content.setdefault("example", example_obj)
        except Exception:
            # se não existir requestBody/content, ignora
            pass

    # Definir exemplos para cada operação conhecida
    set_example("/whatsapp/session/create", "post", {"name": "meu_bot_01"})
    set_example("/whatsapp/session/start", "post", {"name": "meu_bot_01"})
    set_example("/whatsapp/session/stop", "post", {"name": "meu_bot_01"})
    set_example("/whatsapp/webhook/register", "post",
                {"url": "https://meu.endereco.com/wpp/webhook"})
    set_example("/whatsapp/text", "post",
                {"to": "+5511999998888", "message": "Olá mundo!", "session": "meu_bot_01"})
    set_example("/whatsapp/image", "post", {"to": "+5511999998888",
                "image_url": "https://pics.example.com/photo.jpg", "caption": "Foto de exemplo"})
    set_example("/whatsapp/ptt", "post",
                {"to": "+5511999998888", "audio_base64": "<base64-audio>"})
    set_example("/whatsapp/thumb", "post", {"to": "+5511999998888", "url": "https://exemplo.com",
                "title": "Link exemplo", "description": "Descrição do link"})

    # Enriquecer respostas padrão com exemplos e possíveis códigos
    for p, methods in paths.items():
        for m, specop in methods.items():
            responses = specop.setdefault("responses", {})
            responses.setdefault("200", {"description": "Sucesso"})
            responses.setdefault("400", {"description": "Bad Request"})
            responses.setdefault("401", {"description": "Não autorizado"})
            responses.setdefault("429", {"description": "Rate limit excedido"})
            responses.setdefault("500", {"description": "Erro interno"})

    return spec


def run(output_dir: Path = Path("docs")) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    app = create_app()
    spec = app.openapi()

    spec = enrich_openapi(spec)

    json_path = output_dir / "openapi.json"
    yaml_path = output_dir / "openapi.yaml"

    with json_path.open("w", encoding="utf-8") as fh:
        json.dump(spec, fh, indent=2, ensure_ascii=False)

    with yaml_path.open("w", encoding="utf-8") as fh:
        yaml.dump(spec, fh, sort_keys=False, allow_unicode=True)

    print(f"Gerados: {json_path} e {yaml_path}")


if __name__ == "__main__":
    run()
