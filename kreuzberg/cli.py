"""Command-line interface for kreuzberg."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

try:
    import click
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn
except ImportError as e:
    raise ImportError(
        "CLI dependencies are not installed. Please install kreuzberg with the 'cli' extra: pip install kreuzberg[cli]"
    ) from e

from kreuzberg import __version__, extract_bytes_sync, extract_file_sync
from kreuzberg._cli_config import build_extraction_config, find_default_config, load_config_from_file
from kreuzberg.exceptions import KreuzbergError, MissingDependencyError

DEFAULT_MAX_CHARACTERS = 4000
DEFAULT_MAX_OVERLAP = 200

if TYPE_CHECKING:
    from kreuzberg._types import ExtractionConfig, ExtractionResult

console = Console(stderr=True)


class OcrBackendParamType(click.ParamType):
    """Click parameter type for OCR backend selection."""

    name = "ocr_backend"

    def convert(self, value: Any, param: click.Parameter | None, ctx: click.Context | None) -> str | None:
        """Convert parameter value to OCR backend string."""
        if value is None:
            return None
        if value.lower() == "none":
            return "none"
        valid_backends = ["tesseract", "easyocr", "paddleocr", "none"]
        if value.lower() not in valid_backends:
            self.fail(f"Invalid OCR backend '{value}'. Choose from: {', '.join(valid_backends)}", param, ctx)
        return value.lower()  # type: ignore[no-any-return]


def format_extraction_result(result: ExtractionResult, show_metadata: bool, output_format: str) -> str:
    """Format extraction result for output.

    Args:
        result: Extraction result to format.
        show_metadata: Whether to include metadata.
        output_format: Output format (text, json).

    Returns:
        Formatted string.
    """
    if output_format == "json":
        output_data: dict[str, Any] = {
            "content": result.content,
            "mime_type": result.mime_type,
        }
        if show_metadata:
            output_data["metadata"] = result.metadata
        if result.tables:
            output_data["tables"] = result.tables
        if result.chunks:
            output_data["chunks"] = result.chunks
        return json.dumps(output_data, indent=2, ensure_ascii=False)

    output_parts = [result.content]

    if show_metadata:
        output_parts.append("\n\n--- METADATA ---")
        output_parts.append(json.dumps(result.metadata, indent=2, ensure_ascii=False))

    if result.tables:
        output_parts.append("\n\n--- TABLES ---")
        for i, table in enumerate(result.tables):
            output_parts.append(f"\nTable {i + 1}:")
            output_parts.append(json.dumps(table, indent=2, ensure_ascii=False))

    return "\n".join(output_parts)


def _load_config(config: Path | None, verbose: bool) -> dict[str, Any]:
    """Load configuration from file or find default."""
    file_config = {}
    if config:
        file_config = load_config_from_file(config)
    else:
        default_config = find_default_config()
        if default_config:
            try:
                file_config = load_config_from_file(default_config)
                if verbose:
                    console.print(f"[dim]Using configuration from: {default_config}[/dim]")
            except Exception:  # noqa: BLE001
                pass
    return file_config


def _build_cli_args(
    force_ocr: bool,
    chunk_content: bool,
    extract_tables: bool,
    max_chars: int,
    max_overlap: int,
    ocr_backend: str | None,
    tesseract_lang: str | None,
    tesseract_psm: int | None,
    easyocr_languages: str | None,
    paddleocr_languages: str | None,
) -> dict[str, Any]:
    """Build CLI arguments dictionary."""
    cli_args: dict[str, Any] = {
        "force_ocr": force_ocr if force_ocr else None,
        "chunk_content": chunk_content if chunk_content else None,
        "extract_tables": extract_tables if extract_tables else None,
        "max_chars": max_chars if max_chars != DEFAULT_MAX_CHARACTERS else None,
        "max_overlap": max_overlap if max_overlap != DEFAULT_MAX_OVERLAP else None,
        "ocr_backend": ocr_backend,
    }

    if ocr_backend == "tesseract" and (tesseract_lang or tesseract_psm is not None):
        tesseract_config = {}
        if tesseract_lang:
            tesseract_config["language"] = tesseract_lang
        if tesseract_psm is not None:
            tesseract_config["psm"] = tesseract_psm  # type: ignore[assignment]
        cli_args["tesseract_config"] = tesseract_config
    elif ocr_backend == "easyocr" and easyocr_languages:
        cli_args["easyocr_config"] = {"languages": easyocr_languages.split(",")}
    elif ocr_backend == "paddleocr" and paddleocr_languages:
        cli_args["paddleocr_config"] = {"languages": paddleocr_languages.split(",")}

    return cli_args


def _perform_extraction(file: Path | None, extraction_config: ExtractionConfig, verbose: bool) -> ExtractionResult:
    """Perform text extraction from file or stdin."""
    if file is None or (isinstance(file, Path) and file.name == "-"):
        if verbose:
            console.print("[dim]Reading from stdin...[/dim]")
        try:
            input_bytes = sys.stdin.buffer.read()
        except Exception:  # noqa: BLE001
            input_text = sys.stdin.read()
            input_bytes = input_text.encode("utf-8")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task("Extracting text...", total=None)

            try:
                import magic  # type: ignore[import-not-found]

                mime_type = magic.from_buffer(input_bytes, mime=True)
            except ImportError:
                content_str = input_bytes.decode("utf-8", errors="ignore").lower()
                mime_type = "text/html" if "<html" in content_str or "<body" in content_str else "text/plain"

            return extract_bytes_sync(input_bytes, mime_type, config=extraction_config)
    else:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task(f"Extracting text from {file.name}...", total=None)
            return extract_file_sync(str(file), config=extraction_config)


def _write_output(
    result: ExtractionResult, output: Path | None, show_metadata: bool, output_format: str, verbose: bool
) -> None:
    """Format and write extraction output."""
    formatted_output = format_extraction_result(result, show_metadata, output_format)

    if output:
        output.write_text(formatted_output, encoding="utf-8")
        if verbose:
            console.print(f"[green]✓[/green] Output written to: {output}")
    else:
        click.echo(formatted_output)


def handle_error(error: Exception, verbose: bool) -> None:
    """Handle and display errors.

    Args:
        error: The exception to handle.
        verbose: Whether to show full stack trace.
    """
    if isinstance(error, MissingDependencyError):
        console.print(f"[red]Missing dependency:[/red] {error}", style="bold")
        sys.exit(2)
    elif isinstance(error, KreuzbergError):
        console.print(f"[red]Error:[/red] {error}", style="bold")
        if verbose and error.context:
            console.print("\n[dim]Context:[/dim]")
            console.print(json.dumps(error.context, indent=2))
        sys.exit(1)
    else:
        console.print(f"[red]Unexpected error:[/red] {type(error).__name__}: {error}", style="bold")
        if verbose:
            import traceback

            console.print("\n[dim]Traceback:[/dim]")
            traceback.print_exc()
        sys.exit(1)


@click.group(invoke_without_command=True)
@click.version_option(version=__version__, prog_name="kreuzberg")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Kreuzberg - Text extraction from documents.

    Extract text from PDFs, images, Office documents, and more.
    """
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.command()
@click.argument("file", type=click.Path(exists=True, path_type=Path), required=False)
@click.option("-o", "--output", type=click.Path(path_type=Path), help="Output file path (default: stdout)")
@click.option("--force-ocr", is_flag=True, help="Force OCR processing")
@click.option("--chunk-content", is_flag=True, help="Enable content chunking")
@click.option("--extract-tables", is_flag=True, help="Enable table extraction")
@click.option(
    "--max-chars",
    type=int,
    default=DEFAULT_MAX_CHARACTERS,
    help=f"Maximum characters per chunk (default: {DEFAULT_MAX_CHARACTERS})",
)
@click.option(
    "--max-overlap",
    type=int,
    default=DEFAULT_MAX_OVERLAP,
    help=f"Maximum overlap between chunks (default: {DEFAULT_MAX_OVERLAP})",
)
@click.option(
    "--ocr-backend", type=OcrBackendParamType(), help="OCR backend to use (tesseract, easyocr, paddleocr, none)"
)
@click.option("--config", type=click.Path(exists=True, path_type=Path), help="Configuration file path")
@click.option("--show-metadata", is_flag=True, help="Include metadata in output")
@click.option("--output-format", type=click.Choice(["text", "json"]), default="text", help="Output format")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output for debugging")
@click.option("--tesseract-lang", help="Tesseract language(s) (e.g., 'eng+deu')")
@click.option("--tesseract-psm", type=int, help="Tesseract PSM mode (0-13)")
@click.option("--easyocr-languages", help="EasyOCR language codes (comma-separated, e.g., 'en,de')")
@click.option("--paddleocr-languages", help="PaddleOCR language codes (comma-separated, e.g., 'en,german')")
@click.pass_context
def extract(  # noqa: PLR0913
    ctx: click.Context,  # noqa: ARG001
    file: Path | None,
    output: Path | None,
    force_ocr: bool,
    chunk_content: bool,
    extract_tables: bool,
    max_chars: int,
    max_overlap: int,
    ocr_backend: str | None,
    config: Path | None,
    show_metadata: bool,
    output_format: str,
    verbose: bool,
    tesseract_lang: str | None,
    tesseract_psm: int | None,
    easyocr_languages: str | None,
    paddleocr_languages: str | None,
) -> None:
    """Extract text from a document.

    FILE can be a path to a document or '-' to read from stdin.
    If FILE is omitted, reads from stdin.
    """
    try:
        file_config = _load_config(config, verbose)

        cli_args = _build_cli_args(
            force_ocr,
            chunk_content,
            extract_tables,
            max_chars,
            max_overlap,
            ocr_backend,
            tesseract_lang,
            tesseract_psm,
            easyocr_languages,
            paddleocr_languages,
        )

        extraction_config = build_extraction_config(file_config, cli_args)

        result = _perform_extraction(file, extraction_config, verbose)

        _write_output(result, output, show_metadata, output_format, verbose)

    except Exception as e:  # noqa: BLE001
        handle_error(e, verbose)


@cli.command()
@click.option("--config", type=click.Path(exists=True, path_type=Path), help="Configuration file path")
def config(config: Path | None) -> None:
    """Show current configuration."""
    try:
        config_path = config or find_default_config()

        if config_path:
            file_config = load_config_from_file(config_path)
            console.print(f"[bold]Configuration from:[/bold] {config_path}")
            console.print(json.dumps(file_config, indent=2))
        else:
            console.print("[yellow]No configuration file found.[/yellow]")
            console.print("\nDefault configuration values:")
            console.print("  force_ocr: False")
            console.print("  chunk_content: False")
            console.print("  extract_tables: False")
            console.print(f"  max_chars: {DEFAULT_MAX_CHARACTERS}")
            console.print(f"  max_overlap: {DEFAULT_MAX_OVERLAP}")
            console.print("  ocr_backend: tesseract")
    except Exception as e:  # noqa: BLE001
        handle_error(e, verbose=False)


if __name__ == "__main__":
    cli()
