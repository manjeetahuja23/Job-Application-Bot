.PHONY: fmt lint test migrate dev-up dev-down bootstrap-db

fmt:
ruff check --fix .
black .
isort .

lint:
ruff check .
black --check .
isort --check-only .

test:
pytest

migrate:
alembic upgrade head

dev-up:
docker compose up -d

dev-down:
docker compose down

bootstrap-db:
scripts/bootstrap_db.sh
