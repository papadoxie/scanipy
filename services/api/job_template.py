"""Kubernetes Job template generator."""

from __future__ import annotations

import uuid
from typing import Any

from .config import APIConfig


def generate_job_name(session_id: int, repo_name: str) -> str:
    """Generate a unique Kubernetes Job name.

    Args:
        session_id: Session ID
        repo_name: Repository name

    Returns:
        Valid Kubernetes resource name
    """
    # Kubernetes names must be lowercase alphanumeric with hyphens
    safe_repo = repo_name.replace("/", "-").replace("_", "-").replace(".", "-").lower()
    # Limit length and add unique suffix
    safe_repo = safe_repo[:40]  # Leave room for session ID and suffix
    unique_suffix = str(uuid.uuid4())[:8]
    return f"semgrep-{session_id}-{safe_repo}-{unique_suffix}"


def create_job_manifest(
    job_name: str,
    repo_url: str,
    repo_name: str,
    session_id: int,
    job_id: str,
    config: APIConfig,
    semgrep_args: str = "",
    rules_path: str | None = None,
    use_pro: bool = False,
    api_url: str | None = None,
) -> dict[str, Any]:
    """Create a Kubernetes Job manifest.

    Args:
        job_name: Name for the Kubernetes Job
        repo_url: Repository URL to clone
        repo_name: Repository name
        session_id: Session ID
        job_id: Unique job ID
        config: API configuration
        semgrep_args: Additional Semgrep arguments
        rules_path: Path to Semgrep rules
        use_pro: Whether to use Semgrep Pro
        api_url: API service URL for status reporting

    Returns:
        Kubernetes Job manifest dictionary
    """
    env_vars: list[dict[str, Any]] = [
        {"name": "REPO_URL", "value": repo_url},
        {"name": "REPO_NAME", "value": repo_name},
        {"name": "JOB_ID", "value": job_id},
        {"name": "SESSION_ID", "value": str(session_id)},
        {"name": "SEMGREP_ARGS", "value": semgrep_args},
        {"name": "USE_PRO", "value": "true" if use_pro else "false"},
    ]

    if config.s3_bucket:
        env_vars.append({"name": "S3_BUCKET", "value": config.s3_bucket})
        env_vars.append({"name": "AWS_REGION", "value": config.aws_region})
        # AWS credentials should come from service account or secrets
        # For now, we'll rely on IAM roles for service accounts

    if rules_path:
        env_vars.append({"name": "RULES_PATH", "value": rules_path})

    if api_url:
        env_vars.append({"name": "API_URL", "value": api_url})

    manifest: dict[str, Any] = {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {
            "name": job_name,
            "namespace": config.k8s_namespace,
            "labels": {
                "app": "scanipy-semgrep",
                "session-id": str(session_id),
                "job-id": job_id,
            },
        },
        "spec": {
            "ttlSecondsAfterFinished": config.job_ttl_seconds,
            "backoffLimit": 2,  # Retry up to 2 times
            "template": {
                "metadata": {
                    "labels": {
                        "app": "scanipy-semgrep",
                        "session-id": str(session_id),
                        "job-id": job_id,
                    },
                },
                "spec": {
                    "restartPolicy": "Never",
                    "containers": [
                        {
                            "name": "semgrep-worker",
                            "image": config.worker_image,
                            "env": env_vars,
                            "resources": {
                                "requests": {
                                    "memory": "1Gi",
                                    "cpu": "500m",
                                },
                                "limits": {
                                    "memory": "4Gi",
                                    "cpu": "2000m",
                                },
                            },
                        },
                    ],
                },
            },
        },
    }

    return manifest
