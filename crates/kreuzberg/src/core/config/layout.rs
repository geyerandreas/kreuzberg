//! Layout detection configuration.

use serde::{Deserialize, Serialize};

/// Layout detection configuration.
///
/// Controls layout detection behavior in the extraction pipeline.
/// When set on [`ExtractionConfig`](super::ExtractionConfig), layout detection
/// is enabled for PDF extraction.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LayoutDetectionConfig {
    /// Preset for model selection: `"fast"` (YOLO) or `"accurate"` (RT-DETR).
    #[serde(default = "default_preset")]
    pub preset: String,

    /// Confidence threshold override (None = use model default).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub confidence_threshold: Option<f32>,

    /// Whether to apply postprocessing heuristics (default: true).
    #[serde(default = "default_true")]
    pub apply_heuristics: bool,
}

impl Default for LayoutDetectionConfig {
    fn default() -> Self {
        Self {
            preset: default_preset(),
            confidence_threshold: None,
            apply_heuristics: true,
        }
    }
}

fn default_preset() -> String {
    "fast".to_string()
}

fn default_true() -> bool {
    true
}
