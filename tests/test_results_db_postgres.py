"""Tests for PostgreSQL support in ResultsDatabase."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from tools.semgrep.results_db import ResultsDatabase


class TestResultsDatabasePostgreSQL:
    """Tests for PostgreSQL database support."""

    @patch("tools.semgrep.results_db.psycopg2")
    def test_init_with_db_url(self, mock_psycopg2):
        """Test ResultsDatabase initializes with PostgreSQL URL."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
        mock_psycopg2.connect.return_value = mock_conn

        db = ResultsDatabase(db_url="postgresql://user:pass@host/db")

        assert db.is_postgres is True
        assert db.db_url == "postgresql://user:pass@host/db"
        mock_psycopg2.connect.assert_called()

    def test_init_requires_db_path_or_url(self):
        """Test ResultsDatabase raises ValueError when neither db_path nor db_url provided."""
        with pytest.raises(ValueError, match=r"Either db_path.*or db_url"):
            ResultsDatabase()

    @patch("tools.semgrep.results_db.psycopg2")
    def test_create_session_postgres(self, mock_psycopg2):
        """Test create_session works with PostgreSQL."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = [1]
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
        mock_psycopg2.connect.return_value = mock_conn

        db = ResultsDatabase(db_url="postgresql://user:pass@host/db")
        session_id = db.create_session("test query", rules_path="/rules.yaml", use_pro=True)

        assert session_id == 1
        mock_cur.execute.assert_called()

    @patch("tools.semgrep.results_db.psycopg2")
    def test_save_result_postgres(self, mock_psycopg2):
        """Test save_result works with PostgreSQL."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
        mock_psycopg2.connect.return_value = mock_conn

        db = ResultsDatabase(db_url="postgresql://user:pass@host/db")
        db.save_result(
            session_id=1,
            repo_name="owner/repo",
            repo_url="https://github.com/owner/repo",
            success=True,
            output="No findings",
            s3_path="s3://bucket/key",
            k8s_job_id="job-123",
        )

        mock_cur.execute.assert_called()
        # Verify ON CONFLICT clause is used (PostgreSQL syntax)
        call_args = mock_cur.execute.call_args[0][0]
        assert "ON CONFLICT" in call_args

    @patch("tools.semgrep.results_db.psycopg2")
    def test_get_session_results_postgres(self, mock_psycopg2):
        """Test get_session_results works with PostgreSQL."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        from datetime import UTC, datetime

        mock_cur.fetchall.return_value = [
            (
                "owner/repo",
                "https://github.com/owner/repo",
                True,
                "No findings",
                datetime.now(UTC),
                "s3://bucket/key",
                "job-123",
                "semgrep-1-owner-repo-abc123",  # k8s_job_name
            ),
        ]
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
        mock_psycopg2.connect.return_value = mock_conn

        db = ResultsDatabase(db_url="postgresql://user:pass@host/db")
        results = db.get_session_results(1)

        assert len(results) == 1
        assert results[0]["repo"] == "owner/repo"
        assert results[0]["s3_path"] == "s3://bucket/key"
        assert results[0]["k8s_job_id"] == "job-123"

    @patch("tools.semgrep.results_db.psycopg2")
    def test_update_session_status_postgres(self, mock_psycopg2):
        """Test update_session_status works with PostgreSQL."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
        mock_psycopg2.connect.return_value = mock_conn

        db = ResultsDatabase(db_url="postgresql://user:pass@host/db")
        db.update_session_status(1, "completed")

        mock_cur.execute.assert_called()
        call_args = mock_cur.execute.call_args[0][0]
        assert "UPDATE" in call_args
        assert "status" in call_args

    def test_init_raises_import_error_without_psycopg2(self):
        """Test ResultsDatabase raises ImportError when psycopg2 not available."""
        with patch("tools.semgrep.results_db.psycopg2", None):
            with pytest.raises(ImportError, match="psycopg2 is required"):
                ResultsDatabase(db_url="postgresql://user:pass@host/db")

    @patch("tools.semgrep.results_db.psycopg2")
    def test_get_latest_session_postgres(self, mock_psycopg2):
        """Test get_latest_session works with PostgreSQL."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = (42,)
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
        mock_psycopg2.connect.return_value = mock_conn

        db = ResultsDatabase(db_url="postgresql://user:pass@host/db")
        session_id = db.get_latest_session("test query")

        assert session_id == 42
        mock_cur.execute.assert_called()

    @patch("tools.semgrep.results_db.psycopg2")
    def test_get_latest_session_postgres_not_found(self, mock_psycopg2):
        """Test get_latest_session returns None when no session found."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = None
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
        mock_psycopg2.connect.return_value = mock_conn

        db = ResultsDatabase(db_url="postgresql://user:pass@host/db")
        session_id = db.get_latest_session("nonexistent query")

        assert session_id is None

    @patch("tools.semgrep.results_db.psycopg2")
    def test_get_analyzed_repos_postgres(self, mock_psycopg2):
        """Test get_analyzed_repos works with PostgreSQL."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.fetchall.return_value = [("owner/repo1",), ("owner/repo2",)]
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
        mock_psycopg2.connect.return_value = mock_conn

        db = ResultsDatabase(db_url="postgresql://user:pass@host/db")
        analyzed = db.get_analyzed_repos(1)

        assert analyzed == {"owner/repo1", "owner/repo2"}

    @patch("tools.semgrep.results_db.psycopg2")
    def test_get_all_sessions_postgres(self, mock_psycopg2):
        """Test get_all_sessions works with PostgreSQL."""
        from datetime import UTC, datetime

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.fetchall.return_value = [
            (
                1,
                "test query",
                datetime.now(UTC),
                "/rules.yaml",
                True,
                "completed",
                5,
                4,
            ),
        ]
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
        mock_psycopg2.connect.return_value = mock_conn

        db = ResultsDatabase(db_url="postgresql://user:pass@host/db")
        sessions = db.get_all_sessions()

        assert len(sessions) == 1
        assert sessions[0]["id"] == 1
        assert sessions[0]["status"] == "completed"
        assert sessions[0]["result_count"] == 5
        assert sessions[0]["success_count"] == 4

    @patch("tools.semgrep.results_db.psycopg2")
    def test_get_session_postgres(self, mock_psycopg2):
        """Test get_session works with PostgreSQL."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = (
            1,
            "test query",
            datetime.now(UTC),
            "/rules.yaml",
            True,
            "pending",
        )
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
        mock_psycopg2.connect.return_value = mock_conn

        db = ResultsDatabase(db_url="postgresql://user:pass@host/db")
        session = db.get_session(1)

        assert session is not None
        assert session["id"] == 1
        assert session["query"] == "test query"
        assert session["rules_path"] == "/rules.yaml"
        assert session["use_pro"] is True
        assert session["status"] == "pending"
        assert "created_at" in session

    @patch("tools.semgrep.results_db.psycopg2")
    def test_get_session_postgres_not_found(self, mock_psycopg2):
        """Test get_session returns None when session doesn't exist in PostgreSQL."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = None
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
        mock_psycopg2.connect.return_value = mock_conn

        db = ResultsDatabase(db_url="postgresql://user:pass@host/db")
        session = db.get_session(99999)

        assert session is None

    @patch("tools.semgrep.results_db.psycopg2")
    def test_create_session_postgres_raises_runtime_error(self, mock_psycopg2):
        """Test create_session raises RuntimeError when fetchone returns None."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = None  # Simulate no ID returned
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
        mock_psycopg2.connect.return_value = mock_conn

        db = ResultsDatabase(db_url="postgresql://user:pass@host/db")
        with pytest.raises(RuntimeError, match="Failed to create session"):
            db.create_session("test query")

    @patch("tools.semgrep.results_db.psycopg2")
    def test_acquire_job_slot_postgres(self, mock_psycopg2):
        """Test acquire_job_slot works with PostgreSQL."""
        from unittest.mock import MagicMock

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.execute.return_value = None
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
        mock_psycopg2.connect.return_value = mock_conn

        db = ResultsDatabase(db_url="postgresql://user:pass@host/db")

        # Mock k8s_client
        mock_k8s_client = MagicMock()
        mock_k8s_client.count_active_jobs.return_value = 5

        # Test with max_parallel = 10, active = 5 (slot available)
        slot_available, active_count = db.acquire_job_slot(
            session_id=1, max_parallel=10, k8s_client=mock_k8s_client
        )

        assert slot_available is True
        assert active_count == 5
        # Verify advisory lock was called
        assert mock_cur.execute.call_count >= 2  # lock and unlock

    @patch("tools.semgrep.results_db.psycopg2")
    def test_acquire_job_slot_postgres_exception_handling(self, mock_psycopg2):
        """Test acquire_job_slot handles exceptions from k8s_client in PostgreSQL."""
        from unittest.mock import MagicMock

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.execute.return_value = None
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
        mock_psycopg2.connect.return_value = mock_conn

        db = ResultsDatabase(db_url="postgresql://user:pass@host/db")

        # Mock k8s_client to raise exception
        mock_k8s_client = MagicMock()
        mock_k8s_client.count_active_jobs.side_effect = Exception("K8s error")

        # Should use conservative fallback (assume limit reached)
        slot_available, active_count = db.acquire_job_slot(
            session_id=1, max_parallel=10, k8s_client=mock_k8s_client
        )

        assert slot_available is False
        assert active_count == 10  # Conservative fallback
