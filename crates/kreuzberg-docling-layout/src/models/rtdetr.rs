use image::RgbImage;
use ndarray::Array;
use ort::{inputs, session::Session, value::Tensor};

use crate::error::LayoutError;
use crate::models::LayoutModel;
use crate::preprocessing;
use crate::types::{BBox, LayoutClass, LayoutDetection};

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
        let session = crate::session::build_session(path)?;
        let input_names: Vec<String> = session.inputs().iter().map(|i| i.name().to_string()).collect();
        Ok(Self { session, input_names })
    }

    /// Run inference and extract detections from raw outputs.
    fn run_inference(&mut self, img: &RgbImage, threshold: f32) -> Result<Vec<LayoutDetection>, LayoutError> {
        let orig_width = img.width();
        let orig_height = img.height();

        let input_tensor = preprocessing::preprocess_imagenet(img, INPUT_SIZE);
        let images_tensor = Tensor::from_array(input_tensor)?;

        let sizes = Array::from_shape_vec((1, 2), vec![orig_height as i64, orig_width as i64])
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

            // RT-DETR outputs boxes in original image coordinates directly.
            let x1 = boxes[i * 4];
            let y1 = boxes[i * 4 + 1];
            let x2 = boxes[i * 4 + 2];
            let y2 = boxes[i * 4 + 3];

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
