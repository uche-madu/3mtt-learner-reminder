# Makefile for FastAPI project using uv

# Variables
APP_MODULE := app/main.py
HOST := 0.0.0.0
PORT := 8000
DOCKER_SERVICE := web       # Replace with your FastAPI service name
DOCKER_COMPOSE_FILE := docker-compose.yaml
PYTEST_ARGS := tests
TARGET := $(or $(TARGET),local)  # force default to local
MSG ?=                  # optional message

# --- FastAPI commands ---
run: ## Start FastAPI dev server with uv
	@echo "Starting FastAPI dev server with uv..."
	uv run fastapi dev $(APP_MODULE) --host $(HOST) --port $(PORT)

# --- Docker Compose commands ---
up: ## Start Docker Compose services
	@echo "Starting Docker Compose services..."
	docker compose -f $(DOCKER_COMPOSE_FILE) up -d

down: ## Stop Docker Compose services
	@echo "Stopping Docker Compose services..."
	docker compose -f $(DOCKER_COMPOSE_FILE) down

build: ## Build Docker Compose services
	@echo "Building Docker Compose services..."
	docker compose -f $(DOCKER_COMPOSE_FILE) build

shell: ## Enter the FastAPI container shell
	@echo "Entering $(DOCKER_SERVICE) container..."
	docker compose exec $(DOCKER_SERVICE) sh

# --- Alembic ---
# Usage:
#   make migrate               -> upgrade head locally
#   make migrate -t docker     -> upgrade head in Docker container
#   make migrate -m "message"  -> autogenerate revision locally
#   make migrate -t docker -m "message" -> revision in Docker
TARGET ?= local

migrate: ## Run Alembic migrations (local or docker)
ifeq ($(TARGET),docker)
	$(if $(MSG), \
		docker compose exec $(DOCKER_SERVICE) alembic revision --autogenerate -m "$(MSG)", \
		docker compose exec $(DOCKER_SERVICE) alembic upgrade head)
else ifeq ($(TARGET),local)
	$(if $(MSG), \
		alembic revision --autogenerate -m "$(MSG)", \
		alembic upgrade head)
else
	$(error TARGET must be docker or local)
endif


# --- Tests ---
test: ## Run all tests
	uv run pytest $(PYTEST_ARGS)

test-verbose: ## Run all tests in verbose mode
	uv run pytest $(PYTEST_ARGS) -v

test-unit: ## Run unit tests only
	uv run pytest tests -m unit

test-integration: ## Run integration tests only
	uv run pytest tests -m integration

test-e2e: ## Run end-to-end tests only
	uv run pytest tests -m e2e

# --- Pre-commit ---
precommit: ## Run pre-commit hooks on all files
	@echo "Running pre-commit hooks on all files..."
	uv run pre-commit run --all-files


# --- Clean ---
clean: ## Remove cache files
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name "*.pytest_cache" -exec rm -rf {} +

# --- Help ---
help: ## Show available make targets
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

.PHONY: run up down build shell migrate test test-verbose test-unit test-integration test-e2e clean precommit help
