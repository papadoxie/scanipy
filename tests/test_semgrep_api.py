"""Tests for the Semgrep API service."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from services.api.config import APIConfig
from services.api.job_template import create_job_manifest, generate_job_name
from services.api.kubernetes_client import KubernetesClient


class TestAPIConfig:
    """Tests for APIConfig."""

    def test_from_env_defaults(self):
        """Test APIConfig.from_env uses defaults when env vars not set."""
        with patch.dict("os.environ", {}, clear=True):
            config = APIConfig.from_env()
            assert config.k8s_namespace == "default"
            assert config.worker_image == "scanipy-semgrep-worker:latest"
            assert config.api_port == 8000

    def test_from_env_custom_values(self):
        """Test APIConfig.from_env reads custom values from env."""
        env_vars = {
            "K8S_NAMESPACE": "scanipy",
            "WORKER_IMAGE": "custom-image:tag",
            "API_PORT": "9000",
            "S3_BUCKET": "my-bucket",
        }
        with patch.dict("os.environ", env_vars):
            config = APIConfig.from_env()
            assert config.k8s_namespace == "scanipy"
            assert config.worker_image == "custom-image:tag"
            assert config.api_port == 9000
            assert config.s3_bucket == "my-bucket"


class TestJobTemplate:
    """Tests for job template generation."""

    def test_generate_job_name(self):
        """Test generate_job_name creates valid K8s resource name."""
        name = generate_job_name(1, "owner/repo")
        assert name.startswith("semgrep-1-")
        assert "owner-repo" in name.lower()
        # K8s names must be lowercase alphanumeric with hyphens
        assert name.islower() or name.replace("-", "").replace("_", "").isalnum()

    def test_generate_job_name_special_chars(self):
        """Test generate_job_name handles special characters."""
        name = generate_job_name(1, "owner/repo_name.with-dots")
        # Should sanitize special characters
        assert "/" not in name
        assert "." not in name
        assert "_" not in name or name.replace("-", "").replace("_", "").isalnum()

    def test_create_job_manifest(self):
        """Test create_job_manifest creates valid Job manifest."""
        config = APIConfig(
            k8s_namespace="test",
            worker_image="test-image:latest",
            s3_bucket="test-bucket",
        )

        manifest = create_job_manifest(
            job_name="test-job",
            repo_url="https://github.com/owner/repo",
            repo_name="owner/repo",
            session_id=1,
            job_id="job-123",
            config=config,
        )

        assert manifest["apiVersion"] == "batch/v1"
        assert manifest["kind"] == "Job"
        assert manifest["metadata"]["name"] == "test-job"
        assert manifest["metadata"]["namespace"] == "test"
        assert manifest["spec"]["template"]["spec"]["containers"][0]["image"] == "test-image:latest"

    def test_create_job_manifest_with_env_vars(self):
        """Test create_job_manifest includes environment variables."""
        config = APIConfig(
            k8s_namespace="test",
            worker_image="test-image:latest",
            s3_bucket="test-bucket",
        )

        manifest = create_job_manifest(
            job_name="test-job",
            repo_url="https://github.com/owner/repo",
            repo_name="owner/repo",
            session_id=1,
            job_id="job-123",
            config=config,
            semgrep_args="--json",
            rules_path="/rules.yaml",
            use_pro=True,
        )

        env_vars = {
            env["name"]: env["value"]
            for env in manifest["spec"]["template"]["spec"]["containers"][0]["env"]
        }

        assert env_vars["REPO_URL"] == "https://github.com/owner/repo"
        assert env_vars["REPO_NAME"] == "owner/repo"
        assert env_vars["JOB_ID"] == "job-123"
        assert env_vars["SESSION_ID"] == "1"
        assert env_vars["SEMGREP_ARGS"] == "--json"
        assert env_vars["RULES_PATH"] == "/rules.yaml"
        assert env_vars["USE_PRO"] == "true"
        assert env_vars["S3_BUCKET"] == "test-bucket"

    def test_create_job_manifest_with_api_url(self):
        """Test create_job_manifest includes API_URL when provided."""
        config = APIConfig(
            k8s_namespace="test",
            worker_image="test-image:latest",
        )

        manifest = create_job_manifest(
            job_name="test-job",
            repo_url="https://github.com/owner/repo",
            repo_name="owner/repo",
            session_id=1,
            job_id="job-123",
            config=config,
            api_url="http://api:8000",
        )

        env_vars = {
            env["name"]: env["value"]
            for env in manifest["spec"]["template"]["spec"]["containers"][0]["env"]
        }

        assert env_vars.get("API_URL") == "http://api:8000"


class TestKubernetesClient:
    """Tests for KubernetesClient."""

    @patch("services.api.kubernetes_client.k8s_config")
    @patch("services.api.kubernetes_client.client")
    def test_init_loads_incluster_config(self, mock_client, mock_k8s_config):
        """Test KubernetesClient loads in-cluster config first."""
        mock_k8s_config.load_incluster_config.return_value = None
        config = APIConfig()

        client = KubernetesClient(config)

        assert client is not None
        mock_k8s_config.load_incluster_config.assert_called_once()

    @patch("services.api.kubernetes_client.k8s_config")
    @patch("services.api.kubernetes_client.client")
    def test_init_falls_back_to_kubeconfig(self, mock_client, mock_k8s_config):
        """Test KubernetesClient falls back to kubeconfig if in-cluster fails."""
        mock_k8s_config.load_incluster_config.side_effect = Exception("Not in cluster")
        mock_k8s_config.load_kube_config.return_value = None
        config = APIConfig()

        client = KubernetesClient(config)

        assert client is not None
        mock_k8s_config.load_kube_config.assert_called_once()

    @patch("services.api.kubernetes_client.k8s_config")
    @patch("services.api.kubernetes_client.client")
    def test_init_raises_on_config_failure(self, mock_client, mock_k8s_config):
        """Test KubernetesClient raises RuntimeError when config loading fails."""
        mock_k8s_config.load_incluster_config.side_effect = Exception("Not in cluster")
        mock_k8s_config.load_kube_config.side_effect = Exception("No kubeconfig")
        config = APIConfig()

        with pytest.raises(RuntimeError, match="Failed to load Kubernetes config"):
            KubernetesClient(config)

    @patch("services.api.kubernetes_client.k8s_config")
    @patch("services.api.kubernetes_client.client")
    def test_create_job(self, mock_client, mock_k8s_config):
        """Test create_job creates a Kubernetes Job."""
        mock_k8s_config.load_incluster_config.return_value = None
        mock_batch_api = MagicMock()
        mock_client.BatchV1Api.return_value = mock_batch_api
        config = APIConfig(k8s_namespace="test")

        client = KubernetesClient(config)
        job_name, job_id = client.create_job(
            repo_url="https://github.com/owner/repo",
            repo_name="owner/repo",
            session_id=1,
        )

        assert job_name is not None
        assert job_id is not None
        mock_batch_api.create_namespaced_job.assert_called_once()

    @patch("services.api.kubernetes_client.k8s_config")
    @patch("services.api.kubernetes_client.client")
    def test_get_job_status(self, mock_client, mock_k8s_config):
        """Test get_job_status retrieves job status."""
        mock_k8s_config.load_incluster_config.return_value = None
        mock_batch_api = MagicMock()
        mock_job = MagicMock()
        mock_job.status.active = 1
        mock_job.status.succeeded = 0
        mock_job.status.failed = 0
        mock_job.status.conditions = []
        mock_batch_api.read_namespaced_job.return_value = mock_job
        mock_client.BatchV1Api.return_value = mock_batch_api
        config = APIConfig(k8s_namespace="test")

        client = KubernetesClient(config)
        status = client.get_job_status("test-job")

        assert status["name"] == "test-job"
        assert status["active"] == 1
        mock_batch_api.read_namespaced_job.assert_called_once_with(
            name="test-job", namespace="test"
        )

    @patch("services.api.kubernetes_client.k8s_config")
    @patch("services.api.kubernetes_client.client")
    def test_delete_job(self, mock_client, mock_k8s_config):
        """Test delete_job deletes a Kubernetes Job."""
        mock_k8s_config.load_incluster_config.return_value = None
        mock_batch_api = MagicMock()
        mock_client.BatchV1Api.return_value = mock_batch_api
        config = APIConfig(k8s_namespace="test")

        client = KubernetesClient(config)
        client.delete_job("test-job")

        mock_batch_api.delete_namespaced_job.assert_called_once_with(
            name="test-job",
            namespace="test",
            propagation_policy="Background",
        )

    def test_init_raises_import_error_without_kubernetes(self):
        """Test KubernetesClient raises ImportError when kubernetes not available."""
        with patch("services.api.kubernetes_client.client", None):
            config = APIConfig()
            with pytest.raises(ImportError, match="kubernetes library is required"):
                KubernetesClient(config)

    @patch("services.api.kubernetes_client.k8s_config")
    @patch("services.api.kubernetes_client.client")
    def test_create_job_raises_when_not_initialized(self, mock_client, mock_k8s_config):
        """Test create_job raises RuntimeError when batch_api is None."""
        mock_k8s_config.load_incluster_config.return_value = None
        mock_client.BatchV1Api.return_value = None
        config = APIConfig()

        client = KubernetesClient(config)
        client.batch_api = None  # Simulate uninitialized state

        with pytest.raises(RuntimeError, match="Kubernetes client not initialized"):
            client.create_job(
                repo_url="https://github.com/owner/repo",
                repo_name="owner/repo",
                session_id=1,
            )

    @patch("services.api.kubernetes_client.k8s_config")
    @patch("services.api.kubernetes_client.client")
    def test_create_job_handles_api_exception(self, mock_client, mock_k8s_config):
        """Test create_job handles ApiException."""
        from kubernetes.client.rest import ApiException

        mock_k8s_config.load_incluster_config.return_value = None
        mock_batch_api = MagicMock()
        # Create a real ApiException instance
        mock_exc = ApiException(status=403, reason="Forbidden")
        mock_batch_api.create_namespaced_job.side_effect = mock_exc
        mock_client.BatchV1Api.return_value = mock_batch_api
        config = APIConfig()

        client = KubernetesClient(config)
        with pytest.raises(RuntimeError, match="Failed to create Kubernetes Job"):
            client.create_job(
                repo_url="https://github.com/owner/repo",
                repo_name="owner/repo",
                session_id=1,
            )

    @patch("services.api.kubernetes_client.k8s_config")
    @patch("services.api.kubernetes_client.client")
    def test_get_job_status_raises_when_not_initialized(self, mock_client, mock_k8s_config):
        """Test get_job_status raises RuntimeError when batch_api is None."""
        mock_k8s_config.load_incluster_config.return_value = None
        mock_client.BatchV1Api.return_value = None
        config = APIConfig()

        client = KubernetesClient(config)
        client.batch_api = None  # Simulate uninitialized state

        with pytest.raises(RuntimeError, match="Kubernetes client not initialized"):
            client.get_job_status("test-job")

    @patch("services.api.kubernetes_client.k8s_config")
    @patch("services.api.kubernetes_client.client")
    def test_get_job_status_with_conditions(self, mock_client, mock_k8s_config):
        """Test get_job_status includes job conditions."""
        from unittest.mock import Mock

        mock_k8s_config.load_incluster_config.return_value = None
        mock_batch_api = MagicMock()
        mock_job = MagicMock()
        mock_job.status.active = 0
        mock_job.status.succeeded = 1
        mock_job.status.failed = 0
        mock_condition = Mock()
        mock_condition.type = "Complete"
        mock_condition.status = "True"
        mock_condition.message = "Job completed"
        mock_job.status.conditions = [mock_condition]
        mock_batch_api.read_namespaced_job.return_value = mock_job
        mock_client.BatchV1Api.return_value = mock_batch_api
        config = APIConfig(k8s_namespace="test")

        client = KubernetesClient(config)
        status = client.get_job_status("test-job")

        assert status["succeeded"] == 1
        assert len(status["conditions"]) == 1
        assert status["conditions"][0]["type"] == "Complete"

    @patch("services.api.kubernetes_client.k8s_config")
    @patch("services.api.kubernetes_client.client")
    def test_get_job_status_handles_404(self, mock_client, mock_k8s_config):
        """Test get_job_status handles 404 (job not found)."""
        from kubernetes.client.rest import ApiException

        mock_k8s_config.load_incluster_config.return_value = None
        mock_batch_api = MagicMock()
        # Create a real ApiException instance with 404 status
        mock_exception = ApiException(status=404, reason="Not found")
        mock_batch_api.read_namespaced_job.side_effect = mock_exception
        mock_client.BatchV1Api.return_value = mock_batch_api
        config = APIConfig()

        client = KubernetesClient(config)
        status = client.get_job_status("nonexistent-job")

        assert status["name"] == "nonexistent-job"
        assert "error" in status

    @patch("services.api.kubernetes_client.k8s_config")
    @patch("services.api.kubernetes_client.client")
    def test_get_job_status_handles_other_errors(self, mock_client, mock_k8s_config):
        """Test get_job_status handles non-404 ApiException."""
        from kubernetes.client.rest import ApiException

        mock_k8s_config.load_incluster_config.return_value = None
        mock_batch_api = MagicMock()
        # Create a real ApiException instance with 500 status
        mock_exception = ApiException(status=500, reason="Internal Server Error")
        mock_batch_api.read_namespaced_job.side_effect = mock_exception
        mock_client.BatchV1Api.return_value = mock_batch_api
        config = APIConfig()

        client = KubernetesClient(config)
        with pytest.raises(RuntimeError, match="Failed to get job status"):
            client.get_job_status("test-job")

    @patch("services.api.kubernetes_client.k8s_config")
    @patch("services.api.kubernetes_client.client")
    def test_delete_job_raises_when_not_initialized(self, mock_client, mock_k8s_config):
        """Test delete_job raises RuntimeError when batch_api is None."""
        mock_k8s_config.load_incluster_config.return_value = None
        mock_client.BatchV1Api.return_value = None
        config = APIConfig()

        client = KubernetesClient(config)
        client.batch_api = None  # Simulate uninitialized state

        with pytest.raises(RuntimeError, match="Kubernetes client not initialized"):
            client.delete_job("test-job")

    @patch("services.api.kubernetes_client.k8s_config")
    @patch("services.api.kubernetes_client.client")
    def test_delete_job_handles_404(self, mock_client, mock_k8s_config):
        """Test delete_job ignores 404 (job already deleted)."""
        from unittest.mock import Mock

        mock_k8s_config.load_incluster_config.return_value = None
        mock_batch_api = MagicMock()
        mock_exc = Mock()
        mock_exc.status = 404
        mock_batch_api.delete_namespaced_job.side_effect = mock_exc
        mock_client.BatchV1Api.return_value = mock_batch_api
        config = APIConfig()

        # Mock ApiException
        with patch("services.api.kubernetes_client.ApiException", Exception):
            client = KubernetesClient(config)
            # Should not raise, 404 is ignored
            client.delete_job("nonexistent-job")

    @patch("services.api.kubernetes_client.k8s_config")
    @patch("services.api.kubernetes_client.client")
    def test_delete_job_handles_other_errors(self, mock_client, mock_k8s_config):
        """Test delete_job raises RuntimeError for non-404 errors."""
        from kubernetes.client.rest import ApiException

        mock_k8s_config.load_incluster_config.return_value = None
        mock_batch_api = MagicMock()
        # Create a real ApiException instance with 500 status
        mock_exception = ApiException(status=500, reason="Internal Server Error")
        mock_batch_api.delete_namespaced_job.side_effect = mock_exception
        mock_client.BatchV1Api.return_value = mock_batch_api
        config = APIConfig()

        client = KubernetesClient(config)
        with pytest.raises(RuntimeError, match="Failed to delete job"):
            client.delete_job("test-job")
