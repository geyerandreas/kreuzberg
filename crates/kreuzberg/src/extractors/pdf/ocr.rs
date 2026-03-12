//! OCR functionality for PDF extraction.
//!
//! Handles text quality evaluation, OCR fallback decision logic, and OCR processing.

#[cfg(feature = "ocr")]
use crate::core::config::ExtractionConfig;

#[cfg(feature = "ocr")]
pub(crate) const MIN_TOTAL_NON_WHITESPACE: usize = 64;
#[cfg(feature = "ocr")]
pub(crate) const MIN_NON_WHITESPACE_PER_PAGE: f64 = 32.0;
#[cfg(feature = "ocr")]
pub(crate) const MIN_MEANINGFUL_WORD_LEN: usize = 4;
#[cfg(feature = "ocr")]
pub(crate) const MIN_MEANINGFUL_WORDS: usize = 3;
#[cfg(feature = "ocr")]
pub(crate) const MIN_ALNUM_RATIO: f64 = 0.3;
/// Minimum number of Unicode replacement characters (U+FFFD) to trigger OCR fallback.
#[cfg(feature = "ocr")]
pub(crate) const MIN_GARBAGE_CHARS: usize = 5;
/// Maximum fraction of short (1-2 char) words before text is considered fragmented.
#[cfg(feature = "ocr")]
pub(crate) const MAX_FRAGMENTED_WORD_RATIO: f64 = 0.6;
/// Critical fragmentation threshold: triggers OCR regardless of meaningful word count.
/// Normal English text has ~20-30% short words. 80%+ is definitive garbage.
#[cfg(feature = "ocr")]
pub(crate) const CRITICAL_FRAGMENTED_WORD_RATIO: f64 = 0.80;
/// Minimum average word length. Below this with enough words indicates garbled extraction.
#[cfg(feature = "ocr")]
pub(crate) const MIN_AVG_WORD_LENGTH: f64 = 2.0;
/// Minimum word count before average word length check applies.
#[cfg(feature = "ocr")]
pub(crate) const MIN_WORDS_FOR_AVG_LENGTH_CHECK: usize = 50;
/// Minimum consecutive word repetition ratio to detect column scrambling.
/// When pdfium reads multi-column text row-by-row, the same words appear as
/// consecutive duplicates (e.g., "TALK TALK", "of the of the").
#[cfg(feature = "ocr")]
pub(crate) const MIN_CONSECUTIVE_REPEAT_RATIO: f64 = 0.08;
/// Minimum word count before consecutive repetition check is applied.
#[cfg(feature = "ocr")]
pub(crate) const MIN_WORDS_FOR_REPEAT_CHECK: usize = 50;

#[cfg(feature = "ocr")]
pub struct NativeTextStats {
    pub non_whitespace: usize,
    pub alnum: usize,
    pub meaningful_words: usize,
    pub alnum_ratio: f64,
    /// Count of Unicode replacement characters (U+FFFD) indicating encoding failures.
    pub garbage_char_count: usize,
    /// Fraction of whitespace-delimited words that are 1-2 characters (0.0-1.0).
    /// High values indicate fragmented/garbled text extraction.
    pub fragmented_word_ratio: f64,
    /// Fraction of consecutive word pairs that are identical (0.0-1.0).
    /// High values indicate column scrambling where text is duplicated.
    pub consecutive_repeat_ratio: f64,
    /// Average word length (by chars). Very low values indicate garbled extraction.
    pub avg_word_length: f64,
    /// Total word count (whitespace-delimited).
    pub word_count: usize,
}

#[cfg(feature = "ocr")]
pub struct OcrFallbackDecision {
    pub stats: NativeTextStats,
    pub avg_non_whitespace: f64,
    pub avg_alnum: f64,
    pub fallback: bool,
}

#[cfg(feature = "ocr")]
impl NativeTextStats {
    pub fn from(text: &str) -> Self {
        let mut non_whitespace = 0usize;
        let mut alnum = 0usize;
        let mut garbage_char_count = 0usize;

        for ch in text.chars() {
            if ch == '\u{FFFD}' {
                garbage_char_count += 1;
            }
            if !ch.is_whitespace() {
                non_whitespace += 1;
                if ch.is_alphanumeric() {
                    alnum += 1;
                }
            }
        }

        let meaningful_words = text
            .split_whitespace()
            .filter(|word| {
                word.chars()
                    .filter(|c| c.is_alphanumeric())
                    .take(MIN_MEANINGFUL_WORD_LEN)
                    .count()
                    >= MIN_MEANINGFUL_WORD_LEN
            })
            .take(MIN_MEANINGFUL_WORDS)
            .count();

        let alnum_ratio = if non_whitespace == 0 {
            0.0
        } else {
            alnum as f64 / non_whitespace as f64
        };

        // Compute fragmented word ratio: fraction of words that are 1-2 chars.
        // Only meaningful when there are enough words to judge.
        let words: Vec<&str> = text.split_whitespace().collect();
        let fragmented_word_ratio = if words.len() >= 10 {
            let short_count = words.iter().filter(|w| w.len() <= 2).count();
            short_count as f64 / words.len() as f64
        } else {
            0.0
        };

        // Compute consecutive word repetition ratio: fraction of adjacent word pairs
        // that are identical. High values indicate column scrambling where pdfium
        // reads multi-column text row-by-row, duplicating words.
        let consecutive_repeat_ratio = if words.len() >= MIN_WORDS_FOR_REPEAT_CHECK {
            let repeat_count = words.windows(2).filter(|pair| pair[0] == pair[1]).count();
            repeat_count as f64 / (words.len() - 1) as f64
        } else {
            0.0
        };

        let avg_word_length = if words.is_empty() {
            0.0
        } else {
            words.iter().map(|w| w.len()).sum::<usize>() as f64 / words.len() as f64
        };

        Self {
            non_whitespace,
            alnum,
            meaningful_words,
            alnum_ratio,
            garbage_char_count,
            fragmented_word_ratio,
            consecutive_repeat_ratio,
            avg_word_length,
            word_count: words.len(),
        }
    }
}

/// Evaluates native PDF text quality to determine if OCR fallback is needed.
///
/// Analyzes text characteristics (whitespace, alphanumeric ratio, meaningful words)
/// to detect cases where native text extraction produced poor results (e.g., scanned
/// PDFs with garbled text).
///
/// # Arguments
///
/// * `native_text` - The text extracted from the PDF using native methods
/// * `page_count` - Optional page count for per-page average calculations
///
/// # Returns
///
/// An `OcrFallbackDecision` containing:
/// - Statistics about the text quality
/// - Per-page averages
/// - Boolean decision on whether to use OCR
#[cfg(feature = "ocr")]
pub fn evaluate_native_text_for_ocr(native_text: &str, page_count: Option<usize>) -> OcrFallbackDecision {
    let trimmed = native_text.trim();

    if trimmed.is_empty() {
        let empty_stats = NativeTextStats {
            non_whitespace: 0,
            alnum: 0,
            meaningful_words: 0,
            alnum_ratio: 0.0,
            garbage_char_count: 0,
            fragmented_word_ratio: 0.0,
            consecutive_repeat_ratio: 0.0,
            avg_word_length: 0.0,
            word_count: 0,
        };
        return OcrFallbackDecision {
            stats: empty_stats,
            avg_non_whitespace: 0.0,
            avg_alnum: 0.0,
            fallback: true,
        };
    }

    let stats = NativeTextStats::from(trimmed);
    let pages = page_count.unwrap_or(1).max(1) as f64;
    let avg_non_whitespace = stats.non_whitespace as f64 / pages;
    let avg_alnum = stats.alnum as f64 / pages;

    let has_substantial_text = stats.non_whitespace >= MIN_TOTAL_NON_WHITESPACE
        && avg_non_whitespace >= MIN_NON_WHITESPACE_PER_PAGE
        && stats.meaningful_words >= MIN_MEANINGFUL_WORDS;

    let fallback = if stats.non_whitespace == 0 || stats.alnum == 0 {
        true
    } else if stats.garbage_char_count >= MIN_GARBAGE_CHARS {
        // Many replacement characters indicate encoding failures — OCR is likely better.
        true
    } else if stats.fragmented_word_ratio >= MAX_FRAGMENTED_WORD_RATIO && stats.meaningful_words < MIN_MEANINGFUL_WORDS
    {
        // Mostly 1-2 char "words" with few meaningful words = garbled extraction.
        true
    } else if stats.fragmented_word_ratio >= CRITICAL_FRAGMENTED_WORD_RATIO {
        // ≥80% single-char words is garbled text regardless of meaningful word count.
        // Normal English has ~20-30% short words; 80%+ is definitive garbage.
        true
    } else if stats.avg_word_length < MIN_AVG_WORD_LENGTH && stats.word_count >= MIN_WORDS_FOR_AVG_LENGTH_CHECK {
        // Average word length below 2.0 with enough words indicates per-character extraction.
        true
    } else if stats.consecutive_repeat_ratio >= MIN_CONSECUTIVE_REPEAT_RATIO {
        // High consecutive word repetition indicates column scrambling:
        // pdfium read multi-column text row-by-row, duplicating words.
        true
    } else if has_substantial_text {
        false
    } else if (stats.alnum_ratio < MIN_ALNUM_RATIO && avg_alnum < MIN_NON_WHITESPACE_PER_PAGE)
        || (stats.non_whitespace < MIN_TOTAL_NON_WHITESPACE && avg_non_whitespace < MIN_NON_WHITESPACE_PER_PAGE)
    {
        true
    } else {
        stats.meaningful_words == 0 && avg_non_whitespace < MIN_NON_WHITESPACE_PER_PAGE
    };

    OcrFallbackDecision {
        stats,
        avg_non_whitespace,
        avg_alnum,
        fallback,
    }
}

#[cfg(feature = "ocr")]
pub fn evaluate_per_page_ocr(
    native_text: &str,
    boundaries: Option<&[crate::types::PageBoundary]>,
    page_count: Option<usize>,
) -> OcrFallbackDecision {
    let boundaries = match boundaries {
        Some(b) if !b.is_empty() => b,
        _ => return evaluate_native_text_for_ocr(native_text, page_count),
    };

    let mut document_decision = evaluate_native_text_for_ocr(native_text, page_count);

    for boundary in boundaries {
        if boundary.byte_end > native_text.len() || boundary.byte_start > boundary.byte_end {
            continue;
        }
        let page_text = &native_text[boundary.byte_start..boundary.byte_end];
        if evaluate_native_text_for_ocr(page_text, Some(1)).fallback {
            document_decision.fallback = true;
            return document_decision;
        }
    }

    document_decision
}

/// Render PDF pages to images for OCR processing.
///
/// Returns images at the default OCR DPI (300).
#[cfg(feature = "ocr")]
pub(crate) fn render_pages_for_ocr(content: &[u8]) -> crate::Result<Vec<image::DynamicImage>> {
    use crate::pdf::rendering::{PageRenderOptions, PdfRenderer};

    let render_options = PageRenderOptions::default();
    let renderer = PdfRenderer::new().map_err(|e| crate::KreuzbergError::Parsing {
        message: format!("Failed to initialize PDF renderer: {}", e),
        source: None,
    })?;

    renderer
        .render_all_pages(content, &render_options)
        .map_err(|e| crate::KreuzbergError::Parsing {
            message: format!("Failed to render PDF pages: {}", e),
            source: None,
        })
}

/// Extract text from PDF using OCR on pre-rendered page images.
///
/// When `layout_detections` are provided (pixel-space, from the same images),
/// uses layout-aware markdown assembly for structured output. Otherwise falls
/// back to plain OCR text concatenation.
///
/// # Arguments
///
/// * `images` - Pre-rendered page images (shared with layout detection)
/// * `layout_detections` - Optional pixel-space layout detections per page
/// * `config` - Extraction configuration including OCR settings
///
/// # Returns
///
/// Concatenated text from all pages, with markdown structure when layout is available
#[cfg(feature = "ocr")]
pub(crate) async fn extract_with_ocr(
    images: &[image::DynamicImage],
    #[cfg(feature = "layout-detection")] layout_detections: Option<&[crate::layout::DetectionResult]>,
    config: &ExtractionConfig,
) -> crate::Result<String> {
    use crate::plugins::registry::get_ocr_backend_registry;
    use image::ImageEncoder;
    use image::codecs::png::PngEncoder;
    use std::io::Cursor;

    let base_ocr_config = config.ocr.as_ref().ok_or_else(|| crate::KreuzbergError::Parsing {
        message: "OCR config required for force_ocr".to_string(),
        source: None,
    })?;

    // When layout detections are available, ensure OCR produces elements
    // so the layout assembly module can use them for structured markdown.
    #[cfg(feature = "layout-detection")]
    let layout_ocr_config;
    let ocr_config = {
        #[cfg(feature = "layout-detection")]
        if layout_detections.is_some() {
            layout_ocr_config = ensure_elements_enabled(base_ocr_config);
            &layout_ocr_config
        } else {
            base_ocr_config
        }
        #[cfg(not(feature = "layout-detection"))]
        {
            base_ocr_config
        }
    };

    let backend = {
        let registry = get_ocr_backend_registry();
        let registry = registry.read().map_err(|e| crate::KreuzbergError::Plugin {
            message: format!("Failed to acquire read lock on OCR backend registry: {}", e),
            plugin_name: "ocr-registry".to_string(),
        })?;
        registry.get(&ocr_config.backend)?
    };

    // Initialize SLANet for table structure recognition when layout detection is active
    #[cfg(feature = "layout-detection")]
    let mut slanet = if layout_detections.is_some() {
        init_slanet_model(config)
    } else {
        None
    };

    let mut page_texts = Vec::with_capacity(images.len());

    for (page_idx, image) in images.iter().enumerate() {
        let rgb_image = image.to_rgb8();
        let (width, height) = rgb_image.dimensions();

        let mut image_bytes = Cursor::new(Vec::new());
        let encoder = PngEncoder::new(&mut image_bytes);
        encoder
            .write_image(&rgb_image, width, height, image::ColorType::Rgb8.into())
            .map_err(|e| crate::KreuzbergError::Parsing {
                message: format!("Failed to encode image: {}", e),
                source: None,
            })?;

        let image_data = image_bytes.into_inner();
        let ocr_result = backend.process_image(&image_data, ocr_config).await?;

        // When layout detections are available and OCR produced elements,
        // use layout-aware markdown assembly instead of plain text.
        #[cfg(feature = "layout-detection")]
        if let Some(detections) = layout_detections
            && let Some(ref elements) = ocr_result.ocr_elements
            && !elements.is_empty()
        {
            let detection = detections.get(page_idx);

            // Run SLANet table recognition if available
            let recognized_tables = match (detection, slanet.as_mut()) {
                (Some(det), Some(model)) => {
                    let rgb = image.to_rgb8();
                    crate::ocr::layout_assembly::recognize_page_tables(&rgb, det, elements, model)
                }
                _ => Vec::new(),
            };

            let page_md = crate::ocr::layout_assembly::assemble_ocr_markdown(
                elements,
                detection,
                width,
                height,
                &recognized_tables,
            );
            page_texts.push(page_md);
            continue;
        }

        // Fallback: use plain OCR text
        let _ = page_idx; // used only in layout-detection path above
        page_texts.push(ocr_result.content.to_string());
    }

    let page_marker_cfg = config.pages.as_ref().filter(|p| p.insert_page_markers);
    let mut result = String::new();
    for (i, text) in page_texts.iter().enumerate() {
        if let Some(cfg) = page_marker_cfg {
            let marker = cfg.marker_format.replace("{page_num}", &(i + 1).to_string());
            result.push_str(&marker);
        } else if i > 0 {
            result.push_str("\n\n");
        }
        result.push_str(text);
    }
    Ok(result)
}

/// Clone an OCR config with `include_elements` forced to true.
///
/// Layout assembly requires OCR elements with bounding geometry. This ensures
/// the backend produces them regardless of the user's original config.
#[cfg(all(feature = "ocr", feature = "layout-detection"))]
fn ensure_elements_enabled(config: &crate::core::config::ocr::OcrConfig) -> crate::core::config::ocr::OcrConfig {
    let mut config = config.clone();
    match config.element_config.as_mut() {
        Some(ec) => ec.include_elements = true,
        None => {
            config.element_config = Some(crate::types::OcrElementConfig {
                include_elements: true,
                ..Default::default()
            });
        }
    }
    config
}

/// Try to initialize SLANet model for table structure recognition.
///
/// Returns `None` if the model cannot be loaded (not cached, download failed, etc.)
/// — table regions will fall back to heuristic grid reconstruction.
#[cfg(all(feature = "ocr", feature = "layout-detection"))]
fn init_slanet_model(_config: &ExtractionConfig) -> Option<crate::layout::models::slanet::SlaNetModel> {
    let manager = crate::layout::LayoutModelManager::new(None);

    let model_path = match manager.ensure_slanet_plus_model() {
        Ok(p) => p,
        Err(e) => {
            tracing::debug!("SLANet model not available, tables will use heuristic: {e}");
            return None;
        }
    };

    match crate::layout::models::slanet::SlaNetModel::from_file(&model_path.to_string_lossy()) {
        Ok(model) => {
            tracing::debug!("SLANet-plus table structure recognition initialized");
            Some(model)
        }
        Err(e) => {
            tracing::warn!("Failed to load SLANet model: {e}");
            None
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[cfg(feature = "ocr")]
    #[test]
    fn test_empty_text_triggers_fallback() {
        let decision = evaluate_native_text_for_ocr("", Some(1));
        assert!(decision.fallback);
    }

    #[cfg(feature = "ocr")]
    #[test]
    fn test_replacement_chars_trigger_fallback() {
        let text = "The \u{FFFD}\u{FFFD}\u{FFFD} quick \u{FFFD}\u{FFFD}\u{FFFD} brown fox";
        let stats = NativeTextStats::from(text);
        assert_eq!(stats.garbage_char_count, 6);
        let decision = evaluate_native_text_for_ocr(text, Some(1));
        assert!(decision.fallback);
    }

    #[cfg(feature = "ocr")]
    #[test]
    fn test_fragmented_words_trigger_fallback() {
        // Many 1-2 char words = fragmented extraction
        let text = "T h e q u i c k b r o w n f o x j u m p s";
        let stats = NativeTextStats::from(text);
        assert!(stats.fragmented_word_ratio > 0.8);
        let decision = evaluate_native_text_for_ocr(text, Some(1));
        assert!(decision.fallback);
    }

    #[cfg(feature = "ocr")]
    #[test]
    fn test_good_text_no_fallback() {
        let text = "This is a normal paragraph with meaningful words and proper structure. \
                    It contains multiple sentences that form a coherent text block.";
        let decision = evaluate_native_text_for_ocr(text, Some(1));
        assert!(!decision.fallback);
    }

    #[cfg(feature = "ocr")]
    #[test]
    fn test_per_page_single_bad_page_triggers() {
        use crate::types::PageBoundary;

        let text = "Good text on page one with meaningful content.\x00\x00\x00";
        let boundaries = vec![
            PageBoundary {
                page_number: 1,
                byte_start: 0,
                byte_end: 46,
            },
            PageBoundary {
                page_number: 2,
                byte_start: 46,
                byte_end: text.len(),
            },
        ];
        let decision = evaluate_per_page_ocr(text, Some(&boundaries), Some(2));
        // Page 2 has only null bytes → triggers fallback
        assert!(decision.fallback);
    }

    #[cfg(feature = "ocr")]
    #[test]
    fn test_few_replacement_chars_no_fallback() {
        // Under the threshold — don't trigger
        let text = "The quick \u{FFFD} brown fox jumps over the lazy dog repeatedly.";
        let stats = NativeTextStats::from(text);
        assert_eq!(stats.garbage_char_count, 1);
        let decision = evaluate_native_text_for_ocr(text, Some(1));
        assert!(!decision.fallback);
    }

    #[cfg(feature = "ocr")]
    #[test]
    fn test_consecutive_repeat_detects_column_scrambling() {
        // Simulated scrambled column text: "TALK TALK of of the the TOWN TOWN"
        // Build text with enough words (≥50) to trigger the check
        let mut words = Vec::new();
        for _ in 0..10 {
            words.extend_from_slice(&[
                "TALK", "TALK", "of", "of", "the", "the", "TOWN", "TOWN", "London", "London",
            ]);
        }
        let text = words.join(" ");
        let stats = NativeTextStats::from(&text);
        assert!(
            stats.consecutive_repeat_ratio >= MIN_CONSECUTIVE_REPEAT_RATIO,
            "ratio {} should be >= {}",
            stats.consecutive_repeat_ratio,
            MIN_CONSECUTIVE_REPEAT_RATIO
        );
        let decision = evaluate_native_text_for_ocr(&text, Some(1));
        assert!(decision.fallback, "Scrambled column text should trigger OCR fallback");
    }

    #[cfg(feature = "ocr")]
    #[test]
    fn test_normal_text_no_consecutive_repeat_false_positive() {
        // Normal text with enough words — should NOT trigger
        let text = "The quick brown fox jumps over the lazy dog. This is a completely normal \
                    paragraph of text that forms coherent sentences. It contains multiple \
                    meaningful words and no unusual patterns of repetition. The text continues \
                    with more content that demonstrates typical English prose structure and \
                    vocabulary distribution across several sentences of varying length.";
        let stats = NativeTextStats::from(text);
        assert!(
            stats.consecutive_repeat_ratio < MIN_CONSECUTIVE_REPEAT_RATIO,
            "Normal text ratio {} should be < {}",
            stats.consecutive_repeat_ratio,
            MIN_CONSECUTIVE_REPEAT_RATIO
        );
    }

    #[cfg(feature = "ocr")]
    #[test]
    fn test_critical_fragmentation_triggers_fallback() {
        // 80%+ single-char words WITH some meaningful words — should still trigger.
        // This simulates senate-expenditures: per-character extraction where random
        // fragments occasionally form 4+ char tokens.
        let mut words: Vec<&str> = Vec::new();
        // 90 single-char "words"
        for _ in 0..90 {
            words.push("A");
        }
        // 10 meaningful words (enough to pass meaningful_words >= 3)
        for _ in 0..10 {
            words.push("document");
        }
        let text = words.join(" ");
        let stats = NativeTextStats::from(&text);
        assert!(
            stats.fragmented_word_ratio >= CRITICAL_FRAGMENTED_WORD_RATIO,
            "fragmented ratio {} should be >= {}",
            stats.fragmented_word_ratio,
            CRITICAL_FRAGMENTED_WORD_RATIO
        );
        assert!(stats.meaningful_words >= MIN_MEANINGFUL_WORDS);
        let decision = evaluate_native_text_for_ocr(&text, Some(1));
        assert!(
            decision.fallback,
            "Critical fragmentation should trigger OCR even with meaningful words"
        );
    }

    #[cfg(feature = "ocr")]
    #[test]
    fn test_low_avg_word_length_triggers_fallback() {
        // Average word length < 2.0 with 50+ words — garbled extraction
        let mut words: Vec<&str> = Vec::new();
        for _ in 0..55 {
            words.push("x");
        }
        // Add a few meaningful words so meaningful_words >= 3
        words.push("hello");
        words.push("world");
        words.push("testing");
        let text = words.join(" ");
        let stats = NativeTextStats::from(&text);
        assert!(stats.avg_word_length < MIN_AVG_WORD_LENGTH);
        assert!(stats.word_count >= MIN_WORDS_FOR_AVG_LENGTH_CHECK);
        let decision = evaluate_native_text_for_ocr(&text, Some(1));
        assert!(decision.fallback, "Low avg word length should trigger OCR fallback");
    }

    #[cfg(feature = "ocr")]
    #[test]
    fn test_normal_text_with_articles_no_false_positive() {
        // Text with many natural short words (a, I, to, of, is, it, an, or) should NOT trigger
        let text = "I am a fan of it. It is an old or new idea. A to do list is on my desk. \
                    He is in on it. We do go to it. I am at it. Is it so? He or I do it. \
                    The paragraph contains meaningful content with proper structure and sentences.";
        let stats = NativeTextStats::from(text);
        // Verify it has meaningful words and isn't falsely flagged
        assert!(stats.meaningful_words >= MIN_MEANINGFUL_WORDS);
        assert!(
            stats.fragmented_word_ratio < CRITICAL_FRAGMENTED_WORD_RATIO,
            "Normal text fragmentation {} should be < {}",
            stats.fragmented_word_ratio,
            CRITICAL_FRAGMENTED_WORD_RATIO
        );
        let decision = evaluate_native_text_for_ocr(text, Some(1));
        assert!(
            !decision.fallback,
            "Normal text with short words should not trigger OCR"
        );
    }

    #[cfg(feature = "ocr")]
    #[test]
    fn test_short_words_in_normal_text_no_false_positive() {
        // Natural text with some short words (a, I, to, of, is) mixed with meaningful words
        let text = "I am a fan of this document. He is on to something here. \
                    We do have meaningful words like paragraph and structure throughout.";
        let stats = NativeTextStats::from(text);
        assert!(stats.meaningful_words >= MIN_MEANINGFUL_WORDS);
        let decision = evaluate_native_text_for_ocr(text, Some(1));
        assert!(!decision.fallback);
    }
}
