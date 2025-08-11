# Simple Makefile to run FastAPI app in different environments
# Usage:
# make start-dev
# make start-test
# make start-prod

PYTHON=venv/bin/python
MODULE=run.py

export ENV?=development

start-dev:
	ENV=development $(PYTHON) $(MODULE)

start-test:
	ENV=testing $(PYTHON) $(MODULE)

start-prod:
	ENV=production $(PYTHON) $(MODULE)

run-tests:
	$(PYTHON) -m pytest

run-tests-verbose:
	$(PYTHON) -m pytest -v

run-tests-clients:
	$(PYTHON) -m pytest tests/clients/ -v

# Install coverage with: pip install pytest-cov
# run-tests-coverage:
#	$(PYTHON) -m pytest --cov=app --cov-report=html --cov-report=term
