# Examples

Real-world usage examples for security research and code analysis.

## Security Research

### Command Injection

Find potential command injection vulnerabilities:

```bash
python scanipy.py --query "os.system" --language python \
  --keywords "user,input,request" --run-semgrep
```

### SQL Injection

Find potential SQL injection:

```bash
python scanipy.py --query "execute(" --language python \
  --keywords "format,user,%s" --run-semgrep
```

### Unsafe Deserialization

Find unsafe pickle usage:

```bash
python scanipy.py --query "pickle.loads" --language python --run-semgrep
```

### Path Traversal (Tarslip)

Find path traversal vulnerabilities in archive extraction:

```bash
python scanipy.py --query "extractall" --language python \
  --run-semgrep --rules ./tools/semgrep/rules/tarslip.yaml
```

With CodeQL for deeper analysis:

```bash
python scanipy.py --query "extractall" --language python --run-codeql \
  --codeql-queries "codeql/python-queries:Security/CWE-022/TarSlip.ql"
```

### Hardcoded Secrets

Find potential hardcoded credentials:

```bash
python scanipy.py --query "password =" --language python \
  --keywords "secret,api_key,token" --run-semgrep
```

## Code Pattern Analysis

### Deprecated API Usage

Find deprecated urllib2 usage:

```bash
python scanipy.py --query "urllib2" --language python
```

### Library Usage

Find specific library usage in popular repos:

```bash
python scanipy.py --query "import tensorflow" --language python \
  --search-strategy tiered
```

### Recently Updated

Find recently updated repos using a pattern:

```bash
python scanipy.py --query "FastAPI" --language python --sort-by updated
```

## Advanced Filtering

### Exclude Organizations

Search but exclude specific organizations:

```bash
python scanipy.py --query "eval(" \
  --additional-params "stars:>1000 -org:microsoft -org:google"
```

### High-Star Repos Only

Focus on very popular repositories:

```bash
python scanipy.py --query "subprocess.Popen" --language python \
  --additional-params "stars:>10000"
```

### Combined Filters

```bash
python scanipy.py \
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
   python scanipy.py --query "extractall" --language python \
     --output tarslip_repos.json
   ```

2. **Review results, then run analysis:**
   ```bash
   python scanipy.py --query "extractall" \
     --input-file tarslip_repos.json \
     --run-semgrep --rules ./tools/semgrep/rules/tarslip.yaml
   ```

3. **Run CodeQL for deeper analysis:**
   ```bash
   python scanipy.py --query "extractall" --language python \
     --input-file tarslip_repos.json \
     --run-codeql --codeql-output-dir ./tarslip_sarif
   ```

### Long-Running Analysis

For large-scale analysis with resume capability:

```bash
# Start analysis (can be interrupted)
python scanipy.py --query "eval(" --language python \
  --pages 10 \
  --run-semgrep \
  --results-db ./eval_analysis.db \
  --keep-cloned \
  --clone-dir ./eval_repos

# Resume if interrupted
python scanipy.py --query "eval(" --language python \
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
python scanipy.py --query "extractall" --language python \
  --run-semgrep \
  --keep-cloned \
  --clone-dir ./repos \
  --output repos.json

# Then run CodeQL on the same repos
python scanipy.py --query "extractall" --language python \
  --input-file repos.json \
  --run-codeql \
  --clone-dir ./repos \
  --codeql-output-dir ./sarif_results
```

## Language-Specific Examples

### JavaScript/TypeScript

```bash
python scanipy.py --query "eval(" --language javascript --run-codeql
```

### Java

```bash
python scanipy.py --query "Runtime.exec" --language java --run-codeql
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
