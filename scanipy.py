#!/usr/bin/env python3
"""
Scanipy - A tool to scan open source code-bases for security patterns.

This module provides the CLI interface for searching GitHub repositories
and running Semgrep analysis on discovered code.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from colorama import init
from dotenv import load_dotenv

from integrations.github import SearchStrategy, SortOrder, search_repositories

# Load environment variables from .env file
load_dotenv()
from models import (
    DEFAULT_MAX_PAGES,
    DEFAULT_OUTPUT_FILE,
    MAX_DISPLAY_REPOS,
    MAX_FILES_PREVIEW,
    CodeQLConfig,
    Colors,
    SearchConfig,
    SemgrepConfig,
)
from tools.codeql.codeql_runner import analyze_repositories_with_codeql
from tools.semgrep.semgrep_runner import analyze_repositories_with_semgrep

# Initialize colorama for cross-platform color support
init(autoreset=True)

# =============================================================================
# Display Functions
# =============================================================================


class Display:
    """Handles all terminal output and formatting."""

    @staticmethod
    def print_banner() -> None:
        """Print a colorful banner for the tool."""
        banner = f"""
{Colors.HEADER}╔══════════════════════════════════════════════════════════════╗
║                          📡 SCANIPY                          ║
║              Code Pattern Scanner for GitHub                 ║
╚══════════════════════════════════════════════════════════════╝{Colors.RESET}
"""
        print(banner)

    @staticmethod
    def print_search_info(
        config: SearchConfig,
        strategy: SearchStrategy | None = None,
        sort_order: SortOrder | None = None,
    ) -> None:
        """Print search parameters in a formatted way."""
        print(f"{Colors.INFO}🔍 Search Parameters:{Colors.RESET}")
        print(
            f"   {Colors.INFO}•{Colors.RESET} Query: {Colors.WARNING}'{config.query}'{Colors.RESET}"
        )
        if config.language:
            print(
                f"   {Colors.INFO}•{Colors.RESET} Language: "
                f"{Colors.SUCCESS}{config.language}{Colors.RESET}"
            )
        if config.extension:
            print(
                f"   {Colors.INFO}•{Colors.RESET} Extension: "
                f"{Colors.SUCCESS}{config.extension}{Colors.RESET}"
            )
        if config.keywords:
            kw_str = ", ".join(config.keywords)
            print(
                f"   {Colors.INFO}•{Colors.RESET} Keywords: {Colors.WARNING}{kw_str}{Colors.RESET}"
            )
        print(
            f"   {Colors.INFO}•{Colors.RESET} Max Pages: "
            f"{Colors.WARNING}{config.max_pages}{Colors.RESET}"
        )
        if strategy:
            strategy_desc = (
                "tiered by stars" if strategy == SearchStrategy.TIERED_STARS else "greedy"
            )
            print(
                f"   {Colors.INFO}•{Colors.RESET} Strategy: "
                f"{Colors.SUCCESS}{strategy_desc}{Colors.RESET}"
            )
        if sort_order:
            sort_desc = "most stars" if sort_order == SortOrder.STARS else "recently updated"
            print(
                f"   {Colors.INFO}•{Colors.RESET} Sort by: "
                f"{Colors.SUCCESS}{sort_desc}{Colors.RESET}"
            )
        print()

    @staticmethod
    def format_star_count(stars: int | str) -> str:
        """Format star count with appropriate color and formatting."""
        if stars == "N/A" or not isinstance(stars, int):
            return f"{Colors.WARNING}N/A{Colors.RESET}"
        if stars >= 10000:
            return f"{Colors.SUCCESS}⭐ {stars:,}{Colors.RESET}"
        if stars >= 1000:
            return f"{Colors.STARS}⭐ {stars:,}{Colors.RESET}"
        return f"{Colors.WARNING}⭐ {stars}{Colors.RESET}"

    @staticmethod
    def format_updated_at(updated_at: str) -> str:
        """Format the updated_at timestamp for display."""
        if not updated_at:
            return ""
        # ISO format: 2024-12-23T10:30:00Z -> 2024-12-23
        try:
            date_part = updated_at.split("T")[0]
            return f"{Colors.INFO}🕐 Updated: {date_part}{Colors.RESET}"
        except (IndexError, AttributeError):
            return ""

    @staticmethod
    def print_repository(
        index: int, repo: dict[str, Any], query: str, sort_order: SortOrder | None = None
    ) -> None:
        """Print a single repository with colorful formatting."""
        # Repository header
        print(f"{Colors.HEADER}{'─' * 80}{Colors.RESET}")
        print(
            f"{Colors.INFO}{index:2d}.{Colors.RESET} "
            f"{Colors.REPO_NAME}{repo['name']}{Colors.RESET} "
            f"{Display.format_star_count(repo.get('stars', 'N/A'))}"
        )

        # Show updated date if sorting by updated
        if sort_order == SortOrder.UPDATED and repo.get("updated_at"):
            print(f"    {Display.format_updated_at(repo['updated_at'])}")

        # Description
        if repo.get("description"):
            desc = repo["description"]
            if len(desc) > 100:
                desc = desc[:97] + "..."
            print(f"    {Colors.DESCRIPTION}📝 {desc}{Colors.RESET}")

        # File count
        file_count = len(repo["files"])
        if file_count > 0:
            plural = "s" if file_count != 1 else ""
            print(
                f"    {Colors.FILES}📁 {file_count} file{plural} containing '{query}'{Colors.RESET}"
            )

            # Show files with keyword information
            Display._print_file_list(repo["files"])

        # URL
        if repo.get("url"):
            print(f"    {Colors.URL}🔗 {repo['url']}{Colors.RESET}")

        print()

    @staticmethod
    def _print_file_list(files: list[dict[str, Any]]) -> None:
        """Print the list of files with keyword match information."""
        for file in files[:MAX_FILES_PREVIEW]:
            file_line = f"    {Colors.FILES}├─{Colors.RESET} {file['path']}"

            # Add keyword match information (only if keywords were searched)
            keyword_match = file.get("keyword_match")
            if keyword_match is True:
                keywords_str = ", ".join(file.get("keywords_found", []))
                file_line += f" {Colors.SUCCESS}[Keywords: {keywords_str}]{Colors.RESET}"
            elif keyword_match is False:
                file_line += f" {Colors.WARNING}[No keywords matched]{Colors.RESET}"
            # keyword_match is None means keywords weren't searched - don't show anything

            print(file_line)

        if len(files) > MAX_FILES_PREVIEW:
            remaining = len(files) - MAX_FILES_PREVIEW
            plural = "s" if remaining != 1 else ""
            print(
                f"    {Colors.FILES}└─{Colors.RESET} {Colors.WARNING}"
                f"... and {remaining} more file{plural}{Colors.RESET}"
            )

    @staticmethod
    def print_results(
        repos: list[dict[str, Any]], query: str, sort_order: SortOrder | None = None
    ) -> None:
        """Print the list of repositories."""
        if not repos:
            print(f"{Colors.WARNING}📭 No repositories found matching your criteria.{Colors.RESET}")
            return

        if sort_order == SortOrder.UPDATED:
            print(f"{Colors.SUCCESS}🎯 TOP REPOSITORIES BY RECENTLY UPDATED:{Colors.RESET}")
        else:
            print(f"{Colors.SUCCESS}🎯 TOP REPOSITORIES BY STARS:{Colors.RESET}")
        for i, repo in enumerate(repos[:MAX_DISPLAY_REPOS], 1):
            Display.print_repository(i, repo, query, sort_order)

    @staticmethod
    def print_no_results_hint(has_keywords: bool) -> None:
        """Print helpful hints when no results are found."""
        if has_keywords:
            print(
                f"{Colors.INFO}💡 Try with fewer or different keywords, "
                f"or search without keyword filtering.{Colors.RESET}"
            )


# =============================================================================
# CLI Argument Parsing
# =============================================================================

EPILOG = """
Examples:

    # Search for a pattern (uses tiered star search by default)
    scanipy --query "extractall"

    # Search for a specific language
    scanipy --query "pickle.loads" --language python

    # Search with keyword filtering
    scanipy --query "extractall" --keywords "path,directory,zip" --language python

    # Search with a higher page limit
    scanipy --query "pickle.loads" --pages 10

    # Use greedy search (faster but may miss high-star repos)
    scanipy --query "extractall" --search-strategy greedy

    # Search in specific file types
    scanipy --query "os.system" --language python --extension ".py"

    # Search with additional filters
    scanipy --query "subprocess.call" --additional-params "stars:>100"

    # Run Semgrep on top repositories
    scanipy --query "extractall" --run-semgrep

    # Run Semgrep with custom rules
    scanipy --query "extractall" --run-semgrep --rules ./my_rules.yaml

    # Continue analysis from saved results (skip search)
    scanipy --query "extractall" --input-file repos.json --run-semgrep
"""


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Search for open source repositories containing "
            "specific code patterns and sort by stars."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=EPILOG,
    )

    # Search query parameters
    search_group = parser.add_argument_group("Search Options")
    search_group.add_argument(
        "--query",
        "-q",
        required=True,
        help='Code pattern to search for (e.g., "extractall")',
    )
    search_group.add_argument(
        "--language",
        "-l",
        default="",
        help="Programming language to search in (e.g., python)",
    )
    search_group.add_argument(
        "--extension",
        "-e",
        default="",
        help='File extension to search in (e.g., ".py", ".ipynb")',
    )
    search_group.add_argument(
        "--keywords",
        "-k",
        default="",
        help='Comma-separated keywords to look for in files (e.g., "path,directory,zip")',
    )
    search_group.add_argument(
        "--additional-params",
        default="",
        help='Additional search parameters (e.g., "stars:>100 -org:microsoft")',
    )
    search_group.add_argument(
        "--pages",
        "-p",
        type=int,
        default=DEFAULT_MAX_PAGES,
        help=(
            f"Maximum number of pages to retrieve "
            f"(default: {DEFAULT_MAX_PAGES}, max 10 pages = 1000 results)"
        ),
    )
    search_group.add_argument(
        "--search-strategy",
        "-s",
        choices=["tiered", "greedy"],
        default="tiered",
        help=(
            "Search strategy: 'tiered' searches by star ranges (10k+, 1k-10k, etc.) "
            "to prioritize popular repos; 'greedy' is faster but may miss high-star "
            "repos (default: tiered)"
        ),
    )
    search_group.add_argument(
        "--sort-by",
        choices=["stars", "updated"],
        default="stars",
        help=(
            "Sort results by: 'stars' (most starred first) or 'updated' "
            "(most recently updated first) (default: stars)"
        ),
    )

    # GitHub API authentication
    auth_group = parser.add_argument_group("Authentication")
    auth_group.add_argument(
        "--github-token",
        help="GitHub personal access token (also can be set via GITHUB_TOKEN env variable)",
    )

    # Output options
    output_group = parser.add_argument_group("Output Options")
    output_group.add_argument(
        "--output",
        "-o",
        default=DEFAULT_OUTPUT_FILE,
        help=f"Output JSON file path (default: {DEFAULT_OUTPUT_FILE})",
    )
    output_group.add_argument(
        "--input-file",
        "-i",
        default=None,
        help="Load repositories from a JSON file instead of searching (for continuing analysis)",
    )
    output_group.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )

    # Semgrep options
    semgrep_group = parser.add_argument_group("Semgrep Analysis")
    semgrep_group.add_argument(
        "--run-semgrep",
        action="store_true",
        help="Run Semgrep analysis on the top 10 repositories",
    )
    semgrep_group.add_argument(
        "--semgrep-args",
        default="",
        help='Additional arguments to pass to Semgrep (e.g., "--json --verbose")',
    )
    semgrep_group.add_argument(
        "--pro",
        action="store_true",
        help="Use Semgrep with the --pro flag",
    )
    semgrep_group.add_argument(
        "--rules",
        default=None,
        help="Path to custom Semgrep rules file or directory (YAML format)",
    )
    semgrep_group.add_argument(
        "--clone-dir",
        default=None,
        help="Directory to clone repositories into (default: temporary directory)",
    )
    semgrep_group.add_argument(
        "--keep-cloned",
        action="store_true",
        help="Keep cloned repositories after analysis",
    )
    semgrep_group.add_argument(
        "--results-db",
        default=None,
        help="Path to SQLite database for storing Semgrep results (enables resume)",
    )
    semgrep_group.add_argument(
        "--resume",
        action="store_true",
        help="Resume analysis from previous session (requires --results-db)",
    )
    semgrep_group.add_argument(
        "--api-url",
        default=None,
        help="API service URL for containerized execution (e.g., http://localhost:8000)",
    )
    semgrep_group.add_argument(
        "--container-mode",
        action="store_true",
        help="Enable containerized execution using Kubernetes Jobs",
    )
    semgrep_group.add_argument(
        "--s3-bucket",
        default=None,
        help="S3 bucket for storing analysis results (required for container mode)",
    )
    semgrep_group.add_argument(
        "--k8s-namespace",
        default="default",
        help="Kubernetes namespace for jobs (default: default)",
    )
    semgrep_group.add_argument(
        "--max-parallel-jobs",
        type=int,
        default=10,
        help="Maximum number of parallel jobs (default: 10)",
    )
    semgrep_group.add_argument(
        "--max-wait-time",
        type=int,
        default=3600,
        help="Maximum time to wait for analysis completion in seconds (default: 3600)",
    )
    semgrep_group.add_argument(
        "--poll-interval",
        type=int,
        default=10,
        help="Interval between status polls in seconds (default: 10)",
    )

    # CodeQL options
    codeql_group = parser.add_argument_group("CodeQL Analysis")
    codeql_group.add_argument(
        "--run-codeql",
        action="store_true",
        help="Run CodeQL analysis on the top 10 repositories",
    )
    codeql_group.add_argument(
        "--codeql-queries",
        default=None,
        help="Custom CodeQL query suite or path to queries",
    )
    codeql_group.add_argument(
        "--codeql-format",
        default="sarif-latest",
        choices=["sarif-latest", "csv", "text"],
        help="Output format for CodeQL results (default: sarif-latest)",
    )
    codeql_group.add_argument(
        "--codeql-output-dir",
        default=None,
        help="Directory to save SARIF results (default: ./codeql_results)",
    )
    codeql_group.add_argument(
        "--codeql-results-db",
        default=None,
        help="Path to SQLite database for storing analysis results (enables resume)",
    )
    codeql_group.add_argument(
        "--codeql-resume",
        action="store_true",
        help="Resume previous CodeQL analysis from database (requires --codeql-results-db)",
    )

    return parser


def parse_keywords(keywords_str: str) -> list[str]:
    """Parse comma-separated keywords string into a list."""
    if not keywords_str:
        return []
    return [kw.strip() for kw in keywords_str.split(",") if kw.strip()]


def build_configs_from_args(
    args: argparse.Namespace,
) -> tuple[SearchConfig, SemgrepConfig, CodeQLConfig, str | None, SearchStrategy, SortOrder]:
    """
    Build configuration objects from parsed arguments.

    Returns:
        Tuple of (SearchConfig, SemgrepConfig, CodeQLConfig, github_token,
        search_strategy, sort_order)
    """
    search_config = SearchConfig(
        query=args.query,
        language=args.language,
        extension=args.extension,
        keywords=parse_keywords(args.keywords),
        additional_params=args.additional_params,
        max_pages=args.pages,
    )

    semgrep_config = SemgrepConfig(
        enabled=args.run_semgrep,
        args=args.semgrep_args,
        rules_path=args.rules,
        clone_dir=args.clone_dir,
        keep_cloned=args.keep_cloned,
        use_pro=args.pro,
        db_path=args.results_db,
        resume=args.resume,
        api_url=args.api_url,
        container_mode=args.container_mode,
        s3_bucket=args.s3_bucket,
        k8s_namespace=args.k8s_namespace,
        max_parallel_jobs=args.max_parallel_jobs,
        max_wait_time=args.max_wait_time,
        poll_interval=args.poll_interval,
    )

    codeql_config = CodeQLConfig(
        enabled=args.run_codeql,
        query_suite=args.codeql_queries,
        clone_dir=args.clone_dir,
        keep_cloned=args.keep_cloned,
        output_format=args.codeql_format,
        output_dir=args.codeql_output_dir,
        db_path=args.codeql_results_db,
        resume=args.codeql_resume,
    )

    # Resolve GitHub token
    github_token = args.github_token or os.getenv("GITHUB_TOKEN")

    # Resolve search strategy
    strategy_map = {
        "tiered": SearchStrategy.TIERED_STARS,
        "greedy": SearchStrategy.GREEDY,
    }
    search_strategy = strategy_map[args.search_strategy]

    # Resolve sort order
    sort_map = {
        "stars": SortOrder.STARS,
        "updated": SortOrder.UPDATED,
    }
    sort_order = sort_map[args.sort_by]

    return search_config, semgrep_config, codeql_config, github_token, search_strategy, sort_order


# =============================================================================
# Core Application Logic
# =============================================================================


def run_semgrep_analysis(
    repos: list[dict[str, Any]],
    config: SemgrepConfig,
    query: str = "",
) -> None:
    """
    Run Semgrep analysis on the provided repositories.

    Args:
        repos: List of repository dictionaries
        config: Semgrep configuration
        query: The search query (for session tracking)
    """
    # Check if container mode is enabled
    if config.container_mode:
        if not config.api_url:
            print(
                f"{Colors.ERROR}❌ Error: --api-url is required when using "
                f"--container-mode{Colors.RESET}"
            )
            return

        if not config.s3_bucket:
            print(
                f"{Colors.ERROR}❌ Error: --s3-bucket is required when using "
                f"--container-mode{Colors.RESET}"
            )
            print(
                f"{Colors.INFO}💡 Container mode requires an S3 bucket to store "
                f"analysis results.{Colors.RESET}"
            )
            return

        # Use API service for containerized execution
        _run_semgrep_via_api(repos, config, query)
    else:
        # Use local execution (existing behavior)
        analyze_repositories_with_semgrep(
            repo_list=repos,
            colors=Colors,
            semgrep_args=config.args,
            clone_dir=config.clone_dir,
            keep_cloned=config.keep_cloned,
            rules_path=config.rules_path,
            use_pro=config.use_pro,
            db_path=config.db_path,
            resume=config.resume,
            query=query,
        )


def _run_semgrep_via_api(
    repos: list[dict[str, Any]],
    config: SemgrepConfig,
    query: str = "",
) -> None:
    """Run Semgrep analysis via API service (containerized mode).

    Args:
        repos: List of repository dictionaries
        config: Semgrep configuration
        query: The search query
    """
    try:
        import time  # noqa: PLC0415

        import requests  # noqa: PLC0415
    except ImportError:
        print(
            f"{Colors.ERROR}❌ Error: requests library is required for "
            f"container mode.{Colors.RESET}"
        )
        print(f"{Colors.INFO}💡 Install with: pip install requests{Colors.RESET}")
        return

    assert config.api_url is not None

    api_base = config.api_url.rstrip("/")
    session_id: int | None = None

    print(f"{Colors.INFO}🚀 Creating scan session via API...{Colors.RESET}")

    # Create scan session
    try:
        response = requests.post(
            f"{api_base}/api/v1/scans",
            json={
                "query": query,
                "rules_path": config.rules_path,
                "use_pro": config.use_pro,
            },
            timeout=30,
        )
        response.raise_for_status()
        session_data = response.json()
        session_id = session_data["session_id"]
        print(f"{Colors.SUCCESS}✅ Created session {session_id}{Colors.RESET}")
    except requests.RequestException as exc:
        print(f"{Colors.ERROR}❌ Failed to create scan session: {exc}{Colors.RESET}")
        return

    # Add repositories to scan
    print(f"{Colors.INFO}📦 Adding {len(repos)} repositories to scan...{Colors.RESET}")
    queued_repos: list[dict[str, Any]] = []
    max_retries = 100  # Maximum number of retry attempts for queued repos
    retry_count = 0
    initial_repos_processed = False
    any_repos_added = False

    while repos or queued_repos:
        try:
            # Process repos (either initial batch or queued repos from previous iteration)
            repos_to_process = repos if not initial_repos_processed else queued_repos
            if not repos_to_process:
                break

            response = requests.post(
                f"{api_base}/api/v1/scans/{session_id}/repos",
                json={"repos": repos_to_process},
                timeout=60,
            )
            response.raise_for_status()
            jobs_data = response.json()
            jobs_created = jobs_data.get("jobs_created", 0)
            queued_count = jobs_data.get("queued_repos", 0)
            new_queued_repos = jobs_data.get("queued_repos_list", [])

            if jobs_created > 0:
                print(f"{Colors.SUCCESS}✅ Created {jobs_created} Kubernetes Jobs{Colors.RESET}")
                any_repos_added = True

            # Clear initial repos list after first iteration
            if not initial_repos_processed:
                repos = []
                initial_repos_processed = True

            # Update queued repos for next iteration
            queued_repos = new_queued_repos

            if queued_count > 0:
                print(
                    f"{Colors.INFO}⏸️  {queued_count} repositories queued "
                    f"(will retry when jobs complete){Colors.RESET}"
                )

            # If we have queued repos, wait a bit before retrying
            if queued_repos:
                retry_count += 1
                if retry_count >= max_retries:
                    print(
                        f"{Colors.ERROR}❌ Maximum retry attempts reached. "
                        f"{len(queued_repos)} repos still queued.{Colors.RESET}"
                    )
                    break

                # Wait a bit before checking if slots are available
                time.sleep(5)
        except requests.RequestException as exc:
            print(f"{Colors.ERROR}❌ Failed to create jobs: {exc}{Colors.RESET}")
            return

    # If no repos were added, skip polling and results fetching
    if not any_repos_added:
        print(f"{Colors.INFO}No repositories to process.{Colors.RESET}")
        return

    # Poll for results
    print(f"{Colors.INFO}⏳ Waiting for analysis to complete...{Colors.RESET}")
    max_wait_time = config.max_wait_time
    poll_interval = config.poll_interval
    start_time = time.time()

    while time.time() - start_time < max_wait_time:
        try:
            response = requests.get(
                f"{api_base}/api/v1/scans/{session_id}",
                timeout=30,
            )
            response.raise_for_status()
            status_data = response.json()

            completed = status_data.get("completed_repos", 0)
            total = status_data.get("total_repos", 0)
            status_val = status_data.get("status", "unknown")

            print(
                f"{Colors.PROGRESS}📊 Status: {status_val} - "
                f"{completed}/{total} repositories completed{Colors.RESET}",
                end="\r",
            )

            if status_val == "completed":
                print()  # New line after progress
                break

            time.sleep(poll_interval)
        except requests.RequestException:
            time.sleep(poll_interval)
            continue

    # Get final results
    print(f"{Colors.INFO}📥 Fetching results...{Colors.RESET}")
    try:
        response = requests.get(
            f"{api_base}/api/v1/scans/{session_id}/results",
            timeout=30,
        )
        response.raise_for_status()
        results = response.json()

        print(f"\n{Colors.HEADER}{'─' * 80}{Colors.RESET}")
        print(f"{Colors.INFO}📊 Semgrep Analysis Summary:{Colors.RESET}")
        successes = sum(1 for r in results if r.get("success"))
        total = len(results)
        failed = total - successes
        print(
            f"{Colors.INFO}✓ Successfully analyzed: {successes}/{total} repositories{Colors.RESET}"
        )
        print(f"{Colors.INFO}✗ Failed to analyze: {failed}/{total} repositories{Colors.RESET}")
        print(f"{Colors.HEADER}{'─' * 80}{Colors.RESET}")
    except requests.RequestException as exc:
        print(f"{Colors.ERROR}❌ Failed to fetch results: {exc}{Colors.RESET}")
    # Cleanup: All resources (HTTP connections) are automatically cleaned up by requests library


def run_codeql_analysis(
    repos: list[dict[str, Any]],
    config: CodeQLConfig,
    language: str = "",
    query: str = "",
) -> None:
    """
    Run CodeQL analysis on the provided repositories.

    Args:
        repos: List of repository dictionaries
        config: CodeQL configuration
        language: Programming language for analysis
        query: Search query used to find repositories
    """
    analyze_repositories_with_codeql(
        repo_list=repos,
        colors=Colors,
        language=language,
        clone_dir=config.clone_dir,
        keep_cloned=config.keep_cloned,
        query_suite=config.query_suite,
        output_format=config.output_format,
        output_dir=config.output_dir,
        db_path=config.db_path,
        resume=config.resume,
        query=query,
    )


def save_repos_to_file(repos: list[dict[str, Any]], output_path: str) -> None:
    """
    Save repository list to a JSON file.

    Args:
        repos: List of repository dictionaries
        output_path: Path to the output JSON file
    """
    with Path(output_path).open("w", encoding="utf-8") as f:
        json.dump(repos, f, indent=2, ensure_ascii=False)
    print(f"{Colors.SUCCESS}💾 Results saved to {output_path}{Colors.RESET}")


def load_repos_from_file(input_path: str) -> list[dict[str, Any]]:
    """
    Load repository list from a JSON file.

    Args:
        input_path: Path to the input JSON file

    Returns:
        List of repository dictionaries

    Raises:
        FileNotFoundError: If the input file doesn't exist
        json.JSONDecodeError: If the file is not valid JSON
    """
    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    with path.open(encoding="utf-8") as f:
        repos = json.load(f)

    if not isinstance(repos, list):
        raise ValueError(f"Expected a list of repositories, got {type(repos).__name__}")

    return repos


def main() -> int:
    """
    Main entry point for the scanipy CLI.

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    parser = create_argument_parser()
    args = parser.parse_args()

    # Build configuration objects
    search_config, semgrep_config, codeql_config, github_token, search_strategy, sort_order = (
        build_configs_from_args(args)
    )

    # Display banner
    Display.print_banner()

    # Check if loading from input file
    if args.input_file:
        try:
            print(f"{Colors.INFO}📂 Loading repositories from {args.input_file}...{Colors.RESET}")
            repos = load_repos_from_file(args.input_file)
            print(f"{Colors.SUCCESS}✅ Loaded {len(repos)} repositories from file{Colors.RESET}\n")
        except FileNotFoundError as e:
            print(f"{Colors.ERROR}❌ Error: {e}{Colors.RESET}")
            return 1
        except json.JSONDecodeError as e:
            print(f"{Colors.ERROR}❌ Error: Invalid JSON in input file: {e}{Colors.RESET}")
            return 1
        except ValueError as e:
            print(f"{Colors.ERROR}❌ Error: {e}{Colors.RESET}")
            return 1
    else:
        # Validate GitHub token for search
        if not github_token:
            print(
                f"{Colors.ERROR}❌ Error: GITHUB_TOKEN environment variable "
                f"or --github-token argument must be set.{Colors.RESET}"
            )
            return 1

        # Display search info
        Display.print_search_info(search_config, strategy=search_strategy, sort_order=sort_order)

        # Perform GitHub search
        repos = search_repositories(
            search_config, github_token, strategy=search_strategy, sort_order=sort_order
        )

        # Save results to output file
        if repos:
            save_repos_to_file(repos, args.output)

    # Display results
    if repos:
        Display.print_results(repos, search_config.query, sort_order=sort_order)

        # Run Semgrep analysis if requested
        if semgrep_config.enabled:
            run_semgrep_analysis(repos, semgrep_config, query=search_config.query)

        # Run CodeQL analysis if requested
        if codeql_config.enabled:
            if not search_config.language:
                print(
                    f"{Colors.ERROR}❌ Error: --language is required "
                    f"for CodeQL analysis.{Colors.RESET}"
                )
                return 1
            run_codeql_analysis(
                repos, codeql_config, language=search_config.language, query=search_config.query
            )
    else:
        Display.print_results(repos, search_config.query, sort_order=sort_order)
        Display.print_no_results_hint(bool(search_config.keywords))

    return 0


if __name__ == "__main__":
    sys.exit(main())
