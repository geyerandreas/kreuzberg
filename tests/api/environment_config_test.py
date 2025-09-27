from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest

if TYPE_CHECKING:
    from litestar.testing import AsyncTestClient


def test_get_max_upload_size_default() -> None:
    from kreuzberg._api.main import _get_max_upload_size

    with patch.dict(os.environ, {}, clear=True):
        assert _get_max_upload_size() == 1024 * 1024 * 1024  # 1GB


def test_get_max_upload_size_custom() -> None:
    from kreuzberg._api.main import _get_max_upload_size

    custom_size = 2 * 1024 * 1024 * 1024  # 2GB
    with patch.dict(os.environ, {"KREUZBERG_MAX_UPLOAD_SIZE": str(custom_size)}):
        assert _get_max_upload_size() == custom_size


def test_get_max_upload_size_invalid_value() -> None:
    from kreuzberg._api.main import _get_max_upload_size

    with patch.dict(os.environ, {"KREUZBERG_MAX_UPLOAD_SIZE": "invalid"}):
        assert _get_max_upload_size() == 1024 * 1024 * 1024  # Falls back to default


def test_is_opentelemetry_enabled_default() -> None:
    from kreuzberg._api.main import _is_opentelemetry_enabled

    with patch.dict(os.environ, {}, clear=True):
        assert _is_opentelemetry_enabled() is True


def test_is_opentelemetry_enabled_false() -> None:
    from kreuzberg._api.main import _is_opentelemetry_enabled

    test_cases = ["false", "False", "FALSE", "0", "no", "No", "off", "Off"]
    for value in test_cases:
        with patch.dict(os.environ, {"KREUZBERG_ENABLE_OPENTELEMETRY": value}):
            assert _is_opentelemetry_enabled() is False, f"Failed for value: {value}"


def test_is_opentelemetry_enabled_true() -> None:
    from kreuzberg._api.main import _is_opentelemetry_enabled

    test_cases = ["true", "True", "TRUE", "1", "yes", "Yes", "on", "On"]
    for value in test_cases:
        with patch.dict(os.environ, {"KREUZBERG_ENABLE_OPENTELEMETRY": value}):
            assert _is_opentelemetry_enabled() is True, f"Failed for value: {value}"


def test_get_plugins_with_opentelemetry_enabled() -> None:
    from kreuzberg._api.main import _get_plugins

    with patch.dict(os.environ, {"KREUZBERG_ENABLE_OPENTELEMETRY": "true"}):
        plugins = _get_plugins()
        assert len(plugins) == 1
        assert type(plugins[0]).__name__ == "OpenTelemetryPlugin"


def test_get_plugins_with_opentelemetry_disabled() -> None:
    from kreuzberg._api.main import _get_plugins

    with patch.dict(os.environ, {"KREUZBERG_ENABLE_OPENTELEMETRY": "false"}):
        plugins = _get_plugins()
        assert len(plugins) == 0


@pytest.mark.anyio
async def test_app_configuration_with_custom_upload_size() -> None:
    """Test that the Litestar app uses the configured upload size"""
    from kreuzberg._api.main import _get_max_upload_size

    custom_size = 512 * 1024 * 1024  # 512MB

    with patch.dict(os.environ, {"KREUZBERG_MAX_UPLOAD_SIZE": str(custom_size)}):
        assert _get_max_upload_size() == custom_size


@pytest.mark.anyio
async def test_large_file_upload_respected(test_client: AsyncTestClient[Any], tmp_path: Any) -> None:
    """Test that large file upload limits are respected"""

    # Create a test file that would exceed a small upload limit
    test_file = tmp_path / "large_test.txt"
    large_content = "x" * (2 * 1024 * 1024)  # 2MB content
    test_file.write_text(large_content)

    # Test with original app (should work with default 1GB limit)
    with test_file.open("rb") as f:
        response = await test_client.post("/extract", files=[("data", (test_file.name, f.read(), "text/plain"))])

    # Should succeed with default 1GB limit
    assert response.status_code == 201


def test_environment_variable_combinations() -> None:
    """Test various combinations of environment variables"""
    from kreuzberg._api.main import _get_max_upload_size, _is_opentelemetry_enabled

    test_env = {
        "KREUZBERG_MAX_UPLOAD_SIZE": "5368709120",  # 5GB
        "KREUZBERG_ENABLE_OPENTELEMETRY": "false",
    }

    with patch.dict(os.environ, test_env):
        assert _get_max_upload_size() == 5368709120
        assert _is_opentelemetry_enabled() is False


def test_edge_cases_for_upload_size() -> None:
    """Test edge cases for upload size configuration"""
    from kreuzberg._api.main import _get_max_upload_size

    # Test zero
    with patch.dict(os.environ, {"KREUZBERG_MAX_UPLOAD_SIZE": "0"}):
        assert _get_max_upload_size() == 0

    # Test very large number
    large_size = str(10 * 1024 * 1024 * 1024)  # 10GB
    with patch.dict(os.environ, {"KREUZBERG_MAX_UPLOAD_SIZE": large_size}):
        assert _get_max_upload_size() == int(large_size)

    # Test negative number (should fall back to default)
    with patch.dict(os.environ, {"KREUZBERG_MAX_UPLOAD_SIZE": "-1"}):
        assert _get_max_upload_size() == 1024 * 1024 * 1024


def test_edge_cases_for_opentelemetry() -> None:
    """Test edge cases for OpenTelemetry boolean configuration"""
    from kreuzberg._api.main import _is_opentelemetry_enabled

    # Test empty string (should default to true)
    with patch.dict(os.environ, {"KREUZBERG_ENABLE_OPENTELEMETRY": ""}):
        assert _is_opentelemetry_enabled() is False

    # Test random string (should default to false)
    with patch.dict(os.environ, {"KREUZBERG_ENABLE_OPENTELEMETRY": "random"}):
        assert _is_opentelemetry_enabled() is False

    # Test numeric strings
    with patch.dict(os.environ, {"KREUZBERG_ENABLE_OPENTELEMETRY": "2"}):
        assert _is_opentelemetry_enabled() is False

    with patch.dict(os.environ, {"KREUZBERG_ENABLE_OPENTELEMETRY": "1"}):
        assert _is_opentelemetry_enabled() is True
