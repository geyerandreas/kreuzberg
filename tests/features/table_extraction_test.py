def test_gmft_config_cell_required_confidence_empty_dict() -> None:
    """Test GMFTConfig with empty cell_required_confidence dict."""
    from kreuzberg._gmft import _create_gmft_formatter  # type: ignore[attr-defined]

    config_dict = {
        "verbosity": 1,
        "cell_required_confidence": {},  # Empty dict should be handled
    }

    # Should not raise an error with empty dict
    formatter = _create_gmft_formatter(config_dict)
    assert formatter is not None


def test_gmft_process_not_alive_generic_error() -> None:
    """Test GMFT process termination with non-segfault exit code."""
    import multiprocessing
    import queue
    from typing import Any
    from unittest.mock import Mock, patch

    import pytest

    from kreuzberg._gmft import _run_gmft_extraction_in_process  # type: ignore[attr-defined]
    from kreuzberg.exceptions import ParsingError

    # Mock a process that's not alive with non-SIGSEGV exit code
    mock_process = Mock()
    mock_process.is_alive.return_value = False
    mock_process.exitcode = 1  # Generic error, not segfault

    result_queue: multiprocessing.Queue[Any] = multiprocessing.Queue()

    # Patch the queue to raise Empty
    with patch.object(result_queue, "get", side_effect=queue.Empty):
        with patch("multiprocessing.Process", return_value=mock_process):
            with pytest.raises(ParsingError, match="GMFT process terminated"):
                _run_gmft_extraction_in_process(None, {}, result_queue)
