//! Model downloading and caching for layout detection.
//!
//! Downloads ONNX models from HuggingFace Hub and caches them locally.
//! Uses shared download/checksum utilities from [`crate::model_download`].

use std::fs;
use std::path::{Path, PathBuf};

use crate::layout::error::LayoutError;
use crate::model_download;

/// Model definition for a layout model.
#[derive(Debug, Clone)]
struct ModelDefinition {
    model_type: &'static str,
    hf_repo_id: &'static str,
    remote_filename: &'static str,
    local_filename: &'static str,
    sha256_checksum: &'static str,
}

const MODELS: &[ModelDefinition] = &[
    ModelDefinition {
        model_type: "rtdetr",
        hf_repo_id: "Kreuzberg/layout-models",
        remote_filename: "rtdetr/model.onnx",
        local_filename: "model.onnx",
        sha256_checksum: "3bf2fb0ee6df87435b7ae47f0f3930ec3dc97ec56fd824acc6d57bc7a6b89ef2",
    },
    ModelDefinition {
        model_type: "slanet_plus",
        hf_repo_id: "Kreuzberg/layout-models",
        remote_filename: "slanet-plus/model.onnx",
        local_filename: "slanet-plus.onnx",
        sha256_checksum: "a7024cc76213586c74fcf33757bf909a83cf9c76d93cdb326515de5bccfbb697",
    },
];

/// Manages layout model downloading, caching, and path resolution.
#[derive(Debug, Clone)]
pub struct LayoutModelManager {
    cache_dir: PathBuf,
}

impl LayoutModelManager {
    /// Creates a new model manager.
    ///
    /// If `cache_dir` is None, uses the default cache directory:
    /// 1. `KREUZBERG_CACHE_DIR` env var + `/layout`
    /// 2. `.kreuzberg/layout/` in current directory
    pub fn new(cache_dir: Option<PathBuf>) -> Self {
        let cache_dir = cache_dir.unwrap_or_else(|| model_download::resolve_cache_dir("layout"));
        Self { cache_dir }
    }

    /// Ensure the RT-DETR model (Docling Heron) exists locally, downloading if needed.
    pub fn ensure_rtdetr_model(&self) -> Result<PathBuf, LayoutError> {
        self.ensure_model("rtdetr")
    }

    fn ensure_model(&self, model_type: &str) -> Result<PathBuf, LayoutError> {
        let definition = MODELS
            .iter()
            .find(|m| m.model_type == model_type)
            .ok_or_else(|| LayoutError::ModelDownload(format!("Unknown model type: {model_type}")))?;

        let model_dir = self.cache_dir.join(model_type);
        let model_file = model_dir.join(definition.local_filename);

        if model_file.exists() {
            tracing::debug!(model_type, "Layout model found in cache");
            return Ok(model_file);
        }

        tracing::info!(
            model_type,
            repo = definition.hf_repo_id,
            "Downloading layout model from HuggingFace..."
        );
        fs::create_dir_all(&model_dir).map_err(|e| {
            LayoutError::ModelDownload(format!("Failed to create cache dir {}: {e}", model_dir.display()))
        })?;

        let cached_path = model_download::hf_download(definition.hf_repo_id, definition.remote_filename)
            .map_err(LayoutError::ModelDownload)?;

        model_download::verify_sha256(&cached_path, definition.sha256_checksum, model_type)
            .map_err(LayoutError::ModelDownload)?;

        fs::copy(&cached_path, &model_file).map_err(|e| {
            LayoutError::ModelDownload(format!("Failed to copy model to {}: {e}", model_file.display()))
        })?;

        tracing::info!(path = %model_file.display(), model_type, "Layout model saved to cache");
        Ok(model_file)
    }

    /// Check if the RT-DETR model is cached.
    pub fn is_rtdetr_cached(&self) -> bool {
        self.cache_dir.join("rtdetr").join("model.onnx").exists()
    }

    /// Ensure the SLANet-plus table structure recognition model exists locally, downloading if needed.
    pub fn ensure_slanet_plus_model(&self) -> Result<PathBuf, LayoutError> {
        self.ensure_model("slanet_plus")
    }

    /// Check if the SLANet-plus model is cached.
    pub fn is_slanet_plus_cached(&self) -> bool {
        self.cache_dir.join("slanet_plus").join("slanet-plus.onnx").exists()
    }

    /// Get the cache directory path.
    pub fn cache_dir(&self) -> &Path {
        &self.cache_dir
    }
}
