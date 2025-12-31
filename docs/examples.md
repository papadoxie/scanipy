# Examples

Real-world usage examples for security research and code analysis.

!!! note "Command Usage"
    If installed via `pip install scanipy-cli`, use `scanipy` command.
    If running from source, use `python scanipy.py` instead.

## Security Research

### Command Injection

Find potential command injection vulnerabilities:

```bash
scanipy --query "os.system" --language python \
  --keywords "user,input,request" --run-semgrep
```

### SQL Injection

Find potential SQL injection:

```bash
scanipy --query "execute(" --language python \
  --keywords "format,user,%s" --run-semgrep
```

### Unsafe Deserialization

Find unsafe pickle usage:

```bash
scanipy --query "pickle.loads" --language python --run-semgrep
```

### Path Traversal (Tarslip)

Find path traversal vulnerabilities in archive extraction:

```bash
scanipy --query "extractall" --language python \
  --run-semgrep --rules ./tools/semgrep/rules/tarslip.yaml
```

With CodeQL for deeper analysis:

```bash
scanipy --query "extractall" --language python --run-codeql \
  --codeql-queries "codeql/python-queries:Security/CWE-022/TarSlip.ql"
```

### Hardcoded Secrets

Find potential hardcoded credentials:

```bash
scanipy --query "password =" --language python \
  --keywords "secret,api_key,token" --run-semgrep
```

## Code Pattern Analysis

### Deprecated API Usage

Find deprecated urllib2 usage:

```bash
scanipy --query "urllib2" --language python
```

### Library Usage

Find specific library usage in popular repos:

```bash
scanipy --query "import tensorflow" --language python \
  --search-strategy tiered
```

### Recently Updated

Find recently updated repos using a pattern:

```bash
scanipy --query "FastAPI" --language python --sort-by updated
```

## Advanced Filtering

### Exclude Organizations

Search but exclude specific organizations:

```bash
scanipy --query "eval(" \
  --additional-params "stars:>1000 -org:microsoft -org:google"
```

### High-Star Repos Only

Focus on very popular repositories:

```bash
scanipy --query "subprocess.Popen" --language python \
  --additional-params "stars:>10000"
```

### Combined Filters

```bash
scanipy \
  --query "subprocess" \
  --language python \
  --keywords "shell=True,user" \
  --pages 10 \
  --search-strategy tiered \
  --run-semgrep
```

## Workflow Examples

### Research Workflow

1. **Search and save results:**
   ```bash
   scanipy --query "extractall" --language python \
     --output tarslip_repos.json
   ```

2. **Review results, then run analysis:**
   ```bash
   scanipy --query "extractall" \
     --input-file tarslip_repos.json \
     --run-semgrep --rules ./tools/semgrep/rules/tarslip.yaml
   ```

3. **Run CodeQL for deeper analysis:**
   ```bash
   scanipy --query "extractall" --language python \
     --input-file tarslip_repos.json \
     --run-codeql --codeql-output-dir ./tarslip_sarif
   ```

### Long-Running Analysis

For large-scale analysis with resume capability:

```bash
# Start analysis (can be interrupted)
scanipy --query "eval(" --language python \
  --pages 10 \
  --run-semgrep \
  --results-db ./eval_analysis.db \
  --keep-cloned \
  --clone-dir ./eval_repos

# Resume if interrupted
scanipy --query "eval(" --language python \
  --pages 10 \
  --run-semgrep \
  --results-db ./eval_analysis.db \
  --keep-cloned \
  --clone-dir ./eval_repos
```

### Multi-Tool Analysis

Run both Semgrep and CodeQL on the same repositories:

```bash
# First, search and run Semgrep
scanipy --query "extractall" --language python \
  --run-semgrep \
  --keep-cloned \
  --clone-dir ./repos \
  --output repos.json

# Then run CodeQL on the same repos
scanipy --query "extractall" --language python \
  --input-file repos.json \
  --run-codeql \
  --clone-dir ./repos \
  --codeql-output-dir ./sarif_results
```

## Language-Specific Examples

### JavaScript/TypeScript

```bash
scanipy --query "eval(" --language javascript --run-codeql
```

### Java

```bash
scanipy --query "Runtime.exec" --language java --run-codeql
```

### Go

```bash
python scanipy.py --query "os/exec" --language go --run-codeql
```

### C/C++

```bash
python scanipy.py --query "strcpy" --language c --run-codeql \
  --codeql-queries "cpp-security-extended"
```

## Resuming Interrupted Analysis

Both Semgrep and CodeQL support resuming interrupted analysis. This is useful for large scans that may be interrupted.

### Resume Semgrep Analysis

```bash
# Start analysis with database tracking
scanipy --query "SQL injection" --language python \
  --run-semgrep --results-db sql_injection.db

# If interrupted (Ctrl+C, network error, etc.)
# Resume from where you left off
scanipy --query "SQL injection" --language python \
  --run-semgrep --results-db sql_injection.db --resume
```

### Resume CodeQL Analysis

```bash
# Start CodeQL analysis with database tracking
scanipy --query "path traversal" --language python \
  --run-codeql --codeql-results-db path_analysis.db

# Resume interrupted analysis
scanipy --query "path traversal" --language python \
  --run-codeql --codeql-results-db path_analysis.db --codeql-resume
```

### Large-Scale Analysis Workflow

For analyzing hundreds of repositories:

```bash
# Day 1: Start large scan (100+ repos)
scanipy --query "unsafe deserialization" --language java \
  --pages 10 --run-codeql --codeql-results-db deserialization_scan.db

# Analysis interrupted after 40 repositories...

# Day 2: Resume (skips first 40, continues with remaining)
scanipy --query "unsafe deserialization" --language java \
  --pages 10 --run-codeql --codeql-results-db deserialization_scan.db \
  --codeql-resume

# Completed: All 100 repositories analyzed
```

### Key Points

- **Session Matching**: Resume works by matching query, language, and analysis parameters
- **Automatic Skipping**: Already-analyzed repositories are automatically skipped
- **Incremental Saves**: Results are saved after each repository
- **Crash Recovery**: Analysis survives Ctrl+C, network errors, or system crashes
