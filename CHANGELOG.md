# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] - 2025-12-29

First official release of Scanipy! 🎉

### 🚀 Features

- **GitHub Code Search**: Search GitHub for specific code patterns across millions of repositories
- **Tiered Star Search**: Prioritize popular repositories by searching in star tiers (100k+, 50k-100k, 20k-50k, 10k-20k, 5k-10k, 1k-5k)
- **Keyword Filtering**: Filter results by keywords found in file contents
- **Multiple Sort Options**: Sort by stars (popularity) or recently updated
- **Semgrep Integration**: Automatically clone and scan top repositories with Semgrep for security vulnerabilities
- **CodeQL Integration**: Run CodeQL analysis for deep semantic security scanning
- **Custom Rules**: Use built-in security rules or provide your own Semgrep rules
- **Input/Output Files**: Save search results to JSON and continue analysis later with `--input-file`
- **Resume Analysis**: Save progress to SQLite database with `--results-db` and resume interrupted analysis
- **SARIF Output**: Save CodeQL results to SARIF files with `--codeql-output-dir`

### 📚 Documentation

- Comprehensive README with quick start guide
- MkDocs documentation site with:
  - Installation guide
  - Usage guide
  - Semgrep integration docs
  - CodeQL integration docs
  - CLI reference
  - Examples for security research

### 🧪 Testing

- 333 comprehensive unit tests
- 100% code coverage enforced via CI
- Pre-commit hooks for automated testing

### ⚙️ CI/CD

- GitHub Actions workflow for test enforcement
- Automated release workflow with changelog generation
- Ruff linting and Mypy type checking
