# Layout Detection

Detect document layout regions (tables, figures, headers, text blocks, etc.) in PDFs using ONNX-based deep learning models.

## Overview

Layout detection analyzes document pages to identify and classify structural regions. This enables downstream tasks such as table extraction, figure isolation, and reading-order reconstruction.

Kreuzberg ships two model presets:

| Preset       | Model          | Classes | Speed   | Best For                                    |
| ------------ | -------------- | ------- | ------- | ------------------------------------------- |
| `"fast"`     | YOLO DocLayNet | 11      | Fastest | High-throughput pipelines, general documents |
| `"accurate"` | RT-DETR v2     | 17      | Fast    | Complex layouts, forms, mixed-content pages  |

!!! note "Feature gate"
    Layout detection requires the `layout-detection` Cargo feature. It is not included in the default feature set.

## When to Use Layout Detection

- **Table extraction** -- Locate tables before running OCR or structure parsing.
- **Figure isolation** -- Identify pictures, charts, and diagrams for downstream processing.
- **Reading-order reconstruction** -- Use bounding boxes to determine logical reading order.
- **Selective OCR** -- Only OCR regions classified as text, skipping decorative elements.
- **Document understanding pipelines** -- Feed layout regions into LLMs for structured extraction.

## Model Presets

### Fast (YOLO DocLayNet)

The default preset. Uses a YOLO model trained on the DocLayNet dataset. Detects 11 layout classes:

`Caption`, `Footnote`, `Formula`, `ListItem`, `PageFooter`, `PageHeader`, `Picture`, `SectionHeader`, `Table`, `Text`, `Title`

### Accurate (RT-DETR v2)

Uses an RT-DETR v2 model with NMS-free detection. Detects all 17 layout classes including the 11 above plus:

`DocumentIndex`, `Code`, `CheckboxSelected`, `CheckboxUnselected`, `Form`, `KeyValueRegion`

## Configuration

### Programmatic Configuration

=== "Python"

    ```python
    from kreuzberg import ExtractionConfig, LayoutDetectionConfig, extract_file

    config = ExtractionConfig(
        layout=LayoutDetectionConfig(
            preset="accurate",
            confidence_threshold=0.5,
            apply_heuristics=True,
        )
    )

    result = await extract_file("document.pdf", config=config)
    ```

=== "TypeScript"

    ```typescript
    import { extract } from "kreuzberg";

    const result = await extract("document.pdf", {
      layout: {
        preset: "accurate",
        confidenceThreshold: 0.5,
        applyHeuristics: true,
      },
    });
    ```

=== "Rust"

    ```rust
    use kreuzberg::core::{ExtractionConfig, LayoutDetectionConfig};

    let config = ExtractionConfig {
        layout: Some(LayoutDetectionConfig {
            preset: "accurate".to_string(),
            confidence_threshold: Some(0.5),
            apply_heuristics: true,
        }),
        ..Default::default()
    };
    ```

### Configuration Files

=== "TOML"

    ```toml title="kreuzberg.toml"
    [layout]
    preset = "fast"
    # confidence_threshold = 0.4   # optional override
    apply_heuristics = true
    ```

=== "YAML"

    ```yaml title="kreuzberg.yaml"
    layout:
      preset: fast
      # confidence_threshold: 0.4
      apply_heuristics: true
    ```

### Environment Variable

Set `KREUZBERG_LAYOUT_PRESET` to enable layout detection with a preset without modifying code or config files:

```bash
export KREUZBERG_LAYOUT_PRESET=accurate
```

Valid values: `fast`, `accurate` (aliases `yolo`, `rtdetr`, `rt-detr` are also accepted).

When this variable is set and no `layout` configuration exists, a default `LayoutDetectionConfig` is created with the specified preset.

## Model Download and Caching

Models are ONNX files downloaded automatically from HuggingFace on first use. Downloaded models are cached locally so subsequent runs start instantly.

**Default cache location**: `$HOME/.cache/kreuzberg/models/`

You can override the cache directory by setting the `cache_dir` field on `LayoutEngineConfig` when using the Rust API directly.

!!! tip "CI and Docker"
    In containerized environments, mount or pre-populate the model cache directory to avoid downloading models on every container start.

## GPU Acceleration

Layout detection uses ONNX Runtime (ORT) for inference. ORT supports multiple execution providers for hardware acceleration:

| Provider   | Platform      | Notes                                    |
| ---------- | ------------- | ---------------------------------------- |
| CPU        | All           | Default, no extra setup                  |
| CUDA       | Linux, Windows| Requires CUDA toolkit and cuDNN          |
| CoreML     | macOS         | Automatic on Apple Silicon               |
| TensorRT   | Linux         | Requires TensorRT installation           |

ORT automatically selects the best available execution provider at runtime. No configuration is needed -- if CUDA libraries are present, GPU inference is used automatically.

## Layout Classes Reference

All model backends map their native class IDs to a shared set of 17 canonical classes:

| Class                 | ID | Fast | Accurate | Description                            |
| --------------------- | -- | ---- | -------- | -------------------------------------- |
| `Caption`             | 0  | Yes  | Yes      | Figure or table caption                |
| `Footnote`            | 1  | Yes  | Yes      | Page footnote                          |
| `Formula`             | 2  | Yes  | Yes      | Mathematical formula                   |
| `ListItem`            | 3  | Yes  | Yes      | List item or bullet point              |
| `PageFooter`          | 4  | Yes  | Yes      | Running page footer                    |
| `PageHeader`          | 5  | Yes  | Yes      | Running page header                    |
| `Picture`             | 6  | Yes  | Yes      | Image, chart, or diagram               |
| `SectionHeader`       | 7  | Yes  | Yes      | Section or subsection heading          |
| `Table`               | 8  | Yes  | Yes      | Tabular data region                    |
| `Text`                | 9  | Yes  | Yes      | Body text paragraph                    |
| `Title`               | 10 | Yes  | Yes      | Document or page title                 |
| `DocumentIndex`       | 11 | --   | Yes      | Table of contents or index             |
| `Code`                | 12 | --   | Yes      | Code block or listing                  |
| `CheckboxSelected`    | 13 | --   | Yes      | Checked checkbox                       |
| `CheckboxUnselected`  | 14 | --   | Yes      | Unchecked checkbox                     |
| `Form`                | 15 | --   | Yes      | Form region                            |
| `KeyValueRegion`      | 16 | --   | Yes      | Key-value pair region                  |

## Related Documentation

- [Configuration Reference](../reference/configuration.md#layoutdetectionconfig) -- Full field reference
- [Type Reference](../reference/types.md#layoutdetectionconfig) -- Type definitions across languages
- [Element-Based Output](element-based-output.md) -- Using layout-aware extraction results
