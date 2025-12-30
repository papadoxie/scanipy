# Scanipy Coding Guidelines for AI Assistants

**IMPORTANT**: These guidelines are mandatory rules, not suggestions. Follow them precisely when generating or modifying code for the scanipy project. Failure to follow these rules will result in rejected code.

## Absolute Requirements

1. **ALL code must pass CI checks** (linting, type checking, tests)
2. **100% test coverage is mandatory** - no exceptions
3. **Type hints are required** on all functions
4. **Never bypass pre-commit hooks**
5. **Never commit without running full test suite first**

## 1. Code Style & Formatting

### 1.1 Exact Tool Usage
**MUST** use Ruff for formatting and linting:
```bash
# ALWAYS run before committing:
ruff format .          # Auto-format all files
ruff check .           # Check for errors
```

**DO NOT**:
- Use other formatters (black, autopep8, etc.)
- Manually format code
- Assume code is formatted correctly

### 1.2 Line Length
**HARD LIMIT**: 100 characters per line
- Configured in `pyproject.toml` under `[tool.ruff]`
- Ruff will enforce this automatically
- Do not exceed this limit manually

### 1.3 Import Rules
**REQUIRED** at top of every Python file:
```python
from __future__ import annotations
```

**Import order** (enforced by ruff):
1. Standard library imports
2. Third-party imports  
3. Local application imports

**Example**:
```python
from __future__ import annotations

import os
import sys
from pathlib import Path

import requests
from colorama import Fore

from integrations.github import RestAPI
from models import SearchConfig
```

**DO NOT**:
- Use relative imports (no `from . import`)
- Mix import styles

### 1.4 Type Hints (MANDATORY)

**EVERY function MUST have**:
- Type hints for ALL parameters
- Return type annotation
- Use modern syntax (Python 3.12+)

**CORRECT**:
```python
def search_repos(query: str, max_pages: int = 5) -> list[dict[str, Any]]:
    """Search repositories."""
    pass

def process_file(path: str | None = None) -> tuple[bool, str]:
    """Process file."""
    pass
```

**WRONG** (DO NOT DO THIS):
```python
# Missing types
def search_repos(query, max_pages=5):
    pass

# Old typing module syntax  
def search_repos(query: str) -> List[Dict[str, Any]]:
    pass

# Missing return type
def search_repos(query: str, max_pages: int = 5):
    pass
```

**Type syntax rules**:
- Use `| None` NOT `Optional[...]`
- Use `list[...]` NOT `List[...]`
- Use `dict[...]` NOT `Dict[...]`
- Use `tuple[...]` NOT `Tuple[...]`
- Use `Any` from `typing` when type is truly dynamic

### 1.5 Docstrings (MANDATORY)

**EVERY** public function/class/module MUST have a docstring.

**Required format** (Google style):
```python
def analyze_repository(
    repo_url: str,
    config: CodeQLConfig,
    colors: Colors,
) -> tuple[bool, str]:
    """Run CodeQL analysis on a repository.

    Args:
        repo_url: GitHub repository URL (https://github.com/owner/repo)
        config: CodeQL configuration with query suite and output settings
        colors: Terminal color configuration for output formatting

    Returns:
        Tuple of (success_flag, output_or_error_message)

    Raises:
        ValueError: If repo_url is invalid format
        subprocess.CalledProcessError: If CodeQL command fails
    """
```

**Required sections**:
- One-line summary (always present)
- `Args:` - Describe ALL parameters
- `Returns:` - Describe return value(s)
- `Raises:` - List exceptions that can be raised (if any)

**DO NOT**:
- Skip docstrings
- Use other styles (Sphinx, NumPy)
- Leave Args/Returns empty

## 2. Type Checking (MANDATORY)

**MUST pass mypy** before committing:
```bash
mypy scanipy.py models.py integrations/ tools/ --ignore-missing-imports
```

**Zero type errors allowed** - fix all errors, do not suppress with `# type: ignore` unless absolutely necessary and documented.

**When to use `# type: ignore`**:
- Only for third-party library issues
- Must include comment explaining why: `# type: ignore  # requests-mock typing issue`

## 3. Testing (STRICT REQUIREMENTS)

### 3.1 Coverage Requirement
**ABSOLUTE RULE**: 100% code coverage required

**Command**:
```bash
python -m pytest tests/ --cov=. --cov-fail-under=100
```

**This means**:
- EVERY new function MUST have tests
- EVERY new branch/condition MUST be tested
- EVERY error case MUST be tested
- CI will FAIL if coverage < 100%

### 3.2 Test File Organization
**Naming convention** (STRICT):
- Test files: `test_<module_name>.py`
- Test functions: `test_<function_name>_<scenario>`

**Examples**:
```
tests/test_scanipy.py          # Tests for scanipy.py
tests/test_codeql_runner.py    # Tests for tools/codeql/codeql_runner.py
tests/test_github_client.py    # Tests for integrations/github/github.py
```

### 3.3 Test Structure (MANDATORY)

**Use pytest fixtures** from `tests/conftest.py`:
```python
def test_search_with_mock_api(mock_github_token, mock_requests):
    """Test search with mocked GitHub API."""
    # Test implementation
```

**ALWAYS mock**:
- Network calls (`requests`, `urllib`)
- Subprocess calls (`subprocess.run`, `subprocess.Popen`)
- File system operations
- Environment variables

**Example mocking pattern**:
```python
@patch('subprocess.run')
def test_codeql_create_database_success(mock_run, mock_colors):
    """Test successful database creation."""
    mock_run.return_value = MagicMock(returncode=0, stdout="Success")
    # Test code
```

**Test BOTH**:
- Success cases
- Error/failure cases

### 3.4 Pre-commit Hooks (NEVER BYPASS)

**Hooks run automatically** on `git commit`:
1. Linting check (ruff)
2. Format check (ruff)
3. Full test suite with coverage

**DO NOT**:
- Use `git commit --no-verify`
- Skip tests
- Commit code that doesn't pass hooks

**If hooks fail**: Fix the code, don't bypass

## 4. Architecture (STRICT STRUCTURE)

### 4.1 Module Organization (DO NOT VIOLATE)

```
scanipy/
├── scanipy.py              # CLI ONLY: argparse, Display class, main()
├── models.py               # DATA ONLY: dataclasses, constants, Colors
├── integrations/github/    # API ONLY: GitHub REST/GraphQL clients
└── tools/                  # TOOLS ONLY: semgrep, codeql runners
```

**Rules**:
- `scanipy.py` - CLI interface ONLY, no business logic
- `models.py` - Pure data classes ONLY, no functions except properties
- `integrations/` - External API clients ONLY
- `tools/` - Analysis tool runners ONLY

**DO NOT**:
- Put business logic in `scanipy.py`
- Put functions in `models.py` (except `@property`)
- Mix concerns across modules

### 4.2 Where to Put New Code

**Adding a new CLI argument?**
→ `scanipy.py` in the `parse_arguments()` function

**Adding a new configuration option?**
→ `models.py` as a field in appropriate `@dataclass`

**Adding GitHub API functionality?**
→ `integrations/github/github.py` in appropriate client class

**Adding a new analysis tool?**
→ New directory under `tools/` (e.g., `tools/bandit/`)

**Adding utility functions?**
→ In the module where they're used, not in a "utils" file

### 4.3 Data Classes (USE THESE)

**ALWAYS use `@dataclass`** for configuration and data transfer:

```python
from dataclasses import dataclass, field

@dataclass
class SearchConfig:
    """Configuration for GitHub code search."""
    query: str
    language: str = ""
    max_pages: int = 5
    keywords: list[str] = field(default_factory=list)  # CORRECT for mutable defaults
```

**DO NOT**:
```python
# WRONG: Regular class for config
class SearchConfig:
    def __init__(self, query, language=""):
        self.query = query
        self.language = language

# WRONG: Mutable default
@dataclass
class SearchConfig:
    keywords: list[str] = []  # BUG: shared between instances
```

### 4.4 Error Handling (SPECIFIC RULES)

**Create custom exceptions** in the module where they're used:

```python
class GitHubAPIError(Exception):
    """Raised when GitHub API request fails."""
    pass
```

**DO catch specific exceptions**:
```python
try:
    response = requests.get(url)
    response.raise_for_status()
except requests.HTTPError as e:
    raise GitHubAPIError(f"API request failed: {e}") from e
```

**DO NOT catch bare Exception**:
```python
# WRONG
try:
    code()
except Exception:  # Too broad
    pass
```

**Exception messages MUST**:
- Be descriptive
- Include context (what was being done)
- Include relevant values (if safe)

## 5. Dependencies (CONTROLLED)

### 5.1 Current Dependencies (DO NOT REMOVE)
```toml
[project.dependencies]
requests = ">=2.31.0"       # HTTP client for GitHub API
python-dotenv = ">=1.0.0"   # .env file loading
colorama = ">=0.4.6"        # Terminal colors
```

### 5.2 Adding New Dependencies (STRICT PROCESS)

**BEFORE adding a dependency**:
1. Check if standard library has solution
2. Check if existing dependency can do it
3. Evaluate: size, maintenance, security

**IF approved**, add to:
1. `pyproject.toml` under `[project.dependencies]`
2. `requirements.txt` for backwards compatibility

**Example**:
```toml
# pyproject.toml
[project.dependencies]
requests = ">=2.31.0"
python-dotenv = ">=1.0.0"
colorama = ">=0.4.6"
new-package = ">=1.0.0"  # Add here
```

```txt
# requirements.txt
requests>=2.31.0
python-dotenv>=1.0.0
colorama>=0.4.6
new-package>=1.0.0  # Add here too
```

**Commit message MUST explain**:
```
feat: add support for X using new-package

new-package is needed because:
- Standard library doesn't support Y
- Provides essential feature Z
- Well-maintained, 10k+ stars, active development
```

## 6. Git Workflow (EXACT FORMAT)

### 6.1 Commit Message Format (MANDATORY)

**Use Conventional Commits**:
```
<type>: <description>

<optional body>
```

**Types** (ONLY use these):
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `test:` - Test additions/changes
- `refactor:` - Code refactoring (no behavior change)
- `ci:` - CI/CD changes
- `build:` - Build system/dependencies
- `chore:` - Other (config, cleanup)

**Examples** (GOOD):
```
feat: add CodeQL SARIF output support

test: add tests for keyword filtering

fix: handle empty GitHub API response correctly

docs: update README with PyPI installation
```

**Examples** (BAD - DO NOT DO):
```
Added feature        # Missing type
feat Added feature   # Missing colon
Feature: new thing   # Wrong type (use 'feat')
fix: bug             # Too vague
```

### 6.2 Commit Checklist (ALWAYS DO)

**BEFORE every commit**:
```bash
# 1. Format
ruff format .

# 2. Lint
ruff check .

# 3. Type check
mypy scanipy.py models.py integrations/ tools/ --ignore-missing-imports

# 4. Test with coverage
python -m pytest --cov=. --cov-fail-under=100

# 5. Commit (hooks will run automatically)
git add .
git commit -m "feat: your message"
```

**Or use shortcut**:
```bash
make check  # Runs format, lint, typecheck, test
```

## 7. Documentation (SPECIFIC REQUIREMENTS)

### 7.1 Code Documentation

**When changing function behavior**:
- Update docstring immediately
- Update type hints if signatures change
- Keep docstring and code in sync

**Inline comments**:
- Use sparingly - code should be self-documenting
- Only for complex algorithms or non-obvious decisions
- Format: `# Explanation of why, not what`

**DO NOT**:
```python
# WRONG: Obvious comment
x = x + 1  # Increment x

# WRONG: Outdated comment
# This searches by stars  (but code now searches by date)
results = search_by_date()
```

**DO**:
```python
# CORRECT: Non-obvious reasoning
# GitHub API returns max 1000 results, so we search in star tiers
# to ensure we get high-quality repos first
for tier in star_tiers:
    search_tier(tier)
```

### 7.2 User Documentation (MkDocs)

**Location**: `docs/` directory

**Structure**:
```
docs/
├── index.md              # Home page
├── installation.md       # Setup instructions
├── usage.md             # Basic usage
├── semgrep.md           # Semgrep integration
├── codeql.md            # CodeQL integration
├── cli-reference.md     # All CLI options
├── examples.md          # Real-world examples
└── development.md       # Contributing guide
```

**When adding a feature**:
1. Update relevant `.md` file in `docs/`
2. Add examples showing the feature
3. Update CLI reference if new option added

**CLI examples format**:
```bash
# CORRECT: Use 'scanipy' command (for pip users)
scanipy --query "test" --language python

# INCLUDE NOTE for source users
# Note: If running from source, use: python scanipy.py
```

**DO NOT**:
- Forget to update docs when changing features
- Use inconsistent command formats
- Add docs without examples

### 7.3 README.md

**Keep concise** - README is for quick start only

**Structure** (DO NOT change):
1. Title and badges
2. Features (bullet list)
3. Quick Start (basic usage)
4. Link to full documentation
5. Development section
6. Acknowledgments

**Update when**:
- Adding major features
- Changing installation process
- PyPI package name changes

## 8. CLI Design (PATTERNS)

### 8.1 Argument Naming (EXACT FORMAT)

**Use `--kebab-case`**:
```python
parser.add_argument("--run-semgrep")      # CORRECT
parser.add_argument("--clone-dir")        # CORRECT
parser.add_argument("--output-file")      # CORRECT
```

**DO NOT**:
```python
parser.add_argument("--runSemgrep")       # WRONG: camelCase
parser.add_argument("--run_semgrep")      # WRONG: snake_case
parser.add_argument("--RunSemgrep")       # WRONG: PascalCase
```

**Short forms** (provide for common options):
```python
parser.add_argument("--query", "-q")      # CORRECT
parser.add_argument("--language", "-l")   # CORRECT
parser.add_argument("--output", "-o")     # CORRECT
```

### 8.2 Output Formatting (USE Colors CLASS)

**ALWAYS use** `Colors` from `models.py`:

```python
from models import Colors

# CORRECT
print(f"{Colors.SUCCESS}✅ Analysis complete{Colors.RESET}")
print(f"{Colors.ERROR}❌ Failed to clone{Colors.RESET}")
print(f"{Colors.INFO}🔍 Searching...{Colors.RESET}")
print(f"{Colors.WARNING}⚠️  No results found{Colors.RESET}")
```

**DO NOT**:
```python
# WRONG: Hardcoded ANSI codes
print("\033[32m✅ Success\033[0m")

# WRONG: Direct colorama usage
print(Fore.GREEN + "Success" + Style.RESET_ALL)

# WRONG: No colors
print("Success")
```

**Output guidelines**:
- Use emojis for visual feedback: ✅ ❌ 🔍 📁 🎯 ⚠️ 💡
- Show progress for operations > 1 second
- Respect `--verbose` flag for detailed output
- Always reset colors with `{Colors.RESET}`

### 8.3 Exit Codes (ONLY TWO)

```python
sys.exit(0)  # Success - operation completed
sys.exit(1)  # Error - any error occurred
```

**DO NOT**:
- Use other exit codes
- Exit without code: `sys.exit()` is `sys.exit(0)`
- Forget to exit on error

## 9. Security (CRITICAL RULES)

### 9.1 Secrets Management

**NEVER commit**:
- API tokens
- Passwords
- SSH keys
- Any credentials

**Environment variables** (CORRECT):
```python
# CORRECT: Use environment variable
token = os.getenv("GITHUB_TOKEN")

# CORRECT: Check from .env file
load_dotenv()
token = os.getenv("GITHUB_TOKEN")
```

**Files** (MUST be in `.gitignore`):
```gitignore
.env
*.key
*.pem
secrets/
```

### 9.2 Subprocess Security

**ALWAYS use list format**:
```python
# CORRECT: Arguments as list
subprocess.run(["git", "clone", repo_url, path], check=True)
subprocess.run(["codeql", "database", "create", db_path], check=True)
```

**NEVER use shell=True**:
```python
# WRONG: Shell injection risk
subprocess.run(f"git clone {repo_url}", shell=True)  # VULNERABLE

# WRONG: Unsanitized input
cmd = f"codeql scan {user_input}"
subprocess.run(cmd, shell=True)  # VULNERABLE
```

**Validate inputs**:
```python
# CORRECT: Validate before using
if not repo_url.startswith("https://github.com/"):
    raise ValueError(f"Invalid repo URL: {repo_url}")
subprocess.run(["git", "clone", repo_url, path], check=True)
```

## 10. Performance (KNOWN PATTERNS)

### 10.1 API Rate Limits

**GitHub API limits**:
- REST: 5,000 requests/hour (authenticated)
- GraphQL: 5,000 points/hour

**MUST implement**:
```python
# Exponential backoff for retries
for attempt in range(MAX_RETRIES):
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 429:  # Rate limited
            wait = 2 ** attempt
            time.sleep(wait)
            continue
        response.raise_for_status()
        break
    except requests.RequestException as e:
        if attempt == MAX_RETRIES - 1:
            raise
```

### 10.2 Resource Cleanup

**ALWAYS clean up**:
```python
# CORRECT: Use context manager
with tempfile.TemporaryDirectory() as tmpdir:
    # Use tmpdir
    pass  # Auto-cleaned

# CORRECT: Explicit cleanup
tmpdir = tempfile.mkdtemp()
try:
    # Use tmpdir
finally:
    shutil.rmtree(tmpdir)
```

**Provide `--keep-cloned` option**:
- Users may want to inspect cloned repos
- Useful for debugging
- Document in help text

### 10.3 Database Connections

**ALWAYS use context manager**:
```python
# CORRECT
with sqlite3.connect(db_path) as conn:
    cursor = conn.execute("SELECT * FROM results")
    # Connection auto-closed

# WRONG
conn = sqlite3.connect(db_path)
cursor = conn.execute("SELECT * FROM results")
# Connection leaked
```

---

## Quick Command Reference

**Before every commit, run these in order**:

```bash
# 1. Auto-format code
ruff format .

# 2. Check for lint errors
ruff check .

# 3. Fix auto-fixable lint errors
ruff check --fix .

# 4. Type check
mypy scanipy.py models.py integrations/ tools/ --ignore-missing-imports

# 5. Run full test suite with coverage
python -m pytest --cov=. --cov-fail-under=100

# 6. Commit (hooks run automatically)
git add .
git commit -m "type: description"
```

**Or use single command**:
```bash
make check  # Runs lint, typecheck, test
```

**Build package**:
```bash
python -m build
```

**Run locally**:
```bash
# From source
python scanipy.py --query "test" --language python

# After pip install
scanipy --query "test" --language python
```

---

## AI Assistant Checklist

When generating or modifying code, verify:

- [ ] Added `from __future__ import annotations` at top
- [ ] All functions have type hints (params + return)
- [ ] All public functions have Google-style docstrings
- [ ] Used `list[...]`, `dict[...]`, `| None` (not old typing syntax)
- [ ] Line length ≤ 100 characters
- [ ] Imports organized: stdlib, third-party, local
- [ ] Used `@dataclass` for data classes
- [ ] Used `field(default_factory=list)` for mutable defaults
- [ ] Created tests for new code
- [ ] Tests cover all branches and error cases
- [ ] Mocked external dependencies (requests, subprocess, fs)
- [ ] Used `Colors` class for terminal output
- [ ] Used `--kebab-case` for CLI arguments
- [ ] Validated inputs before subprocess calls
- [ ] Used list format for subprocess (not shell=True)
- [ ] Cleaned up resources (tempfile, db connections)
- [ ] Conventional commit message format
- [ ] Would pass: ruff, mypy, pytest --cov-fail-under=100

---

## Common Patterns

### Creating a new dataclass
```python
from __future__ import annotations

from dataclasses import dataclass, field

@dataclass
class MyConfig:
    """Configuration for my feature."""
    
    required_field: str
    optional_field: str = ""
    list_field: list[str] = field(default_factory=list)
    dict_field: dict[str, int] = field(default_factory=dict)
```

### Adding a CLI argument
```python
# In scanipy.py, parse_arguments() function
parser.add_argument(
    "--my-option",
    "-m",
    help="Description of option",
    default="default_value",
)
```

### Using subprocess safely
```python
try:
    result = subprocess.run(
        ["command", "arg1", "arg2"],
        check=True,
        capture_output=True,
        text=True,
    )
    return True, result.stdout
except subprocess.CalledProcessError as e:
    return False, f"Command failed: {e.stderr}"
```

### Writing tests with mocks
```python
from unittest.mock import MagicMock, patch

@patch('subprocess.run')
def test_my_function(mock_run):
    """Test my function with mocked subprocess."""
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout="success",
        stderr="",
    )
    
    result = my_function()
    
    assert result is True
    mock_run.assert_called_once_with(
        ["expected", "command"],
        check=True,
        capture_output=True,
    )
```

### Error handling pattern
```python
class MyToolError(Exception):
    """Raised when my tool fails."""
    pass

def my_function(param: str) -> str:
    """Do something with param."""
    try:
        result = risky_operation(param)
        return result
    except ValueError as e:
        raise MyToolError(f"Invalid parameter '{param}': {e}") from e
    except Exception as e:
        raise MyToolError(f"Unexpected error processing '{param}': {e}") from e
```

---

## Forbidden Patterns (NEVER DO)

❌ **NO type: ignore without explanation**
```python
result = func()  # type: ignore  # WRONG: No explanation
result = func()  # type: ignore  # library-name has no stubs  # CORRECT
```

❌ **NO bare except**
```python
try:
    code()
except:  # WRONG: Catches everything including KeyboardInterrupt
    pass
```

❌ **NO mutable defaults**
```python
def func(items=[]):  # WRONG: Shared between calls
    items.append(1)

def func(items=None):  # CORRECT
    if items is None:
        items = []
```

❌ **NO shell=True**
```python
subprocess.run(f"git clone {url}", shell=True)  # WRONG: Injection risk
subprocess.run(["git", "clone", url])  # CORRECT
```

❌ **NO hardcoded colors**
```python
print("\033[32mSuccess\033[0m")  # WRONG
print(f"{Colors.SUCCESS}Success{Colors.RESET}")  # CORRECT
```

❌ **NO committing without tests**
```python
# If you add a new function, you MUST add tests
# Coverage must stay at 100%
```

❌ **NO skipping type hints**
```python
def func(x, y):  # WRONG: No types
    pass

def func(x: int, y: str) -> bool:  # CORRECT
    pass
```

---

## Remember

1. **100% test coverage is mandatory** - no exceptions
2. **All functions need type hints** - including return types
3. **All public functions need docstrings** - Google style
4. **Use ruff for formatting** - never manual formatting
5. **Mock external dependencies** - always in tests
6. **Conventional commits** - feat, fix, docs, test, etc.
7. **Never use shell=True** - always list format for subprocess
8. **Clean up resources** - use context managers
9. **Run full checks before commit** - make check
10. **Read existing code** - follow established patterns
