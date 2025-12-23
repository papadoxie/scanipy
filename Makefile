.PHONY: install dev test hooks clean lint format typecheck check

# Install production dependencies
install:
	pip install -r requirements.txt

# Install dev dependencies and git hooks
dev: install hooks
	pip install pytest pytest-cov ruff mypy

# Install git hooks
hooks:
	@./scripts/setup-hooks.sh

# Run tests
test:
	python -m pytest tests/

# Run tests with coverage
coverage:
	python -m pytest tests/ --cov=. --cov-report=term-missing

# Run linter
lint:
	ruff check .

# Run formatter
format:
	ruff format .
	ruff check --fix .

# Run type checker
typecheck:
	mypy scanipy.py models.py integrations/ tools/

# Run all checks (lint + typecheck + test)
check: lint typecheck test

# Clean up
clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage .mypy_cache .ruff_cache
