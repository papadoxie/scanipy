"""Database module for storing and retrieving Semgrep analysis results.

This module provides SQLite and PostgreSQL-based persistence for Semgrep analysis results,
allowing analysis to be resumed if interrupted.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from psycopg2.extensions import connection as pg_connection_type
else:
    pg_connection_type = Any

try:
    import psycopg2
    from psycopg2 import sql
    from psycopg2.extensions import connection as pg_connection
except ImportError:
    psycopg2 = None  # type: ignore[assignment]
    sql = None  # type: ignore[assignment]
    pg_connection = None  # type: ignore[assignment, misc]


@dataclass
class AnalysisResult:
    """Represents a single repository analysis result."""

    repo_name: str
    repo_url: str
    success: bool
    output: str
    analyzed_at: str


class ResultsDatabase:
    """Database for storing Semgrep analysis results.

    Supports both SQLite (for local development) and PostgreSQL (for production).
    Can be initialized with either a file path (SQLite) or connection string (PostgreSQL).
    """

    def __init__(
        self,
        db_path: str | Path | None = None,
        db_url: str | None = None,
    ) -> None:
        """Initialize the database connection.

        Args:
            db_path: Path to the SQLite database file (for local development)
            db_url: PostgreSQL connection URL (for production)
                    Format: postgresql://user:password@host:port/database

        Raises:
            ValueError: If neither db_path nor db_url is provided
        """
        if not db_path and not db_url:
            raise ValueError("Either db_path (SQLite) or db_url (PostgreSQL) must be provided")

        self.db_path = Path(db_path) if db_path else None
        self.db_url = db_url
        self.is_postgres = db_url is not None

        if self.db_path:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_db()

    def _init_db(self) -> None:
        """Create the database schema if it doesn't exist."""
        if self.is_postgres:
            self._init_postgres()
        else:
            self._init_sqlite()

    def _init_sqlite(self) -> None:
        """Initialize SQLite database schema."""
        assert self.db_path is not None
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS analysis_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    rules_path TEXT,
                    use_pro INTEGER DEFAULT 0,
                    k8s_job_id TEXT,
                    status TEXT DEFAULT 'pending'
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS analysis_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    repo_name TEXT NOT NULL,
                    repo_url TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    output TEXT NOT NULL,
                    analyzed_at TEXT NOT NULL,
                    s3_path TEXT,
                    k8s_job_id TEXT,
                    FOREIGN KEY (session_id) REFERENCES analysis_sessions(id),
                    UNIQUE(session_id, repo_name)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_results_session
                ON analysis_results(session_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_results_repo
                ON analysis_results(repo_name)
            """)
            conn.commit()

    def _init_postgres(self) -> None:
        """Initialize PostgreSQL database schema."""
        if not psycopg2:
            raise ImportError(
                "psycopg2 is required for PostgreSQL support. "
                "Install with: pip install psycopg2-binary"
            )

        assert self.db_url is not None
        with psycopg2.connect(self.db_url) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS analysis_sessions (
                        id SERIAL PRIMARY KEY,
                        query TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        rules_path TEXT,
                        use_pro BOOLEAN DEFAULT FALSE,
                        k8s_job_id TEXT,
                        status TEXT DEFAULT 'pending'
                    )
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS analysis_results (
                        id SERIAL PRIMARY KEY,
                        session_id INTEGER NOT NULL,
                        repo_name TEXT NOT NULL,
                        repo_url TEXT NOT NULL,
                        success BOOLEAN NOT NULL,
                        output TEXT NOT NULL,
                        analyzed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        s3_path TEXT,
                        k8s_job_id TEXT,
                        FOREIGN KEY (session_id) REFERENCES analysis_sessions(id),
                        UNIQUE(session_id, repo_name)
                    )
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_results_session
                    ON analysis_results(session_id)
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_results_repo
                    ON analysis_results(repo_name)
                """)
            conn.commit()

    def create_session(
        self,
        query: str,
        rules_path: str | None = None,
        use_pro: bool = False,
        k8s_job_id: str | None = None,
    ) -> int:
        """Create a new analysis session and return its ID.

        Args:
            query: The search query used
            rules_path: Path to custom Semgrep rules
            use_pro: Whether Semgrep Pro was used
            k8s_job_id: Optional Kubernetes Job ID for tracking

        Returns:
            The session ID
        """
        if self.is_postgres:
            assert self.db_url is not None
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO analysis_sessions
                        (query, created_at, rules_path, use_pro, k8s_job_id)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING id
                        """,
                        (query, datetime.now(UTC), rules_path, use_pro, k8s_job_id),
                    )
                    row = cur.fetchone()
                    if row is None:
                        raise RuntimeError("Failed to create session - no ID returned")
                    session_id = row[0]
                conn.commit()
                return int(session_id)
        else:
            assert self.db_path is not None
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO analysis_sessions
                    (query, created_at, rules_path, use_pro, k8s_job_id)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (query, datetime.now(UTC).isoformat(), rules_path, int(use_pro), k8s_job_id),
                )
                conn.commit()
                return cursor.lastrowid or 0

    def get_latest_session(self, query: str) -> int | None:
        """Get the latest session ID for a given query.

        Args:
            query: The search query

        Returns:
            The session ID or None if no session exists
        """
        if self.is_postgres:
            assert self.db_url is not None
            with psycopg2.connect(self.db_url) as conn, conn.cursor() as cur:
                cur.execute(
                    """
                        SELECT id FROM analysis_sessions
                        WHERE query = %s
                        ORDER BY created_at DESC
                        LIMIT 1
                        """,
                    (query,),
                )
                row = cur.fetchone()
                return row[0] if row else None
        else:
            assert self.db_path is not None
            with sqlite3.connect(self.db_path) as sqlite_conn:
                cursor = sqlite_conn.execute(
                    """
                    SELECT id FROM analysis_sessions
                    WHERE query = ?
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (query,),
                )
                row = cursor.fetchone()
                return row[0] if row else None

    def save_result(
        self,
        session_id: int,
        repo_name: str,
        repo_url: str,
        success: bool,
        output: str,
        s3_path: str | None = None,
        k8s_job_id: str | None = None,
    ) -> None:
        """Save an analysis result to the database.

        Args:
            session_id: The session ID
            repo_name: Name of the repository
            repo_url: URL of the repository
            success: Whether analysis succeeded
            output: Semgrep output or error message
            s3_path: Optional S3 path where results are stored
            k8s_job_id: Optional Kubernetes Job ID for tracking
        """
        if self.is_postgres:
            assert self.db_url is not None
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO analysis_results
                        (session_id, repo_name, repo_url, success, output,
                         analyzed_at, s3_path, k8s_job_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (session_id, repo_name)
                        DO UPDATE SET
                            repo_url = EXCLUDED.repo_url,
                            success = EXCLUDED.success,
                            output = EXCLUDED.output,
                            analyzed_at = EXCLUDED.analyzed_at,
                            s3_path = EXCLUDED.s3_path,
                            k8s_job_id = EXCLUDED.k8s_job_id
                        """,
                        (
                            session_id,
                            repo_name,
                            repo_url,
                            success,
                            output,
                            datetime.now(UTC),
                            s3_path,
                            k8s_job_id,
                        ),
                    )
                conn.commit()
        else:
            assert self.db_path is not None
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO analysis_results
                    (session_id, repo_name, repo_url, success, output,
                     analyzed_at, s3_path, k8s_job_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        repo_name,
                        repo_url,
                        int(success),
                        output,
                        datetime.now(UTC).isoformat(),
                        s3_path,
                        k8s_job_id,
                    ),
                )
                conn.commit()

    def get_analyzed_repos(self, session_id: int) -> set[str]:
        """Get the set of repository names already analyzed in a session.

        Args:
            session_id: The session ID

        Returns:
            Set of repository names that have been analyzed
        """
        if self.is_postgres:
            assert self.db_url is not None
            with psycopg2.connect(self.db_url) as conn, conn.cursor() as cur:
                cur.execute(
                    """
                        SELECT repo_name FROM analysis_results
                        WHERE session_id = %s
                        """,
                    (session_id,),
                )
                return {row[0] for row in cur.fetchall()}
        else:
            assert self.db_path is not None
            with sqlite3.connect(self.db_path) as sqlite_conn:
                cursor = sqlite_conn.execute(
                    """
                    SELECT repo_name FROM analysis_results
                    WHERE session_id = ?
                    """,
                    (session_id,),
                )
                return {row[0] for row in cursor.fetchall()}

    def get_session_results(self, session_id: int) -> list[dict[str, Any]]:
        """Get all results for a session.

        Args:
            session_id: The session ID

        Returns:
            List of result dictionaries
        """
        if self.is_postgres:
            assert self.db_url is not None
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT repo_name, repo_url, success, output, analyzed_at,
                               s3_path, k8s_job_id
                        FROM analysis_results
                        WHERE session_id = %s
                        ORDER BY id
                        """,
                        (session_id,),
                    )
                    # Fetch all rows before cursor context exits
                    rows = cur.fetchall()
                # Process rows after cursor is closed
                return [
                    {
                        "repo": row[0],
                        "url": row[1],
                        "success": bool(row[2]),
                        "output": row[3],
                        "analyzed_at": row[4].isoformat() if row[4] else None,
                        "s3_path": row[5],
                        "k8s_job_id": row[6],
                    }
                    for row in rows
                ]
        else:
            assert self.db_path is not None
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT repo_name, repo_url, success, output, analyzed_at, s3_path, k8s_job_id
                    FROM analysis_results
                    WHERE session_id = ?
                    ORDER BY id
                    """,
                    (session_id,),
                )
                return [
                    {
                        "repo": row[0],
                        "url": row[1],
                        "success": bool(row[2]),
                        "output": row[3],
                        "analyzed_at": row[4],
                        "s3_path": row[5],
                        "k8s_job_id": row[6],
                    }
                    for row in cursor.fetchall()
                ]

    def get_all_sessions(self) -> list[dict[str, Any]]:
        """Get all analysis sessions.

        Returns:
            List of session dictionaries
        """
        if self.is_postgres:
            assert self.db_url is not None
            with psycopg2.connect(self.db_url) as conn, conn.cursor() as cur:
                cur.execute(
                    """
                        SELECT s.id, s.query, s.created_at, s.rules_path, s.use_pro, s.status,
                               COUNT(r.id) as result_count,
                               SUM(CASE WHEN r.success = TRUE THEN 1 ELSE 0 END) as success_count
                        FROM analysis_sessions s
                        LEFT JOIN analysis_results r ON s.id = r.session_id
                        GROUP BY s.id
                        ORDER BY s.created_at DESC
                        """
                )
                return [
                    {
                        "id": row[0],
                        "query": row[1],
                        "created_at": row[2].isoformat() if row[2] else None,
                        "rules_path": row[3],
                        "use_pro": bool(row[4]),
                        "status": row[5],
                        "result_count": row[6],
                        "success_count": row[7] or 0,
                    }
                    for row in cur.fetchall()
                ]
        else:
            assert self.db_path is not None
            with sqlite3.connect(self.db_path) as sqlite_conn:
                cursor = sqlite_conn.execute(
                    """
                    SELECT s.id, s.query, s.created_at, s.rules_path, s.use_pro, s.status,
                           COUNT(r.id) as result_count,
                           SUM(CASE WHEN r.success = 1 THEN 1 ELSE 0 END) as success_count
                    FROM analysis_sessions s
                    LEFT JOIN analysis_results r ON s.id = r.session_id
                    GROUP BY s.id
                    ORDER BY s.created_at DESC
                    """
                )
                return [
                    {
                        "id": row[0],
                        "query": row[1],
                        "created_at": row[2],
                        "rules_path": row[3],
                        "use_pro": bool(row[4]),
                        "status": row[5],
                        "result_count": row[6],
                        "success_count": row[7] or 0,
                    }
                    for row in cursor.fetchall()
                ]

    def get_session(self, session_id: int) -> dict[str, Any] | None:
        """Get a session by ID.

        Args:
            session_id: The session ID

        Returns:
            Session dictionary or None if not found
        """
        if self.is_postgres:
            assert self.db_url is not None
            with psycopg2.connect(self.db_url) as conn, conn.cursor() as cur:
                cur.execute(
                    """
                        SELECT id, query, created_at, rules_path, use_pro, status
                        FROM analysis_sessions
                        WHERE id = %s
                        """,
                    (session_id,),
                )
                row = cur.fetchone()
                if not row:
                    return None
                return {
                    "id": row[0],
                    "query": row[1],
                    "created_at": row[2].isoformat() if row[2] else None,
                    "rules_path": row[3],
                    "use_pro": bool(row[4]),
                    "status": row[5],
                }
        else:
            assert self.db_path is not None
            with sqlite3.connect(self.db_path) as sqlite_conn:
                cursor = sqlite_conn.execute(
                    """
                    SELECT id, query, created_at, rules_path, use_pro, status
                    FROM analysis_sessions
                    WHERE id = ?
                    """,
                    (session_id,),
                )
                row = cursor.fetchone()
                if not row:
                    return None
                return {
                    "id": row[0],
                    "query": row[1],
                    "created_at": row[2],
                    "rules_path": row[3],
                    "use_pro": bool(row[4]),
                    "status": row[5],
                }

    def export_session_to_json(self, session_id: int) -> str:
        """Export a session's results to JSON.

        Args:
            session_id: The session ID

        Returns:
            JSON string of the results
        """
        results = self.get_session_results(session_id)
        return json.dumps(results, indent=2)

    def update_session_status(self, session_id: int, status: str) -> None:
        """Update the status of a session.

        Args:
            session_id: The session ID
            status: New status (e.g., 'pending', 'running', 'completed', 'failed')
        """
        if self.is_postgres:
            assert self.db_url is not None
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE analysis_sessions
                        SET status = %s
                        WHERE id = %s
                        """,
                        (status, session_id),
                    )
                conn.commit()
        else:
            assert self.db_path is not None
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    UPDATE analysis_sessions
                    SET status = ?
                    WHERE id = ?
                    """,
                    (status, session_id),
                )
                conn.commit()
