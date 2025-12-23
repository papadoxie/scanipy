"""Tests for the Semgrep runner module."""

import os
import subprocess
from unittest.mock import MagicMock, patch, call

import pytest

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
        mock_run.assert_called_once_with(
            ["which", "git"], check=True, capture_output=True
        )

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

    @patch("tools.semgrep.semgrep_runner.os.path.exists")
    @patch("tools.semgrep.semgrep_runner.subprocess.run")
    def test_run_semgrep_with_rules_path(self, mock_run, mock_exists, mock_colors):
        """Test _run_semgrep includes rules path when specified."""
        mock_exists.return_value = True
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        
        _run_semgrep("/tmp/repo", mock_colors, rules_path="/path/to/rules.yaml")
        
        call_args = mock_run.call_args[0][0]
        assert "--config" in call_args
        assert "/path/to/rules.yaml" in call_args

    @patch("tools.semgrep.semgrep_runner.os.path.exists")
    def test_run_semgrep_with_nonexistent_rules(self, mock_exists, mock_colors):
        """Test _run_semgrep returns error for nonexistent rules path."""
        mock_exists.return_value = False
        
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
    def test_returns_empty_when_semgrep_not_installed(
        self, mock_check, mock_colors
    ):
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
        
        repos = [{"url": f"https://github.com/owner/repo{i}", "name": f"repo{i}"} for i in range(15)]
        
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

    @patch("tools.semgrep.semgrep_runner.os.makedirs")
    @patch("tools.semgrep.semgrep_runner._run_semgrep")
    @patch("tools.semgrep.semgrep_runner._clone_repository")
    @patch("tools.semgrep.semgrep_runner._check_command_exists")
    def test_uses_custom_clone_dir(
        self,
        mock_check,
        mock_clone,
        mock_semgrep,
        mock_makedirs,
        mock_colors,
    ):
        """Test uses custom clone directory when specified."""
        mock_check.return_value = True
        mock_clone.return_value = True
        mock_semgrep.return_value = (True, "No findings")
        
        repos = [{"url": "https://github.com/owner/repo", "name": "repo"}]
        
        analyze_repositories_with_semgrep(
            repos, mock_colors, clone_dir="/custom/dir"
        )
        
        mock_makedirs.assert_called_once_with("/custom/dir", exist_ok=True)

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
