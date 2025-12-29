# Usage Guide

## Basic Search

Search for a code pattern across GitHub repositories:

```bash
# Search for a code pattern
python scanipy.py --query "pickle.loads"

# Search with a specific language
python scanipy.py --query "eval(" --language python
```

## Language & Extension Filtering

```bash
# Search in Python files only
python scanipy.py --query "subprocess.call" --language python

# Search in specific file extensions
python scanipy.py --query "os.system" --extension ".py"

# Combine both
python scanipy.py --query "exec(" --language python --extension ".py"
```

## Keyword Filtering

Filter results to only include files containing specific keywords:

```bash
# Find extractall usage that also mentions path or directory
python scanipy.py --query "extractall" --keywords "path,directory,zip"
```

## Search Strategies

Scanipy offers two search strategies:

| Strategy | Description | Best For |
|----------|-------------|----------|
| `tiered` (default) | Searches repositories in star tiers (100k+, 50k-100k, 20k-50k, etc.) | Finding popular, well-maintained code |
| `greedy` | Standard GitHub search, faster but may miss high-star repos | Quick searches, less popular patterns |

```bash
# Use tiered search (default) - prioritizes popular repos
python scanipy.py --query "extractall" --search-strategy tiered

# Use greedy search - faster but less targeted
python scanipy.py --query "extractall" --search-strategy greedy
```

## Sorting Results

```bash
# Sort by stars (default)
python scanipy.py --query "extractall" --sort-by stars

# Sort by recently updated
python scanipy.py --query "extractall" --sort-by updated
```

## Pagination

Control how many pages of results to retrieve:

```bash
# Get more results (max 10 pages)
python scanipy.py --query "extractall" --pages 10

# Quick search with fewer results
python scanipy.py --query "extractall" --pages 2
```

## Output Options

```bash
# Save results to a custom file
python scanipy.py --query "extractall" --output my_results.json

# Enable verbose output
python scanipy.py --query "extractall" --verbose
```

## Using Saved Results

Scanipy automatically saves search results to `repos.json`. You can continue analysis later without re-running the search:

```bash
# First, run a search (results saved to repos.json)
python scanipy.py --query "memcpy" --language c --output repos.json

# Later, continue with analysis using saved results
python scanipy.py --query "memcpy" --input-file repos.json --run-semgrep

# Use a custom input file
python scanipy.py --query "extractall" -i my_repos.json --run-semgrep
```

## Advanced GitHub Search

Use additional GitHub search qualifiers:

```bash
# Search with GitHub search qualifiers
python scanipy.py --query "eval(" --additional-params "stars:>1000 -org:microsoft"

# Combine multiple filters
python scanipy.py \
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
