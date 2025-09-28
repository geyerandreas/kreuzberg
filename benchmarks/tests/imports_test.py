import pytest


def test_kreuzberg_import() -> None:
    try:
        import kreuzberg

        assert hasattr(kreuzberg, "extract_file_sync")
    except ImportError:
        raise ImportError("kreuzberg not installed") from None


@pytest.mark.xfail(reason="Docling requires newer transformers version with AutoModelForImageTextToText")
def test_docling_import() -> None:
    try:
        from docling.document_converter import DocumentConverter

        assert DocumentConverter is not None
    except ImportError:
        raise ImportError("docling not installed") from None


def test_markitdown_import() -> None:
    try:
        from markitdown import MarkItDown

        assert MarkItDown is not None
    except ImportError:
        raise ImportError("markitdown not installed") from None


def test_unstructured_import() -> None:
    try:
        from unstructured.partition.auto import partition

        assert partition is not None
    except ImportError:
        raise ImportError("unstructured not installed") from None


def test_extractors_import() -> None:
    from src.extractors import (
        DoclingExtractor,
        KreuzbergAsyncExtractor,
        KreuzbergSyncExtractor,
        MarkItDownExtractor,
        UnstructuredExtractor,
        get_extractor,
    )

    assert KreuzbergSyncExtractor is not None
    assert KreuzbergAsyncExtractor is not None
    assert DoclingExtractor is not None
    assert MarkItDownExtractor is not None
    assert UnstructuredExtractor is not None
    assert get_extractor is not None
