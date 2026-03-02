//! High-level layout detection engine.
//!
//! Provides [`LayoutEngine`] as the main entry point for layout detection,
//! with [`LayoutPreset`] for simple configuration and [`LayoutEngineConfig`]
//! for full programmatic control.

use std::fmt;
use std::path::PathBuf;
use std::str::FromStr;

use image::RgbImage;
use serde::{Deserialize, Serialize};

use crate::error::LayoutError;
use crate::model_manager::LayoutModelManager;
use crate::models::LayoutModel;
use crate::models::rtdetr::RtDetrModel;
use crate::models::yolo::{YoloModel, YoloVariant};
use crate::postprocessing::heuristics;
use crate::types::DetectionResult;

/// Preset for layout detection model selection.
///
/// Used by language bindings (Python, Node.js, etc.) for simple configuration.
/// Rust users who need fine-grained control should use [`LayoutEngineConfig`] instead.
///
/// Currently both presets use the Docling Heron RT-DETR v2 model (17 document
/// layout classes). Additional model backends may be added in future releases.
#[derive(Debug, Default, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum LayoutPreset {
    /// Fast detection. Currently uses RT-DETR v2 (Docling Heron).
    #[default]
    Fast,
    /// Accurate detection using RT-DETR v2 (Docling Heron, 17 classes, NMS-free).
    Accurate,
}

impl fmt::Display for LayoutPreset {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            LayoutPreset::Fast => write!(f, "fast"),
            LayoutPreset::Accurate => write!(f, "accurate"),
        }
    }
}

impl FromStr for LayoutPreset {
    type Err = String;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s.to_lowercase().as_str() {
            "fast" | "yolo" => Ok(LayoutPreset::Fast),
            "accurate" | "rtdetr" | "rt-detr" | "heron" => Ok(LayoutPreset::Accurate),
            _ => Err(format!("Invalid layout preset: '{s}'. Valid presets: fast, accurate")),
        }
    }
}

/// Which underlying model architecture to use.
#[derive(Debug, Clone)]
pub enum ModelBackend {
    /// YOLO trained on DocLayNet (11 classes, 640x640 input).
    YoloDocLayNet,
    /// RT-DETR v2 (17 classes, 640x640 input, NMS-free).
    RtDetr,
    /// Custom model from a local file path.
    Custom { path: PathBuf, variant: CustomModelVariant },
}

/// Variant selection for custom model paths.
#[derive(Debug, Clone)]
pub enum CustomModelVariant {
    RtDetr,
    YoloDocLayNet,
    YoloDocStructBench,
    Yolox { input_width: u32, input_height: u32 },
}

/// Full configuration for the layout engine.
///
/// Provides fine-grained control over model selection, thresholds, and
/// postprocessing. For simple use cases, prefer [`LayoutPreset`].
#[derive(Debug, Clone)]
pub struct LayoutEngineConfig {
    /// Which model backend to use.
    pub backend: ModelBackend,
    /// Confidence threshold override (None = use model default).
    pub confidence_threshold: Option<f32>,
    /// Whether to apply postprocessing heuristics.
    pub apply_heuristics: bool,
    /// Custom cache directory for model files (None = default).
    pub cache_dir: Option<PathBuf>,
}

impl Default for LayoutEngineConfig {
    fn default() -> Self {
        Self::from_preset(LayoutPreset::default())
    }
}

impl LayoutEngineConfig {
    /// Create a config from a preset.
    pub fn from_preset(preset: LayoutPreset) -> Self {
        let backend = match preset {
            // Both presets currently use RT-DETR (Docling Heron).
            // A dedicated fast model may be added in future releases.
            LayoutPreset::Fast | LayoutPreset::Accurate => ModelBackend::RtDetr,
        };
        Self {
            backend,
            confidence_threshold: None,
            apply_heuristics: true,
            cache_dir: None,
        }
    }
}

/// High-level layout detection engine.
///
/// Wraps model loading, inference, and postprocessing into a single
/// reusable object. Models are downloaded and cached on first use.
pub struct LayoutEngine {
    model: Box<dyn LayoutModel>,
    config: LayoutEngineConfig,
}

impl LayoutEngine {
    /// Create a layout engine from a preset.
    ///
    /// Downloads the model from HuggingFace on first use, caching it locally.
    pub fn from_preset(preset: LayoutPreset) -> Result<Self, LayoutError> {
        let config = LayoutEngineConfig::from_preset(preset);
        Self::from_config(config)
    }

    /// Create a layout engine from a full config.
    pub fn from_config(config: LayoutEngineConfig) -> Result<Self, LayoutError> {
        crate::ort_discovery::ensure_ort_available();

        let model: Box<dyn LayoutModel> = match &config.backend {
            ModelBackend::YoloDocLayNet => {
                return Err(LayoutError::ModelDownload(
                    "YOLO DocLayNet model is not available for automatic download. \
                     Use ModelBackend::Custom with a local YOLO ONNX file instead."
                        .to_string(),
                ));
            }
            ModelBackend::RtDetr => {
                let manager = LayoutModelManager::new(config.cache_dir.clone());
                let model_path = manager.ensure_rtdetr_model()?;
                let path_str = model_path.to_string_lossy();
                Box::new(RtDetrModel::from_file(&path_str)?)
            }
            ModelBackend::Custom { path, variant } => {
                let path_str = path.to_string_lossy();
                match variant {
                    CustomModelVariant::RtDetr => Box::new(RtDetrModel::from_file(&path_str)?),
                    CustomModelVariant::YoloDocLayNet => Box::new(YoloModel::from_file(
                        &path_str,
                        YoloVariant::DocLayNet,
                        640,
                        640,
                        "Custom-YOLO-DocLayNet",
                    )?),
                    CustomModelVariant::YoloDocStructBench => Box::new(YoloModel::from_file(
                        &path_str,
                        YoloVariant::DocStructBench,
                        1024,
                        1024,
                        "Custom-DocLayout-YOLO",
                    )?),
                    CustomModelVariant::Yolox {
                        input_width,
                        input_height,
                    } => Box::new(YoloModel::from_file(
                        &path_str,
                        YoloVariant::Yolox,
                        *input_width,
                        *input_height,
                        "Custom-YOLOX",
                    )?),
                }
            }
        };

        Ok(Self { model, config })
    }

    /// Run layout detection on an image.
    ///
    /// Returns a [`DetectionResult`] with bounding boxes, classes, and confidence scores.
    /// If `apply_heuristics` is enabled in config, postprocessing is applied automatically.
    pub fn detect(&mut self, img: &RgbImage) -> Result<DetectionResult, LayoutError> {
        let mut detections = if let Some(threshold) = self.config.confidence_threshold {
            self.model.detect_with_threshold(img, threshold)?
        } else {
            self.model.detect(img)?
        };

        let page_width = img.width();
        let page_height = img.height();

        if self.config.apply_heuristics {
            heuristics::apply_heuristics(&mut detections, page_width as f32, page_height as f32);
        }

        Ok(DetectionResult::new(page_width, page_height, detections))
    }

    /// Get the model name.
    pub fn model_name(&self) -> &str {
        self.model.name()
    }
}
