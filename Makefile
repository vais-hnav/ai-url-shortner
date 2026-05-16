PYTHON := ./venv/bin/python
PIP := ./venv/bin/pip
ALEMBIC := ./venv/bin/alembic
UVICORN := ./venv/bin/uvicorn

.PHONY: setup install run lint-check check-env bootstrap status db-up db-down db-logs migrate-head migrate-new compose-up compose-down compose-logs

setup:
	python3 -m venv venv
	$(PIP) install --upgrade pip
	$(PIP) install -e .

install:
	$(PIP) install -e .

run:
	$(UVICORN) app.main:app --reload --host 127.0.0.1 --port 8000

lint-check:
	PYTHONPYCACHEPREFIX=/private/tmp/codex-pycache $(PYTHON) -m compileall app

check-env:
	$(PYTHON) -c "from app.core.config import settings; print('env-ok', settings.app_name, settings.debug)"

bootstrap: check-env compose-up status
	@attempt=1; \
	until curl -fsS http://127.0.0.1:8000/health > /dev/null; do \
		if [ $$attempt -ge 30 ]; then \
			echo "bootstrap-error: app health check timed out"; \
			docker compose logs --tail=100 app; \
			exit 1; \
		fi; \
		sleep 1; \
		attempt=$$((attempt + 1)); \
	done
	@echo "bootstrap-ok: app is healthy at http://127.0.0.1:8000"

status:
	docker compose ps

db-up:
	docker compose up -d postgres

db-down:
	docker compose stop postgres

db-logs:
	docker compose logs -f postgres

migrate-head:
	$(ALEMBIC) upgrade head

migrate-new:
	$(ALEMBIC) revision --autogenerate -m "$(m)"

compose-up:
	docker compose up -d --build

compose-down:
	docker compose down

compose-logs:
	docker compose logs -f app postgres
