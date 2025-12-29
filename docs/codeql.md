# CodeQL Integration

Scanipy can run [CodeQL](https://codeql.github.com/) semantic analysis on the top 10 repositories. CodeQL provides deep semantic security scanning using GitHub's code analysis engine.

## Prerequisites

Install the CodeQL CLI before using this feature:

1. Download from [GitHub Releases](https://github.com/github/codeql-cli-binaries/releases)
2. Extract and add to your PATH

```bash
# Download and extract (Linux)
wget https://github.com/github/codeql-cli-binaries/releases/latest/download/codeql-linux64.zip
unzip codeql-linux64.zip

# Add to PATH
export PATH="$PWD/codeql:$PATH"

# Verify installation
codeql --version
```

For detailed instructions, see the [CodeQL CLI documentation](https://codeql.github.com/docs/codeql-cli/getting-started-with-the-codeql-cli/).

## Basic Usage

CodeQL requires a language to be specified:

```bash
python scanipy.py --query "extractall" --language python --run-codeql
```

## Supported Languages

| Language | CodeQL Identifier |
|----------|-------------------|
| Python | `python` |
| JavaScript | `javascript` |
| TypeScript | `javascript` (uses JS extractor) |
| Java | `java` |
| Kotlin | `java` (uses Java extractor) |
| C | `cpp` |
| C++ | `cpp` |
| C# | `csharp` |
| Go | `go` |
| Ruby | `ruby` |
| Swift | `swift` |

## Custom Query Suites

```bash
# Use a different query suite
python scanipy.py --query "extractall" --language python --run-codeql \
  --codeql-queries "python-security-extended"

# Run a specific query for faster analysis
python scanipy.py --query "extractall" --language python --run-codeql \
  --codeql-queries "codeql/python-queries:Security/CWE-022/TarSlip.ql"
```

## Output Formats

```bash
# SARIF format (default)
python scanipy.py --query "extractall" --language python --run-codeql \
  --codeql-format sarif-latest

# CSV format
python scanipy.py --query "extractall" --language python --run-codeql \
  --codeql-format csv

# Text format
python scanipy.py --query "extractall" --language python --run-codeql \
  --codeql-format text
```

## Saving SARIF Results

Save SARIF results to files for later analysis:

```bash
# Save to default directory (./codeql_results)
python scanipy.py --query "extractall" --language python --run-codeql

# Save to custom directory
python scanipy.py --query "extractall" --language python --run-codeql \
  --codeql-output-dir ./my_sarif_results
```

SARIF files are saved with timestamped filenames:
```
my_sarif_results/
├── owner_repo1_20251229_120000.sarif
├── owner_repo2_20251229_120100.sarif
└── ...
```

## Managing Cloned Repositories

```bash
# Keep cloned repositories after analysis
python scanipy.py --query "extractall" --language python --run-codeql \
  --keep-cloned --clone-dir ./repos
```

## Performance Tips

### Use Specific Queries

Running the full security suite can take a long time. For faster analysis, use specific queries:

```bash
# Full suite (slow)
python scanipy.py --query "extractall" --language python --run-codeql

# Specific query (fast)
python scanipy.py --query "extractall" --language python --run-codeql \
  --codeql-queries "codeql/python-queries:Security/CWE-022/TarSlip.ql"
```

### Limit Pages

Reduce the number of repositories to analyze:

```bash
python scanipy.py --query "extractall" --language python --run-codeql --pages 1
```

## CodeQL Options Reference

| Option | Description | Default |
|--------|-------------|---------|
| `--run-codeql` | Enable CodeQL analysis | False |
| `--codeql-queries` | Query suite or path | Default suite |
| `--codeql-format` | Output format (sarif-latest, csv, text) | `sarif-latest` |
| `--codeql-output-dir` | Directory to save SARIF results | `./codeql_results` |
| `--clone-dir` | Directory for cloned repos | Temp dir |
| `--keep-cloned` | Keep repos after analysis | False |

## Understanding Results

CodeQL results are displayed in a summary format:

```
--- CodeQL results for owner/repo ---
  [ERROR] py/tarslip at src/file.py:42
    This file extraction depends on a potentially untrusted source.

  Total findings: 1
```

SARIF files contain detailed information including:

- Rule descriptions and severity
- Code locations (file, line, column)
- Code flow paths
- Remediation suggestions
