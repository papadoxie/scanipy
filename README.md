# scanipy
A tool to scan open source code-bases for simple patterns

## Development Setup

After cloning the repository, install the git hooks to ensure tests pass before each commit:

```bash
./scripts/setup-hooks.sh
```

This will install a pre-commit hook that runs all tests before allowing a commit.

## Running Tests

```bash
python -m pytest tests/
```

With coverage:

```bash
python -m pytest tests/ --cov=. --cov-report=term-missing
```
