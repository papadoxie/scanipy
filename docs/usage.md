# Usage Guide

!!! note "Command Usage"
    If installed via `pip install scanipy-cli`, use `scanipy` command.
    If running from source, use `python scanipy.py` instead.

## Basic Search

Search for a code pattern across GitHub repositories:

```bash
# Search for a code pattern
scanipy --query "pickle.loads"

# Search with a specific language
scanipy --query "eval(" --language python
```

## Language & Extension Filtering

```bash
# Search in Python files only
scanipy --query "subprocess.call" --language python

# Search in specific file extensions
scanipy --query "os.system" --extension ".py"

# Combine both
scanipy --query "exec(" --language python --extension ".py"
```

## Keyword Filtering

Filter results to only include files containing specific keywords:

```bash
# Find extractall usage that also mentions path or directory
scanipy --query "extractall" --keywords "path,directory,zip"
```

## Search Strategies

Scanipy offers two search strategies:

| Strategy | Description | Best For |
|----------|-------------|----------|
| `tiered` (default) | Searches repositories in star tiers (100k+, 50k-100k, 20k-50k, etc.) | Finding popular, well-maintained code |
| `greedy` | Standard GitHub search, faster but may miss high-star repos | Quick searches, less popular patterns |

```bash
# Use tiered search (default) - prioritizes popular repos
scanipy --query "extractall" --search-strategy tiered

# Use greedy search - faster but less targeted
scanipy --query "extractall" --search-strategy greedy
```

## Sorting Results

```bash
# Sort by stars (default)
scanipy --query "extractall" --sort-by stars

# Sort by recently updated
scanipy --query "extractall" --sort-by updated
```

## Pagination

Control how many pages of results to retrieve:

```bash
# Get more results (max 10 pages)
scanipy --query "extractall" --pages 10

# Quick search with fewer results
scanipy --query "extractall" --pages 2
```

## Output Options

```bash
# Save results to a custom file
scanipy --query "extractall" --output my_results.json

# Enable verbose output
scanipy --query "extractall" --verbose
```

## Using Saved Results

Scanipy automatically saves search results to `repos.json`. You can continue analysis later without re-running the search:

```bash
# First, run a search (results saved to repos.json)
scanipy --query "memcpy" --language c --output repos.json

# Later, continue with analysis using saved results
scanipy --query "memcpy" --input-file repos.json --run-semgrep

# Use a custom input file
scanipy --query "extractall" -i my_repos.json --run-semgrep
```

## Advanced GitHub Search

Use additional GitHub search qualifiers:

```bash
# Search with GitHub search qualifiers
scanipy --query "eval(" --additional-params "stars:>1000 -org:microsoft"

# Combine multiple filters
scanipy \
  --query "subprocess" \
  --language python \
  --keywords "shell=True,user" \
  --pages 10 \
  --search-strategy tiered
```

## Next Steps

- [Semgrep Integration](semgrep.md) - Run security analysis with Semgrep
- [CodeQL Integration](codeql.md) - Run semantic analysis with CodeQL
- [CLI Reference](cli-reference.md) - Complete command-line options
