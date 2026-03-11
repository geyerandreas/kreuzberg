"""Batch-extract all PDF fixtures with Docling and save as vendored markdown.

Usage:
    python vendor_docling.py <fixtures_dir>

Outputs to: <fixtures_dir>/vendored/docling/md/{name}.md
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from docling.document_converter import DocumentConverter


def find_pdf_fixtures(fixtures_dir: Path) -> list[tuple[str, Path]]:
    """Find all PDF fixtures by reading JSON manifests."""
    results = []
    seen = set()

    # Scan both root-level and pdf/ subdirectory
    search_dirs = [fixtures_dir, fixtures_dir / "pdf"]
    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        for json_file in sorted(search_dir.glob("*.json")):
            try:
                manifest = json.loads(json_file.read_text())
                if manifest.get("file_type") != "pdf":
                    continue
                doc_path = manifest.get("document", "")
                if not doc_path:
                    continue
                full_path = (json_file.parent / doc_path).resolve()
                if full_path.exists() and full_path.suffix.lower() == ".pdf":
                    name = json_file.stem
                    if name not in seen:
                        seen.add(name)
                        results.append((name, full_path))
            except (json.JSONDecodeError, KeyError):
                continue

    return results


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: vendor_docling.py <fixtures_dir>", file=sys.stderr)
        sys.exit(1)

    fixtures_dir = Path(sys.argv[1]).resolve()
    output_dir = fixtures_dir / "vendored" / "docling" / "md"
    output_dir.mkdir(parents=True, exist_ok=True)

    pdfs = find_pdf_fixtures(fixtures_dir)
    print(f"Found {len(pdfs)} PDF fixtures", file=sys.stderr)

    converter = DocumentConverter()

    succeeded = 0
    failed = 0

    for i, (name, pdf_path) in enumerate(pdfs, 1):
        out_path = output_dir / f"{name}.md"
        if out_path.exists():
            print(f"[{i}/{len(pdfs)}] {name}: already exists, skipping", file=sys.stderr)
            succeeded += 1
            continue

        print(f"[{i}/{len(pdfs)}] {name}: extracting...", end="", file=sys.stderr, flush=True)
        start = time.perf_counter()
        try:
            result = converter.convert(str(pdf_path))
            markdown = result.document.export_to_markdown()
            out_path.write_text(markdown)
            elapsed = time.perf_counter() - start
            print(f" {elapsed:.1f}s, {len(markdown)} chars", file=sys.stderr)
            succeeded += 1
        except Exception as e:
            elapsed = time.perf_counter() - start
            print(f" FAILED ({elapsed:.1f}s): {e}", file=sys.stderr)
            failed += 1

    print(f"\nDone: {succeeded} succeeded, {failed} failed", file=sys.stderr)
    print(f"Output: {output_dir}", file=sys.stderr)


if __name__ == "__main__":
    main()
