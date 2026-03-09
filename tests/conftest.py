"""Shared fixtures for Granola MCP server tests."""

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from mcp_granola.data import GranolaData
from mcp_granola.server import mcp

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture()
def fixture_data() -> dict[str, Any]:
    """Load the test fixture cache-v3.json and return parsed state."""
    fixture_path = FIXTURES_DIR / "cache-v3.json"
    raw = json.loads(fixture_path.read_text())
    return json.loads(raw["cache"])["state"]


@pytest.fixture()
def granola_data(fixture_data: dict[str, Any]) -> GranolaData:
    """Create a GranolaData instance backed by fixture data.

    Patches the singleton and file loading to use test fixtures.
    """
    # Reset singleton state
    GranolaData._instance = None
    GranolaData._data = None
    GranolaData._last_modified = None
    GranolaData._search_cache = None

    instance = GranolaData()
    instance._data = fixture_data
    instance._last_modified = 1.0  # Prevent reload attempts
    return instance


@pytest.fixture()
def mcp_server(granola_data: GranolaData):
    """Provide the FastMCP server with data patched to use fixtures."""
    with patch("mcp_granola.server.get_data", return_value=granola_data):
        yield mcp


@pytest.fixture(autouse=True)
def _reset_singleton():
    """Reset the GranolaData singleton between tests."""
    yield
    GranolaData._instance = None
    GranolaData._data = None
    GranolaData._last_modified = None
    GranolaData._search_cache = None
