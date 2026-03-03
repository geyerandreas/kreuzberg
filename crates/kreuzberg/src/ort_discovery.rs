//! ONNX Runtime library auto-discovery.
//!
//! Delegates to the shared implementation in the `layout` module when the
//! `layout-detection` feature is enabled. Otherwise falls back to a local
//! implementation with the same logic.

/// Ensure ONNX Runtime is discoverable. Safe to call multiple times (no-op after first).
#[cfg(feature = "layout-detection")]
pub fn ensure_ort_available() {
    crate::layout::ort_discovery::ensure_ort_available();
}

#[cfg(not(feature = "layout-detection"))]
pub fn ensure_ort_available() {
    use std::sync::Once;
    static ORT_INIT: Once = Once::new();

    ORT_INIT.call_once(|| {
        if let Err(msg) = try_discover_ort() {
            tracing::warn!("ONNX Runtime not found: {msg}");
        }
    });
}

#[cfg(not(feature = "layout-detection"))]
fn try_discover_ort() -> Result<(), &'static str> {
    // Already set and valid?
    if let Ok(path) = std::env::var("ORT_DYLIB_PATH")
        && std::path::Path::new(&path).exists()
    {
        return Ok(());
    }

    let candidates: &[&str] = platform_candidates();

    for path in candidates {
        if std::path::Path::new(path).exists() {
            // SAFETY: single-threaded inside Once::call_once
            #[allow(unsafe_code)]
            unsafe {
                std::env::set_var("ORT_DYLIB_PATH", path);
            }
            tracing::debug!("Auto-discovered ONNX Runtime at {path}");
            return Ok(());
        }
    }

    Err("ONNX Runtime library not found in common installation paths")
}

#[cfg(all(not(feature = "layout-detection"), target_os = "macos"))]
fn platform_candidates() -> &'static [&'static str] {
    &[
        "/opt/homebrew/lib/libonnxruntime.dylib",
        "/usr/local/lib/libonnxruntime.dylib",
    ]
}

#[cfg(all(not(feature = "layout-detection"), target_os = "linux"))]
fn platform_candidates() -> &'static [&'static str] {
    &[
        "/usr/lib/libonnxruntime.so",
        "/usr/local/lib/libonnxruntime.so",
        "/usr/lib/x86_64-linux-gnu/libonnxruntime.so",
        "/usr/lib/aarch64-linux-gnu/libonnxruntime.so",
    ]
}

#[cfg(all(not(feature = "layout-detection"), target_os = "windows"))]
fn platform_candidates() -> &'static [&'static str] {
    &[
        "C:\\Program Files\\onnxruntime\\bin\\onnxruntime.dll",
        "C:\\Windows\\System32\\onnxruntime.dll",
    ]
}

#[cfg(all(
    not(feature = "layout-detection"),
    not(any(target_os = "macos", target_os = "linux", target_os = "windows"))
))]
fn platform_candidates() -> &'static [&'static str] {
    &[]
}
