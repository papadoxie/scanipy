"""Configuration management for the API service."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class APIConfig:
    """Configuration for the API service."""

    # Kubernetes configuration
    k8s_namespace: str = "default"
    worker_image: str = "scanipy-semgrep-worker:latest"

    # S3 configuration
    s3_bucket: str = ""
    aws_region: str = "us-east-1"

    # Database configuration
    db_url: str | None = None  # PostgreSQL connection URL
    db_path: str | None = None  # SQLite path (for local dev)

    # API configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Job configuration
    max_parallel_jobs: int = 10
    job_ttl_seconds: int = 3600  # Time to keep completed jobs

    @classmethod
    def from_env(cls) -> APIConfig:
        """Create configuration from environment variables."""
        return cls(
            k8s_namespace=os.getenv("K8S_NAMESPACE", "default"),
            worker_image=os.getenv("WORKER_IMAGE", "scanipy-semgrep-worker:latest"),
            s3_bucket=os.getenv("S3_BUCKET", ""),
            aws_region=os.getenv("AWS_REGION", "us-east-1"),
            db_url=os.getenv("DATABASE_URL"),
            db_path=os.getenv("DATABASE_PATH"),
            api_host=os.getenv("API_HOST", "0.0.0.0"),
            api_port=int(os.getenv("API_PORT", "8000")),
            max_parallel_jobs=int(os.getenv("MAX_PARALLEL_JOBS", "10")),
            job_ttl_seconds=int(os.getenv("JOB_TTL_SECONDS", "3600")),
        )
