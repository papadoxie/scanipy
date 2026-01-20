#!/usr/bin/env python3
"""Standalone worker script for containerized Semgrep analysis.

This script runs in a container and:
1. Clones a repository
2. Runs Semgrep analysis
3. Uploads results to S3
4. Reports status back to API service
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

try:
    import boto3  # type: ignore[import-untyped]
    from botocore.exceptions import ClientError  # type: ignore[import-untyped]
except ImportError:
    boto3 = None  # type: ignore[assignment, misc]
    ClientError = None  # type: ignore[assignment, misc]


def get_env_var(name: str, required: bool = True) -> str:
    """Get environment variable, raise error if required and missing."""
    value = os.getenv(name)
    if required and not value:
        raise ValueError(f"Required environment variable {name} is not set")
    return value or ""


def clone_repository(repo_url: str, clone_path: str) -> bool:
    """Clone repository to the specified path."""
    try:
        subprocess.run(
            ["git", "clone", "--depth=1", repo_url, clone_path],
            check=True,
            capture_output=True,
            text=True,
        )
        return True
    except subprocess.CalledProcessError as exc:
        print(f"ERROR: Failed to clone {repo_url}: {exc}", file=sys.stderr)
        if exc.stdout:
            print(f"STDOUT: {exc.stdout}", file=sys.stderr)
        if exc.stderr:
            print(f"STDERR: {exc.stderr}", file=sys.stderr)
        return False


def run_semgrep(
    repo_path: str,
    semgrep_args: str = "",
    rules_path: str | None = None,
    use_pro: bool = False,
) -> tuple[bool, str]:
    """Execute Semgrep against repository path."""
    try:
        cmd: list[str] = ["semgrep", "scan"]
        if use_pro:
            cmd.append("--pro")
        if rules_path:
            if not Path(rules_path).exists():
                return False, f"Error: Rules file or directory not found: {rules_path}"
            cmd.extend(["--config", rules_path])
        if semgrep_args and semgrep_args.strip():
            cmd.extend(semgrep_args.split())
        cmd.append(repo_path)

        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return True, result.stdout
    except subprocess.CalledProcessError as exc:
        error_msg = f"Error running semgrep: {exc}"
        if exc.stdout:
            error_msg += f"\nOutput: {exc.stdout}"
        if exc.stderr:
            error_msg += f"\nError: {exc.stderr}"
        return False, error_msg


def upload_to_s3(
    content: str,
    bucket: str,
    key: str,
    aws_access_key_id: str | None = None,
    aws_secret_access_key: str | None = None,
    aws_region: str = "us-east-1",
) -> str | None:
    """Upload content to S3 and return the S3 URL."""
    if not boto3:
        print("WARNING: boto3 not available, skipping S3 upload", file=sys.stderr)
        return None

    try:
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=aws_region,
        )
        s3_client.put_object(Bucket=bucket, Key=key, Body=content.encode("utf-8"))
        s3_url = f"s3://{bucket}/{key}"
        print(f"Uploaded results to {s3_url}")
        return s3_url
    except ClientError as exc:
        print(f"ERROR: Failed to upload to S3: {exc}", file=sys.stderr)
        return None
    except Exception as exc:
        print(f"ERROR: Unexpected error uploading to S3: {exc}", file=sys.stderr)
        return None


def report_status(
    api_url: str,
    job_id: str,
    status: str,
    session_id: str,
    result: dict[str, Any] | None = None,
) -> bool:
    """Report job status back to API service.

    Args:
        api_url: Base URL of the API service
        job_id: Kubernetes Job ID
        status: Job status (e.g., 'completed', 'failed')
        session_id: Session ID for tracking results
        result: Optional result dictionary with analysis output

    Returns:
        True if status was reported successfully, False otherwise
    """
    try:
        import requests  # noqa: PLC0415

        payload: dict[str, Any] = {
            "job_id": job_id,
            "status": status,
            "session_id": session_id,
        }
        if result:
            payload["result"] = result

        response = requests.post(
            f"{api_url}/api/v1/jobs/{job_id}/status",
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        return True
    except Exception as exc:
        print(f"WARNING: Failed to report status to API: {exc}", file=sys.stderr)
        return False


def main() -> int:
    """Main worker entry point."""
    # Get required environment variables
    try:
        repo_url = get_env_var("REPO_URL")
        repo_name = get_env_var("REPO_NAME")
        job_id = get_env_var("JOB_ID")
        session_id = get_env_var("SESSION_ID")
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    # Get optional environment variables
    semgrep_args = get_env_var("SEMGREP_ARGS", required=False)
    rules_path = get_env_var("RULES_PATH", required=False) or None
    use_pro = os.getenv("USE_PRO", "false").lower() == "true"
    s3_bucket = get_env_var("S3_BUCKET", required=False) or None
    aws_access_key_id = get_env_var("AWS_ACCESS_KEY_ID", required=False) or None
    aws_secret_access_key = get_env_var("AWS_SECRET_ACCESS_KEY", required=False) or None
    aws_region = get_env_var("AWS_REGION", required=False) or "us-east-1"
    api_url = get_env_var("API_URL", required=False) or None

    # Create temporary directory for cloning
    with tempfile.TemporaryDirectory(prefix="scanipy_worker_") as temp_dir:
        clone_path = str(Path(temp_dir) / repo_name.replace("/", "_"))

        # Clone repository
        print(f"Cloning repository: {repo_url}")
        if not clone_repository(repo_url, clone_path):
            clone_result = {
                "repo": repo_name,
                "url": repo_url,
                "success": False,
                "output": "Failed to clone repository",
                "s3_path": None,
            }
            if api_url:
                report_status(api_url, job_id, "failed", session_id, clone_result)
            print(json.dumps(clone_result))
            return 1

        # Run Semgrep
        print(f"Running Semgrep analysis on {repo_name}")
        success, output = run_semgrep(clone_path, semgrep_args, rules_path, use_pro)

        # Upload to S3 if bucket is configured and analysis succeeded
        s3_url: str | None = None
        if s3_bucket and success:
            s3_key = f"semgrep-results/{session_id}/{repo_name.replace('/', '_')}/results.json"
            s3_url = upload_to_s3(
                output,
                s3_bucket,
                s3_key,
                aws_access_key_id,
                aws_secret_access_key,
                aws_region,
            )

        # Prepare result
        result: dict[str, Any] = {
            "repo": repo_name,
            "url": repo_url,
            "success": success,
            "output": output,
            "s3_path": s3_url,
        }

        # Report status to API if configured
        if api_url:
            status = "completed" if success else "failed"
            report_status(api_url, job_id, status, session_id, result)

        # Output result as JSON for logging
        print(json.dumps(result))
        return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
