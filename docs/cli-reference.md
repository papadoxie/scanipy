# CLI Reference

Complete command-line options reference for Scanipy.

!!! note "Command Usage"
    If installed via `pip install scanipy-cli`, use `scanipy` command.
    If running from source, use `python scanipy.py` instead.

## Synopsis

```bash
scanipy --query QUERY [OPTIONS]
```

## Required Arguments

| Option | Short | Description |
|--------|-------|-------------|
| `--query` | `-q` | Code pattern to search for |

## Search Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--language` | `-l` | Programming language filter | None |
| `--extension` | `-e` | File extension filter | None |
| `--keywords` | `-k` | Comma-separated keywords to filter by | None |
| `--additional-params` | | Extra GitHub search parameters | None |
| `--pages` | `-p` | Max pages to retrieve (max 10) | 5 |
| `--search-strategy` | `-s` | Search strategy: `tiered` or `greedy` | `tiered` |
| `--sort-by` | | Sort by: `stars` or `updated` | `stars` |

## Authentication

| Option | Description | Default |
|--------|-------------|---------|
| `--github-token` | GitHub Personal Access Token | `$GITHUB_TOKEN` |

## Output Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--output` | `-o` | Output JSON file path | `repos.json` |
| `--input-file` | `-i` | Load repos from JSON file (skip search) | None |
| `--verbose` | `-v` | Enable verbose output | False |

## Semgrep Options

| Option | Description | Default |
|--------|-------------|---------|
| `--run-semgrep` | Run Semgrep on top 10 repos | False |
| `--semgrep-args` | Additional Semgrep arguments | None |
| `--pro` | Use Semgrep Pro | False |
| `--rules` | Custom Semgrep rules path | None |
| `--results-db` | SQLite database for saving/resuming analysis | None |
| `--resume` | Resume analysis from previous session | False |
| `--container-mode` | Enable containerized execution via API service | False |
| `--api-url` | API service URL for containerized execution | None |
| `--s3-bucket` | S3 bucket for storing results (container mode) | None |
| `--k8s-namespace` | Kubernetes namespace for jobs | `default` |
| `--max-parallel-jobs` | Maximum parallel Kubernetes jobs | 10 |

## CodeQL Options

| Option | Description | Default |
|--------|-------------|---------|
| `--run-codeql` | Run CodeQL on top 10 repos | False |
| `--codeql-queries` | CodeQL query suite or path | Default suite |
| `--codeql-format` | CodeQL output format (`sarif-latest`, `csv`, `text`) | `sarif-latest` |
| `--codeql-output-dir` | Directory to save SARIF results | `./codeql_results` |
| `--codeql-results-db` | SQLite database for storing analysis results | None |
| `--codeql-resume` | Resume previous CodeQL analysis | False |

## Shared Analysis Options

These options apply to both Semgrep and CodeQL analysis:

| Option | Description | Default |
|--------|-------------|---------|
| `--clone-dir` | Directory for cloned repos | Temp dir |
| `--keep-cloned` | Keep repos after analysis | False |

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GITHUB_TOKEN` | GitHub Personal Access Token |

## Examples

### Basic Search

```bash
scanipy --query "pickle.loads" --language python
```

### With Semgrep Analysis (Local Mode)

```bash
scanipy --query "extractall" --language python --run-semgrep \
  --rules ./tools/semgrep/rules/tarslip.yaml
```

### With Semgrep Analysis (Containerized Mode)

```bash
scanipy --query "extractall" --language python --run-semgrep \
  --container-mode \
  --api-url http://scanipy-api:8000 \
  --s3-bucket scanipy-results \
  --k8s-namespace scanipy \
  --max-parallel-jobs 20
```

### With CodeQL Analysis

```bash
scanipy --query "extractall" --language python --run-codeql \
  --codeql-output-dir ./results
```

### Full Example

```bash
scanipy \
  --query "subprocess" \
  --language python \
  --keywords "shell=True,user" \
  --pages 10 \
  --search-strategy tiered \
  --run-semgrep \
  --keep-cloned \
  --clone-dir ./repos \
  --results-db ./analysis.db \
  --verbose
```

## Exit Codes

| Code | Description |
|------|-------------|
| 0 | Success |
| 1 | Error (missing token, invalid arguments, etc.) |
| 2 | Argument parsing error |
