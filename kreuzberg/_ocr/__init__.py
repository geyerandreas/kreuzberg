from functools import lru_cache
from typing import Any

from kreuzberg._ocr._base import OCRBackend
from kreuzberg._ocr._easyocr import EasyOCRBackend
from kreuzberg._ocr._paddleocr import PaddleBackend
from kreuzberg._ocr._pool import TesseractProcessPool
from kreuzberg._ocr._sync import (
    process_batch_images_process_pool,
    process_batch_images_sync,
    process_batch_images_threaded,
    process_image_bytes_easyocr_sync,
    process_image_bytes_paddleocr_sync,
    process_image_bytes_tesseract_sync,
    process_image_easyocr_sync,
    process_image_paddleocr_sync,
    process_image_tesseract_sync,
)
from kreuzberg._ocr._tesseract import TesseractBackend
from kreuzberg._types import OcrBackendType

__all__ = [
    "EasyOCRBackend",
    "OCRBackend",
    "PaddleBackend",
    "TesseractBackend",
    "TesseractProcessPool",
    "get_ocr_backend",
    "process_batch_images_process_pool",
    "process_batch_images_sync",
    "process_batch_images_threaded",
    "process_image_bytes_easyocr_sync",
    "process_image_bytes_paddleocr_sync",
    "process_image_bytes_tesseract_sync",
    "process_image_easyocr_sync",
    "process_image_paddleocr_sync",
    "process_image_tesseract_sync",
]


@lru_cache
def get_ocr_backend(backend: OcrBackendType) -> OCRBackend[Any]:
    if backend == "easyocr":
        return EasyOCRBackend()
    if backend == "paddleocr":
        return PaddleBackend()
    return TesseractBackend()
