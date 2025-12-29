# Development Guide

## Setup Development Environment

```bash
# Clone and setup
git clone https://github.com/papadoxie/scanipy.git
cd scanipy

# Install dependencies and git hooks
make dev
```

This will:

- Install all dependencies
- Install pre-commit hooks (runs tests before each commit)

## Running Tests

```bash
# Run all tests
make test

# Run tests with coverage report
make coverage

# Run specific test file
python -m pytest tests/test_github_client.py -v

# Run specific test
python -m pytest tests/test_codeql_runner.py::TestLanguageMap -v
```

## Linting & Type Checking

```bash
# Run linter (ruff)
make lint

# Run formatter (ruff)
make format

# Run type checker (mypy)
make typecheck

# Run all checks (lint + typecheck + test)
make check
```

## Manual Hook Installation

If not using `make`, you can install hooks manually:

```bash
./scripts/setup-hooks.sh
```

## Project Structure

```
scanipy/
├── scanipy.py              # Main CLI entry point
├── models.py               # Data models and configuration
├── integrations/
│   └── github/
│       ├── github.py       # GitHub API client (REST & GraphQL)
│       ├── models.py       # GitHub-specific models
│       └── search.py       # Search strategies and utilities
├── tools/
│   ├── semgrep/
│   │   ├── semgrep_runner.py  # Semgrep integration
│   │   └── rules/
│   │       └── tarslip.yaml   # Built-in security rules
│   └── codeql/
│       └── codeql_runner.py   # CodeQL integration
├── tests/                  # Comprehensive test suite (333 tests, 100% coverage)
├── scripts/
│   ├── pre-commit          # Git pre-commit hook
│   └── setup-hooks.sh      # Hook installation script
├── docs/                   # Documentation (MkDocs)
└── .github/
    └── workflows/
        └── tests.yml       # CI/CD pipeline
```

## Code Quality Standards

- **100% test coverage** enforced via CI
- **Ruff linting** for code style and error detection
- **Mypy type checking** for static type analysis
- **Pre-commit hooks** run linting and tests before each commit
- **GitHub Actions** validates all PRs with lint, typecheck, and test jobs

## Adding New Features

### 1. Create Tests First

Write tests for your new feature:

```python
# tests/test_new_feature.py
def test_new_feature():
    result = new_function()
    assert result == expected
```

### 2. Implement the Feature

Add your implementation:

```python
# tools/new_tool/new_runner.py
def new_function():
    return "result"
```

### 3. Update Models (if needed)

Add configuration models:

```python
# models.py
@dataclass
class NewConfig:
    enabled: bool = False
    option: str = "default"
```

### 4. Add CLI Arguments (if needed)

Update the argument parser:

```python
# scanipy.py
parser.add_argument("--new-option", help="Description")
```

### 5. Update Documentation

Add documentation for your feature:

```bash
# Create new doc page
docs/new-feature.md

# Update index
docs/index.md
```

### 6. Run All Checks

```bash
make check
```

## Contributing Guidelines

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Run `make dev` to set up your environment
4. Make your changes
5. Ensure tests pass (`make test`)
6. Commit your changes (pre-commit hook will run tests)
7. Push to your branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat: add new feature`
- `fix: resolve bug`
- `docs: update documentation`
- `test: add tests`
- `refactor: improve code structure`

### Pull Request Checklist

- [ ] Tests pass (`make test`)
- [ ] Linting passes (`make lint`)
- [ ] Type checking passes (`make typecheck`)
- [ ] 100% test coverage maintained
- [ ] Documentation updated (if applicable)
