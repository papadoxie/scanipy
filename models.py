"""
Data models and configuration classes for Scanipy.

This module contains all the data structures used throughout the application,
including configuration objects and shared constants.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from colorama import Fore, Style

# =============================================================================
# Constants
# =============================================================================

DEFAULT_MAX_PAGES = 5
DEFAULT_PER_PAGE = 100
DEFAULT_OUTPUT_FILE = "repos.json"
MAX_DISPLAY_REPOS = 20
MAX_FILES_PREVIEW = 3


# =============================================================================
# Color Configuration
# =============================================================================


class Colors:
    """Terminal color and styling configuration using colorama."""

    HEADER = Fore.CYAN + Style.BRIGHT
    SUCCESS = Fore.GREEN + Style.BRIGHT
    WARNING = Fore.YELLOW + Style.BRIGHT
    ERROR = Fore.RED + Style.BRIGHT
    INFO = Fore.BLUE + Style.BRIGHT
    PROGRESS = Fore.CYAN
    REPO_NAME = Fore.MAGENTA + Style.BRIGHT
    STARS = Fore.YELLOW + Style.BRIGHT
    FILES = Fore.GREEN
    URL = Fore.BLUE + Style.DIM
    DESCRIPTION = Fore.WHITE + Style.DIM
    RESET = Style.RESET_ALL


# =============================================================================
# Configuration Data Classes
# =============================================================================


@dataclass
class SearchConfig:
    """Configuration for GitHub code search."""

    query: str
    language: str = ""
    extension: str = ""
    keywords: list[str] = field(default_factory=list)
    additional_params: str = ""
    max_pages: int = DEFAULT_MAX_PAGES
    per_page: int = DEFAULT_PER_PAGE

    @property
    def full_query(self) -> str:
        """Build the complete search query string."""
        parts = [self.query]
        if self.language:
            parts.append(f"language:{self.language}")
        if self.extension:
            parts.append(f"extension:{self.extension}")
        if self.additional_params:
            parts.append(self.additional_params)
        return " ".join(parts)


DEFAULT_RESULTS_DB = "semgrep_results.db"


@dataclass
class SemgrepConfig:
    """Configuration for Semgrep analysis."""

    enabled: bool = False
    args: str = ""
    rules_path: str | None = None
    clone_dir: str | None = None
    keep_cloned: bool = False
    use_pro: bool = False
    db_path: str | None = None
    resume: bool = False


@dataclass
class CodeQLConfig:
    """Configuration for CodeQL analysis."""

    enabled: bool = False
    query_suite: str | None = None
    clone_dir: str | None = None
    keep_cloned: bool = False
    output_format: str = "sarif-latest"
    output_dir: str | None = None
