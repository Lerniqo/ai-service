# Simple Makefile to run FastAPI app in different environments
# Usage:
# make start-dev
# make start-test
# make start-prod

PYTHON=python
MODULE=run.py

export ENV?=development

start-dev:
	ENV=development $(PYTHON) $(MODULE)

start-test:
	ENV=testing $(PYTHON) $(MODULE)

start-prod:
	ENV=production $(PYTHON) $(MODULE)
