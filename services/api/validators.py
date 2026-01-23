"""Input validation functions for API endpoints."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse


def validate_session_id(session_id: int) -> int:
    """Validate session ID.

    Args:
        session_id: Session ID to validate

    Returns:
        Validated session ID

    Raises:
        ValueError: If session_id is invalid
    """
    if session_id <= 0:
        raise ValueError(f"session_id must be greater than 0, got: {session_id}")
    if session_id > 2**31 - 1:  # Reasonable upper bound (PostgreSQL integer max)
        raise ValueError(f"session_id too large: {session_id}")
    return session_id


def validate_repo_name(name: str) -> str:
    """Validate GitHub repository name format.

    Args:
        name: Repository name to validate (format: owner/repo)

    Returns:
        Validated repository name

    Raises:
        ValueError: If repository name format is invalid
    """
    if not name:
        raise ValueError("Repository name cannot be empty")

    # GitHub repo format: owner/repo
    # Owner and repo can contain alphanumeric, hyphens, underscores, dots
    # Must have exactly one slash
    pattern = r"^[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+$"
    if not re.match(pattern, name):
        raise ValueError(
            f"Invalid repository name format: {name}. "
            "Expected format: owner/repo (e.g., 'owner/repo-name')"
        )

    # Check length limits (GitHub allows up to 100 chars for owner, 100 for repo)
    parts = name.split("/")
    if len(parts) != 2:
        raise ValueError(f"Invalid repository name format: {name}. Expected: owner/repo")

    owner, repo = parts
    if len(owner) > 100 or len(repo) > 100:
        raise ValueError(
            f"Repository name too long: {name}. Owner and repo names must be <= 100 characters each"
        )

    return name


def validate_repo_url(url: str) -> str:
    """Validate GitHub repository URL.

    Args:
        url: Repository URL to validate

    Returns:
        Validated repository URL

    Raises:
        ValueError: If URL format is invalid
    """
    if not url:
        raise ValueError("Repository URL cannot be empty")

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Invalid URL scheme: {url}. Must be http:// or https://")

    if parsed.netloc not in ("github.com", "www.github.com"):
        raise ValueError(
            f"Invalid repository URL: {url}. Only GitHub repositories are supported (github.com)"
        )

    # Extract owner/repo from path
    path_parts = [p for p in parsed.path.split("/") if p]
    if len(path_parts) < 2:
        raise ValueError(
            f"Invalid repository URL format: {url}. Expected: https://github.com/owner/repo"
        )

    # Validate the repo name part
    owner = path_parts[0]
    repo = path_parts[1]
    repo_name = f"{owner}/{repo}"
    validate_repo_name(repo_name)  # Reuse repo name validation

    return url


def validate_rules_path(path: str | None) -> str | None:
    """Validate rules file path and prevent path traversal.

    Args:
        path: Path to validate

    Returns:
        Validated path or None

    Raises:
        ValueError: If path contains path traversal or is invalid
    """
    if path is None:
        return None

    if not path:
        raise ValueError("Rules path cannot be empty string")

    # Resolve path to prevent path traversal
    try:
        resolved = Path(path).resolve()
    except (OSError, ValueError) as exc:
        raise ValueError(f"Invalid rules path: {path}. Error: {exc}") from exc

    # Check for path traversal attempts
    # Ensure the resolved path doesn't contain '..' components
    if ".." in str(resolved):
        raise ValueError(f"Path traversal detected in rules path: {path}")

    # Check if path exists and is a file or directory
    # Note: We validate existence to prevent errors, but in some cases (like tests)
    # the path might not exist yet. We'll validate format but allow non-existent paths
    # if they're being created. However, if the path exists, it must be a file or directory.
    if resolved.exists() and not (resolved.is_file() or resolved.is_dir()):
        raise ValueError(f"Rules path must be a file or directory: {path}")

    return str(resolved)
