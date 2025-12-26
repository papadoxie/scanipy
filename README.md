# 📡 Scanipy

A powerful command-line tool to scan open source code-bases on GitHub for security patterns and vulnerabilities. Scanipy searches GitHub repositories for specific code patterns and optionally runs [Semgrep](https://semgrep.dev/) analysis on discovered code.

[![Tests](https://github.com/papadoxie/scanipy/actions/workflows/tests.yml/badge.svg)](https://github.com/papadoxie/scanipy/actions/workflows/tests.yml)
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen.svg)](https://github.com/papadoxie/scanipy)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

## 🎯 Features

- **Smart Code Search**: Search GitHub for specific code patterns across millions of repositories
- **Tiered Star Search**: Prioritize popular, well-maintained repositories by searching in star tiers (100k+, 50k-100k, 20k-50k, 10k-20k, 5k-10k, 1k-5k)
- **Keyword Filtering**: Filter results by keywords found in file contents
- **Multiple Sort Options**: Sort by stars (popularity) or recently updated
- **Semgrep Integration**: Automatically clone and scan top repositories with Semgrep for security vulnerabilities
- **Custom Rules**: Use built-in security rules or provide your own Semgrep rules
- **Colorful Output**: Beautiful terminal output with progress indicators

## 📋 Table of Contents

- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Usage](#-usage)
- [Configuration](#%EF%B8%8F-configuration)
- [Examples](#-examples)
- [Development](#-development)
- [Contributing](#-contributing)

## 🚀 Installation

### Prerequisites

- Python 3.12 or higher
- A GitHub Personal Access Token ([create one here](https://github.com/settings/tokens))
- (Optional) [Semgrep](https://semgrep.dev/docs/getting-started/) for security analysis

### Install from source

```bash
# Clone the repository
git clone https://github.com/papadoxie/scanipy.git
cd scanipy

# Create virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Set up GitHub Token

```bash
# Option 1: Environment variable
export GITHUB_TOKEN="your_github_token_here"

# Option 2: Create a .env file
echo "GITHUB_TOKEN=your_github_token_here" > .env
```

## ⚡ Quick Start

```bash
# Search for repositories using extractall (potential path traversal)
python scanipy.py --query "extractall" --language python

# Search and run Semgrep analysis
python scanipy.py --query "extractall" --language python --run-semgrep
```

## 📖 Usage

### Basic Search

```bash
# Search for a code pattern
python scanipy.py --query "pickle.loads"

# Search with a specific language
python scanipy.py --query "eval(" --language python
```

### Language & Extension Filtering

```bash
# Search in Python files only
python scanipy.py --query "subprocess.call" --language python

# Search in specific file extensions
python scanipy.py --query "os.system" --extension ".py"

# Combine both
python scanipy.py --query "exec(" --language python --extension ".py"
```

### Keyword Filtering

Filter results to only include files containing specific keywords:

```bash
# Find extractall usage that also mentions path or directory
python scanipy.py --query "extractall" --keywords "path,directory,zip"
```

### Search Strategies

Scanipy offers two search strategies:

| Strategy | Description | Best For |
|----------|-------------|----------|
| `tiered` (default) | Searches repositories in star tiers (100k+, 50k-100k, 20k-50k, etc.) | Finding popular, well-maintained code |
| `greedy` | Standard GitHub search, faster but may miss high-star repos | Quick searches, less popular patterns |

```bash
# Use tiered search (default) - prioritizes popular repos
python scanipy.py --query "extractall" --search-strategy tiered

# Use greedy search - faster but less targeted
python scanipy.py --query "extractall" --search-strategy greedy
```

### Sorting Results

```bash
# Sort by stars (default)
python scanipy.py --query "extractall" --sort-by stars

# Sort by recently updated
python scanipy.py --query "extractall" --sort-by updated
```

### Semgrep Analysis

Automatically clone and scan the top 10 repositories with Semgrep:

```bash
# Run with default Semgrep rules
python scanipy.py --query "extractall" --run-semgrep

# Use custom Semgrep rules
python scanipy.py --query "extractall" --run-semgrep --rules ./my_rules.yaml

# Use built-in tarslip rules
python scanipy.py --query "extractall" --run-semgrep --rules ./tools/semgrep/rules/tarslip.yaml

# Use Semgrep Pro
python scanipy.py --query "extractall" --run-semgrep --pro

# Keep cloned repositories after analysis
python scanipy.py --query "extractall" --run-semgrep --keep-cloned --clone-dir ./repos
```

## ⚙️ Configuration

### Command Line Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--query` | `-q` | Code pattern to search for | Required |
| `--language` | `-l` | Programming language filter | None |
| `--extension` | `-e` | File extension filter | None |
| `--keywords` | `-k` | Comma-separated keywords to filter by | None |
| `--additional-params` | | Extra GitHub search parameters | None |
| `--pages` | `-p` | Max pages to retrieve (max 10) | 5 |
| `--search-strategy` | `-s` | Search strategy: `tiered` or `greedy` | `tiered` |
| `--sort-by` | | Sort by: `stars` or `updated` | `stars` |
| `--github-token` | | GitHub token (or use env var) | `$GITHUB_TOKEN` |
| `--output` | `-o` | Output JSON file path | `repos.json` |
| `--input-file` | `-i` | Load repos from JSON file (skip search) | None |
| `--verbose` | `-v` | Enable verbose output | False |
| `--run-semgrep` | | Run Semgrep on top 10 repos | False |
| `--semgrep-args` | | Additional Semgrep arguments | None |
| `--pro` | | Use Semgrep Pro | False |
| `--rules` | | Custom Semgrep rules path | None |
| `--clone-dir` | | Directory for cloned repos | Temp dir |
| `--keep-cloned` | | Keep repos after analysis | False |

### Environment Variables

| Variable | Description |
|----------|-------------|
| `GITHUB_TOKEN` | GitHub Personal Access Token |

## 💡 Examples

### Security Research

```bash
# Find potential command injection vulnerabilities
python scanipy.py --query "os.system" --language python --keywords "user,input,request"

# Find potential SQL injection
python scanipy.py --query "execute(" --language python --keywords "format,user,%s"

# Find unsafe deserialization
python scanipy.py --query "pickle.loads" --language python --run-semgrep

# Find path traversal vulnerabilities (tarslip)
python scanipy.py --query "extractall" --language python --run-semgrep --rules ./tools/semgrep/rules/tarslip.yaml
```

### Continue Analysis from Saved Results

Scanipy automatically saves search results to `repos.json` (or your specified output file). You can continue analysis later without re-running the search:

```bash
# First, run a search (results saved to repos.json)
python scanipy.py --query "memcpy" --language c --output repos.json

# Later, continue with Semgrep analysis using saved results
python scanipy.py --query "memcpy" --input-file repos.json --run-semgrep

# Use a custom input file
python scanipy.py --query "extractall" -i my_repos.json --run-semgrep --rules ./my_rules.yaml
```

### Code Pattern Analysis

```bash
# Find deprecated API usage
python scanipy.py --query "urllib2" --language python

# Find specific library usage in popular repos
python scanipy.py --query "import tensorflow" --language python --search-strategy tiered

# Find recently updated repos using a pattern
python scanipy.py --query "FastAPI" --language python --sort-by updated
```

### Advanced Filtering

```bash
# Search with GitHub search qualifiers
python scanipy.py --query "eval(" --additional-params "stars:>1000 -org:microsoft"

# Combine multiple filters
python scanipy.py \
  --query "subprocess" \
  --language python \
  --keywords "shell=True,user" \
  --pages 10 \
  --search-strategy tiered
```

## 🛠️ Development

### Setup Development Environment

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

### Running Tests

```bash
# Run all tests
make test

# Run tests with coverage report
make coverage

# Run specific test file
python -m pytest tests/test_github_client.py -v
```

### Linting & Type Checking

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

### Manual Hook Installation

If not using `make`, you can install hooks manually:

```bash
./scripts/setup-hooks.sh
```

### Project Structure

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
│   └── semgrep/
│       ├── semgrep_runner.py  # Semgrep integration
│       └── rules/
│           └── tarslip.yaml   # Built-in security rules
├── tests/                  # Comprehensive test suite (233 tests, 100% coverage)
├── scripts/
│   ├── pre-commit          # Git pre-commit hook
│   └── setup-hooks.sh      # Hook installation script
└── .github/
    └── workflows/
        └── tests.yml       # CI/CD pipeline
```

### Code Quality

- **100% test coverage** enforced via CI
- **Ruff linting** for code style and error detection
- **Mypy type checking** for static type analysis
- **Pre-commit hooks** run linting and tests before each commit
- **GitHub Actions** validates all PRs with lint, typecheck, and test jobs

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Run `make dev` to set up your environment
4. Make your changes
5. Ensure tests pass (`make test`)
6. Commit your changes (pre-commit hook will run tests)
7. Push to your branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### Guidelines

- Maintain 100% test coverage
- Follow existing code style
- Add tests for new features
- Update documentation as needed

## 🙏 Acknowledgments

- [GitHub API](https://docs.github.com/en/rest) for code search capabilities
- [Semgrep](https://semgrep.dev/) for static analysis
- [Colorama](https://pypi.org/project/colorama/) for cross-platform terminal colors

---

<p align="center">
  Made with ❤️ for the security research community
</p>
