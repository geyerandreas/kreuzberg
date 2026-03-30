//! Centralized image OCR processing.
//!
//! Provides a shared function for processing extracted images with OCR,
//! used by DOCX, PPTX, Jupyter, Markdown, and other extractors.

#[cfg(all(feature = "ocr", feature = "tokio-runtime"))]
use crate::ocr::OcrProcessor;
use crate::types::{ExtractedImage, ExtractionResult, Metadata};

/// Process extracted images with OCR if configured.
///
/// For each image, spawns a blocking OCR task and stores the result
/// in `image.ocr_result`. If OCR is not configured or fails for an
/// individual image, that image's `ocr_result` remains `None`.
///
/// This function is the single shared implementation used by all
/// document extractors (DOCX, PPTX, Jupyter, Markdown, etc.).
#[cfg(all(feature = "ocr", feature = "tokio-runtime"))]
pub async fn process_images_with_ocr(
    mut images: Vec<ExtractedImage>,
    config: &crate::core::config::ExtractionConfig,
) -> crate::Result<Vec<ExtractedImage>> {
    if config.ocr.is_none() {
        return Ok(images);
    }

    let ocr_config = config.ocr.as_ref().unwrap();
    let tess_config = ocr_config.tesseract_config.as_ref().cloned().unwrap_or_default();
    let output_format = config.output_format;

    use tokio::task::JoinSet;

    // Each spawned task returns `(image_index, spawn_blocking_result)`.
    // `spawn_blocking` itself may fail if the thread panics; we carry that
    // as a `Result` so we can translate it into a `KreuzbergError` in the
    // collection loop below, keeping the JoinSet item type concrete.
    type OcrTaskResult = (
        usize,
        Result<Result<crate::types::OcrExtractionResult, crate::ocr::error::OcrError>, tokio::task::JoinError>,
    );
    let mut join_set: JoinSet<OcrTaskResult> = JoinSet::new();

    for (idx, image) in images.iter().enumerate() {
        let image_data = image.data.clone();
        let tess_config_clone = tess_config.clone();
        let span = tracing::Span::current();

        join_set.spawn(async move {
            let blocking_result = tokio::task::spawn_blocking(move || {
                let _guard = span.entered();
                let cache_dir = std::env::var("KREUZBERG_CACHE_DIR").ok().map(std::path::PathBuf::from);

                let proc = OcrProcessor::new(cache_dir)?;
                let ocr_tess_config: crate::ocr::types::TesseractConfig = (&tess_config_clone).into();
                proc.process_image_with_format(&image_data, &ocr_tess_config, output_format)
            })
            .await;
            (idx, blocking_result)
        });
    }

    while let Some(join_result) = join_set.join_next().await {
        // JoinSet join error means the async wrapper itself panicked, which is
        // not expected; propagate as a hard error.
        let (idx, blocking_result) = join_result.map_err(|e| crate::KreuzbergError::Ocr {
            message: format!("OCR task panicked: {}", e),
            source: None,
        })?;

        // Translate spawn_blocking join error (thread panic) into a KreuzbergError.
        let ocr_result = blocking_result.map_err(|e| crate::KreuzbergError::Ocr {
            message: format!("OCR blocking task panicked: {}", e),
            source: None,
        })?;

        match ocr_result {
            Ok(ocr_extraction) => {
                let extraction_result = ExtractionResult {
                    content: ocr_extraction.content,
                    mime_type: ocr_extraction.mime_type.into(),
                    metadata: Metadata::default(),
                    tables: vec![],
                    detected_languages: None,
                    chunks: None,
                    images: None,
                    djot_content: None,
                    pages: None,
                    elements: None,
                    ocr_elements: ocr_extraction.ocr_elements,
                    document: None,
                    #[cfg(any(feature = "keywords-yake", feature = "keywords-rake"))]
                    extracted_keywords: None,
                    quality_score: None,
                    processing_warnings: Vec::new(),
                    annotations: None,
                    children: None,
                    uris: None,
                    formatted_content: None,
                };
                images[idx].ocr_result = Some(Box::new(extraction_result));
            }
            Err(_) => {
                images[idx].ocr_result = None;
            }
        }
    }

    Ok(images)
}
