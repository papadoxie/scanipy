"""Kubernetes client wrapper for creating and managing Jobs."""

from __future__ import annotations

import uuid
from typing import Any

try:
    from kubernetes import client
    from kubernetes import config as k8s_config
    from kubernetes.client.rest import ApiException
except ImportError:
    client = None  # type: ignore[assignment,misc]
    k8s_config = None  # type: ignore[assignment,misc]
    ApiException = None  # type: ignore[assignment,misc]

from .config import APIConfig
from .job_template import create_job_manifest, generate_job_name


class KubernetesClient:
    """Client for interacting with Kubernetes API."""

    def __init__(self, api_config: APIConfig) -> None:
        """Initialize Kubernetes client.

        Args:
            api_config: API configuration

        Raises:
            ImportError: If kubernetes library is not installed
            RuntimeError: If Kubernetes config cannot be loaded
        """
        if not client:
            raise ImportError(
                "kubernetes library is required. Install with: pip install kubernetes"
            )

        self.config = api_config
        self.batch_api = None
        self.core_api = None
        self._init_client()

    def _init_client(self) -> None:
        """Initialize Kubernetes API clients."""
        try:
            # Try to load in-cluster config first (for pods running in K8s)
            k8s_config.load_incluster_config()
        except Exception:
            try:
                # Fall back to kubeconfig (for local development)
                k8s_config.load_kube_config()
            except Exception as exc:
                raise RuntimeError(
                    f"Failed to load Kubernetes config: {exc}. "
                    "Ensure you're running in a Kubernetes cluster or have kubeconfig configured."
                ) from exc

        self.batch_api = client.BatchV1Api()
        self.core_api = client.CoreV1Api()

    def create_job(
        self,
        repo_url: str,
        repo_name: str,
        session_id: int,
        semgrep_args: str = "",
        rules_path: str | None = None,
        use_pro: bool = False,
        api_url: str | None = None,
    ) -> tuple[str, str]:
        """Create a Kubernetes Job for Semgrep analysis.

        Args:
            repo_url: Repository URL to clone
            repo_name: Repository name
            session_id: Session ID
            semgrep_args: Additional Semgrep arguments
            rules_path: Path to Semgrep rules
            use_pro: Whether to use Semgrep Pro
            api_url: API service URL for status reporting

        Returns:
            Tuple of (job_name, job_id)

        Raises:
            ApiException: If job creation fails
        """
        if not self.batch_api:
            raise RuntimeError("Kubernetes client not initialized")

        job_id = str(uuid.uuid4())
        job_name = generate_job_name(session_id, repo_name)

        manifest = create_job_manifest(
            job_name=job_name,
            repo_url=repo_url,
            repo_name=repo_name,
            session_id=session_id,
            job_id=job_id,
            config=self.config,
            semgrep_args=semgrep_args,
            rules_path=rules_path,
            use_pro=use_pro,
            api_url=api_url,
        )

        try:
            self.batch_api.create_namespaced_job(
                namespace=self.config.k8s_namespace,
                body=manifest,
            )
            return job_name, job_id
        except ApiException as exc:
            raise RuntimeError(f"Failed to create Kubernetes Job {job_name}: {exc.reason}") from exc

    def get_job_status(self, job_name: str) -> dict[str, Any]:
        """Get the status of a Kubernetes Job.

        Args:
            job_name: Name of the Job

        Returns:
            Dictionary with job status information

        Raises:
            ApiException: If job retrieval fails
        """
        if not self.batch_api:
            raise RuntimeError("Kubernetes client not initialized")

        try:
            job = self.batch_api.read_namespaced_job(
                name=job_name,
                namespace=self.config.k8s_namespace,
            )

            status = {
                "name": job_name,
                "active": job.status.active or 0,
                "succeeded": job.status.succeeded or 0,
                "failed": job.status.failed or 0,
                "conditions": [],
            }

            if job.status.conditions:
                for condition in job.status.conditions:
                    status["conditions"].append(
                        {
                            "type": condition.type,
                            "status": condition.status,
                            "message": condition.message or "",
                        }
                    )

            return status
        except ApiException as exc:
            if exc.status == 404:
                return {"name": job_name, "error": "Job not found"}
            raise RuntimeError(f"Failed to get job status: {exc.reason}") from exc

    def delete_job(self, job_name: str) -> None:
        """Delete a Kubernetes Job.

        Args:
            job_name: Name of the Job to delete

        Raises:
            ApiException: If job deletion fails
        """
        if not self.batch_api:
            raise RuntimeError("Kubernetes client not initialized")

        try:
            self.batch_api.delete_namespaced_job(
                name=job_name,
                namespace=self.config.k8s_namespace,
                propagation_policy="Background",
            )
        except ApiException as exc:
            if exc.status != 404:  # Ignore if already deleted
                raise RuntimeError(f"Failed to delete job: {exc.reason}") from exc
