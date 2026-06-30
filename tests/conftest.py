"""Test configuration and shared fixtures for TCAI.

All paths are derived from __file__, never hardcoded.
"""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def project_root() -> Path:
    """Project root directory, derived from conftest.py location."""
    return Path(__file__).resolve().parent.parent


@pytest.fixture
def test_fixtures() -> Path:
    """Directory containing fixed test data files."""
    return Path(__file__).resolve().parent / "fixtures"
