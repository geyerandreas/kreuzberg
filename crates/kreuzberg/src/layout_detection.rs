//! Layout detection via ONNX Runtime (YOLO + RT-DETR).
//!
//! This module wraps `kreuzberg-layout` and integrates it into the kreuzberg
//! extraction pipeline. Models are auto-downloaded from HuggingFace on first use.

pub use kreuzberg_layout::{
    BBox, CustomModelVariant, DetectionResult, LayoutClass, LayoutDetection, LayoutEngine, LayoutEngineConfig,
    LayoutError, LayoutModelManager, LayoutPreset, ModelBackend,
};

use crate::core::config::layout::LayoutDetectionConfig;

/// Convert an [`LayoutDetectionConfig`] into a [`LayoutEngineConfig`].
pub fn config_from_extraction(layout_config: &LayoutDetectionConfig) -> LayoutEngineConfig {
    let preset: LayoutPreset = layout_config.preset.parse().unwrap_or(LayoutPreset::Fast);

    let mut engine_config = LayoutEngineConfig::from_preset(preset);
    engine_config.confidence_threshold = layout_config.confidence_threshold;
    engine_config.apply_heuristics = layout_config.apply_heuristics;
    engine_config
}

/// Create a [`LayoutEngine`] from a [`LayoutDetectionConfig`].
///
/// Ensures ORT is available, then creates the engine with model download.
pub fn create_engine(layout_config: &LayoutDetectionConfig) -> Result<LayoutEngine, LayoutError> {
    crate::ort_discovery::ensure_ort_available();
    let config = config_from_extraction(layout_config);
    LayoutEngine::from_config(config)
}
