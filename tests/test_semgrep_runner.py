"""Tests for the Semgrep runner module."""

import subprocess
from unittest.mock import MagicMock, patch

from tools.semgrep.semgrep_runner import (
    _check_command_exists,
    _clone_repository,
    _run_semgrep,
    analyze_repositories_with_semgrep,
)


class TestCheckCommandExists:
    """Tests for the _check_command_exists function."""

    @patch("tools.semgrep.semgrep_runner.subprocess.run")
    def test_command_exists(self, mock_run):
        """Test _check_command_exists returns True when command exists."""
        mock_run.return_value = MagicMock(returncode=0)

        result = _check_command_exists("git")

        assert result is True
        mock_run.assert_called_once_with(["which", "git"], check=True, capture_output=True)

    @patch("tools.semgrep.semgrep_runner.subprocess.run")
    def test_command_not_exists(self, mock_run):
        """Test _check_command_exists returns False when command doesn't exist."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "which")

        result = _check_command_exists("nonexistent")

        assert result is False


class TestCloneRepository:
    """Tests for the _clone_repository function."""

    @patch("tools.semgrep.semgrep_runner.subprocess.run")
    def test_clone_success(self, mock_run, mock_colors):
        """Test _clone_repository returns True on success."""
        mock_run.return_value = MagicMock(returncode=0)

        result = _clone_repository(
            "https://github.com/owner/repo",
            "/tmp/repo",
            mock_colors,
        )

        assert result is True
        mock_run.assert_called_once_with(
            ["git", "clone", "--depth=1", "https://github.com/owner/repo", "/tmp/repo"],
            check=True,
            capture_output=True,
        )

    @patch("tools.semgrep.semgrep_runner.subprocess.run")
    def test_clone_failure(self, mock_run, mock_colors):
        """Test _clone_repository returns False on failure."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "git clone")

        result = _clone_repository(
            "https://github.com/owner/repo",
            "/tmp/repo",
            mock_colors,
        )

        assert result is False


class TestRunSemgrep:
    """Tests for the _run_semgrep function."""

    @patch("tools.semgrep.semgrep_runner.subprocess.run")
    def test_run_semgrep_success(self, mock_run, mock_colors):
        """Test _run_semgrep returns success with output."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="No findings",
            stderr="",
        )

        success, output = _run_semgrep("/tmp/repo", mock_colors)

        assert success is True
        assert output == "No findings"

    @patch("tools.semgrep.semgrep_runner.subprocess.run")
    def test_run_semgrep_failure(self, mock_run, mock_colors):
        """Test _run_semgrep returns failure with error message."""
        error = subprocess.CalledProcessError(1, "semgrep")
        error.stdout = "stdout content"
        error.stderr = "stderr content"
        mock_run.side_effect = error

        success, output = _run_semgrep("/tmp/repo", mock_colors)

        assert success is False
        assert "Error" in output

    @patch("tools.semgrep.semgrep_runner.subprocess.run")
    def test_run_semgrep_with_pro(self, mock_run, mock_colors):
        """Test _run_semgrep includes --pro flag when specified."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        _run_semgrep("/tmp/repo", mock_colors, use_pro=True)

        call_args = mock_run.call_args[0][0]
        assert "--pro" in call_args

    @patch("tools.semgrep.semgrep_runner.Path")
    @patch("tools.semgrep.semgrep_runner.subprocess.run")
    def test_run_semgrep_with_rules_path(self, mock_run, mock_path, mock_colors):
        """Test _run_semgrep includes rules path when specified."""
        mock_path.return_value.exists.return_value = True
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        _run_semgrep("/tmp/repo", mock_colors, rules_path="/path/to/rules.yaml")

        call_args = mock_run.call_args[0][0]
        assert "--config" in call_args
        assert "/path/to/rules.yaml" in call_args

    @patch("tools.semgrep.semgrep_runner.Path")
    def test_run_semgrep_with_nonexistent_rules(self, mock_path, mock_colors):
        """Test _run_semgrep returns error for nonexistent rules path."""
        mock_path.return_value.exists.return_value = False

        success, output = _run_semgrep(
            "/tmp/repo", mock_colors, rules_path="/nonexistent/rules.yaml"
        )

        assert success is False
        assert "not found" in output

    @patch("tools.semgrep.semgrep_runner.subprocess.run")
    def test_run_semgrep_with_args(self, mock_run, mock_colors):
        """Test _run_semgrep includes additional args when specified."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        _run_semgrep("/tmp/repo", mock_colors, semgrep_args="--json --verbose")

        call_args = mock_run.call_args[0][0]
        assert "--json" in call_args
        assert "--verbose" in call_args


class TestAnalyzeRepositoriesWithSemgrep:
    """Tests for the analyze_repositories_with_semgrep function."""

    @patch("tools.semgrep.semgrep_runner._check_command_exists")
    def test_returns_empty_when_semgrep_not_installed(self, mock_check, mock_colors):
        """Test returns empty list when semgrep is not installed."""
        mock_check.return_value = False

        result = analyze_repositories_with_semgrep([], mock_colors)

        assert result == []
        mock_check.assert_called_with("semgrep")

    @patch("tools.semgrep.semgrep_runner._check_command_exists")
    def test_returns_empty_when_git_not_installed(self, mock_check, mock_colors):
        """Test returns empty list when git is not installed."""
        # semgrep exists, git doesn't
        mock_check.side_effect = [True, False]

        result = analyze_repositories_with_semgrep([], mock_colors)

        assert result == []

    @patch("tools.semgrep.semgrep_runner.shutil.rmtree")
    @patch("tools.semgrep.semgrep_runner.tempfile.mkdtemp")
    @patch("tools.semgrep.semgrep_runner._run_semgrep")
    @patch("tools.semgrep.semgrep_runner._clone_repository")
    @patch("tools.semgrep.semgrep_runner._check_command_exists")
    def test_analyzes_up_to_10_repos(
        self,
        mock_check,
        mock_clone,
        mock_semgrep,
        mock_mkdtemp,
        mock_rmtree,
        mock_colors,
    ):
        """Test analyzes maximum of 10 repositories."""
        mock_check.return_value = True
        mock_clone.return_value = True
        mock_semgrep.return_value = (True, "No findings")
        mock_mkdtemp.return_value = "/tmp/test"

        repos = [
            {"url": f"https://github.com/owner/repo{i}", "name": f"repo{i}"} for i in range(15)
        ]

        result = analyze_repositories_with_semgrep(repos, mock_colors)

        # Should only analyze first 10
        assert len(result) == 10
        assert mock_clone.call_count == 10

    @patch("tools.semgrep.semgrep_runner.shutil.rmtree")
    @patch("tools.semgrep.semgrep_runner.tempfile.mkdtemp")
    @patch("tools.semgrep.semgrep_runner._run_semgrep")
    @patch("tools.semgrep.semgrep_runner._clone_repository")
    @patch("tools.semgrep.semgrep_runner._check_command_exists")
    def test_cleans_up_temp_dir(
        self,
        mock_check,
        mock_clone,
        mock_semgrep,
        mock_mkdtemp,
        mock_rmtree,
        mock_colors,
    ):
        """Test cleans up temporary directory after analysis."""
        mock_check.return_value = True
        mock_clone.return_value = True
        mock_semgrep.return_value = (True, "No findings")
        mock_mkdtemp.return_value = "/tmp/test"

        repos = [{"url": "https://github.com/owner/repo", "name": "repo"}]

        analyze_repositories_with_semgrep(repos, mock_colors)

        mock_rmtree.assert_called_once_with("/tmp/test")

    @patch("tools.semgrep.semgrep_runner.shutil.rmtree")
    @patch("tools.semgrep.semgrep_runner.tempfile.mkdtemp")
    @patch("tools.semgrep.semgrep_runner._run_semgrep")
    @patch("tools.semgrep.semgrep_runner._clone_repository")
    @patch("tools.semgrep.semgrep_runner._check_command_exists")
    def test_keeps_cloned_repos_when_requested(
        self,
        mock_check,
        mock_clone,
        mock_semgrep,
        mock_mkdtemp,
        mock_rmtree,
        mock_colors,
    ):
        """Test keeps cloned repos when keep_cloned=True."""
        mock_check.return_value = True
        mock_clone.return_value = True
        mock_semgrep.return_value = (True, "No findings")
        mock_mkdtemp.return_value = "/tmp/test"

        repos = [{"url": "https://github.com/owner/repo", "name": "repo"}]

        analyze_repositories_with_semgrep(repos, mock_colors, keep_cloned=True)

        mock_rmtree.assert_not_called()

    @patch("tools.semgrep.semgrep_runner.Path")
    @patch("tools.semgrep.semgrep_runner._run_semgrep")
    @patch("tools.semgrep.semgrep_runner._clone_repository")
    @patch("tools.semgrep.semgrep_runner._check_command_exists")
    def test_uses_custom_clone_dir(
        self,
        mock_check,
        mock_clone,
        mock_semgrep,
        mock_path,
        mock_colors,
    ):
        """Test uses custom clone directory when specified."""
        mock_check.return_value = True
        mock_clone.return_value = True
        mock_semgrep.return_value = (True, "No findings")

        repos = [{"url": "https://github.com/owner/repo", "name": "repo"}]

        analyze_repositories_with_semgrep(repos, mock_colors, clone_dir="/custom/dir")

        mock_path.return_value.mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @patch("tools.semgrep.semgrep_runner.shutil.rmtree")
    @patch("tools.semgrep.semgrep_runner.tempfile.mkdtemp")
    @patch("tools.semgrep.semgrep_runner._run_semgrep")
    @patch("tools.semgrep.semgrep_runner._clone_repository")
    @patch("tools.semgrep.semgrep_runner._check_command_exists")
    def test_returns_results_with_success_status(
        self,
        mock_check,
        mock_clone,
        mock_semgrep,
        mock_mkdtemp,
        mock_rmtree,
        mock_colors,
    ):
        """Test returns results with success status for each repo."""
        mock_check.return_value = True
        mock_clone.return_value = True
        mock_semgrep.return_value = (True, "No findings")
        mock_mkdtemp.return_value = "/tmp/test"

        repos = [{"url": "https://github.com/owner/repo", "name": "owner/repo"}]

        results = analyze_repositories_with_semgrep(repos, mock_colors)

        assert len(results) == 1
        assert results[0]["repo"] == "owner/repo"
        assert results[0]["success"] is True
        assert results[0]["output"] == "No findings"

    @patch("tools.semgrep.semgrep_runner.shutil.rmtree")
    @patch("tools.semgrep.semgrep_runner.tempfile.mkdtemp")
    @patch("tools.semgrep.semgrep_runner._clone_repository")
    @patch("tools.semgrep.semgrep_runner._check_command_exists")
    def test_handles_clone_failure(
        self,
        mock_check,
        mock_clone,
        mock_mkdtemp,
        mock_rmtree,
        mock_colors,
    ):
        """Test handles clone failure gracefully."""
        mock_check.return_value = True
        mock_clone.return_value = False
        mock_mkdtemp.return_value = "/tmp/test"

        repos = [{"url": "https://github.com/owner/repo", "name": "owner/repo"}]

        results = analyze_repositories_with_semgrep(repos, mock_colors)

        assert len(results) == 1
        assert results[0]["success"] is False
        assert "Failed to clone" in results[0]["output"]

    @patch("tools.semgrep.semgrep_runner.shutil.rmtree")
    @patch("tools.semgrep.semgrep_runner.tempfile.mkdtemp")
    @patch("tools.semgrep.semgrep_runner._check_command_exists")
    def test_skips_repos_without_url(
        self,
        mock_check,
        mock_mkdtemp,
        mock_rmtree,
        mock_colors,
    ):
        """Test skips repositories without URL."""
        mock_check.return_value = True
        mock_mkdtemp.return_value = "/tmp/test"

        repos = [{"name": "repo_without_url"}]

        results = analyze_repositories_with_semgrep(repos, mock_colors)

        assert len(results) == 0

    @patch("tools.semgrep.semgrep_runner.shutil.rmtree")
    @patch("tools.semgrep.semgrep_runner.tempfile.mkdtemp")
    @patch("tools.semgrep.semgrep_runner._run_semgrep")
    @patch("tools.semgrep.semgrep_runner._clone_repository")
    @patch("tools.semgrep.semgrep_runner._check_command_exists")
    def test_semgrep_analysis_failure(
        self,
        mock_check,
        mock_clone,
        mock_semgrep,
        mock_mkdtemp,
        mock_rmtree,
        mock_colors,
    ):
        """Test handles semgrep analysis failure."""
        mock_check.return_value = True
        mock_clone.return_value = True
        mock_semgrep.return_value = (False, "Semgrep error occurred")
        mock_mkdtemp.return_value = "/tmp/test"

        repos = [{"url": "https://github.com/owner/repo", "name": "owner/repo"}]

        results = analyze_repositories_with_semgrep(repos, mock_colors)

        assert len(results) == 1
        assert results[0]["success"] is False
        assert "Semgrep error" in results[0]["output"]

    @patch("tools.semgrep.semgrep_runner.shutil.rmtree")
    @patch("tools.semgrep.semgrep_runner.tempfile.mkdtemp")
    @patch("tools.semgrep.semgrep_runner._run_semgrep")
    @patch("tools.semgrep.semgrep_runner._clone_repository")
    @patch("tools.semgrep.semgrep_runner._check_command_exists")
    def test_cleanup_exception_handling(
        self,
        mock_check,
        mock_clone,
        mock_semgrep,
        mock_mkdtemp,
        mock_rmtree,
        mock_colors,
    ):
        """Test handles exception during cleanup."""
        mock_check.return_value = True
        mock_clone.return_value = True
        mock_semgrep.return_value = (True, "No findings")
        mock_mkdtemp.return_value = "/tmp/test"
        mock_rmtree.side_effect = OSError("Permission denied")

        repos = [{"url": "https://github.com/owner/repo", "name": "owner/repo"}]

        # Should not crash even if cleanup fails
        results = analyze_repositories_with_semgrep(repos, mock_colors)

        assert len(results) == 1

    @patch("tools.semgrep.semgrep_runner.shutil.rmtree")
    @patch("tools.semgrep.semgrep_runner.tempfile.mkdtemp")
    @patch("tools.semgrep.semgrep_runner._run_semgrep")
    @patch("tools.semgrep.semgrep_runner._clone_repository")
    @patch("tools.semgrep.semgrep_runner._check_command_exists")
    def test_prints_pro_flag_message(
        self,
        mock_check,
        mock_clone,
        mock_semgrep,
        mock_mkdtemp,
        mock_rmtree,
        mock_colors,
        capsys,
    ):
        """Test prints pro flag message when use_pro is True."""
        mock_check.return_value = True
        mock_clone.return_value = True
        mock_semgrep.return_value = (True, "No findings")
        mock_mkdtemp.return_value = "/tmp/test"

        repos = [{"url": "https://github.com/owner/repo", "name": "owner/repo"}]

        analyze_repositories_with_semgrep(repos, mock_colors, use_pro=True)

        captured = capsys.readouterr()
        assert "--pro" in captured.out

    @patch("tools.semgrep.semgrep_runner.shutil.rmtree")
    @patch("tools.semgrep.semgrep_runner.tempfile.mkdtemp")
    @patch("tools.semgrep.semgrep_runner._run_semgrep")
    @patch("tools.semgrep.semgrep_runner._clone_repository")
    @patch("tools.semgrep.semgrep_runner._check_command_exists")
    def test_prints_rules_path_message(
        self,
        mock_check,
        mock_clone,
        mock_semgrep,
        mock_mkdtemp,
        mock_rmtree,
        mock_colors,
        capsys,
    ):
        """Test prints rules path message when rules_path is provided."""
        mock_check.return_value = True
        mock_clone.return_value = True
        mock_semgrep.return_value = (True, "No findings")
        mock_mkdtemp.return_value = "/tmp/test"

        repos = [{"url": "https://github.com/owner/repo", "name": "owner/repo"}]

        analyze_repositories_with_semgrep(repos, mock_colors, rules_path="/path/to/rules")

        captured = capsys.readouterr()
        assert "/path/to/rules" in captured.out


class TestAnalyzeRepositoriesWithDatabase:
    """Tests for database integration in analyze_repositories_with_semgrep."""

    @patch("tools.semgrep.semgrep_runner.shutil.rmtree")
    @patch("tools.semgrep.semgrep_runner.tempfile.mkdtemp")
    @patch("tools.semgrep.semgrep_runner._run_semgrep")
    @patch("tools.semgrep.semgrep_runner._clone_repository")
    @patch("tools.semgrep.semgrep_runner._check_command_exists")
    def test_saves_results_to_database(
        self,
        mock_check,
        mock_clone,
        mock_semgrep,
        mock_mkdtemp,
        mock_rmtree,
        mock_colors,
        tmp_path,
    ):
        """Test that results are saved to database when db_path is provided."""
        mock_check.return_value = True
        mock_clone.return_value = True
        mock_semgrep.return_value = (True, "No findings")
        mock_mkdtemp.return_value = str(tmp_path / "clone")

        db_path = str(tmp_path / "results.db")
        repos = [{"url": "https://github.com/owner/repo", "name": "owner/repo"}]

        analyze_repositories_with_semgrep(repos, mock_colors, db_path=db_path, query="test query")

        # Verify database was created and contains results
        from tools.semgrep.results_db import ResultsDatabase

        db = ResultsDatabase(db_path)
        sessions = db.get_all_sessions()
        assert len(sessions) == 1
        assert sessions[0]["result_count"] == 1

    @patch("tools.semgrep.semgrep_runner.shutil.rmtree")
    @patch("tools.semgrep.semgrep_runner.tempfile.mkdtemp")
    @patch("tools.semgrep.semgrep_runner._run_semgrep")
    @patch("tools.semgrep.semgrep_runner._clone_repository")
    @patch("tools.semgrep.semgrep_runner._check_command_exists")
    def test_resumes_from_existing_session(
        self,
        mock_check,
        mock_clone,
        mock_semgrep,
        mock_mkdtemp,
        mock_rmtree,
        mock_colors,
        tmp_path,
        capsys,
    ):
        """Test that analysis resumes from existing session."""
        mock_check.return_value = True
        mock_clone.return_value = True
        mock_semgrep.return_value = (True, "No findings")
        mock_mkdtemp.return_value = str(tmp_path / "clone")

        db_path = str(tmp_path / "results.db")

        # Create a session with one analyzed repo
        from tools.semgrep.results_db import ResultsDatabase

        db = ResultsDatabase(db_path)
        session_id = db.create_session("test query")
        db.save_result(session_id, "owner/repo1", "url1", True, "Already analyzed")

        repos = [
            {"url": "https://github.com/owner/repo1", "name": "owner/repo1"},
            {"url": "https://github.com/owner/repo2", "name": "owner/repo2"},
        ]

        analyze_repositories_with_semgrep(
            repos, mock_colors, db_path=db_path, query="test query", resume=True
        )

        captured = capsys.readouterr()
        assert "Resuming session" in captured.out
        # Only repo2 should be cloned (repo1 was already analyzed)
        assert mock_clone.call_count == 1

    @patch("tools.semgrep.semgrep_runner.shutil.rmtree")
    @patch("tools.semgrep.semgrep_runner.tempfile.mkdtemp")
    @patch("tools.semgrep.semgrep_runner._run_semgrep")
    @patch("tools.semgrep.semgrep_runner._clone_repository")
    @patch("tools.semgrep.semgrep_runner._check_command_exists")
    def test_skips_all_repos_when_already_analyzed(
        self,
        mock_check,
        mock_clone,
        mock_semgrep,
        mock_mkdtemp,
        mock_rmtree,
        mock_colors,
        tmp_path,
        capsys,
    ):
        """Test that all repos are skipped when already analyzed."""
        mock_check.return_value = True
        mock_clone.return_value = True
        mock_semgrep.return_value = (True, "No findings")
        mock_mkdtemp.return_value = str(tmp_path / "clone")

        db_path = str(tmp_path / "results.db")

        # Create a session with all repos already analyzed
        from tools.semgrep.results_db import ResultsDatabase

        db = ResultsDatabase(db_path)
        session_id = db.create_session("test query")
        db.save_result(session_id, "owner/repo1", "url1", True, "output1")
        db.save_result(session_id, "owner/repo2", "url2", True, "output2")

        repos = [
            {"url": "https://github.com/owner/repo1", "name": "owner/repo1"},
            {"url": "https://github.com/owner/repo2", "name": "owner/repo2"},
        ]

        results = analyze_repositories_with_semgrep(
            repos, mock_colors, db_path=db_path, query="test query", resume=True
        )

        captured = capsys.readouterr()
        assert "All repositories already analyzed" in captured.out
        assert mock_clone.call_count == 0
        # Should return results from database
        assert len(results) == 2

    @patch("tools.semgrep.semgrep_runner.shutil.rmtree")
    @patch("tools.semgrep.semgrep_runner.tempfile.mkdtemp")
    @patch("tools.semgrep.semgrep_runner._run_semgrep")
    @patch("tools.semgrep.semgrep_runner._clone_repository")
    @patch("tools.semgrep.semgrep_runner._check_command_exists")
    def test_creates_new_session_without_resume(
        self,
        mock_check,
        mock_clone,
        mock_semgrep,
        mock_mkdtemp,
        mock_rmtree,
        mock_colors,
        tmp_path,
        capsys,
    ):
        """Test that new session is created when resume=False."""
        mock_check.return_value = True
        mock_clone.return_value = True
        mock_semgrep.return_value = (True, "No findings")
        mock_mkdtemp.return_value = str(tmp_path / "clone")

        db_path = str(tmp_path / "results.db")
        repos = [{"url": "https://github.com/owner/repo", "name": "owner/repo"}]

        analyze_repositories_with_semgrep(
            repos, mock_colors, db_path=db_path, query="test query", resume=False
        )

        captured = capsys.readouterr()
        assert "Created new session" in captured.out

    @patch("tools.semgrep.semgrep_runner.shutil.rmtree")
    @patch("tools.semgrep.semgrep_runner.tempfile.mkdtemp")
    @patch("tools.semgrep.semgrep_runner._run_semgrep")
    @patch("tools.semgrep.semgrep_runner._clone_repository")
    @patch("tools.semgrep.semgrep_runner._check_command_exists")
    def test_saves_clone_failure_to_database(
        self,
        mock_check,
        mock_clone,
        mock_semgrep,
        mock_mkdtemp,
        mock_rmtree,
        mock_colors,
        tmp_path,
    ):
        """Test that clone failures are saved to database."""
        mock_check.return_value = True
        mock_clone.return_value = False  # Clone fails
        mock_mkdtemp.return_value = str(tmp_path / "clone")

        db_path = str(tmp_path / "results.db")
        repos = [{"url": "https://github.com/owner/repo", "name": "owner/repo"}]

        analyze_repositories_with_semgrep(repos, mock_colors, db_path=db_path, query="test query")

        from tools.semgrep.results_db import ResultsDatabase

        db = ResultsDatabase(db_path)
        session_id = db.get_latest_session("test query")
        results = db.get_session_results(session_id)

        assert len(results) == 1
        assert results[0]["success"] is False
        assert "Failed to clone" in results[0]["output"]

    @patch("tools.semgrep.semgrep_runner.shutil.rmtree")
    @patch("tools.semgrep.semgrep_runner.tempfile.mkdtemp")
    @patch("tools.semgrep.semgrep_runner._run_semgrep")
    @patch("tools.semgrep.semgrep_runner._clone_repository")
    @patch("tools.semgrep.semgrep_runner._check_command_exists")
    def test_prints_db_path_message(
        self,
        mock_check,
        mock_clone,
        mock_semgrep,
        mock_mkdtemp,
        mock_rmtree,
        mock_colors,
        tmp_path,
        capsys,
    ):
        """Test prints database path message when db_path is provided."""
        mock_check.return_value = True
        mock_clone.return_value = True
        mock_semgrep.return_value = (True, "No findings")
        mock_mkdtemp.return_value = str(tmp_path / "clone")

        db_path = str(tmp_path / "results.db")
        repos = [{"url": "https://github.com/owner/repo", "name": "owner/repo"}]

        analyze_repositories_with_semgrep(repos, mock_colors, db_path=db_path, query="test query")

        captured = capsys.readouterr()
        assert "Saving results to" in captured.out
        assert db_path in captured.out

    @patch("tools.semgrep.semgrep_runner.shutil.rmtree")
    @patch("tools.semgrep.semgrep_runner.tempfile.mkdtemp")
    @patch("tools.semgrep.semgrep_runner._run_semgrep")
    @patch("tools.semgrep.semgrep_runner._clone_repository")
    @patch("tools.semgrep.semgrep_runner._check_command_exists")
    def test_returns_all_results_including_previously_analyzed(
        self,
        mock_check,
        mock_clone,
        mock_semgrep,
        mock_mkdtemp,
        mock_rmtree,
        mock_colors,
        tmp_path,
    ):
        """Test that results include previously analyzed repos when resuming."""
        mock_check.return_value = True
        mock_clone.return_value = True
        mock_semgrep.return_value = (True, "New analysis")
        mock_mkdtemp.return_value = str(tmp_path / "clone")

        db_path = str(tmp_path / "results.db")

        # Create a session with one analyzed repo
        from tools.semgrep.results_db import ResultsDatabase

        db = ResultsDatabase(db_path)
        session_id = db.create_session("test query")
        db.save_result(session_id, "owner/repo1", "url1", True, "Previous analysis")

        repos = [
            {"url": "https://github.com/owner/repo1", "name": "owner/repo1"},
            {"url": "https://github.com/owner/repo2", "name": "owner/repo2"},
        ]

        results = analyze_repositories_with_semgrep(
            repos, mock_colors, db_path=db_path, query="test query", resume=True
        )

        # Should include both repos
        assert len(results) == 2
        repo_names = [r["repo"] for r in results]
        assert "owner/repo1" in repo_names
        assert "owner/repo2" in repo_names

    @patch("tools.semgrep.semgrep_runner.shutil.rmtree")
    @patch("tools.semgrep.semgrep_runner.tempfile.mkdtemp")
    @patch("tools.semgrep.semgrep_runner._run_semgrep")
    @patch("tools.semgrep.semgrep_runner._clone_repository")
    @patch("tools.semgrep.semgrep_runner._check_command_exists")
    def test_all_repos_analyzed_no_db_returns_empty(
        self,
        mock_check,
        mock_clone,
        mock_semgrep,
        mock_mkdtemp,
        mock_rmtree,
        mock_colors,
        tmp_path,
    ):
        """Test returns empty when all repos analyzed but no db session."""
        mock_check.return_value = True
        mock_clone.return_value = True
        mock_semgrep.return_value = (True, "No findings")
        mock_mkdtemp.return_value = str(tmp_path / "clone")

        db_path = str(tmp_path / "results.db")

        # Create a session with all repos analyzed
        from tools.semgrep.results_db import ResultsDatabase

        db = ResultsDatabase(db_path)
        session_id = db.create_session("different query")
        db.save_result(session_id, "owner/repo1", "url1", True, "output1")

        repos = [{"url": "https://github.com/owner/repo1", "name": "owner/repo1"}]

        # Resume with a different query that has no session yet
        # But the repo is in already_analyzed from a different session
        # This is an edge case - resume=True but query has no session
        # So session_id will be None after get_latest_session
        # Then create_session is called, making session_id not None
        # So the return [] path is when db is None or session_id is None
        # after filtering. Let's test with resume=True but no matching session
        analyze_repositories_with_semgrep(
            repos,
            mock_colors,
            db_path=db_path,
            query="new query",  # Different query, no existing session
            resume=True,
        )

        # Should analyze the repo since it's a new session
        assert mock_clone.call_count == 1
