.PHONY: init lint test format clean run-dev run-prod docker-build docker-up help

# Variables
PYTHON := python3.11
PIP := $(PYTHON) -m pip
VENV := venv
PROJECT_NAME := lot-genius

# Default target
.DEFAULT_GOAL := help

## Initialize development environment
init:
	@echo "Initializing development environment..."
	$(PIP) install -U pip
	$(PIP) install pre-commit
	pre-commit install
	@echo "Environment initialized successfully!"

## Run linters
lint:
	@echo "Running linters..."
	@if [ -f "backend/requirements.txt" ]; then \
		cd backend && ruff check . && black --check . && isort --check-only .; \
	else \
		echo "Backend not yet initialized (stub)"; \
	fi

## Run tests
test:
	@echo "Running tests..."
	@if [ -d "backend/tests" ]; then \
		cd backend && pytest tests/ -v; \
	else \
		echo "Tests will be added in Step 2/3 (stub)"; \
	fi

## Format code
format:
	@echo "Formatting code..."
	@if [ -d "backend" ]; then \
		cd backend && black . && isort .; \
	else \
		echo "Backend not yet initialized (stub)"; \
	fi

## Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleanup complete!"

## Run development server
run-dev:
	@echo "Starting development server..."
	@if [ -f "backend/main.py" ]; then \
		cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000; \
	else \
		echo "Backend not yet initialized (stub)"; \
	fi

## Run production server
run-prod:
	@echo "Starting production server..."
	@if [ -f "backend/main.py" ]; then \
		cd backend && gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000; \
	else \
		echo "Backend not yet initialized (stub)"; \
	fi

## Build Docker image
docker-build:
	@echo "Building Docker image..."
	@if [ -f "Dockerfile" ]; then \
		docker build -t $(PROJECT_NAME):latest .; \
	else \
		echo "Dockerfile not yet created (stub)"; \
	fi

## Run Docker containers
docker-up:
	@echo "Starting Docker containers..."
	@if [ -f "docker-compose.yml" ]; then \
		docker-compose up -d; \
	else \
		echo "Docker Compose not yet configured (stub)"; \
	fi

## Show available commands
help:
	@echo "Available commands:"
	@echo "  make init        - Initialize development environment"
	@echo "  make lint        - Run code linters"
	@echo "  make test        - Run test suite"
	@echo "  make format      - Format code with black/isort"
	@echo "  make clean       - Remove build artifacts"
	@echo "  make run-dev     - Start development server"
	@echo "  make run-prod    - Start production server"
	@echo "  make docker-build - Build Docker image"
	@echo "  make docker-up   - Start Docker containers"
	@echo "  make help        - Show this help message"