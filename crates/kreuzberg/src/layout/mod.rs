//! Layout detection via ONNX Runtime (YOLO + RT-DETR).
//!
//! This module provides ONNX-based document layout detection, integrated into
//! the kreuzberg extraction pipeline. Models are auto-downloaded from HuggingFace
//! on first use.
//!
//! The ONNX session is cached globally so that repeated extractions (e.g. batch
//! processing) pay model-load cost only once.

pub mod engine;
pub mod error;
pub(crate) mod inference_timings;
mod model_manager;
pub mod models;
pub mod postprocessing;
pub mod preprocessing;
pub mod session;
pub mod types;

pub use engine::{CustomModelVariant, DetectTimings, LayoutEngine, LayoutEngineConfig, LayoutPreset, ModelBackend};
pub use error::LayoutError;
pub use model_manager::LayoutModelManager;
pub use models::LayoutModel;
pub use models::rtdetr::RtDetrModel;
pub use models::yolo::{YoloModel, YoloVariant};
pub use types::{BBox, DetectionResult, LayoutClass, LayoutDetection};

use std::sync::OnceLock;

use crate::core::config::layout::LayoutDetectionConfig;
use crate::model_cache::ModelCache;

/// Global cached layout engine.
static CACHED_ENGINE: ModelCache<LayoutEngine> = ModelCache::new();

/// Global cached TATR table structure recognition model.
static CACHED_TATR: ModelCache<models::tatr::TatrModel> = ModelCache::new();

/// Tracks whether TATR loading has been attempted.
///
/// `true` means loading succeeded at least once; `false` means it failed and
/// we should not retry (avoids repeated model-download attempts and redundant
/// warning logs on every document).
static TATR_TRIED: OnceLock<bool> = OnceLock::new();

/// Convert an [`LayoutDetectionConfig`] into a [`LayoutEngineConfig`].
pub fn config_from_extraction(layout_config: &LayoutDetectionConfig) -> LayoutEngineConfig {
    let preset: LayoutPreset = layout_config.preset.parse().unwrap_or_else(|_| {
        tracing::warn!(
            preset = %layout_config.preset,
            "unrecognized layout preset, falling back to 'accurate'"
        );
        LayoutPreset::Accurate
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

/// Take the cached layout engine, or create a new one if the cache is empty.
///
/// The caller owns the engine for the duration of its work and should
/// return it via [`return_engine`] when done. This avoids holding the
/// global mutex during inference.
pub fn take_or_create_engine(layout_config: &LayoutDetectionConfig) -> Result<LayoutEngine, LayoutError> {
    CACHED_ENGINE.take_or_create(|| create_engine(layout_config))
}

/// Return a layout engine to the global cache for reuse by future extractions.
pub fn return_engine(engine: LayoutEngine) {
    CACHED_ENGINE.put(engine);
}

/// Take the cached TATR model, or create a new one if the cache is empty.
///
/// Returns `None` if the model cannot be loaded. Once a load attempt fails,
/// subsequent calls return `None` immediately without retrying, avoiding
/// repeated download attempts and redundant warning logs.
pub fn take_or_create_tatr() -> Option<models::tatr::TatrModel> {
    // Fast path: if we already know TATR is unavailable, skip immediately.
    if let Some(&false) = TATR_TRIED.get() {
        return None;
    }

    let result = CACHED_TATR.take_or_create(|| {
        crate::ort_discovery::ensure_ort_available();
        let manager = LayoutModelManager::new(None);
        let model_path = manager.ensure_tatr_model()?;
        models::tatr::TatrModel::from_file(&model_path.to_string_lossy())
    });

    match result {
        Ok(model) => {
            // Mark as available (no-op if already set to true).
            TATR_TRIED.get_or_init(|| true);
            Some(model)
        }
        Err(e) => {
            // Only log and set the flag on the first failure.
            TATR_TRIED.get_or_init(|| {
                tracing::warn!("TATR table structure model unavailable, table structure recognition disabled: {e}");
                false
            });
            None
        }
    }
}

/// Return a TATR model to the global cache for reuse.
pub fn return_tatr(model: models::tatr::TatrModel) {
    CACHED_TATR.put(model);
}

// ---------------------------------------------------------------------------
// SLANeXT table model caching
// ---------------------------------------------------------------------------

/// Global cached SLANeXT wired model.
static CACHED_SLANET_WIRED: ModelCache<models::slanet::SlanetModel> = ModelCache::new();

/// Global cached SLANeXT wireless model.
static CACHED_SLANET_WIRELESS: ModelCache<models::slanet::SlanetModel> = ModelCache::new();

/// Global cached SLANet-plus model.
static CACHED_SLANET_PLUS: ModelCache<models::slanet::SlanetModel> = ModelCache::new();

/// Global cached table classifier model.
static CACHED_TABLE_CLASSIFIER: ModelCache<models::table_classifier::TableClassifier> = ModelCache::new();

/// Tracks whether SLANeXT loading has been attempted per variant.
static SLANET_WIRED_TRIED: OnceLock<bool> = OnceLock::new();
static SLANET_WIRELESS_TRIED: OnceLock<bool> = OnceLock::new();
static SLANET_PLUS_TRIED: OnceLock<bool> = OnceLock::new();
static TABLE_CLASSIFIER_TRIED: OnceLock<bool> = OnceLock::new();

/// Which table structure model to use.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TableModelBackend {
    /// TATR (Table Transformer) — default, 30MB.
    Tatr,
    /// SLANeXT wired variant — 365MB, optimized for bordered tables.
    SlanetWired,
    /// SLANeXT wireless variant — 365MB, optimized for borderless tables.
    SlanetWireless,
    /// SLANet-plus — 7.78MB, lightweight general-purpose.
    SlanetPlus,
    /// Classifier-routed SLANeXT: auto-select wired/wireless per table.
    /// Uses PP-LCNet classifier (6.78MB) + both SLANeXT variants (730MB total).
    SlanetAuto,
}

impl TableModelBackend {
    /// Parse from config string.
    pub fn from_config(s: Option<&str>) -> Self {
        match s {
            Some("slanet_wired") => Self::SlanetWired,
            Some("slanet_wireless") => Self::SlanetWireless,
            Some("slanet_plus") => Self::SlanetPlus,
            Some("slanet_auto") => Self::SlanetAuto,
            Some("tatr") | None => Self::Tatr,
            Some(unknown) => {
                tracing::warn!(table_model = unknown, "Unknown table model, falling back to TATR");
                Self::Tatr
            }
        }
    }
}

/// Take a cached SLANeXT model for the given variant, or create a new one.
pub fn take_or_create_slanet(variant: &str) -> Option<models::slanet::SlanetModel> {
    let (cache, tried) = match variant {
        "slanet_wired" => (&CACHED_SLANET_WIRED, &SLANET_WIRED_TRIED),
        "slanet_wireless" => (&CACHED_SLANET_WIRELESS, &SLANET_WIRELESS_TRIED),
        "slanet_plus" => (&CACHED_SLANET_PLUS, &SLANET_PLUS_TRIED),
        _ => return None,
    };

    if let Some(&false) = tried.get() {
        return None;
    }

    let result = cache.take_or_create(|| {
        crate::ort_discovery::ensure_ort_available();
        let manager = LayoutModelManager::new(None);
        let model_path = manager.ensure_slanet_model(variant)?;
        models::slanet::SlanetModel::from_file(&model_path.to_string_lossy())
    });

    match result {
        Ok(model) => {
            tried.get_or_init(|| true);
            Some(model)
        }
        Err(e) => {
            tried.get_or_init(|| {
                tracing::warn!(variant, "SLANeXT model unavailable: {e}");
                false
            });
            None
        }
    }
}

/// Return a SLANeXT model to the global cache for reuse.
pub fn return_slanet(variant: &str, model: models::slanet::SlanetModel) {
    match variant {
        "slanet_wired" => CACHED_SLANET_WIRED.put(model),
        "slanet_wireless" => CACHED_SLANET_WIRELESS.put(model),
        "slanet_plus" => CACHED_SLANET_PLUS.put(model),
        _ => {}
    }
}

/// Take a cached table classifier, or create a new one.
pub fn take_or_create_table_classifier() -> Option<models::table_classifier::TableClassifier> {
    if let Some(&false) = TABLE_CLASSIFIER_TRIED.get() {
        return None;
    }

    let result = CACHED_TABLE_CLASSIFIER.take_or_create(|| {
        crate::ort_discovery::ensure_ort_available();
        let manager = LayoutModelManager::new(None);
        let model_path = manager.ensure_table_classifier()?;
        models::table_classifier::TableClassifier::from_file(&model_path.to_string_lossy())
    });

    match result {
        Ok(model) => {
            TABLE_CLASSIFIER_TRIED.get_or_init(|| true);
            Some(model)
        }
        Err(e) => {
            TABLE_CLASSIFIER_TRIED.get_or_init(|| {
                tracing::warn!("Table classifier unavailable: {e}");
                false
            });
            None
        }
    }
}

/// Return a table classifier to the global cache for reuse.
pub fn return_table_classifier(model: models::table_classifier::TableClassifier) {
    CACHED_TABLE_CLASSIFIER.put(model);
}
