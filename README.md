# 📡 Scanipy

A powerful command-line tool to scan open source code-bases on GitHub for security patterns and vulnerabilities. Scanipy searches GitHub repositories for specific code patterns and optionally runs [Semgrep](https://semgrep.dev/) or [CodeQL](https://codeql.github.com/) analysis on discovered code.

[![Tests](https://github.com/papadoxie/scanipy/actions/workflows/tests.yml/badge.svg)](https://github.com/papadoxie/scanipy/actions/workflows/tests.yml)
[![Coverage](https://img.shields.io/badge/coverage-99%25-brightgreen.svg)](https://github.com/papadoxie/scanipy)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![PyPI](https://img.shields.io/pypi/v/scanipy-cli.svg)](https://pypi.org/project/scanipy-cli/)

## 🎯 Features

- **Smart Code Search**: Search GitHub for specific code patterns across millions of repositories
- **Tiered Star Search**: Prioritize popular, well-maintained repositories by searching in star tiers
- **Keyword Filtering**: Filter results by keywords found in file contents
- **Semgrep Integration**: Automatically clone and scan repositories with Semgrep
- **CodeQL Integration**: Run CodeQL analysis for deep semantic security scanning
- **Containerized Execution**: Run parallel Semgrep scans using Kubernetes Jobs (EKS-ready)
- **Resume Capability**: Resume interrupted analysis from where it left off (Semgrep & CodeQL)
- **Custom Rules**: Use built-in security rules or provide your own
- **PostgreSQL Support**: Use PostgreSQL for production deployments alongside SQLite


## 🏆 Vulnerabilities Found

This section showcases real-world vulnerabilities discovered using Scanipy:

| CVE ID | Project | Vulnerability Type | Description | Reporter
|--------|---------|--------------------|-------------|---------|
| CVE-2025-61765 | [python-socketio](https://github.com/miguelgrinberg/python-socketio) | Unsafe Pickle Deserialization | Arbitrary Python code execution (RCE) through malicious pickle deserialization in certain multi-server deployments | [locus-x64](https://github.com/locus-x64)

> **Found a vulnerability using Scanipy?** We'd love to hear about it! Open an issue or PR to add your finding to this list.

## ⚡ Quick Start

```bash
# Install from PyPI
pip install scanipy-cli

# Or clone and setup from source
git clone https://github.com/papadoxie/scanipy.git
cd scanipy
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Set GitHub token
export GITHUB_TOKEN="your_token_here"

# Search for code patterns (if installed via pip)
scanipy --query "extractall" --language python

# Or run from source
python scanipy.py --query "extractall" --language python

# Run Semgrep analysis (local mode)
scanipy --query "extractall" --language python --run-semgrep

# Run Semgrep analysis (containerized mode - requires API service)
scanipy --query "extractall" --language python --run-semgrep \
  --container-mode \
  --api-url http://scanipy-api:8000 \
  --s3-bucket scanipy-results

# Run CodeQL analysis
scanipy --query "extractall" --language python --run-codeql
```

## 📚 Documentation

Full documentation is available in the [`docs/`](docs/) directory:

| Document | Description |
|----------|-------------|
| [Installation](docs/installation.md) | Setup instructions and prerequisites |
| [Usage Guide](docs/usage.md) | Basic and advanced usage |
| [Semgrep Integration](docs/semgrep.md) | Running Semgrep security analysis |
| [CodeQL Integration](docs/codeql.md) | Running CodeQL semantic analysis |
| [Deployment Guide](docs/deployment.md) | Deploying containerized execution to EKS |
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