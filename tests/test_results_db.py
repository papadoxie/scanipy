"""Tests for the Semgrep results database module (SQLite)."""

from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path

import pytest

from tools.semgrep.results_db import AnalysisResult, ResultsDatabase


class TestAnalysisResult:
    """Tests for the AnalysisResult dataclass."""

    def test_create_analysis_result(self):
        """Test creating an AnalysisResult instance."""
        result = AnalysisResult(
            repo_name="owner/repo",
            repo_url="https://github.com/owner/repo",
            success=True,
            output="No findings",
            analyzed_at="2024-01-01T00:00:00+00:00",
        )

        assert result.repo_name == "owner/repo"
        assert result.repo_url == "https://github.com/owner/repo"
        assert result.success is True
        assert result.output == "No findings"
        assert result.analyzed_at == "2024-01-01T00:00:00+00:00"

    def test_analysis_result_with_failure(self):
        """Test creating an AnalysisResult with failure status."""
        result = AnalysisResult(
            repo_name="owner/repo",
            repo_url="https://github.com/owner/repo",
            success=False,
            output="Error: semgrep failed",
            analyzed_at="2024-01-01T00:00:00+00:00",
        )

        assert result.success is False
        assert "Error" in result.output


class TestResultsDatabase:
    """Tests for the ResultsDatabase class."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir) / "test_results.db"

    @pytest.fixture
    def db(self, temp_db_path):
        """Create a ResultsDatabase instance."""
        return ResultsDatabase(temp_db_path)

    def test_init_creates_database_file(self, temp_db_path):
        """Test that initialization creates the database file."""
        ResultsDatabase(temp_db_path)
        assert temp_db_path.exists()

    def test_init_creates_parent_directories(self):
        """Test that initialization creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_path = Path(tmpdir) / "nested" / "dir" / "test.db"
            ResultsDatabase(nested_path)
            assert nested_path.exists()

    def test_init_creates_tables(self, temp_db_path):
        """Test that initialization creates required tables."""
        ResultsDatabase(temp_db_path)

        with sqlite3.connect(temp_db_path) as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = [row[0] for row in cursor.fetchall()]

        assert "analysis_sessions" in tables
        assert "analysis_results" in tables

    def test_init_creates_indexes(self, temp_db_path):
        """Test that initialization creates required indexes."""
        ResultsDatabase(temp_db_path)

        with sqlite3.connect(temp_db_path) as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index' ORDER BY name")
            indexes = [row[0] for row in cursor.fetchall()]

        assert "idx_results_session" in indexes
        assert "idx_results_repo" in indexes

    def test_create_session(self, db):
        """Test creating a new analysis session."""
        session_id = db.create_session("python extractall")

        assert session_id > 0

    def test_create_session_with_rules_path(self, db):
        """Test creating a session with custom rules path."""
        session_id = db.create_session(
            "python extractall",
            rules_path="/path/to/rules.yaml",
        )

        assert session_id > 0

    def test_create_session_with_use_pro(self, db):
        """Test creating a session with use_pro flag."""
        session_id = db.create_session(
            "python extractall",
            use_pro=True,
        )

        assert session_id > 0

    def test_create_multiple_sessions(self, db):
        """Test creating multiple sessions returns unique IDs."""
        session1 = db.create_session("query1")
        session2 = db.create_session("query2")
        session3 = db.create_session("query1")  # Same query, new session

        assert session1 != session2
        assert session2 != session3
        assert session1 != session3

    def test_get_latest_session(self, db):
        """Test getting the latest session for a query."""
        db.create_session("query1")
        session2 = db.create_session("query1")

        latest = db.get_latest_session("query1")

        assert latest == session2

    def test_get_latest_session_no_match(self, db):
        """Test getting latest session when no sessions exist."""
        result = db.get_latest_session("nonexistent")

        assert result is None

    def test_save_result(self, db):
        """Test saving an analysis result."""
        session_id = db.create_session("test query")

        db.save_result(
            session_id=session_id,
            repo_name="owner/repo",
            repo_url="https://github.com/owner/repo",
            success=True,
            output="No findings",
        )

        # Verify result was saved
        results = db.get_session_results(session_id)
        assert len(results) == 1
        assert results[0]["repo"] == "owner/repo"
        assert results[0]["success"] is True

    def test_save_result_updates_existing(self, db):
        """Test that saving a result for same repo updates existing."""
        session_id = db.create_session("test query")

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
        )

        results = db.get_session_results(session_id)
        assert len(results) == 1
        assert results[0]["success"] is True
        assert "Second attempt" in results[0]["output"]

    def test_get_analyzed_repos(self, db):
        """Test getting set of analyzed repository names."""
        session_id = db.create_session("test query")

        db.save_result(session_id, "owner/repo1", "url1", True, "output1")
        db.save_result(session_id, "owner/repo2", "url2", True, "output2")
        db.save_result(session_id, "owner/repo3", "url3", False, "output3")

        analyzed = db.get_analyzed_repos(session_id)

        assert analyzed == {"owner/repo1", "owner/repo2", "owner/repo3"}

    def test_get_analyzed_repos_empty_session(self, db):
        """Test getting analyzed repos for empty session."""
        session_id = db.create_session("test query")

        analyzed = db.get_analyzed_repos(session_id)

        assert analyzed == set()

    def test_get_session_results(self, db):
        """Test getting all results for a session."""
        session_id = db.create_session("test query")

        db.save_result(session_id, "owner/repo1", "url1", True, "output1")
        db.save_result(session_id, "owner/repo2", "url2", False, "output2")

        results = db.get_session_results(session_id)

        assert len(results) == 2
        assert results[0]["repo"] == "owner/repo1"
        assert results[0]["url"] == "url1"
        assert results[0]["success"] is True
        assert results[0]["output"] == "output1"
        assert "analyzed_at" in results[0]

    def test_get_session_results_preserves_order(self, db):
        """Test that results are returned in insertion order."""
        session_id = db.create_session("test query")

        db.save_result(session_id, "repo3", "url3", True, "output3")
        db.save_result(session_id, "repo1", "url1", True, "output1")
        db.save_result(session_id, "repo2", "url2", True, "output2")

        results = db.get_session_results(session_id)

        assert [r["repo"] for r in results] == ["repo3", "repo1", "repo2"]

    def test_get_all_sessions(self, db):
        """Test getting all analysis sessions."""
        session1 = db.create_session("query1", rules_path="/path/rules.yaml")
        session2 = db.create_session("query2", use_pro=True)

        # Add some results to session1
        db.save_result(session1, "repo1", "url1", True, "output1")
        db.save_result(session1, "repo2", "url2", False, "output2")

        sessions = db.get_all_sessions()

        assert len(sessions) == 2
        # Sessions are ordered by created_at DESC
        assert sessions[0]["id"] == session2
        assert sessions[0]["query"] == "query2"
        assert sessions[0]["use_pro"] is True
        assert sessions[0]["result_count"] == 0

        assert sessions[1]["id"] == session1
        assert sessions[1]["query"] == "query1"
        assert sessions[1]["rules_path"] == "/path/rules.yaml"
        assert sessions[1]["result_count"] == 2
        assert sessions[1]["success_count"] == 1

    def test_get_all_sessions_empty(self, db):
        """Test getting sessions when none exist."""
        sessions = db.get_all_sessions()

        assert sessions == []

    def test_export_session_to_json(self, db):
        """Test exporting session results to JSON."""
        session_id = db.create_session("test query")
        db.save_result(session_id, "owner/repo", "url", True, "No findings")

        json_str = db.export_session_to_json(session_id)
        data = json.loads(json_str)

        assert len(data) == 1
        assert data[0]["repo"] == "owner/repo"
        assert data[0]["success"] is True

    def test_export_empty_session_to_json(self, db):
        """Test exporting empty session to JSON."""
        session_id = db.create_session("test query")

        json_str = db.export_session_to_json(session_id)
        data = json.loads(json_str)

        assert data == []

    def test_database_accepts_string_path(self):
        """Test that database accepts string path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            db = ResultsDatabase(db_path)
            session_id = db.create_session("test")
            assert session_id > 0

    def test_database_isolation_between_sessions(self, db):
        """Test that results are isolated between sessions."""
        session1 = db.create_session("query1")
        session2 = db.create_session("query2")

        db.save_result(session1, "repo1", "url1", True, "output1")
        db.save_result(session2, "repo2", "url2", True, "output2")

        results1 = db.get_session_results(session1)
        results2 = db.get_session_results(session2)

        assert len(results1) == 1
        assert results1[0]["repo"] == "repo1"
        assert len(results2) == 1
        assert results2[0]["repo"] == "repo2"

    def test_same_repo_different_sessions(self, db):
        """Test that same repo can exist in different sessions."""
        session1 = db.create_session("query1")
        session2 = db.create_session("query2")

        db.save_result(session1, "owner/repo", "url", True, "session1 output")
        db.save_result(session2, "owner/repo", "url", True, "session2 output")

        results1 = db.get_session_results(session1)
        results2 = db.get_session_results(session2)

        assert results1[0]["output"] == "session1 output"
        assert results2[0]["output"] == "session2 output"

    def test_update_session_status(self, db):
        """Test updating session status."""
        session_id = db.create_session("test query")

        db.update_session_status(session_id, "completed")

        # Verify status was updated
        sessions = db.get_all_sessions()
        assert sessions[0]["status"] == "completed"

    def test_get_session(self, db):
        """Test getting a session by ID."""
        session_id = db.create_session("test query", rules_path="/rules.yaml", use_pro=True)

        session = db.get_session(session_id)

        assert session is not None
        assert session["id"] == session_id
        assert session["query"] == "test query"
        assert session["rules_path"] == "/rules.yaml"
        assert session["use_pro"] is True
        assert "created_at" in session
        assert "status" in session

    def test_get_session_not_found(self, db):
        """Test getting a non-existent session returns None."""
        session = db.get_session(99999)

        assert session is None
