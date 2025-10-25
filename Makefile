# Makefile for AI Service
# Local development and testing

PYTHON=./venv/bin/python
MODULE=run.py

export ENV?=development

# Development targets
start-dev:
	ENV=development $(PYTHON) $(MODULE)

start-test:
	ENV=testing $(PYTHON) $(MODULE)

start-prod:
	ENV=production $(PYTHON) $(MODULE)

# Testing targets
run-tests:
	$(PYTHON) -m pytest

run-tests-verbose:
	$(PYTHON) -m pytest -v

run-tests-clients:
	$(PYTHON) -m pytest tests/clients/ -v

run-tests-e2e:
	$(PYTHON) -m pytest tests/test_e2e.py -v

run-tests-all:
	$(PYTHON) -m pytest -v

# Install coverage with: pip install pytest-cov
run-tests-coverage:
	$(PYTHON) -m pytest --cov=app --cov-report=html --cov-report=term

# Docker targets
docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-up-logs:
	docker compose up

docker-down:
	docker compose down

docker-restart:
	docker compose restart

docker-logs:
	docker compose logs -f ai-service

docker-shell:
	docker compose exec ai-service /bin/bash

docker-clean:
	docker compose down -v
	docker system prune -f

docker-rebuild:
	docker compose down
	docker compose build --no-cache
	docker compose up -d

# Test the Docker deployment
docker-test:
	@echo "Testing Docker deployment..."
	@sleep 5
	@curl -s http://localhost:8000/health/ping || echo "Service not ready yet"
	@curl -s http://localhost:8000/health || echo "Health check failed"

# Help target
help:
	@echo "Available targets:"
	@echo ""
	@echo "Development:"
	@echo "  start-dev           - Start service in development mode"
	@echo "  start-test          - Start service in testing mode"
	@echo "  start-prod          - Start service in production mode"
	@echo ""
	@echo "Testing:"
	@echo "  run-tests           - Run all tests"
	@echo "  run-tests-verbose   - Run tests with verbose output"
	@echo "  run-tests-coverage  - Run tests with coverage report"
	@echo ""
	@echo "Docker:"
	@echo "  docker-build        - Build Docker image"
	@echo "  docker-up           - Start Docker container in background"
	@echo "  docker-up-logs      - Start Docker container with logs"
	@echo "  docker-down         - Stop Docker container"
	@echo "  docker-restart      - Restart Docker container"
	@echo "  docker-logs         - Show container logs"
	@echo "  docker-shell        - Open shell in container"
	@echo "  docker-clean        - Remove containers and volumes"
	@echo "  docker-rebuild      - Rebuild and restart container"
	@echo "  docker-test         - Test Docker deployment"
	@echo ""
	@echo "Deployment:"
	@echo "  Push to 'main' or 'production' branch to trigger GitHub Actions deployment"

.PHONY: start-dev start-test start-prod run-tests run-tests-verbose \
        run-tests-clients run-tests-e2e run-tests-all run-tests-coverage \
        docker-build docker-up docker-up-logs docker-down docker-restart \
        docker-logs docker-shell docker-clean docker-rebuild docker-test help

