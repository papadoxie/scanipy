"""Tests for the CodeQL runner module."""

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from tools.codeql.codeql_runner import (
    DEFAULT_QUERY_SUITES,
    LANGUAGE_MAP,
    _check_command_exists,
    _clone_repository,
    _create_codeql_database,
    _get_codeql_language,
    _print_sarif_summary,
    _run_codeql_analysis,
    analyze_repositories_with_codeql,
)


class MockColors:
    """Mock color configuration for testing."""

    HEADER = ""
    SUCCESS = ""
    WARNING = ""
    ERROR = ""
    INFO = ""
    RESET = ""
    REPO_NAME = ""
    PROGRESS = ""


class TestLanguageMap:
    """Tests for the language map constants."""

    def test_python_mapping(self):
        """Test Python language mapping."""
        assert LANGUAGE_MAP["python"] == "python"

    def test_javascript_mapping(self):
        """Test JavaScript language mapping."""
        assert LANGUAGE_MAP["javascript"] == "javascript"

    def test_typescript_uses_javascript(self):
        """Test TypeScript uses JavaScript extractor."""
        assert LANGUAGE_MAP["typescript"] == "javascript"

    def test_kotlin_uses_java(self):
        """Test Kotlin uses Java extractor."""
        assert LANGUAGE_MAP["kotlin"] == "java"

    def test_cpp_variants(self):
        """Test C/C++ variants all map to cpp."""
        assert LANGUAGE_MAP["c"] == "cpp"
        assert LANGUAGE_MAP["cpp"] == "cpp"
        assert LANGUAGE_MAP["c++"] == "cpp"

    def test_csharp_variants(self):
        """Test C# variants all map to csharp."""
        assert LANGUAGE_MAP["csharp"] == "csharp"
        assert LANGUAGE_MAP["c#"] == "csharp"

    def test_go_variants(self):
        """Test Go variants."""
        assert LANGUAGE_MAP["go"] == "go"
        assert LANGUAGE_MAP["golang"] == "go"


class TestDefaultQuerySuites:
    """Tests for the default query suites."""

    def test_has_python_suite(self):
        """Test Python query suite exists."""
        assert "python" in DEFAULT_QUERY_SUITES
        assert "security" in DEFAULT_QUERY_SUITES["python"]

    def test_has_javascript_suite(self):
        """Test JavaScript query suite exists."""
        assert "javascript" in DEFAULT_QUERY_SUITES

    def test_all_mapped_languages_have_suites(self):
        """Test all mapped languages have default query suites."""
        unique_languages = set(LANGUAGE_MAP.values())
        for lang in unique_languages:
            assert lang in DEFAULT_QUERY_SUITES


class TestCheckCommandExists:
    """Tests for the _check_command_exists function."""

    def test_command_exists(self):
        """Test command exists returns True."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock()
            result = _check_command_exists("git")
            assert result is True
            mock_run.assert_called_once_with(["which", "git"], check=True, capture_output=True)

    def test_command_not_exists(self):
        """Test command not exists returns False."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "which")
            result = _check_command_exists("nonexistent")
            assert result is False


class TestGetCodeqlLanguage:
    """Tests for the _get_codeql_language function."""

    def test_python_lowercase(self):
        """Test Python lowercase."""
        assert _get_codeql_language("python") == "python"

    def test_python_uppercase(self):
        """Test Python uppercase."""
        assert _get_codeql_language("PYTHON") == "python"

    def test_python_mixed_case(self):
        """Test Python mixed case."""
        assert _get_codeql_language("Python") == "python"

    def test_unknown_language(self):
        """Test unknown language returns None."""
        assert _get_codeql_language("unknown") is None

    def test_typescript_maps_to_javascript(self):
        """Test TypeScript maps to JavaScript."""
        assert _get_codeql_language("typescript") == "javascript"


class TestCloneRepository:
    """Tests for the _clone_repository function."""

    def test_clone_success(self):
        """Test successful clone."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock()
            result = _clone_repository("https://github.com/test/repo", "/tmp/test", MockColors())
            assert result is True
            mock_run.assert_called_once_with(
                ["git", "clone", "--depth=1", "https://github.com/test/repo", "/tmp/test"],
                check=True,
                capture_output=True,
            )

    def test_clone_failure(self):
        """Test clone failure."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "git")
            result = _clone_repository("https://github.com/test/repo", "/tmp/test", MockColors())
            assert result is False


class TestCreateCodeqlDatabase:
    """Tests for the _create_codeql_database function."""

    def test_create_database_success(self):
        """Test successful database creation."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="success", stderr="")
            success, output = _create_codeql_database(
                "/tmp/repo", "/tmp/db", "python", MockColors()
            )
            assert success is True
            assert "success" in output

    def test_create_database_failure(self):
        """Test database creation failure."""
        with patch("subprocess.run") as mock_run:
            exc = subprocess.CalledProcessError(1, "codeql")
            exc.stdout = "out"
            exc.stderr = "err"
            mock_run.side_effect = exc
            success, output = _create_codeql_database(
                "/tmp/repo", "/tmp/db", "python", MockColors()
            )
            assert success is False
            assert "Error creating database" in output


class TestRunCodeqlAnalysis:
    """Tests for the _run_codeql_analysis function."""

    def test_run_analysis_success(self):
        """Test successful analysis."""
        with (
            patch("subprocess.run") as mock_run,
            tempfile.TemporaryDirectory() as tmpdir,
        ):
            db_path = Path(tmpdir) / "db"
            db_path.mkdir()
            results_file = Path(tmpdir) / "results.sarif"
            results_file.write_text('{"runs": []}')

            mock_run.return_value = MagicMock(stdout="success", stderr="")

            success, _output = _run_codeql_analysis(str(db_path), "python", MockColors())
            assert success is True

    def test_run_analysis_with_custom_query_suite(self):
        """Test analysis with custom query suite."""
        with (
            patch("subprocess.run") as mock_run,
            tempfile.TemporaryDirectory() as tmpdir,
        ):
            db_path = Path(tmpdir) / "db"
            db_path.mkdir()

            mock_run.return_value = MagicMock(stdout="success", stderr="")

            _run_codeql_analysis(str(db_path), "python", MockColors(), query_suite="custom-queries")

            call_args = mock_run.call_args[0][0]
            assert "custom-queries" in call_args

    def test_run_analysis_failure(self):
        """Test analysis failure."""
        with patch("subprocess.run") as mock_run:
            exc = subprocess.CalledProcessError(1, "codeql")
            exc.stdout = "out"
            exc.stderr = "err"
            mock_run.side_effect = exc

            success, output = _run_codeql_analysis("/tmp/db", "python", MockColors())
            assert success is False
            assert "Error running analysis" in output


class TestAnalyzeRepositoriesWithCodeql:
    """Tests for the analyze_repositories_with_codeql function."""

    def test_returns_empty_when_codeql_not_installed(self):
        """Test returns empty when CodeQL not installed."""
        with patch("tools.codeql.codeql_runner._check_command_exists") as mock_check:
            mock_check.return_value = False

            result = analyze_repositories_with_codeql(
                [{"url": "https://github.com/test/repo", "name": "test"}],
                MockColors(),
                language="python",
            )

            assert result == []

    def test_returns_empty_when_git_not_installed(self):
        """Test returns empty when git not installed."""
        with patch("tools.codeql.codeql_runner._check_command_exists") as mock_check:
            # CodeQL exists, git doesn't
            mock_check.side_effect = lambda cmd: cmd == "codeql"

            result = analyze_repositories_with_codeql(
                [{"url": "https://github.com/test/repo", "name": "test"}],
                MockColors(),
                language="python",
            )

            assert result == []

    def test_returns_empty_when_no_language(self):
        """Test returns empty when no language specified."""
        with patch("tools.codeql.codeql_runner._check_command_exists") as mock_check:
            mock_check.return_value = True

            result = analyze_repositories_with_codeql(
                [{"url": "https://github.com/test/repo", "name": "test"}],
                MockColors(),
                language="",
            )

            assert result == []

    def test_returns_empty_when_invalid_language(self):
        """Test returns empty when invalid language specified."""
        with patch("tools.codeql.codeql_runner._check_command_exists") as mock_check:
            mock_check.return_value = True

            result = analyze_repositories_with_codeql(
                [{"url": "https://github.com/test/repo", "name": "test"}],
                MockColors(),
                language="unknown_language",
            )

            assert result == []

    def test_analyzes_up_to_10_repos(self):
        """Test only analyzes first 10 repositories."""
        with (
            patch("tools.codeql.codeql_runner._check_command_exists") as mock_check,
            patch("tools.codeql.codeql_runner._clone_repository") as mock_clone,
            patch("tools.codeql.codeql_runner._create_codeql_database") as mock_create_db,
            patch("tools.codeql.codeql_runner._run_codeql_analysis") as mock_analyze,
            patch("tempfile.mkdtemp") as mock_mkdtemp,
            patch("shutil.rmtree"),
        ):
            mock_check.return_value = True
            mock_clone.return_value = True
            mock_create_db.return_value = (True, "success")
            mock_analyze.return_value = (True, '{"runs": []}')
            mock_mkdtemp.return_value = "/tmp/test"

            repos = [
                {"url": f"https://github.com/test/repo{i}", "name": f"repo{i}"} for i in range(15)
            ]

            result = analyze_repositories_with_codeql(repos, MockColors(), language="python")

            assert len(result) == 10
            assert mock_clone.call_count == 10

    def test_skips_repos_without_url(self):
        """Test skips repos without URL."""
        with (
            patch("tools.codeql.codeql_runner._check_command_exists") as mock_check,
            patch("tools.codeql.codeql_runner._clone_repository") as mock_clone,
            patch("tools.codeql.codeql_runner._create_codeql_database") as mock_create_db,
            patch("tools.codeql.codeql_runner._run_codeql_analysis") as mock_analyze,
            patch("tempfile.mkdtemp") as mock_mkdtemp,
            patch("shutil.rmtree"),
        ):
            mock_check.return_value = True
            mock_clone.return_value = True
            mock_create_db.return_value = (True, "success")
            mock_analyze.return_value = (True, '{"runs": []}')
            mock_mkdtemp.return_value = "/tmp/test"

            repos = [
                {"name": "no_url_repo"},
                {"url": "https://github.com/test/repo", "name": "with_url"},
            ]

            analyze_repositories_with_codeql(repos, MockColors(), language="python")

            # Should only try to clone the repo with URL
            assert mock_clone.call_count == 1

    def test_handles_clone_failure(self):
        """Test handles clone failure gracefully."""
        with (
            patch("tools.codeql.codeql_runner._check_command_exists") as mock_check,
            patch("tools.codeql.codeql_runner._clone_repository") as mock_clone,
            patch("tempfile.mkdtemp") as mock_mkdtemp,
            patch("shutil.rmtree"),
        ):
            mock_check.return_value = True
            mock_clone.return_value = False
            mock_mkdtemp.return_value = "/tmp/test"

            repos = [{"url": "https://github.com/test/repo", "name": "test"}]

            result = analyze_repositories_with_codeql(repos, MockColors(), language="python")

            assert len(result) == 1
            assert result[0]["success"] is False
            assert "Failed to clone" in result[0]["output"]

    def test_handles_database_creation_failure(self):
        """Test handles database creation failure."""
        with (
            patch("tools.codeql.codeql_runner._check_command_exists") as mock_check,
            patch("tools.codeql.codeql_runner._clone_repository") as mock_clone,
            patch("tools.codeql.codeql_runner._create_codeql_database") as mock_create_db,
            patch("tempfile.mkdtemp") as mock_mkdtemp,
            patch("shutil.rmtree"),
        ):
            mock_check.return_value = True
            mock_clone.return_value = True
            mock_create_db.return_value = (False, "Database creation failed")
            mock_mkdtemp.return_value = "/tmp/test"

            repos = [{"url": "https://github.com/test/repo", "name": "test"}]

            result = analyze_repositories_with_codeql(repos, MockColors(), language="python")

            assert len(result) == 1
            assert result[0]["success"] is False
            assert "Database creation failed" in result[0]["output"]

    def test_handles_analysis_failure(self):
        """Test handles analysis failure."""
        with (
            patch("tools.codeql.codeql_runner._check_command_exists") as mock_check,
            patch("tools.codeql.codeql_runner._clone_repository") as mock_clone,
            patch("tools.codeql.codeql_runner._create_codeql_database") as mock_create_db,
            patch("tools.codeql.codeql_runner._run_codeql_analysis") as mock_analyze,
            patch("tempfile.mkdtemp") as mock_mkdtemp,
            patch("shutil.rmtree"),
        ):
            mock_check.return_value = True
            mock_clone.return_value = True
            mock_create_db.return_value = (True, "success")
            mock_analyze.return_value = (False, "Analysis failed")
            mock_mkdtemp.return_value = "/tmp/test"

            repos = [{"url": "https://github.com/test/repo", "name": "test"}]

            result = analyze_repositories_with_codeql(repos, MockColors(), language="python")

            assert len(result) == 1
            assert result[0]["success"] is False

    def test_uses_custom_clone_dir(self):
        """Test uses custom clone directory."""
        with (
            patch("tools.codeql.codeql_runner._check_command_exists") as mock_check,
            patch("tools.codeql.codeql_runner._clone_repository") as mock_clone,
            patch("tools.codeql.codeql_runner._create_codeql_database") as mock_create_db,
            patch("tools.codeql.codeql_runner._run_codeql_analysis") as mock_analyze,
            tempfile.TemporaryDirectory() as tmpdir,
        ):
            mock_check.return_value = True
            mock_clone.return_value = True
            mock_create_db.return_value = (True, "success")
            mock_analyze.return_value = (True, '{"runs": []}')

            repos = [{"url": "https://github.com/test/repo", "name": "test"}]

            analyze_repositories_with_codeql(
                repos, MockColors(), language="python", clone_dir=tmpdir
            )

            # Check clone was called with path in custom dir
            clone_call_args = mock_clone.call_args[0]
            assert tmpdir in clone_call_args[1]

    def test_keeps_cloned_repos_when_requested(self):
        """Test keeps cloned repos when keep_cloned is True."""
        with (
            patch("tools.codeql.codeql_runner._check_command_exists") as mock_check,
            patch("tools.codeql.codeql_runner._clone_repository") as mock_clone,
            patch("tools.codeql.codeql_runner._create_codeql_database") as mock_create_db,
            patch("tools.codeql.codeql_runner._run_codeql_analysis") as mock_analyze,
            patch("tempfile.mkdtemp") as mock_mkdtemp,
            patch("shutil.rmtree") as mock_rmtree,
        ):
            mock_check.return_value = True
            mock_clone.return_value = True
            mock_create_db.return_value = (True, "success")
            mock_analyze.return_value = (True, '{"runs": []}')
            mock_mkdtemp.return_value = "/tmp/test"

            repos = [{"url": "https://github.com/test/repo", "name": "test"}]

            analyze_repositories_with_codeql(
                repos, MockColors(), language="python", keep_cloned=True
            )

            # rmtree should not be called when keep_cloned is True
            mock_rmtree.assert_not_called()

    def test_cleans_up_temp_dir(self):
        """Test cleans up temporary directory."""
        with (
            patch("tools.codeql.codeql_runner._check_command_exists") as mock_check,
            patch("tools.codeql.codeql_runner._clone_repository") as mock_clone,
            patch("tools.codeql.codeql_runner._create_codeql_database") as mock_create_db,
            patch("tools.codeql.codeql_runner._run_codeql_analysis") as mock_analyze,
            patch("tempfile.mkdtemp") as mock_mkdtemp,
            patch("shutil.rmtree") as mock_rmtree,
        ):
            mock_check.return_value = True
            mock_clone.return_value = True
            mock_create_db.return_value = (True, "success")
            mock_analyze.return_value = (True, '{"runs": []}')
            mock_mkdtemp.return_value = "/tmp/test"

            repos = [{"url": "https://github.com/test/repo", "name": "test"}]

            analyze_repositories_with_codeql(repos, MockColors(), language="python")

            mock_rmtree.assert_called_once_with("/tmp/test")

    def test_cleanup_exception_handling(self):
        """Test cleanup handles exceptions."""
        with (
            patch("tools.codeql.codeql_runner._check_command_exists") as mock_check,
            patch("tools.codeql.codeql_runner._clone_repository") as mock_clone,
            patch("tools.codeql.codeql_runner._create_codeql_database") as mock_create_db,
            patch("tools.codeql.codeql_runner._run_codeql_analysis") as mock_analyze,
            patch("tempfile.mkdtemp") as mock_mkdtemp,
            patch("shutil.rmtree") as mock_rmtree,
        ):
            mock_check.return_value = True
            mock_clone.return_value = True
            mock_create_db.return_value = (True, "success")
            mock_analyze.return_value = (True, '{"runs": []}')
            mock_mkdtemp.return_value = "/tmp/test"
            mock_rmtree.side_effect = PermissionError("Cannot delete")

            repos = [{"url": "https://github.com/test/repo", "name": "test"}]

            # Should not raise exception
            result = analyze_repositories_with_codeql(repos, MockColors(), language="python")

            assert len(result) == 1

    def test_returns_results_with_success_status(self):
        """Test returns results with success status."""
        with (
            patch("tools.codeql.codeql_runner._check_command_exists") as mock_check,
            patch("tools.codeql.codeql_runner._clone_repository") as mock_clone,
            patch("tools.codeql.codeql_runner._create_codeql_database") as mock_create_db,
            patch("tools.codeql.codeql_runner._run_codeql_analysis") as mock_analyze,
            patch("tempfile.mkdtemp") as mock_mkdtemp,
            patch("shutil.rmtree"),
        ):
            mock_check.return_value = True
            mock_clone.return_value = True
            mock_create_db.return_value = (True, "success")
            mock_analyze.return_value = (True, '{"runs": []}')
            mock_mkdtemp.return_value = "/tmp/test"

            repos = [{"url": "https://github.com/test/repo", "name": "test"}]

            result = analyze_repositories_with_codeql(repos, MockColors(), language="python")

            assert len(result) == 1
            assert result[0]["repo"] == "test"
            assert result[0]["success"] is True


class TestPrintSarifSummary:
    """Tests for the _print_sarif_summary function."""

    def test_prints_valid_sarif(self, capsys):
        """Test prints valid SARIF summary."""
        sarif = {
            "runs": [
                {
                    "results": [
                        {
                            "ruleId": "test-rule",
                            "message": {"text": "Test message"},
                            "level": "error",
                            "locations": [
                                {
                                    "physicalLocation": {
                                        "artifactLocation": {"uri": "test.py"},
                                        "region": {"startLine": 10},
                                    }
                                }
                            ],
                        }
                    ]
                }
            ]
        }

        _print_sarif_summary(str(sarif).replace("'", '"'), MockColors())

        captured = capsys.readouterr()
        assert "test-rule" in captured.out
        assert "Test message" in captured.out

    def test_handles_invalid_json(self, capsys):
        """Test handles invalid JSON."""
        _print_sarif_summary("not valid json", MockColors())

        captured = capsys.readouterr()
        assert "not valid json" in captured.out

    def test_handles_empty_runs(self, capsys):
        """Test handles empty runs."""
        sarif = '{"runs": []}'

        _print_sarif_summary(sarif, MockColors())

        captured = capsys.readouterr()
        assert "Total findings: 0" in captured.out

    def test_truncates_long_messages(self, capsys):
        """Test truncates long messages."""
        long_message = "A" * 200
        sarif = {
            "runs": [
                {
                    "results": [
                        {
                            "ruleId": "test-rule",
                            "message": {"text": long_message},
                            "level": "warning",
                        }
                    ]
                }
            ]
        }

        _print_sarif_summary(str(sarif).replace("'", '"'), MockColors())

        captured = capsys.readouterr()
        assert "..." in captured.out

    def test_shows_more_findings_indicator(self, capsys):
        """Test shows indicator when more than 10 findings."""
        results = [
            {
                "ruleId": f"rule-{i}",
                "message": {"text": f"Message {i}"},
                "level": "warning",
            }
            for i in range(15)
        ]
        sarif = {"runs": [{"results": results}]}

        _print_sarif_summary(str(sarif).replace("'", '"'), MockColors())

        captured = capsys.readouterr()
        assert "5 more findings" in captured.out

    def test_truncates_long_output(self, capsys):
        """Test truncates output longer than 2000 chars."""
        long_output = "x" * 3000

        _print_sarif_summary(long_output, MockColors())

        captured = capsys.readouterr()
        assert "... (output truncated)" in captured.out


class TestAnalyzeWithQuerySuite:
    """Tests for query suite printing."""

    def test_prints_query_suite_message(self, capsys):
        """Test prints query suite message when provided."""
        with (
            patch("tools.codeql.codeql_runner._check_command_exists") as mock_check,
            patch("tools.codeql.codeql_runner._clone_repository") as mock_clone,
            patch("tools.codeql.codeql_runner._create_codeql_database") as mock_create_db,
            patch("tools.codeql.codeql_runner._run_codeql_analysis") as mock_analyze,
            patch("tempfile.mkdtemp") as mock_mkdtemp,
            patch("shutil.rmtree"),
        ):
            mock_check.return_value = True
            mock_clone.return_value = True
            mock_create_db.return_value = (True, "success")
            mock_analyze.return_value = (True, '{"runs": []}')
            mock_mkdtemp.return_value = "/tmp/test"

            repos = [{"url": "https://github.com/test/repo", "name": "test"}]

            analyze_repositories_with_codeql(
                repos, MockColors(), language="python", query_suite="custom-security"
            )

            captured = capsys.readouterr()
            assert "Query suite: custom-security" in captured.out


class TestCodeQLConfigIntegration:
    """Tests for CodeQL config in build_configs_from_args."""

    def test_codeql_config_defaults(self):
        """Test CodeQLConfig has correct defaults."""
        from models import CodeQLConfig

        config = CodeQLConfig()
        assert config.enabled is False
        assert config.query_suite is None
        assert config.clone_dir is None
        assert config.keep_cloned is False
        assert config.output_format == "sarif-latest"

    def test_codeql_config_populated(self):
        """Test CodeQLConfig is populated correctly from args."""
        from unittest.mock import patch

        from models import CodeQLConfig
        from scanipy import build_configs_from_args, create_argument_parser

        parser = create_argument_parser()
        args = parser.parse_args(
            [
                "--query",
                "test",
                "--run-codeql",
                "--codeql-queries",
                "custom-queries",
                "--codeql-format",
                "csv",
            ]
        )

        with patch.dict("os.environ", {"GITHUB_TOKEN": "test_token"}):
            _, _, codeql_config, _, _, _ = build_configs_from_args(args)

        assert isinstance(codeql_config, CodeQLConfig)
        assert codeql_config.enabled is True
        assert codeql_config.query_suite == "custom-queries"
        assert codeql_config.output_format == "csv"
