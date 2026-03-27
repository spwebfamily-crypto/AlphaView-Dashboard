PYTHON ?= python

.PHONY: backend-test frontend-build

backend-test:
	cd backend && $(PYTHON) -m pytest

frontend-build:
	cd frontend && npm run build

