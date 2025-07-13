from abc import ABC, abstractmethod
from pathlib import Path
from typing import Generic, TypeVar

from PIL.Image import Image

from kreuzberg._types import ExtractionResult

try:  # pragma: no cover
    from typing import Unpack  # type: ignore[attr-defined]
except ImportError:  # pragma: no cover
    from typing_extensions import Unpack


T = TypeVar("T")


class OCRBackend(ABC, Generic[T]):
    """Abstract base class for Optical Character Recognition (OCR) backend implementations.

    This class provides the blueprint for OCR backend implementations,
    offering both synchronous and asynchronous methods to process images
    and files for text extraction.
    """

    @abstractmethod
    async def process_image(self, image: Image, **kwargs: Unpack[T]) -> ExtractionResult:
        """Asynchronously process an image and extract its text and metadata.

        Args:
            image: An instance of PIL.Image representing the input image.
            **kwargs: Any kwargs related to the given backend

        Returns:
            The extraction result object
        """
        ...

    @abstractmethod
    async def process_file(self, path: Path, **kwargs: Unpack[T]) -> ExtractionResult:
        """Asynchronously process a file and extract its text and metadata.

        Args:
            path: A Path object representing the file to be processed.
            **kwargs: Any kwargs related to the given backend

        Returns:
            The extraction result object
        """
        ...

    @abstractmethod
    def process_image_sync(self, image: Image, **kwargs: Unpack[T]) -> ExtractionResult:
        """Synchronously process an image and extract its text and metadata.

        Args:
            image: An instance of PIL.Image representing the input image.
            **kwargs: Any kwargs related to the given backend

        Returns:
            The extraction result object
        """
        ...

    @abstractmethod
    def process_file_sync(self, path: Path, **kwargs: Unpack[T]) -> ExtractionResult:
        """Synchronously process a file and extract its text and metadata.

        Args:
            path: A Path object representing the file to be processed.
            **kwargs: Any kwargs related to the given backend

        Returns:
            The extraction result object
        """
        ...

    def process_batch_sync(self, paths: list[Path], **kwargs: Unpack[T]) -> list[ExtractionResult]:
        """Synchronously process a batch of files and extract their text and metadata.

        Default implementation processes files sequentially. Backends can override
        for more efficient batch processing.

        Args:
            paths: List of Path objects representing files to be processed.
            **kwargs: Any kwargs related to the given backend

        Returns:
            List of extraction result objects in the same order as input paths
        """
        return [self.process_file_sync(path, **kwargs) for path in paths]

    async def process_batch(self, paths: list[Path], **kwargs: Unpack[T]) -> list[ExtractionResult]:
        """Asynchronously process a batch of files and extract their text and metadata.

        Default implementation processes files concurrently. Backends can override
        for more efficient batch processing.

        Args:
            paths: List of Path objects representing files to be processed.
            **kwargs: Any kwargs related to the given backend

        Returns:
            List of extraction result objects in the same order as input paths
        """
        from kreuzberg._utils._sync import run_taskgroup

        tasks = [self.process_file(path, **kwargs) for path in paths]
        return await run_taskgroup(*tasks)

    def __hash__(self) -> int:
        """Hash function for allowing caching."""
        return hash(type(self).__name__)
