# scanipy
A tool to scan open source code-bases for simple patterns

## Development Setup

After cloning the repository, run:

```bash
make dev
```

This will:
- Install dependencies
- Install git hooks (pre-commit testing)

## Running Tests

```bash
make test
```

With coverage:

```bash
make coverage
```

## Manual Hook Installation

If not using `make`, you can install hooks manually:

```bash
./scripts/setup-hooks.sh
```
