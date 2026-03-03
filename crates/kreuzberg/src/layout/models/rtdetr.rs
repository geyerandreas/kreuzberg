use image::RgbImage;
use ndarray::Array;
use ort::{inputs, session::Session, value::Tensor};

use crate::layout::error::LayoutError;
use crate::layout::models::LayoutModel;
use crate::layout::preprocessing;
use crate::layout::types::{BBox, LayoutClass, LayoutDetection};

/// Default confidence threshold for RT-DETR detections.
const DEFAULT_THRESHOLD: f32 = 0.3;

/// RT-DETR input resolution.
const INPUT_SIZE: u32 = 640;

/// Docling RT-DETR v2 layout detection model.
///
/// This model is NMS-free (transformer-based end-to-end detection).
///
/// Input tensors:
///   - `images`:            f32 [batch, 3, 640, 640]  (preprocessed pixel data)
///   - `orig_target_sizes`: i64 [batch, 2]            ([height, width] of original image)
///
/// Output tensors:
///   - `labels`: i64 [batch, num_queries]   (class IDs, 0-16)
///   - `boxes`:  f32 [batch, num_queries, 4] (bounding boxes in original image coordinates)
///   - `scores`: f32 [batch, num_queries]   (confidence scores)
pub struct RtDetrModel {
    session: Session,
    input_names: Vec<String>,
}

impl RtDetrModel {
    /// Load a Docling RT-DETR ONNX model from a file.
    pub fn from_file(path: &str) -> Result<Self, LayoutError> {
        let session = crate::layout::session::build_session(path)?;
        let input_names: Vec<String> = session.inputs().iter().map(|i| i.name().to_string()).collect();
        Ok(Self { session, input_names })
    }

    /// Run inference and extract detections from raw outputs.
    ///
    /// Uses aspect-preserving letterbox preprocessing (Lanczos3) to avoid
    /// distorting the page geometry. The model sees a properly proportioned
    /// image, which produces more accurate bounding box coordinates.
    fn run_inference(&mut self, img: &RgbImage, threshold: f32) -> Result<Vec<LayoutDetection>, LayoutError> {
        let orig_width = img.width();
        let orig_height = img.height();

        // Letterbox preprocessing: resize preserving aspect ratio, pad to 640×640.
        let (input_tensor, scale, pad_x, pad_y) = preprocessing::preprocess_imagenet_letterbox(img, INPUT_SIZE);
        let images_tensor = Tensor::from_array(input_tensor)?;

        // Tell the model the "original" size is 640×640 (the letterboxed size).
        // The model maps output boxes to this coordinate space; we un-letterbox below.
        let sizes = Array::from_shape_vec((1, 2), vec![INPUT_SIZE as i64, INPUT_SIZE as i64])
            .map_err(|e| LayoutError::InvalidOutput(format!("Failed to create sizes tensor: {e}")))?;
        let sizes_tensor = Tensor::from_array(sizes)?;

        let outputs = self.session.run(inputs![
            self.input_names[0].clone() => images_tensor,
            self.input_names[1].clone() => sizes_tensor
        ])?;

        // Extract output tensors: try i64 labels first, then f32 boxes/scores.
        let mut float_data: Vec<Vec<f32>> = Vec::new();
        let mut float_shapes: Vec<Vec<usize>> = Vec::new();
        let mut label_data: Vec<i64> = Vec::new();

        for (_name, value) in outputs.iter() {
            if let Ok(view) = value.try_extract_tensor::<i64>() {
                label_data = view.1.to_vec();
                continue;
            }
            if let Ok(view) = value.try_extract_tensor::<f32>() {
                let shape: Vec<usize> = view.0.iter().map(|&d| d as usize).collect();
                let data: Vec<f32> = view.1.to_vec();
                float_shapes.push(shape);
                float_data.push(data);
            }
        }

        // If labels came as f32 instead of i64, convert the last float output.
        if label_data.is_empty() && float_data.len() >= 3 {
            label_data = float_data.last().unwrap().iter().map(|&v| v as i64).collect();
            float_data.pop();
            float_shapes.pop();
        }

        if float_data.len() < 2 {
            return Err(LayoutError::InvalidOutput(format!(
                "Expected at least 2 float output tensors, got {}",
                float_data.len()
            )));
        }

        let boxes = &float_data[0];
        let scores = &float_data[1];
        let box_shape = &float_shapes[0];
        let num_detections = if box_shape.len() == 3 {
            box_shape[1]
        } else {
            box_shape[0]
        };

        // Un-letterbox: map from padded 640×640 space → original image coordinates.
        let inv_scale = 1.0 / scale;
        let pad_x_f = pad_x as f32;
        let pad_y_f = pad_y as f32;

        let mut detections = Vec::new();
        for i in 0..num_detections {
            let score = scores[i];
            if score < threshold {
                continue;
            }

            let label_id = label_data[i];
            let class = match LayoutClass::from_docling_id(label_id) {
                Some(c) => c,
                None => continue,
            };

            // Boxes are in 640×640 letterboxed coordinates. Remove padding and rescale.
            let x1 = ((boxes[i * 4] - pad_x_f) * inv_scale).clamp(0.0, orig_width as f32);
            let y1 = ((boxes[i * 4 + 1] - pad_y_f) * inv_scale).clamp(0.0, orig_height as f32);
            let x2 = ((boxes[i * 4 + 2] - pad_x_f) * inv_scale).clamp(0.0, orig_width as f32);
            let y2 = ((boxes[i * 4 + 3] - pad_y_f) * inv_scale).clamp(0.0, orig_height as f32);

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

impl LayoutModel for RtDetrModel {
    fn detect(&mut self, img: &RgbImage) -> Result<Vec<LayoutDetection>, LayoutError> {
        self.run_inference(img, DEFAULT_THRESHOLD)
    }

    fn detect_with_threshold(&mut self, img: &RgbImage, threshold: f32) -> Result<Vec<LayoutDetection>, LayoutError> {
        self.run_inference(img, threshold)
    }

    fn name(&self) -> &str {
        "Docling RT-DETR v2"
    }
}
