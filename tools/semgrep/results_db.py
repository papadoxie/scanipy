"""Database module for storing and retrieving Semgrep analysis results.

This module provides SQLite-based persistence for Semgrep analysis results,
allowing analysis to be resumed if interrupted.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass
class AnalysisResult:
    """Represents a single repository analysis result."""

    repo_name: str
    repo_url: str
    success: bool
    output: str
    analyzed_at: str


class ResultsDatabase:
    """SQLite database for storing Semgrep analysis results."""

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
                CREATE TABLE IF NOT EXISTS analysis_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    rules_path TEXT,
                    use_pro INTEGER DEFAULT 0
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

    def create_session(
        self,
        query: str,
        rules_path: str | None = None,
        use_pro: bool = False,
    ) -> int:
        """Create a new analysis session and return its ID.

        Args:
            query: The search query used
            rules_path: Path to custom Semgrep rules
            use_pro: Whether Semgrep Pro was used

        Returns:
            The session ID
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO analysis_sessions (query, created_at, rules_path, use_pro)
                VALUES (?, ?, ?, ?)
                """,
                (query, datetime.now(UTC).isoformat(), rules_path, int(use_pro)),
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
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
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
    ) -> None:
        """Save an analysis result to the database.

        Args:
            session_id: The session ID
            repo_name: Name of the repository
            repo_url: URL of the repository
            success: Whether analysis succeeded
            output: Semgrep output or error message
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO analysis_results
                (session_id, repo_name, repo_url, success, output, analyzed_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    repo_name,
                    repo_url,
                    int(success),
                    output,
                    datetime.now(UTC).isoformat(),
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
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
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
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT repo_name, repo_url, success, output, analyzed_at
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
                }
                for row in cursor.fetchall()
            ]

    def get_all_sessions(self) -> list[dict[str, Any]]:
        """Get all analysis sessions.

        Returns:
            List of session dictionaries
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT s.id, s.query, s.created_at, s.rules_path, s.use_pro,
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
                    "result_count": row[5],
                    "success_count": row[6] or 0,
                }
                for row in cursor.fetchall()
            ]

    def export_session_to_json(self, session_id: int) -> str:
        """Export a session's results to JSON.

        Args:
            session_id: The session ID

        Returns:
            JSON string of the results
        """
        results = self.get_session_results(session_id)
        return json.dumps(results, indent=2)
