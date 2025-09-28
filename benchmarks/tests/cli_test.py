from unittest.mock import MagicMock, patch

from click.testing import CliRunner
from src.cli import main


def test_cli_help() -> None:
    """Test that CLI help works."""
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "Run benchmarks for all frameworks" in result.output


def test_cli_default_options() -> None:
    """Test CLI with default options."""
    runner = CliRunner()

    # Mock the async runner to avoid actually running benchmarks
    with (
        patch("src.cli.ComprehensiveBenchmarkRunner") as mock_runner_class,
        patch("src.cli.ResultAggregator") as mock_aggregator_class,
        patch("src.cli.asyncio.run") as mock_asyncio,
    ):
        # Setup mocks
        mock_runner = MagicMock()
        mock_runner_class.return_value = mock_runner
        mock_asyncio.return_value = []  # Empty results

        mock_aggregator = MagicMock()
        mock_aggregator_class.return_value = mock_aggregator
        mock_aggregator.aggregate_results.return_value = {}

        # Run CLI
        result = runner.invoke(main, [])

        # Check it ran without errors
        assert result.exit_code == 0
        assert "Starting Benchmark Suite" in result.output

        # Check runner was configured correctly
        mock_runner_class.assert_called_once()
        config = mock_runner_class.call_args[0][0]
        assert config.iterations == 3  # default
        assert config.timeout_seconds == 300  # default


def test_cli_custom_options() -> None:
    """Test CLI with custom options."""
    runner = CliRunner()

    with (
        patch("src.cli.ComprehensiveBenchmarkRunner") as mock_runner_class,
        patch("src.cli.ResultAggregator") as mock_aggregator_class,
        patch("src.cli.asyncio.run") as mock_asyncio,
    ):
        # Setup mocks
        mock_runner = MagicMock()
        mock_runner_class.return_value = mock_runner
        mock_asyncio.return_value = []

        mock_aggregator = MagicMock()
        mock_aggregator_class.return_value = mock_aggregator
        mock_aggregator.aggregate_results.return_value = {}

        # Run with custom options
        result = runner.invoke(main, ["--iterations", "5", "--timeout", "600", "--output", "custom/output.json"])

        assert result.exit_code == 0

        # Check config was updated
        config = mock_runner_class.call_args[0][0]
        assert config.iterations == 5
        assert config.timeout_seconds == 600

        # Check output path in log
        assert "Output: custom/output.json" in result.output


def test_cli_keyboard_interrupt() -> None:
    """Test CLI handles keyboard interrupt gracefully."""
    runner = CliRunner()

    with (
        patch("src.cli.ComprehensiveBenchmarkRunner") as mock_runner_class,
        patch("src.cli.asyncio.run") as mock_asyncio,
    ):
        mock_runner_class.return_value = MagicMock()
        mock_asyncio.side_effect = KeyboardInterrupt()

        result = runner.invoke(main, [])

        assert result.exit_code == 1
        assert "interrupted by user" in result.output


def test_cli_benchmark_failure() -> None:
    """Test CLI handles benchmark failures."""
    runner = CliRunner()

    with (
        patch("src.cli.ComprehensiveBenchmarkRunner") as mock_runner_class,
        patch("src.cli.asyncio.run") as mock_asyncio,
    ):
        mock_runner_class.return_value = MagicMock()
        mock_asyncio.side_effect = Exception("Test error")

        result = runner.invoke(main, [])

        assert result.exit_code == 1
        assert "Benchmark failed" in result.output
