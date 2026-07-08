.PHONY: up api-test api-migrate web-dev

up:
	docker compose up --build

api-migrate:
	cd services/api && alembic upgrade head

api-test:
	cd services/api && pytest

web-dev:
	cd apps/web && npm run dev

