# 📡 Scanipy

A powerful command-line tool to scan open source code-bases on GitHub for security patterns and vulnerabilities. Scanipy searches GitHub repositories for specific code patterns and optionally runs [Semgrep](https://semgrep.dev/) or [CodeQL](https://codeql.github.com/) analysis on discovered code.

[![Tests](https://github.com/papadoxie/scanipy/actions/workflows/tests.yml/badge.svg)](https://github.com/papadoxie/scanipy/actions/workflows/tests.yml)
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen.svg)](https://github.com/papadoxie/scanipy)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

## 🎯 Features

- **Smart Code Search**: Search GitHub for specific code patterns across millions of repositories
- **Tiered Star Search**: Prioritize popular, well-maintained repositories by searching in star tiers (100k+, 50k-100k, 20k-50k, 10k-20k, 5k-10k, 1k-5k)
- **Keyword Filtering**: Filter results by keywords found in file contents
- **Multiple Sort Options**: Sort by stars (popularity) or recently updated
- **Semgrep Integration**: Automatically clone and scan top repositories with Semgrep for security vulnerabilities
- **CodeQL Integration**: Run CodeQL analysis for deep semantic security scanning
- **Custom Rules**: Use built-in security rules or provide your own Semgrep rules
- **Colorful Output**: Beautiful terminal output with progress indicators

## ⚡ Quick Start

```bash
# Search for repositories using extractall (potential path traversal)
python scanipy.py --query "extractall" --language python

# Search and run Semgrep analysis
python scanipy.py --query "extractall" --language python --run-semgrep

# Search and run CodeQL analysis
python scanipy.py --query "extractall" --language python --run-codeql
```

## 📚 Documentation

- [Installation](installation.md) - How to install Scanipy and its dependencies
- [Usage Guide](usage.md) - Basic and advanced usage examples
- [Semgrep Integration](semgrep.md) - Running Semgrep security analysis
- [CodeQL Integration](codeql.md) - Running CodeQL semantic analysis
- [CLI Reference](cli-reference.md) - Complete command-line options reference
- [Examples](examples.md) - Real-world usage examples
- [Development](development.md) - Contributing and development setup

## 🤝 Contributing

We welcome contributions! See the [Development Guide](development.md) for setup instructions and guidelines.

---

<p align="center">
  Made with ❤️ for the security research community
</p>
