"""Tests for ImportError handling in modules with optional dependencies."""

from __future__ import annotations

import importlib
import sys
from unittest.mock import patch


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

                # Verify that placeholder classes are created when BaseModel is None
                assert api_module.CreateScanRequest is None
                assert api_module.AddReposRequest is None
        finally:
            # Restore by removing from sys.modules - next import will be fresh
            sys.modules.pop("services.api.api", None)
