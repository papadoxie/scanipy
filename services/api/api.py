"""FastAPI service for containerized Semgrep analysis."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from fastapi import FastAPI, HTTPException, status
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel
else:
    try:
        from fastapi import FastAPI, HTTPException, status
        from fastapi.responses import JSONResponse
        from pydantic import BaseModel
    except ImportError:
        FastAPI = None  # type: ignore[assignment, misc]
        HTTPException = None  # type: ignore[assignment, misc]
        status = None  # type: ignore[assignment, misc]
        JSONResponse = None  # type: ignore[assignment, misc]
        BaseModel = None  # type: ignore[assignment, misc]

from tools.semgrep.results_db import ResultsDatabase  # noqa: E402

from .config import APIConfig  # noqa: E402
from .kubernetes_client import KubernetesClient  # noqa: E402
from .validators import (  # noqa: E402
    validate_repo_name,
    validate_repo_url,
    validate_rules_path,
    validate_session_id,
)


# Pydantic models for request/response (only define if BaseModel is available)
# Use a function to prevent mypy from statically analyzing the condition
def _check_base_model() -> bool:
    """Check if BaseModel is available at runtime."""
    return BaseModel is not None  # type: ignore[comparison-overlap, unused-ignore]


if _check_base_model():
    from pydantic import field_validator

    class CreateScanRequest(BaseModel):
        """Request to create a new scan session."""

        query: str
        rules_path: str | None = None
        use_pro: bool = False

        @field_validator("rules_path")
        @classmethod
        def validate_rules_path_field(cls, v: str | None) -> str | None:
            """Validate rules_path field."""
            return validate_rules_path(v)

    class AddReposRequest(BaseModel):
        """Request to add repositories to a scan session."""

        repos: list[dict[str, Any]]  # List of repo dicts with 'name' and 'url'

        @field_validator("repos")
        @classmethod
        def validate_repos(cls, v: list[dict[str, Any]]) -> list[dict[str, Any]]:
            """Validate repository entries."""
            for repo in v:
                repo_name = repo.get("name")
                repo_url = repo.get("url")
                if repo_name:
                    try:
                        validate_repo_name(repo_name)
                    except ValueError as exc:
                        raise ValueError(f"Invalid repo name in repos list: {exc}") from exc
                if repo_url:
                    try:
                        validate_repo_url(repo_url)
                    except ValueError as exc:
                        raise ValueError(f"Invalid repo URL in repos list: {exc}") from exc
            return v

    class JobStatusResponse(BaseModel):
        """Response for job status."""

        job_id: str
        job_name: str
        status: dict[str, Any]

    class ScanStatusResponse(BaseModel):
        """Response for scan session status."""

        session_id: int
        status: str
        total_repos: int
        completed_repos: int
        failed_repos: int
        jobs: list[JobStatusResponse]

    class JobInfo(BaseModel):
        """Information about a created Kubernetes job."""

        repo_name: str
        job_name: str
        job_id: str

    class AddReposResponse(BaseModel):
        """Response for adding repositories to a scan."""

        session_id: int
        jobs_created: int
        jobs: list[JobInfo]
        queued_repos: int
        queued_repos_list: list[dict[str, str]]
        max_parallel_jobs: int
        active_jobs: int


if not _check_base_model():
    # Placeholder classes when FastAPI is not available
    # These are intentionally None when FastAPI is not installed
    CreateScanRequest: Any = None  # type: ignore[no-redef]
    AddReposRequest: Any = None  # type: ignore[no-redef]
    JobStatusResponse: Any = None  # type: ignore[no-redef]
    ScanStatusResponse: Any = None  # type: ignore[no-redef]
    JobInfo: Any = None  # type: ignore[no-redef]
    AddReposResponse: Any = None  # type: ignore[no-redef]


# Initialize FastAPI app
# Use a function to prevent mypy from statically analyzing the condition
def _check_fastapi() -> bool:
    """Check if FastAPI is available at runtime."""
    return FastAPI is not None  # type: ignore[comparison-overlap, unused-ignore]


if _check_fastapi():
    app = FastAPI(title="Scanipy Semgrep API", version="1.0.0")
else:
    # Create a dummy app object with no-op decorators when FastAPI is not available
    class DummyApp:
        """Dummy app object when FastAPI is not available."""

        def post(self, *_args: Any, **_kwargs: Any) -> Any:
            """No-op post decorator."""
            return lambda func: func

        def get(self, *_args: Any, **_kwargs: Any) -> Any:
            """No-op get decorator."""
            return lambda func: func

    app: Any = DummyApp()  # type: ignore[no-redef]


# Global state (would use dependency injection in production)
api_config: APIConfig | None = None
k8s_client: KubernetesClient | None = None
db: ResultsDatabase | None = None


def init_api(config: APIConfig) -> None:
    """Initialize the API with configuration.

    Args:
        config: API configuration
    """
    global api_config, k8s_client, db  # noqa: PLW0603

    api_config = config

    # Initialize database
    if config.db_url:
        db = ResultsDatabase(db_url=config.db_url)
    elif config.db_path:
        db = ResultsDatabase(db_path=config.db_path)
    else:
        raise ValueError("Either db_url or db_path must be provided")

    # Initialize Kubernetes client
    try:
        k8s_client = KubernetesClient(config)
    except Exception as exc:
        logger.warning("Failed to initialize Kubernetes client: %s", exc)
        logger.warning("API will run in local mode only")


@app.post("/api/v1/scans", response_model=dict[str, Any])
async def create_scan(request: CreateScanRequest) -> dict[str, Any]:
    """Create a new scan session.

    Args:
        request: Scan creation request

    Returns:
        Session information
    """
    if not db:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database not initialized",
        )

    session_id = db.create_session(
        query=request.query,
        rules_path=request.rules_path,
        use_pro=request.use_pro,
    )

    return {
        "session_id": session_id,
        "query": request.query,
        "status": "pending",
    }


@app.get("/api/v1/scans/{session_id}", response_model=ScanStatusResponse)
async def get_scan_status(session_id: int) -> ScanStatusResponse:
    """Get the status of a scan session.

    Args:
        session_id: Session ID

    Returns:
        Scan status information
    """
    # Validate session_id
    try:
        session_id = validate_session_id(session_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if not db:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database not initialized",
        )

    # Check if session exists in analysis_sessions table
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    # Get results (may be empty if workers haven't reported yet)
    results = db.get_session_results(session_id)

    completed = sum(1 for r in results if r.get("success"))
    failed = len(results) - completed

    # Get job statuses if K8s client is available
    jobs: list[JobStatusResponse] = []
    all_jobs_finished = True
    if k8s_client:
        for result in results:
            job_name = result.get("k8s_job_name")
            job_id = result.get("k8s_job_id")
            # Use job_name if available, otherwise fall back to job_id (for backward compatibility)
            # But job_id is a UUID and won't work with get_job_status, so we need job_name
            if job_name:
                try:
                    job_status = k8s_client.get_job_status(job_name)
                    jobs.append(
                        JobStatusResponse(
                            job_id=job_id or "",
                            job_name=job_name,
                            status=job_status,
                        )
                    )
                    # Check if job is still running
                    # get_job_status returns: name, active, succeeded, failed, conditions
                    # A job is finished if succeeded > 0 or failed > 0
                    # A job is still running if active > 0
                    active = job_status.get("active", 0)
                    succeeded = job_status.get("succeeded", 0)
                    job_failed_pods = job_status.get("failed", 0)

                    # Job is finished if it has succeeded or failed pods
                    # Job is still running if it has active pods
                    is_finished = (succeeded > 0 or job_failed_pods > 0) and active == 0
                    if not is_finished:
                        all_jobs_finished = False
                except Exception as exc:
                    # If we can't get job status, the job might have been cleaned up
                    # Since we have a result in the database, the job finished (success or failure)
                    # Log the exception for debugging but assume it's finished if we have a result
                    logger.warning(
                        "Failed to get job status for job_name=%s, session_id=%s: %s",
                        job_name,
                        session_id,
                        exc,
                        exc_info=True,
                    )
                    # Job might not exist anymore, but we have a result so assume finished
            elif job_id:
                # Legacy case: we have job_id but no job_name
                # This shouldn't happen for new jobs, but handle gracefully
                # We can't look up the job without the name, so assume it's finished
                # if we have a result with output
                if result.get("output"):
                    # Has result, assume finished
                    pass
                else:
                    # Pending job without job_name - can't check status
                    all_jobs_finished = False
    elif not k8s_client:
        # If K8s client is not available, we can't check job statuses via K8s API
        # We need to determine completion based on database results only
        # When jobs are created, they create database entries with empty output (pending)
        # When jobs complete, update_job_status updates them with actual output
        # So a result with empty output means the job is still pending
        if len(results) == 0:
            # No results yet - scan is definitely not complete
            all_jobs_finished = False
        else:
            # Check if all results have non-empty output (meaning all jobs have reported)
            # A result with empty output means the job is still pending
            all_results_finished = all(result.get("output", "") != "" for result in results)
            all_jobs_finished = all_results_finished

    # Scan is completed when all jobs have finished (regardless of success/failure)
    # A job is finished when it has a result in the database with non-empty output
    # (or when K8s status confirms it's finished, if K8s client is available)
    scan_completed = len(results) > 0 and all_jobs_finished

    return ScanStatusResponse(
        session_id=session_id,
        status="completed" if scan_completed else "running",
        total_repos=len(results),
        completed_repos=completed,
        failed_repos=failed,
        jobs=jobs,
    )


@app.get("/api/v1/scans/{session_id}/results", response_model=list[dict[str, Any]])
async def get_scan_results(session_id: int) -> list[dict[str, Any]]:
    """Get all results for a scan session.

    Args:
        session_id: Session ID

    Returns:
        List of analysis results (may be empty if workers haven't reported yet)
    """
    # Validate session_id
    try:
        session_id = validate_session_id(session_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if not db:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database not initialized",
        )

    # Check if session exists in analysis_sessions table
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    # Get results (may be empty if workers haven't reported yet)
    return db.get_session_results(session_id)


@app.post("/api/v1/scans/{session_id}/repos", response_model=AddReposResponse)
async def add_repos_to_scan(
    session_id: int,
    request: AddReposRequest,
) -> AddReposResponse:
    """Add repositories to a scan session and create Kubernetes Jobs.

    Args:
        session_id: Session ID
        request: Request with list of repositories

    Returns:
        Information about created jobs
    """
    # Validate session_id
    try:
        session_id = validate_session_id(session_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if not db:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database not initialized",
        )

    if not k8s_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Kubernetes client not available",
        )

    if not api_config:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API configuration not initialized",
        )

    # Get session info to determine rules_path and use_pro
    session_info = db.get_session(session_id)
    if not session_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    created_jobs: list[dict[str, Any]] = []
    queued_repos: list[dict[str, Any]] = []

    # Get analyzed repos once before the loop to avoid N+1 queries
    analyzed = db.get_analyzed_repos(session_id)

    max_parallel = api_config.max_parallel_jobs

    for repo in request.repos:
        repo_name = repo.get("name")
        repo_url = repo.get("url")

        if not repo_name or not repo_url:
            continue

        # Check if already analyzed (using pre-fetched set)
        if repo_name in analyzed:
            continue

        # Use database-level locking to atomically check and reserve a job slot
        # This prevents race conditions when multiple requests create jobs simultaneously
        slot_available, _ = db.acquire_job_slot(
            session_id=session_id,
            max_parallel=max_parallel,
            k8s_client=k8s_client,
        )

        if not slot_available:
            # Queue this repo for later (when jobs complete)
            queued_repos.append({"name": repo_name, "url": repo_url})
            continue

        # Create Kubernetes Job
        try:
            job_name, job_id = k8s_client.create_job(
                repo_url=repo_url,
                repo_name=repo_name,
                session_id=session_id,
                semgrep_args="",  # Could be passed in request
                rules_path=session_info.get("rules_path"),
                use_pro=session_info.get("use_pro", False),
                api_url=f"http://{api_config.api_host}:{api_config.api_port}",
            )

            # Store pending job info in database (job will be updated when worker reports back)
            # Store as a pending result entry so we can track job_name
            db.save_result(
                session_id=session_id,
                repo_name=repo_name,
                repo_url=repo_url,
                success=False,  # Pending - will be updated when worker reports
                output="",  # Pending - will be updated when worker reports
                k8s_job_id=job_id,
                k8s_job_name=job_name,
            )

            created_jobs.append(
                {
                    "repo_name": repo_name,
                    "job_name": job_name,
                    "job_id": job_id,
                }
            )
        except Exception as exc:
            # Log error but continue with other repos
            logger.error("Failed to create job for %s: %s", repo_name, exc, exc_info=True)

    # Get final active jobs count for response
    try:
        final_active_jobs = k8s_client.count_active_jobs(session_id)
    except Exception as exc:
        logger.warning("Failed to get final active jobs count: %s", exc)
        # Estimate based on created jobs (conservative)
        final_active_jobs = len(created_jobs)

    # Convert created_jobs to JobInfo objects
    job_infos: list[JobInfo] = []
    for job in created_jobs:
        job_infos.append(
            JobInfo(
                repo_name=job["repo_name"],
                job_name=job["job_name"],
                job_id=job["job_id"],
            )
        )

    return AddReposResponse(
        session_id=session_id,
        jobs_created=len(created_jobs),
        jobs=job_infos,
        queued_repos=len(queued_repos),
        queued_repos_list=queued_repos,  # Include list for CLI to retry
        max_parallel_jobs=max_parallel,
        active_jobs=final_active_jobs,
    )


@app.get("/health")
async def health_check() -> dict[str, Any]:
    """Health check endpoint."""
    return {"status": "healthy", "service": "scanipy-api"}


@app.post("/api/v1/jobs/{job_id}/status")
async def update_job_status(
    job_id: str,
    status_update: dict[str, Any],
) -> dict[str, Any]:
    """Update job status (called by worker containers).

    Args:
        job_id: Job ID
        status_update: Status update from worker

    Returns:
        Confirmation
    """
    if not db:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database not initialized",
        )

    result = status_update.get("result")

    if result:
        # Validate session_id is present and valid (must be > 0)
        session_id_raw = status_update.get("session_id")
        if session_id_raw is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required field 'session_id' in status update",
            )

        try:
            session_id = int(session_id_raw)
        except (ValueError, TypeError) as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid session_id value: {session_id_raw}",
            ) from err

        # Validate session_id using validator
        try:
            session_id = validate_session_id(session_id)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc

        repo_name = result.get("repo")
        repo_url = result.get("url", "")
        success = result.get("success", False)
        output = result.get("output", "")
        s3_path = result.get("s3_path")

        # Validate required fields before saving
        if not repo_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required field 'repo' in result",
            )

        # Validate repo_name format
        try:
            validate_repo_name(repo_name)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid repo name: {exc}",
            ) from exc

        # Validate repo_url if provided
        if repo_url:
            try:
                validate_repo_url(repo_url)
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid repo URL: {exc}",
                ) from exc

        # Get existing job_name from database if available (stored when job was created)
        # If not available, we can't look it up, but that's okay - job_name is optional
        existing_results = db.get_session_results(session_id)
        job_name = None
        for existing_result in existing_results:
            if existing_result.get("repo") == repo_name:
                job_name = existing_result.get("k8s_job_name")
                break

        db.save_result(
            session_id=session_id,
            repo_name=repo_name,
            repo_url=repo_url,
            success=success,
            output=output,
            s3_path=s3_path,
            k8s_job_id=job_id,
            k8s_job_name=job_name,  # Preserve job_name if it was stored when job was created
        )

    return {"status": "ok", "job_id": job_id}


if __name__ == "__main__":
    import uvicorn

    config = APIConfig.from_env()
    init_api(config)

    uvicorn.run(app, host=config.api_host, port=config.api_port)
