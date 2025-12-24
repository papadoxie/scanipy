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
    (100000, None),  # 100k+ stars - most popular
    (50000, 99999),  # 50k-100k stars
    (20000, 49999),  # 20k-50k stars
    (10000, 19999),  # 10k-20k stars
    (5000, 9999),  # 5k-10k stars
    (1000, 4999),  # 1k-5k stars
]


# =============================================================================
# Exceptions
# =============================================================================


class GitHubAPIError(Exception):
    """Raised when a GitHub API request fails."""


class GitHubNetworkError(GitHubAPIError):
    """Raised when a network error occurs (DNS, connection, timeout)."""


class GitHubRateLimitError(GitHubAPIError):
    """Raised when GitHub API rate limit is exceeded."""
