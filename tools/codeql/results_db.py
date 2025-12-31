"""Database module for storing and retrieving CodeQL analysis results.

This module provides SQLite-based persistence for CodeQL analysis results,
allowing analysis to be resumed if interrupted.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass
class CodeQLAnalysisResult:
    """Represents a single repository CodeQL analysis result."""

    repo_name: str
    repo_url: str
    success: bool
    output: str
    analyzed_at: str
    sarif_path: str | None = None


class CodeQLResultsDatabase:
    """SQLite database for storing CodeQL analysis results."""

    def __init__(self, db_path: str | Path) -> None:
        """Initialize the database connection.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Create the database schema if it doesn't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS codeql_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT NOT NULL,
                    language TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    query_suite TEXT,
                    output_format TEXT DEFAULT 'sarif-latest'
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS codeql_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    repo_name TEXT NOT NULL,
                    repo_url TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    output TEXT NOT NULL,
                    analyzed_at TEXT NOT NULL,
                    sarif_path TEXT,
                    FOREIGN KEY (session_id) REFERENCES codeql_sessions(id),
                    UNIQUE(session_id, repo_name)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_codeql_results_session
                ON codeql_results(session_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_codeql_results_repo
                ON codeql_results(repo_name)
            """)
            conn.commit()

    def create_session(
        self,
        query: str,
        language: str,
        query_suite: str | None = None,
        output_format: str = "sarif-latest",
    ) -> int:
        """Create a new CodeQL analysis session and return its ID.

        Args:
            query: The search query used
            language: The CodeQL language being analyzed
            query_suite: CodeQL query suite or path
            output_format: Output format (sarif-latest, csv, text)

        Returns:
            The session ID
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO codeql_sessions (
                    query, language, created_at, query_suite, output_format
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (query, language, datetime.now(UTC).isoformat(), query_suite, output_format),
            )
            conn.commit()
            session_id = cursor.lastrowid
            if session_id is None:
                raise RuntimeError("Failed to create session")
            return session_id

    def find_session(
        self,
        query: str,
        language: str,
        query_suite: str | None = None,
    ) -> int | None:
        """Find an existing session matching the parameters.

        Args:
            query: The search query used
            language: The CodeQL language being analyzed
            query_suite: CodeQL query suite or path

        Returns:
            Session ID if found, None otherwise
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT id FROM codeql_sessions
                WHERE query = ? AND language = ? AND query_suite IS ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (query, language, query_suite),
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
        sarif_path: str | None = None,
    ) -> None:
        """Save a CodeQL analysis result.

        Args:
            session_id: Session ID from create_session()
            repo_name: Repository name (owner/repo)
            repo_url: Repository URL
            success: Whether analysis succeeded
            output: Analysis output or error message
            sarif_path: Path to saved SARIF file (if applicable)
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO codeql_results
                (session_id, repo_name, repo_url, success, output, analyzed_at, sarif_path)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    repo_name,
                    repo_url,
                    int(success),
                    output,
                    datetime.now(UTC).isoformat(),
                    sarif_path,
                ),
            )
            conn.commit()

    def get_analyzed_repos(self, session_id: int) -> set[str]:
        """Get set of repository names already analyzed in this session.

        Args:
            session_id: Session ID

        Returns:
            Set of repository names (owner/repo)
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT repo_name FROM codeql_results
                WHERE session_id = ?
                """,
                (session_id,),
            )
            return {row[0] for row in cursor.fetchall()}

    def get_session_results(self, session_id: int) -> list[CodeQLAnalysisResult]:
        """Get all analysis results for a session.

        Args:
            session_id: Session ID

        Returns:
            List of analysis results
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT repo_name, repo_url, success, output, analyzed_at, sarif_path
                FROM codeql_results
                WHERE session_id = ?
                ORDER BY analyzed_at
                """,
                (session_id,),
            )
            return [
                CodeQLAnalysisResult(
                    repo_name=row[0],
                    repo_url=row[1],
                    success=bool(row[2]),
                    output=row[3],
                    analyzed_at=row[4],
                    sarif_path=row[5],
                )
                for row in cursor.fetchall()
            ]

    def get_session_stats(self, session_id: int) -> dict[str, int]:
        """Get statistics for a session.

        Args:
            session_id: Session ID

        Returns:
            Dictionary with 'total', 'success', 'failed' counts
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success,
                    SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed
                FROM codeql_results
                WHERE session_id = ?
                """,
                (session_id,),
            )
            row = cursor.fetchone()
            return {
                "total": row[0] or 0,
                "success": row[1] or 0,
                "failed": row[2] or 0,
            }
