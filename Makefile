PYTHON=python
DOCKER=docker compose

run:
	$(PYTHON) src/manage.py runserver 0.0.0.0:8000

migrate:
	$(PYTHON) src/manage.py migrate

makemigrations:
	$(PYTHON) src/manage.py makemigrations

bootstrap-rbac:
	$(PYTHON) src/manage.py bootstrap_rbac

seed-demo:
	$(PYTHON) src/manage.py seed_demo_data

seed-demo-reset:
	$(PYTHON) src/manage.py seed_demo_data --reset

warm-reports-cache:
	$(PYTHON) src/manage.py warm_reports_cache

docker-up:
	$(DOCKER) up --build -d

docker-down:
	$(DOCKER) down

docker-logs:
	$(DOCKER) logs -f web

lint:
	ruff check src
