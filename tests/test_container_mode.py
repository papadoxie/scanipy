"""Tests for container mode functionality in CLI."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from models import SemgrepConfig
from scanipy import run_semgrep_analysis


class TestContainerMode:
    """Tests for container mode execution."""

    @patch("scanipy.analyze_repositories_with_semgrep")
    def test_run_semgrep_analysis_local_mode(self, mock_analyze):
        """Test run_semgrep_analysis uses local mode when container_mode=False."""
        config = SemgrepConfig(
            enabled=True,
            container_mode=False,
        )
        repos = [{"name": "owner/repo", "url": "https://github.com/owner/repo"}]

        run_semgrep_analysis(repos, config, query="test")

        mock_analyze.assert_called_once()

    @patch("scanipy._run_semgrep_via_api")
    def test_run_semgrep_analysis_container_mode(self, mock_api):
        """Test run_semgrep_analysis uses API mode when container_mode=True."""
        config = SemgrepConfig(
            enabled=True,
            container_mode=True,
            api_url="http://api:8000",
            s3_bucket="test-bucket",  # Required for container mode
        )
        repos = [{"name": "owner/repo", "url": "https://github.com/owner/repo"}]

        run_semgrep_analysis(repos, config, query="test")

        mock_api.assert_called_once_with(repos, config, "test")

    @patch("scanipy._run_semgrep_via_api")
    def test_run_semgrep_analysis_container_mode_no_api_url(self, mock_api):
        """Test run_semgrep_analysis prints error when api_url missing in container mode."""
        config = SemgrepConfig(
            enabled=True,
            container_mode=True,
            api_url=None,
        )
        repos = [{"name": "owner/repo", "url": "https://github.com/owner/repo"}]

        run_semgrep_analysis(repos, config, query="test")

        mock_api.assert_not_called()

    @patch("scanipy._run_semgrep_via_api")
    def test_run_semgrep_analysis_container_mode_no_s3_bucket(self, mock_api, capsys):
        """Test run_semgrep_analysis prints error when s3_bucket missing in container mode."""
        config = SemgrepConfig(
            enabled=True,
            container_mode=True,
            api_url="http://api:8000",
            s3_bucket=None,  # Missing S3 bucket
        )
        repos = [{"name": "owner/repo", "url": "https://github.com/owner/repo"}]

        run_semgrep_analysis(repos, config, query="test")

        mock_api.assert_not_called()
        captured = capsys.readouterr()
        assert "s3-bucket is required" in captured.out
        assert "Container mode requires an S3 bucket" in captured.out

    def test_run_semgrep_via_api_success(self):
        """Test _run_semgrep_via_api successfully creates session and jobs."""
        # Mock the requests module before importing
        import sys

        mock_requests = MagicMock()
        sys.modules["requests"] = mock_requests
        try:
            # Create a mock RequestException class
            class MockRequestError(Exception):
                pass

            mock_requests.RequestException = MockRequestError

            # Mock API responses
            mock_create_response = MagicMock()
            mock_create_response.json.return_value = {"session_id": 1}
            mock_create_response.raise_for_status.return_value = None

            mock_jobs_response = MagicMock()
            mock_jobs_response.json.return_value = {"jobs_created": 2, "jobs": []}
            mock_jobs_response.raise_for_status.return_value = None

            mock_status_response = MagicMock()
            mock_status_response.json.return_value = {
                "session_id": 1,
                "status": "completed",
                "total_repos": 2,
                "completed_repos": 2,
                "failed_repos": 0,
            }
            mock_status_response.raise_for_status.return_value = None

            mock_results_response = MagicMock()
            mock_results_response.json.return_value = [
                {"repo": "owner/repo1", "success": True, "output": "No findings"},
                {"repo": "owner/repo2", "success": True, "output": "No findings"},
            ]
            mock_results_response.raise_for_status.return_value = None

            mock_requests.post.side_effect = [mock_create_response, mock_jobs_response]
            mock_requests.get.side_effect = [mock_status_response, mock_results_response]

            config = SemgrepConfig(
                enabled=True,
                container_mode=True,
                api_url="http://api:8000",
            )
            repos = [
                {"name": "owner/repo1", "url": "https://github.com/owner/repo1"},
                {"name": "owner/repo2", "url": "https://github.com/owner/repo2"},
            ]

            # Import and call the actual function
            from scanipy import _run_semgrep_via_api

            # Patch time.sleep to speed up test
            with patch("time.sleep"):
                _run_semgrep_via_api(repos, config, query="test")

            # Verify API calls
            assert mock_requests.post.call_count == 2  # Create session + add repos
            assert mock_requests.get.call_count == 2  # Status check + get results
        finally:
            # Clean up
            if "requests" in sys.modules and isinstance(sys.modules["requests"], MagicMock):
                del sys.modules["requests"]

    def test_run_semgrep_via_api_create_session_failure(self):
        """Test _run_semgrep_via_api handles session creation failure."""
        import sys

        mock_requests = MagicMock()

        # Create a mock RequestException class
        class MockRequestError(Exception):
            pass

        mock_requests.RequestException = MockRequestError
        mock_requests.post.side_effect = MockRequestError("Connection error")
        sys.modules["requests"] = mock_requests

        try:
            config = SemgrepConfig(
                enabled=True,
                container_mode=True,
                api_url="http://api:8000",
            )
            repos = [{"name": "owner/repo", "url": "https://github.com/owner/repo"}]

            from scanipy import _run_semgrep_via_api

            _run_semgrep_via_api(repos, config, query="test")

            # Should not proceed to create jobs
            assert mock_requests.post.call_count == 1
        finally:
            if "requests" in sys.modules and isinstance(sys.modules["requests"], MagicMock):
                del sys.modules["requests"]

    def test_run_semgrep_via_api_polls_until_complete(self):
        """Test _run_semgrep_via_api polls status until completion."""
        import sys

        mock_requests = MagicMock()
        sys.modules["requests"] = mock_requests

        try:
            # Create a mock RequestException class
            class MockRequestError(Exception):
                pass

            mock_requests.RequestException = MockRequestError

            # Mock API responses
            mock_create_response = MagicMock()
            mock_create_response.json.return_value = {"session_id": 1}
            mock_create_response.raise_for_status.return_value = None

            mock_jobs_response = MagicMock()
            mock_jobs_response.json.return_value = {"jobs_created": 1, "jobs": []}
            mock_jobs_response.raise_for_status.return_value = None

            # First status check: running
            mock_running_response = MagicMock()
            mock_running_response.json.return_value = {
                "session_id": 1,
                "status": "running",
                "total_repos": 1,
                "completed_repos": 0,
                "failed_repos": 0,
            }
            mock_running_response.raise_for_status.return_value = None

            # Second status check: completed
            mock_completed_response = MagicMock()
            mock_completed_response.json.return_value = {
                "session_id": 1,
                "status": "completed",
                "total_repos": 1,
                "completed_repos": 1,
                "failed_repos": 0,
            }
            mock_completed_response.raise_for_status.return_value = None

            mock_results_response = MagicMock()
            mock_results_response.json.return_value = [
                {"repo": "owner/repo", "success": True, "output": "No findings"}
            ]
            mock_results_response.raise_for_status.return_value = None

            mock_requests.post.side_effect = [mock_create_response, mock_jobs_response]
            mock_requests.get.side_effect = [
                mock_running_response,
                mock_completed_response,
                mock_results_response,
            ]

            config = SemgrepConfig(
                enabled=True,
                container_mode=True,
                api_url="http://api:8000",
            )
            repos = [{"name": "owner/repo", "url": "https://github.com/owner/repo"}]

            from scanipy import _run_semgrep_via_api

            # Patch time.sleep to speed up test
            with patch("time.sleep"):
                _run_semgrep_via_api(repos, config, query="test")

            # Should poll status at least twice (running then completed)
            status_calls = list(mock_requests.get.call_args_list)
            assert len(status_calls) >= 2
        finally:
            if "requests" in sys.modules and isinstance(sys.modules["requests"], MagicMock):
                del sys.modules["requests"]

    def test_run_semgrep_via_api_handles_missing_requests(self, capsys):
        """Test _run_semgrep_via_api handles missing requests library."""
        import builtins

        # Save the real __import__ before patching
        real_import = builtins.__import__

        # Make import raise ImportError for requests
        def import_side_effect(name, *args, **kwargs):
            if name == "requests":
                raise ImportError("No module named 'requests'")
            # For other imports, use real import (bypass the mock)
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=import_side_effect):
            config = SemgrepConfig(
                enabled=True,
                container_mode=True,
                api_url="http://api:8000",
                s3_bucket="test-bucket",
            )
            repos = [{"name": "owner/repo", "url": "https://github.com/owner/repo"}]

            from scanipy import _run_semgrep_via_api

            # Should handle gracefully without crashing
            _run_semgrep_via_api(repos, config, query="test")

            # Should print error message
            captured = capsys.readouterr()
            assert "requests library is required" in captured.out

    def test_run_semgrep_via_api_create_jobs_failure(self):
        """Test _run_semgrep_via_api handles job creation failure."""
        import sys

        mock_requests = MagicMock()
        sys.modules["requests"] = mock_requests
        try:

            class MockRequestError(Exception):
                pass

            mock_requests.RequestException = MockRequestError

            mock_create_response = MagicMock()
            mock_create_response.json.return_value = {"session_id": 1}
            mock_create_response.raise_for_status.return_value = None

            mock_requests.post.side_effect = [
                mock_create_response,
                MockRequestError("Failed to create jobs"),
            ]

            config = SemgrepConfig(
                enabled=True,
                container_mode=True,
                api_url="http://api:8000",
            )
            repos = [{"name": "owner/repo", "url": "https://github.com/owner/repo"}]

            from scanipy import _run_semgrep_via_api

            _run_semgrep_via_api(repos, config, query="test")

            # Should not proceed to poll
            assert mock_requests.post.call_count == 2
            assert mock_requests.get.call_count == 0
        finally:
            if "requests" in sys.modules and isinstance(sys.modules["requests"], MagicMock):
                del sys.modules["requests"]

    def test_run_semgrep_via_api_poll_exception(self):
        """Test _run_semgrep_via_api handles exceptions during polling."""
        import sys

        mock_requests = MagicMock()
        sys.modules["requests"] = mock_requests
        try:

            class MockRequestError(Exception):
                pass

            mock_requests.RequestException = MockRequestError

            mock_create_response = MagicMock()
            mock_create_response.json.return_value = {"session_id": 1}
            mock_create_response.raise_for_status.return_value = None

            mock_jobs_response = MagicMock()
            mock_jobs_response.json.return_value = {"jobs_created": 1}
            mock_jobs_response.raise_for_status.return_value = None

            # First poll raises exception, second succeeds
            mock_status_response = MagicMock()
            mock_status_response.json.return_value = {
                "session_id": 1,
                "status": "completed",
                "total_repos": 1,
                "completed_repos": 1,
            }
            mock_status_response.raise_for_status.return_value = None

            mock_results_response = MagicMock()
            mock_results_response.json.return_value = [{"repo": "owner/repo", "success": True}]
            mock_results_response.raise_for_status.return_value = None

            mock_requests.post.side_effect = [mock_create_response, mock_jobs_response]
            mock_requests.get.side_effect = [
                MockRequestError("Network error"),
                mock_status_response,
                mock_results_response,
            ]

            config = SemgrepConfig(
                enabled=True,
                container_mode=True,
                api_url="http://api:8000",
            )
            repos = [{"name": "owner/repo", "url": "https://github.com/owner/repo"}]

            from scanipy import _run_semgrep_via_api

            with patch("time.sleep"):
                _run_semgrep_via_api(repos, config, query="test")

            # Should continue polling after exception
            assert mock_requests.get.call_count >= 2
        finally:
            if "requests" in sys.modules and isinstance(sys.modules["requests"], MagicMock):
                del sys.modules["requests"]

    def test_run_semgrep_via_api_fetch_results_failure(self):
        """Test _run_semgrep_via_api handles results fetch failure."""
        import sys

        mock_requests = MagicMock()
        sys.modules["requests"] = mock_requests
        try:

            class MockRequestError(Exception):
                pass

            mock_requests.RequestException = MockRequestError

            mock_create_response = MagicMock()
            mock_create_response.json.return_value = {"session_id": 1}
            mock_create_response.raise_for_status.return_value = None

            mock_jobs_response = MagicMock()
            mock_jobs_response.json.return_value = {"jobs_created": 1}
            mock_jobs_response.raise_for_status.return_value = None

            mock_status_response = MagicMock()
            mock_status_response.json.return_value = {
                "session_id": 1,
                "status": "completed",
                "total_repos": 1,
                "completed_repos": 1,
            }
            mock_status_response.raise_for_status.return_value = None

            mock_requests.post.side_effect = [mock_create_response, mock_jobs_response]
            mock_requests.get.side_effect = [
                mock_status_response,
                MockRequestError("Failed to fetch results"),
            ]

            config = SemgrepConfig(
                enabled=True,
                container_mode=True,
                api_url="http://api:8000",
            )
            repos = [{"name": "owner/repo", "url": "https://github.com/owner/repo"}]

            from scanipy import _run_semgrep_via_api

            with patch("time.sleep"):
                _run_semgrep_via_api(repos, config, query="test")

            # Should handle error gracefully
            assert mock_requests.get.call_count == 2
        finally:
            if "requests" in sys.modules and isinstance(sys.modules["requests"], MagicMock):
                del sys.modules["requests"]

    def test_run_semgrep_via_api_empty_repos_break(self):
        """Test _run_semgrep_via_api breaks when repos_to_process is empty."""
        import sys

        mock_requests = MagicMock()
        sys.modules["requests"] = mock_requests
        try:

            class MockRequestError(Exception):
                pass

            mock_requests.RequestException = MockRequestError

            mock_create_response = MagicMock()
            mock_create_response.json.return_value = {"session_id": 1}
            mock_create_response.raise_for_status.return_value = None

            mock_requests.post.side_effect = [mock_create_response]

            config = SemgrepConfig(
                enabled=True,
                container_mode=True,
                api_url="http://api:8000",
                s3_bucket="test-bucket",
            )
            repos: list[dict[str, Any]] = []  # Empty repos list

            from scanipy import _run_semgrep_via_api

            with patch("time.sleep"):
                _run_semgrep_via_api(repos, config, query="test")

            # Should break early when repos_to_process is empty (after creating session)
            # repos is empty, so repos_to_process will be empty, triggering break
            assert mock_requests.post.call_count == 1  # Only create session
        finally:
            if "requests" in sys.modules and isinstance(sys.modules["requests"], MagicMock):
                del sys.modules["requests"]

    def test_run_semgrep_via_api_queued_repos_retry(self):
        """Test _run_semgrep_via_api retries queued repos."""
        import sys

        mock_requests = MagicMock()
        sys.modules["requests"] = mock_requests
        try:

            class MockRequestError(Exception):
                pass

            mock_requests.RequestException = MockRequestError

            mock_create_response = MagicMock()
            mock_create_response.json.return_value = {"session_id": 1}
            mock_create_response.raise_for_status.return_value = None

            # First add_repos: some queued
            mock_jobs_response1 = MagicMock()
            mock_jobs_response1.json.return_value = {
                "jobs_created": 2,
                "queued_repos": 1,
                "queued_repos_list": [
                    {"name": "owner/repo3", "url": "https://github.com/owner/repo3"}
                ],
            }
            mock_jobs_response1.raise_for_status.return_value = None

            # Second add_repos: all processed
            mock_jobs_response2 = MagicMock()
            mock_jobs_response2.json.return_value = {
                "jobs_created": 1,
                "queued_repos": 0,
            }
            mock_jobs_response2.raise_for_status.return_value = None

            mock_status_response = MagicMock()
            mock_status_response.json.return_value = {
                "session_id": 1,
                "status": "completed",
                "total_repos": 3,
                "completed_repos": 3,
            }
            mock_status_response.raise_for_status.return_value = None

            mock_results_response = MagicMock()
            mock_results_response.json.return_value = [
                {"repo": "owner/repo1", "success": True},
                {"repo": "owner/repo2", "success": True},
                {"repo": "owner/repo3", "success": True},
            ]
            mock_results_response.raise_for_status.return_value = None

            mock_requests.post.side_effect = [
                mock_create_response,
                mock_jobs_response1,
                mock_jobs_response2,
            ]
            mock_requests.get.side_effect = [mock_status_response, mock_results_response]

            config = SemgrepConfig(
                enabled=True,
                container_mode=True,
                api_url="http://api:8000",
                s3_bucket="test-bucket",
            )
            repos = [
                {"name": "owner/repo1", "url": "https://github.com/owner/repo1"},
                {"name": "owner/repo2", "url": "https://github.com/owner/repo2"},
                {"name": "owner/repo3", "url": "https://github.com/owner/repo3"},
            ]

            from scanipy import _run_semgrep_via_api

            with patch("time.sleep"):
                _run_semgrep_via_api(repos, config, query="test")

            # Should retry with queued repos
            assert mock_requests.post.call_count == 3  # create + add_repos (twice)
        finally:
            if "requests" in sys.modules and isinstance(sys.modules["requests"], MagicMock):
                del sys.modules["requests"]

    def test_run_semgrep_via_api_queued_repos_message(self, capsys):
        """Test _run_semgrep_via_api prints message when repos are queued."""
        import sys

        mock_requests = MagicMock()
        sys.modules["requests"] = mock_requests
        try:

            class MockRequestError(Exception):
                pass

            mock_requests.RequestException = MockRequestError

            mock_create_response = MagicMock()
            mock_create_response.json.return_value = {"session_id": 1}
            mock_create_response.raise_for_status.return_value = None

            # Return queued repos first time, then process them
            mock_jobs_response1 = MagicMock()
            mock_jobs_response1.json.return_value = {
                "jobs_created": 1,
                "queued_repos": 1,
                "queued_repos_list": [
                    {"name": "owner/repo2", "url": "https://github.com/owner/repo2"}
                ],
            }
            mock_jobs_response1.raise_for_status.return_value = None

            mock_jobs_response2 = MagicMock()
            mock_jobs_response2.json.return_value = {
                "jobs_created": 1,
                "queued_repos": 0,
            }
            mock_jobs_response2.raise_for_status.return_value = None

            mock_status_response = MagicMock()
            mock_status_response.json.return_value = {
                "session_id": 1,
                "status": "completed",
                "total_repos": 2,
                "completed_repos": 2,
            }
            mock_status_response.raise_for_status.return_value = None

            mock_results_response = MagicMock()
            mock_results_response.json.return_value = [
                {"repo": "owner/repo1", "success": True},
                {"repo": "owner/repo2", "success": True},
            ]
            mock_results_response.raise_for_status.return_value = None

            mock_requests.post.side_effect = [
                mock_create_response,
                mock_jobs_response1,
                mock_jobs_response2,
            ]
            mock_requests.get.side_effect = [mock_status_response, mock_results_response]

            config = SemgrepConfig(
                enabled=True,
                container_mode=True,
                api_url="http://api:8000",
                s3_bucket="test-bucket",
            )
            repos = [
                {"name": "owner/repo1", "url": "https://github.com/owner/repo1"},
                {"name": "owner/repo2", "url": "https://github.com/owner/repo2"},
            ]

            from scanipy import _run_semgrep_via_api

            with patch("time.sleep"):
                _run_semgrep_via_api(repos, config, query="test")

            # Should print queued repos message
            captured = capsys.readouterr()
            assert "queued" in captured.out.lower() or "repositories queued" in captured.out
        finally:
            if "requests" in sys.modules and isinstance(sys.modules["requests"], MagicMock):
                del sys.modules["requests"]
