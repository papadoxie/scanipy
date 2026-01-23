"""Pytest configuration and shared fixtures for Scanipy tests."""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def mock_github_token():
    """Provide a mock GitHub token."""
    return "ghp_test_token_1234567890"


@pytest.fixture
def mock_env_token(mock_github_token):
    """Set up environment with mock GitHub token."""
    with patch.dict(os.environ, {"GITHUB_TOKEN": mock_github_token}):
        yield mock_github_token


@pytest.fixture
def sample_search_config():
    """Create a sample SearchConfig for testing."""
    from models import SearchConfig

    return SearchConfig(
        query="extractall",
        language="python",
        extension=".py",
        keywords=["path", "directory"],
        additional_params="stars:>100",
        max_pages=5,
        per_page=100,
    )


@pytest.fixture
def sample_semgrep_config():
    """Create a sample SemgrepConfig for testing."""
    from models import SemgrepConfig

    return SemgrepConfig(
        enabled=True,
        args="--json",
        rules_path="/path/to/rules.yaml",
        clone_dir="/tmp/repos",
        keep_cloned=False,
        use_pro=False,
    )


@pytest.fixture
def sample_repository_data():
    """Create sample repository data for testing."""
    return {
        "owner/repo1": {
            "name": "owner/repo1",
            "url": "https://github.com/owner/repo1",
            "stars": 1500,
            "description": "A sample repository",
            "updated_at": "2024-12-20T10:00:00Z",
            "files": [
                {
                    "path": "src/main.py",
                    "url": "https://github.com/owner/repo1/blob/main/src/main.py",
                    "raw_url": None,
                    "keywords_found": [],
                    "keyword_match": None,
                },
            ],
        },
        "owner/repo2": {
            "name": "owner/repo2",
            "url": "https://github.com/owner/repo2",
            "stars": 500,
            "description": "Another repository",
            "updated_at": "2024-12-22T15:30:00Z",
            "files": [
                {
                    "path": "lib/utils.py",
                    "url": "https://github.com/owner/repo2/blob/main/lib/utils.py",
                    "raw_url": None,
                    "keywords_found": ["path"],
                    "keyword_match": True,
                },
            ],
        },
    }


@pytest.fixture
def mock_rest_api_response():
    """Create a mock REST API response for code search."""
    return {
        "total_count": 2,
        "incomplete_results": False,
        "items": [
            {
                "name": "main.py",
                "path": "src/main.py",
                "html_url": "https://github.com/owner/repo1/blob/main/src/main.py",
                "repository": {
                    "full_name": "owner/repo1",
                    "html_url": "https://github.com/owner/repo1",
                },
            },
            {
                "name": "utils.py",
                "path": "lib/utils.py",
                "html_url": "https://github.com/owner/repo2/blob/main/lib/utils.py",
                "repository": {
                    "full_name": "owner/repo2",
                    "html_url": "https://github.com/owner/repo2",
                },
            },
        ],
    }


@pytest.fixture
def mock_repo_search_response():
    """Create a mock repository search API response."""
    return {
        "total_count": 2,
        "incomplete_results": False,
        "items": [
            {
                "full_name": "owner/repo1",
                "html_url": "https://github.com/owner/repo1",
                "stargazers_count": 15000,
                "description": "A popular repository",
            },
            {
                "full_name": "owner/repo2",
                "html_url": "https://github.com/owner/repo2",
                "stargazers_count": 12000,
                "description": "Another popular repository",
            },
        ],
    }


@pytest.fixture
def mock_graphql_response():
    """Create a mock GraphQL API response."""
    return {
        "data": {
            "repo0": {
                "nameWithOwner": "owner/repo1",
                "stargazerCount": 1500,
                "description": "A sample repository",
                "url": "https://github.com/owner/repo1",
                "updatedAt": "2024-12-20T10:00:00Z",
            },
            "repo1": {
                "nameWithOwner": "owner/repo2",
                "stargazerCount": 500,
                "description": "Another repository",
                "url": "https://github.com/owner/repo2",
                "updatedAt": "2024-12-22T15:30:00Z",
            },
        }
    }


@pytest.fixture
def mock_colors():
    """Create a mock Colors class for testing."""
    mock = MagicMock()
    mock.HEADER = ""
    mock.SUCCESS = ""
    mock.WARNING = ""
    mock.ERROR = ""
    mock.INFO = ""
    mock.PROGRESS = ""
    mock.REPO_NAME = ""
    mock.STARS = ""
    mock.FILES = ""
    mock.URL = ""
    mock.DESCRIPTION = ""
    mock.RESET = ""
    return mock


def pytest_collection_modifyitems(config, items):
    """Modify test collection to run ImportError tests last."""
    # Separate ImportError tests from other tests
    import_error_tests = []
    other_tests = []

    for item in items:
        # Check if test is from test_import_errors.py using nodeid
        if "test_import_errors" in item.nodeid:
            import_error_tests.append(item)
        else:
            other_tests.append(item)

    # Reorder: other tests first, then ImportError tests
    items[:] = other_tests + import_error_tests
