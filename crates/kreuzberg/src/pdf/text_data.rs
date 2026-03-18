//! Single-pass pdfium text extraction DTO.
//!
//! Extracts all per-character data from a PDF page in one pass through
//! `page.text().chars()`, avoiding redundant FFI calls. Downstream consumers
//! (`chars_to_segments`, ligature repair, etc.) operate on the pre-extracted
//! `PageTextData` instead of re-querying the pdfium API.

use pdfium_render::prelude::*;

/// All character data extracted from pdfium in a single pass.
#[derive(Clone, Debug)]
pub(crate) struct ExtractedChar {
    pub ch: char,
    pub x: f32,
    pub y: f32,
    pub right_x: f32,
    pub font_size: f32,
    pub is_bold: bool,
    pub is_italic: bool,
    pub is_monospace: bool,
    pub is_symbolic: bool,
    pub has_map_error: bool,
    /// True for pdfium-generated synthetic word boundary characters.
    /// Used by the ligature repair map builder; will also be consumed
    /// by the hierarchy extraction path.
    #[allow(dead_code)]
    pub is_generated: bool,
    pub is_hyphen: bool,
    /// Numeric font weight (100-900, 0 if unavailable).
    /// Used by the hierarchy extraction path for heading detection.
    #[allow(dead_code)]
    pub font_weight: u32,
}

/// A pre-merged text run from pdfium's segment API (`FPDFText_CountRects`/`GetRect`).
///
/// Pdfium groups characters sharing the same baseline and font settings into
/// segments, with proper word boundary detection via CMap knowledge. Each
/// segment represents a contiguous run of same-style text on a single line.
#[derive(Debug, Clone)]
pub(crate) struct ExtractedSegment {
    pub text: String,
    pub x: f32,
    pub y: f32,
    pub width: f32,
    pub height: f32,
    pub font_size: f32,
    pub is_bold: bool,
    pub is_italic: bool,
    pub is_monospace: bool,
    pub baseline_y: f32,
}

/// Pre-extracted text data for a single PDF page.
///
/// Built once via `extract_page_text_data`, then consumed by downstream
/// processing (segment assembly, ligature repair, etc.) without further
/// pdfium calls on the page's text layer.
pub(crate) struct PageTextData {
    pub chars: Vec<ExtractedChar>,
    /// Full text as returned by `page.text().all()`.
    /// Used by downstream consumers for whole-page text analysis
    /// (e.g., contextual ligature detection, broken word spacing).
    #[allow(dead_code)]
    pub full_text: String,
    pub ligature_repair_map: Option<Vec<(char, &'static str)>>,
    /// Pre-merged text segments from pdfium's rect-based API.
    /// Each segment shares baseline and font settings. May be empty
    /// if the page has no text or segment extraction fails.
    pub segments: Vec<ExtractedSegment>,
}

/// Extract all text data from a PDF page in a single pass.
///
/// Calls `page.text()` once, iterates `chars()` once, and calls
/// `font_info()` once per character. Builds the ligature repair map
/// inline from characters with encoding errors.
///
/// Returns `None` if the page has no text or `page.text()` fails.
pub(crate) fn extract_page_text_data(page: &PdfPage) -> Option<PageTextData> {
    let text_obj = page.text().ok()?;
    let full_text = text_obj.all();
    let chars = text_obj.chars();
    let char_count = chars.len();
    if char_count == 0 {
        return None;
    }

    let mut extracted: Vec<ExtractedChar> = Vec::with_capacity(char_count);
    let mut repair_map: Vec<(char, &'static str)> = Vec::new();
    let mut has_any_map_error = false;

    for i in 0..char_count {
        let ch = match chars.get(i) {
            Ok(c) => c,
            Err(_) => continue,
        };

        // Generated chars (pdfium's synthetic word boundaries): push as space markers.
        if ch.is_generated().unwrap_or(false) {
            let (x, y) = if let Some(last) = extracted.last() {
                (last.x + last.font_size * 0.5, last.y)
            } else {
                (0.0, 0.0)
            };
            let space_fs = extracted.last().map_or(12.0, |c| c.font_size);
            extracted.push(ExtractedChar {
                ch: ' ',
                x,
                y,
                right_x: x + space_fs * 0.6,
                font_size: space_fs,
                is_bold: false,
                is_italic: false,
                is_monospace: false,
                is_symbolic: false,
                has_map_error: false,
                is_generated: true,
                is_hyphen: false,
                font_weight: 0,
            });
            continue;
        }

        // Filter invalid unicode, control chars, soft hyphens.
        let unicode_val = ch.unicode_value();
        if unicode_val == 0xFFFE || unicode_val == 0xFFFF || unicode_val == 0 {
            continue;
        }
        let uc = match char::from_u32(unicode_val) {
            Some(c) => c,
            None => continue,
        };
        if uc.is_control() && uc != '\n' && uc != '\r' && uc != '\t' {
            continue;
        }
        if uc == '\u{00AD}' {
            continue;
        }

        let origin = match ch.origin() {
            Ok(o) => o,
            Err(_) => continue,
        };
        let fs = ch.scaled_font_size().value;
        let effective_fs = if fs > 0.0 { fs } else { 12.0 };
        let right_x = ch
            .tight_bounds()
            .map(|b| b.right().value)
            .unwrap_or(origin.0.value + effective_fs * 0.6);

        // Single font_info() call per character (was 2x in old code path).
        let font_info = ch.font_info();
        let has_map_error = ch.has_unicode_map_error().unwrap_or(false);
        let is_symbolic = ch.font_is_symbolic();
        let is_hyphen = ch.is_hyphen().unwrap_or(false);
        let font_weight = ch
            .font_weight()
            .map(|w| match w {
                PdfFontWeight::Weight100 => 100,
                PdfFontWeight::Weight200 => 200,
                PdfFontWeight::Weight300 => 300,
                PdfFontWeight::Weight400Normal => 400,
                PdfFontWeight::Weight500 => 500,
                PdfFontWeight::Weight600 => 600,
                PdfFontWeight::Weight700Bold => 700,
                PdfFontWeight::Weight800 => 800,
                PdfFontWeight::Weight900 => 900,
                PdfFontWeight::Custom(w) => w,
            })
            .unwrap_or(0);

        // Build ligature repair map inline.
        if has_map_error && !is_symbolic {
            has_any_map_error = true;
            let mapped_char = uc;
            if !repair_map.iter().any(|(c, _)| *c == mapped_char) {
                let ligature = match unicode_val {
                    // Standard Type1/CM ligature positions (low bytes)
                    0x0B => Some("ff"),
                    0x0C => Some("fi"),
                    0x0D => Some("fl"),
                    0x0E => Some("ffi"),
                    0x0F => Some("ffl"),
                    // Alternate low-byte positions
                    0x01 => Some("fi"),
                    0x02 => Some("fl"),
                    0x03 => Some("ff"),
                    0x04 => Some("ffi"),
                    0x05 => Some("ffl"),
                    // ASCII positions (broken CMap)
                    0x21 => Some("fi"),
                    0x22 => Some("ff"),
                    0x23 => Some("fl"),
                    0x24 => Some("ffi"),
                    0x25 => Some("ffl"),
                    _ => None,
                };
                if let Some(lig) = ligature {
                    repair_map.push((mapped_char, lig));
                }
            }
        }

        extracted.push(ExtractedChar {
            ch: uc,
            x: origin.0.value,
            y: origin.1.value,
            right_x,
            font_size: effective_fs,
            is_bold: font_info.1,
            is_italic: font_info.2,
            is_monospace: ch.font_is_fixed_pitch(),
            is_symbolic,
            has_map_error,
            is_generated: false,
            is_hyphen,
            font_weight,
        });
    }

    let _ = has_any_map_error; // used only to gate repair_map construction above

    // Extract segments (pdfium's pre-merged text runs via FPDFText_CountRects/GetRect).
    let pdfium_segments = text_obj.segments();
    let seg_count = pdfium_segments.len();
    let mut segments = Vec::with_capacity(seg_count);
    for i in 0..seg_count {
        if let Ok(seg) = pdfium_segments.get(i) {
            let text = seg.text();
            if text.trim().is_empty() {
                continue;
            }
            let bounds = seg.bounds();
            // Sample font properties from the first non-whitespace character in the segment.
            let (font_size, is_bold, is_italic, is_monospace, baseline_y) = if let Ok(seg_chars) = seg.chars() {
                let mut fs = 12.0_f32;
                let mut bold = false;
                let mut italic = false;
                let mut mono = false;
                let mut bl_y = bounds.bottom().value;
                let mut found = false;
                for ch in seg_chars.iter() {
                    let uv = ch.unicode_value();
                    if let Some(uc) = char::from_u32(uv)
                        && uc.is_whitespace()
                    {
                        continue;
                    }
                    let scaled = ch.scaled_font_size().value;
                    fs = if scaled > 0.0 { scaled } else { 12.0 };
                    let info = ch.font_info();
                    bold = info.1;
                    italic = info.2;
                    mono = ch.font_is_fixed_pitch();
                    if let Ok(origin) = ch.origin() {
                        bl_y = origin.1.value;
                    }
                    found = true;
                    break;
                }
                if !found {
                    continue; // skip segment if no real chars found
                }
                (fs, bold, italic, mono, bl_y)
            } else {
                // chars() failed; use bounds for geometry, defaults for font
                (12.0, false, false, false, bounds.bottom().value)
            };

            segments.push(ExtractedSegment {
                text,
                x: bounds.left().value,
                y: bounds.bottom().value,
                width: bounds.width().value,
                height: bounds.height().value,
                font_size,
                is_bold,
                is_italic,
                is_monospace,
                baseline_y,
            });
        }
    }

    Some(PageTextData {
        chars: extracted,
        full_text,
        ligature_repair_map: if repair_map.is_empty() { None } else { Some(repair_map) },
        segments,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_extracted_char_default_values() {
        let ec = ExtractedChar {
            ch: 'A',
            x: 10.0,
            y: 20.0,
            right_x: 16.0,
            font_size: 12.0,
            is_bold: false,
            is_italic: false,
            is_monospace: false,
            is_symbolic: false,
            has_map_error: false,
            is_generated: false,
            is_hyphen: false,
            font_weight: 400,
        };
        assert_eq!(ec.ch, 'A');
        assert!(!ec.is_generated);
        assert_eq!(ec.font_weight, 400);
    }
}
