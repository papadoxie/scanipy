"""
Models and constants for the GitHub integration.

This module contains exception classes, constants, and configuration
values used by the GitHub API clients.
"""

from __future__ import annotations

# =============================================================================
# Constants
# =============================================================================

GITHUB_API_BASE_URL = "https://api.github.com"
GITHUB_REST_SEARCH_URL = f"{GITHUB_API_BASE_URL}/search/code"
GITHUB_REPO_SEARCH_URL = f"{GITHUB_API_BASE_URL}/search/repositories"
GITHUB_GRAPHQL_URL = f"{GITHUB_API_BASE_URL}/graphql"

# Timeouts (seconds)
DEFAULT_TIMEOUT = 30
CONTENT_FETCH_TIMEOUT = 10

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 2.0  # Base delay between retries (seconds)
RETRY_BACKOFF = 2  # Exponential backoff multiplier

# Rate limiting delays (seconds)
RATE_LIMIT_DELAY = 0.5
RATE_LIMIT_FALLBACK_DELAY = 1.0
KEYWORD_FILTER_DELAY = 0.2
BATCH_QUERY_DELAY = 2.0

# Pagination defaults
DEFAULT_PER_PAGE = 100
DEFAULT_MAX_PAGES = 10
DEFAULT_BATCH_SIZE = 25

# Progress display
PROGRESS_UPDATE_INTERVAL = 10

# Star tiers for tiered search (highest to lowest priority)
# Each tier is (min_stars, max_stars or None for unlimited)
DEFAULT_STAR_TIERS = [
    (10000, None),  # 10k+ stars - most popular
    (1000, 9999),  # 1k-10k stars
    (100, 999),  # 100-1k stars
    (10, 99),  # 10-100 stars
    (0, 9),  # <10 stars - least popular
]

# Maximum results per tier (to balance coverage across tiers)
DEFAULT_PAGES_PER_TIER = 2


# =============================================================================
# Exceptions
# =============================================================================


class GitHubAPIError(Exception):
    """Raised when a GitHub API request fails."""


class GitHubNetworkError(GitHubAPIError):
    """Raised when a network error occurs (DNS, connection, timeout)."""


class GitHubRateLimitError(GitHubAPIError):
    """Raised when GitHub API rate limit is exceeded."""
