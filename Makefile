# ============================================================
# Interactive Curriculum Engine - dev task runner
# Cross-platform targets delegate to the right tool per language.
# ============================================================

.PHONY: help dev dev-up dev-down install lint format typecheck \
        test test-py test-web migrate seed eval bootstrap clean

PYTHON := python
UV := uv
PNPM := pnpm

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

bootstrap: ## Install all deps (py + node) + pre-commit hooks
	$(UV) sync
	$(PNPM) install
	$(UV) run pre-commit install
	@echo "Bootstrap complete. Copy .env.example -> .env and fill in secrets."

dev: dev-up ## Start the full dev stack (compose) in the background
	@echo "Stack up. API: http://localhost:8000  Web: http://localhost:3000"

dev-up: ## Start docker-compose dev stack
	docker compose -f infra/compose/docker-compose.dev.yml up -d

dev-down: ## Stop docker-compose dev stack
	docker compose -f infra/compose/docker-compose.dev.yml down

dev-logs: ## Tail compose logs
	docker compose -f infra/compose/docker-compose.dev.yml logs -f --tail=200

install: ## Re-sync deps
	$(UV) sync
	$(PNPM) install

lint: ## Lint everything (ruff + eslint)
	$(UV) run ruff check .
	$(UV) run ruff format --check .
	$(UV) run mypy
	$(PNPM) run lint:web

format: ## Auto-format everything
	$(UV) run ruff format .
	$(UV) run ruff check --fix .
	$(PNPM) run format:web

typecheck: ## Type-check (mypy + tsc)
	$(UV) run mypy
	$(PNPM) run typecheck:web

test: test-py test-web ## Run all tests

test-py: ## Run Python tests (exclude integration/e2e/gpu/golden)
	$(UV) run pytest -m "not integration and not e2e and not gpu and not golden"

test-integration: ## Run integration tests (requires live services)
	$(UV) run pytest -m "integration"

test-e2e: ## Run end-to-end tests (requires live stack)
	$(UV) run pytest -m "e2e"

test-web: ## Run frontend tests
	$(PNPM) run test:web

migrate: ## Apply database migrations (alembic upgrade head)
	$(UV) run alembic -c db/alembic.ini upgrade head

migrate-new: ## Create a new migration: make migrate-new m="message"
	@test -n "$(m)" || (echo "Usage: make migrate-new m='add users table'" && exit 1)
	$(UV) run alembic -c db/alembic.ini revision --autogenerate -m "$(m)"

seed: ## Seed dev database with sample data
	$(UV) run python scripts/seed-db.py

eval: ## Run the golden-set evaluation suite
	$(UV) run python scripts/eval-golden.py

run-pipeline: ## Run the full pipeline on a sample video (Phase-0 smoke test)
	$(UV) run python scripts/run-pipeline.py

clean: ## Remove build/test caches
	@find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	@rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov 2>/dev/null || true
	@rm -rf apps/web/.next apps/web/node_modules 2>/dev/null || true
