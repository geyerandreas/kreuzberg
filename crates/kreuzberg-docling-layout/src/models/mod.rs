pub mod detectron2;
pub mod rtdetr;
pub mod yolo;

use image::RgbImage;

use crate::error::LayoutError;
use crate::types::LayoutDetection;

/// Common interface for all layout detection model backends.
pub trait LayoutModel {
    /// Run layout detection on an image using the default confidence threshold.
    fn detect(&mut self, img: &RgbImage) -> Result<Vec<LayoutDetection>, LayoutError>;

    /// Run layout detection with a custom confidence threshold.
    fn detect_with_threshold(&mut self, img: &RgbImage, threshold: f32) -> Result<Vec<LayoutDetection>, LayoutError>;

    /// Human-readable model name for benchmark output.
    fn name(&self) -> &str;
}
