"""Utilities for running Semgrep analysis on repositories."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .results_db import ResultsDatabase


def _check_command_exists(cmd: str) -> bool:
    """Return True when *cmd* can be found in PATH."""
    try:
        subprocess.run(["which", cmd], check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        return False


def clone_repository(repo_url: str, clone_path: str, colors: Any | None = None) -> bool:
    """Clone *repo_url* into *clone_path* and return True on success.

    Args:
        repo_url: Repository URL to clone
        clone_path: Path where repository should be cloned
        colors: Optional color configuration for output (for backward compatibility)

    Returns:
        True if clone succeeded, False otherwise
    """
    try:
        subprocess.run(
            ["git", "clone", "--depth=1", repo_url, clone_path], check=True, capture_output=True
        )
        return True
    except subprocess.CalledProcessError as exc:
        if colors:
            print(f"{colors.ERROR}❌ Failed to clone {repo_url}: {exc}{colors.RESET}")
        return False


def run_semgrep_analysis(
    repo_path: str,
    semgrep_args: str = "",
    rules_path: str | None = None,
    use_pro: bool = False,
    colors: Any | None = None,
) -> tuple[bool, str]:
    """Execute Semgrep against *repo_path* and return success flag with output.

    Args:
        repo_path: Path to repository to analyze
        semgrep_args: Additional arguments for Semgrep
        rules_path: Path to custom Semgrep rules
        use_pro: Whether to use Semgrep Pro
        colors: Optional color configuration for output (for backward compatibility)

    Returns:
        Tuple of (success: bool, output: str)
    """
    try:
        cmd: list[str] = ["semgrep", "scan"]
        if use_pro:
            cmd.append("--pro")
        if rules_path:
            if not Path(rules_path).exists():
                return False, f"Error: Rules file or directory not found: {rules_path}"
            cmd.extend(["--config", rules_path])
        if semgrep_args and semgrep_args.strip():
            cmd.extend(semgrep_args.split())
        cmd.append(repo_path)

        if colors:
            print(f"{colors.INFO}🔍 Running semgrep: {' '.join(cmd)}{colors.RESET}")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return True, result.stdout
    except subprocess.CalledProcessError as exc:
        error_msg = f"Error running semgrep: {exc}"
        if exc.stdout:
            error_msg += f"\nOutput: {exc.stdout}"
        if exc.stderr:
            error_msg += f"\nError: {exc.stderr}"
        return False, error_msg


# Backward compatibility functions (keep old names for existing code)
def _clone_repository(repo_url: str, clone_path: str, colors: Any) -> bool:
    """Backward compatibility wrapper for clone_repository."""
    return clone_repository(repo_url, clone_path, colors)


def _run_semgrep(
    repo_path: str,
    colors: Any,
    semgrep_args: str = "",
    rules_path: str | None = None,
    use_pro: bool = False,
) -> tuple[bool, str]:
    """Backward compatibility wrapper for run_semgrep_analysis."""
    return run_semgrep_analysis(repo_path, semgrep_args, rules_path, use_pro, colors)


def analyze_repositories_with_semgrep(
    repo_list: Iterable[dict[str, Any]],
    colors: Any,
    semgrep_args: str = "",
    clone_dir: str | None = None,
    keep_cloned: bool = False,
    rules_path: str | None = None,
    use_pro: bool = False,
    db_path: str | None = None,
    resume: bool = False,
    query: str = "",
) -> list[dict[str, Any]]:
    """Clone repositories in *repo_list* and run Semgrep on the first ten entries.

    Args:
        repo_list: Iterable of repository dictionaries
        colors: Color configuration object
        semgrep_args: Additional arguments for Semgrep
        clone_dir: Directory to clone repos into (default: temp dir)
        keep_cloned: Whether to keep cloned repos after analysis
        rules_path: Path to custom Semgrep rules
        use_pro: Whether to use Semgrep Pro
        db_path: Path to SQLite database for storing results
        resume: Whether to resume from previous session
        query: The search query (used for session tracking)

    Returns:
        List of analysis result dictionaries
    """
    if not _check_command_exists("semgrep"):
        print(f"{colors.ERROR}❌ Error: semgrep is not installed on your system.{colors.RESET}")
        print(
            f"{colors.INFO}💡 To install semgrep, follow instructions at https://github.com/semgrep/semgrep{colors.RESET}"
        )
        return []

    if not _check_command_exists("git"):
        print(f"{colors.ERROR}❌ Error: git is not installed on your system.{colors.RESET}")
        return []

    # Initialize database if path provided
    db: ResultsDatabase | None = None
    session_id: int | None = None
    already_analyzed: set[str] = set()

    if db_path:
        db = ResultsDatabase(db_path)
        if resume and query:
            session_id = db.get_latest_session(query)
            if session_id:
                already_analyzed = db.get_analyzed_repos(session_id)
                print(
                    f"{colors.INFO}📂 Resuming session {session_id} - "
                    f"{len(already_analyzed)} repos already analyzed{colors.RESET}"
                )
        if session_id is None:
            session_id = db.create_session(query, rules_path, use_pro)
            print(f"{colors.INFO}💾 Created new session {session_id} in database{colors.RESET}")

    using_temp_dir = clone_dir is None
    actual_clone_dir: str
    if using_temp_dir:
        actual_clone_dir = tempfile.mkdtemp(prefix="scanipy_repos_")
        print(
            f"{colors.INFO}📁 Created temporary directory "
            f"for cloning: {actual_clone_dir}{colors.RESET}"
        )
    else:
        assert clone_dir is not None  # for type checker
        actual_clone_dir = clone_dir
        Path(actual_clone_dir).mkdir(parents=True, exist_ok=True)
        print(f"{colors.INFO}📁 Using directory for cloning: {actual_clone_dir}{colors.RESET}")

    repos_to_analyze = list(repo_list)[:10]

    # Filter out already analyzed repos if resuming
    if already_analyzed:
        repos_to_analyze = [r for r in repos_to_analyze if r.get("name") not in already_analyzed]
        if not repos_to_analyze:
            print(f"{colors.SUCCESS}✅ All repositories already analyzed!{colors.RESET}")
            # db and session_id are guaranteed to be set when already_analyzed is truthy
            assert db is not None
            assert session_id is not None
            return db.get_session_results(session_id)

    print(f"{colors.HEADER}{'─' * 80}{colors.RESET}")
    print(
        f"{colors.INFO}🚀 Running semgrep analysis on "
        f"{len(repos_to_analyze)} repositories...{colors.RESET}"
    )
    if rules_path:
        print(f"{colors.INFO}📝 Using custom rules from: {rules_path}{colors.RESET}")
    if use_pro:
        print(f"{colors.INFO}🔒 Using semgrep with --pro flag{colors.RESET}")
    if db_path:
        print(f"{colors.INFO}💾 Saving results to: {db_path}{colors.RESET}")
    print(f"{colors.HEADER}{'─' * 80}{colors.RESET}")

    results: list[dict[str, Any]] = []

    for index, repo in enumerate(repos_to_analyze, start=1):
        repo_url = repo.get("url")
        if not repo_url:
            continue

        repo_name = repo.get("name", f"repo_{index}")
        clone_path = str(Path(actual_clone_dir) / repo_name.replace("/", "_"))

        print(
            f"\n{colors.INFO}[{index}/{len(repos_to_analyze)}] Analyzing "
            f"{colors.REPO_NAME}{repo_name}{colors.RESET}"
        )
        print(
            f"{colors.PROGRESS}📥 Cloning repository: {repo_url} to {clone_path}...{colors.RESET}"
        )

        if _clone_repository(repo_url, clone_path, colors):
            print(f"{colors.SUCCESS}✅ Cloning successful{colors.RESET}")
            print(f"{colors.PROGRESS}🔍 Running semgrep analysis...{colors.RESET}")
            success, output = _run_semgrep(clone_path, colors, semgrep_args, rules_path, use_pro)

            if success:
                print(f"{colors.SUCCESS}✅ semgrep analysis complete{colors.RESET}")
                print(f"\n{colors.HEADER}--- semgrep results for {repo_name} ---{colors.RESET}")
                print(output)
                print(f"{colors.HEADER}{'─' * 80}{colors.RESET}")
            else:
                print(f"{colors.ERROR}❌ semgrep analysis failed{colors.RESET}")
                print(f"{colors.ERROR}{output}{colors.RESET}")

            result = {"repo": repo_name, "success": success, "output": output}
            results.append(result)

            # Save to database
            if db and session_id:
                db.save_result(session_id, repo_name, repo_url, success, output)
        else:
            result = {
                "repo": repo_name,
                "success": False,
                "output": "Failed to clone repository",
            }
            results.append(result)

            # Save failure to database
            if db and session_id and repo_url:
                db.save_result(session_id, repo_name, repo_url, False, "Failed to clone repository")

    if using_temp_dir and not keep_cloned:
        print(f"{colors.INFO}🧹 Cleaning up temporary directory...{colors.RESET}")
        try:
            shutil.rmtree(actual_clone_dir)
            print(f"{colors.SUCCESS}✅ Cleanup successful{colors.RESET}")
        except Exception as exc:
            print(f"{colors.ERROR}❌ Failed to clean up: {exc}{colors.RESET}")
    elif keep_cloned:
        print(f"{colors.INFO}💾 Repositories have been kept at: {actual_clone_dir}{colors.RESET}")

    # Get all results including previously analyzed ones
    all_results = results
    if db and session_id and already_analyzed:
        all_results = db.get_session_results(session_id)

    print(f"\n{colors.HEADER}{'─' * 80}{colors.RESET}")
    print(f"{colors.INFO}📊 Semgrep Analysis Summary:{colors.RESET}")
    successes = sum(1 for result in all_results if result.get("success"))
    total = len(all_results)
    failed = total - successes
    print(f"{colors.INFO}✓ Successfully analyzed: {successes}/{total} repositories{colors.RESET}")
    print(f"{colors.INFO}✗ Failed to analyze: {failed}/{total} repositories{colors.RESET}")
    if db_path:
        print(f"{colors.INFO}💾 Results saved to: {db_path}{colors.RESET}")
    print(f"{colors.HEADER}{'─' * 80}{colors.RESET}")

    return all_results
