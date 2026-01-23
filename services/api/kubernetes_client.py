"""Kubernetes client wrapper for creating and managing Jobs."""

from __future__ import annotations

import uuid
from typing import Any

try:
    from kubernetes import client  # type: ignore[import-untyped]
    from kubernetes import config as k8s_config  # type: ignore[import-untyped]
    from kubernetes.client.rest import ApiException  # type: ignore[import-untyped]
except ImportError:
    client = None  # type: ignore[assignment, misc]
    k8s_config = None  # type: ignore[assignment, misc]
    ApiException = None  # type: ignore[assignment, misc]

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
        self.batch_api: Any = None
        self.core_api: Any = None
        self._init_client()

    def _init_client(self) -> None:
        """Initialize Kubernetes API clients.

        Attempts to load Kubernetes configuration in the following order:
        1. In-cluster config (for pods running inside Kubernetes)
        2. Kubeconfig file (for local development)

        Raises:
            RuntimeError: If both configuration methods fail
        """
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
        assert self.batch_api is not None  # Type narrowing for mypy

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
        assert self.batch_api is not None  # Type narrowing for mypy

        try:
            job = self.batch_api.read_namespaced_job(
                name=job_name,
                namespace=self.config.k8s_namespace,
            )

            status: dict[str, Any] = {
                "name": job_name,
                "active": job.status.active or 0,
                "succeeded": job.status.succeeded or 0,
                "failed": job.status.failed or 0,
                "conditions": [],
            }

            if job.status.conditions:
                conditions_list: list[dict[str, Any]] = status["conditions"]
                for condition in job.status.conditions:
                    conditions_list.append(
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
        assert self.batch_api is not None  # Type narrowing for mypy

        try:
            self.batch_api.delete_namespaced_job(
                name=job_name,
                namespace=self.config.k8s_namespace,
                propagation_policy="Background",
            )
        except ApiException as exc:
            if exc.status != 404:  # Ignore if already deleted
                raise RuntimeError(f"Failed to delete job: {exc.reason}") from exc

    def count_active_jobs(self, session_id: int) -> int:
        """Count the number of active (running) jobs for a session.

        A job is considered active if it has active pods (status.active > 0).
        This method queries the Kubernetes API to get the current state of all
        jobs labeled with the given session_id.

        Args:
            session_id: Session ID to count jobs for. Jobs are filtered by
                       the 'session-id' label matching this value.

        Returns:
            Number of active jobs for the session. Returns 0 if no active jobs
            are found or if the session has no jobs.

        Raises:
            RuntimeError: If Kubernetes client is not initialized
            RuntimeError: If job listing fails (wraps ApiException)
        """
        if not self.batch_api:
            raise RuntimeError("Kubernetes client not initialized")
        assert self.batch_api is not None  # Type narrowing for mypy

        try:
            # List all jobs with the session-id label
            label_selector = f"session-id={session_id}"
            jobs = self.batch_api.list_namespaced_job(
                namespace=self.config.k8s_namespace,
                label_selector=label_selector,
            )

            # Count jobs that have active pods (still running)
            active_count = 0
            for job in jobs.items:
                if job.status.active and job.status.active > 0:
                    active_count += 1

            return active_count
        except ApiException as exc:
            raise RuntimeError(f"Failed to count active jobs: {exc.reason}") from exc
