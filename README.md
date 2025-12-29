# 📡 Scanipy

A powerful command-line tool to scan open source code-bases on GitHub for security patterns and vulnerabilities. Scanipy searches GitHub repositories for specific code patterns and optionally runs [Semgrep](https://semgrep.dev/) or [CodeQL](https://codeql.github.com/) analysis on discovered code.

[![Tests](https://github.com/papadoxie/scanipy/actions/workflows/tests.yml/badge.svg)](https://github.com/papadoxie/scanipy/actions/workflows/tests.yml)
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen.svg)](https://github.com/papadoxie/scanipy)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

## 🎯 Features

- **Smart Code Search**: Search GitHub for specific code patterns across millions of repositories
- **Tiered Star Search**: Prioritize popular, well-maintained repositories by searching in star tiers
- **Keyword Filtering**: Filter results by keywords found in file contents
- **Semgrep Integration**: Automatically clone and scan repositories with Semgrep
- **CodeQL Integration**: Run CodeQL analysis for deep semantic security scanning
- **Custom Rules**: Use built-in security rules or provide your own

## ⚡ Quick Start

```bash
# Clone and setup
git clone https://github.com/papadoxie/scanipy.git
cd scanipy
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Set GitHub token
export GITHUB_TOKEN="your_token_here"

# Search for code patterns
python scanipy.py --query "extractall" --language python

# Run Semgrep analysis
python scanipy.py --query "extractall" --language python --run-semgrep

# Run CodeQL analysis
python scanipy.py --query "extractall" --language python --run-codeql
```

## 📚 Documentation

Full documentation is available in the [`docs/`](docs/) directory:

| Document | Description |
|----------|-------------|
| [Installation](docs/installation.md) | Setup instructions and prerequisites |
| [Usage Guide](docs/usage.md) | Basic and advanced usage |
| [Semgrep Integration](docs/semgrep.md) | Running Semgrep security analysis |
| [CodeQL Integration](docs/codeql.md) | Running CodeQL semantic analysis |
| [CLI Reference](docs/cli-reference.md) | Complete command-line options |
| [Examples](docs/examples.md) | Real-world usage examples |
| [Development](docs/development.md) | Contributing and development setup |

### Building the Docs

```bash
# Install MkDocs
pip install mkdocs mkdocs-material

# Serve locally
mkdocs serve

# Build static site
mkdocs build
```

## 🛠️ Development

```bash
# Setup development environment
make dev

# Run tests
make test

# Run all checks (lint, typecheck, test)
make check
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes and ensure tests pass (`make check`)
4. Commit and push to your branch
5. Open a Pull Request

See [Development Guide](docs/development.md) for detailed instructions.

## 🙏 Acknowledgments

- [GitHub API](https://docs.github.com/en/rest) for code search capabilities
- [Semgrep](https://semgrep.dev/) for static analysis
- [CodeQL](https://codeql.github.com/) for semantic analysis

---

<p align="center">
  Made with ❤️ for the security research community
</p>
