"""Tests for the API service endpoints."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

pytest_plugins = ("pytest_asyncio",)

# Mock FastAPI before importing api module
with patch("services.api.api.FastAPI"):
    from services.api.api import (
        init_api,
        update_job_status,
    )
    from services.api.config import APIConfig


class TestAPIEndpoints:
    """Tests for API service endpoints."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database."""
        with patch("services.api.api.ResultsDatabase") as mock_db_class:
            mock_db = MagicMock()
            mock_db.create_session.return_value = 1
            mock_db.get_session_results.return_value = []
            mock_db.get_all_sessions.return_value = []
            mock_db.get_analyzed_repos.return_value = set()
            mock_db_class.return_value = mock_db
            yield mock_db

    @pytest.fixture
    def api_config(self):
        """Create API configuration."""
        return APIConfig(
            db_path="/tmp/test.db",
            k8s_namespace="test",
            worker_image="test-image:latest",
            s3_bucket="test-bucket",
        )

    def test_init_api(self, api_config, mock_db):
        """Test init_api initializes the API."""
        init_api(api_config)

        # Verify database was initialized
        from services.api import api as api_module

        assert api_module.db is not None
        assert api_module.api_config == api_config

    def test_init_api_with_db_url(self, mock_db):
        """Test init_api with PostgreSQL URL."""
        config = APIConfig(db_url="postgresql://user:pass@host/db")
        init_api(config)

        from services.api import api as api_module

        assert api_module.db is not None

    def test_init_api_raises_without_db(self):
        """Test init_api raises ValueError when no database configured."""
        config = APIConfig()
        with pytest.raises(ValueError, match="Either db_url or db_path"):
            init_api(config)

    @pytest.mark.asyncio
    async def test_create_scan(self, api_config, mock_db):
        """Test create_scan endpoint."""
        from services.api import api as api_module

        # Ensure FastAPI models are available
        if api_module.CreateScanRequest is None:
            pytest.skip("FastAPI not available")

        init_api(api_config)
        request = api_module.CreateScanRequest(
            query="test query",
            rules_path="/rules.yaml",
            use_pro=True,
        )

        result = await api_module.create_scan(request)

        assert result["session_id"] == 1
        assert result["query"] == "test query"
        assert result["status"] == "pending"
        mock_db.create_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_scan_without_db(self, api_config):
        """Test create_scan raises error when database not initialized."""
        from services.api import api as api_module

        if api_module.CreateScanRequest is None:
            pytest.skip("FastAPI not available")

        api_module.db = None
        request = api_module.CreateScanRequest(query="test query")

        with pytest.raises(api_module.HTTPException) as exc_info:
            await api_module.create_scan(request)

        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_get_scan_status(self, api_config, mock_db):
        """Test get_scan_status endpoint."""
        from services.api import api as api_module

        if api_module.ScanStatusResponse is None:
            pytest.skip("FastAPI not available")

        mock_db.get_session_results.return_value = [
            {"repo": "owner/repo1", "success": True},
            {"repo": "owner/repo2", "success": False},
        ]
        init_api(api_config)

        result = await api_module.get_scan_status(1)

        assert result.session_id == 1
        assert result.total_repos == 2
        assert result.completed_repos == 1
        assert result.failed_repos == 1
        # Status should be "completed" when all jobs have finished (regardless of success/failure)
        # Since we have results for both repos (one succeeded, one failed), both jobs finished
        assert result.status == "completed"

    @pytest.mark.asyncio
    async def test_get_scan_status_not_found(self, api_config, mock_db):
        """Test get_scan_status raises 404 when session not found."""
        from services.api import api as api_module

        mock_db.get_session_results.return_value = []
        init_api(api_config)

        with pytest.raises(api_module.HTTPException) as exc_info:
            await api_module.get_scan_status(999)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_scan_status_without_db(self, api_config):
        """Test get_scan_status raises 500 when database not initialized."""
        from services.api import api as api_module

        init_api(api_config)
        api_module.db = None  # Set to None after init to test error path

        with pytest.raises(api_module.HTTPException) as exc_info:
            await api_module.get_scan_status(1)

        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_get_scan_results(self, api_config, mock_db):
        """Test get_scan_results endpoint."""
        from services.api import api as api_module

        mock_db.get_session_results.return_value = [
            {"repo": "owner/repo1", "success": True, "output": "No findings"},
        ]
        init_api(api_config)

        results = await api_module.get_scan_results(1)

        assert len(results) == 1
        assert results[0]["repo"] == "owner/repo1"

    @pytest.mark.asyncio
    async def test_get_scan_results_without_db(self, api_config):
        """Test get_scan_results raises 500 when database not initialized."""
        from services.api import api as api_module

        init_api(api_config)
        api_module.db = None  # Set to None after init to test error path

        with pytest.raises(api_module.HTTPException) as exc_info:
            await api_module.get_scan_results(1)

        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_get_scan_results_not_found(self, api_config, mock_db):
        """Test get_scan_results raises 404 when session has no results."""
        from services.api import api as api_module

        mock_db.get_session_results.return_value = []
        init_api(api_config)

        with pytest.raises(api_module.HTTPException) as exc_info:
            await api_module.get_scan_results(999)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_add_repos_to_scan(self, api_config, mock_db):
        """Test add_repos_to_scan endpoint."""
        from services.api import api as api_module

        if api_module.AddReposRequest is None:
            pytest.skip("FastAPI not available")

        mock_db.get_all_sessions.return_value = [
            {"id": 1, "query": "test", "rules_path": "/rules.yaml", "use_pro": False}
        ]
        mock_k8s_client = MagicMock()
        mock_k8s_client.create_job.return_value = ("job-1", "job-id-1")
        init_api(api_config)
        api_module.k8s_client = mock_k8s_client

        request = api_module.AddReposRequest(
            repos=[
                {"name": "owner/repo1", "url": "https://github.com/owner/repo1"},
            ]
        )

        result = await api_module.add_repos_to_scan(1, request)

        assert result["session_id"] == 1
        assert result["jobs_created"] == 1
        mock_k8s_client.create_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_repos_to_scan_without_k8s(self, api_config, mock_db):
        """Test add_repos_to_scan raises error when K8s client not available."""
        from services.api import api as api_module

        if api_module.AddReposRequest is None:
            pytest.skip("FastAPI not available")

        mock_db.get_all_sessions.return_value = [{"id": 1, "query": "test"}]
        init_api(api_config)
        api_module.k8s_client = None

        request = api_module.AddReposRequest(
            repos=[{"name": "owner/repo", "url": "https://github.com/owner/repo"}]
        )

        with pytest.raises(api_module.HTTPException) as exc_info:
            await api_module.add_repos_to_scan(1, request)

        assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check endpoint."""
        from services.api import api as api_module

        result = await api_module.health_check()

        assert result["status"] == "healthy"
        assert result["service"] == "scanipy-api"

    @pytest.mark.asyncio
    async def test_update_job_status(self, api_config, mock_db):
        """Test update_job_status endpoint."""

        init_api(api_config)

        status_update = {
            "session_id": "1",
            "result": {
                "repo": "owner/repo",
                "url": "https://github.com/owner/repo",
                "success": True,
                "output": "No findings",
                "s3_path": "s3://bucket/key",
            },
        }

        result = await update_job_status("job-123", status_update)

        assert result["status"] == "ok"
        assert result["job_id"] == "job-123"
        mock_db.save_result.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_job_status_missing_repo(self, api_config, mock_db):
        """Test update_job_status raises error when repo is missing."""
        from services.api import api as api_module

        init_api(api_config)

        status_update = {
            "session_id": "1",
            "result": {
                "url": "https://github.com/owner/repo",
                "success": True,
                "output": "No findings",
            },
        }

        with pytest.raises(api_module.HTTPException) as exc_info:
            await update_job_status("job-123", status_update)

        assert exc_info.value.status_code == 400
        assert "Missing required field 'repo'" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_update_job_status_without_db(self, api_config):
        """Test update_job_status raises error when database not initialized."""
        from services.api import api as api_module

        api_module.db = None

        with pytest.raises(api_module.HTTPException) as exc_info:
            await update_job_status("job-123", {"result": {"repo": "owner/repo"}})

        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_update_job_status_no_result(self, api_config, mock_db):
        """Test update_job_status handles missing result."""

        init_api(api_config)

        status_update = {"session_id": "1"}

        result = await update_job_status("job-123", status_update)

        assert result["status"] == "ok"
        # Should not call save_result when result is missing
        mock_db.save_result.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_job_status_missing_session_id(self, api_config, mock_db):
        """Test update_job_status raises error when session_id is missing."""
        from services.api import api as api_module

        init_api(api_config)

        status_update = {
            "result": {
                "repo": "owner/repo",
                "url": "https://github.com/owner/repo",
                "success": True,
                "output": "No findings",
            },
        }

        with pytest.raises(api_module.HTTPException) as exc_info:
            await update_job_status("job-123", status_update)

        assert exc_info.value.status_code == 400
        assert "Missing required field 'session_id'" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_update_job_status_invalid_session_id_zero(self, api_config, mock_db):
        """Test update_job_status raises error when session_id is 0."""
        from services.api import api as api_module

        init_api(api_config)

        status_update = {
            "session_id": "0",
            "result": {
                "repo": "owner/repo",
                "url": "https://github.com/owner/repo",
                "success": True,
                "output": "No findings",
            },
        }

        with pytest.raises(api_module.HTTPException) as exc_info:
            await update_job_status("job-123", status_update)

        assert exc_info.value.status_code == 400
        assert "session_id must be greater than 0" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_update_job_status_invalid_session_id_negative(self, api_config, mock_db):
        """Test update_job_status raises error when session_id is negative."""
        from services.api import api as api_module

        init_api(api_config)

        status_update = {
            "session_id": "-1",
            "result": {
                "repo": "owner/repo",
                "url": "https://github.com/owner/repo",
                "success": True,
                "output": "No findings",
            },
        }

        with pytest.raises(api_module.HTTPException) as exc_info:
            await update_job_status("job-123", status_update)

        assert exc_info.value.status_code == 400
        assert "session_id must be greater than 0" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_scan_status_with_k8s_jobs(self, api_config, mock_db):
        """Test get_scan_status includes job statuses when K8s client available."""
        from services.api import api as api_module

        if api_module.ScanStatusResponse is None:
            pytest.skip("FastAPI not available")

        mock_db.get_session_results.return_value = [
            {"repo": "owner/repo1", "success": True, "k8s_job_id": "job-1"},
        ]
        mock_k8s_client = MagicMock()
        mock_k8s_client.get_job_status.return_value = {
            "name": "job-1",
            "succeeded": 1,
        }
        init_api(api_config)
        api_module.k8s_client = mock_k8s_client

        result = await api_module.get_scan_status(1)

        assert result.session_id == 1
        assert len(result.jobs) == 1
        mock_k8s_client.get_job_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_scan_status_k8s_job_exception(self, api_config, mock_db):
        """Test get_scan_status handles exceptions when getting job status."""
        from services.api import api as api_module

        if api_module.ScanStatusResponse is None:
            pytest.skip("FastAPI not available")

        mock_db.get_session_results.return_value = [
            {"repo": "owner/repo1", "success": True, "k8s_job_id": "job-1"},
        ]
        mock_k8s_client = MagicMock()
        mock_k8s_client.get_job_status.side_effect = Exception("Job not found")
        init_api(api_config)
        api_module.k8s_client = mock_k8s_client

        result = await api_module.get_scan_status(1)

        assert result.session_id == 1
        # Should continue even if job status fails
        assert len(result.jobs) == 0

    @pytest.mark.asyncio
    async def test_add_repos_to_scan_missing_session(self, api_config, mock_db):
        """Test add_repos_to_scan raises 404 when session not found."""
        from services.api import api as api_module

        if api_module.AddReposRequest is None:
            pytest.skip("FastAPI not available")

        mock_db.get_all_sessions.return_value = []
        mock_k8s_client = MagicMock()
        init_api(api_config)
        api_module.k8s_client = mock_k8s_client

        request = api_module.AddReposRequest(
            repos=[{"name": "owner/repo", "url": "https://github.com/owner/repo"}]
        )

        with pytest.raises(api_module.HTTPException) as exc_info:
            await api_module.add_repos_to_scan(999, request)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_add_repos_to_scan_missing_api_config(self, api_config, mock_db):
        """Test add_repos_to_scan raises error when API config not initialized."""
        from services.api import api as api_module

        if api_module.AddReposRequest is None:
            pytest.skip("FastAPI not available")

        mock_db.get_all_sessions.return_value = [{"id": 1, "query": "test"}]
        mock_k8s_client = MagicMock()
        init_api(api_config)
        api_module.k8s_client = mock_k8s_client
        api_module.api_config = None

        request = api_module.AddReposRequest(
            repos=[{"name": "owner/repo", "url": "https://github.com/owner/repo"}]
        )

        with pytest.raises(api_module.HTTPException) as exc_info:
            await api_module.add_repos_to_scan(1, request)

        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_add_repos_to_scan_invalid_repo(self, api_config, mock_db):
        """Test add_repos_to_scan skips repos with missing name or URL."""
        from services.api import api as api_module

        if api_module.AddReposRequest is None:
            pytest.skip("FastAPI not available")

        mock_db.get_all_sessions.return_value = [{"id": 1, "query": "test"}]
        mock_k8s_client = MagicMock()
        mock_k8s_client.create_job.return_value = ("test-job", "test-job-id")
        init_api(api_config)
        api_module.k8s_client = mock_k8s_client

        request = api_module.AddReposRequest(
            repos=[
                {"name": "owner/repo1", "url": "https://github.com/owner/repo1"},
                {"name": "", "url": "https://github.com/owner/repo2"},  # Missing name
                {"name": "owner/repo3"},  # Missing URL
            ]
        )

        result = await api_module.add_repos_to_scan(1, request)

        # Should only create job for valid repo
        assert result["jobs_created"] == 1
        mock_k8s_client.create_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_repos_to_scan_already_analyzed(self, api_config, mock_db):
        """Test add_repos_to_scan skips already analyzed repos."""
        from services.api import api as api_module

        if api_module.AddReposRequest is None:
            pytest.skip("FastAPI not available")

        mock_db.get_all_sessions.return_value = [{"id": 1, "query": "test"}]
        mock_db.get_analyzed_repos.return_value = {"owner/repo1"}
        mock_k8s_client = MagicMock()
        mock_k8s_client.create_job.return_value = ("test-job", "test-job-id")
        init_api(api_config)
        api_module.k8s_client = mock_k8s_client

        request = api_module.AddReposRequest(
            repos=[
                # Already analyzed
                {"name": "owner/repo1", "url": "https://github.com/owner/repo1"},
                {"name": "owner/repo2", "url": "https://github.com/owner/repo2"},
            ]
        )

        result = await api_module.add_repos_to_scan(1, request)

        # Should only create job for new repo
        assert result["jobs_created"] == 1
        mock_k8s_client.create_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_repos_to_scan_job_creation_failure(self, api_config, mock_db):
        """Test add_repos_to_scan handles job creation failures gracefully."""
        from services.api import api as api_module

        if api_module.AddReposRequest is None:
            pytest.skip("FastAPI not available")

        mock_db.get_all_sessions.return_value = [{"id": 1, "query": "test"}]
        mock_k8s_client = MagicMock()
        mock_k8s_client.create_job.side_effect = Exception("Failed to create job")
        init_api(api_config)
        api_module.k8s_client = mock_k8s_client

        request = api_module.AddReposRequest(
            repos=[{"name": "owner/repo", "url": "https://github.com/owner/repo"}]
        )

        result = await api_module.add_repos_to_scan(1, request)

        # Should continue even if job creation fails
        assert result["jobs_created"] == 0

    @pytest.mark.asyncio
    async def test_add_repos_to_scan_without_db(self, api_config):
        """Test add_repos_to_scan raises 500 when database not initialized."""
        from services.api import api as api_module

        if api_module.AddReposRequest is None:
            pytest.skip("FastAPI not available")

        init_api(api_config)
        api_module.db = None  # Set to None after init to test error path

        request = api_module.AddReposRequest(
            repos=[{"name": "owner/repo", "url": "https://github.com/owner/repo"}]
        )

        with pytest.raises(api_module.HTTPException) as exc_info:
            await api_module.add_repos_to_scan(1, request)

        assert exc_info.value.status_code == 500
