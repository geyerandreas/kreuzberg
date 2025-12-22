#![allow(clippy::too_many_lines)]

use e2e_rust::{assertions, resolve_document};
use kreuzberg::core::config::{ExtractionConfig, FontConfig, PdfConfig};
use std::path::PathBuf;
use tempfile::TempDir;

#[test]
fn test_font_config_default_enabled() {
    let document_path = resolve_document("pdfs/assembly_language_for_beginners_al4_b_en.pdf");
    if !document_path.exists() {
        println!(
            "Skipping font_config_default_enabled: missing document at {}",
            document_path.display()
        );
        return;
    }

    let font_config = FontConfig {
        enabled: true,
        custom_font_dirs: None,
    };

    let pdf_config = PdfConfig {
        extract_images: false,
        passwords: None,
        extract_metadata: true,
        font_config: Some(font_config),
    };

    let mut config = ExtractionConfig::default();
    config.pdf_options = Some(pdf_config);

    let result = match kreuzberg::extract_file_sync(&document_path, None, &config) {
        Err(err) => panic!("Extraction failed with font config enabled: {err:?}"),
        Ok(result) => result,
    };

    assertions::assert_expected_mime(&result, &["application/pdf"]);
    assertions::assert_min_content_length(&result, 100);
}

#[test]
fn test_font_config_disabled() {
    let document_path = resolve_document("pdfs/bayesian_data_analysis_third_edition_13th_feb_2020.pdf");
    if !document_path.exists() {
        println!(
            "Skipping font_config_disabled: missing document at {}",
            document_path.display()
        );
        return;
    }

    let font_config = FontConfig {
        enabled: false,
        custom_font_dirs: None,
    };

    let pdf_config = PdfConfig {
        extract_images: false,
        passwords: None,
        extract_metadata: true,
        font_config: Some(font_config),
    };

    let mut config = ExtractionConfig::default();
    config.pdf_options = Some(pdf_config);

    let result = match kreuzberg::extract_file_sync(&document_path, None, &config) {
        Err(err) => panic!("Extraction failed with font config disabled: {err:?}"),
        Ok(result) => result,
    };

    assertions::assert_expected_mime(&result, &["application/pdf"]);
    assertions::assert_min_content_length(&result, 100);
}

#[test]
fn test_font_config_with_custom_directory() {
    let document_path = resolve_document("pdfs/code_and_formula.pdf");
    if !document_path.exists() {
        println!(
            "Skipping font_config_with_custom_directory: missing document at {}",
            document_path.display()
        );
        return;
    }

    // Create temporary font directory
    let temp_dir = match TempDir::new() {
        Ok(dir) => dir,
        Err(e) => panic!("Failed to create temp directory: {e}"),
    };

    let font_config = FontConfig {
        enabled: true,
        custom_font_dirs: Some(vec![temp_dir.path().to_path_buf()]),
    };

    let pdf_config = PdfConfig {
        extract_images: false,
        passwords: None,
        extract_metadata: true,
        font_config: Some(font_config),
    };

    let mut config = ExtractionConfig::default();
    config.pdf_options = Some(pdf_config);

    let result = match kreuzberg::extract_file_sync(&document_path, None, &config) {
        Err(err) => panic!("Extraction failed with custom font directory: {err:?}"),
        Ok(result) => result,
    };

    assertions::assert_expected_mime(&result, &["application/pdf"]);
    assertions::assert_min_content_length(&result, 100);
}

#[test]
fn test_font_config_multiple_custom_directories() {
    let document_path = resolve_document("pdfs/fundamentals_of_deep_learning_2014.pdf");
    if !document_path.exists() {
        println!(
            "Skipping font_config_multiple_custom_directories: missing document at {}",
            document_path.display()
        );
        return;
    }

    // Create multiple temporary font directories
    let temp_dir1 = match TempDir::new() {
        Ok(dir) => dir,
        Err(e) => panic!("Failed to create temp directory 1: {e}"),
    };

    let temp_dir2 = match TempDir::new() {
        Ok(dir) => dir,
        Err(e) => panic!("Failed to create temp directory 2: {e}"),
    };

    let temp_dir3 = match TempDir::new() {
        Ok(dir) => dir,
        Err(e) => panic!("Failed to create temp directory 3: {e}"),
    };

    let font_config = FontConfig {
        enabled: true,
        custom_font_dirs: Some(vec![
            temp_dir1.path().to_path_buf(),
            temp_dir2.path().to_path_buf(),
            temp_dir3.path().to_path_buf(),
        ]),
    };

    let pdf_config = PdfConfig {
        extract_images: false,
        passwords: None,
        extract_metadata: true,
        font_config: Some(font_config),
    };

    let mut config = ExtractionConfig::default();
    config.pdf_options = Some(pdf_config);

    let result = match kreuzberg::extract_file_sync(&document_path, None, &config) {
        Err(err) => panic!("Extraction failed with multiple font directories: {err:?}"),
        Ok(result) => result,
    };

    assertions::assert_expected_mime(&result, &["application/pdf"]);
    assertions::assert_min_content_length(&result, 100);
}

#[test]
fn test_font_config_invalid_directory_graceful_handling() {
    let document_path = resolve_document("pdfs/assembly_language_for_beginners_al4_b_en.pdf");
    if !document_path.exists() {
        println!(
            "Skipping font_config_invalid_directory_graceful_handling: missing document at {}",
            document_path.display()
        );
        return;
    }

    let font_config = FontConfig {
        enabled: true,
        custom_font_dirs: Some(vec![
            PathBuf::from("/nonexistent/path/that/does/not/exist"),
            PathBuf::from("/another/invalid/directory/12345"),
        ]),
    };

    let pdf_config = PdfConfig {
        extract_images: false,
        passwords: None,
        extract_metadata: true,
        font_config: Some(font_config),
    };

    let mut config = ExtractionConfig::default();
    config.pdf_options = Some(pdf_config);

    // Should not fail even with invalid directories
    let result = match kreuzberg::extract_file_sync(&document_path, None, &config) {
        Err(err) => panic!("Extraction should not fail with invalid font directories: {err:?}"),
        Ok(result) => result,
    };

    assertions::assert_expected_mime(&result, &["application/pdf"]);
    assertions::assert_min_content_length(&result, 100);
}

#[test]
fn test_font_config_empty_directory_array() {
    let document_path = resolve_document("pdfs/bayesian_data_analysis_third_edition_13th_feb_2020.pdf");
    if !document_path.exists() {
        println!(
            "Skipping font_config_empty_directory_array: missing document at {}",
            document_path.display()
        );
        return;
    }

    let font_config = FontConfig {
        enabled: true,
        custom_font_dirs: Some(vec![]),
    };

    let pdf_config = PdfConfig {
        extract_images: false,
        passwords: None,
        extract_metadata: true,
        font_config: Some(font_config),
    };

    let mut config = ExtractionConfig::default();
    config.pdf_options = Some(pdf_config);

    let result = match kreuzberg::extract_file_sync(&document_path, None, &config) {
        Err(err) => panic!("Extraction failed with empty font directory array: {err:?}"),
        Ok(result) => result,
    };

    assertions::assert_expected_mime(&result, &["application/pdf"]);
    assertions::assert_min_content_length(&result, 100);
}

#[test]
fn test_font_config_none() {
    let document_path = resolve_document("pdfs/code_and_formula.pdf");
    if !document_path.exists() {
        println!(
            "Skipping font_config_none: missing document at {}",
            document_path.display()
        );
        return;
    }

    let pdf_config = PdfConfig {
        extract_images: false,
        passwords: None,
        extract_metadata: true,
        font_config: None,
    };

    let mut config = ExtractionConfig::default();
    config.pdf_options = Some(pdf_config);

    let result = match kreuzberg::extract_file_sync(&document_path, None, &config) {
        Err(err) => panic!("Extraction failed with no font config: {err:?}"),
        Ok(result) => result,
    };

    assertions::assert_expected_mime(&result, &["application/pdf"]);
    assertions::assert_min_content_length(&result, 100);
}

#[test]
fn test_font_config_with_metadata_extraction() {
    let document_path = resolve_document("pdfs/fundamentals_of_deep_learning_2014.pdf");
    if !document_path.exists() {
        println!(
            "Skipping font_config_with_metadata_extraction: missing document at {}",
            document_path.display()
        );
        return;
    }

    let temp_dir = match TempDir::new() {
        Ok(dir) => dir,
        Err(e) => panic!("Failed to create temp directory: {e}"),
    };

    let font_config = FontConfig {
        enabled: true,
        custom_font_dirs: Some(vec![temp_dir.path().to_path_buf()]),
    };

    let pdf_config = PdfConfig {
        extract_images: false,
        passwords: None,
        extract_metadata: true,
        font_config: Some(font_config),
    };

    let mut config = ExtractionConfig::default();
    config.pdf_options = Some(pdf_config);

    let result = match kreuzberg::extract_file_sync(&document_path, None, &config) {
        Err(err) => panic!("Extraction failed with metadata extraction enabled: {err:?}"),
        Ok(result) => result,
    };

    assertions::assert_expected_mime(&result, &["application/pdf"]);
    assertions::assert_min_content_length(&result, 100);

    // Metadata is always present as a struct, not Option
    let _ = result.metadata;
}
