PY := python3
PIP := pip
UVICORN := uvicorn

.PHONY: gui api test lint typecheck deps
 
docs-openapi:
	$(PY) scripts/generate_openapi.py


gui:
	$(PY) src/main.py

api:
	$(UVICORN) src.api.waha_api:create_app --factory --port 8001

test:
	$(PY) -m pytest -q

lint:
	flake8 src/

typecheck:
	mypy --explicit-package-bases src/api src/whatsapp

deps:
	$(PIP) install -r requirements.txt

web:
	DJANGO_DEBUG=true $(PY) manage.py runserver 127.0.0.1:8002
