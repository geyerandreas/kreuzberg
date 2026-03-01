//! Detectron2 (Faster R-CNN / Mask R-CNN) layout detection via ONNX.
//!
//! Based on the unstructuredio models and layoutparser-ort implementation.
//! Reference: https://github.com/styrowolf/layoutparser-ort (Apache-2.0)

use image::RgbImage;
use ndarray::Array;
use ort::{inputs, session::Session, value::Tensor};

use crate::error::LayoutError;
use crate::models::LayoutModel;
use crate::types::{BBox, LayoutClass, LayoutDetection};

/// Default confidence threshold (Detectron2 outputs are already NMS-filtered,
/// so a higher threshold is appropriate).
const DEFAULT_THRESHOLD: f32 = 0.8;

/// Fixed input dimensions for the unstructuredio Detectron2 models.
const INPUT_WIDTH: u32 = 800;
const INPUT_HEIGHT: u32 = 1035;

/// Which output index contains the confidence scores.
#[derive(Debug, Clone, Copy)]
pub enum Detectron2Variant {
    /// Faster R-CNN: scores at output index 2.
    FasterRcnn,
    /// Mask R-CNN: scores at output index 3 (index 2 is masks).
    MaskRcnn,
}

/// Detectron2-based layout detection model (Faster R-CNN or Mask R-CNN).
///
/// These models already include NMS in the ONNX graph, so outputs are
/// filtered detections (no NMS post-processing needed).
///
/// Input: `"x.1"` — f32 [3, 1035, 800] (CHW, raw 0-255 pixels, no normalization)
/// Outputs:
///   - [0] boxes: f32 [num_dets, 4] (x1, y1, x2, y2 in input coordinates)
///   - [1] labels: i64 [num_dets]
///   - [2] scores (Faster R-CNN) or masks (Mask R-CNN)
///   - [3] scores (Mask R-CNN only)
pub struct Detectron2Model {
    session: Session,
    variant: Detectron2Variant,
    model_name: String,
}

impl Detectron2Model {
    /// Load a Detectron2 ONNX model from a file.
    pub fn from_file(path: &str, variant: Detectron2Variant, model_name: &str) -> Result<Self, LayoutError> {
        let session = crate::session::build_session(path)?;
        Ok(Self {
            session,
            variant,
            model_name: model_name.to_string(),
        })
    }

    fn score_output_index(&self) -> usize {
        match self.variant {
            Detectron2Variant::FasterRcnn => 2,
            Detectron2Variant::MaskRcnn => 3,
        }
    }

    fn run_inference(&mut self, img: &RgbImage, threshold: f32) -> Result<Vec<LayoutDetection>, LayoutError> {
        let orig_width = img.width();
        let orig_height = img.height();

        // Extract score index before mutable borrow of session.
        let score_idx = self.score_output_index();

        // Preprocess: resize to 800x1035, raw pixel values 0-255, CHW (no batch dim).
        let input_tensor = preprocess_detectron2(img);
        let images_tensor = Tensor::from_array(input_tensor)?;

        let outputs = self.session.run(inputs!["x.1" => images_tensor])?;

        // Collect outputs into owned data to avoid lifetime issues with output views.
        let mut boxes_data: Vec<f32> = Vec::new();
        let mut labels_data: Vec<i64> = Vec::new();
        let mut scores_data: Vec<f32> = Vec::new();

        for (idx, (_name, value)) in outputs.iter().enumerate() {
            if idx == 0 {
                // Boxes: f32 [num_dets, 4]
                let view = value
                    .try_extract_tensor::<f32>()
                    .map_err(|e| LayoutError::InvalidOutput(format!("boxes: {e}")))?;
                boxes_data = view.1.to_vec();
            } else if idx == 1 {
                // Labels: i64 [num_dets]
                let view = value
                    .try_extract_tensor::<i64>()
                    .map_err(|e| LayoutError::InvalidOutput(format!("labels: {e}")))?;
                labels_data = view.1.to_vec();
            } else if idx == score_idx {
                // Scores: f32 [num_dets]
                let view = value
                    .try_extract_tensor::<f32>()
                    .map_err(|e| LayoutError::InvalidOutput(format!("scores: {e}")))?;
                scores_data = view.1.to_vec();
            }
        }

        if boxes_data.is_empty() || labels_data.is_empty() || scores_data.is_empty() {
            return Err(LayoutError::InvalidOutput(
                "Missing required outputs (boxes, labels, or scores)".into(),
            ));
        }

        let width_scale = orig_width as f32 / INPUT_WIDTH as f32;
        let height_scale = orig_height as f32 / INPUT_HEIGHT as f32;

        let num_dets = scores_data.len();
        let mut detections = Vec::new();

        for i in 0..num_dets {
            let score = scores_data[i];
            if score < threshold {
                continue;
            }

            let label_id = labels_data[i];
            let class = LayoutClass::from_publaynet_id(label_id).unwrap_or(LayoutClass::Text);

            let x1 = boxes_data[i * 4] * width_scale;
            let y1 = boxes_data[i * 4 + 1] * height_scale;
            let x2 = boxes_data[i * 4 + 2] * width_scale;
            let y2 = boxes_data[i * 4 + 3] * height_scale;

            detections.push(LayoutDetection::new(class, score, BBox::new(x1, y1, x2, y2)));
        }

        detections.sort_by(|a, b| {
            b.confidence
                .partial_cmp(&a.confidence)
                .unwrap_or(std::cmp::Ordering::Equal)
        });

        Ok(detections)
    }
}

impl LayoutModel for Detectron2Model {
    fn detect(&mut self, img: &RgbImage) -> Result<Vec<LayoutDetection>, LayoutError> {
        self.run_inference(img, DEFAULT_THRESHOLD)
    }

    fn detect_with_threshold(&mut self, img: &RgbImage, threshold: f32) -> Result<Vec<LayoutDetection>, LayoutError> {
        self.run_inference(img, threshold)
    }

    fn name(&self) -> &str {
        &self.model_name
    }
}

/// Preprocess image for Detectron2: resize to 800x1035, raw 0-255 pixels, CHW format (no batch dim).
fn preprocess_detectron2(img: &RgbImage) -> ndarray::Array3<f32> {
    let resized = image::imageops::resize(img, INPUT_WIDTH, INPUT_HEIGHT, image::imageops::FilterType::Triangle);
    let pixels = resized.as_raw();
    let hw = (INPUT_HEIGHT * INPUT_WIDTH) as usize;

    let mut data = vec![0.0f32; 3 * hw];
    for i in 0..hw {
        data[i] = pixels[i * 3] as f32; // R: 0-255 raw
        data[hw + i] = pixels[i * 3 + 1] as f32; // G: 0-255 raw
        data[2 * hw + i] = pixels[i * 3 + 2] as f32; // B: 0-255 raw
    }

    Array::from_shape_vec((3, INPUT_HEIGHT as usize, INPUT_WIDTH as usize), data)
        .expect("shape mismatch in preprocess_detectron2")
}
