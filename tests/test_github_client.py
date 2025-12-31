"""Tests for the GitHub API client classes."""

from __future__ import annotations

import os
from collections import defaultdict
from unittest.mock import MagicMock, patch

import pytest
import requests

from integrations.github.github import GraphQLAPI, RestAPI
from integrations.github.models import (
    GitHubAPIError,
    GitHubNetworkError,
    GitHubRateLimitError,
)


class TestBaseGitHubClient:
    """Tests for the BaseGitHubClient abstract class."""

    def test_init_with_token(self, mock_github_token):
        """Test initialization with explicit token."""
        client = RestAPI(token=mock_github_token)
        assert client.token == mock_github_token

    def test_init_with_env_token(self, mock_env_token):
        """Test initialization with environment token."""
        client = RestAPI()
        assert client.token == mock_env_token

    def test_init_without_token_raises_error(self):
        """Test initialization without token raises GitHubAPIError."""
        with patch.dict(os.environ, {}, clear=True):
            # Ensure GITHUB_TOKEN is not in environment
            if "GITHUB_TOKEN" in os.environ:
                del os.environ["GITHUB_TOKEN"]
            with pytest.raises(GitHubAPIError) as exc_info:
                RestAPI()
            assert "GITHUB_TOKEN" in str(exc_info.value)

    def test_init_with_existing_repositories(self, mock_github_token, sample_repository_data):
        """Test initialization with existing repository data."""
        client = RestAPI(token=mock_github_token, repositories=sample_repository_data)
        assert client.repositories == sample_repository_data

    def test_init_creates_default_repositories(self, mock_github_token):
        """Test initialization creates defaultdict for repositories."""
        client = RestAPI(token=mock_github_token)
        assert isinstance(client.repositories, defaultdict)

    def test_create_repo_entry(self, mock_github_token):
        """Test _create_repo_entry creates correct structure."""
        client = RestAPI(token=mock_github_token)
        entry = client._create_repo_entry("owner/repo")

        assert entry["name"] == "owner/repo"
        assert entry["url"] == ""
        assert entry["stars"] == 0
        assert entry["description"] == ""
        assert entry["files"] == []

    def test_create_file_entry(self, mock_github_token):
        """Test _create_file_entry creates correct structure."""
        client = RestAPI(token=mock_github_token)
        entry = client._create_file_entry(
            path="src/main.py",
            url="https://github.com/owner/repo/blob/main/src/main.py",
            raw_url="https://raw.githubusercontent.com/owner/repo/main/src/main.py",
        )

        assert entry["path"] == "src/main.py"
        assert entry["url"] == "https://github.com/owner/repo/blob/main/src/main.py"
        assert entry["raw_url"] == "https://raw.githubusercontent.com/owner/repo/main/src/main.py"
        assert entry["keywords_found"] == []
        assert entry["keyword_match"] is None

    def test_create_file_entry_without_raw_url(self, mock_github_token):
        """Test _create_file_entry works without raw_url."""
        client = RestAPI(token=mock_github_token)
        entry = client._create_file_entry(
            path="src/main.py",
            url="https://github.com/owner/repo/blob/main/src/main.py",
        )
        assert entry["raw_url"] is None


class TestRestAPI:
    """Tests for the RestAPI class."""

    def test_headers_format(self, mock_github_token):
        """Test _headers returns correct format."""
        client = RestAPI(token=mock_github_token)
        headers = client._headers

        assert "Authorization" in headers
        assert headers["Authorization"] == f"token {mock_github_token}"
        assert headers["Accept"] == "application/vnd.github.v3+json"

    def test_build_search_query_basic(self, mock_github_token):
        """Test _build_search_query with just query."""
        client = RestAPI(token=mock_github_token)
        query = client._build_search_query("extractall", None, None, None)
        assert query == "extractall"

    def test_build_search_query_with_language(self, mock_github_token):
        """Test _build_search_query with language."""
        client = RestAPI(token=mock_github_token)
        query = client._build_search_query("extractall", "python", None, None)
        assert query == "extractall language:python"

    def test_build_search_query_with_extension(self, mock_github_token):
        """Test _build_search_query with extension."""
        client = RestAPI(token=mock_github_token)
        query = client._build_search_query("extractall", None, ".py", None)
        assert query == "extractall extension:.py"

    def test_build_search_query_with_all_params(self, mock_github_token):
        """Test _build_search_query with all parameters."""
        client = RestAPI(token=mock_github_token)
        query = client._build_search_query("extractall", "python", ".py", "stars:>100")
        assert query == "extractall language:python extension:.py stars:>100"

    def test_format_tier_label_unlimited(self, mock_github_token):
        """Test _format_tier_label with unlimited upper bound."""
        client = RestAPI(token=mock_github_token)
        label = client._format_tier_label(10000, None)
        assert "10,000+" in label

    def test_format_tier_label_range(self, mock_github_token):
        """Test _format_tier_label with range."""
        client = RestAPI(token=mock_github_token)
        label = client._format_tier_label(1000, 9999)
        assert "1,000" in label
        assert "9,999" in label

    def test_format_tier_label_low(self, mock_github_token):
        """Test _format_tier_label with zero min."""
        client = RestAPI(token=mock_github_token)
        label = client._format_tier_label(0, 9)
        assert "<10" in label

    def test_build_star_filter_unlimited(self, mock_github_token):
        """Test _build_star_filter with unlimited upper bound."""
        client = RestAPI(token=mock_github_token)
        filter_str = client._build_star_filter(10000, None)
        assert filter_str == "stars:>=10000"

    def test_build_star_filter_range(self, mock_github_token):
        """Test _build_star_filter with range."""
        client = RestAPI(token=mock_github_token)
        filter_str = client._build_star_filter(1000, 9999)
        assert filter_str == "stars:1000..9999"

    def test_build_star_filter_low(self, mock_github_token):
        """Test _build_star_filter with zero min."""
        client = RestAPI(token=mock_github_token)
        filter_str = client._build_star_filter(0, 9)
        assert filter_str == "stars:<=9"

    def test_convert_to_raw_url(self, mock_github_token):
        """Test _convert_to_raw_url conversion."""
        client = RestAPI(token=mock_github_token)
        github_url = "https://github.com/owner/repo/blob/main/src/main.py"
        raw_url = client._convert_to_raw_url(github_url)

        assert "raw.githubusercontent.com" in raw_url
        assert "/blob/" not in raw_url
        assert raw_url == "https://raw.githubusercontent.com/owner/repo/main/src/main.py"

    def test_find_keywords_in_content(self, mock_github_token):
        """Test _find_keywords_in_content finds keywords."""
        client = RestAPI(token=mock_github_token)
        content = "This is a test with path and directory keywords"
        keywords = ["path", "directory", "missing"]

        found = client._find_keywords_in_content(content, keywords)

        assert "path" in found
        assert "directory" in found
        assert "missing" not in found

    def test_find_keywords_case_insensitive(self, mock_github_token):
        """Test _find_keywords_in_content is case insensitive."""
        client = RestAPI(token=mock_github_token)
        content = "This contains PATH and Directory"
        keywords = ["path", "directory"]

        found = client._find_keywords_in_content(content, keywords)

        assert "path" in found
        assert "directory" in found

    def test_count_new_repos(self, mock_github_token):
        """Test _count_new_repos counts correctly."""
        client = RestAPI(token=mock_github_token)
        client.repositories["existing/repo"] = {"files": []}

        items = [
            {"repository": {"full_name": "existing/repo"}},
            {"repository": {"full_name": "new/repo1"}},
            {"repository": {"full_name": "new/repo2"}},
        ]

        count = client._count_new_repos(items)
        assert count == 2


class TestRestAPIRetry:
    """Tests for REST API retry functionality."""

    @patch("integrations.github.github.requests.get")
    def test_request_with_retry_success(self, mock_get, mock_github_token):
        """Test _request_with_retry succeeds on first attempt."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        client = RestAPI(token=mock_github_token)
        response = client._request_with_retry("get", "https://api.github.com/test")

        assert response.status_code == 200
        assert mock_get.call_count == 1

    @patch("integrations.github.github.time.sleep")
    @patch("integrations.github.github.requests.get")
    def test_request_with_retry_connection_error(self, mock_get, mock_sleep, mock_github_token):
        """Test _request_with_retry retries on connection error."""
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")

        client = RestAPI(token=mock_github_token)

        with pytest.raises(GitHubNetworkError):
            client._request_with_retry("get", "https://api.github.com/test", max_retries=2)

        assert mock_get.call_count == 2

    @patch("integrations.github.github.requests.get")
    def test_request_with_retry_rate_limit_403(self, mock_get, mock_github_token):
        """Test _request_with_retry raises on rate limit (403)."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.headers = {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1234567890"}
        mock_get.return_value = mock_response

        client = RestAPI(token=mock_github_token)

        with pytest.raises(GitHubRateLimitError):
            client._request_with_retry("get", "https://api.github.com/test")

    @patch("integrations.github.github.requests.get")
    def test_request_with_retry_rate_limit_429(self, mock_get, mock_github_token):
        """Test _request_with_retry raises on rate limit (429)."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "60"}
        mock_get.return_value = mock_response

        client = RestAPI(token=mock_github_token)

        with pytest.raises(GitHubRateLimitError):
            client._request_with_retry("get", "https://api.github.com/test")


class TestGraphQLAPI:
    """Tests for the GraphQLAPI class."""

    def test_headers_format(self, mock_github_token):
        """Test _headers returns correct format for GraphQL."""
        client = GraphQLAPI(token=mock_github_token)
        headers = client._headers

        assert "Authorization" in headers
        assert headers["Authorization"] == f"Bearer {mock_github_token}"
        assert headers["Content-Type"] == "application/json"

    def test_build_graphql_query(self, mock_github_token):
        """Test _build_graphql_query creates valid query."""
        client = GraphQLAPI(token=mock_github_token)
        repo_names = ["owner/repo1", "owner/repo2"]

        query = client._build_graphql_query(repo_names)

        assert "query" in query
        assert "repo0" in query
        assert "repo1" in query
        assert 'owner: "owner"' in query
        assert 'name: "repo1"' in query
        assert 'name: "repo2"' in query
        assert "stargazerCount" in query
        assert "description" in query
        assert "url" in query
        assert "updatedAt" in query

    def test_get_batch(self, mock_github_token):
        """Test _get_batch returns correct slice."""
        client = GraphQLAPI(token=mock_github_token)
        repo_names = ["repo1", "repo2", "repo3", "repo4", "repo5"]

        batch = client._get_batch(repo_names, batch_idx=0, batch_size=2)
        assert batch == ["repo1", "repo2"]

        batch = client._get_batch(repo_names, batch_idx=1, batch_size=2)
        assert batch == ["repo3", "repo4"]

        batch = client._get_batch(repo_names, batch_idx=2, batch_size=2)
        assert batch == ["repo5"]

    def test_update_repositories_from_response(self, mock_github_token, mock_graphql_response):
        """Test _update_repositories_from_response updates data correctly."""
        client = GraphQLAPI(token=mock_github_token)
        client.repositories = {
            "owner/repo1": {"name": "owner/repo1", "files": []},
            "owner/repo2": {"name": "owner/repo2", "files": []},
        }

        client._update_repositories_from_response(
            mock_graphql_response, ["owner/repo1", "owner/repo2"]
        )

        assert client.repositories["owner/repo1"]["stars"] == 1500
        assert client.repositories["owner/repo1"]["description"] == "A sample repository"
        assert client.repositories["owner/repo1"]["url"] == "https://github.com/owner/repo1"
        assert client.repositories["owner/repo1"]["updated_at"] == "2024-12-20T10:00:00Z"

    def test_update_repositories_handles_missing_repo(self, mock_github_token):
        """Test _update_repositories_from_response handles missing repo data."""
        client = GraphQLAPI(token=mock_github_token)
        client.repositories = {
            "owner/repo1": {"name": "owner/repo1", "files": []},
        }

        # Response with null repo data (repo not found)
        response = {"data": {"repo0": None}}

        client._update_repositories_from_response(response, ["owner/repo1"])

        # Should not crash, repo should remain unchanged
        assert client.repositories["owner/repo1"]["files"] == []


class TestRestAPISearch:
    """Tests for REST API search methods."""

    @patch("integrations.github.github.time.sleep")
    @patch("integrations.github.github.RestAPI._request_with_retry")
    def test_search_basic(self, mock_request, mock_sleep, mock_github_token):
        """Test basic search functionality."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "total_count": 1,
            "items": [
                {
                    "path": "src/main.py",
                    "html_url": "https://github.com/owner/repo/blob/main/src/main.py",
                    "repository": {
                        "full_name": "owner/repo",
                        "html_url": "https://github.com/owner/repo",
                    },
                }
            ],
        }
        mock_response.headers = {"X-RateLimit-Remaining": "10"}
        mock_request.return_value = mock_response

        client = RestAPI(token=mock_github_token)
        client.search("extractall", max_pages=1)

        assert "owner/repo" in client.repositories
        assert len(client.repositories["owner/repo"]["files"]) == 1

    @patch("integrations.github.github.time.sleep")
    @patch("integrations.github.github.RestAPI._request_with_retry")
    def test_search_with_language_and_extension(self, mock_request, mock_sleep, mock_github_token):
        """Test search with language and extension filters."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"total_count": 0, "items": []}
        mock_response.headers = {"X-RateLimit-Remaining": "10"}
        mock_request.return_value = mock_response

        client = RestAPI(token=mock_github_token)
        client.search("test", language="python", extension=".py", max_pages=1)

        # Check the query was built correctly
        call_args = mock_request.call_args
        assert "language:python" in str(call_args)
        assert "extension:.py" in str(call_args)

    @patch("integrations.github.github.time.sleep")
    @patch("integrations.github.github.RestAPI._request_with_retry")
    def test_search_handles_empty_results(self, mock_request, mock_sleep, mock_github_token):
        """Test search handles empty results gracefully."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"total_count": 0, "items": []}
        mock_response.headers = {"X-RateLimit-Remaining": "10"}
        mock_request.return_value = mock_response

        client = RestAPI(token=mock_github_token)
        client.search("nonexistent_pattern_xyz", max_pages=1)

        assert len(client.repositories) == 0

    @patch("integrations.github.github.time.sleep")
    @patch("integrations.github.github.requests.get")
    def test_filter_by_keywords(self, mock_get, mock_sleep, mock_github_token):
        """Test filter_by_keywords filters files correctly."""
        # Setup: mock the raw content fetch
        mock_content_response = MagicMock()
        mock_content_response.status_code = 200
        mock_content_response.text = "This file contains path and directory keywords"
        mock_get.return_value = mock_content_response

        client = RestAPI(token=mock_github_token)
        client.repositories = {
            "owner/repo": {
                "name": "owner/repo",
                "files": [
                    {
                        "path": "src/main.py",
                        "url": "https://github.com/owner/repo/blob/main/src/main.py",
                        "raw_url": "https://raw.githubusercontent.com/owner/repo/main/src/main.py",
                        "keyword_match": None,
                        "keywords_found": [],
                    }
                ],
            }
        }

        client.filter_by_keywords(["path", "directory"])

        # File should be marked as matching
        assert client.repositories["owner/repo"]["files"][0]["keyword_match"] is True
        assert "path" in client.repositories["owner/repo"]["files"][0]["keywords_found"]

    @patch("integrations.github.github.time.sleep")
    @patch("integrations.github.github.requests.get")
    def test_filter_by_keywords_no_match(self, mock_get, mock_sleep, mock_github_token):
        """Test filter_by_keywords marks files without matches."""
        mock_content_response = MagicMock()
        mock_content_response.status_code = 200
        mock_content_response.text = "This file has no relevant content"
        mock_get.return_value = mock_content_response

        client = RestAPI(token=mock_github_token)
        client.repositories = {
            "owner/repo": {
                "name": "owner/repo",
                "files": [
                    {
                        "path": "src/main.py",
                        "url": "https://github.com/owner/repo/blob/main/src/main.py",
                        "keyword_match": None,
                        "keywords_found": [],
                    }
                ],
            }
        }

        client.filter_by_keywords(["path", "directory"])

        # File should be marked as NOT matching (removed from repo)
        # The filter removes non-matching files, so repo might be empty
        assert (
            len(client.repositories) == 0
            or client.repositories["owner/repo"]["files"][0]["keyword_match"] is False
        )


class TestRestAPIRetryAdvanced:
    """Advanced tests for REST API retry functionality."""

    @patch("integrations.github.github.time.sleep")
    @patch("integrations.github.github.requests.get")
    def test_request_with_retry_timeout_error(self, mock_get, mock_sleep, mock_github_token):
        """Test _request_with_retry retries on timeout."""
        mock_get.side_effect = requests.exceptions.Timeout("Request timed out")

        client = RestAPI(token=mock_github_token)

        with pytest.raises(GitHubNetworkError) as exc_info:
            client._request_with_retry("get", "https://api.github.com/test", max_retries=2)

        assert "timeout" in str(exc_info.value).lower()
        assert mock_get.call_count == 2

    @patch("integrations.github.github.time.sleep")
    @patch("integrations.github.github.requests.post")
    def test_request_with_retry_post_method(self, mock_post, mock_sleep, mock_github_token):
        """Test _request_with_retry works with POST method."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        client = RestAPI(token=mock_github_token)
        response = client._request_with_retry(
            "post", "https://api.github.com/graphql", json={"query": "test"}
        )

        assert response.status_code == 200
        mock_post.assert_called_once()

    @patch("integrations.github.github.requests.get")
    def test_request_with_retry_invalid_method(self, mock_get, mock_github_token):
        """Test _request_with_retry raises on invalid method."""
        client = RestAPI(token=mock_github_token)

        with pytest.raises(ValueError) as exc_info:
            client._request_with_retry("delete", "https://api.github.com/test")

        assert "Unsupported HTTP method" in str(exc_info.value)

    @patch("integrations.github.github.time.sleep")
    @patch("integrations.github.github.requests.get")
    def test_request_with_retry_exponential_backoff(self, mock_get, mock_sleep, mock_github_token):
        """Test _request_with_retry uses exponential backoff."""
        mock_get.side_effect = requests.exceptions.ConnectionError("Failed")

        client = RestAPI(token=mock_github_token)

        with pytest.raises(GitHubNetworkError):
            client._request_with_retry("get", "https://api.github.com/test", max_retries=3)

        # Check sleep was called with increasing delays
        assert mock_sleep.call_count == 2  # Called between retries (not after last)
        delays = [call[0][0] for call in mock_sleep.call_args_list]
        assert delays[1] > delays[0]  # Second delay should be longer

    @patch("integrations.github.github.requests.get")
    def test_request_with_retry_403_non_rate_limit(self, mock_get, mock_github_token):
        """Test _request_with_retry returns 403 when not rate limited."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.headers = {"X-RateLimit-Remaining": "100"}  # Not rate limited
        mock_get.return_value = mock_response

        client = RestAPI(token=mock_github_token)
        response = client._request_with_retry("get", "https://api.github.com/test")

        # Should return response without raising (not a rate limit error)
        assert response.status_code == 403


class TestRestAPISearchByStars:
    """Tests for REST API tiered star search."""

    @patch("integrations.github.github.time.sleep")
    @patch("integrations.github.github.RestAPI._request_with_retry")
    def test_search_by_stars_basic(self, mock_request, mock_sleep, mock_github_token):
        """Test search_by_stars executes tiered search."""
        mock_repo_response = MagicMock()
        mock_repo_response.status_code = 200
        mock_repo_response.json.return_value = {"items": [{"full_name": "owner/popular-repo"}]}
        mock_repo_response.headers = {"X-RateLimit-Remaining": "10"}

        mock_code_response = MagicMock()
        mock_code_response.status_code = 200
        mock_code_response.json.return_value = {
            "items": [
                {
                    "path": "src/main.py",
                    "html_url": "https://github.com/owner/popular-repo/blob/main/src/main.py",
                    "repository": {
                        "full_name": "owner/popular-repo",
                        "html_url": "https://github.com/owner/popular-repo",
                    },
                }
            ]
        }
        mock_code_response.headers = {"X-RateLimit-Remaining": "10"}

        mock_request.side_effect = [mock_repo_response, mock_code_response] * 5

        client = RestAPI(token=mock_github_token)
        client.search_by_stars("extractall", max_pages=1, star_tiers=[(10000, None)])

        assert mock_request.called

    @patch("integrations.github.github.time.sleep")
    @patch("integrations.github.github.RestAPI._request_with_retry")
    def test_search_by_stars_no_repos_in_tier(self, mock_request, mock_sleep, mock_github_token):
        """Test search_by_stars handles empty tier results."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": []}
        mock_response.headers = {"X-RateLimit-Remaining": "10"}
        mock_request.return_value = mock_response

        client = RestAPI(token=mock_github_token)
        client.search_by_stars("nonexistent", max_pages=1, star_tiers=[(10000, None)])

        assert len(client.repositories) == 0

    @patch("integrations.github.github.time.sleep")
    @patch("integrations.github.github.RestAPI._request_with_retry")
    def test_find_repos_by_stars_rate_limit(self, mock_request, mock_sleep, mock_github_token):
        """Test _find_repos_by_stars handles rate limit errors."""
        mock_request.side_effect = GitHubRateLimitError("Rate limit exceeded")

        client = RestAPI(token=mock_github_token)
        repos, pages_used = client._find_repos_by_stars(min_stars=1000, max_stars=None)

        assert repos == []
        assert pages_used == 0

    @patch("integrations.github.github.time.sleep")
    @patch("integrations.github.github.RestAPI._request_with_retry")
    def test_find_repos_by_stars_network_error(self, mock_request, mock_sleep, mock_github_token):
        """Test _find_repos_by_stars handles network errors."""
        mock_request.side_effect = GitHubNetworkError("Network failed")

        client = RestAPI(token=mock_github_token)
        repos, pages_used = client._find_repos_by_stars(min_stars=1000, max_stars=None)

        assert repos == []
        assert pages_used == 0

    @patch("integrations.github.github.time.sleep")
    @patch("integrations.github.github.RestAPI._request_with_retry")
    def test_search_code_in_repo_success(self, mock_request, mock_sleep, mock_github_token):
        """Test _search_code_in_repo finds matches."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {
                    "path": "src/main.py",
                    "html_url": "https://github.com/owner/repo/blob/main/src/main.py",
                    "repository": {"full_name": "owner/repo"},
                }
            ]
        }
        mock_response.headers = {"X-RateLimit-Remaining": "10"}
        mock_request.return_value = mock_response

        client = RestAPI(token=mock_github_token)
        result = client._search_code_in_repo("owner/repo", "extractall")

        assert result is True
        assert "owner/repo" in client.repositories

    @patch("integrations.github.github.time.sleep")
    @patch("integrations.github.github.RestAPI._request_with_retry")
    def test_search_code_in_repo_no_matches(self, mock_request, mock_sleep, mock_github_token):
        """Test _search_code_in_repo returns False when no matches."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": []}
        mock_request.return_value = mock_response

        client = RestAPI(token=mock_github_token)
        result = client._search_code_in_repo("owner/repo", "nonexistent")

        assert result is False

    @patch("integrations.github.github.RestAPI._request_with_retry")
    def test_search_code_in_repo_network_error(self, mock_request, mock_github_token):
        """Test _search_code_in_repo handles network errors."""
        mock_request.side_effect = GitHubNetworkError("Failed")

        client = RestAPI(token=mock_github_token)
        result = client._search_code_in_repo("owner/repo", "query")

        assert result is False


class TestRestAPIRateLimiting:
    """Tests for rate limiting handling."""

    @patch("integrations.github.github.time.sleep")
    def test_handle_rate_limit_with_remaining(self, mock_sleep, mock_github_token):
        """Test _handle_rate_limit with remaining requests."""
        mock_response = MagicMock()
        mock_response.headers = {"X-RateLimit-Remaining": "50"}

        client = RestAPI(token=mock_github_token)
        client._handle_rate_limit(mock_response)

        mock_sleep.assert_called_once()

    @patch("integrations.github.github.time.sleep")
    def test_handle_rate_limit_no_header(self, mock_sleep, mock_github_token):
        """Test _handle_rate_limit without rate limit header."""
        mock_response = MagicMock()
        mock_response.headers = {}

        client = RestAPI(token=mock_github_token)
        client._handle_rate_limit(mock_response)

        mock_sleep.assert_called_once()

    @patch("integrations.github.github.time.time")
    @patch("integrations.github.github.time.sleep")
    def test_handle_rate_limit_exhausted(self, mock_sleep, mock_time, mock_github_token):
        """Test _handle_rate_limit when rate limit exhausted."""
        mock_time.return_value = 1000
        mock_response = MagicMock()
        mock_response.headers = {
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": "1005",
        }

        client = RestAPI(token=mock_github_token)
        client._handle_rate_limit(mock_response)

        mock_sleep.assert_called()


class TestRestAPIUtilities:
    """Tests for REST API utility methods."""

    def test_remove_empty_repositories(self, mock_github_token):
        """Test _remove_empty_repositories removes repos without files."""
        client = RestAPI(token=mock_github_token)
        client.repositories = {
            "has_files": {"files": [{"path": "test.py"}]},
            "no_files": {"files": []},
        }

        client._remove_empty_repositories()

        assert "has_files" in client.repositories
        assert "no_files" not in client.repositories

    def test_log_api_error(self, mock_github_token, capsys):
        """Test _log_api_error prints error details."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"message": "Not Found"}

        client = RestAPI(token=mock_github_token)
        client._log_api_error(mock_response)

        captured = capsys.readouterr()
        assert "404" in captured.out

    def test_log_api_error_non_json(self, mock_github_token, capsys):
        """Test _log_api_error handles non-JSON response."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.side_effect = ValueError("Not JSON")
        mock_response.text = "Internal Server Error"

        client = RestAPI(token=mock_github_token)
        client._log_api_error(mock_response)

        captured = capsys.readouterr()
        assert "500" in captured.out

    def test_print_progress(self, mock_github_token, capsys):
        """Test _print_progress outputs progress."""
        client = RestAPI(token=mock_github_token)
        client._print_progress(10, 100)

        captured = capsys.readouterr()
        assert "10" in captured.out


class TestGraphQLAPIBatchQuery:
    """Tests for GraphQL batch query functionality."""

    @patch("integrations.github.github.time.sleep")
    @patch("integrations.github.github.GraphQLAPI._request_with_retry")
    def test_batch_query_success(self, mock_request, mock_sleep, mock_github_token):
        """Test batch_query fetches repository metadata."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "repo0": {
                    "nameWithOwner": "owner/repo1",
                    "stargazerCount": 1000,
                    "description": "Test repo",
                    "url": "https://github.com/owner/repo1",
                    "updatedAt": "2024-12-20T10:00:00Z",
                }
            }
        }
        mock_request.return_value = mock_response

        client = GraphQLAPI(token=mock_github_token)
        client.repositories = {"owner/repo1": {"files": []}}
        client.batch_query(batch_size=25)

        assert client.repositories["owner/repo1"]["stars"] == 1000

    @patch("integrations.github.github.time.sleep")
    @patch("integrations.github.github.GraphQLAPI._request_with_retry")
    def test_batch_query_empty_repos(self, mock_request, mock_sleep, mock_github_token):
        """Test batch_query with no repositories."""
        client = GraphQLAPI(token=mock_github_token)
        client.repositories = {}
        client.batch_query()

        mock_request.assert_not_called()

    @patch("integrations.github.github.time.sleep")
    @patch("integrations.github.github.GraphQLAPI._request_with_retry")
    def test_batch_query_handles_errors(self, mock_request, mock_sleep, mock_github_token):
        """Test batch_query handles GraphQL errors gracefully."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"repo0": None},
            "errors": [{"message": "Repository not found"}],
        }
        mock_request.return_value = mock_response

        client = GraphQLAPI(token=mock_github_token)
        client.repositories = {"owner/nonexistent": {"files": []}}
        client.batch_query()

    @patch("integrations.github.github.time.sleep")
    @patch("integrations.github.github.GraphQLAPI._request_with_retry")
    def test_batch_query_network_error(self, mock_request, mock_sleep, mock_github_token):
        """Test batch_query handles network errors."""
        mock_request.side_effect = GitHubNetworkError("Network failed")

        client = GraphQLAPI(token=mock_github_token)
        client.repositories = {"owner/repo": {"files": []}}
        client.batch_query()

    @patch("integrations.github.github.time.sleep")
    @patch("integrations.github.github.GraphQLAPI._request_with_retry")
    def test_fetch_batch_data_api_error(self, mock_request, mock_sleep, mock_github_token):
        """Test _fetch_batch_data raises on non-200 status."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_request.return_value = mock_response

        client = GraphQLAPI(token=mock_github_token)

        with pytest.raises(GitHubAPIError):
            client._fetch_batch_data(["owner/repo"])

    @patch("integrations.github.github.time.sleep")
    @patch("integrations.github.github.GraphQLAPI._request_with_retry")
    def test_batch_query_rate_limit_error(self, mock_request, mock_sleep, mock_github_token):
        """Test batch_query handles rate limit errors."""
        mock_request.side_effect = GitHubRateLimitError("Rate limit exceeded")

        client = GraphQLAPI(token=mock_github_token)
        client.repositories = {"owner/repo": {"files": []}}
        client.batch_query()
        # Should not crash


class TestRestAPIRequestException:
    """Tests for request exception handling in _request_with_retry."""

    @patch("integrations.github.github.time.sleep")
    @patch("integrations.github.github.requests.get")
    def test_request_with_retry_timeout(self, mock_get, mock_sleep, mock_github_token):
        """Test _request_with_retry handles timeout exceptions."""
        mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")

        client = RestAPI(token=mock_github_token)

        with pytest.raises(GitHubNetworkError) as exc_info:
            client._request_with_retry("get", "https://api.github.com/test")

        assert "timeout" in str(exc_info.value).lower()

    @patch("integrations.github.github.time.sleep")
    @patch("integrations.github.github.requests.get")
    def test_request_with_retry_connection_error(self, mock_get, mock_sleep, mock_github_token):
        """Test _request_with_retry handles connection errors."""
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")

        client = RestAPI(token=mock_github_token)

        with pytest.raises(GitHubNetworkError) as exc_info:
            client._request_with_retry("get", "https://api.github.com/test")

        assert "connection" in str(exc_info.value).lower()

    @patch("integrations.github.github.time.sleep")
    @patch("integrations.github.github.requests.get")
    def test_request_with_retry_generic_request_exception(
        self, mock_get, mock_sleep, mock_github_token
    ):
        """Test _request_with_retry handles generic request exceptions."""
        mock_get.side_effect = requests.exceptions.RequestException("Request failed")

        client = RestAPI(token=mock_github_token)

        with pytest.raises(GitHubNetworkError) as exc_info:
            client._request_with_retry("get", "https://api.github.com/test")

        assert "failed" in str(exc_info.value).lower()


class TestRestAPISearchAPIError:
    """Tests for search method API error handling."""

    @patch("integrations.github.github.time.sleep")
    @patch("integrations.github.github.RestAPI._request_with_retry")
    def test_search_handles_api_error(self, mock_request, mock_sleep, mock_github_token):
        """Test search handles GitHubAPIError from _execute_search."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"message": "Internal Server Error"}
        mock_request.return_value = mock_response

        client = RestAPI(token=mock_github_token)
        client.search("extractall", max_pages=1)

        # Should not crash, just break the loop


class TestRestAPIFindReposByStarsEdgeCases:
    """Tests for _find_repos_by_stars edge cases."""

    @patch("integrations.github.github.time.sleep")
    @patch("integrations.github.github.RestAPI._request_with_retry")
    def test_find_repos_by_stars_non_200_status(self, mock_request, mock_sleep, mock_github_token):
        """Test _find_repos_by_stars handles non-200 status code."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.json.return_value = {"message": "Forbidden"}
        mock_request.return_value = mock_response

        client = RestAPI(token=mock_github_token)
        repos, pages_used = client._find_repos_by_stars(min_stars=1000, max_stars=None)

        assert repos == []
        assert pages_used == 1  # One page was attempted

    @patch("integrations.github.github.time.sleep")
    @patch("integrations.github.github.RestAPI._request_with_retry")
    def test_find_repos_by_stars_with_max_stars(self, mock_request, mock_sleep, mock_github_token):
        """Test _find_repos_by_stars with max_stars parameter."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [{"full_name": "owner/repo1"}, {"full_name": "owner/repo2"}]
        }
        mock_response.headers = {"X-RateLimit-Remaining": "10"}
        mock_request.return_value = mock_response

        client = RestAPI(token=mock_github_token)
        repos, pages_used = client._find_repos_by_stars(min_stars=100, max_stars=1000, max_pages=1)

        assert "owner/repo1" in repos
        assert "owner/repo2" in repos
        assert pages_used == 1


class TestRestAPISearchCodeInRepoEdgeCases:
    """Tests for _search_code_in_repo edge cases."""

    @patch("integrations.github.github.time.sleep")
    @patch("integrations.github.github.RestAPI._request_with_retry")
    def test_search_code_in_repo_rate_limit_error(
        self, mock_request, mock_sleep, mock_github_token
    ):
        """Test _search_code_in_repo handles rate limit errors."""
        mock_request.side_effect = GitHubRateLimitError("Rate limit exceeded")

        client = RestAPI(token=mock_github_token)
        result = client._search_code_in_repo("owner/repo", "query")

        assert result is False


class TestRestAPIFilterByKeywordsEdgeCases:
    """Tests for filter_by_keywords edge cases."""

    @patch("integrations.github.github.time.sleep")
    @patch("integrations.github.github.requests.get")
    def test_filter_by_keywords_fetch_exception(self, mock_get, mock_sleep, mock_github_token):
        """Test filter_by_keywords handles request exceptions when fetching content."""
        mock_get.side_effect = requests.RequestException("Network error")

        client = RestAPI(token=mock_github_token)
        client.repositories = {
            "owner/repo": {
                "files": [
                    {"path": "test.py", "url": "https://github.com/owner/repo/blob/main/test.py"}
                ]
            }
        }

        client.filter_by_keywords(["keyword"])

        # Files should be kept even if fetch fails
        assert "owner/repo" in client.repositories

    @patch("integrations.github.github.time.sleep")
    @patch("integrations.github.github.requests.get")
    def test_filter_by_keywords_file_without_url(self, mock_get, mock_sleep, mock_github_token):
        """Test filter_by_keywords handles files without URL."""
        client = RestAPI(token=mock_github_token)
        client.repositories = {
            "owner/repo": {
                "files": [{"path": "test.py"}]  # No URL
            }
        }

        client.filter_by_keywords(["keyword"])

        # File should be kept
        assert len(client.repositories["owner/repo"]["files"]) == 1

    @patch("integrations.github.github.time.sleep")
    @patch("integrations.github.github.requests.get")
    def test_filter_by_keywords_non_200_response(self, mock_get, mock_sleep, mock_github_token):
        """Test filter_by_keywords handles non-200 response when fetching content."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        client = RestAPI(token=mock_github_token)
        client.repositories = {
            "owner/repo": {
                "files": [
                    {"path": "test.py", "url": "https://github.com/owner/repo/blob/main/test.py"}
                ]
            }
        }

        client.filter_by_keywords(["keyword"])

        # Files should be kept even if content fetch returns 404
        assert "owner/repo" in client.repositories

    def test_filter_by_keywords_empty_list(self, mock_github_token):
        """Test filter_by_keywords returns early when keywords list is empty."""
        client = RestAPI(token=mock_github_token)
        client.repositories = {
            "owner/repo": {
                "files": [
                    {"path": "test.py", "url": "https://github.com/owner/repo/blob/main/test.py"}
                ]
            }
        }

        # Empty keywords should return early without filtering
        client.filter_by_keywords([])

        # Repository should remain unchanged
        assert len(client.repositories["owner/repo"]["files"]) == 1


class TestSearchByStarsSkipExisting:
    """Tests for search_by_stars skipping existing repositories."""

    @patch("integrations.github.github.time.sleep")
    @patch("integrations.github.github.RestAPI._request_with_retry")
    def test_search_by_stars_skips_existing_repos(
        self, mock_request, mock_sleep, mock_github_token
    ):
        """Test search_by_stars skips repos already in repositories dict."""
        # First response: repo search
        mock_repo_response = MagicMock()
        mock_repo_response.status_code = 200
        mock_repo_response.json.return_value = {"items": [{"full_name": "owner/existing-repo"}]}
        mock_repo_response.headers = {"X-RateLimit-Remaining": "10"}

        mock_request.return_value = mock_repo_response

        client = RestAPI(token=mock_github_token)
        # Pre-populate with existing repo
        client.repositories = {"owner/existing-repo": {"files": []}}

        client.search_by_stars("query", max_pages=1, star_tiers=[(10000, None)])

        # Should still have only the original repo (skipped the duplicate)
        assert "owner/existing-repo" in client.repositories


class TestFindReposByStarsWithLanguage:
    """Tests for _find_repos_by_stars with language filter."""

    @patch("integrations.github.github.time.sleep")
    @patch("integrations.github.github.RestAPI._request_with_retry")
    def test_find_repos_by_stars_with_language(self, mock_request, mock_sleep, mock_github_token):
        """Test _find_repos_by_stars includes language filter."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": [{"full_name": "owner/python-repo"}]}
        mock_response.headers = {"X-RateLimit-Remaining": "10"}
        mock_request.return_value = mock_response

        client = RestAPI(token=mock_github_token)
        repos, pages_used = client._find_repos_by_stars(
            min_stars=1000, max_stars=None, language="python", max_pages=1
        )

        assert "owner/python-repo" in repos
        assert pages_used == 1
        # Verify language was included in the query
        call_args = mock_request.call_args
        assert "language:python" in call_args[1]["params"]["q"]


class TestSearchCodeInRepoNon200:
    """Tests for _search_code_in_repo non-200 status handling."""

    @patch("integrations.github.github.time.sleep")
    @patch("integrations.github.github.RestAPI._request_with_retry")
    def test_search_code_in_repo_non_200_status(self, mock_request, mock_sleep, mock_github_token):
        """Test _search_code_in_repo returns False on non-200 status."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_request.return_value = mock_response

        client = RestAPI(token=mock_github_token)
        result = client._search_code_in_repo("owner/repo", "query")

        assert result is False


class TestGraphQLBatchQueryRateLimit:
    """Tests for GraphQL batch_query rate limit handling."""

    @patch("integrations.github.github.time.sleep")
    @patch("integrations.github.github.GraphQLAPI._request_with_retry")
    def test_process_batch_rate_limit_error(
        self, mock_request, mock_sleep, mock_github_token, capsys
    ):
        """Test _process_batch handles rate limit errors."""
        mock_request.side_effect = GitHubRateLimitError("Rate limit exceeded")

        client = GraphQLAPI(token=mock_github_token)
        client.repositories = {"owner/repo": {"files": []}}

        # Call _process_batch directly with required arguments
        client._process_batch(["owner/repo"], batch_num=1, total_batches=1)

        captured = capsys.readouterr()
        assert "Rate limit" in captured.out

    @patch("integrations.github.github.time.sleep")
    @patch("integrations.github.github.GraphQLAPI._request_with_retry")
    def test_process_batch_api_error(self, mock_request, mock_sleep, mock_github_token, capsys):
        """Test _process_batch handles generic API errors."""
        mock_request.side_effect = GitHubAPIError("API error occurred")

        client = GraphQLAPI(token=mock_github_token)
        client.repositories = {"owner/repo": {"files": []}}

        client._process_batch(["owner/repo"], batch_num=1, total_batches=1)

        captured = capsys.readouterr()
        assert "Error" in captured.out


class TestSearchByStarsPageBudgetExhaustion:
    """Tests for search_by_stars page budget exhaustion."""

    @patch("integrations.github.github.time.sleep")
    @patch("integrations.github.github.RestAPI._request_with_retry")
    def test_search_by_stars_stops_when_budget_exhausted(
        self, mock_request, mock_sleep, mock_github_token, capsys
    ):
        """Test search_by_stars stops processing tiers when page budget is exhausted."""
        # Mock response that returns full page (100 items) so tier doesn't exhaust early
        mock_repo_response = MagicMock()
        mock_repo_response.status_code = 200
        mock_repo_response.json.return_value = {
            "items": [{"full_name": f"owner/repo{i}"} for i in range(100)]
        }
        mock_repo_response.headers = {"X-RateLimit-Remaining": "10"}

        mock_code_response = MagicMock()
        mock_code_response.status_code = 200
        mock_code_response.json.return_value = {"items": []}
        mock_code_response.headers = {"X-RateLimit-Remaining": "10"}

        # Return repo response then code responses
        mock_request.side_effect = [mock_repo_response, mock_code_response] * 100

        client = RestAPI(token=mock_github_token)
        # Use only 1 page budget with multiple tiers - later tiers should not be processed
        client.search_by_stars(
            "query",
            max_pages=1,
            star_tiers=[(100000, None), (50000, 99999), (10000, 49999)],
        )

        captured = capsys.readouterr()
        # Should only see Tier 1, not Tier 2 or Tier 3 (stops after budget exhausted)
        assert "Tier 1/3" in captured.out
        assert "Tier 2/3" not in captured.out
        assert "Tier 3/3" not in captured.out
