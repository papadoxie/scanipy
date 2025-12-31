# Scanipy AI Agent Instructions

## Architecture Overview

Scanipy is a security research tool that searches GitHub for code patterns and runs SAST analysis (Semgrep/CodeQL). Architecture follows strict separation of concerns:

- **`scanipy.py`**: CLI interface only (argparse + Display class). No business logic.
- **`models.py`**: Pure data classes (@dataclass) + constants. No functions except @property.
- **`integrations/github/`**: External API clients (REST + GraphQL, rate limiting, retries)
- **`tools/semgrep/` & `tools/codeql/`**: Analysis tool runners + SQLite persistence for resume capability

**Critical flow**: CLI parses args → builds config dataclasses → calls `search_repositories()` → optionally runs analysis tools → saves to JSON/database

## Mandatory Code Standards

**Every Python file must start with:**
```python
from __future__ import annotations
```

**Type hints required everywhere:**
- Use `list[T]` not `List[T]`, `dict[K,V]` not `Dict[K,V]`, `str | None` not `Optional[str]`
- Every function needs param types + return type
- Run `mypy scanipy.py models.py integrations/ tools/ --ignore-missing-imports` (zero errors required)

**100% test coverage is non-negotiable:**
- New code without tests = CI failure
- Mock all external calls: `@patch('subprocess.run')`, `@patch('requests.get')`
- Test both success and failure paths
- Run: `python -m pytest tests/ --cov=. --cov-fail-under=100`

**Formatting with ruff (line length 100):**
```bash
ruff format .  # Auto-format
ruff check .   # Lint (use --fix for auto-fixes)
```

## Key Design Patterns

**Search strategies** (`integrations/github/search.py`):
- `TIERED_STARS`: Searches in star buckets (10k+, 1k-10k, etc.) to prioritize popular repos
- `GREEDY`: Fast but may miss high-star repos due to GitHub API's 1000-result limit

**Resume capability** (tools/*/results_db.py):
- Both Semgrep and CodeQL use SQLite to track analyzed repos per session
- Session matched by: query + rules/language + other params
- `--*-resume` flag skips already-analyzed repos, survives interruptions

**Rate limiting** (integrations/github/github.py):
- Exponential backoff with `RETRY_BACKOFF` multiplier
- Automatic detection via HTTP 429 + `X-RateLimit-Remaining` header
- Different delays for different operations (batch queries vs content fetching)

## Development Workflow

**Full check before commit (pre-commit hook enforces this):**
```bash
make check  # Runs ruff format + ruff check + mypy + pytest
```

**Git pre-commit hook** (installed via `make dev`):
- Blocks commits if linting/formatting/tests fail
- Never use `git commit --no-verify`
- Located at `scripts/pre-commit`

**Adding a new CLI option:**
1. Add argument in `scanipy.py::create_argument_parser()` (use --kebab-case)
2. Add field to relevant @dataclass in `models.py`
3. Pass to function in `scanipy.py::main()`
4. Write tests covering the new option

**Adding a new analysis tool:**
1. Create `tools/<toolname>/` with `<toolname>_runner.py` + `results_db.py`
2. Follow Semgrep/CodeQL pattern: runner takes config dataclass + returns `tuple[bool, str]`
3. Implement resume via SQLite (see existing `results_db.py` files)
4. Mock subprocess calls in tests: `@patch('subprocess.run')`

## Common Pitfalls

- **Don't catch bare `Exception`**: Use specific exceptions (`GitHubAPIError`, `subprocess.CalledProcessError`)
- **Don't use `shell=True`**: Always pass subprocess commands as lists for security
- **Don't use mutable defaults**: Use `field(default_factory=list)` in dataclasses
- **Don't skip `from __future__ import annotations`**: CI will fail on import order
- **Don't bypass pre-commit hooks**: Fix issues instead of committing with `--no-verify`

## Testing Patterns

**Use fixtures from `tests/conftest.py`:**
- `mock_github_token`: Returns test token string
- `mock_env_token`: Sets GITHUB_TOKEN in environment
- `sample_search_config`: Pre-configured SearchConfig

**Mock external dependencies:**
```python
@patch('subprocess.run')
def test_codeql_success(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout="Success")
    success, output = analyze_repo(...)
    assert success is True
```

**Database tests use tempfile:**
```python
with tempfile.NamedTemporaryFile(suffix=".db") as f:
    db = ResultsDatabase(f.name)
    # Test database operations
```

## Critical Files Reference

- `.github/CODING_GUIDELINES.md`: Comprehensive style guide (940 lines)
- `pyproject.toml`: Build config, dependencies, coverage settings
- `Makefile`: Common dev tasks (`make check`, `make test`, `make dev`)
- `integrations/github/models.py`: API constants + custom exceptions
- `tools/*/results_db.py`: Resume capability implementation (session tracking)

## Package Distribution

- PyPI package name: `scanipy-cli` (not `scanipy`)
- Entry point: `scanipy` command (maps to `scanipy:main`)
- Version managed by `hatch-vcs` from git tags
- Build: `python -m build` (creates wheel + sdist in `dist/`)
