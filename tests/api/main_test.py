from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, Mock, patch

import pytest
from litestar.testing import AsyncTestClient

from kreuzberg._api.main import app, exception_handler
from kreuzberg.exceptions import OCRError, ParsingError, ValidationError

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def test_client() -> AsyncTestClient[Any]:
    return AsyncTestClient(app=app)


@pytest.mark.anyio
async def test_health_check(test_client: AsyncTestClient[Any]) -> None:
    response = await test_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.anyio
async def test_extract_from_file(test_client: AsyncTestClient[Any], searchable_pdf: Path) -> None:
    with searchable_pdf.open("rb") as f:
        response = await test_client.post(
            "/extract", files=[("data", (searchable_pdf.name, f.read(), "application/pdf"))]
        )

    assert response.status_code == 201
    data = response.json()
    assert "Sample PDF" in data[0]["content"]
    assert data[0]["mime_type"] in ["text/plain", "text/markdown"]


@pytest.mark.anyio
async def test_extract_from_multiple_files(
    test_client: AsyncTestClient[Any], searchable_pdf: Path, scanned_pdf: Path
) -> None:
    with searchable_pdf.open("rb") as f1, scanned_pdf.open("rb") as f2:
        response = await test_client.post(
            "/extract",
            files=[
                ("data", (searchable_pdf.name, f1.read(), "application/pdf")),
                ("data", (scanned_pdf.name, f2.read(), "application/pdf")),
            ],
        )

    assert response.status_code == 201
    data = response.json()
    assert len(data) == 2
    assert "Sample PDF" in data[0]["content"]
    assert data[1]["content"]


@pytest.mark.anyio
async def test_extract_from_file_extraction_error(test_client: AsyncTestClient[Any], tmp_path: Path) -> None:
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello world")

    with patch("kreuzberg._api.main.batch_extract_bytes", new_callable=AsyncMock) as mock_extract:
        mock_extract.side_effect = Exception("Test error")
        with test_file.open("rb") as f:
            response = await test_client.post("/extract", files=[("data", (test_file.name, f.read(), "text/plain"))])

    assert response.status_code == 500
    error_response = response.json()

    assert "detail" in error_response
    assert error_response["status_code"] == 500


@pytest.mark.anyio
async def test_extract_validation_error_response(test_client: AsyncTestClient[Any], tmp_path: Path) -> None:
    """Test that ValidationError is properly handled by the API."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello world")

    with patch("kreuzberg._api.main.batch_extract_bytes", new_callable=AsyncMock) as mock_extract:
        mock_extract.side_effect = ValidationError("Invalid configuration", context={"param": "invalid_value"})
        with test_file.open("rb") as f:
            response = await test_client.post("/extract", files=[("data", (test_file.name, f.read(), "text/plain"))])

    assert response.status_code == 400
    error_response = response.json()
    assert "Invalid configuration" in error_response["message"]
    assert '"param": "invalid_value"' in error_response["details"]


@pytest.mark.anyio
async def test_extract_parsing_error_response(test_client: AsyncTestClient[Any], tmp_path: Path) -> None:
    """Test that ParsingError is properly handled by the API."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello world")

    with patch("kreuzberg._api.main.batch_extract_bytes", new_callable=AsyncMock) as mock_extract:
        mock_extract.side_effect = ParsingError("Failed to parse document", context={"file_type": "unknown"})
        with test_file.open("rb") as f:
            response = await test_client.post("/extract", files=[("data", (test_file.name, f.read(), "text/plain"))])

    assert response.status_code == 422
    error_response = response.json()
    assert "Failed to parse document" in error_response["message"]
    assert '"file_type": "unknown"' in error_response["details"]


@pytest.mark.anyio
async def test_extract_ocr_error_response(test_client: AsyncTestClient[Any], tmp_path: Path) -> None:
    """Test that OCRError is properly handled by the API."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello world")

    with patch("kreuzberg._api.main.batch_extract_bytes", new_callable=AsyncMock) as mock_extract:
        mock_extract.side_effect = OCRError("OCR processing failed", context={"engine": "tesseract"})
        with test_file.open("rb") as f:
            response = await test_client.post("/extract", files=[("data", (test_file.name, f.read(), "text/plain"))])

    assert response.status_code == 500
    error_response = response.json()
    assert "OCR processing failed" in error_response["message"]
    assert '"engine": "tesseract"' in error_response["details"]


@pytest.mark.anyio
async def test_extract_from_unsupported_file(test_client: AsyncTestClient[Any], tmp_path: Path) -> None:
    test_file = tmp_path / "test.unsupported"
    test_file.write_text("hello world")

    with test_file.open("rb") as f:
        response = await test_client.post("/extract", files=[("data", (test_file.name, f.read()))])

    assert response.status_code in [201, 400, 422]
    if response.status_code != 201:
        error_response = response.json()
        assert "message" in error_response


@pytest.mark.anyio
async def test_extract_from_docx(test_client: AsyncTestClient[Any], docx_document: Path) -> None:
    with docx_document.open("rb") as f:
        response = await test_client.post(
            "/extract",
            files=[
                (
                    "data",
                    (
                        docx_document.name,
                        f.read(),
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    ),
                )
            ],
        )

    assert response.status_code == 201
    data = response.json()
    assert len(data) == 1
    assert "content" in data[0]
    assert data[0]["mime_type"] in ["text/plain", "text/markdown"]


@pytest.mark.anyio
async def test_extract_from_image(test_client: AsyncTestClient[Any], ocr_image: Path) -> None:
    with ocr_image.open("rb") as f:
        response = await test_client.post("/extract", files=[("data", (ocr_image.name, f.read(), "image/jpeg"))])

    assert response.status_code == 201
    data = response.json()
    assert len(data) == 1
    assert "content" in data[0]
    assert data[0]["mime_type"] in ["text/plain", "text/markdown"]


@pytest.mark.anyio
async def test_extract_from_excel(test_client: AsyncTestClient[Any], excel_document: Path) -> None:
    with excel_document.open("rb") as f:
        response = await test_client.post(
            "/extract",
            files=[
                (
                    "data",
                    (
                        excel_document.name,
                        f.read(),
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    ),
                )
            ],
        )

    assert response.status_code == 201
    data = response.json()
    assert len(data) == 1
    assert "content" in data[0]
    assert data[0]["mime_type"] in ["text/plain", "text/markdown"]


@pytest.mark.anyio
async def test_extract_from_html(test_client: AsyncTestClient[Any], html_document: Path) -> None:
    with html_document.open("rb") as f:
        response = await test_client.post("/extract", files=[("data", (html_document.name, f.read(), "text/html"))])

    assert response.status_code == 201
    data = response.json()
    assert len(data) == 1
    assert "content" in data[0]
    assert data[0]["mime_type"] in ["text/plain", "text/markdown"]


@pytest.mark.anyio
async def test_extract_from_markdown(test_client: AsyncTestClient[Any], markdown_document: Path) -> None:
    with markdown_document.open("rb") as f:
        response = await test_client.post(
            "/extract", files=[("data", (markdown_document.name, f.read(), "text/markdown"))]
        )

    assert response.status_code == 201
    data = response.json()
    assert len(data) == 1
    assert "content" in data[0]
    assert data[0]["mime_type"] in ["text/plain", "text/markdown"]


@pytest.mark.anyio
async def test_extract_from_pptx(test_client: AsyncTestClient[Any], pptx_document: Path) -> None:
    with pptx_document.open("rb") as f:
        response = await test_client.post(
            "/extract",
            files=[
                (
                    "data",
                    (
                        pptx_document.name,
                        f.read(),
                        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    ),
                )
            ],
        )

    assert response.status_code == 201
    data = response.json()
    assert len(data) == 1
    assert "content" in data[0]
    assert data[0]["mime_type"] in ["text/plain", "text/markdown"]


@pytest.mark.anyio
async def test_extract_mixed_file_types(
    test_client: AsyncTestClient[Any], searchable_pdf: Path, docx_document: Path, excel_document: Path
) -> None:
    files = []
    with searchable_pdf.open("rb") as f1, docx_document.open("rb") as f2, excel_document.open("rb") as f3:
        files = [
            ("data", (searchable_pdf.name, f1.read(), "application/pdf")),
            (
                "data",
                (
                    docx_document.name,
                    f2.read(),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                ),
            ),
            (
                "data",
                (excel_document.name, f3.read(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            ),
        ]
        response = await test_client.post("/extract", files=files)

    assert response.status_code == 201
    data = response.json()
    assert len(data) == 3
    for item in data:
        assert "content" in item
        assert item["mime_type"] in ["text/plain", "text/markdown"]


@pytest.mark.anyio
async def test_extract_empty_file_list(test_client: AsyncTestClient[Any]) -> None:
    response = await test_client.post("/extract", files=[])
    assert response.status_code == 500


@pytest.mark.anyio
async def test_extract_non_ascii_pdf(test_client: AsyncTestClient[Any], non_ascii_pdf: Path) -> None:
    with non_ascii_pdf.open("rb") as f:
        response = await test_client.post(
            "/extract", files=[("data", (non_ascii_pdf.name, f.read(), "application/pdf"))]
        )

    assert response.status_code == 201
    data = response.json()
    assert len(data) == 1
    assert "content" in data[0]
    assert data[0]["mime_type"] in ["text/plain", "text/markdown"]


# Test exception handler directly
def test_exception_handler_validation_error() -> None:
    """Test exception handler with ValidationError."""
    # Create mock request
    mock_request = Mock()
    mock_request.method = "POST"
    mock_request.url = "http://test.com/extract"
    mock_app = Mock()
    mock_app.logger = Mock()
    mock_request.app = mock_app

    # Create ValidationError
    error = ValidationError("Invalid input", context={"field": "test"})

    response = exception_handler(mock_request, error)

    assert response.status_code == 400
    assert "Invalid input" in response.content["message"]
    assert '"field": "test"' in response.content["details"]

    # Verify logging was called
    mock_app.logger.error.assert_called_once()
    call_args = mock_app.logger.error.call_args
    assert call_args[0][0] == "API error"
    assert call_args[1]["method"] == "POST"
    assert call_args[1]["status_code"] == 400


def test_exception_handler_parsing_error() -> None:
    """Test exception handler with ParsingError."""
    # Create mock request
    mock_request = Mock()
    mock_request.method = "GET"
    mock_request.url = "http://test.com/health"
    mock_app = Mock()
    mock_app.logger = Mock()
    mock_request.app = mock_app

    # Create ParsingError
    error = ParsingError("Failed to parse document", context={"file": "test.pdf"})

    response = exception_handler(mock_request, error)

    assert response.status_code == 422
    assert "Failed to parse document" in response.content["message"]
    assert '"file": "test.pdf"' in response.content["details"]


def test_exception_handler_other_error() -> None:
    """Test exception handler with other KreuzbergError (OCRError)."""
    # Create mock request
    mock_request = Mock()
    mock_request.method = "POST"
    mock_request.url = "http://test.com/extract"
    mock_app = Mock()
    mock_app.logger = Mock()
    mock_request.app = mock_app

    # Create OCRError (other KreuzbergError)
    error = OCRError("OCR processing failed", context={"engine": "tesseract"})

    response = exception_handler(mock_request, error)

    assert response.status_code == 500
    assert "OCR processing failed" in response.content["message"]
    assert '"engine": "tesseract"' in response.content["details"]


def test_exception_handler_no_logger() -> None:
    """Test exception handler when request.app.logger is None."""
    # Create mock request without logger
    mock_request = Mock()
    mock_request.method = "POST"
    mock_request.url = "http://test.com/extract"
    mock_app = Mock()
    mock_app.logger = None  # No logger
    mock_request.app = mock_app

    # Create ValidationError
    error = ValidationError("Invalid input", context={"field": "test"})

    # Should not raise exception even without logger
    response = exception_handler(mock_request, error)

    assert response.status_code == 400
    assert "Invalid input" in response.content["message"]


def test_import_error_handling() -> None:
    """Test that ImportError handling works correctly."""
    # Test the import error structure by examining the code directly
    # We can't easily test the actual import failure due to caching,
    # but we can test that MissingDependencyError.create_for_package works
    from kreuzberg.exceptions import MissingDependencyError

    # Test that the exception creation works as expected
    import_error = ImportError("No module named 'litestar'")
    try:
        raise MissingDependencyError.create_for_package(
            dependency_group="litestar",
            functionality="Litestar API and docker container",
            package_name="litestar",
        ) from import_error
    except MissingDependencyError as e:
        assert "litestar" in str(e).lower()
        assert e.__cause__ is import_error


# =============================================================================
# COMPREHENSIVE TESTS FOR API MODULE
# =============================================================================


@pytest.mark.anyio
async def test_get_configuration_no_config(
    test_client: AsyncTestClient[Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test GET /config when no configuration file exists."""
    # Mock try_discover_config to return None
    with patch("kreuzberg._api.main.try_discover_config", return_value=None):
        response = await test_client.get("/config")

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "No configuration file found"
    assert data["config"] is None


@pytest.mark.anyio
async def test_get_configuration_with_config(test_client: AsyncTestClient[Any]) -> None:
    """Test GET /config when configuration file exists."""
    from kreuzberg import ExtractionConfig
    from kreuzberg._ocr._tesseract import PSMMode, TesseractConfig

    # Create a test config
    test_config = ExtractionConfig(
        ocr_backend="tesseract",
        ocr_config=TesseractConfig(language="fra", psm=PSMMode.SINGLE_BLOCK),
        extract_tables=True,
        chunk_content=True,
        enable_quality_processing=True,
        max_chars=5000,
    )

    # Mock try_discover_config to return our test config
    with patch("kreuzberg._api.main.try_discover_config", return_value=test_config):
        response = await test_client.get("/config")

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Configuration loaded successfully"
    assert data["config"] is not None
    assert data["config"]["ocr_backend"] == "tesseract"
    assert data["config"]["extract_tables"] is True
    assert data["config"]["chunk_content"] is True
    assert data["config"]["enable_quality_processing"] is True
    assert data["config"]["max_chars"] == 5000


@pytest.mark.anyio
async def test_extract_with_discovered_config(test_client: AsyncTestClient[Any], searchable_pdf: Path) -> None:
    """Test that extraction uses discovered config."""
    from kreuzberg import ExtractionConfig

    # Create a test config with specific settings
    test_config = ExtractionConfig(chunk_content=True, max_chars=1000, max_overlap=200)

    # Mock try_discover_config to return our test config
    with patch("kreuzberg._api.main.try_discover_config", return_value=test_config):
        # Mock batch_extract_bytes to verify config is passed
        with patch("kreuzberg._api.main.batch_extract_bytes", new_callable=AsyncMock) as mock_extract:
            mock_extract.return_value = [
                {"content": "Test content", "mime_type": "text/plain", "metadata": {}, "chunks": ["chunk1", "chunk2"]}
            ]

            with searchable_pdf.open("rb") as f:
                response = await test_client.post(
                    "/extract", files=[("data", (searchable_pdf.name, f.read(), "application/pdf"))]
                )

            # Verify batch_extract_bytes was called with the discovered config
            assert mock_extract.called
            call_args = mock_extract.call_args
            used_config = call_args[1]["config"]
            assert used_config.chunk_content is True
            assert used_config.max_chars == 1000
            assert used_config.max_overlap == 200

    assert response.status_code == 201


@pytest.mark.anyio
async def test_extract_without_discovered_config(test_client: AsyncTestClient[Any], searchable_pdf: Path) -> None:
    """Test that extraction uses default config when none discovered."""
    # Mock try_discover_config to return None
    with patch("kreuzberg._api.main.try_discover_config", return_value=None):
        # Mock batch_extract_bytes to verify default config is used
        with patch("kreuzberg._api.main.batch_extract_bytes", new_callable=AsyncMock) as mock_extract:
            mock_extract.return_value = [
                {"content": "Test content", "mime_type": "text/plain", "metadata": {}, "chunks": []}
            ]

            with searchable_pdf.open("rb") as f:
                response = await test_client.post(
                    "/extract", files=[("data", (searchable_pdf.name, f.read(), "application/pdf"))]
                )

            # Verify batch_extract_bytes was called with default config
            assert mock_extract.called
            call_args = mock_extract.call_args
            used_config = call_args[1]["config"]
            # Default config should have default values
            assert used_config.chunk_content is False
            assert used_config.max_chars == 2000  # Default value

    assert response.status_code == 201


@pytest.mark.anyio
async def test_extract_large_file_list(test_client: AsyncTestClient[Any], tmp_path: Path) -> None:
    """Test extraction with many files."""
    # Create 20 test files
    files = []
    for i in range(20):
        test_file = tmp_path / f"test_{i}.txt"
        test_file.write_text(f"Content {i}")
        with test_file.open("rb") as f:
            files.append(("data", (test_file.name, f.read(), "text/plain")))

    response = await test_client.post("/extract", files=files)

    assert response.status_code == 201
    data = response.json()
    assert len(data) == 20
    for i, item in enumerate(data):
        assert f"Content {i}" in item["content"]


@pytest.mark.anyio
async def test_extract_with_custom_mime_types(test_client: AsyncTestClient[Any], tmp_path: Path) -> None:
    """Test extraction with various MIME type scenarios."""
    test_file = tmp_path / "test.bin"
    test_file.write_bytes(b"binary content")

    # Test with no MIME type (should infer)
    with test_file.open("rb") as f:
        response = await test_client.post("/extract", files=[("data", (test_file.name, f.read()))])

    # Even unknown files might be processed (e.g., as text)
    assert response.status_code in [201, 400, 422]


@pytest.mark.anyio
async def test_extract_file_with_none_content_type(test_client: AsyncTestClient[Any], tmp_path: Path) -> None:
    """Test extraction when content_type is None."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello world")

    # Mock UploadFile with None content_type
    with patch("kreuzberg._api.main.batch_extract_bytes", new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = [
            {"content": "Hello world", "mime_type": "text/plain", "metadata": {}, "chunks": []}
        ]

        with test_file.open("rb") as f:
            response = await test_client.post(
                "/extract",
                files=[("data", (test_file.name, f.read(), None))],  # None content_type
            )

        # Verify the None was passed through
        assert mock_extract.called
        call_args = mock_extract.call_args[0][0]
        assert len(call_args) == 1
        # The second element of the tuple should be None
        # (since we mocked it, we can't easily verify this part)

    assert response.status_code == 201


@pytest.mark.anyio
async def test_health_check_idempotent(test_client: AsyncTestClient[Any]) -> None:
    """Test that health check is idempotent."""
    # Call health check multiple times
    responses = []
    for _ in range(5):
        response = await test_client.get("/health")
        responses.append(response)

    # All should be successful and identical
    for response in responses:
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


@pytest.mark.anyio
async def test_extract_memory_error_handling(test_client: AsyncTestClient[Any], tmp_path: Path) -> None:
    """Test handling of MemoryError during extraction."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")

    with patch("kreuzberg._api.main.batch_extract_bytes", new_callable=AsyncMock) as mock_extract:
        mock_extract.side_effect = MemoryError("Out of memory")

        with test_file.open("rb") as f:
            response = await test_client.post("/extract", files=[("data", (test_file.name, f.read(), "text/plain"))])

    # MemoryError is not a KreuzbergError, so it should be 500
    assert response.status_code == 500


def test_exception_handler_with_empty_context() -> None:
    """Test exception handler with empty context."""
    mock_request = Mock()
    mock_request.method = "POST"
    mock_request.url = "http://test.com/extract"
    mock_app = Mock()
    mock_app.logger = Mock()
    mock_request.app = mock_app

    # Create error with empty context
    error = ValidationError("Test error", context={})

    response = exception_handler(mock_request, error)

    assert response.status_code == 400
    assert response.content["message"] == "ValidationError: Test error"
    assert response.content["details"] == "{}"


def test_exception_handler_context_serialization() -> None:
    """Test exception handler with complex context that needs JSON serialization."""
    mock_request = Mock()
    mock_request.method = "POST"
    mock_request.url = "http://test.com/extract"
    mock_app = Mock()
    mock_app.logger = Mock()
    mock_request.app = mock_app

    # Create error with complex context
    error = ParsingError(
        "Complex error",
        context={"numbers": [1, 2, 3], "nested": {"key": "value"}, "boolean": True, "none": None, "float": 3.14},
    )

    response = exception_handler(mock_request, error)

    assert response.status_code == 422
    # Verify JSON serialization worked
    assert '"numbers": [1, 2, 3]' in response.content["details"]
    assert '"nested": {"key": "value"}' in response.content["details"]
    assert '"boolean": true' in response.content["details"]
    assert '"none": null' in response.content["details"]
    assert '"float": 3.14' in response.content["details"]


@pytest.mark.anyio
async def test_api_routes_registration(test_client: AsyncTestClient[Any]) -> None:
    """Test that all expected routes are registered."""
    # Get the app's route handler map
    from kreuzberg._api.main import app

    # Check that all expected routes exist
    routes = [(route.path, route.methods) for route in app.routes if hasattr(route, "path")]

    # Verify expected routes
    expected_routes = [("/extract", ["POST"]), ("/health", ["GET"]), ("/config", ["GET"])]

    for path, methods in expected_routes:
        found = False
        for route_path, route_methods in routes:
            if path in str(route_path):
                found = True
                for method in methods:
                    assert method in route_methods
                break
        assert found, f"Route {path} not found"


@pytest.mark.anyio
async def test_opentelemetry_plugin_loaded() -> None:
    """Test that OpenTelemetry plugin is loaded."""
    from kreuzberg._api.main import app

    # Check that OpenTelemetryPlugin is in the app's plugins
    plugin_types = [type(plugin).__name__ for plugin in app.plugins]
    assert "OpenTelemetryPlugin" in plugin_types


@pytest.mark.anyio
async def test_structured_logging_configured() -> None:
    """Test that structured logging is configured."""
    from kreuzberg._api.main import app

    # Check that StructLoggingConfig is used
    assert app.logging_config is not None
    assert type(app.logging_config).__name__ == "StructLoggingConfig"


@pytest.mark.anyio
async def test_exception_handlers_registered() -> None:
    """Test that exception handlers are properly registered."""
    from kreuzberg._api.main import app
    from kreuzberg.exceptions import KreuzbergError

    # Check that KreuzbergError handler is registered
    assert KreuzbergError in app.exception_handlers


@pytest.mark.anyio
async def test_msgspec_serialization_deterministic(test_client: AsyncTestClient[Any]) -> None:
    """Test that msgspec serialization is deterministic."""
    import msgspec

    from kreuzberg import ExtractionConfig

    # Create a config with nested structures
    config = ExtractionConfig(
        ocr_backend="tesseract", extract_tables=True, chunk_content=True, max_chars=5000, max_overlap=1000
    )

    # Serialize multiple times
    serialized_results = []
    for _ in range(5):
        serialized = msgspec.to_builtins(config, order="deterministic")
        serialized_results.append(str(serialized))

    # All serializations should be identical
    assert all(s == serialized_results[0] for s in serialized_results)
