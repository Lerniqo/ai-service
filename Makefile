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

# Help target
help:
	@echo "Available targets:"
	@echo "  start-dev           - Start service in development mode"
	@echo "  start-test          - Start service in testing mode"
	@echo "  start-prod          - Start service in production mode"
	@echo "  run-tests           - Run all tests"
	@echo "  run-tests-verbose   - Run tests with verbose output"
	@echo "  run-tests-coverage  - Run tests with coverage report"
	@echo ""
	@echo "Deployment:"
	@echo "  Push to 'main' or 'production' branch to trigger GitHub Actions deployment"

.PHONY: start-dev start-test start-prod run-tests run-tests-verbose \
        run-tests-clients run-tests-e2e run-tests-all run-tests-coverage help

