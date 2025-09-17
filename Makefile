.PHONY: help install dev test lint format type-check clean docker ui run-screener run-analyzer run-strategy run-execution

# Default target
help:
	@echo "Algorithmic Trader - Available commands:"
	@echo ""
	@echo "Setup & Development:"
	@echo "  install         Install dependencies with poetry"
	@echo "  dev             Install dev dependencies"
	@echo "  clean           Clean cache files and build artifacts"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint            Run linting with ruff"
	@echo "  format          Format code with black and isort"
	@echo "  type-check      Run type checking with mypy"
	@echo "  test            Run all tests"
	@echo "  test-unit       Run unit tests only"
	@echo "  test-golden     Run golden tests only"
	@echo ""
	@echo "Applications:"
	@echo "  run-screener    Run screener pipeline"
	@echo "  run-analyzer    Run analyzer pipeline"
	@echo "  run-strategy    Run strategy engine"
	@echo "  run-execution   Run execution engine"
	@echo ""
	@echo "UI & Dashboard:"
	@echo "  ui              Run Streamlit UI locally"
	@echo "  ui.docker.build Build UI Docker image"
	@echo "  ui.docker.push  Push UI Docker image"
	@echo "  ui.deploy       Deploy UI to K8s"
	@echo ""
	@echo "Infrastructure:"
	@echo "  docker          Build all Docker images"
	@echo "  deploy          Deploy to Kubernetes"
	@echo "  logs            View application logs"
	@echo ""
	@echo "Backtesting:"
	@echo "  backtest        Run QuantConnect Lean backtests"
	@echo "  backtest.docker Run backtests in Docker"

# Environment variables
POETRY := poetry
PYTHON := $(POETRY) run python
PYTEST := $(POETRY) run pytest
RUFF := $(POETRY) run ruff
BLACK := $(POETRY) run black
ISORT := $(POETRY) run isort
MYPY := $(POETRY) run mypy
STREAMLIT := $(POETRY) run streamlit
DOCKER_REGISTRY := ghcr.io/abhikanap
APP_VERSION := $(shell git rev-parse --short HEAD || echo "latest")

# Setup & Development
install:
	$(POETRY) install

dev:
	$(POETRY) install --with dev

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	rm -rf dist/ build/ *.egg-info/

# Code Quality
lint:
	$(RUFF) check .

format:
	$(BLACK) .
	$(ISORT) .
	$(RUFF) --fix .

type-check:
	$(MYPY) packages/ apps/ ui/

test:
	$(PYTEST) tests/ -v --cov=packages --cov=apps --cov=ui --cov-report=term-missing

test-unit:
	$(PYTEST) tests/unit/ -v

test-golden:
	$(PYTEST) tests/golden/ -v

# Applications
run-screener:
	$(PYTHON) -m apps.screener.cli run --provider yahoo

run-analyzer:
	$(PYTHON) -m apps.analyzer.cli run

run-strategy:
	$(PYTHON) -m apps.strategy.cli run

run-execution:
	$(PYTHON) -m apps.execution.cli run --dry-run

run-pipeline:
	make run-screener && make run-analyzer && make run-strategy

# UI & Dashboard
ui:
	$(STREAMLIT) run ui/app.py --server.port=8501

ui.docker.build:
	docker build -f infra/docker/Dockerfile.ui -t $(DOCKER_REGISTRY)/algorithmic-trader-ui:$(APP_VERSION) .

ui.docker.push:
	docker push $(DOCKER_REGISTRY)/algorithmic-trader-ui:$(APP_VERSION)

ui.deploy:
	kubectl apply -f infra/k8s/ui/

# Infrastructure
docker:
	docker build -f infra/docker/Dockerfile.api -t $(DOCKER_REGISTRY)/algorithmic-trader-api:$(APP_VERSION) .
	docker build -f infra/docker/Dockerfile.ui -t $(DOCKER_REGISTRY)/algorithmic-trader-ui:$(APP_VERSION) .
	docker build -f infra/docker/Dockerfile.worker -t $(DOCKER_REGISTRY)/algorithmic-trader-worker:$(APP_VERSION) .

docker.push:
	docker push $(DOCKER_REGISTRY)/algorithmic-trader-api:$(APP_VERSION)
	docker push $(DOCKER_REGISTRY)/algorithmic-trader-ui:$(APP_VERSION)
	docker push $(DOCKER_REGISTRY)/algorithmic-trader-worker:$(APP_VERSION)

deploy:
	kubectl apply -f infra/k8s/

logs:
	kubectl logs -f deployment/algorithmic-trader-api -n trading

# Backtesting
backtest:
	$(PYTHON) -m lean backtest "Strategy Library/BasicStrategyAlgorithm"

backtest.docker:
	docker run --rm -v $(PWD)/artifacts:/Lean/Outputs quantconnect/lean:latest

# Development helpers
setup-pre-commit:
	$(POETRY) run pre-commit install

check-all: lint type-check test

ci: install check-all

# AWS/Cloud helpers (if using EKS)
aws.login:
	aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $(DOCKER_REGISTRY)

eks.context:
	aws eks update-kubeconfig --region us-east-1 --name algorithmic-trader

# Local development database
db.start:
	docker run -d --name postgres-trading -p 5432:5432 -e POSTGRES_PASSWORD=trading -e POSTGRES_DB=trading postgres:15

db.stop:
	docker stop postgres-trading && docker rm postgres-trading

# Redis for background tasks
redis.start:
	docker run -d --name redis-trading -p 6379:6379 redis:7-alpine

redis.stop:
	docker stop redis-trading && docker rm redis-trading

# Full local environment
local.start: db.start redis.start

local.stop: db.stop redis.stop

# Production-like testing
prod.test:
	@echo "Running production-like tests..."
	$(PYTEST) tests/ -v --cov=packages --cov=apps --cov=ui -x
	make type-check
	make lint
	@echo "✅ All production checks passed!"

# ======================
# DOCKER COMMANDS
# ======================

# Docker Compose configuration
DOCKER_COMPOSE := $(shell which docker-compose 2>/dev/null || echo "docker compose")
ENV_FILE := .env.docker

docker-check-env: ## Check if Docker environment file exists
	@if [ ! -f $(ENV_FILE) ]; then \
		echo "Creating $(ENV_FILE) from template..."; \
		cp .env.docker.template $(ENV_FILE); \
		echo "Please edit $(ENV_FILE) and add your Alpaca API keys"; \
	fi

docker-build: docker-check-env ## Build Docker images
	@echo "Building Docker images..."
	$(DOCKER_COMPOSE) --env-file $(ENV_FILE) build --no-cache

docker-start: docker-check-env ## Start all Docker services
	@echo "Starting Docker services..."
	$(DOCKER_COMPOSE) --env-file $(ENV_FILE) up -d
	@echo "Waiting for services to be ready..."
	@sleep 10

docker-stop: ## Stop all Docker services
	@echo "Stopping Docker services..."
	$(DOCKER_COMPOSE) down

docker-restart: ## Restart Docker services
	$(DOCKER_COMPOSE) restart

docker-logs: ## Show Docker service logs
	$(DOCKER_COMPOSE) logs -f

docker-status: ## Show Docker service status
	@echo "Service Status:"
	@$(DOCKER_COMPOSE) ps
	@echo ""
	@echo "Access URLs:"
	@echo "  📊 Trading Dashboard: http://localhost:8501"
	@echo "  📈 Prometheus: http://localhost:9090"
	@echo "  📉 Grafana: http://localhost:3000"

docker-shell: ## Open shell in trading container
	$(DOCKER_COMPOSE) exec trading-engine bash

docker-pipeline: ## Run trading pipeline in Docker
	$(DOCKER_COMPOSE) --env-file $(ENV_FILE) run --rm pipeline-runner

docker-backtest: ## Run backtest in Docker
	$(DOCKER_COMPOSE) --env-file $(ENV_FILE) run --rm backtest-runner

docker-clean: ## Clean up Docker containers and volumes
	$(DOCKER_COMPOSE) down --volumes --remove-orphans
	docker system prune -f

docker-setup: docker-build docker-start docker-status ## Complete Docker setup
	@echo "✅ Docker setup completed! Dashboard available at http://localhost:8501"
