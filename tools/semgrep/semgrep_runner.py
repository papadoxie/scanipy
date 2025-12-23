"""Utilities for running Semgrep analysis on repositories."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from collections.abc import Iterable
from pathlib import Path
from typing import Any


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
            ["git", "clone", "--depth=1", repo_url, clone_path], check=True, capture_output=True
        )
        return True
    except subprocess.CalledProcessError as exc:
        print(f"{colors.ERROR}❌ Failed to clone {repo_url}: {exc}{colors.RESET}")
        return False


def _run_semgrep(
    repo_path: str,
    colors: Any,
    semgrep_args: str = "",
    rules_path: str | None = None,
    use_pro: bool = False,
) -> tuple[bool, str]:
    """Execute Semgrep against *repo_path* and return success flag with output."""
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

        print(f"{colors.INFO}🔍 Running semgrep: {' '.join(cmd)}{colors.RESET}")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return True, result.stdout
    except subprocess.CalledProcessError as exc:
        return False, (f"Error running semgrep: {exc}\nOutput: {exc.stdout}\nError: {exc.stderr}")


def analyze_repositories_with_semgrep(
    repo_list: Iterable[dict[str, Any]],
    colors: Any,
    semgrep_args: str = "",
    clone_dir: str | None = None,
    keep_cloned: bool = False,
    rules_path: str | None = None,
    use_pro: bool = False,
) -> list[dict[str, Any]]:
    """Clone repositories in *repo_list* and run Semgrep on the first ten entries."""
    if not _check_command_exists("semgrep"):
        print(f"{colors.ERROR}❌ Error: semgrep is not installed on your system.{colors.RESET}")
        print(
            f"{colors.INFO}💡 To install semgrep, follow instructions at https://github.com/semgrep/semgrep{colors.RESET}"
        )
        return []

    if not _check_command_exists("git"):
        print(f"{colors.ERROR}❌ Error: git is not installed on your system.{colors.RESET}")
        return []

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

    print(f"{colors.HEADER}{'─' * 80}{colors.RESET}")
    print(
        f"{colors.INFO}🚀 Running semgrep analysis on the top "
        f"{len(repos_to_analyze)} repositories...{colors.RESET}"
    )
    if rules_path:
        print(f"{colors.INFO}📝 Using custom rules from: {rules_path}{colors.RESET}")
    if use_pro:
        print(f"{colors.INFO}🔒 Using semgrep with --pro flag{colors.RESET}")
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

            results.append({"repo": repo_name, "success": success, "output": output})
        else:
            results.append(
                {"repo": repo_name, "success": False, "output": "Failed to clone repository"}
            )

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
    print(f"{colors.INFO}📊 semrep Analysis Summary:{colors.RESET}")
    successes = sum(1 for result in results if result.get("success"))
    total = len(results)
    failed = total - successes
    print(f"{colors.INFO}✓ Successfully analyzed: {successes}/{total} repositories{colors.RESET}")
    print(f"{colors.INFO}✗ Failed to analyze: {failed}/{total} repositories{colors.RESET}")
    print(f"{colors.HEADER}{'─' * 80}{colors.RESET}")

    return results
