"""Tests for the GitHub integration models module."""

import pytest

from integrations.github.models import (
    BATCH_QUERY_DELAY,
    CONTENT_FETCH_TIMEOUT,
    DEFAULT_BATCH_SIZE,
    DEFAULT_MAX_PAGES,
    DEFAULT_PER_PAGE,
    DEFAULT_STAR_TIERS,
    DEFAULT_TIMEOUT,
    GITHUB_API_BASE_URL,
    GITHUB_GRAPHQL_URL,
    GITHUB_REPO_SEARCH_URL,
    GITHUB_REST_SEARCH_URL,
    KEYWORD_FILTER_DELAY,
    MAX_RETRIES,
    PROGRESS_UPDATE_INTERVAL,
    RATE_LIMIT_DELAY,
    RATE_LIMIT_FALLBACK_DELAY,
    RETRY_BACKOFF,
    RETRY_DELAY,
    GitHubAPIError,
    GitHubNetworkError,
    GitHubRateLimitError,
)


class TestURLConstants:
    """Tests for URL constants."""

    def test_github_api_base_url(self):
        """Test GITHUB_API_BASE_URL is correct."""
        assert GITHUB_API_BASE_URL == "https://api.github.com"

    def test_github_rest_search_url(self):
        """Test GITHUB_REST_SEARCH_URL is correct."""
        assert GITHUB_REST_SEARCH_URL == "https://api.github.com/search/code"

    def test_github_repo_search_url(self):
        """Test GITHUB_REPO_SEARCH_URL is correct."""
        assert GITHUB_REPO_SEARCH_URL == "https://api.github.com/search/repositories"

    def test_github_graphql_url(self):
        """Test GITHUB_GRAPHQL_URL is correct."""
        assert GITHUB_GRAPHQL_URL == "https://api.github.com/graphql"


class TestTimeoutConstants:
    """Tests for timeout constants."""

    def test_default_timeout(self):
        """Test DEFAULT_TIMEOUT has expected value."""
        assert DEFAULT_TIMEOUT == 30

    def test_content_fetch_timeout(self):
        """Test CONTENT_FETCH_TIMEOUT has expected value."""
        assert CONTENT_FETCH_TIMEOUT == 10


class TestRetryConstants:
    """Tests for retry configuration constants."""

    def test_max_retries(self):
        """Test MAX_RETRIES has expected value."""
        assert MAX_RETRIES == 3

    def test_retry_delay(self):
        """Test RETRY_DELAY has expected value."""
        assert RETRY_DELAY == 2.0

    def test_retry_backoff(self):
        """Test RETRY_BACKOFF has expected value."""
        assert RETRY_BACKOFF == 2


class TestRateLimitConstants:
    """Tests for rate limiting constants."""

    def test_rate_limit_delay(self):
        """Test RATE_LIMIT_DELAY has expected value."""
        assert RATE_LIMIT_DELAY == 0.5

    def test_rate_limit_fallback_delay(self):
        """Test RATE_LIMIT_FALLBACK_DELAY has expected value."""
        assert RATE_LIMIT_FALLBACK_DELAY == 1.0

    def test_keyword_filter_delay(self):
        """Test KEYWORD_FILTER_DELAY has expected value."""
        assert KEYWORD_FILTER_DELAY == 0.2

    def test_batch_query_delay(self):
        """Test BATCH_QUERY_DELAY has expected value."""
        assert BATCH_QUERY_DELAY == 2.0


class TestPaginationConstants:
    """Tests for pagination constants."""

    def test_default_per_page(self):
        """Test DEFAULT_PER_PAGE has expected value."""
        assert DEFAULT_PER_PAGE == 100

    def test_default_max_pages(self):
        """Test DEFAULT_MAX_PAGES has expected value."""
        assert DEFAULT_MAX_PAGES == 10

    def test_default_batch_size(self):
        """Test DEFAULT_BATCH_SIZE has expected value."""
        assert DEFAULT_BATCH_SIZE == 25

    def test_progress_update_interval(self):
        """Test PROGRESS_UPDATE_INTERVAL has expected value."""
        assert PROGRESS_UPDATE_INTERVAL == 10


class TestStarTierConstants:
    """Tests for star tier configuration."""

    def test_default_star_tiers_count(self):
        """Test DEFAULT_STAR_TIERS has expected number of tiers."""
        assert len(DEFAULT_STAR_TIERS) == 6

    def test_default_star_tiers_structure(self):
        """Test DEFAULT_STAR_TIERS has correct structure."""
        for tier in DEFAULT_STAR_TIERS:
            assert isinstance(tier, tuple)
            assert len(tier) == 2
            assert isinstance(tier[0], int)
            assert tier[1] is None or isinstance(tier[1], int)

    def test_default_star_tiers_order(self):
        """Test DEFAULT_STAR_TIERS is ordered from highest to lowest."""
        # First tier should have highest min_stars (100k+)
        assert DEFAULT_STAR_TIERS[0][0] == 100000
        assert DEFAULT_STAR_TIERS[0][1] is None  # No upper limit

        # Last tier should have lowest min_stars (1k-5k)
        assert DEFAULT_STAR_TIERS[-1][0] == 1000
        assert DEFAULT_STAR_TIERS[-1][1] == 4999


class TestExceptions:
    """Tests for exception classes."""

    def test_github_api_error_is_exception(self):
        """Test GitHubAPIError is an Exception."""
        assert issubclass(GitHubAPIError, Exception)

    def test_github_api_error_message(self):
        """Test GitHubAPIError can be raised with message."""
        with pytest.raises(GitHubAPIError) as exc_info:
            raise GitHubAPIError("API request failed")
        assert str(exc_info.value) == "API request failed"

    def test_github_network_error_is_api_error(self):
        """Test GitHubNetworkError is a GitHubAPIError."""
        assert issubclass(GitHubNetworkError, GitHubAPIError)

    def test_github_network_error_message(self):
        """Test GitHubNetworkError can be raised with message."""
        with pytest.raises(GitHubNetworkError) as exc_info:
            raise GitHubNetworkError("Connection failed")
        assert str(exc_info.value) == "Connection failed"

    def test_github_rate_limit_error_is_api_error(self):
        """Test GitHubRateLimitError is a GitHubAPIError."""
        assert issubclass(GitHubRateLimitError, GitHubAPIError)

    def test_github_rate_limit_error_message(self):
        """Test GitHubRateLimitError can be raised with message."""
        with pytest.raises(GitHubRateLimitError) as exc_info:
            raise GitHubRateLimitError("Rate limit exceeded")
        assert str(exc_info.value) == "Rate limit exceeded"

    def test_catching_network_error_as_api_error(self):
        """Test GitHubNetworkError can be caught as GitHubAPIError."""
        try:
            raise GitHubNetworkError("Network issue")
        except GitHubAPIError as e:
            assert str(e) == "Network issue"

    def test_catching_rate_limit_error_as_api_error(self):
        """Test GitHubRateLimitError can be caught as GitHubAPIError."""
        try:
            raise GitHubRateLimitError("Rate limited")
        except GitHubAPIError as e:
            assert str(e) == "Rate limited"
