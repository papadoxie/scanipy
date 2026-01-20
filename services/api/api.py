"""FastAPI service for containerized Semgrep analysis."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

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

from tools.semgrep.results_db import ResultsDatabase

from .config import APIConfig
from .kubernetes_client import KubernetesClient


# Pydantic models for request/response (only define if BaseModel is available)
# Use a function to prevent mypy from statically analyzing the condition
def _check_base_model() -> bool:
    """Check if BaseModel is available at runtime."""
    return BaseModel is not None  # type: ignore[comparison-overlap, unused-ignore]


if _check_base_model():

    class CreateScanRequest(BaseModel):
        """Request to create a new scan session."""

        query: str
        rules_path: str | None = None
        use_pro: bool = False

    class AddReposRequest(BaseModel):
        """Request to add repositories to a scan session."""

        repos: list[dict[str, Any]]  # List of repo dicts with 'name' and 'url'

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


if not _check_base_model():
    # Placeholder classes when FastAPI is not available
    # These are intentionally None when FastAPI is not installed
    CreateScanRequest: Any = None  # type: ignore[no-redef]
    AddReposRequest: Any = None  # type: ignore[no-redef]
    JobStatusResponse: Any = None  # type: ignore[no-redef]
    ScanStatusResponse: Any = None  # type: ignore[no-redef]


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
        print(f"WARNING: Failed to initialize Kubernetes client: {exc}")
        print("API will run in local mode only")


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
    if not db:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database not initialized",
        )

    results = db.get_session_results(session_id)
    if not results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    completed = sum(1 for r in results if r.get("success"))
    failed = len(results) - completed

    # Get job statuses if K8s client is available
    jobs: list[JobStatusResponse] = []
    all_jobs_finished = True
    if k8s_client:
        for result in results:
            job_id = result.get("k8s_job_id")
            if job_id:
                # Extract job name from result or construct it
                # In a real implementation, we'd store job_name in the database
                try:
                    job_status = k8s_client.get_job_status(job_id)
                    jobs.append(
                        JobStatusResponse(
                            job_id=job_id,
                            job_name=job_status.get("name", ""),
                            status=job_status,
                        )
                    )
                    # Check if job is still running
                    job_status_str = job_status.get("status", "").lower()
                    if job_status_str not in ("succeeded", "failed", "complete"):
                        all_jobs_finished = False
                except Exception:
                    # If we can't get job status, the job might have been cleaned up
                    # Since we have a result in the database, the job finished (success or failure)
                    # Assume it's finished if we have a result
                    pass  # Job might not exist anymore
    else:
        # If K8s client is not available, we can't check job statuses
        # Results are only saved when jobs finish (via update_job_status)
        # So if we have results, those jobs are done
        # However, we don't know if there are more jobs that haven't reported yet
        # For now, assume scan is completed when we have results
        # (This is a limitation - ideally we'd track expected total repos)
        all_jobs_finished = len(results) > 0

    # Scan is completed when all jobs have finished (regardless of success/failure)
    # A job is finished when it has a result in the database (success or failure)
    # If we have results and all K8s jobs have finished status, the scan is complete
    # Note: This assumes we have results for all expected repos, which we don't track
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
        List of analysis results
    """
    if not db:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database not initialized",
        )

    results = db.get_session_results(session_id)
    if not results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    return results


@app.post("/api/v1/scans/{session_id}/repos")
async def add_repos_to_scan(
    session_id: int,
    request: AddReposRequest,
) -> dict[str, Any]:
    """Add repositories to a scan session and create Kubernetes Jobs.

    Args:
        session_id: Session ID
        request: Request with list of repositories

    Returns:
        Information about created jobs
    """
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
    sessions = db.get_all_sessions()
    session_info = next((s for s in sessions if s["id"] == session_id), None)
    if not session_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    created_jobs: list[dict[str, Any]] = []

    for repo in request.repos:
        repo_name = repo.get("name")
        repo_url = repo.get("url")

        if not repo_name or not repo_url:
            continue

        # Check if already analyzed
        analyzed = db.get_analyzed_repos(session_id)
        if repo_name in analyzed:
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

            created_jobs.append(
                {
                    "repo_name": repo_name,
                    "job_name": job_name,
                    "job_id": job_id,
                }
            )
        except Exception as exc:
            # Log error but continue with other repos
            print(f"Failed to create job for {repo_name}: {exc}")

    return {
        "session_id": session_id,
        "jobs_created": len(created_jobs),
        "jobs": created_jobs,
    }


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

        if session_id <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"session_id must be greater than 0, got: {session_id}",
            )

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

        db.save_result(
            session_id=session_id,
            repo_name=repo_name,
            repo_url=repo_url,
            success=success,
            output=output,
            s3_path=s3_path,
            k8s_job_id=job_id,
        )

    return {"status": "ok", "job_id": job_id}


if __name__ == "__main__":
    import uvicorn

    config = APIConfig.from_env()
    init_api(config)

    uvicorn.run(app, host=config.api_host, port=config.api_port)
