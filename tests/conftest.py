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
def fixture_data_v6() -> dict[str, Any]:
    """Load the test fixture cache-v6.json and return parsed state."""
    fixture_path = FIXTURES_DIR / "cache-v6.json"
    raw = json.loads(fixture_path.read_text())
    # v6: cache is already a dict, not a JSON string
    return raw["cache"]["state"]


def _make_granola_data(data: dict[str, Any]) -> GranolaData:
    """Create a GranolaData instance backed by fixture data."""
    GranolaData._instance = None
    GranolaData._data = None
    GranolaData._last_modified = None
    GranolaData._search_cache = None
    GranolaData._cache_path = None

    instance = GranolaData()
    instance._data = data
    instance._last_modified = 1.0  # Prevent reload attempts
    return instance


@pytest.fixture()
def granola_data(fixture_data: dict[str, Any]) -> GranolaData:
    """Create a GranolaData instance backed by v3 fixture data."""
    return _make_granola_data(fixture_data)


@pytest.fixture()
def granola_data_v6(fixture_data_v6: dict[str, Any]) -> GranolaData:
    """Create a GranolaData instance backed by v6 fixture data."""
    return _make_granola_data(fixture_data_v6)


@pytest.fixture()
def mcp_server(granola_data: GranolaData):
    """Provide the FastMCP server with data patched to use v3 fixtures."""
    with patch("mcp_granola.server.get_data", return_value=granola_data):
        yield mcp


@pytest.fixture()
def mcp_server_v6(granola_data_v6: GranolaData):
    """Provide the FastMCP server with data patched to use v6 fixtures."""
    with patch("mcp_granola.server.get_data", return_value=granola_data_v6):
        yield mcp


@pytest.fixture(autouse=True)
def _reset_singleton():
    """Reset the GranolaData singleton between tests."""
    yield
    GranolaData._instance = None
    GranolaData._data = None
    GranolaData._last_modified = None
    GranolaData._search_cache = None
    GranolaData._cache_path = None
