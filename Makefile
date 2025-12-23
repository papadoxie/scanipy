.PHONY: install dev test hooks clean

# Install production dependencies
install:
	pip install -r requirements.txt

# Install dev dependencies and git hooks
dev: install hooks
	pip install pytest pytest-cov

# Install git hooks
hooks:
	@./scripts/setup-hooks.sh

# Run tests
test:
	python -m pytest tests/

# Run tests with coverage
coverage:
	python -m pytest tests/ --cov=. --cov-report=term-missing

# Clean up
clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage
