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

When running Semgrep analysis on many repositories, you can use `--results-db` to save progress to a database. Scanipy supports both SQLite (for local development) and PostgreSQL (for production). If the analysis is interrupted (Ctrl+C, network error, etc.), simply re-run the same command to resume from where you left off:

```bash
# Start analysis with SQLite database persistence
scanipy --query "extractall" --run-semgrep --results-db ./results.db

# If interrupted, just run the same command again - already analyzed repos will be skipped
scanipy --query "extractall" --run-semgrep --results-db ./results.db
# Output: "📂 Resuming session 1 - 5 repos already analyzed"

# Or use --resume flag explicitly
scanipy --query "extractall" --run-semgrep --results-db ./results.db --resume
```

### Database Support

- **SQLite**: Default for local development. Use `--results-db ./path/to/db.sqlite`
- **PostgreSQL**: For production deployments. Configure via API service environment variables (see [Deployment Guide](deployment.md))

The database stores:
- Analysis sessions (query, timestamp, rules used, status)
- Results for each repository (success/failure, Semgrep output, S3 path, K8s job ID)

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

1. **CLI** creates a scan session via API service
2. **API Service** creates Kubernetes Jobs (one per repository) up to `--max-parallel-jobs` limit
3. **Worker Containers** (one per Job) execute in parallel:
   - Clone the repository
   - Run Semgrep analysis
   - Upload results to S3
   - Report status back to API service
4. **CLI** polls API service for completion and fetches final results

### Benefits of Containerized Mode

- **Parallel Execution**: Multiple repositories scanned simultaneously
- **Scalability**: Leverage Kubernetes cluster resources
- **Isolation**: Each scan runs in its own container
- **Resilience**: Failed jobs don't affect others
- **Production-Ready**: Designed for EKS deployment

### Deployment

See [Deployment Guide](deployment.md) for detailed EKS deployment instructions, including:
- Building and pushing container images
- Setting up Kubernetes resources (RBAC, ConfigMaps, Secrets)
- Configuring IAM roles for S3 access
- Exposing the API service
- Monitoring and troubleshooting

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
| `--clone-dir` | Directory for cloned repos (local mode only) |
| `--keep-cloned` | Keep repos after analysis (local mode only) |
| `--results-db` | Database path for saving/resuming (SQLite) |
| `--resume` | Resume analysis from previous session |
| `--container-mode` | Enable containerized execution via API service |
| `--api-url` | API service URL (required for container mode) |
| `--s3-bucket` | S3 bucket for storing results (required for container mode) |
| `--k8s-namespace` | Kubernetes namespace for jobs (default: `default`) |
| `--max-parallel-jobs` | Maximum parallel Kubernetes jobs (default: 10) |
