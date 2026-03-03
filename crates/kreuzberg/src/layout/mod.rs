//! Layout detection via ONNX Runtime (YOLO + RT-DETR).
//!
//! This module provides ONNX-based document layout detection, integrated into
//! the kreuzberg extraction pipeline. Models are auto-downloaded from HuggingFace
//! on first use.

pub mod engine;
pub mod error;
mod model_manager;
pub mod models;
pub mod postprocessing;
pub mod preprocessing;
pub mod session;
pub mod types;

pub use engine::{CustomModelVariant, LayoutEngine, LayoutEngineConfig, LayoutPreset, ModelBackend};
pub use error::LayoutError;
pub use model_manager::LayoutModelManager;
pub use models::LayoutModel;
pub use models::rtdetr::RtDetrModel;
pub use models::yolo::{YoloModel, YoloVariant};
pub use types::{BBox, DetectionResult, LayoutClass, LayoutDetection};

use crate::core::config::layout::LayoutDetectionConfig;

/// Convert an [`LayoutDetectionConfig`] into a [`LayoutEngineConfig`].
pub fn config_from_extraction(layout_config: &LayoutDetectionConfig) -> LayoutEngineConfig {
    let preset: LayoutPreset = layout_config.preset.parse().unwrap_or_else(|_| {
        tracing::warn!(
            preset = %layout_config.preset,
            "unrecognized layout preset, falling back to 'fast'"
        );
        LayoutPreset::Fast
    });

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
