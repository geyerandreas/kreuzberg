# mypy: disable-error-code=unused-ignore

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from multiprocessing import cpu_count
from pathlib import Path
from typing import TYPE_CHECKING

from kreuzberg import ExtractionConfig, ExtractionResult, batch_extract_file, extract_file, extract_file_sync
from kreuzberg._mime_types import PLAIN_TEXT_MIME_TYPE
from kreuzberg._ocr._tesseract import TesseractBackend, TesseractConfig  # type: ignore[attr-defined]
from kreuzberg._ocr._tesseract import _process_image_with_tesseract as proc_worker  # type: ignore[attr-defined]
from kreuzberg._ocr._tesseract import _process_image_with_tesseract as worker  # type: ignore[attr-defined]
from kreuzberg._types import PSMMode
from kreuzberg._utils._process_pool import process_pool

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable


class KreuzbergBenchmarks:
    def __init__(self, test_files_dir: Path | None = None) -> None:
        self.test_files_dir = test_files_dir or Path("../tests/test_source_files")
        self.test_files = self._discover_test_files()

    def _discover_test_files(self) -> list[Path]:
        if not self.test_files_dir.exists():
            return []

        extensions = [
            ".pdf",
            ".docx",
            ".xlsx",
            ".pptx",
            ".html",
            ".md",
            ".png",
            ".jpg",
            ".jpeg",
            ".eml",
            ".json",
            ".yaml",
            ".yml",
            ".toml",
        ]
        test_files = [file for ext in extensions for file in self.test_files_dir.glob(f"*{ext}")]

        return sorted(test_files)[:10]

    def get_sync_benchmarks(
        self,
    ) -> list[tuple[str, Callable[[], ExtractionResult], dict[str, str]]]:
        benchmarks: list[tuple[str, Callable[[], ExtractionResult], dict[str, str]]] = []

        def _make_sync_default(f: Path) -> Callable[[], ExtractionResult]:
            def run() -> ExtractionResult:
                return extract_file_sync(f)

            return run

        def _make_sync_force_ocr(f: Path) -> Callable[[], ExtractionResult]:
            def run() -> ExtractionResult:
                return extract_file_sync(f, config=ExtractionConfig(force_ocr=True))

            return run

        for test_file in self.test_files:
            if not test_file.exists():
                continue

            file_type = test_file.suffix[1:]
            base_name = test_file.stem

            benchmarks.append(
                (
                    f"sync_{file_type}_{base_name}_default",
                    _make_sync_default(test_file),
                    {
                        "file_type": file_type,
                        "file_name": str(test_file.name),
                        "config": "default",
                    },
                )
            )

            if file_type in ["pdf", "png", "jpg", "jpeg"]:
                benchmarks.append(
                    (
                        f"sync_{file_type}_{base_name}_force_ocr",
                        _make_sync_force_ocr(test_file),
                        {
                            "file_type": file_type,
                            "file_name": str(test_file.name),
                            "config": "force_ocr",
                        },
                    )
                )

        if len(self.test_files) >= 3:
            small_batch = self.test_files[:3]
            medium_batch = self.test_files[: min(5, len(self.test_files))]

            benchmarks.extend(
                [
                    (
                        "sync_batch_small",
                        (lambda: [extract_file_sync(f) for f in small_batch][-1]),
                        {"batch_size": str(len(small_batch)), "config": "sequential"},
                    ),
                    (
                        "sync_batch_medium",
                        (lambda: [extract_file_sync(f) for f in medium_batch][-1]),
                        {"batch_size": str(len(medium_batch)), "config": "sequential"},
                    ),
                ]
            )

        return benchmarks

    def get_async_benchmarks(
        self,
    ) -> list[tuple[str, Callable[[], Awaitable[ExtractionResult]], dict[str, str]]]:
        benchmarks: list[tuple[str, Callable[[], Awaitable[ExtractionResult]], dict[str, str]]] = []

        def _make_async_default(f: Path) -> Callable[[], Awaitable[ExtractionResult]]:
            async def run() -> ExtractionResult:
                return await extract_file(f)

            return run

        def _make_async_force_ocr(f: Path) -> Callable[[], Awaitable[ExtractionResult]]:
            async def run() -> ExtractionResult:
                return await extract_file(f, config=ExtractionConfig(force_ocr=True))

            return run

        for test_file in self.test_files:
            if not test_file.exists():
                continue

            file_type = test_file.suffix[1:]
            base_name = test_file.stem

            benchmarks.append(
                (
                    f"async_{file_type}_{base_name}_default",
                    _make_async_default(test_file),
                    {
                        "file_type": file_type,
                        "file_name": str(test_file.name),
                        "config": "default",
                    },
                )
            )

            if file_type in ["pdf", "png", "jpg", "jpeg"]:
                benchmarks.append(
                    (
                        f"async_{file_type}_{base_name}_force_ocr",
                        _make_async_force_ocr(test_file),
                        {
                            "file_type": file_type,
                            "file_name": str(test_file.name),
                            "config": "force_ocr",
                        },
                    )
                )

        if len(self.test_files) >= 3:
            small_batch = self.test_files[:3]
            medium_batch = self.test_files[: min(5, len(self.test_files))]

            async def _run_small(files: list[Path]) -> ExtractionResult:
                res = await batch_extract_file(files)
                return res[-1]

            async def _run_medium(files: list[Path]) -> ExtractionResult:
                res = await batch_extract_file(files)
                return res[-1]

            async def _run_seq(files: list[Path]) -> ExtractionResult:
                results = [await extract_file(f) for f in files]
                return results[-1]

            def make_async_runner(
                fn: Callable[[list[Path]], Awaitable[ExtractionResult]], files: list[Path]
            ) -> Callable[[], Awaitable[ExtractionResult]]:
                async def run() -> ExtractionResult:
                    return await fn(files)

                return run

            benchmarks.extend(
                [
                    (
                        "async_batch_small_concurrent",
                        make_async_runner(_run_small, small_batch),
                        {"batch_size": str(len(small_batch)), "config": "concurrent"},
                    ),
                    (
                        "async_batch_medium_concurrent",
                        make_async_runner(_run_medium, medium_batch),
                        {"batch_size": str(len(medium_batch)), "config": "concurrent"},
                    ),
                    (
                        "async_batch_small_sequential",
                        make_async_runner(_run_seq, small_batch),
                        {
                            "batch_size": str(len(small_batch)),
                            "config": "sequential_async",
                        },
                    ),
                ]
            )

        return benchmarks

    def get_comparison_benchmarks(
        self,
    ) -> list[
        tuple[
            str,
            Callable[[], ExtractionResult] | Callable[[], Awaitable[ExtractionResult]],
            dict[str, str],
        ]
    ]:
        if not self.test_files:
            return []

        test_file = self.test_files[0]

        def _make_sync_default(f: Path) -> Callable[[], ExtractionResult]:
            def run() -> ExtractionResult:
                return extract_file_sync(f)

            return run

        def _make_async_default(f: Path) -> Callable[[], Awaitable[ExtractionResult]]:
            async def run() -> ExtractionResult:
                return await extract_file(f)

            return run

        benchmarks: list[
            tuple[
                str,
                Callable[[], ExtractionResult] | Callable[[], Awaitable[ExtractionResult]],
                dict[str, str],
            ]
        ] = []

        benchmarks.extend(
            [
                (
                    "comparison_sync_default",
                    _make_sync_default(test_file),
                    {
                        "type": "sync",
                        "operation": "single_file",
                        "file": str(test_file.name),
                    },
                ),
                (
                    "comparison_async_default",
                    _make_async_default(test_file),
                    {
                        "type": "async",
                        "operation": "single_file",
                        "file": str(test_file.name),
                    },
                ),
            ]
        )

        if len(self.test_files) >= 3:
            batch_files = self.test_files[:3]

            async def _cmp_async(files: list[Path]) -> ExtractionResult:
                res = await batch_extract_file(files)
                return res[-1]

            benchmarks.extend(
                [
                    (
                        "comparison_sync_batch",
                        lambda: [extract_file_sync(f) for f in batch_files][-1],
                        {
                            "type": "sync",
                            "operation": "batch",
                            "batch_size": str(len(batch_files)),
                        },
                    ),
                    (
                        "comparison_async_batch",
                        (lambda files=batch_files: _cmp_async(files)),
                        {
                            "type": "async",
                            "operation": "batch",
                            "batch_size": str(len(batch_files)),
                        },
                    ),
                ]
            )

        return benchmarks

    def get_stress_benchmarks(
        self,
    ) -> list[
        tuple[
            str,
            Callable[[], ExtractionResult] | Callable[[], Awaitable[ExtractionResult]],
            dict[str, str],
        ]
    ]:
        if len(self.test_files) < 2:
            return []

        all_files = self.test_files * 2
        large_batch = all_files[: min(10, len(all_files))]

        async def _async_large(files: list[Path]) -> ExtractionResult:
            res = await batch_extract_file(files)
            return res[-1]

        return [
            (
                "stress_sync_large_batch",
                lambda: [extract_file_sync(f) for f in large_batch][-1],
                {
                    "type": "stress",
                    "operation": "sync_batch",
                    "batch_size": str(len(large_batch)),
                },
            ),
            (
                "stress_async_large_batch",
                (lambda files=large_batch: _async_large(files)),
                {
                    "type": "stress",
                    "operation": "async_batch",
                    "batch_size": str(len(large_batch)),
                },
            ),
        ]

    def get_backend_benchmarks(
        self,
    ) -> list[tuple[str, Callable[[], ExtractionResult], dict[str, str]]]:
        benchmarks: list[tuple[str, Callable[[], ExtractionResult], dict[str, str]]] = []

        for test_file in self.test_files:
            if not test_file.exists():
                continue

            file_type = test_file.suffix[1:]
            base_name = test_file.stem

            def make_extractor(file_path: Path) -> Callable[[], ExtractionResult]:
                return lambda: extract_file_sync(file_path)

            benchmarks.append(
                (
                    f"kreuzberg_{file_type}_{base_name}",
                    make_extractor(test_file),
                    {
                        "file_type": file_type,
                        "file_name": str(test_file.name),
                        "backend": "kreuzberg",
                        "operation": "extract_file_sync",
                    },
                )
            )

        return benchmarks

    def get_tesseract_ocr_benchmarks(
        self,
    ) -> list[tuple[str, Callable[[], ExtractionResult], dict[str, str]]]:
        image_files = [p for p in self.test_files if p.suffix.lower() in {".png", ".jpg", ".jpeg"}]
        image_files = image_files[:4] if len(image_files) > 4 else image_files

        if not image_files:
            return []

        backend = TesseractBackend()
        cfg = TesseractConfig(language="eng")

        def run_threads() -> ExtractionResult:
            results = backend.process_batch_sync(image_files, **cfg.__dict__)  # type: ignore[arg-type]
            return results[-1]

        def run_processes() -> ExtractionResult:
            cfg_dict: dict[str, object] = {}
            for field_name in cfg.__dataclass_fields__:
                value = getattr(cfg, field_name)
                cfg_dict[field_name] = getattr(value, "value", value)

            results_ordered: list[ExtractionResult | None] = [None] * len(image_files)
            with process_pool() as pool:
                fut_to_idx = {pool.submit(worker, str(p), cfg_dict): i for i, p in enumerate(image_files)}
                for fut in as_completed(fut_to_idx):
                    i = fut_to_idx[fut]
                    rd = fut.result()
                    if rd.get("success"):
                        results_ordered[i] = ExtractionResult(
                            content=str(rd.get("text", "")),
                            mime_type=PLAIN_TEXT_MIME_TYPE,
                            metadata={},
                            chunks=[],
                        )
                    else:
                        results_ordered[i] = ExtractionResult(
                            content=f"[OCR error: {rd.get('error')}]",
                            mime_type=PLAIN_TEXT_MIME_TYPE,
                            metadata={},
                            chunks=[],
                        )

            if results_ordered[-1] is None:
                raise RuntimeError("No results from OCR processing")
            return results_ordered[-1]

        return [
            (
                "tesseract_threads_batch_sync",
                run_threads,
                {"backend": "tesseract", "mode": "threads", "operation": "batch_sync", "n": str(len(image_files))},
            ),
            (
                "tesseract_process_pool_batch_sync",
                run_processes,
                {"backend": "tesseract", "mode": "process_pool", "operation": "batch_sync", "n": str(len(image_files))},
            ),
        ]

    def get_tesseract_variant_benchmarks(
        self,
    ) -> list[tuple[str, Callable[[], ExtractionResult], dict[str, str]]]:
        image_files = [p for p in self.test_files if p.suffix.lower() in {".png", ".jpg", ".jpeg"}]
        image_files = image_files[:4] if len(image_files) > 4 else image_files

        if not image_files:
            return []

        backend = TesseractBackend()

        formats = ["text", "markdown", "tsv"]
        psms: list[PSMMode | int] = [PSMMode.AUTO, PSMMode.SINGLE_BLOCK, PSMMode.SINGLE_LINE]

        benches: list[tuple[str, Callable[[], ExtractionResult], dict[str, str]]] = []

        for ofmt in formats:
            for psm in psms:
                enable_tables = ofmt in {"markdown", "tsv"}
                cfg = TesseractConfig(
                    language="eng",
                    output_format=ofmt,  # type: ignore[arg-type]
                    psm=psm,  # type: ignore[arg-type]
                    enable_table_detection=enable_tables,
                )

                def make_runner(config: TesseractConfig) -> Callable[[], ExtractionResult]:
                    def _run() -> ExtractionResult:
                        results = backend.process_batch_sync(image_files, **config.__dict__)  # type: ignore[arg-type]
                        return results[-1]

                    return _run

                name = (
                    f"tesseract_threads_sync_ofmt={ofmt}_psm={psm.value if hasattr(psm, 'value') else psm}"
                    f"_tables={'on' if enable_tables else 'off'}"
                )

                benches.append(
                    (
                        name,
                        make_runner(cfg),
                        {
                            "backend": "tesseract",
                            "mode": "threads",
                            "operation": "batch_sync",
                            "n": str(len(image_files)),
                            "output_format": ofmt,
                            "psm": str(psm.value if hasattr(psm, "value") else psm),
                            "tables": "on" if enable_tables else "off",
                        },
                    )
                )

        return benches

    def get_tesseract_architecture_benchmarks(
        self,
        workers: list[int] | None = None,
    ) -> list[tuple[str, Callable[[], ExtractionResult], dict[str, str]]]:
        image_files = [p for p in self.test_files if p.suffix.lower() in {".png", ".jpg", ".jpeg"}]
        image_files = image_files[:6] if len(image_files) > 6 else image_files
        if not image_files:
            return []

        backend = TesseractBackend()
        cfg = TesseractConfig(language="eng", output_format="text")

        if not workers:
            c = max(1, cpu_count())
            workers = sorted({1, max(1, c // 2), c})

        def make_threads_runner(n: int) -> Callable[[], ExtractionResult]:
            def _run() -> ExtractionResult:
                results: list[ExtractionResult | None] = [None] * len(image_files)

                def task(i: int, p: Path) -> tuple[int, ExtractionResult]:
                    return (i, backend.process_file_sync(p, **cfg.__dict__))

                with ThreadPoolExecutor(max_workers=n) as ex:
                    futs = {ex.submit(task, i, p): i for i, p in enumerate(image_files)}
                    for fut in as_completed(futs):
                        i, res = fut.result()
                        results[i] = res
                if results[-1] is None:
                    raise RuntimeError("No results from OCR processing")
                return results[-1]

            return _run

        def make_process_runner(_n: int) -> Callable[[], ExtractionResult]:
            def _run() -> ExtractionResult:
                cfg_dict: dict[str, object] = {}
                for field_name in cfg.__dataclass_fields__:
                    val = getattr(cfg, field_name)
                    cfg_dict[field_name] = getattr(val, "value", val)

                results: list[ExtractionResult | None] = [None] * len(image_files)
                with process_pool() as pool:
                    futs = {pool.submit(proc_worker, str(p), cfg_dict): i for i, p in enumerate(image_files)}
                    for fut in as_completed(futs):
                        i = futs[fut]
                        rd = fut.result()
                        if rd.get("success"):
                            results[i] = ExtractionResult(
                                content=str(rd.get("text", "")),
                                mime_type=PLAIN_TEXT_MIME_TYPE,
                                metadata={},
                                chunks=[],
                            )
                        else:
                            results[i] = ExtractionResult(
                                content=f"[OCR error: {rd.get('error')}]",
                                mime_type=PLAIN_TEXT_MIME_TYPE,
                                metadata={},
                                chunks=[],
                            )
                if results[-1] is None:
                    raise RuntimeError("No results from OCR processing")
                return results[-1]

            return _run

        benches: list[tuple[str, Callable[[], ExtractionResult], dict[str, str]]] = []
        for n in workers:
            benches.append(
                (
                    f"tesseract_threads_n={n}",
                    make_threads_runner(n),
                    {"backend": "tesseract", "arch": "threads", "workers": str(n)},
                )
            )
            benches.append(
                (
                    f"tesseract_processes_n={n}",
                    make_process_runner(n),
                    {"backend": "tesseract", "arch": "processes", "workers": str(n)},
                )
            )

        return benches

    def get_image_benchmarks(
        self,
    ) -> list[
        tuple[
            str,
            Callable[[], ExtractionResult] | Callable[[], Awaitable[ExtractionResult]],
            dict[str, str],
        ]
    ]:
        benchmarks: list[
            tuple[
                str,
                Callable[[], ExtractionResult] | Callable[[], Awaitable[ExtractionResult]],
                dict[str, str],
            ]
        ] = []

        for test_file in self.test_files:
            if not test_file.exists():
                continue

            file_type = test_file.suffix[1:]
            base_name = test_file.stem

            cfg_images_only = ExtractionConfig(extract_images=True, extract_tables=False)
            cfg_images_text = ExtractionConfig(extract_images=True)

            benchmarks.append(
                (
                    f"sync_image_extraction_{file_type}_{base_name}_images_only",
                    (lambda f=test_file, cfg=cfg_images_only: extract_file_sync(f, config=cfg)),
                    {"mode": "sync", "variant": "images_only", "file": str(test_file.name)},
                )
            )
            benchmarks.append(
                (
                    f"sync_image_extraction_{file_type}_{base_name}_images_and_text",
                    (lambda f=test_file, cfg=cfg_images_text: extract_file_sync(f, config=cfg)),
                    {"mode": "sync", "variant": "images_and_text", "file": str(test_file.name)},
                )
            )

            benchmarks.append(
                (
                    f"async_image_extraction_{file_type}_{base_name}_images_only",
                    (lambda f=test_file, cfg=cfg_images_only: extract_file(f, config=cfg)),
                    {"mode": "async", "variant": "images_only", "file": str(test_file.name)},
                )
            )
            benchmarks.append(
                (
                    f"async_image_extraction_{file_type}_{base_name}_images_and_text",
                    (lambda f=test_file, cfg=cfg_images_text: extract_file(f, config=cfg)),
                    {"mode": "async", "variant": "images_and_text", "file": str(test_file.name)},
                )
            )

        return benchmarks

    def get_image_stress_benchmarks(
        self,
    ) -> list[
        tuple[
            str,
            Callable[[], ExtractionResult] | Callable[[], Awaitable[ExtractionResult]],
            dict[str, str],
        ]
    ]:
        benchmarks: list[
            tuple[
                str,
                Callable[[], ExtractionResult] | Callable[[], Awaitable[ExtractionResult]],
                dict[str, str],
            ]
        ] = []

        pdf_files = [f for f in self.test_files if f.suffix.lower() == ".pdf"]
        if not pdf_files:
            return benchmarks

        for test_file in pdf_files[:3]:
            cfg = ExtractionConfig(extract_images=True)

            def make_sync_loop(file_path: Path, cfg_local: ExtractionConfig = cfg) -> Callable[[], ExtractionResult]:
                def _runner() -> ExtractionResult:
                    result: ExtractionResult | None = None
                    for _ in range(5):
                        result = extract_file_sync(file_path, config=cfg_local)
                    if result is None:
                        raise RuntimeError("image stress benchmark returned no result")
                    return result

                return _runner

            def make_async_loop(
                file_path: Path, cfg_local: ExtractionConfig = cfg
            ) -> Callable[[], Awaitable[ExtractionResult]]:
                async def _runner() -> ExtractionResult:
                    result: ExtractionResult | None = None
                    for _ in range(5):
                        result = await extract_file(file_path, config=cfg_local)
                    if result is None:
                        raise RuntimeError("image stress benchmark returned no result")
                    return result

                return _runner

            benchmarks.append(
                (
                    f"sync_image_stress_pdf_{test_file.stem}",
                    make_sync_loop(test_file),
                    {"mode": "sync", "variant": "image_stress", "file": str(test_file.name)},
                )
            )
            benchmarks.append(
                (
                    f"async_image_stress_pdf_{test_file.stem}",
                    make_async_loop(test_file),
                    {"mode": "async", "variant": "image_stress", "file": str(test_file.name)},
                )
            )

        return benchmarks
