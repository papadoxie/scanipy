"""Tests for the GitHub API client classes."""

import os
from collections import defaultdict
from unittest.mock import MagicMock, patch, PropertyMock

import pytest
import requests

from integrations.github.github import BaseGitHubClient, RestAPI, GraphQLAPI
from integrations.github.models import (
    GitHubAPIError,
    GitHubNetworkError,
    GitHubRateLimitError,
    DEFAULT_TIMEOUT,
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
        query = client._build_search_query(
            "extractall", "python", ".py", "stars:>100"
        )
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

    def test_update_repositories_from_response(
        self, mock_github_token, mock_graphql_response
    ):
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
