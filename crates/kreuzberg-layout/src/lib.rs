#![deny(unsafe_code)]

pub mod engine;
pub mod error;
mod model_manager;
pub mod models;
#[allow(unsafe_code)]
pub mod ort_discovery;
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
