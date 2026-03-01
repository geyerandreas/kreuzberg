//! Model downloading and caching for layout detection.
//!
//! Downloads ONNX models from `Kreuzberg/layout-models` on HuggingFace Hub
//! and caches them locally.

use std::fs;
use std::path::{Path, PathBuf};

use crate::error::LayoutError;

/// HuggingFace repository containing layout detection ONNX models.
const HF_REPO_ID: &str = "Kreuzberg/layout-models";

/// Model definition for a layout model.
#[derive(Debug, Clone)]
struct ModelDefinition {
    model_type: &'static str,
    remote_filename: &'static str,
    local_filename: &'static str,
    sha256_checksum: &'static str,
}

const MODELS: &[ModelDefinition] = &[
    ModelDefinition {
        model_type: "yolo",
        remote_filename: "yolov10-doclaynet.onnx",
        local_filename: "model.onnx",
        // TODO: fill after uploading models to HuggingFace
        sha256_checksum: "",
    },
    ModelDefinition {
        model_type: "rtdetr",
        remote_filename: "rtdetr-v2-docling.onnx",
        local_filename: "model.onnx",
        // TODO: fill after uploading models to HuggingFace
        sha256_checksum: "",
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
        let cache_dir = cache_dir.unwrap_or_else(Self::default_cache_dir);
        Self { cache_dir }
    }

    fn default_cache_dir() -> PathBuf {
        if let Ok(env_path) = std::env::var("KREUZBERG_CACHE_DIR") {
            return PathBuf::from(env_path).join("layout");
        }
        std::env::current_dir()
            .unwrap_or_else(|_| PathBuf::from("."))
            .join(".kreuzberg")
            .join("layout")
    }

    /// Ensure the YOLO model exists locally, downloading if needed.
    pub fn ensure_yolo_model(&self) -> Result<PathBuf, LayoutError> {
        self.ensure_model("yolo")
    }

    /// Ensure the RT-DETR model exists locally, downloading if needed.
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

        tracing::info!(model_type, "Downloading layout model from HuggingFace...");
        fs::create_dir_all(&model_dir).map_err(|e| {
            LayoutError::ModelDownload(format!("Failed to create cache dir {}: {e}", model_dir.display()))
        })?;

        let cached_path = self.hf_download(definition.remote_filename)?;

        if !definition.sha256_checksum.is_empty() {
            Self::verify_checksum(&cached_path, definition.sha256_checksum, model_type)?;
        }

        fs::copy(&cached_path, &model_file).map_err(|e| {
            LayoutError::ModelDownload(format!("Failed to copy model to {}: {e}", model_file.display()))
        })?;

        tracing::info!(path = %model_file.display(), model_type, "Layout model saved to cache");
        Ok(model_file)
    }

    fn hf_download(&self, remote_filename: &str) -> Result<PathBuf, LayoutError> {
        tracing::info!(repo = HF_REPO_ID, filename = remote_filename, "Downloading via hf-hub");

        let api = hf_hub::api::sync::ApiBuilder::new()
            .with_progress(true)
            .build()
            .map_err(|e| LayoutError::ModelDownload(format!("Failed to initialize HF Hub API: {e}")))?;

        let repo = api.model(HF_REPO_ID.to_string());
        let cached_path = repo.get(remote_filename).map_err(|e| {
            LayoutError::ModelDownload(format!("Failed to download '{remote_filename}' from {HF_REPO_ID}: {e}"))
        })?;

        Ok(cached_path)
    }

    fn verify_checksum(path: &Path, expected: &str, label: &str) -> Result<(), LayoutError> {
        if expected.is_empty() {
            return Ok(());
        }

        let bytes =
            fs::read(path).map_err(|e| LayoutError::ModelDownload(format!("Failed to read file for checksum: {e}")))?;

        use sha2::{Digest, Sha256};
        let mut hasher = Sha256::new();
        hasher.update(&bytes);
        let hash_hex = hex::encode(hasher.finalize());

        if hash_hex != expected {
            return Err(LayoutError::ModelDownload(format!(
                "Checksum mismatch for {label}: expected {expected}, got {hash_hex}"
            )));
        }

        tracing::debug!(label, "Checksum verified");
        Ok(())
    }

    /// Check if the YOLO model is cached.
    pub fn is_yolo_cached(&self) -> bool {
        self.cache_dir.join("yolo").join("model.onnx").exists()
    }

    /// Check if the RT-DETR model is cached.
    pub fn is_rtdetr_cached(&self) -> bool {
        self.cache_dir.join("rtdetr").join("model.onnx").exists()
    }

    /// Get the cache directory path.
    pub fn cache_dir(&self) -> &Path {
        &self.cache_dir
    }
}
