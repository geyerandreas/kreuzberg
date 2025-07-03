from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest
from litestar.testing import AsyncTestClient

from kreuzberg.docker.main import app

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def test_client() -> AsyncTestClient:
    return AsyncTestClient(app=app)


@pytest.mark.anyio
async def test_health_check(test_client: AsyncTestClient) -> None:
    response = await test_client.post("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.anyio
async def test_extract_from_file(test_client: AsyncTestClient, tmp_path: Path) -> None:
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello world")

    with test_file.open("rb") as f:
        response = await test_client.post("/extract", files={"file": f})

    assert response.status_code == 200
    data = response.json()
    assert data["content"] == "hello world\n"
    assert data["mime_type"] == "text/plain"


@pytest.mark.anyio
async def test_extract_from_file_extraction_error(test_client: AsyncTestClient, tmp_path: Path) -> None:
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello world")

    with patch("kreuzberg.docker.main.extract_bytes", new_callable=AsyncMock) as mock_extract:
        mock_extract.side_effect = Exception("Test error")
        with test_file.open("rb") as f:
            response = await test_client.post("/extract", files={"file": f})

    assert response.status_code == 500
    assert "An internal server error occurred." in response.text
