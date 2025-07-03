from __future__ import annotations

from typing import TYPE_CHECKING, Any

import msgspec
import structlog
from litestar import Litestar, post
from litestar.contrib.opentelemetry import OpenTelemetryConfig
from litestar.exceptions import HTTPException
from litestar.status_codes import HTTP_422_UNPROCESSABLE_ENTITY, HTTP_500_INTERNAL_SERVER_ERROR

from kreuzberg import ExtractionConfig, extract_bytes
from kreuzberg.exceptions import KreuzbergError

if TYPE_CHECKING:
    from litestar.datastructures import UploadFile

# Configure logging
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)
logger = structlog.get_logger()


class ExtractionRequest(msgspec.Struct):
    """Represents a request to extract content from a file."""

    file: UploadFile


@post("/extract", operation_id="extract_file")
async def extract_from_file(data: ExtractionRequest) -> dict[str, Any]:
    """Extracts text content from an uploaded file."""
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(filename=data.file.filename, content_type=data.file.content_type)

    try:
        logger.info("Receiving file")
        file_bytes = await data.file.read()

        config = ExtractionConfig(ocr_backend="tesseract")
        result = await extract_bytes(file_bytes, mime_type=data.file.content_type, config=config)

        logger.info("Successfully extracted content")
        return result.to_dict()

    except KreuzbergError as e:
        logger.exception("Extraction failed")
        raise HTTPException(status_code=HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Extraction failed: {e}") from e
    except Exception as e:
        logger.exception("An unexpected server error occurred")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="An internal server error occurred."
        ) from e


@post("/health", operation_id="health_check")
async def health_check() -> dict[str, str]:
    """A simple health check endpoint."""
    return {"status": "ok"}


def create_app() -> Litestar:
    """Create the Litestar application."""
    opentelemetry_config = OpenTelemetryConfig(
        service_name="kreuzberg-api",
    )

    return Litestar(
        route_handlers=[extract_from_file, health_check],
        middleware=[opentelemetry_config.middleware],
    )


app = create_app()
