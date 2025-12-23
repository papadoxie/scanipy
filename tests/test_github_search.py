"""Tests for the GitHub search module."""

from unittest.mock import MagicMock, patch

import pytest

from integrations.github.search import (
    SearchStrategy,
    SortOrder,
    search_repositories,
)
from models import SearchConfig


class TestSearchStrategy:
    """Tests for the SearchStrategy enum."""

    def test_greedy_value(self):
        """Test GREEDY enum value."""
        assert SearchStrategy.GREEDY.value == "greedy"

    def test_tiered_stars_value(self):
        """Test TIERED_STARS enum value."""
        assert SearchStrategy.TIERED_STARS.value == "tiered"

    def test_enum_members(self):
        """Test all enum members exist."""
        assert hasattr(SearchStrategy, "GREEDY")
        assert hasattr(SearchStrategy, "TIERED_STARS")


class TestSortOrder:
    """Tests for the SortOrder enum."""

    def test_stars_value(self):
        """Test STARS enum value."""
        assert SortOrder.STARS.value == "stars"

    def test_updated_value(self):
        """Test UPDATED enum value."""
        assert SortOrder.UPDATED.value == "updated"

    def test_enum_members(self):
        """Test all enum members exist."""
        assert hasattr(SortOrder, "STARS")
        assert hasattr(SortOrder, "UPDATED")


class TestSearchRepositories:
    """Tests for the search_repositories function."""

    @patch("integrations.github.search.GraphQLAPI")
    @patch("integrations.github.search.RestAPI")
    def test_search_with_tiered_strategy(
        self, mock_rest_api, mock_graphql_api, sample_search_config, mock_github_token
    ):
        """Test search_repositories uses tiered strategy by default."""
        mock_rest_instance = MagicMock()
        mock_rest_instance.repositories = {}
        mock_rest_api.return_value = mock_rest_instance
        
        mock_graphql_instance = MagicMock()
        mock_graphql_instance.repositories = {}
        mock_graphql_api.return_value = mock_graphql_instance
        
        search_repositories(
            sample_search_config, mock_github_token, strategy=SearchStrategy.TIERED_STARS
        )
        
        mock_rest_instance.search_by_stars.assert_called_once()
        mock_rest_instance.search.assert_not_called()

    @patch("integrations.github.search.GraphQLAPI")
    @patch("integrations.github.search.RestAPI")
    def test_search_with_greedy_strategy(
        self, mock_rest_api, mock_graphql_api, sample_search_config, mock_github_token
    ):
        """Test search_repositories uses greedy strategy when specified."""
        mock_rest_instance = MagicMock()
        mock_rest_instance.repositories = {}
        mock_rest_api.return_value = mock_rest_instance
        
        mock_graphql_instance = MagicMock()
        mock_graphql_instance.repositories = {}
        mock_graphql_api.return_value = mock_graphql_instance
        
        search_repositories(
            sample_search_config, mock_github_token, strategy=SearchStrategy.GREEDY
        )
        
        mock_rest_instance.search.assert_called_once()
        mock_rest_instance.search_by_stars.assert_not_called()

    @patch("integrations.github.search.GraphQLAPI")
    @patch("integrations.github.search.RestAPI")
    def test_search_applies_keyword_filtering(
        self, mock_rest_api, mock_graphql_api, mock_github_token
    ):
        """Test search_repositories applies keyword filtering when keywords specified."""
        config = SearchConfig(query="test", keywords=["path", "directory"])
        
        mock_rest_instance = MagicMock()
        mock_rest_instance.repositories = {}
        mock_rest_api.return_value = mock_rest_instance
        
        mock_graphql_instance = MagicMock()
        mock_graphql_instance.repositories = {}
        mock_graphql_api.return_value = mock_graphql_instance
        
        search_repositories(config, mock_github_token, strategy=SearchStrategy.GREEDY)
        
        mock_rest_instance.filter_by_keywords.assert_called_once_with(["path", "directory"])

    @patch("integrations.github.search.GraphQLAPI")
    @patch("integrations.github.search.RestAPI")
    def test_search_skips_keyword_filtering_when_no_keywords(
        self, mock_rest_api, mock_graphql_api, mock_github_token
    ):
        """Test search_repositories skips keyword filtering when no keywords."""
        config = SearchConfig(query="test", keywords=[])
        
        mock_rest_instance = MagicMock()
        mock_rest_instance.repositories = {}
        mock_rest_api.return_value = mock_rest_instance
        
        mock_graphql_instance = MagicMock()
        mock_graphql_instance.repositories = {}
        mock_graphql_api.return_value = mock_graphql_instance
        
        search_repositories(config, mock_github_token, strategy=SearchStrategy.GREEDY)
        
        mock_rest_instance.filter_by_keywords.assert_not_called()

    @patch("integrations.github.search.GraphQLAPI")
    @patch("integrations.github.search.RestAPI")
    def test_search_enriches_with_graphql(
        self, mock_rest_api, mock_graphql_api, sample_search_config, mock_github_token
    ):
        """Test search_repositories enriches data with GraphQL."""
        mock_rest_instance = MagicMock()
        mock_rest_instance.repositories = {"owner/repo": {"files": []}}
        mock_rest_api.return_value = mock_rest_instance
        
        mock_graphql_instance = MagicMock()
        mock_graphql_instance.repositories = {"owner/repo": {"files": [], "stars": 100}}
        mock_graphql_api.return_value = mock_graphql_instance
        
        search_repositories(
            sample_search_config, mock_github_token, strategy=SearchStrategy.GREEDY
        )
        
        mock_graphql_api.assert_called_once()
        mock_graphql_instance.batch_query.assert_called_once()

    @patch("integrations.github.search.GraphQLAPI")
    @patch("integrations.github.search.RestAPI")
    def test_search_sorts_by_stars_default(
        self, mock_rest_api, mock_graphql_api, sample_search_config, mock_github_token
    ):
        """Test search_repositories sorts by stars by default."""
        mock_rest_instance = MagicMock()
        mock_rest_instance.repositories = {}
        mock_rest_api.return_value = mock_rest_instance
        
        mock_graphql_instance = MagicMock()
        mock_graphql_instance.repositories = {
            "low_stars": {"stars": 100, "updated_at": "2024-12-22"},
            "high_stars": {"stars": 1000, "updated_at": "2024-12-20"},
        }
        mock_graphql_api.return_value = mock_graphql_instance
        
        results = search_repositories(
            sample_search_config, mock_github_token, strategy=SearchStrategy.GREEDY
        )
        
        # Should be sorted by stars descending
        assert results[0]["stars"] == 1000
        assert results[1]["stars"] == 100

    @patch("integrations.github.search.GraphQLAPI")
    @patch("integrations.github.search.RestAPI")
    def test_search_sorts_by_updated(
        self, mock_rest_api, mock_graphql_api, sample_search_config, mock_github_token
    ):
        """Test search_repositories sorts by updated when specified."""
        mock_rest_instance = MagicMock()
        mock_rest_instance.repositories = {}
        mock_rest_api.return_value = mock_rest_instance
        
        mock_graphql_instance = MagicMock()
        mock_graphql_instance.repositories = {
            "old_update": {"stars": 1000, "updated_at": "2024-12-20"},
            "new_update": {"stars": 100, "updated_at": "2024-12-22"},
        }
        mock_graphql_api.return_value = mock_graphql_instance
        
        results = search_repositories(
            sample_search_config,
            mock_github_token,
            strategy=SearchStrategy.GREEDY,
            sort_order=SortOrder.UPDATED,
        )
        
        # Should be sorted by updated_at descending
        assert results[0]["updated_at"] == "2024-12-22"
        assert results[1]["updated_at"] == "2024-12-20"

    @patch("integrations.github.search.GraphQLAPI")
    @patch("integrations.github.search.RestAPI")
    def test_search_returns_list(
        self, mock_rest_api, mock_graphql_api, sample_search_config, mock_github_token
    ):
        """Test search_repositories returns a list."""
        mock_rest_instance = MagicMock()
        mock_rest_instance.repositories = {}
        mock_rest_api.return_value = mock_rest_instance
        
        mock_graphql_instance = MagicMock()
        mock_graphql_instance.repositories = {}
        mock_graphql_api.return_value = mock_graphql_instance
        
        results = search_repositories(
            sample_search_config, mock_github_token, strategy=SearchStrategy.GREEDY
        )
        
        assert isinstance(results, list)
