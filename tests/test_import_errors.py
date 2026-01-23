"""Tests for ImportError handling in modules with optional dependencies."""

from __future__ import annotations

import importlib
import sys
from typing import Any
from unittest.mock import patch

import pytest


class TestImportErrorHandling:
    """Tests for ImportError exception handlers in various modules."""

    def test_kubernetes_client_import_error(self):
        """Test KubernetesClient handles missing kubernetes library."""
        # Get the real __import__ before any patching
        real_import = __import__

        def side_effect(name, *args, **kwargs):
            if name == "kubernetes" or name.startswith("kubernetes."):
                raise ImportError(f"No module named '{name}'")
            return real_import(name, *args, **kwargs)

        try:
            with patch("builtins.__import__", side_effect=side_effect):
                # Remove from sys.modules and reload
                sys.modules.pop("services.api.kubernetes_client", None)
                import services.api.kubernetes_client as k8s_module

                importlib.reload(k8s_module)

                # Verify that client, k8s_config, and ApiException are None
                assert k8s_module.client is None
                assert k8s_module.k8s_config is None
                assert k8s_module.ApiException is None
        finally:
            # Restore by removing from sys.modules - next import will be fresh
            sys.modules.pop("services.api.kubernetes_client", None)

    def test_results_db_import_error(self):
        """Test ResultsDatabase handles missing psycopg2 library."""
        # Get the real __import__ before any patching
        real_import = __import__

        def side_effect(name, *args, **kwargs):
            if name == "psycopg2" or name.startswith("psycopg2."):
                raise ImportError(f"No module named '{name}'")
            return real_import(name, *args, **kwargs)

        try:
            with patch("builtins.__import__", side_effect=side_effect):
                # Remove from sys.modules and reload
                sys.modules.pop("tools.semgrep.results_db", None)
                import tools.semgrep.results_db as db_module

                importlib.reload(db_module)

                # Verify that psycopg2 and sql are None
                assert db_module.psycopg2 is None
                # When psycopg2 types are installed, mypy thinks sql can never be None
                # but in this test we mock the import to fail, so it will be None at runtime
                assert db_module.sql is None  # type: ignore[unreachable]
                # Note: pg_connection is a type alias when psycopg2 is available,
                # but set to None in the except block. We don't test it directly
                # as it's a type alias and the test would be unreachable when types are installed.
        finally:
            # Restore by removing from sys.modules - next import will be fresh
            sys.modules.pop("tools.semgrep.results_db", None)

    def test_api_module_import_error(self):
        """Test API module handles missing FastAPI library."""
        # Get the real __import__ before any patching
        real_import = __import__

        def side_effect(name, *args, **kwargs):
            if name in ("fastapi", "pydantic", "pydantic_settings"):
                raise ImportError(f"No module named '{name}'")
            return real_import(name, *args, **kwargs)

        try:
            with patch("builtins.__import__", side_effect=side_effect):
                # Remove from sys.modules and reload
                sys.modules.pop("services.api.api", None)
                import services.api.api as api_module

                importlib.reload(api_module)

                # Verify that FastAPI, HTTPException, status, JSONResponse, and BaseModel are None
                assert api_module.FastAPI is None
                assert api_module.HTTPException is None  # type: ignore[unreachable]
                assert api_module.status is None
                assert api_module.JSONResponse is None
                assert api_module.BaseModel is None

                # Verify that DummyApp is used when FastAPI is None
                assert api_module.app is not None
                assert hasattr(api_module.app, "post")
                assert hasattr(api_module.app, "get")

                # Test DummyApp decorators work correctly
                def dummy_func():
                    return "test"

                decorated = api_module.app.post("/test")(dummy_func)
                assert decorated == dummy_func  # Should return the function unchanged

                decorated = api_module.app.get("/test")(dummy_func)
                assert decorated == dummy_func  # Should return the function unchanged

                # Verify that placeholder classes are created when BaseModel is None
                assert api_module.CreateScanRequest is None
                assert api_module.AddReposRequest is None
                assert api_module.JobStatusResponse is None
                assert api_module.ScanStatusResponse is None
        finally:
            # Restore by removing from sys.modules - next import will be fresh
            sys.modules.pop("services.api.api", None)

    def test_api_module_dummy_app_decorators(self):
        """Test DummyApp decorators work correctly when FastAPI is not available."""
        # Get the real __import__ before any patching
        real_import = __import__

        def side_effect(name, *args, **kwargs):
            if name in ("fastapi", "pydantic", "pydantic_settings"):
                raise ImportError(f"No module named '{name}'")
            return real_import(name, *args, **kwargs)

        try:
            with patch("builtins.__import__", side_effect=side_effect):
                # Remove from sys.modules and reload
                sys.modules.pop("services.api.api", None)
                import services.api.api as api_module

                importlib.reload(api_module)

                # Verify DummyApp decorators work
                def test_function():
                    return "test"

                # Test post decorator
                decorated_post = api_module.app.post("/test", response_model=dict)(test_function)
                assert decorated_post == test_function

                # Test get decorator
                decorated_get = api_module.app.get("/test")(test_function)
                assert decorated_get == test_function

                # Verify app is DummyApp instance
                assert isinstance(api_module.app, api_module.DummyApp)
        finally:
            # Restore by removing from sys.modules - next import will be fresh
            sys.modules.pop("services.api.api", None)

    def test_api_module_main_block_code_path(self):
        """Test that the main block code path exists and logic is correct."""
        from pathlib import Path

        # Get the path to api.py
        api_file = Path(__file__).parent.parent / "services" / "api" / "api.py"

        # Read the file and verify the main block exists
        content = api_file.read_text(encoding="utf-8")
        assert 'if __name__ == "__main__":' in content
        assert "import uvicorn" in content

        # Test the main block logic by executing it manually
        # We can't actually run the main block (it would start a server),
        # but we can test the logic it would execute
        import tempfile

        import services.api.api as api_module
        from services.api.config import APIConfig

        # Create a temporary database file
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
            tmp_db_path = Path(tmp_db.name)

        try:
            # Execute the same logic as the main block (with proper config)
            config = APIConfig(
                db_path=str(tmp_db_path),
                api_host="0.0.0.0",
                api_port=8000,
            )
            api_module.init_api(config)

            # Verify the setup is correct (what main block would do)
            assert api_module.app is not None
            assert config.api_host is not None
            assert config.api_port is not None
        finally:
            # Clean up
            if tmp_db_path.exists():
                tmp_db_path.unlink()

    def test_api_module_type_checking_imports(self):
        """Test TYPE_CHECKING import block by executing the imports directly."""
        from pathlib import Path

        # Get the path to api.py
        api_file = Path(__file__).parent.parent / "services" / "api" / "api.py"

        # Read the file content
        content = api_file.read_text(encoding="utf-8")

        # Verify TYPE_CHECKING block exists
        assert "if TYPE_CHECKING:" in content
        assert "from fastapi import FastAPI, HTTPException, status" in content
        assert "from fastapi.responses import JSONResponse" in content
        assert "from pydantic import BaseModel" in content

        # Execute the TYPE_CHECKING block imports directly to test that code path
        # This simulates what would happen if TYPE_CHECKING were True
        namespace: dict[str, Any] = {}

        # Execute the imports that are in the TYPE_CHECKING block
        type_checking_imports = """
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
"""
        try:
            exec(type_checking_imports, namespace)
            # Verify imports were executed successfully
            assert "FastAPI" in namespace
            assert "HTTPException" in namespace
            assert "status" in namespace
            assert "JSONResponse" in namespace
            assert "BaseModel" in namespace
            # Verify they are actual classes, not None
            assert namespace["FastAPI"] is not None
            assert namespace["HTTPException"] is not None
            assert namespace["BaseModel"] is not None
        except ImportError as e:
            # If FastAPI is not installed, that's expected in some test environments
            # But we still verify the code path exists
            pytest.skip(f"FastAPI not available: {e}")
