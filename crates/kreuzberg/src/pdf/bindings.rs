use super::error::PdfError;
use pdfium_render::prelude::*;

pub(crate) fn bind_pdfium(
    map_err: fn(String) -> PdfError,
    context: &'static str,
) -> Result<Box<dyn PdfiumLibraryBindings>, PdfError> {
    #[cfg(all(feature = "pdf", feature = "bundled-pdfium"))]
    {
        // WASM target: use dynamic binding to WASM module
        // SAFETY: pdfium-render handles WASM module lifecycle internally.
        // For WASM builds, the PDFium library is linked at compile time
        // and the WASM runtime manages initialization.
        #[cfg(target_arch = "wasm32")]
        {
            Pdfium::bind_to_system_library()
                .map_err(|e| map_err(format!("Failed to initialize Pdfium for WASM ({}): {}", context, e)))
        }

        // Non-WASM targets: extract and link dynamically
        #[cfg(not(target_arch = "wasm32"))]
        {
            let lib_path = crate::pdf::extract_bundled_pdfium()
                .map_err(|e| map_err(format!("Failed to extract bundled Pdfium ({}): {}", context, e)))?;

            let lib_dir = lib_path.parent().ok_or_else(|| {
                map_err(format!(
                    "Failed to determine Pdfium extraction directory for '{}' ({})",
                    lib_path.display(),
                    context
                ))
            })?;

            Pdfium::bind_to_library(Pdfium::pdfium_platform_library_name_at_path(lib_dir))
                .map_err(|e| map_err(format!("Failed to initialize Pdfium ({}): {}", context, e)))
        }
    }

    #[cfg(all(feature = "pdf", not(feature = "bundled-pdfium")))]
    {
        Pdfium::bind_to_system_library()
            .map_err(|e| map_err(format!("Failed to initialize Pdfium ({}): {}", context, e)))
    }
}
