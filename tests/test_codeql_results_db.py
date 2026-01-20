"""Tests for CodeQL results database module."""

from __future__ import annotations

import sqlite3
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tools.codeql.results_db import CodeQLAnalysisResult, CodeQLResultsDatabase


@pytest.fixture
def temp_db_path() -> Path:  # type: ignore[misc]
    """Create a temporary database path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "test_codeql.db"


@pytest.fixture
def db(temp_db_path: Path) -> CodeQLResultsDatabase:
    """Create a CodeQL results database instance."""
    return CodeQLResultsDatabase(temp_db_path)


def test_init_creates_database_file(temp_db_path: Path) -> None:
    """Test that initializing creates the database file."""
    assert not temp_db_path.exists()
    CodeQLResultsDatabase(temp_db_path)
    assert temp_db_path.exists()


def test_init_creates_tables(db: CodeQLResultsDatabase) -> None:
    """Test that database initialization creates required tables."""
    with sqlite3.connect(db.db_path) as conn:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        assert "codeql_sessions" in tables
        assert "codeql_results" in tables


def test_init_creates_indexes(db: CodeQLResultsDatabase) -> None:
    """Test that database initialization creates required indexes."""
    with sqlite3.connect(db.db_path) as conn:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index' ORDER BY name")
        indexes = [row[0] for row in cursor.fetchall()]
        assert "idx_codeql_results_session" in indexes
        assert "idx_codeql_results_repo" in indexes


def test_create_session_returns_id(db: CodeQLResultsDatabase) -> None:
    """Test that create_session returns a valid session ID."""
    session_id = db.create_session(
        query="test query",
        language="python",
        query_suite="security-extended",
    )
    assert isinstance(session_id, int)
    assert session_id > 0


def test_create_session_stores_data(db: CodeQLResultsDatabase) -> None:
    """Test that create_session stores session data correctly."""
    session_id = db.create_session(
        query="vulnerability scan",
        language="javascript",
        query_suite="security-and-quality",
        output_format="sarif-latest",
    )

    with sqlite3.connect(db.db_path) as conn:
        cursor = conn.execute(
            "SELECT query, language, query_suite, output_format FROM codeql_sessions WHERE id = ?",
            (session_id,),
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "vulnerability scan"
        assert row[1] == "javascript"
        assert row[2] == "security-and-quality"
        assert row[3] == "sarif-latest"


def test_create_session_sets_created_at(db: CodeQLResultsDatabase) -> None:
    """Test that create_session sets the created_at timestamp."""
    before = datetime.now(UTC)
    session_id = db.create_session(query="test", language="python")
    after = datetime.now(UTC)

    with sqlite3.connect(db.db_path) as conn:
        cursor = conn.execute("SELECT created_at FROM codeql_sessions WHERE id = ?", (session_id,))
        row = cursor.fetchone()
        assert row is not None
        created_at = datetime.fromisoformat(row[0])
        assert before <= created_at <= after


def test_find_session_returns_existing_session(db: CodeQLResultsDatabase) -> None:
    """Test that find_session returns an existing matching session."""
    session_id = db.create_session(
        query="test query",
        language="python",
        query_suite="security-extended",
    )

    found_id = db.find_session(
        query="test query",
        language="python",
        query_suite="security-extended",
    )

    assert found_id == session_id


def test_find_session_returns_none_if_not_found(db: CodeQLResultsDatabase) -> None:
    """Test that find_session returns None if no matching session exists."""
    db.create_session(query="query1", language="python")

    found_id = db.find_session(query="query2", language="python")

    assert found_id is None


def test_find_session_matches_query_suite(db: CodeQLResultsDatabase) -> None:
    """Test that find_session matches on query_suite."""
    session1 = db.create_session(query="test", language="python", query_suite="security-extended")
    session2 = db.create_session(
        query="test", language="python", query_suite="security-and-quality"
    )

    found1 = db.find_session(query="test", language="python", query_suite="security-extended")
    found2 = db.find_session(query="test", language="python", query_suite="security-and-quality")

    assert found1 == session1
    assert found2 == session2


def test_find_session_matches_none_query_suite(db: CodeQLResultsDatabase) -> None:
    """Test that find_session correctly matches None query_suite."""
    session_id = db.create_session(query="test", language="python", query_suite=None)

    found_id = db.find_session(query="test", language="python", query_suite=None)

    assert found_id == session_id


def test_save_result_stores_data(db: CodeQLResultsDatabase) -> None:
    """Test that save_result stores result data correctly."""
    session_id = db.create_session(query="test", language="python")

    db.save_result(
        session_id=session_id,
        repo_name="owner/repo",
        repo_url="https://github.com/owner/repo",
        success=True,
        output="Analysis complete",
        sarif_path="/path/to/results.sarif",
    )

    with sqlite3.connect(db.db_path) as conn:
        cursor = conn.execute(
            """
            SELECT repo_name, repo_url, success, output, sarif_path
            FROM codeql_results WHERE session_id = ?
            """,
            (session_id,),
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "owner/repo"
        assert row[1] == "https://github.com/owner/repo"
        assert row[2] == 1  # SQLite stores boolean as integer
        assert row[3] == "Analysis complete"
        assert row[4] == "/path/to/results.sarif"


def test_save_result_sets_analyzed_at(db: CodeQLResultsDatabase) -> None:
    """Test that save_result sets the analyzed_at timestamp."""
    session_id = db.create_session(query="test", language="python")
    before = datetime.now(UTC)

    db.save_result(
        session_id=session_id,
        repo_name="owner/repo",
        repo_url="https://github.com/owner/repo",
        success=True,
        output="Done",
    )

    after = datetime.now(UTC)

    with sqlite3.connect(db.db_path) as conn:
        cursor = conn.execute(
            "SELECT analyzed_at FROM codeql_results WHERE session_id = ?",
            (session_id,),
        )
        row = cursor.fetchone()
        assert row is not None
        analyzed_at = datetime.fromisoformat(row[0])
        assert before <= analyzed_at <= after


def test_save_result_replaces_existing(db: CodeQLResultsDatabase) -> None:
    """Test that save_result replaces existing result for same repo."""
    session_id = db.create_session(query="test", language="python")

    db.save_result(
        session_id=session_id,
        repo_name="owner/repo",
        repo_url="https://github.com/owner/repo",
        success=False,
        output="First attempt failed",
    )

    db.save_result(
        session_id=session_id,
        repo_name="owner/repo",
        repo_url="https://github.com/owner/repo",
        success=True,
        output="Second attempt succeeded",
        sarif_path="/path/to/results.sarif",
    )

    with sqlite3.connect(db.db_path) as conn:
        cursor = conn.execute(
            "SELECT success, output FROM codeql_results WHERE session_id = ? AND repo_name = ?",
            (session_id, "owner/repo"),
        )
        rows = cursor.fetchall()
        assert len(rows) == 1
        assert rows[0][0] == 1  # success=True
        assert rows[0][1] == "Second attempt succeeded"


def test_get_analyzed_repos_returns_set(db: CodeQLResultsDatabase) -> None:
    """Test that get_analyzed_repos returns a set of repo names."""
    session_id = db.create_session(query="test", language="python")

    db.save_result(
        session_id=session_id,
        repo_name="owner/repo1",
        repo_url="https://github.com/owner/repo1",
        success=True,
        output="Done",
    )
    db.save_result(
        session_id=session_id,
        repo_name="owner/repo2",
        repo_url="https://github.com/owner/repo2",
        success=False,
        output="Failed",
    )

    repos = db.get_analyzed_repos(session_id)

    assert isinstance(repos, set)
    assert repos == {"owner/repo1", "owner/repo2"}


def test_get_analyzed_repos_empty_session(db: CodeQLResultsDatabase) -> None:
    """Test that get_analyzed_repos returns empty set for session with no results."""
    session_id = db.create_session(query="test", language="python")

    repos = db.get_analyzed_repos(session_id)

    assert repos == set()


def test_get_session_results_returns_list(db: CodeQLResultsDatabase) -> None:
    """Test that get_session_results returns a list of CodeQLAnalysisResult."""
    session_id = db.create_session(query="test", language="python")

    db.save_result(
        session_id=session_id,
        repo_name="owner/repo1",
        repo_url="https://github.com/owner/repo1",
        success=True,
        output="Success",
        sarif_path="/path/to/repo1.sarif",
    )
    db.save_result(
        session_id=session_id,
        repo_name="owner/repo2",
        repo_url="https://github.com/owner/repo2",
        success=False,
        output="Failed",
    )

    results = db.get_session_results(session_id)

    assert len(results) == 2
    assert all(isinstance(r, CodeQLAnalysisResult) for r in results)
    assert results[0].repo_name == "owner/repo1"
    assert results[0].success is True
    assert results[1].repo_name == "owner/repo2"
    assert results[1].success is False


def test_get_session_results_empty(db: CodeQLResultsDatabase) -> None:
    """Test that get_session_results returns empty list for session with no results."""
    session_id = db.create_session(query="test", language="python")

    results = db.get_session_results(session_id)

    assert results == []


def test_get_session_stats_returns_dict(db: CodeQLResultsDatabase) -> None:
    """Test that get_session_stats returns statistics dictionary."""
    session_id = db.create_session(query="test", language="python")

    db.save_result(
        session_id=session_id,
        repo_name="owner/repo1",
        repo_url="https://github.com/owner/repo1",
        success=True,
        output="Success",
    )
    db.save_result(
        session_id=session_id,
        repo_name="owner/repo2",
        repo_url="https://github.com/owner/repo2",
        success=True,
        output="Success",
    )
    db.save_result(
        session_id=session_id,
        repo_name="owner/repo3",
        repo_url="https://github.com/owner/repo3",
        success=False,
        output="Failed",
    )

    stats = db.get_session_stats(session_id)

    assert stats["total"] == 3
    assert stats["success"] == 2
    assert stats["failed"] == 1


def test_get_session_stats_empty(db: CodeQLResultsDatabase) -> None:
    """Test that get_session_stats returns zeros for empty session."""
    session_id = db.create_session(query="test", language="python")

    stats = db.get_session_stats(session_id)

    assert stats["total"] == 0
    assert stats["success"] == 0
    assert stats["failed"] == 0


def test_multiple_sessions_isolated(db: CodeQLResultsDatabase) -> None:
    """Test that multiple sessions are isolated from each other."""
    session1 = db.create_session(query="query1", language="python")
    session2 = db.create_session(query="query2", language="javascript")

    db.save_result(
        session_id=session1,
        repo_name="repo1",
        repo_url="https://github.com/owner/repo1",
        success=True,
        output="Done",
    )
    db.save_result(
        session_id=session2,
        repo_name="repo2",
        repo_url="https://github.com/owner/repo2",
        success=True,
        output="Done",
    )

    repos1 = db.get_analyzed_repos(session1)
    repos2 = db.get_analyzed_repos(session2)

    assert repos1 == {"repo1"}
    assert repos2 == {"repo2"}


def test_codeql_analysis_result_dataclass() -> None:
    """Test CodeQLAnalysisResult dataclass creation."""
    result = CodeQLAnalysisResult(
        repo_name="owner/repo",
        repo_url="https://github.com/owner/repo",
        success=True,
        output="Analysis complete",
        analyzed_at="2025-01-01T00:00:00Z",
        sarif_path="/path/to/results.sarif",
    )

    assert result.repo_name == "owner/repo"
    assert result.repo_url == "https://github.com/owner/repo"
    assert result.success is True
    assert result.output == "Analysis complete"
    assert result.analyzed_at == "2025-01-01T00:00:00Z"
    assert result.sarif_path == "/path/to/results.sarif"


def test_codeql_analysis_result_optional_sarif_path() -> None:
    """Test CodeQLAnalysisResult with None sarif_path."""
    result = CodeQLAnalysisResult(
        repo_name="owner/repo",
        repo_url="https://github.com/owner/repo",
        success=False,
        output="Analysis failed",
        analyzed_at="2025-01-01T00:00:00Z",
        sarif_path=None,
    )

    assert result.sarif_path is None


def test_create_session_raises_on_none_lastrowid(temp_db_path: Path) -> None:
    """Test that create_session raises RuntimeError if lastrowid is None."""
    from unittest.mock import MagicMock, patch

    db = CodeQLResultsDatabase(temp_db_path)

    with patch("sqlite3.connect") as mock_connect:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.lastrowid = None
        mock_conn.execute.return_value = mock_cursor
        mock_connect.return_value.__enter__.return_value = mock_conn

        with pytest.raises(RuntimeError, match="Failed to create session"):
            db.create_session(query="test", language="python")
