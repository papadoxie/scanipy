# Installation

## Prerequisites

- Python 3.12 or higher
- A GitHub Personal Access Token ([create one here](https://github.com/settings/tokens))
- (Optional) [Semgrep](https://semgrep.dev/docs/getting-started/) for security analysis
- (Optional) [CodeQL CLI](https://codeql.github.com/docs/codeql-cli/getting-started-with-the-codeql-cli/) for semantic security analysis
- (Optional) For containerized execution:
  - Kubernetes cluster (EKS, GKE, AKS, or local with k3d/kind)
  - Docker for building container images
  - AWS S3 bucket (or S3-compatible storage)
  - PostgreSQL database (for production deployments)

## Install from PyPI (Recommended)

```bash
pip install scanipy-cli
```

This installs the `scanipy` command globally.

## Install from Source

```bash
# Clone the repository
git clone https://github.com/papadoxie/scanipy.git
cd scanipy

# Create virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Or install with optional container dependencies
pip install -r requirements.txt
pip install psycopg2-binary boto3 kubernetes fastapi pytest-asyncio
```

## Optional Dependencies

Scanipy supports optional dependencies for advanced features:

### Containerized Execution

For running Semgrep analysis in Kubernetes:

```bash
pip install psycopg2-binary  # PostgreSQL support
pip install boto3            # AWS S3 support
pip install kubernetes       # Kubernetes client
pip install fastapi          # API service
pip install pytest-asyncio  # Async test support (dev)
```

Or install all optional dependencies at once:

```bash
pip install scanipy-cli[container]
```

### Development Dependencies

For contributing to Scanipy:

```bash
pip install scanipy-cli[dev]
```

Or install everything:

```bash
pip install scanipy-cli[all]
```

## Set up GitHub Token

Scanipy requires a GitHub Personal Access Token to search repositories.

### Option 1: Environment Variable

```bash
export GITHUB_TOKEN="your_github_token_here"
```

### Option 2: Create a .env File

```bash
echo "GITHUB_TOKEN=your_github_token_here" > .env
```

### Option 3: Command Line Argument

```bash
scanipy --query "test" --github-token "your_token_here"
```

## Installing Semgrep (Optional)

Semgrep is used for static analysis of cloned repositories.

```bash
# Using pip
pip install semgrep

# Or using Homebrew (macOS)
brew install semgrep
```

For more installation options, see the [Semgrep documentation](https://semgrep.dev/docs/getting-started/).

## Installing CodeQL (Optional)

CodeQL provides deep semantic security analysis.

1. Download the CodeQL CLI from [GitHub Releases](https://github.com/github/codeql-action/releases)
2. Extract and add to your PATH:

```bash
# Download and extract
wget https://github.com/github/codeql-cli-binaries/releases/latest/download/codeql-linux64.zip
unzip codeql-linux64.zip

# Add to PATH
export PATH="$PWD/codeql:$PATH"

# Verify installation
codeql --version
```

For detailed instructions, see the [CodeQL CLI documentation](https://codeql.github.com/docs/codeql-cli/getting-started-with-the-codeql-cli/).

## Verify Installation

```bash
# Check Python version
python --version  # Should be 3.12+

# Run Scanipy help (if installed via pip)
scanipy --help

# Or from source
python scanipy.py --help

# Run tests (optional, from source only)
python -m pytest
```
