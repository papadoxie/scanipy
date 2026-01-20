"""Tests for the Semgrep worker module."""

from __future__ import annotations

import os
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from tools.semgrep.worker.worker import (
    clone_repository,
    get_env_var,
    main,
    report_status,
    run_semgrep,
    upload_to_s3,
)


class TestGetEnvVar:
    """Tests for the get_env_var function."""

    def test_get_required_env_var_exists(self):
        """Test get_env_var returns value when variable exists."""
        with patch.dict(os.environ, {"TEST_VAR": "test_value"}):
            result = get_env_var("TEST_VAR", required=True)
            assert result == "test_value"

    def test_get_required_env_var_missing(self):
        """Test get_env_var raises ValueError when required variable is missing."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Required environment variable"):
                get_env_var("MISSING_VAR", required=True)

    def test_get_optional_env_var_missing(self):
        """Test get_env_var returns empty string when optional variable is missing."""
        with patch.dict(os.environ, {}, clear=True):
            result = get_env_var("MISSING_VAR", required=False)
            assert result == ""


class TestCloneRepository:
    """Tests for the clone_repository function."""

    @patch("tools.semgrep.worker.worker.subprocess.run")
    def test_clone_success(self, mock_run):
        """Test clone_repository returns True on success."""
        mock_run.return_value = MagicMock(returncode=0)

        result = clone_repository("https://github.com/owner/repo", "/tmp/repo")

        assert result is True
        mock_run.assert_called_once_with(
            ["git", "clone", "--depth=1", "https://github.com/owner/repo", "/tmp/repo"],
            check=True,
            capture_output=True,
            text=True,
        )

    @patch("tools.semgrep.worker.worker.subprocess.run")
    def test_clone_failure(self, mock_run):
        """Test clone_repository returns False on failure."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "git clone")

        result = clone_repository("https://github.com/owner/repo", "/tmp/repo")

        assert result is False

    @patch("tools.semgrep.worker.worker.subprocess.run")
    def test_clone_failure_with_output(self, mock_run):
        """Test clone_repository prints stdout and stderr on failure."""
        mock_exc = subprocess.CalledProcessError(1, "git", "error")
        mock_exc.stdout = "stdout output"
        mock_exc.stderr = "stderr output"
        mock_run.side_effect = mock_exc

        result = clone_repository("https://github.com/owner/repo", "/tmp/repo")

        assert result is False


class TestRunSemgrep:
    """Tests for the run_semgrep function."""

    @patch("tools.semgrep.worker.worker.subprocess.run")
    def test_run_semgrep_success(self, mock_run):
        """Test run_semgrep returns success with output."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="No findings",
            stderr="",
        )

        success, output = run_semgrep("/tmp/repo")

        assert success is True
        assert output == "No findings"

    @patch("tools.semgrep.worker.worker.subprocess.run")
    def test_run_semgrep_failure(self, mock_run):
        """Test run_semgrep returns failure with error message."""
        error = subprocess.CalledProcessError(1, "semgrep")
        error.stdout = "stdout content"
        error.stderr = "stderr content"
        mock_run.side_effect = error

        success, output = run_semgrep("/tmp/repo")

        assert success is False
        assert "Error" in output

    @patch("tools.semgrep.worker.worker.subprocess.run")
    def test_run_semgrep_with_pro(self, mock_run):
        """Test run_semgrep includes --pro flag when specified."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        run_semgrep("/tmp/repo", use_pro=True)

        call_args = mock_run.call_args[0][0]
        assert "--pro" in call_args

    @patch("tools.semgrep.worker.worker.Path")
    @patch("tools.semgrep.worker.worker.subprocess.run")
    def test_run_semgrep_with_rules_path(self, mock_run, mock_path):
        """Test run_semgrep includes rules path when specified."""
        mock_path.return_value.exists.return_value = True
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        run_semgrep("/tmp/repo", rules_path="/path/to/rules.yaml")

        call_args = mock_run.call_args[0][0]
        assert "--config" in call_args
        assert "/path/to/rules.yaml" in call_args

    @patch("tools.semgrep.worker.worker.Path")
    def test_run_semgrep_with_nonexistent_rules(self, mock_path):
        """Test run_semgrep returns error for nonexistent rules path."""
        mock_path.return_value.exists.return_value = False

        success, output = run_semgrep("/tmp/repo", rules_path="/nonexistent/rules.yaml")

        assert success is False
        assert "not found" in output

    @patch("tools.semgrep.worker.worker.subprocess.run")
    def test_run_semgrep_with_args(self, mock_run):
        """Test run_semgrep includes semgrep_args when provided."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        run_semgrep("/tmp/repo", semgrep_args="--json --severity=ERROR")

        call_args = mock_run.call_args[0][0]
        assert "--json" in call_args
        assert "--severity=ERROR" in call_args

    @patch("tools.semgrep.worker.worker.subprocess.run")
    def test_run_semgrep_failure_with_output(self, mock_run):
        """Test run_semgrep includes stdout and stderr in error message."""
        mock_exc = subprocess.CalledProcessError(1, "semgrep", "error")
        mock_exc.stdout = "stdout content"
        mock_exc.stderr = "stderr content"
        mock_run.side_effect = mock_exc

        success, output = run_semgrep("/tmp/repo")

        assert success is False
        assert "stdout content" in output
        assert "stderr content" in output


class TestUploadToS3:
    """Tests for the upload_to_s3 function."""

    @patch("tools.semgrep.worker.worker.boto3")
    def test_upload_success(self, mock_boto3):
        """Test upload_to_s3 returns S3 URL on success."""
        mock_s3_client = MagicMock()
        mock_boto3.client.return_value = mock_s3_client

        result = upload_to_s3("content", "bucket", "key")

        assert result == "s3://bucket/key"
        mock_s3_client.put_object.assert_called_once_with(
            Bucket="bucket", Key="key", Body=b"content"
        )

    @patch("tools.semgrep.worker.worker.boto3")
    def test_upload_failure(self, mock_boto3):
        """Test upload_to_s3 returns None on ClientError."""
        # Create a mock ClientError class
        class MockClientError(Exception):
            def __init__(self, error_dict, operation_name):
                self.error_dict = error_dict
                self.operation_name = operation_name
                super().__init__(f"{operation_name}: {error_dict}")

        import tools.semgrep.worker.worker as worker_module
        original_client_error = worker_module.ClientError
        try:
            # Set ClientError to our mock class
            worker_module.ClientError = MockClientError

            mock_s3_client = MagicMock()
            mock_s3_client.put_object.side_effect = MockClientError(
                {"Error": {"Code": "AccessDenied"}}, "PutObject"
            )
            mock_boto3.client.return_value = mock_s3_client

            result = upload_to_s3("content", "bucket", "key")

            assert result is None
        finally:
            worker_module.ClientError = original_client_error

    @patch("tools.semgrep.worker.worker.boto3")
    @patch("tools.semgrep.worker.worker.ClientError")
    def test_upload_unexpected_error(self, mock_client_error, mock_boto3):
        """Test upload_to_s3 handles unexpected exceptions."""
        # Ensure ClientError is available (not None)
        try:
            from botocore.exceptions import ClientError
            # Ensure ClientError is available in worker module
            import tools.semgrep.worker.worker as worker_module
            worker_module.ClientError = ClientError
        except ImportError:
            pytest.skip("botocore not available")

        mock_s3_client = MagicMock()
        mock_s3_client.put_object.side_effect = ValueError("Unexpected error")
        mock_boto3.client.return_value = mock_s3_client

        result = upload_to_s3("content", "bucket", "key")

        assert result is None

    @patch("tools.semgrep.worker.worker.boto3")
    def test_upload_unexpected_error_without_botocore(self, mock_boto3):
        """Test upload_to_s3 handles unexpected exceptions when ClientError won't match."""
        import tools.semgrep.worker.worker as worker_module

        # Create a custom exception class that won't match ValueError
        class CustomError(Exception):
            pass

        # Set ClientError to a class that won't match ValueError
        # This ensures the except Exception clause is executed
        original_client_error = worker_module.ClientError
        try:
            worker_module.ClientError = CustomError

            mock_s3_client = MagicMock()
            mock_s3_client.put_object.side_effect = ValueError("Unexpected error")
            mock_boto3.client.return_value = mock_s3_client

            result = upload_to_s3("content", "bucket", "key")

            assert result is None
        finally:
            worker_module.ClientError = original_client_error

    def test_upload_without_boto3(self):
        """Test upload_to_s3 returns None when boto3 is not available."""
        with patch("tools.semgrep.worker.worker.boto3", None):
            result = upload_to_s3("content", "bucket", "key")
            assert result is None


class TestReportStatus:
    """Tests for the report_status function."""

    @patch("builtins.__import__")
    def test_report_status_success(self, mock_import):
        """Test report_status returns True on success."""
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_requests.post.return_value = mock_response

        def import_side_effect(name, *args, **kwargs):
            if name == "requests":
                return mock_requests
            return __import__(name, *args, **kwargs)

        mock_import.side_effect = import_side_effect

        result = report_status(
            "http://api:8000", "job-123", "completed", "session-456", {"repo": "test"}
        )

        assert result is True
        mock_requests.post.assert_called_once()
        # Verify session_id is in the payload
        call_args = mock_requests.post.call_args
        assert call_args[1]["json"]["session_id"] == "session-456"

    @patch("builtins.__import__")
    def test_report_status_failure(self, mock_import):
        """Test report_status returns False on failure."""
        mock_requests = MagicMock()
        mock_requests.post.side_effect = Exception("Connection error")

        def import_side_effect(name, *args, **kwargs):
            if name == "requests":
                return mock_requests
            return __import__(name, *args, **kwargs)

        mock_import.side_effect = import_side_effect

        result = report_status("http://api:8000", "job-123", "failed", "session-456", None)

        assert result is False
        # Verify session_id is still in the payload even when result is None
        call_args = mock_requests.post.call_args
        assert call_args[1]["json"]["session_id"] == "session-456"


class TestMain:
    """Tests for the main worker function."""

    @patch.dict(
        os.environ,
        {
            "REPO_URL": "https://github.com/owner/repo",
            "REPO_NAME": "owner/repo",
            "JOB_ID": "job-123",
            "SESSION_ID": "1",
        },
        clear=True,
    )
    @patch("tools.semgrep.worker.worker.report_status")
    @patch("tools.semgrep.worker.worker.upload_to_s3")
    @patch("tools.semgrep.worker.worker.run_semgrep")
    @patch("tools.semgrep.worker.worker.clone_repository")
    @patch("tools.semgrep.worker.worker.tempfile.TemporaryDirectory")
    def test_main_success(
        self,
        mock_tempdir,
        mock_clone,
        mock_semgrep,
        mock_upload,
        mock_report,
    ):
        """Test main function succeeds with all steps."""
        mock_tempdir.return_value.__enter__.return_value = "/tmp/work"
        mock_clone.return_value = True
        mock_semgrep.return_value = (True, "No findings")
        mock_upload.return_value = "s3://bucket/key"

        with patch.dict(
            os.environ,
            {
                "REPO_URL": "https://github.com/owner/repo",
                "REPO_NAME": "owner/repo",
                "JOB_ID": "job-123",
                "SESSION_ID": "1",
                "S3_BUCKET": "test-bucket",
                "API_URL": "http://api:8000",
            },
            clear=True,
        ):
            result = main()

        assert result == 0
        mock_clone.assert_called_once()
        mock_semgrep.assert_called_once()
        # S3 upload only happens if bucket is set
        mock_upload.assert_called_once()
        # report_status only called if API_URL is set
        mock_report.assert_called_once()

    @patch.dict(
        os.environ,
        {
            "REPO_URL": "https://github.com/owner/repo",
            "REPO_NAME": "owner/repo",
            "JOB_ID": "job-123",
            "SESSION_ID": "1",
            "API_URL": "http://api:8000",
        },
        clear=True,
    )
    @patch("tools.semgrep.worker.worker.report_status")
    @patch("tools.semgrep.worker.worker.clone_repository")
    @patch("tools.semgrep.worker.worker.tempfile.TemporaryDirectory")
    def test_main_clone_failure(self, mock_tempdir, mock_clone, mock_report):
        """Test main function fails when clone fails."""
        mock_tempdir.return_value.__enter__.return_value = "/tmp/work"
        mock_clone.return_value = False

        result = main()

        assert result == 1
        # Verify report_status was called when API_URL is set
        mock_report.assert_called_once()

    @patch.dict(os.environ, {}, clear=True)
    def test_main_missing_required_env(self):
        """Test main function fails when required env vars are missing."""
        result = main()
        assert result == 1

    @patch.dict(
        os.environ,
        {
            "REPO_URL": "https://github.com/owner/repo",
            "REPO_NAME": "owner/repo",
            "JOB_ID": "job-123",
            "SESSION_ID": "1",
            "S3_BUCKET": "test-bucket",
        },
        clear=True,
    )
    @patch("tools.semgrep.worker.worker.report_status")
    @patch("tools.semgrep.worker.worker.upload_to_s3")
    @patch("tools.semgrep.worker.worker.run_semgrep")
    @patch("tools.semgrep.worker.worker.clone_repository")
    @patch("tools.semgrep.worker.worker.tempfile.TemporaryDirectory")
    def test_main_with_s3_upload(
        self,
        mock_tempdir,
        mock_clone,
        mock_semgrep,
        mock_upload,
        mock_report,
    ):
        """Test main function uploads to S3 when bucket is configured."""
        mock_tempdir.return_value.__enter__.return_value = "/tmp/work"
        mock_clone.return_value = True
        mock_semgrep.return_value = (True, "No findings")
        mock_upload.return_value = "s3://test-bucket/key"

        with patch.dict(
            os.environ,
            {
                "REPO_URL": "https://github.com/owner/repo",
                "REPO_NAME": "owner/repo",
                "JOB_ID": "job-123",
                "SESSION_ID": "1",
                "S3_BUCKET": "test-bucket",
            },
            clear=True,
        ):
            result = main()

        assert result == 0
        mock_upload.assert_called_once()
        # Verify S3 bucket was passed
        call_args = mock_upload.call_args
        assert call_args[0][1] == "test-bucket"  # bucket is second positional arg


class TestImportErrorHandling:
    """Tests for ImportError handling in worker module."""

    def test_upload_to_s3_with_missing_boto3(self):
        """Test upload_to_s3 handles missing boto3 gracefully."""
        import builtins
        import importlib
        import sys

        # Save original boto3
        original_boto3 = sys.modules.get("boto3")
        original_botocore = sys.modules.get("botocore")

        # Get the real __import__ before any patching
        real_import = __import__

        def side_effect(name, *args, **kwargs):
            if name in ("boto3", "botocore") or name.startswith("botocore."):
                raise ImportError(f"No module named '{name}'")
            return real_import(name, *args, **kwargs)

        try:
            with patch("builtins.__import__", side_effect=side_effect):
                # Remove from sys.modules and reload
                sys.modules.pop("tools.semgrep.worker.worker", None)
                import tools.semgrep.worker.worker as worker_module
                importlib.reload(worker_module)

                # Verify that boto3 is None (ImportError was caught)
                assert worker_module.boto3 is None
                assert worker_module.ClientError is None

                # Test that upload_to_s3 handles None boto3
                # This should not crash even though boto3 is None
                result = worker_module.upload_to_s3("content", "bucket", "key")
                # When boto3 is None, upload_to_s3 should return None
                assert result is None
        finally:
            # Restore by removing from sys.modules - next import will be fresh
            sys.modules.pop("tools.semgrep.worker.worker", None)
