# CodeQL Integration

Scanipy can run [CodeQL](https://codeql.github.com/) semantic analysis on the top 10 repositories. CodeQL provides deep semantic security scanning using GitHub's code analysis engine.

!!! note "Command Usage"
    If installed via `pip install scanipy-cli`, use `scanipy` command.
    If running from source, use `python scanipy.py` instead.

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
scanipy --query "extractall" --language python --run-codeql
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
scanipy --query "extractall" --language python --run-codeql \
  --codeql-queries "python-security-extended"

# Run a specific query for faster analysis
scanipy --query "extractall" --language python --run-codeql \
  --codeql-queries "codeql/python-queries:Security/CWE-022/TarSlip.ql"
```

## Output Formats

```bash
# SARIF format (default)
scanipy --query "extractall" --language python --run-codeql \
  --codeql-format sarif-latest

# CSV format
scanipy --query "extractall" --language python --run-codeql \
  --codeql-format csv

# Text format
scanipy --query "extractall" --language python --run-codeql \
  --codeql-format text
```

## Saving SARIF Results

Save SARIF results to files for later analysis:

```bash
# Save to default directory (./codeql_results)
scanipy --query "extractall" --language python --run-codeql

# Save to custom directory
scanipy --query "extractall" --language python --run-codeql \
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
scanipy --query "extractall" --language python --run-codeql \
  --keep-cloned --clone-dir ./repos
```

## Resume Capability

CodeQL analysis can be interrupted and resumed from where it left off. This is useful for long-running analyses that may be interrupted by network issues, Ctrl+C, or system restarts.

### Basic Resume

```bash
# Start analysis with a results database
scanipy --query "extractall" --language python --run-codeql \
  --codeql-results-db codeql_analysis.db

# If interrupted, resume from the same session
scanipy --query "extractall" --language python --run-codeql \
  --codeql-results-db codeql_analysis.db --codeql-resume
```

### How It Works

1. **Session Tracking**: Each analysis run creates a session tracked by query, language, and query suite
2. **Incremental Saves**: Results are saved to SQLite after analyzing each repository
3. **Smart Resume**: Already-analyzed repositories are automatically skipped
4. **Survives Interruptions**: Analysis can survive Ctrl+C, network errors, or system crashes

### Example Workflow

```bash
# Day 1: Start analyzing 100 repositories
scanipy --query "path traversal" --language python --run-codeql \
  --codeql-results-db path_traversal.db --pages 10

# Analysis interrupted after 40 repos...
# Ctrl+C

# Day 2: Resume analysis (skips first 40 repos)
scanipy --query "path traversal" --language python --run-codeql \
  --codeql-results-db path_traversal.db --codeql-resume

# Continue where you left off - remaining 60 repos analyzed
```

### Session Matching

Resume works by matching:
- **Query**: The search query used
- **Language**: The programming language
- **Query Suite**: The CodeQL query suite (if specified)

If any of these change, a new session is created:

```bash
# Creates session 1
scanipy --query "pickle.loads" --language python --run-codeql \
  --codeql-results-db analysis.db

# Creates session 2 (different query)
scanipy --query "eval" --language python --run-codeql \
  --codeql-results-db analysis.db

# Creates session 3 (different query suite)
scanipy --query "pickle.loads" --language python --run-codeql \
  --codeql-results-db analysis.db --codeql-queries "security-extended"
```

### Viewing Results

The database stores:
- Repository names and URLs
- Success/failure status
- Error messages (for failures)
- SARIF file paths (for successes)
- Analysis timestamps

You can query the database directly using SQLite:

```bash
sqlite3 codeql_analysis.db "SELECT repo_name, success FROM codeql_results"
```

### Best Practices

1. **Use Descriptive Database Names**: Name databases after the vulnerability or pattern you're searching for
   ```bash
   --codeql-results-db sql_injection_scan.db
   ```

2. **Always Use Resume Flag**: When continuing analysis, always specify `--codeql-resume`

3. **Match Parameters**: Ensure query, language, and query suite match the original analysis

4. **Check Session Info**: The tool prints session information showing how many repos were already analyzed

## Performance Tips

### Use Specific Queries

Running the full security suite can take a long time. For faster analysis, use specific queries:

```bash
# Full suite (slow)
scanipy --query "extractall" --language python --run-codeql

# Specific query (fast)
scanipy --query "extractall" --language python --run-codeql \
  --codeql-queries "codeql/python-queries:Security/CWE-022/TarSlip.ql"
```

### Limit Pages

Reduce the number of repositories to analyze:

```bash
scanipy --query "extractall" --language python --run-codeql --pages 1
```

## CodeQL Options Reference

| Option | Description | Default |
|--------|-------------|---------|
| `--run-codeql` | Enable CodeQL analysis | False |
| `--codeql-queries` | Query suite or path | Default suite |
| `--codeql-format` | Output format (sarif-latest, csv, text) | `sarif-latest` |
| `--codeql-output-dir` | Directory to save SARIF results | `./codeql_results` |
| `--codeql-results-db` | Path to SQLite database for results | None |
| `--codeql-resume` | Resume from previous session | False |
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
