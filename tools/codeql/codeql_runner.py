"""Utilities for running CodeQL analysis on repositories."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Mapping of common languages to CodeQL language identifiers
LANGUAGE_MAP: dict[str, str] = {
    "python": "python",
    "javascript": "javascript",
    "typescript": "javascript",  # TypeScript uses JavaScript extractor
    "java": "java",
    "kotlin": "java",  # Kotlin uses Java extractor
    "c": "cpp",
    "cpp": "cpp",
    "c++": "cpp",
    "csharp": "csharp",
    "c#": "csharp",
    "go": "go",
    "golang": "go",
    "ruby": "ruby",
    "swift": "swift",
}

# Default queries for each language
DEFAULT_QUERY_SUITES: dict[str, str] = {
    "python": "python-security-and-quality",
    "javascript": "javascript-security-and-quality",
    "java": "java-security-and-quality",
    "cpp": "cpp-security-and-quality",
    "csharp": "csharp-security-and-quality",
    "go": "go-security-and-quality",
    "ruby": "ruby-security-and-quality",
    "swift": "swift-security-and-quality",
}


def _check_command_exists(cmd: str) -> bool:
    """Return True when *cmd* can be found in PATH."""
    try:
        subprocess.run(["which", cmd], check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        return False


def _clone_repository(repo_url: str, clone_path: str, colors: Any) -> bool:
    """Clone *repo_url* into *clone_path* and return True on success."""
    try:
        subprocess.run(
            ["git", "clone", "--depth=1", repo_url, clone_path],
            check=True,
            capture_output=True,
        )
        return True
    except subprocess.CalledProcessError as exc:
        print(f"{colors.ERROR}❌ Failed to clone {repo_url}: {exc}{colors.RESET}")
        return False


def _get_codeql_language(language: str) -> str | None:
    """Map a language name to CodeQL language identifier."""
    return LANGUAGE_MAP.get(language.lower())


def _create_codeql_database(
    repo_path: str,
    db_path: str,
    language: str,
    colors: Any,
) -> tuple[bool, str]:
    """Create a CodeQL database for the repository.

    Args:
        repo_path: Path to the cloned repository
        db_path: Path where the CodeQL database will be created
        language: CodeQL language identifier
        colors: Color configuration object

    Returns:
        Tuple of (success, output/error message)
    """
    try:
        cmd = [
            "codeql",
            "database",
            "create",
            db_path,
            f"--language={language}",
            f"--source-root={repo_path}",
            "--overwrite",
        ]

        print(f"{colors.INFO}🔨 Creating CodeQL database: {' '.join(cmd)}{colors.RESET}")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return True, result.stdout + result.stderr
    except subprocess.CalledProcessError as exc:
        return False, f"Error creating database: {exc}\nOutput: {exc.stdout}\nError: {exc.stderr}"


def _run_codeql_analysis(
    db_path: str,
    language: str,
    colors: Any,
    query_suite: str | None = None,
    output_format: str = "sarif-latest",
) -> tuple[bool, str]:
    """Run CodeQL analysis on a database.

    Args:
        db_path: Path to the CodeQL database
        language: CodeQL language identifier
        colors: Color configuration object
        query_suite: Custom query suite or path to queries
        output_format: Output format (sarif-latest, csv, etc.)

    Returns:
        Tuple of (success, output/error message)
    """
    try:
        # Determine which queries to run
        if query_suite:
            queries = query_suite
        else:
            queries = DEFAULT_QUERY_SUITES.get(language, f"{language}-security-and-quality")

        results_file = Path(db_path).parent / "results.sarif"

        cmd = [
            "codeql",
            "database",
            "analyze",
            db_path,
            queries,
            f"--format={output_format}",
            f"--output={results_file}",
        ]

        print(f"{colors.INFO}🔍 Running CodeQL analysis: {' '.join(cmd)}{colors.RESET}")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)

        # Read and return the results
        if results_file.exists():
            sarif_content = results_file.read_text()
            return True, sarif_content
        return True, result.stdout

    except subprocess.CalledProcessError as exc:
        return False, f"Error running analysis: {exc}\nOutput: {exc.stdout}\nError: {exc.stderr}"


def analyze_repositories_with_codeql(
    repo_list: Iterable[dict[str, Any]],
    colors: Any,
    language: str = "",
    clone_dir: str | None = None,
    keep_cloned: bool = False,
    query_suite: str | None = None,
    output_format: str = "sarif-latest",
    output_dir: str | None = None,
) -> list[dict[str, Any]]:
    """Clone repositories and run CodeQL analysis on the first ten entries.

    Args:
        repo_list: Iterable of repository dictionaries
        colors: Color configuration object
        language: Programming language for analysis (required for CodeQL)
        clone_dir: Directory to clone repos into (default: temp dir)
        keep_cloned: Whether to keep cloned repos after analysis
        query_suite: Custom query suite or path to queries
        output_format: Output format for results
        output_dir: Directory to save SARIF results (default: ./codeql_results)

    Returns:
        List of analysis result dictionaries
    """
    if not _check_command_exists("codeql"):
        print(f"{colors.ERROR}❌ Error: codeql is not installed on your system.{colors.RESET}")
        print(
            f"{colors.INFO}💡 To install CodeQL, follow instructions at "
            f"https://codeql.github.com/docs/codeql-cli/getting-started-with-the-codeql-cli/"
            f"{colors.RESET}"
        )
        return []

    if not _check_command_exists("git"):
        print(f"{colors.ERROR}❌ Error: git is not installed on your system.{colors.RESET}")
        return []

    # Validate and map language
    codeql_language = _get_codeql_language(language) if language else None
    if not codeql_language:
        print(f"{colors.ERROR}❌ Error: Language is required for CodeQL analysis.{colors.RESET}")
        print(
            f"{colors.INFO}💡 Supported languages: {', '.join(sorted(set(LANGUAGE_MAP.values())))}"
            f"{colors.RESET}"
        )
        return []

    using_temp_dir = clone_dir is None
    actual_clone_dir: str
    if using_temp_dir:
        actual_clone_dir = tempfile.mkdtemp(prefix="scanipy_codeql_")
        print(
            f"{colors.INFO}📁 Created temporary directory "
            f"for cloning: {actual_clone_dir}{colors.RESET}"
        )
    else:
        assert clone_dir is not None
        actual_clone_dir = clone_dir
        Path(actual_clone_dir).mkdir(parents=True, exist_ok=True)
        print(f"{colors.INFO}📁 Using directory for cloning: {actual_clone_dir}{colors.RESET}")

    repos_to_analyze = list(repo_list)[:10]

    print(f"{colors.HEADER}{'─' * 80}{colors.RESET}")
    print(
        f"{colors.INFO}🚀 Running CodeQL analysis on "
        f"{len(repos_to_analyze)} repositories...{colors.RESET}"
    )
    print(f"{colors.INFO}📝 Language: {codeql_language}{colors.RESET}")
    if query_suite:
        print(f"{colors.INFO}📝 Query suite: {query_suite}{colors.RESET}")
    print(f"{colors.HEADER}{'─' * 80}{colors.RESET}")

    results: list[dict[str, Any]] = []

    for index, repo in enumerate(repos_to_analyze, start=1):
        repo_url = repo.get("url")
        if not repo_url:
            continue

        repo_name = repo.get("name", f"repo_{index}")
        repo_dir = Path(actual_clone_dir) / repo_name.replace("/", "_")
        clone_path = str(repo_dir)
        db_path = str(repo_dir / "codeql-db")

        print(
            f"\n{colors.INFO}[{index}/{len(repos_to_analyze)}] Analyzing "
            f"{colors.REPO_NAME}{repo_name}{colors.RESET}"
        )
        print(
            f"{colors.PROGRESS}📥 Cloning repository: {repo_url} to {clone_path}...{colors.RESET}"
        )

        if _clone_repository(repo_url, clone_path, colors):
            print(f"{colors.SUCCESS}✅ Cloning successful{colors.RESET}")

            # Create CodeQL database
            print(f"{colors.PROGRESS}🔨 Creating CodeQL database...{colors.RESET}")
            db_success, db_output = _create_codeql_database(
                clone_path, db_path, codeql_language, colors
            )

            if db_success:
                print(f"{colors.SUCCESS}✅ Database created{colors.RESET}")

                # Run analysis
                print(f"{colors.PROGRESS}🔍 Running CodeQL analysis...{colors.RESET}")
                success, output = _run_codeql_analysis(
                    db_path, codeql_language, colors, query_suite, output_format
                )

                if success:
                    print(f"{colors.SUCCESS}✅ CodeQL analysis complete{colors.RESET}")
                    print(f"\n{colors.HEADER}--- CodeQL results for {repo_name} ---{colors.RESET}")
                    # Print summary instead of full SARIF
                    _print_sarif_summary(output, colors)
                    print(f"{colors.HEADER}{'─' * 80}{colors.RESET}")

                    # Save SARIF results to file
                    sarif_path = _save_sarif_results(output, repo_name, colors, output_dir)
                    result = {
                        "repo": repo_name,
                        "success": success,
                        "output": output,
                        "sarif_file": sarif_path,
                    }
                else:
                    print(f"{colors.ERROR}❌ CodeQL analysis failed{colors.RESET}")
                    print(f"{colors.ERROR}{output}{colors.RESET}")
                    result = {"repo": repo_name, "success": success, "output": output}
            else:
                print(f"{colors.ERROR}❌ Failed to create CodeQL database{colors.RESET}")
                print(f"{colors.ERROR}{db_output}{colors.RESET}")
                result = {"repo": repo_name, "success": False, "output": db_output}

            results.append(result)
        else:
            result = {
                "repo": repo_name,
                "success": False,
                "output": "Failed to clone repository",
            }
            results.append(result)

    if using_temp_dir and not keep_cloned:
        print(f"{colors.INFO}🧹 Cleaning up temporary directory...{colors.RESET}")
        try:
            shutil.rmtree(actual_clone_dir)
            print(f"{colors.SUCCESS}✅ Cleanup successful{colors.RESET}")
        except Exception as exc:
            print(f"{colors.ERROR}❌ Failed to clean up: {exc}{colors.RESET}")
    elif keep_cloned:
        print(f"{colors.INFO}💾 Repositories have been kept at: {actual_clone_dir}{colors.RESET}")

    print(f"\n{colors.HEADER}{'─' * 80}{colors.RESET}")
    print(f"{colors.INFO}📊 CodeQL Analysis Summary:{colors.RESET}")
    successes = sum(1 for result in results if result.get("success"))
    total = len(results)
    failed = total - successes
    print(f"{colors.INFO}✓ Successfully analyzed: {successes}/{total} repositories{colors.RESET}")
    print(f"{colors.INFO}✗ Failed to analyze: {failed}/{total} repositories{colors.RESET}")
    print(f"{colors.HEADER}{'─' * 80}{colors.RESET}")

    return results


def _save_sarif_results(
    sarif_output: str,
    repo_name: str,
    colors: Any,
    output_dir: str | None = None,
) -> str:
    """Save SARIF results to a file.

    Args:
        sarif_output: The SARIF JSON output
        repo_name: Name of the repository
        colors: Color configuration object
        output_dir: Directory to save results (default: ./codeql_results)

    Returns:
        Path to the saved SARIF file
    """
    # Determine output directory
    if output_dir is None:
        output_dir = "./codeql_results"

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Create filename with timestamp
    timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
    safe_repo_name = repo_name.replace("/", "_").replace("\\", "_")
    filename = f"{safe_repo_name}_{timestamp}.sarif"
    filepath = output_path / filename

    # Write SARIF content
    filepath.write_text(sarif_output)
    print(f"{colors.INFO}💾 SARIF results saved to: {filepath}{colors.RESET}")

    return str(filepath)


def _print_sarif_summary(sarif_output: str, colors: Any) -> None:
    """Print a summary of SARIF results."""
    try:
        sarif = json.loads(sarif_output)
        runs = sarif.get("runs", [])
        total_results = 0

        for run in runs:
            results = run.get("results", [])
            total_results += len(results)

            for result in results[:10]:  # Show first 10 findings
                rule_id = result.get("ruleId", "unknown")
                message = result.get("message", {}).get("text", "No message")
                level = result.get("level", "warning")

                # Get location info
                locations = result.get("locations", [])
                location_str = ""
                if locations:
                    loc = locations[0].get("physicalLocation", {})
                    artifact = loc.get("artifactLocation", {}).get("uri", "")
                    region = loc.get("region", {})
                    line = region.get("startLine", "?")
                    location_str = f" at {artifact}:{line}"

                level_color = colors.ERROR if level == "error" else colors.WARNING
                print(f"  {level_color}[{level.upper()}]{colors.RESET} {rule_id}{location_str}")
                print(f"    {message[:100]}{'...' if len(message) > 100 else ''}")

            if len(results) > 10:
                print(f"  ... and {len(results) - 10} more findings")

        print(f"\n  {colors.INFO}Total findings: {total_results}{colors.RESET}")

    except json.JSONDecodeError:
        # Not valid JSON, just print raw output
        print(sarif_output[:2000])
        if len(sarif_output) > 2000:
            print("... (output truncated)")
