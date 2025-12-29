# Installation

## Prerequisites

- Python 3.12 or higher
- A GitHub Personal Access Token ([create one here](https://github.com/settings/tokens))
- (Optional) [Semgrep](https://semgrep.dev/docs/getting-started/) for security analysis
- (Optional) [CodeQL CLI](https://codeql.github.com/docs/codeql-cli/getting-started-with-the-codeql-cli/) for semantic security analysis

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
python scanipy.py --query "test" --github-token "your_token_here"
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

# Run Scanipy help
python scanipy.py --help

# Run tests (optional)
python -m pytest
```
