# Semgrep Integration

Scanipy can automatically clone and scan the top 10 repositories with [Semgrep](https://semgrep.dev/) for security vulnerabilities.

!!! note "Command Usage"
    If installed via `pip install scanipy-cli`, use `scanipy` command.
    If running from source, use `python scanipy.py` instead.

## Prerequisites

Install Semgrep before using this feature:

```bash
pip install semgrep
```

## Basic Usage

```bash
# Run with default Semgrep rules
scanipy --query "extractall" --run-semgrep
```

## Custom Rules

```bash
# Use custom Semgrep rules
scanipy --query "extractall" --run-semgrep --rules ./my_rules.yaml

# Use built-in tarslip rules
scanipy --query "extractall" --run-semgrep --rules ./tools/semgrep/rules/tarslip.yaml
```

## Semgrep Pro

If you have a Semgrep Pro license:

```bash
scanipy --query "extractall" --run-semgrep --pro
```

## Additional Semgrep Arguments

Pass additional arguments directly to Semgrep:

```bash
scanipy --query "extractall" --run-semgrep --semgrep-args "--severity ERROR --json"
```

## Managing Cloned Repositories

```bash
# Keep cloned repositories after analysis
scanipy --query "extractall" --run-semgrep --keep-cloned

# Specify a custom clone directory
scanipy --query "extractall" --run-semgrep --clone-dir ./repos

# Combine both
scanipy --query "extractall" --run-semgrep --keep-cloned --clone-dir ./repos
```

## Resuming Interrupted Analysis

When running Semgrep analysis on many repositories, you can use `--results-db` to save progress to a SQLite database. If the analysis is interrupted (Ctrl+C, network error, etc.), simply re-run the same command to resume from where you left off:

```bash
# Start analysis with database persistence
scanipy --query "extractall" --run-semgrep --results-db ./results.db

# If interrupted, just run the same command again - already analyzed repos will be skipped
scanipy --query "extractall" --run-semgrep --results-db ./results.db
# Output: "📂 Resuming session 1 - 5 repos already analyzed"
```

## Containerized Execution (Kubernetes)

Scanipy supports containerized execution using Kubernetes Jobs for parallel analysis across multiple repositories.

### Prerequisites

1. **Kubernetes cluster** (EKS, GKE, AKS, or local with k3d/kind)
2. **API service** running in the cluster
3. **Worker container image** built and available
4. **S3 bucket** for storing results (or S3-compatible storage)

### Basic Containerized Usage

```bash
# Run with containerized execution
scanipy --query "extractall" --run-semgrep \
  --container-mode \
  --api-url http://scanipy-api:8000 \
  --s3-bucket scanipy-results
```

### Container Mode Options

```bash
# Full container mode example
scanipy --query "extractall" --run-semgrep \
  --container-mode \
  --api-url http://scanipy-api:8000 \
  --s3-bucket scanipy-results \
  --k8s-namespace scanipy \
  --max-parallel-jobs 20 \
  --rules ./custom-rules.yaml \
  --pro
```

### Architecture

When using `--container-mode`:

1. CLI creates a scan session via API
2. API creates Kubernetes Jobs (one per repository)
3. Each Job runs a worker container that:
   - Clones the repository
   - Runs Semgrep analysis
   - Uploads results to S3
   - Reports status back to API
4. CLI polls API for completion and fetches results

### Deployment

See [Deployment Guide](deployment.md) for detailed EKS deployment instructions.

The database stores:

- Analysis sessions (query, timestamp, rules used)
- Results for each repository (success/failure, Semgrep output)

## Built-in Rules

Scanipy includes built-in security rules:

### Tarslip Rules

Detect path traversal vulnerabilities in archive extraction:

```bash
scanipy --query "extractall" --run-semgrep --rules ./tools/semgrep/rules/tarslip.yaml
```

## Semgrep Options Reference

| Option | Description |
|--------|-------------|
| `--run-semgrep` | Enable Semgrep analysis |
| `--rules` | Path to custom Semgrep rules |
| `--pro` | Use Semgrep Pro |
| `--semgrep-args` | Additional Semgrep CLI arguments |
| `--clone-dir` | Directory for cloned repos |
| `--keep-cloned` | Keep repos after analysis |
| `--results-db` | SQLite database for saving/resuming |
