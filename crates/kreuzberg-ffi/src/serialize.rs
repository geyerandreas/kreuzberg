//! Result serialization FFI functions.
//!
//! Provides C-compatible functions for serializing extraction results to
//! TOON and JSON formats. These functions accept a JSON string representation
//! of an `ExtractionResult`, deserialize it, and re-serialize to the target format.
//!
//! All string-returning functions return pointers to C strings that MUST be freed
//! with `kreuzberg_free_string()`.

use crate::ffi_panic_guard;
use crate::helpers::{clear_last_error, set_last_error};
use kreuzberg::types::ExtractionResult;
use std::ffi::{CStr, CString};
use std::os::raw::c_char;
use std::ptr;

/// Serialize an extraction result to TOON format.
///
/// Takes a JSON string representation of an `ExtractionResult`, deserializes it,
/// and re-serializes it to TOON wire format.
///
/// # Arguments
///
/// * `result_json` - Null-terminated C string containing the extraction result as JSON
///
/// # Returns
///
/// A heap-allocated C string containing the TOON representation, or NULL on error
/// (check `kreuzberg_last_error` for details).
///
/// The returned pointer MUST be freed with `kreuzberg_free_string()`.
///
/// # Safety
///
/// - `result_json` must be a valid null-terminated C string containing valid JSON
/// - `result_json` cannot be NULL
/// - The returned pointer (if non-NULL) must be freed with `kreuzberg_free_string`
///
/// # Example (C)
///
/// ```c
/// CExtractionResult* result = kreuzberg_extract_file_sync("document.pdf");
/// if (result != NULL && result->success) {
///     // Get the full result as JSON first (via metadata_json or custom serialization)
///     char* toon = kreuzberg_serialize_to_toon(result_json_str);
///     if (toon != NULL) {
///         printf("TOON: %s\n", toon);
///         kreuzberg_free_string(toon);
///     }
/// }
/// ```
#[unsafe(no_mangle)]
pub unsafe extern "C" fn kreuzberg_serialize_to_toon(result_json: *const c_char) -> *mut c_char {
    ffi_panic_guard!("kreuzberg_serialize_to_toon", {
        if result_json.is_null() {
            set_last_error("result_json cannot be NULL".to_string());
            return ptr::null_mut();
        }

        clear_last_error();

        let json_str = match unsafe { CStr::from_ptr(result_json) }.to_str() {
            Ok(s) => s,
            Err(e) => {
                set_last_error(format!("Invalid UTF-8 in result JSON: {}", e));
                return ptr::null_mut();
            }
        };

        let result: ExtractionResult = match serde_json::from_str(json_str) {
            Ok(r) => r,
            Err(e) => {
                set_last_error(format!("Failed to parse result JSON: {}", e));
                return ptr::null_mut();
            }
        };

        let toon_str = match serde_toon::to_string(&result) {
            Ok(s) => s,
            Err(e) => {
                set_last_error(format!("Failed to serialize result to TOON: {}", e));
                return ptr::null_mut();
            }
        };

        match CString::new(toon_str) {
            Ok(c_string) => c_string.into_raw(),
            Err(e) => {
                set_last_error(format!("Failed to convert TOON string to C string: {}", e));
                ptr::null_mut()
            }
        }
    })
}

/// Serialize an extraction result to pretty-printed JSON format.
///
/// Takes a JSON string representation of an `ExtractionResult`, deserializes it,
/// and re-serializes it to pretty-printed JSON.
///
/// This is useful for normalizing JSON output or converting compact JSON to a
/// human-readable format.
///
/// # Arguments
///
/// * `result_json` - Null-terminated C string containing the extraction result as JSON
///
/// # Returns
///
/// A heap-allocated C string containing the pretty-printed JSON representation,
/// or NULL on error (check `kreuzberg_last_error` for details).
///
/// The returned pointer MUST be freed with `kreuzberg_free_string()`.
///
/// # Safety
///
/// - `result_json` must be a valid null-terminated C string containing valid JSON
/// - `result_json` cannot be NULL
/// - The returned pointer (if non-NULL) must be freed with `kreuzberg_free_string`
///
/// # Example (C)
///
/// ```c
/// char* pretty = kreuzberg_serialize_to_json(compact_json_str);
/// if (pretty != NULL) {
///     printf("JSON:\n%s\n", pretty);
///     kreuzberg_free_string(pretty);
/// }
/// ```
#[unsafe(no_mangle)]
pub unsafe extern "C" fn kreuzberg_serialize_to_json(result_json: *const c_char) -> *mut c_char {
    ffi_panic_guard!("kreuzberg_serialize_to_json", {
        if result_json.is_null() {
            set_last_error("result_json cannot be NULL".to_string());
            return ptr::null_mut();
        }

        clear_last_error();

        let json_str = match unsafe { CStr::from_ptr(result_json) }.to_str() {
            Ok(s) => s,
            Err(e) => {
                set_last_error(format!("Invalid UTF-8 in result JSON: {}", e));
                return ptr::null_mut();
            }
        };

        let result: ExtractionResult = match serde_json::from_str(json_str) {
            Ok(r) => r,
            Err(e) => {
                set_last_error(format!("Failed to parse result JSON: {}", e));
                return ptr::null_mut();
            }
        };

        let pretty_json = match serde_json::to_string_pretty(&result) {
            Ok(s) => s,
            Err(e) => {
                set_last_error(format!("Failed to serialize result to JSON: {}", e));
                return ptr::null_mut();
            }
        };

        match CString::new(pretty_json) {
            Ok(c_string) => c_string.into_raw(),
            Err(e) => {
                set_last_error(format!("Failed to convert JSON string to C string: {}", e));
                ptr::null_mut()
            }
        }
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::ffi::CStr;

    fn sample_result_json() -> CString {
        CString::new(
            r#"{"content":"Hello world","mime_type":"text/plain","metadata":{},"tables":[],"processing_warnings":[]}"#,
        )
        .expect("valid CString")
    }

    #[test]
    fn test_serialize_to_toon_success() {
        let json = sample_result_json();
        let result = unsafe { kreuzberg_serialize_to_toon(json.as_ptr()) };
        assert!(!result.is_null(), "TOON serialization should succeed");

        let toon_str = unsafe { CStr::from_ptr(result).to_str().unwrap() };
        assert!(
            toon_str.contains("Hello world"),
            "TOON output should contain the content"
        );

        unsafe {
            crate::kreuzberg_free_string(result);
        }
    }

    #[test]
    fn test_serialize_to_toon_null_input() {
        let result = unsafe { kreuzberg_serialize_to_toon(ptr::null()) };
        assert!(result.is_null(), "NULL input should return NULL");
    }

    #[test]
    fn test_serialize_to_toon_invalid_json() {
        let invalid = CString::new("not valid json").expect("valid CString");
        let result = unsafe { kreuzberg_serialize_to_toon(invalid.as_ptr()) };
        assert!(result.is_null(), "Invalid JSON should return NULL");
    }

    #[test]
    fn test_serialize_to_json_success() {
        let json = sample_result_json();
        let result = unsafe { kreuzberg_serialize_to_json(json.as_ptr()) };
        assert!(!result.is_null(), "JSON serialization should succeed");

        let json_str = unsafe { CStr::from_ptr(result).to_str().unwrap() };
        assert!(
            json_str.contains("Hello world"),
            "JSON output should contain the content"
        );
        // Pretty-printed JSON should have newlines
        assert!(json_str.contains('\n'), "Pretty-printed JSON should contain newlines");

        unsafe {
            crate::kreuzberg_free_string(result);
        }
    }

    #[test]
    fn test_serialize_to_json_null_input() {
        let result = unsafe { kreuzberg_serialize_to_json(ptr::null()) };
        assert!(result.is_null(), "NULL input should return NULL");
    }

    #[test]
    fn test_serialize_to_json_invalid_json() {
        let invalid = CString::new("not valid json").expect("valid CString");
        let result = unsafe { kreuzberg_serialize_to_json(invalid.as_ptr()) };
        assert!(result.is_null(), "Invalid JSON should return NULL");
    }

    #[test]
    fn test_serialize_roundtrip() {
        let json = sample_result_json();

        // Serialize to JSON, then back
        let pretty = unsafe { kreuzberg_serialize_to_json(json.as_ptr()) };
        assert!(!pretty.is_null());

        // The pretty JSON should also be valid input for TOON serialization
        let toon = unsafe { kreuzberg_serialize_to_toon(pretty) };
        assert!(!toon.is_null(), "Pretty JSON should be valid input for TOON");

        unsafe {
            crate::kreuzberg_free_string(pretty);
            crate::kreuzberg_free_string(toon);
        }
    }
}
