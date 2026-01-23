# CodeQL Example Queries

This directory contains example CodeQL queries for finding security vulnerabilities in C/C++ repositories.

## Memory Corruption Queries

### `memory-corruption.ql`
Comprehensive query that detects multiple types of memory corruption vulnerabilities:
- Buffer overflows from unsafe string functions
- Use-after-free vulnerabilities
- Double-free vulnerabilities
- Null pointer dereferences
- Array access without bounds checking

**Usage:**
```bash
scanipy --query "malloc" --language c --run-codeql --codeql-query-suite tools/codeql/queries/memory-corruption.ql
```

### `buffer-overflow.ql`
Focused query for detecting buffer overflow vulnerabilities from unsafe string operations:
- `strcpy` → use `strncpy` or `strlcpy`
- `strcat` → use `strncat` or `strlcat`
- `sprintf` → use `snprintf`
- `vsprintf` → use `vsnprintf`
- `gets` → use `fgets`
- `scanf` with `%s` → use width specifier

**Usage:**
```bash
scanipy --query "strcpy" --language c --run-codeql --codeql-query-suite tools/codeql/queries/buffer-overflow.ql
```

### `use-after-free.ql`
Path-sensitive query for detecting use-after-free vulnerabilities where memory is accessed after being freed.

**CWE:** CWE-416 (Use After Free)

**Usage:**
```bash
scanipy --query "free" --language cpp --run-codeql --codeql-query-suite tools/codeql/queries/use-after-free.ql
```

### `double-free.ql`
Detects double-free vulnerabilities where the same memory is freed multiple times.

**CWE:** CWE-415 (Double Free)

**Usage:**
```bash
scanipy --query "malloc" --language cpp --run-codeql --codeql-query-suite tools/codeql/queries/double-free.ql
```

### `null-pointer-deref.ql`
Path-sensitive query for detecting null pointer dereferences after allocation without proper null checks.

**CWE:** CWE-476 (NULL Pointer Dereference)

**Usage:**
```bash
scanipy --query "malloc NULL" --language c --run-codeql --codeql-query-suite tools/codeql/queries/null-pointer-deref.ql
```

## Running Custom Queries

To use these queries with Scanipy:

1. **Single query file:**
   ```bash
   scanipy --query "your-search" --language cpp --run-codeql \
     --codeql-query-suite tools/codeql/queries/buffer-overflow.ql
   ```

2. **All queries in directory:**
   ```bash
   scanipy --query "your-search" --language cpp --run-codeql \
     --codeql-query-suite tools/codeql/queries/
   ```

3. **With resume capability:**
   ```bash
   scanipy --query "malloc" --language c --run-codeql \
     --codeql-query-suite tools/codeql/queries/memory-corruption.ql \
     --codeql-results-db memory_bugs.db \
     --codeql-resume
   ```

## Query Development

For more information on writing CodeQL queries:
- [CodeQL for C/C++](https://codeql.github.com/docs/codeql-language-guides/codeql-for-cpp/)
- [CodeQL Query Help](https://codeql.github.com/codeql-query-help/cpp/)
- [CodeQL Standard Library](https://codeql.github.com/codeql-standard-libraries/cpp/)

## Contributing

To add new queries:
1. Create a `.ql` file with proper metadata annotations
2. Include `@name`, `@description`, `@kind`, `@problem.severity`, and `@security-severity`
3. Tag with relevant CWE identifiers
4. Add usage examples to this README
5. Test on known vulnerable code samples
