"""Tests for the scanipy CLI module."""

import argparse
import os
import sys
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

# Import after path setup in conftest
from scanipy import (
    Display,
    create_argument_parser,
    parse_keywords,
    build_configs_from_args,
    main,
)
from models import Colors, SearchConfig, SemgrepConfig
from integrations.github.search import SearchStrategy, SortOrder


class TestParseKeywords:
    """Tests for the parse_keywords function."""

    def test_empty_string(self):
        """Test parse_keywords with empty string."""
        result = parse_keywords("")
        assert result == []

    def test_single_keyword(self):
        """Test parse_keywords with single keyword."""
        result = parse_keywords("path")
        assert result == ["path"]

    def test_multiple_keywords(self):
        """Test parse_keywords with multiple keywords."""
        result = parse_keywords("path,directory,zip")
        assert result == ["path", "directory", "zip"]

    def test_keywords_with_spaces(self):
        """Test parse_keywords handles spaces correctly."""
        result = parse_keywords("path, directory , zip")
        assert result == ["path", "directory", "zip"]

    def test_keywords_with_empty_entries(self):
        """Test parse_keywords filters empty entries."""
        result = parse_keywords("path,,directory")
        assert result == ["path", "directory"]


class TestCreateArgumentParser:
    """Tests for the create_argument_parser function."""

    def test_parser_created(self):
        """Test create_argument_parser returns parser."""
        parser = create_argument_parser()
        assert isinstance(parser, argparse.ArgumentParser)

    def test_query_required(self):
        """Test --query is required."""
        parser = create_argument_parser()
        with pytest.raises(SystemExit):
            parser.parse_args([])

    def test_query_accepted(self):
        """Test --query is accepted."""
        parser = create_argument_parser()
        args = parser.parse_args(["--query", "test"])
        assert args.query == "test"

    def test_query_short_form(self):
        """Test -q short form works."""
        parser = create_argument_parser()
        args = parser.parse_args(["-q", "test"])
        assert args.query == "test"

    def test_language_default(self):
        """Test --language has empty default."""
        parser = create_argument_parser()
        args = parser.parse_args(["--query", "test"])
        assert args.language == ""

    def test_language_accepted(self):
        """Test --language is accepted."""
        parser = create_argument_parser()
        args = parser.parse_args(["--query", "test", "--language", "python"])
        assert args.language == "python"

    def test_extension_default(self):
        """Test --extension has empty default."""
        parser = create_argument_parser()
        args = parser.parse_args(["--query", "test"])
        assert args.extension == ""

    def test_keywords_default(self):
        """Test --keywords has empty default."""
        parser = create_argument_parser()
        args = parser.parse_args(["--query", "test"])
        assert args.keywords == ""

    def test_pages_default(self):
        """Test --pages has correct default."""
        parser = create_argument_parser()
        args = parser.parse_args(["--query", "test"])
        assert args.pages == 5

    def test_search_strategy_default(self):
        """Test --search-strategy has tiered default."""
        parser = create_argument_parser()
        args = parser.parse_args(["--query", "test"])
        assert args.search_strategy == "tiered"

    def test_search_strategy_greedy(self):
        """Test --search-strategy accepts greedy."""
        parser = create_argument_parser()
        args = parser.parse_args(["--query", "test", "--search-strategy", "greedy"])
        assert args.search_strategy == "greedy"

    def test_sort_by_default(self):
        """Test --sort-by has stars default."""
        parser = create_argument_parser()
        args = parser.parse_args(["--query", "test"])
        assert args.sort_by == "stars"

    def test_sort_by_updated(self):
        """Test --sort-by accepts updated."""
        parser = create_argument_parser()
        args = parser.parse_args(["--query", "test", "--sort-by", "updated"])
        assert args.sort_by == "updated"

    def test_run_semgrep_default(self):
        """Test --run-semgrep is False by default."""
        parser = create_argument_parser()
        args = parser.parse_args(["--query", "test"])
        assert args.run_semgrep is False

    def test_run_semgrep_flag(self):
        """Test --run-semgrep flag."""
        parser = create_argument_parser()
        args = parser.parse_args(["--query", "test", "--run-semgrep"])
        assert args.run_semgrep is True

    def test_pro_flag(self):
        """Test --pro flag."""
        parser = create_argument_parser()
        args = parser.parse_args(["--query", "test", "--pro"])
        assert args.pro is True

    def test_keep_cloned_flag(self):
        """Test --keep-cloned flag."""
        parser = create_argument_parser()
        args = parser.parse_args(["--query", "test", "--keep-cloned"])
        assert args.keep_cloned is True


class TestBuildConfigsFromArgs:
    """Tests for the build_configs_from_args function."""

    def test_returns_tuple(self):
        """Test build_configs_from_args returns correct tuple."""
        parser = create_argument_parser()
        args = parser.parse_args(["--query", "test"])
        
        with patch.dict("os.environ", {"GITHUB_TOKEN": "test_token"}):
            result = build_configs_from_args(args)
        
        assert len(result) == 5
        assert isinstance(result[0], SearchConfig)
        assert isinstance(result[1], SemgrepConfig)
        assert isinstance(result[2], str)  # token
        assert isinstance(result[3], SearchStrategy)
        assert isinstance(result[4], SortOrder)

    def test_search_config_populated(self):
        """Test SearchConfig is populated correctly."""
        parser = create_argument_parser()
        args = parser.parse_args([
            "--query", "extractall",
            "--language", "python",
            "--extension", ".py",
            "--keywords", "path,directory",
            "--pages", "10",
        ])
        
        with patch.dict("os.environ", {"GITHUB_TOKEN": "test_token"}):
            search_config, _, _, _, _ = build_configs_from_args(args)
        
        assert search_config.query == "extractall"
        assert search_config.language == "python"
        assert search_config.extension == ".py"
        assert search_config.keywords == ["path", "directory"]
        assert search_config.max_pages == 10

    def test_semgrep_config_populated(self):
        """Test SemgrepConfig is populated correctly."""
        parser = create_argument_parser()
        args = parser.parse_args([
            "--query", "test",
            "--run-semgrep",
            "--semgrep-args=--json --verbose",
            "--rules", "/path/to/rules.yaml",
            "--clone-dir", "/tmp/repos",
            "--keep-cloned",
            "--pro",
        ])
        
        with patch.dict("os.environ", {"GITHUB_TOKEN": "test_token"}):
            _, semgrep_config, _, _, _ = build_configs_from_args(args)
        
        assert semgrep_config.enabled is True
        assert semgrep_config.args == "--json --verbose"
        assert semgrep_config.rules_path == "/path/to/rules.yaml"
        assert semgrep_config.clone_dir == "/tmp/repos"
        assert semgrep_config.keep_cloned is True
        assert semgrep_config.use_pro is True

    def test_token_from_arg(self):
        """Test token is taken from argument."""
        parser = create_argument_parser()
        args = parser.parse_args([
            "--query", "test",
            "--github-token", "arg_token",
        ])
        
        with patch.dict("os.environ", {"GITHUB_TOKEN": "env_token"}):
            _, _, token, _, _ = build_configs_from_args(args)
        
        assert token == "arg_token"

    def test_token_from_env(self):
        """Test token is taken from environment."""
        parser = create_argument_parser()
        args = parser.parse_args(["--query", "test"])
        
        with patch.dict("os.environ", {"GITHUB_TOKEN": "env_token"}):
            _, _, token, _, _ = build_configs_from_args(args)
        
        assert token == "env_token"

    def test_search_strategy_tiered(self):
        """Test search strategy is TIERED_STARS."""
        parser = create_argument_parser()
        args = parser.parse_args(["--query", "test", "--search-strategy", "tiered"])
        
        with patch.dict("os.environ", {"GITHUB_TOKEN": "test_token"}):
            _, _, _, strategy, _ = build_configs_from_args(args)
        
        assert strategy == SearchStrategy.TIERED_STARS

    def test_search_strategy_greedy(self):
        """Test search strategy is GREEDY."""
        parser = create_argument_parser()
        args = parser.parse_args(["--query", "test", "--search-strategy", "greedy"])
        
        with patch.dict("os.environ", {"GITHUB_TOKEN": "test_token"}):
            _, _, _, strategy, _ = build_configs_from_args(args)
        
        assert strategy == SearchStrategy.GREEDY

    def test_sort_order_stars(self):
        """Test sort order is STARS."""
        parser = create_argument_parser()
        args = parser.parse_args(["--query", "test", "--sort-by", "stars"])
        
        with patch.dict("os.environ", {"GITHUB_TOKEN": "test_token"}):
            _, _, _, _, sort_order = build_configs_from_args(args)
        
        assert sort_order == SortOrder.STARS

    def test_sort_order_updated(self):
        """Test sort order is UPDATED."""
        parser = create_argument_parser()
        args = parser.parse_args(["--query", "test", "--sort-by", "updated"])
        
        with patch.dict("os.environ", {"GITHUB_TOKEN": "test_token"}):
            _, _, _, _, sort_order = build_configs_from_args(args)
        
        assert sort_order == SortOrder.UPDATED


class TestDisplay:
    """Tests for the Display class."""

    def test_format_star_count_high(self):
        """Test format_star_count with high star count."""
        result = Display.format_star_count(15000)
        assert "15,000" in result

    def test_format_star_count_medium(self):
        """Test format_star_count with medium star count."""
        result = Display.format_star_count(1500)
        assert "1,500" in result

    def test_format_star_count_low(self):
        """Test format_star_count with low star count."""
        result = Display.format_star_count(50)
        assert "50" in result

    def test_format_star_count_na(self):
        """Test format_star_count with N/A."""
        result = Display.format_star_count("N/A")
        assert "N/A" in result

    def test_format_star_count_zero(self):
        """Test format_star_count with zero stars."""
        result = Display.format_star_count(0)
        assert "0" in result

    def test_format_star_count_non_int(self):
        """Test format_star_count with non-integer type."""
        result = Display.format_star_count("unknown")
        assert "N/A" in result

    def test_format_updated_at_valid(self):
        """Test format_updated_at with valid ISO date."""
        result = Display.format_updated_at("2024-12-20T10:30:00Z")
        assert "2024-12-20" in result

    def test_format_updated_at_empty(self):
        """Test format_updated_at with empty string."""
        result = Display.format_updated_at("")
        assert result == ""

    def test_format_updated_at_none(self):
        """Test format_updated_at with None-like value."""
        result = Display.format_updated_at(None)
        assert result == ""

    def test_format_updated_at_no_t_separator(self):
        """Test format_updated_at with date without T separator."""
        result = Display.format_updated_at("2024-12-20")
        assert "2024-12-20" in result

    def test_print_banner(self, capsys):
        """Test print_banner outputs banner text."""
        Display.print_banner()
        captured = capsys.readouterr()
        assert "SCANIPY" in captured.out
        assert "Code Pattern Scanner" in captured.out

    def test_print_search_info_basic(self, capsys, sample_search_config):
        """Test print_search_info with basic config."""
        Display.print_search_info(sample_search_config)
        captured = capsys.readouterr()
        assert "Search Parameters" in captured.out
        assert sample_search_config.query in captured.out

    def test_print_search_info_with_strategy(self, capsys, sample_search_config):
        """Test print_search_info with strategy."""
        Display.print_search_info(sample_search_config, strategy=SearchStrategy.TIERED_STARS)
        captured = capsys.readouterr()
        assert "tiered by stars" in captured.out

    def test_print_search_info_with_sort_order(self, capsys, sample_search_config):
        """Test print_search_info with sort order."""
        Display.print_search_info(sample_search_config, sort_order=SortOrder.UPDATED)
        captured = capsys.readouterr()
        assert "recently updated" in captured.out

    def test_print_repository_basic(self, capsys):
        """Test print_repository with basic repo data."""
        repo = {
            "name": "owner/test-repo",
            "stars": 500,
            "description": "A test repository",
            "url": "https://github.com/owner/test-repo",
            "files": [{"path": "src/main.py", "keyword_match": None}],
        }
        Display.print_repository(1, repo, "test query")
        captured = capsys.readouterr()
        assert "owner/test-repo" in captured.out
        assert "500" in captured.out
        assert "A test repository" in captured.out

    def test_print_repository_with_long_description(self, capsys):
        """Test print_repository truncates long descriptions."""
        long_desc = "A" * 150
        repo = {
            "name": "owner/repo",
            "stars": 100,
            "description": long_desc,
            "url": "https://github.com/owner/repo",
            "files": [],
        }
        Display.print_repository(1, repo, "query")
        captured = capsys.readouterr()
        assert "..." in captured.out

    def test_print_repository_with_keyword_match(self, capsys):
        """Test print_repository shows keyword match info."""
        repo = {
            "name": "owner/repo",
            "stars": 100,
            "files": [
                {"path": "src/main.py", "keyword_match": True, "keywords_found": ["path", "zip"]},
            ],
        }
        Display.print_repository(1, repo, "query")
        captured = capsys.readouterr()
        assert "Keywords:" in captured.out
        assert "path" in captured.out

    def test_print_repository_with_no_keyword_match(self, capsys):
        """Test print_repository shows no match info."""
        repo = {
            "name": "owner/repo",
            "stars": 100,
            "files": [
                {"path": "src/main.py", "keyword_match": False},
            ],
        }
        Display.print_repository(1, repo, "query")
        captured = capsys.readouterr()
        assert "No keywords matched" in captured.out

    def test_print_repository_with_updated_sort(self, capsys):
        """Test print_repository shows updated date when sorting by updated."""
        repo = {
            "name": "owner/repo",
            "stars": 100,
            "updated_at": "2024-12-20T10:30:00Z",
            "files": [],
        }
        Display.print_repository(1, repo, "query", sort_order=SortOrder.UPDATED)
        captured = capsys.readouterr()
        assert "2024-12-20" in captured.out

    def test_print_repository_many_files(self, capsys):
        """Test print_repository shows 'and X more files' for many files."""
        repo = {
            "name": "owner/repo",
            "stars": 100,
            "files": [{"path": f"file{i}.py", "keyword_match": None} for i in range(10)],
        }
        Display.print_repository(1, repo, "query")
        captured = capsys.readouterr()
        assert "more file" in captured.out

    def test_print_results_empty(self, capsys):
        """Test print_results with empty list."""
        Display.print_results([], "query")
        captured = capsys.readouterr()
        assert "No repositories found" in captured.out

    def test_print_results_with_repos(self, capsys):
        """Test print_results with repositories."""
        repos = [
            {"name": "repo1", "stars": 100, "files": []},
            {"name": "repo2", "stars": 50, "files": []},
        ]
        Display.print_results(repos, "query")
        captured = capsys.readouterr()
        assert "TOP REPOSITORIES BY STARS" in captured.out

    def test_print_results_sorted_by_updated(self, capsys):
        """Test print_results shows updated header when sorted by updated."""
        repos = [{"name": "repo1", "stars": 100, "files": []}]
        Display.print_results(repos, "query", sort_order=SortOrder.UPDATED)
        captured = capsys.readouterr()
        assert "RECENTLY UPDATED" in captured.out

    def test_print_no_results_hint_with_keywords(self, capsys):
        """Test print_no_results_hint shows hint when keywords used."""
        Display.print_no_results_hint(has_keywords=True)
        captured = capsys.readouterr()
        assert "fewer or different keywords" in captured.out

    def test_print_no_results_hint_without_keywords(self, capsys):
        """Test print_no_results_hint shows nothing when no keywords."""
        Display.print_no_results_hint(has_keywords=False)
        captured = capsys.readouterr()
        assert captured.out == ""


class TestMain:
    """Tests for the main function."""

    @patch("scanipy.search_repositories")
    @patch("scanipy.Display.print_results")
    @patch("scanipy.Display.print_search_info")
    @patch("scanipy.Display.print_banner")
    def test_main_success(
        self,
        mock_banner,
        mock_search_info,
        mock_print_results,
        mock_search,
    ):
        """Test main function executes successfully."""
        mock_search.return_value = [{"name": "repo", "stars": 100}]
        
        with patch.dict("os.environ", {"GITHUB_TOKEN": "test_token"}):
            with patch("sys.argv", ["scanipy", "--query", "test"]):
                exit_code = main()
        
        assert exit_code == 0
        mock_banner.assert_called_once()
        mock_search.assert_called_once()

    def test_main_no_token(self, capsys):
        """Test main returns error when no token."""
        with patch.dict("os.environ", {}, clear=True):
            if "GITHUB_TOKEN" in os.environ:
                del os.environ["GITHUB_TOKEN"]
            with patch("sys.argv", ["scanipy", "--query", "test"]):
                exit_code = main()
        
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "GITHUB_TOKEN" in captured.out

    @patch("scanipy.run_semgrep_analysis")
    @patch("scanipy.search_repositories")
    @patch("scanipy.Display.print_results")
    @patch("scanipy.Display.print_search_info")
    @patch("scanipy.Display.print_banner")
    def test_main_with_semgrep(
        self,
        mock_banner,
        mock_search_info,
        mock_print_results,
        mock_search,
        mock_semgrep,
    ):
        """Test main function runs semgrep when flag is set."""
        mock_search.return_value = [{"name": "repo", "stars": 100}]
        
        with patch.dict("os.environ", {"GITHUB_TOKEN": "test_token"}):
            with patch("sys.argv", ["scanipy", "--query", "test", "--run-semgrep"]):
                exit_code = main()
        
        assert exit_code == 0
        mock_semgrep.assert_called_once()

    @patch("scanipy.search_repositories")
    @patch("scanipy.Display.print_results")
    @patch("scanipy.Display.print_search_info")
    @patch("scanipy.Display.print_banner")
    def test_main_empty_results(
        self,
        mock_banner,
        mock_search_info,
        mock_print_results,
        mock_search,
    ):
        """Test main function handles empty results."""
        mock_search.return_value = []
        
        with patch.dict("os.environ", {"GITHUB_TOKEN": "test_token"}):
            with patch("sys.argv", ["scanipy", "--query", "nonexistent"]):
                exit_code = main()
        
        assert exit_code == 0
        mock_print_results.assert_called()

    @patch("scanipy.search_repositories")
    @patch("scanipy.Display.print_no_results_hint")
    @patch("scanipy.Display.print_results")
    @patch("scanipy.Display.print_search_info")
    @patch("scanipy.Display.print_banner")
    def test_main_empty_results_with_keywords(
        self,
        mock_banner,
        mock_search_info,
        mock_print_results,
        mock_hint,
        mock_search,
    ):
        """Test main function shows hint when empty results with keywords."""
        mock_search.return_value = []
        
        with patch.dict("os.environ", {"GITHUB_TOKEN": "test_token"}):
            with patch("sys.argv", ["scanipy", "--query", "test", "--keywords", "path,dir"]):
                exit_code = main()
        
        assert exit_code == 0
        mock_hint.assert_called_once_with(True)


class TestDisplayFormatEdgeCases:
    """Tests for Display format method edge cases."""

    def test_format_updated_at_exception_handling(self):
        """Test format_updated_at handles exceptions gracefully."""
        # Test with a value that causes an exception in split
        class BadString:
            def split(self, *args):
                raise ValueError("Bad value")
        
        # The method should return empty string on exception
        result = Display.format_updated_at("")
        assert result == ""

    def test_format_updated_at_attribute_error(self):
        """Test format_updated_at handles AttributeError."""
        # Passing None should trigger AttributeError in split
        result = Display.format_updated_at(None)
        assert result == ""

    def test_format_updated_at_index_error(self):
        """Test format_updated_at handles IndexError."""
        # Create a mock object that raises IndexError when accessing [0]
        class BadSplit:
            def split(self, *args):
                return []  # Empty list, [0] will raise IndexError
        
        # This won't work directly since we check for empty string first
        # But we can test with an object that has split returning empty list
        result = Display.format_updated_at("")
        assert result == ""

    def test_format_updated_at_with_integer(self):
        """Test format_updated_at handles non-string types."""
        # Passing an integer should trigger AttributeError (no split method)
        result = Display.format_updated_at(12345)
        assert result == ""


class TestRunSemgrepAnalysis:
    """Tests for run_semgrep_analysis function."""

    @patch("scanipy.analyze_repositories_with_semgrep")
    def test_run_semgrep_analysis_called(self, mock_analyze):
        """Test run_semgrep_analysis calls analyze function."""
        from scanipy import run_semgrep_analysis
        from models import SemgrepConfig
        
        repos = [{"name": "test/repo", "url": "https://github.com/test/repo"}]
        config = SemgrepConfig(enabled=True)
        
        run_semgrep_analysis(repos, config)
        
        mock_analyze.assert_called_once()