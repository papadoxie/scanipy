# Semgrep Integration

Scanipy can automatically clone and scan the top 10 repositories with [Semgrep](https://semgrep.dev/) for security vulnerabilities.

## Prerequisites

Install Semgrep before using this feature:

```bash
pip install semgrep
```

## Basic Usage

```bash
# Run with default Semgrep rules
python scanipy.py --query "extractall" --run-semgrep
```

## Custom Rules

```bash
# Use custom Semgrep rules
python scanipy.py --query "extractall" --run-semgrep --rules ./my_rules.yaml

# Use built-in tarslip rules
python scanipy.py --query "extractall" --run-semgrep --rules ./tools/semgrep/rules/tarslip.yaml
```

## Semgrep Pro

If you have a Semgrep Pro license:

```bash
python scanipy.py --query "extractall" --run-semgrep --pro
```

## Additional Semgrep Arguments

Pass additional arguments directly to Semgrep:

```bash
python scanipy.py --query "extractall" --run-semgrep --semgrep-args "--severity ERROR --json"
```

## Managing Cloned Repositories

```bash
# Keep cloned repositories after analysis
python scanipy.py --query "extractall" --run-semgrep --keep-cloned

# Specify a custom clone directory
python scanipy.py --query "extractall" --run-semgrep --clone-dir ./repos

# Combine both
python scanipy.py --query "extractall" --run-semgrep --keep-cloned --clone-dir ./repos
```

## Resuming Interrupted Analysis

When running Semgrep analysis on many repositories, you can use `--results-db` to save progress to a SQLite database. If the analysis is interrupted (Ctrl+C, network error, etc.), simply re-run the same command to resume from where you left off:

```bash
# Start analysis with database persistence
python scanipy.py --query "extractall" --run-semgrep --results-db ./results.db

# If interrupted, just run the same command again - already analyzed repos will be skipped
python scanipy.py --query "extractall" --run-semgrep --results-db ./results.db
# Output: "📂 Resuming session 1 - 5 repos already analyzed"
```

The database stores:

- Analysis sessions (query, timestamp, rules used)
- Results for each repository (success/failure, Semgrep output)

## Built-in Rules

Scanipy includes built-in security rules:

### Tarslip Rules

Detect path traversal vulnerabilities in archive extraction:

```bash
python scanipy.py --query "extractall" --run-semgrep --rules ./tools/semgrep/rules/tarslip.yaml
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
