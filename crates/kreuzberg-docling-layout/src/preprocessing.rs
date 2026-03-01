use image::RgbImage;
use ndarray::Array4;

/// ImageNet normalization constants.
const IMAGENET_MEAN: [f32; 3] = [0.485, 0.456, 0.406];
const IMAGENET_STD: [f32; 3] = [0.229, 0.224, 0.225];

/// Preprocess an image for models using ImageNet normalization (e.g., RT-DETR).
///
/// Pipeline: resize to target_size x target_size (bilinear) -> rescale /255 -> ImageNet normalize -> NCHW f32.
///
/// Uses a single vectorized pass over contiguous pixel data for maximum throughput.
pub fn preprocess_imagenet(img: &RgbImage, target_size: u32) -> Array4<f32> {
    let resized = image::imageops::resize(img, target_size, target_size, image::imageops::FilterType::Triangle);
    let pixels = resized.as_raw();
    let hw = (target_size * target_size) as usize;

    // Pre-compute reciprocals to avoid repeated division.
    let inv_std_r = 1.0 / IMAGENET_STD[0];
    let inv_std_g = 1.0 / IMAGENET_STD[1];
    let inv_std_b = 1.0 / IMAGENET_STD[2];

    // Allocate contiguous NCHW buffer: [R plane | G plane | B plane].
    let mut data = vec![0.0f32; 3 * hw];

    for i in 0..hw {
        let r = pixels[i * 3] as f32 * (1.0 / 255.0);
        let g = pixels[i * 3 + 1] as f32 * (1.0 / 255.0);
        let b = pixels[i * 3 + 2] as f32 * (1.0 / 255.0);
        data[i] = (r - IMAGENET_MEAN[0]) * inv_std_r;
        data[hw + i] = (g - IMAGENET_MEAN[1]) * inv_std_g;
        data[2 * hw + i] = (b - IMAGENET_MEAN[2]) * inv_std_b;
    }

    Array4::from_shape_vec((1, 3, target_size as usize, target_size as usize), data)
        .expect("shape mismatch in preprocess_imagenet")
}

/// Preprocess with rescale only (no ImageNet normalization).
///
/// Pipeline: resize to target_size x target_size -> rescale /255 -> NCHW f32.
pub fn preprocess_rescale(img: &RgbImage, target_size: u32) -> Array4<f32> {
    let resized = image::imageops::resize(img, target_size, target_size, image::imageops::FilterType::Triangle);
    let pixels = resized.as_raw();
    let hw = (target_size * target_size) as usize;

    let mut data = vec![0.0f32; 3 * hw];
    for i in 0..hw {
        data[i] = pixels[i * 3] as f32 * (1.0 / 255.0);
        data[hw + i] = pixels[i * 3 + 1] as f32 * (1.0 / 255.0);
        data[2 * hw + i] = pixels[i * 3 + 2] as f32 * (1.0 / 255.0);
    }

    Array4::from_shape_vec((1, 3, target_size as usize, target_size as usize), data)
        .expect("shape mismatch in preprocess_rescale")
}

/// Letterbox preprocessing for YOLOX-style models.
///
/// Resizes the image to fit within (target_width x target_height) while maintaining
/// aspect ratio, padding the remaining area with value 114.0 (raw pixel value).
/// No normalization — values are 0-255 as YOLOX expects.
///
/// Returns the NCHW tensor and the scale ratio (for rescaling detections back).
pub fn preprocess_letterbox(img: &RgbImage, target_width: u32, target_height: u32) -> (Array4<f32>, f32) {
    let (orig_w, orig_h) = (img.width() as f32, img.height() as f32);
    let scale = (target_height as f32 / orig_h).min(target_width as f32 / orig_w);
    let new_w = (orig_w * scale) as u32;
    let new_h = (orig_h * scale) as u32;

    let resized = image::imageops::resize(img, new_w, new_h, image::imageops::FilterType::Triangle);

    let tw = target_width as usize;
    let th = target_height as usize;
    let hw = th * tw;
    // Fill with padding value 114.0 (raw pixel value, no normalization).
    let mut data = vec![114.0f32; 3 * hw];

    let rw = new_w as usize;
    let rh = new_h as usize;
    let resized_pixels = resized.as_raw();

    for y in 0..rh {
        for x in 0..rw {
            let src_idx = (y * rw + x) * 3;
            let dst_idx = y * tw + x;
            data[dst_idx] = resized_pixels[src_idx] as f32;
            data[hw + dst_idx] = resized_pixels[src_idx + 1] as f32;
            data[2 * hw + dst_idx] = resized_pixels[src_idx + 2] as f32;
        }
    }

    let tensor = Array4::from_shape_vec((1, 3, th, tw), data).expect("shape mismatch in preprocess_letterbox");

    (tensor, scale)
}
