"""Shared fixtures for API tests."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from kreuzberg._api.main import app

if TYPE_CHECKING:
    from litestar.testing import AsyncTestClient


@pytest.fixture
def test_client() -> AsyncTestClient[Any]:
    """Create a test client for the API."""
    from litestar.testing import AsyncTestClient

    return AsyncTestClient(app=app)
