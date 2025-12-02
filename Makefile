.PHONY: help install dev test lint format migrate run docker-build docker-up docker-down clean

# Variables
PYTHON := python
PIP := pip
UVICORN := uvicorn
ALEMBIC := alembic
PYTEST := pytest
BLACK := black
ISORT := isort
FLAKE8 := flake8
MYPY := mypy

help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

install: ## Install production dependencies
	$(PIP) install -r requirements.txt

dev: ## Install development dependencies
	$(PIP) install -r requirements.txt
	$(PIP) install pytest pytest-asyncio pytest-cov httpx aiosqlite black isort flake8 mypy

test: ## Run tests
	$(PYTEST) tests/ -v --cov=app --cov-report=term-missing

lint: ## Run linters
	$(FLAKE8) app/ tests/
	$(MYPY) app/

format: ## Format code
	$(BLACK) app/ tests/
	$(ISORT) app/ tests/

migrate: ## Run database migrations
	$(ALEMBIC) upgrade head

migrate-create: ## Create a new migration (usage: make migrate-create msg="migration message")
	$(ALEMBIC) revision --autogenerate -m "$(msg)"

run: ## Run development server
	$(UVICORN) app.main:app --reload --host 0.0.0.0 --port 8000

run-prod: ## Run production server
	$(UVICORN) app.main:app --host 0.0.0.0 --port 8000 --workers 4

docker-build: ## Build Docker image
	docker build -t discuzz-api .

docker-up: ## Start Docker containers
	docker-compose up -d

docker-down: ## Stop Docker containers
	docker-compose down

docker-logs: ## View Docker logs
	docker-compose logs -f

clean: ## Clean up cache and temp files
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	rm -rf .coverage htmlcov/

seed: ## Seed the database with sample data
	$(PYTHON) -c "from scripts.seed import seed_database; import asyncio; asyncio.run(seed_database())"
