"""Tests for the models module."""

from models import (
    DEFAULT_MAX_PAGES,
    DEFAULT_OUTPUT_FILE,
    DEFAULT_PER_PAGE,
    MAX_DISPLAY_REPOS,
    MAX_FILES_PREVIEW,
    Colors,
    SearchConfig,
    SemgrepConfig,
)


class TestConstants:
    """Tests for module constants."""

    def test_default_max_pages(self):
        """Test DEFAULT_MAX_PAGES has expected value."""
        assert DEFAULT_MAX_PAGES == 5

    def test_default_per_page(self):
        """Test DEFAULT_PER_PAGE has expected value."""
        assert DEFAULT_PER_PAGE == 100

    def test_default_output_file(self):
        """Test DEFAULT_OUTPUT_FILE has expected value."""
        assert DEFAULT_OUTPUT_FILE == "repos.json"

    def test_max_display_repos(self):
        """Test MAX_DISPLAY_REPOS has expected value."""
        assert MAX_DISPLAY_REPOS == 20

    def test_max_files_preview(self):
        """Test MAX_FILES_PREVIEW has expected value."""
        assert MAX_FILES_PREVIEW == 3


class TestColors:
    """Tests for the Colors class."""

    def test_colors_has_header(self):
        """Test Colors has HEADER attribute."""
        assert hasattr(Colors, "HEADER")
        assert Colors.HEADER is not None

    def test_colors_has_success(self):
        """Test Colors has SUCCESS attribute."""
        assert hasattr(Colors, "SUCCESS")
        assert Colors.SUCCESS is not None

    def test_colors_has_warning(self):
        """Test Colors has WARNING attribute."""
        assert hasattr(Colors, "WARNING")
        assert Colors.WARNING is not None

    def test_colors_has_error(self):
        """Test Colors has ERROR attribute."""
        assert hasattr(Colors, "ERROR")
        assert Colors.ERROR is not None

    def test_colors_has_info(self):
        """Test Colors has INFO attribute."""
        assert hasattr(Colors, "INFO")
        assert Colors.INFO is not None

    def test_colors_has_reset(self):
        """Test Colors has RESET attribute."""
        assert hasattr(Colors, "RESET")
        assert Colors.RESET is not None


class TestSearchConfig:
    """Tests for the SearchConfig dataclass."""

    def test_search_config_required_query(self):
        """Test SearchConfig requires query parameter."""
        config = SearchConfig(query="test query")
        assert config.query == "test query"

    def test_search_config_defaults(self):
        """Test SearchConfig has correct default values."""
        config = SearchConfig(query="test")
        assert config.language == ""
        assert config.extension == ""
        assert config.keywords == []
        assert config.additional_params == ""
        assert config.max_pages == DEFAULT_MAX_PAGES
        assert config.per_page == DEFAULT_PER_PAGE

    def test_search_config_with_all_params(self):
        """Test SearchConfig with all parameters specified."""
        config = SearchConfig(
            query="extractall",
            language="python",
            extension=".py",
            keywords=["path", "directory"],
            additional_params="stars:>100",
            max_pages=10,
            per_page=50,
        )
        assert config.query == "extractall"
        assert config.language == "python"
        assert config.extension == ".py"
        assert config.keywords == ["path", "directory"]
        assert config.additional_params == "stars:>100"
        assert config.max_pages == 10
        assert config.per_page == 50

    def test_full_query_basic(self):
        """Test full_query property with just query."""
        config = SearchConfig(query="test query")
        assert config.full_query == "test query"

    def test_full_query_with_language(self):
        """Test full_query property with language."""
        config = SearchConfig(query="test", language="python")
        assert config.full_query == "test language:python"

    def test_full_query_with_extension(self):
        """Test full_query property with extension."""
        config = SearchConfig(query="test", extension=".py")
        assert config.full_query == "test extension:.py"

    def test_full_query_with_additional_params(self):
        """Test full_query property with additional params."""
        config = SearchConfig(query="test", additional_params="stars:>100")
        assert config.full_query == "test stars:>100"

    def test_full_query_with_all_params(self):
        """Test full_query property with all parameters."""
        config = SearchConfig(
            query="test",
            language="python",
            extension=".py",
            additional_params="stars:>100",
        )
        assert config.full_query == "test language:python extension:.py stars:>100"

    def test_keywords_not_in_full_query(self):
        """Test that keywords are not included in full_query."""
        config = SearchConfig(query="test", keywords=["path", "directory"])
        assert "path" not in config.full_query
        assert "directory" not in config.full_query


class TestSemgrepConfig:
    """Tests for the SemgrepConfig dataclass."""

    def test_semgrep_config_defaults(self):
        """Test SemgrepConfig has correct default values."""
        config = SemgrepConfig()
        assert config.enabled is False
        assert config.args == ""
        assert config.rules_path is None
        assert config.clone_dir is None
        assert config.keep_cloned is False
        assert config.use_pro is False

    def test_semgrep_config_enabled(self):
        """Test SemgrepConfig with enabled=True."""
        config = SemgrepConfig(enabled=True)
        assert config.enabled is True

    def test_semgrep_config_with_all_params(self):
        """Test SemgrepConfig with all parameters specified."""
        config = SemgrepConfig(
            enabled=True,
            args="--json --verbose",
            rules_path="/path/to/rules.yaml",
            clone_dir="/tmp/repos",
            keep_cloned=True,
            use_pro=True,
        )
        assert config.enabled is True
        assert config.args == "--json --verbose"
        assert config.rules_path == "/path/to/rules.yaml"
        assert config.clone_dir == "/tmp/repos"
        assert config.keep_cloned is True
        assert config.use_pro is True
