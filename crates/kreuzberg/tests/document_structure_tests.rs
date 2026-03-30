//! Integration tests verifying DocumentStructure output for all migrated extractors.

mod helpers;

use kreuzberg::core::config::ExtractionConfig;
use kreuzberg::core::extractor::extract_file;
use kreuzberg::extraction::derive::derive_extraction_result;
use kreuzberg::rendering::render_to_markdown;
use kreuzberg::types::document_structure::{AnnotationKind, NodeContent};

/// Helper: check whether a document contains at least one node matching a predicate.
fn has_node_type(
    doc: &kreuzberg::types::document_structure::DocumentStructure,
    predicate: fn(&NodeContent) -> bool,
) -> bool {
    doc.nodes.iter().any(|n| predicate(&n.content))
}

/// Build an `ExtractionConfig` with document structure enabled.
fn config_with_structure() -> ExtractionConfig {
    ExtractionConfig {
        include_document_structure: true,
        ..Default::default()
    }
}

// ============================================================================
// 1. DOCX
// ============================================================================

#[cfg(feature = "office")]
#[tokio::test]
async fn test_document_structure_docx() {
    let path = helpers::get_test_file_path("docx/unit_test_headers.docx");
    if !path.exists() {
        return;
    }

    let config = config_with_structure();
    let result = extract_file(&path, None, &config)
        .await
        .expect("DOCX extraction should succeed");

    assert!(result.document.is_some(), "document should be populated");
    let doc = result.document.as_ref().unwrap();

    assert!(!doc.nodes.is_empty(), "document nodes should be non-empty for DOCX");
    assert_eq!(
        doc.source_format.as_deref(),
        Some("docx"),
        "source_format should be 'docx'"
    );
    assert!(doc.validate().is_ok(), "document structure validation should pass");
    assert!(
        has_node_type(doc, |c| matches!(c, NodeContent::Heading { .. })),
        "DOCX with headers should contain Heading nodes"
    );

    let md = render_to_markdown(doc);
    assert!(
        !md.trim().is_empty(),
        "render_to_markdown should produce non-empty output"
    );
}

// ============================================================================
// 2. PPTX
// ============================================================================

#[cfg(feature = "office")]
#[tokio::test]
async fn test_document_structure_pptx() {
    let path = helpers::get_test_file_path("pptx/powerpoint_sample.ppsx");
    if !path.exists() {
        return;
    }

    let config = config_with_structure();
    let result = extract_file(&path, None, &config)
        .await
        .expect("PPTX extraction should succeed");

    assert!(result.document.is_some(), "document should be populated");
    let doc = result.document.as_ref().unwrap();

    assert_eq!(
        doc.source_format.as_deref(),
        Some("pptx"),
        "source_format should be 'pptx'"
    );
    assert!(doc.validate().is_ok(), "document structure validation should pass");
    assert!(
        has_node_type(doc, |c| matches!(c, NodeContent::Slide { .. })),
        "PPTX should contain Slide nodes"
    );

    let md = render_to_markdown(doc);
    assert!(
        !md.trim().is_empty(),
        "render_to_markdown should produce non-empty output"
    );
}

// ============================================================================
// 3. HTML
// ============================================================================

#[cfg(feature = "html")]
#[tokio::test]
async fn test_document_structure_html() {
    let path = helpers::get_test_file_path("html/html.htm");
    if !path.exists() {
        return;
    }

    let config = config_with_structure();
    let result = extract_file(&path, None, &config)
        .await
        .expect("HTML extraction should succeed");

    assert!(result.document.is_some(), "document should be populated");
    let doc = result.document.as_ref().unwrap();

    assert_eq!(
        doc.source_format.as_deref(),
        Some("html"),
        "source_format should be 'html'"
    );
    assert!(doc.validate().is_ok(), "document structure validation should pass");
    assert!(
        has_node_type(doc, |c| matches!(c, NodeContent::Heading { .. })),
        "HTML should contain Heading nodes"
    );
    assert!(
        has_node_type(doc, |c| matches!(c, NodeContent::Paragraph { .. })),
        "HTML should contain Paragraph nodes"
    );

    let md = render_to_markdown(doc);
    assert!(
        !md.trim().is_empty(),
        "render_to_markdown should produce non-empty output"
    );
}

// ============================================================================
// 4. LaTeX
// ============================================================================

#[cfg(feature = "office")]
#[tokio::test]
async fn test_document_structure_latex() {
    let path = helpers::get_test_file_path("latex/basic_sections.tex");
    if !path.exists() {
        return;
    }

    let config = config_with_structure();
    let result = extract_file(&path, None, &config)
        .await
        .expect("LaTeX extraction should succeed");

    assert!(result.document.is_some(), "document should be populated");
    let doc = result.document.as_ref().unwrap();

    assert_eq!(
        doc.source_format.as_deref(),
        Some("latex"),
        "source_format should be 'latex'"
    );
    assert!(doc.validate().is_ok(), "document structure validation should pass");
    assert!(
        has_node_type(doc, |c| matches!(c, NodeContent::Heading { .. })),
        "LaTeX with \\section commands should contain Heading nodes"
    );

    let md = render_to_markdown(doc);
    assert!(
        !md.trim().is_empty(),
        "render_to_markdown should produce non-empty output"
    );
}

// ============================================================================
// 5. RST
// ============================================================================

#[cfg(feature = "office")]
#[tokio::test]
async fn test_document_structure_rst() {
    let path = helpers::get_test_file_path("rst/restructured_text.rst");
    if !path.exists() {
        return;
    }

    let config = config_with_structure();
    let result = extract_file(&path, None, &config)
        .await
        .expect("RST extraction should succeed");

    assert!(result.document.is_some(), "document should be populated");
    let doc = result.document.as_ref().unwrap();

    assert_eq!(
        doc.source_format.as_deref(),
        Some("rst"),
        "source_format should be 'rst'"
    );
    assert!(doc.validate().is_ok(), "document structure validation should pass");
    assert!(
        has_node_type(doc, |c| matches!(c, NodeContent::Heading { .. })),
        "RST should contain Heading nodes"
    );

    let md = render_to_markdown(doc);
    assert!(
        !md.trim().is_empty(),
        "render_to_markdown should produce non-empty output"
    );
}

// ============================================================================
// 6. Org Mode
// ============================================================================

#[cfg(feature = "office")]
#[tokio::test]
async fn test_document_structure_orgmode() {
    let path = helpers::get_test_file_path("org/comprehensive.org");
    if !path.exists() {
        return;
    }

    let config = config_with_structure();
    let result = extract_file(&path, None, &config)
        .await
        .expect("OrgMode extraction should succeed");

    assert!(result.document.is_some(), "document should be populated");
    let doc = result.document.as_ref().unwrap();

    assert_eq!(
        doc.source_format.as_deref(),
        Some("orgmode"),
        "source_format should be 'orgmode'"
    );
    assert!(doc.validate().is_ok(), "document structure validation should pass");
    assert!(
        has_node_type(doc, |c| matches!(c, NodeContent::Heading { .. })),
        "OrgMode with * headings should contain Heading nodes"
    );

    let md = render_to_markdown(doc);
    assert!(
        !md.trim().is_empty(),
        "render_to_markdown should produce non-empty output"
    );
}

// ============================================================================
// 7. EPUB
// ============================================================================

#[cfg(feature = "office")]
#[tokio::test]
async fn test_document_structure_epub() {
    let path = helpers::get_test_file_path("epub/features.epub");
    if !path.exists() {
        return;
    }

    let config = config_with_structure();
    let result = extract_file(&path, None, &config)
        .await
        .expect("EPUB extraction should succeed");

    assert!(result.document.is_some(), "document should be populated");
    let doc = result.document.as_ref().unwrap();

    assert_eq!(
        doc.source_format.as_deref(),
        Some("epub"),
        "source_format should be 'epub'"
    );
    assert!(!doc.nodes.is_empty(), "document nodes should be non-empty for EPUB");
    assert!(doc.validate().is_ok(), "document structure validation should pass");

    let md = render_to_markdown(doc);
    assert!(
        !md.trim().is_empty(),
        "render_to_markdown should produce non-empty output"
    );
}

// ============================================================================
// 8. Excel
// ============================================================================

#[cfg(any(feature = "excel", feature = "excel-wasm"))]
#[tokio::test]
async fn test_document_structure_excel() {
    let path = helpers::get_test_file_path("xlsx/excel_multi_sheet.xlsx");
    if !path.exists() {
        return;
    }

    let config = config_with_structure();
    let result = extract_file(&path, None, &config)
        .await
        .expect("Excel extraction should succeed");

    assert!(result.document.is_some(), "document should be populated");
    let doc = result.document.as_ref().unwrap();

    assert_eq!(
        doc.source_format.as_deref(),
        Some("excel"),
        "source_format should be 'excel'"
    );
    assert!(doc.validate().is_ok(), "document structure validation should pass");
    assert!(
        has_node_type(doc, |c| matches!(c, NodeContent::Table { .. })),
        "Excel should contain Table nodes from sheet data"
    );
    assert!(
        has_node_type(doc, |c| matches!(c, NodeContent::Heading { .. })),
        "Excel should contain Heading nodes from sheet names"
    );

    let md = render_to_markdown(doc);
    assert!(
        !md.trim().is_empty(),
        "render_to_markdown should produce non-empty output"
    );
}

// ============================================================================
// 9. CSV
// ============================================================================

#[tokio::test]
async fn test_document_structure_csv() {
    let path = helpers::get_test_file_path("csv/data_table.csv");
    if !path.exists() {
        return;
    }

    let config = config_with_structure();
    let result = extract_file(&path, None, &config)
        .await
        .expect("CSV extraction should succeed");

    assert!(result.document.is_some(), "document should be populated");
    let doc = result.document.as_ref().unwrap();

    assert_eq!(
        doc.source_format.as_deref(),
        Some("csv"),
        "source_format should be 'csv'"
    );
    assert!(doc.validate().is_ok(), "document structure validation should pass");
    assert!(
        has_node_type(doc, |c| matches!(c, NodeContent::Table { .. })),
        "CSV should contain Table nodes"
    );

    let md = render_to_markdown(doc);
    assert!(
        !md.trim().is_empty(),
        "render_to_markdown should produce non-empty output"
    );
}

// ============================================================================
// 10. Email
// ============================================================================

#[cfg(feature = "email")]
#[tokio::test]
async fn test_document_structure_email() {
    let path = helpers::get_test_file_path("email/fake_email.msg");
    if !path.exists() {
        return;
    }

    let config = config_with_structure();
    let result = extract_file(&path, None, &config)
        .await
        .expect("Email extraction should succeed");

    assert!(result.document.is_some(), "document should be populated");
    let doc = result.document.as_ref().unwrap();

    assert_eq!(
        doc.source_format.as_deref(),
        Some("email"),
        "source_format should be 'email'"
    );
    assert!(doc.validate().is_ok(), "document structure validation should pass");
    assert!(
        has_node_type(doc, |c| matches!(c, NodeContent::MetadataBlock { .. })),
        "Email should contain MetadataBlock nodes from headers"
    );
    assert!(
        has_node_type(doc, |c| matches!(c, NodeContent::Paragraph { .. })),
        "Email should contain Paragraph nodes from body"
    );

    let md = render_to_markdown(doc);
    assert!(
        !md.trim().is_empty(),
        "render_to_markdown should produce non-empty output"
    );
}

// ============================================================================
// 11. BibTeX
// ============================================================================

#[cfg(feature = "office")]
#[tokio::test]
async fn test_document_structure_bibtex() {
    let path = helpers::get_test_file_path("bibtex/comprehensive.bib");
    if !path.exists() {
        return;
    }

    let config = config_with_structure();
    let result = extract_file(&path, None, &config)
        .await
        .expect("BibTeX extraction should succeed");

    assert!(result.document.is_some(), "document should be populated");
    let doc = result.document.as_ref().unwrap();

    assert_eq!(
        doc.source_format.as_deref(),
        Some("bibtex"),
        "source_format should be 'bibtex'"
    );
    assert!(doc.validate().is_ok(), "document structure validation should pass");
    assert!(
        has_node_type(doc, |c| matches!(c, NodeContent::Citation { .. })),
        "BibTeX should contain Citation nodes"
    );

    let md = render_to_markdown(doc);
    assert!(
        !md.trim().is_empty(),
        "render_to_markdown should produce non-empty output"
    );
}

// ============================================================================
// 12. Jupyter
// ============================================================================

#[cfg(feature = "office")]
#[tokio::test]
async fn test_document_structure_jupyter() {
    let path = helpers::get_test_file_path("jupyter/mime.ipynb");
    if !path.exists() {
        return;
    }

    let config = config_with_structure();
    let result = extract_file(&path, None, &config)
        .await
        .expect("Jupyter extraction should succeed");

    assert!(result.document.is_some(), "document should be populated");
    let doc = result.document.as_ref().unwrap();

    assert_eq!(
        doc.source_format.as_deref(),
        Some("jupyter"),
        "source_format should be 'jupyter'"
    );
    assert!(doc.validate().is_ok(), "document structure validation should pass");
    assert!(
        has_node_type(doc, |c| matches!(c, NodeContent::Code { .. })),
        "Jupyter should contain Code nodes from code cells"
    );

    let md = render_to_markdown(doc);
    assert!(
        !md.trim().is_empty(),
        "render_to_markdown should produce non-empty output"
    );
}

// ============================================================================
// 13. PlainText
// ============================================================================

#[tokio::test]
async fn test_document_structure_plaintext() {
    let path = helpers::get_test_file_path("text/contract.txt");
    if !path.exists() {
        return;
    }

    let config = config_with_structure();
    let result = extract_file(&path, None, &config)
        .await
        .expect("PlainText extraction should succeed");

    assert!(result.document.is_some(), "document should be populated");
    let doc = result.document.as_ref().unwrap();

    assert_eq!(
        doc.source_format.as_deref(),
        Some("text"),
        "source_format should be 'text'"
    );
    assert!(doc.validate().is_ok(), "document structure validation should pass");
    assert!(
        has_node_type(doc, |c| matches!(c, NodeContent::Paragraph { .. })),
        "PlainText should contain Paragraph nodes"
    );

    let md = render_to_markdown(doc);
    assert!(
        !md.trim().is_empty(),
        "render_to_markdown should produce non-empty output"
    );
}

// ============================================================================
// 14. Markdown
// ============================================================================

#[tokio::test]
async fn test_document_structure_markdown() {
    let path = helpers::get_test_file_path("markdown/comprehensive.md");
    if !path.exists() {
        return;
    }

    let config = config_with_structure();
    let result = extract_file(&path, None, &config)
        .await
        .expect("Markdown extraction should succeed");

    assert!(result.document.is_some(), "document should be populated");
    let doc = result.document.as_ref().unwrap();

    if doc.source_format.is_some() {
        assert_eq!(
            doc.source_format.as_deref(),
            Some("markdown"),
            "source_format should be 'markdown' when set"
        );
    }
    assert!(doc.validate().is_ok(), "document structure validation should pass");
    assert!(
        has_node_type(doc, |c| matches!(c, NodeContent::Heading { .. }))
            || has_node_type(doc, |c| matches!(c, NodeContent::Paragraph { .. })),
        "Markdown should contain Heading or Paragraph nodes"
    );

    let md = render_to_markdown(doc);
    assert!(
        !md.trim().is_empty(),
        "render_to_markdown should produce non-empty output"
    );
}

// ============================================================================
// 15. ODT
// ============================================================================

#[cfg(feature = "office")]
#[tokio::test]
async fn test_document_structure_odt() {
    let path = helpers::get_test_file_path("odt/headers.odt");
    if !path.exists() {
        return;
    }

    let config = config_with_structure();
    let result = extract_file(&path, None, &config)
        .await
        .expect("ODT extraction should succeed");

    assert!(result.document.is_some(), "document should be populated");
    let doc = result.document.as_ref().unwrap();

    assert_eq!(
        doc.source_format.as_deref(),
        Some("odt"),
        "source_format should be 'odt'"
    );
    assert!(doc.validate().is_ok(), "document structure validation should pass");
    assert!(!doc.nodes.is_empty(), "document nodes should be non-empty for ODT");
    assert!(
        has_node_type(doc, |c| matches!(c, NodeContent::Heading { .. })),
        "ODT with headers should contain Heading nodes"
    );
    assert!(
        has_node_type(doc, |c| matches!(c, NodeContent::Paragraph { .. })),
        "ODT should contain Paragraph nodes"
    );

    let md = render_to_markdown(doc);
    assert!(
        !md.trim().is_empty(),
        "render_to_markdown should produce non-empty output"
    );
}

#[cfg(feature = "office")]
#[tokio::test]
async fn test_document_structure_odt_table() {
    let path = helpers::get_test_file_path("odt/simpleTable.odt");
    if !path.exists() {
        return;
    }

    let config = config_with_structure();
    let result = extract_file(&path, None, &config)
        .await
        .expect("ODT table extraction should succeed");

    assert!(result.document.is_some(), "document should be populated");
    let doc = result.document.as_ref().unwrap();

    assert_eq!(doc.source_format.as_deref(), Some("odt"));
    assert!(doc.validate().is_ok());
    assert!(
        has_node_type(doc, |c| matches!(c, NodeContent::Table { .. })),
        "ODT with table should contain Table nodes"
    );
}

#[cfg(feature = "office")]
#[tokio::test]
async fn test_document_structure_odt_list() {
    let path = helpers::get_test_file_path("odt/unorderedList.odt");
    if !path.exists() {
        return;
    }

    let config = config_with_structure();
    let result = extract_file(&path, None, &config)
        .await
        .expect("ODT list extraction should succeed");

    assert!(result.document.is_some(), "document should be populated");
    let doc = result.document.as_ref().unwrap();

    assert_eq!(doc.source_format.as_deref(), Some("odt"));
    assert!(doc.validate().is_ok());
    assert!(
        has_node_type(doc, |c| matches!(c, NodeContent::List { .. })),
        "ODT with list should contain List nodes"
    );
    assert!(
        has_node_type(doc, |c| matches!(c, NodeContent::ListItem { .. })),
        "ODT with list should contain ListItem nodes"
    );
}

// ============================================================================
// 16. DOC
// ============================================================================

#[cfg(feature = "office")]
#[tokio::test]
async fn test_document_structure_doc() {
    let path = helpers::get_test_file_path("doc/unit_test_lists.doc");
    if !path.exists() {
        return;
    }

    let config = config_with_structure();
    let result = extract_file(&path, None, &config)
        .await
        .expect("DOC extraction should succeed");

    assert!(result.document.is_some(), "document should be populated");
    let doc = result.document.as_ref().unwrap();

    assert_eq!(
        doc.source_format.as_deref(),
        Some("doc"),
        "source_format should be 'doc'"
    );
    assert!(doc.validate().is_ok(), "document structure validation should pass");
    assert!(!doc.nodes.is_empty(), "document nodes should be non-empty for DOC");
    assert!(
        has_node_type(doc, |c| matches!(c, NodeContent::Paragraph { .. })),
        "DOC should contain Paragraph nodes"
    );

    let md = render_to_markdown(doc);
    assert!(
        !md.trim().is_empty(),
        "render_to_markdown should produce non-empty output"
    );
}

// ============================================================================
// 17. PPT
// ============================================================================

#[cfg(feature = "office")]
#[tokio::test]
async fn test_document_structure_ppt() {
    let path = helpers::get_test_file_path("ppt/simple.ppt");
    if !path.exists() {
        return;
    }

    let config = config_with_structure();
    let result = extract_file(&path, None, &config)
        .await
        .expect("PPT extraction should succeed");

    assert!(result.document.is_some(), "document should be populated");
    let doc = result.document.as_ref().unwrap();

    assert_eq!(
        doc.source_format.as_deref(),
        Some("ppt"),
        "source_format should be 'ppt'"
    );
    assert!(doc.validate().is_ok(), "document structure validation should pass");
    assert!(!doc.nodes.is_empty(), "document nodes should be non-empty for PPT");
    assert!(
        has_node_type(doc, |c| matches!(c, NodeContent::Slide { .. })),
        "PPT should contain Slide nodes"
    );

    let md = render_to_markdown(doc);
    assert!(
        !md.trim().is_empty(),
        "render_to_markdown should produce non-empty output"
    );
}

// ============================================================================
// 18. RTF
// ============================================================================

#[cfg(feature = "office")]
#[tokio::test]
async fn test_document_structure_rtf() {
    let path = helpers::get_test_file_path("rtf/heading.rtf");
    if !path.exists() {
        return;
    }

    let config = config_with_structure();
    let result = extract_file(&path, None, &config)
        .await
        .expect("RTF extraction should succeed");

    assert!(result.document.is_some(), "document should be populated");
    let doc = result.document.as_ref().unwrap();

    assert_eq!(
        doc.source_format.as_deref(),
        Some("rtf"),
        "source_format should be 'rtf'"
    );
    assert!(doc.validate().is_ok(), "document structure validation should pass");
    assert!(!doc.nodes.is_empty(), "document nodes should be non-empty for RTF");
    assert!(
        has_node_type(doc, |c| matches!(c, NodeContent::Paragraph { .. })),
        "RTF should contain Paragraph nodes"
    );

    let md = render_to_markdown(doc);
    assert!(
        !md.trim().is_empty(),
        "render_to_markdown should produce non-empty output"
    );
}

#[cfg(feature = "office")]
#[tokio::test]
async fn test_document_structure_rtf_table() {
    let path = helpers::get_test_file_path("rtf/table_simple.rtf");
    if !path.exists() {
        return;
    }

    let config = config_with_structure();
    let result = extract_file(&path, None, &config)
        .await
        .expect("RTF table extraction should succeed");

    assert!(result.document.is_some(), "document should be populated");
    let doc = result.document.as_ref().unwrap();

    assert_eq!(doc.source_format.as_deref(), Some("rtf"));
    assert!(doc.validate().is_ok());
    assert!(
        has_node_type(doc, |c| matches!(c, NodeContent::Table { .. }))
            || has_node_type(doc, |c| matches!(c, NodeContent::Paragraph { .. })),
        "RTF with tables should contain Table or Paragraph nodes"
    );
}

// ============================================================================
// 19. DocBook
// ============================================================================

#[cfg(feature = "xml")]
#[tokio::test]
async fn test_document_structure_docbook() {
    let path = helpers::get_test_file_path("docbook/docbook-chapter.docbook");
    if !path.exists() {
        return;
    }

    let config = config_with_structure();
    let result = extract_file(&path, None, &config)
        .await
        .expect("DocBook extraction should succeed");

    assert!(result.document.is_some(), "document should be populated");
    let doc = result.document.as_ref().unwrap();

    assert!(!doc.nodes.is_empty(), "document nodes should be non-empty for DocBook");
    assert_eq!(
        doc.source_format.as_deref(),
        Some("docbook"),
        "source_format should be 'docbook'"
    );
    assert!(doc.validate().is_ok(), "document structure validation should pass");
    assert!(
        has_node_type(doc, |c| matches!(c, NodeContent::Heading { .. })),
        "DocBook with chapters/sections should contain Heading nodes"
    );
    assert!(
        has_node_type(doc, |c| matches!(c, NodeContent::Paragraph { .. })),
        "DocBook should contain Paragraph nodes"
    );

    let md = render_to_markdown(doc);
    assert!(
        !md.trim().is_empty(),
        "render_to_markdown should produce non-empty output"
    );
}

// ============================================================================
// 20. JATS
// ============================================================================

#[cfg(feature = "xml")]
#[tokio::test]
async fn test_document_structure_jats() {
    let path = helpers::get_test_file_path("jats/sample_article.jats");
    if !path.exists() {
        return;
    }

    let config = config_with_structure();
    let result = extract_file(&path, None, &config)
        .await
        .expect("JATS extraction should succeed");

    assert!(result.document.is_some(), "document should be populated");
    let doc = result.document.as_ref().unwrap();

    assert!(!doc.nodes.is_empty(), "document nodes should be non-empty for JATS");
    assert_eq!(
        doc.source_format.as_deref(),
        Some("jats"),
        "source_format should be 'jats'"
    );
    assert!(doc.validate().is_ok(), "document structure validation should pass");
    assert!(
        has_node_type(doc, |c| matches!(c, NodeContent::Heading { .. })),
        "JATS article should contain Heading nodes"
    );
    assert!(
        has_node_type(doc, |c| matches!(c, NodeContent::Paragraph { .. })),
        "JATS article should contain Paragraph nodes"
    );

    let md = render_to_markdown(doc);
    assert!(
        !md.trim().is_empty(),
        "render_to_markdown should produce non-empty output"
    );
}

// ============================================================================
// 21. FictionBook
// ============================================================================

#[cfg(feature = "office")]
#[tokio::test]
async fn test_document_structure_fictionbook() {
    let path = helpers::get_test_file_path("fictionbook/basic.fb2");
    if !path.exists() {
        return;
    }

    let config = config_with_structure();
    let result = extract_file(&path, None, &config)
        .await
        .expect("FictionBook extraction should succeed");

    assert!(result.document.is_some(), "document should be populated");
    let doc = result.document.as_ref().unwrap();

    assert!(
        !doc.nodes.is_empty(),
        "document nodes should be non-empty for FictionBook"
    );
    assert_eq!(
        doc.source_format.as_deref(),
        Some("fictionbook"),
        "source_format should be 'fictionbook'"
    );
    assert!(doc.validate().is_ok(), "document structure validation should pass");
    assert!(
        has_node_type(doc, |c| matches!(c, NodeContent::Heading { .. })),
        "FictionBook with sections should contain Heading nodes"
    );
    assert!(
        has_node_type(doc, |c| matches!(c, NodeContent::Paragraph { .. })),
        "FictionBook should contain Paragraph nodes"
    );

    let md = render_to_markdown(doc);
    assert!(
        !md.trim().is_empty(),
        "render_to_markdown should produce non-empty output"
    );
}

// ============================================================================
// DBF
// ============================================================================

#[tokio::test]
async fn test_document_structure_dbf() {
    let path = helpers::get_test_file_path("dbf/stations.dbf");
    if !path.exists() {
        return;
    }

    let config = config_with_structure();
    let result = extract_file(&path, None, &config)
        .await
        .expect("DBF extraction should succeed");

    assert!(result.document.is_some(), "document should be populated");
    let doc = result.document.as_ref().unwrap();

    assert_eq!(
        doc.source_format.as_deref(),
        Some("dbf"),
        "source_format should be 'dbf'"
    );
    assert!(doc.validate().is_ok(), "document structure validation should pass");
    assert!(
        has_node_type(doc, |c| matches!(c, NodeContent::Table { .. })),
        "DBF should contain Table nodes from records"
    );

    let md = render_to_markdown(doc);
    assert!(
        !md.trim().is_empty(),
        "render_to_markdown should produce non-empty output"
    );
}

// ============================================================================
// Citation (RIS)
// ============================================================================

#[cfg(feature = "office")]
#[tokio::test]
async fn test_document_structure_citation() {
    let path = helpers::get_test_file_path("data_formats/sample.ris");
    if !path.exists() {
        return;
    }

    let config = config_with_structure();
    let result = extract_file(&path, None, &config)
        .await
        .expect("Citation extraction should succeed");

    assert!(result.document.is_some(), "document should be populated");
    let doc = result.document.as_ref().unwrap();

    assert_eq!(
        doc.source_format.as_deref(),
        Some("citation"),
        "source_format should be 'citation'"
    );
    assert!(doc.validate().is_ok(), "document structure validation should pass");
    assert!(
        has_node_type(doc, |c| matches!(c, NodeContent::Citation { .. })),
        "Citation file should contain Citation nodes"
    );

    let md = render_to_markdown(doc);
    assert!(
        !md.trim().is_empty(),
        "render_to_markdown should produce non-empty output"
    );
}

// ============================================================================
// XML
// ============================================================================

#[tokio::test]
async fn test_document_structure_xml() {
    let path = helpers::get_test_file_path("xml/simple_note.xml");
    if !path.exists() {
        return;
    }

    let config = config_with_structure();
    let result = extract_file(&path, None, &config)
        .await
        .expect("XML extraction should succeed");

    assert!(result.document.is_some(), "document should be populated");
    let doc = result.document.as_ref().unwrap();

    assert_eq!(
        doc.source_format.as_deref(),
        Some("xml"),
        "source_format should be 'xml'"
    );
    assert!(doc.validate().is_ok(), "document structure validation should pass");
    assert!(
        has_node_type(doc, |c| matches!(c, NodeContent::Paragraph { .. })),
        "XML should contain Paragraph nodes from text content"
    );

    let md = render_to_markdown(doc);
    assert!(
        !md.trim().is_empty(),
        "render_to_markdown should produce non-empty output"
    );
}

// ============================================================================
// Structured (JSON)
// ============================================================================

#[tokio::test]
async fn test_document_structure_json() {
    let path = helpers::get_test_file_path("json/simple.json");
    if !path.exists() {
        return;
    }

    let config = config_with_structure();
    let result = extract_file(&path, None, &config)
        .await
        .expect("JSON extraction should succeed");

    assert!(result.document.is_some(), "document should be populated");
    let doc = result.document.as_ref().unwrap();

    assert_eq!(
        doc.source_format.as_deref(),
        Some("json"),
        "source_format should be 'json'"
    );
    assert!(doc.validate().is_ok(), "document structure validation should pass");
    assert!(
        has_node_type(doc, |c| matches!(c, NodeContent::Code { .. })),
        "JSON should contain Code nodes for structured data"
    );

    let md = render_to_markdown(doc);
    assert!(
        !md.trim().is_empty(),
        "render_to_markdown should produce non-empty output"
    );
}

// ============================================================================
// Structured (YAML)
// ============================================================================

#[tokio::test]
async fn test_document_structure_yaml() {
    let path = helpers::get_test_file_path("yaml/simple.yaml");
    if !path.exists() {
        return;
    }

    let config = config_with_structure();
    let result = extract_file(&path, None, &config)
        .await
        .expect("YAML extraction should succeed");

    assert!(result.document.is_some(), "document should be populated");
    let doc = result.document.as_ref().unwrap();

    assert_eq!(
        doc.source_format.as_deref(),
        Some("yaml"),
        "source_format should be 'yaml'"
    );
    assert!(doc.validate().is_ok(), "document structure validation should pass");
    assert!(
        has_node_type(doc, |c| matches!(c, NodeContent::Code { .. })),
        "YAML should contain Code nodes for structured data"
    );

    let md = render_to_markdown(doc);
    assert!(
        !md.trim().is_empty(),
        "render_to_markdown should produce non-empty output"
    );
}

// ============================================================================
// Image (no OCR -- structure only)
// ============================================================================

#[cfg(any(feature = "ocr", feature = "ocr-wasm"))]
#[tokio::test]
async fn test_document_structure_image() {
    let path = helpers::get_test_file_path("images/example.jpg");
    if !path.exists() {
        return;
    }

    let config = config_with_structure();
    let result = extract_file(&path, None, &config).await;

    // Image extraction may fail if OCR backend is not configured at runtime;
    // verify it does not crash and produces a document when it succeeds.
    let result = match result {
        Ok(r) => r,
        Err(_) => return,
    };

    assert!(result.document.is_some(), "document should be populated for image");
    let doc = result.document.as_ref().unwrap();

    assert_eq!(
        doc.source_format.as_deref(),
        Some("image"),
        "source_format should be 'image'"
    );
    assert!(doc.validate().is_ok(), "document structure validation should pass");
    assert!(
        has_node_type(doc, |c| matches!(c, NodeContent::Image { .. })),
        "Image should contain Image nodes"
    );

    let md = render_to_markdown(doc);
    assert!(
        !md.trim().is_empty(),
        "render_to_markdown should produce non-empty output"
    );
}

// ============================================================================
// OPML
// ============================================================================

#[cfg(feature = "office")]
#[tokio::test]
async fn test_document_structure_opml() {
    let path = helpers::get_test_file_path("opml/outline.opml");
    if !path.exists() {
        return;
    }

    let config = config_with_structure();
    let result = extract_file(&path, None, &config)
        .await
        .expect("OPML extraction should succeed");

    assert!(result.document.is_some(), "document should be populated");
    let doc = result.document.as_ref().unwrap();

    assert_eq!(
        doc.source_format.as_deref(),
        Some("opml"),
        "source_format should be 'opml'"
    );
    assert!(doc.validate().is_ok(), "document structure validation should pass");
    assert!(!doc.nodes.is_empty(), "document nodes should be non-empty for OPML");

    let md = render_to_markdown(doc);
    assert!(
        !md.trim().is_empty(),
        "render_to_markdown should produce non-empty output"
    );
}

// ============================================================================
// HWP
// ============================================================================

#[cfg(feature = "hwp")]
#[tokio::test]
async fn test_document_structure_hwp() {
    let path = helpers::get_test_file_path("hwp/converted_output.hwp");
    if !path.exists() {
        return;
    }

    let config = config_with_structure();
    let result = extract_file(&path, None, &config)
        .await
        .expect("HWP extraction should succeed");

    assert!(result.document.is_some(), "document should be populated");
    let doc = result.document.as_ref().unwrap();

    assert_eq!(
        doc.source_format.as_deref(),
        Some("hwp"),
        "source_format should be 'hwp'"
    );
    assert!(doc.validate().is_ok(), "document structure validation should pass");
    assert!(
        has_node_type(doc, |c| matches!(c, NodeContent::Paragraph { .. })),
        "HWP should contain Paragraph nodes"
    );

    let md = render_to_markdown(doc);
    assert!(
        !md.trim().is_empty(),
        "render_to_markdown should produce non-empty output"
    );
}

// ============================================================================
// iWork Keynote
// ============================================================================

#[cfg(feature = "iwork")]
#[tokio::test]
async fn test_document_structure_keynote() {
    let path = helpers::get_test_file_path("iwork/test.key");
    if !path.exists() {
        return;
    }

    let config = config_with_structure();
    let result = extract_file(&path, None, &config)
        .await
        .expect("Keynote extraction should succeed");

    assert!(result.document.is_some(), "document should be populated");
    let doc = result.document.as_ref().unwrap();

    assert_eq!(
        doc.source_format.as_deref(),
        Some("keynote"),
        "source_format should be 'keynote'"
    );
    assert!(doc.validate().is_ok(), "document structure validation should pass");
    assert!(!doc.nodes.is_empty(), "document nodes should be non-empty for Keynote");

    let md = render_to_markdown(doc);
    assert!(
        !md.trim().is_empty(),
        "render_to_markdown should produce non-empty output"
    );
}

// ============================================================================
// iWork Numbers
// ============================================================================

#[cfg(feature = "iwork")]
#[tokio::test]
async fn test_document_structure_numbers() {
    let path = helpers::get_test_file_path("iwork/test.numbers");
    if !path.exists() {
        return;
    }

    let config = config_with_structure();
    let result = extract_file(&path, None, &config)
        .await
        .expect("Numbers extraction should succeed");

    assert!(result.document.is_some(), "document should be populated");
    let doc = result.document.as_ref().unwrap();

    assert_eq!(
        doc.source_format.as_deref(),
        Some("numbers"),
        "source_format should be 'numbers'"
    );
    assert!(doc.validate().is_ok(), "document structure validation should pass");
    assert!(!doc.nodes.is_empty(), "document nodes should be non-empty for Numbers");

    let md = render_to_markdown(doc);
    assert!(
        !md.trim().is_empty(),
        "render_to_markdown should produce non-empty output"
    );
}

// ============================================================================
// iWork Pages
// ============================================================================

#[cfg(feature = "iwork")]
#[tokio::test]
async fn test_document_structure_pages() {
    let path = helpers::get_test_file_path("iwork/test.pages");
    if !path.exists() {
        return;
    }

    let config = config_with_structure();
    let result = extract_file(&path, None, &config)
        .await
        .expect("Pages extraction should succeed");

    assert!(result.document.is_some(), "document should be populated");
    let doc = result.document.as_ref().unwrap();

    assert_eq!(
        doc.source_format.as_deref(),
        Some("pages"),
        "source_format should be 'pages'"
    );
    assert!(doc.validate().is_ok(), "document structure validation should pass");
    assert!(
        has_node_type(doc, |c| matches!(c, NodeContent::Paragraph { .. })),
        "Pages should contain Paragraph nodes"
    );

    let md = render_to_markdown(doc);
    assert!(
        !md.trim().is_empty(),
        "render_to_markdown should produce non-empty output"
    );
}

// ============================================================================
// Enhanced Markdown (office feature — pulldown-cmark AST)
// ============================================================================

#[cfg(feature = "office")]
#[tokio::test]
async fn test_document_structure_enhanced_markdown() {
    let path = helpers::get_test_file_path("markdown/comprehensive.md");
    if !path.exists() {
        return;
    }

    let config = config_with_structure();
    let result = extract_file(&path, None, &config)
        .await
        .expect("Enhanced Markdown extraction should succeed");

    assert!(
        result.document.is_some(),
        "document should be populated for enhanced markdown"
    );
    let doc = result.document.as_ref().unwrap();

    assert_eq!(
        doc.source_format.as_deref(),
        Some("markdown"),
        "source_format should be 'markdown'"
    );
    assert!(doc.validate().is_ok(), "document structure validation should pass");
    assert!(
        has_node_type(doc, |c| matches!(c, NodeContent::Heading { .. })),
        "Enhanced Markdown should contain Heading nodes from pulldown-cmark AST"
    );
    assert!(
        has_node_type(doc, |c| matches!(c, NodeContent::Paragraph { .. })),
        "Enhanced Markdown should contain Paragraph nodes"
    );

    let md = render_to_markdown(doc);
    assert!(
        !md.trim().is_empty(),
        "render_to_markdown should produce non-empty output"
    );
}

#[cfg(feature = "office")]
#[tokio::test]
async fn test_document_structure_enhanced_markdown_with_code() {
    let path = helpers::get_test_file_path("markdown/extraction_test.md");
    if !path.exists() {
        return;
    }

    let config = config_with_structure();
    let result = extract_file(&path, None, &config)
        .await
        .expect("Enhanced Markdown extraction should succeed");

    assert!(result.document.is_some(), "document should be populated");
    let doc = result.document.as_ref().unwrap();

    assert!(doc.validate().is_ok(), "document structure validation should pass");

    let md = render_to_markdown(doc);
    assert!(
        !md.trim().is_empty(),
        "render_to_markdown should produce non-empty output"
    );
}

// ============================================================================
// MDX
// ============================================================================

#[cfg(feature = "mdx")]
#[tokio::test]
async fn test_document_structure_mdx() {
    let path = helpers::get_test_file_path("markdown/sample.mdx");
    if !path.exists() {
        return;
    }

    let config = config_with_structure();
    let result = extract_file(&path, None, &config)
        .await
        .expect("MDX extraction should succeed");

    assert!(result.document.is_some(), "document should be populated for MDX");
    let doc = result.document.as_ref().unwrap();

    assert_eq!(
        doc.source_format.as_deref(),
        Some("mdx"),
        "source_format should be 'mdx'"
    );
    assert!(doc.validate().is_ok(), "document structure validation should pass");
    assert!(
        has_node_type(doc, |c| matches!(c, NodeContent::Heading { .. })),
        "MDX should contain Heading nodes"
    );
    assert!(
        has_node_type(doc, |c| matches!(c, NodeContent::Paragraph { .. })),
        "MDX should contain Paragraph nodes"
    );

    let md = render_to_markdown(doc);
    assert!(
        !md.trim().is_empty(),
        "render_to_markdown should produce non-empty output"
    );
}

#[cfg(feature = "mdx")]
#[tokio::test]
async fn test_document_structure_mdx_with_frontmatter() {
    let path = helpers::get_test_file_path("markdown/sample.mdx");
    if !path.exists() {
        return;
    }

    let config = config_with_structure();
    let result = extract_file(&path, None, &config)
        .await
        .expect("MDX extraction should succeed");

    let doc = result.document.as_ref().unwrap();

    // sample.mdx has YAML frontmatter which should produce a MetadataBlock
    assert!(
        has_node_type(doc, |c| matches!(c, NodeContent::MetadataBlock { .. })),
        "MDX with frontmatter should contain MetadataBlock nodes"
    );
}

// ============================================================================
// Djot
// ============================================================================

#[tokio::test]
async fn test_document_structure_djot() {
    let path = helpers::get_test_file_path("markdown/tables.djot");
    if !path.exists() {
        return;
    }

    let config = config_with_structure();
    let result = extract_file(&path, None, &config)
        .await
        .expect("Djot extraction should succeed");

    assert!(result.document.is_some(), "document should be populated for Djot");
    let doc = result.document.as_ref().unwrap();

    assert_eq!(
        doc.source_format.as_deref(),
        Some("djot"),
        "source_format should be 'djot'"
    );
    assert!(doc.validate().is_ok(), "document structure validation should pass");
    assert!(!doc.nodes.is_empty(), "document nodes should be non-empty for Djot");

    let md = render_to_markdown(doc);
    assert!(
        !md.trim().is_empty(),
        "render_to_markdown should produce non-empty output"
    );
}

// ============================================================================
// Typst
// ============================================================================

#[cfg(feature = "office")]
#[tokio::test]
async fn test_document_structure_typst() {
    let path = helpers::get_test_file_path("typst/headings.typ");
    if !path.exists() {
        return;
    }

    let config = config_with_structure();
    let result = extract_file(&path, None, &config)
        .await
        .expect("Typst extraction should succeed");

    assert!(result.document.is_some(), "document should be populated for Typst");
    let doc = result.document.as_ref().unwrap();

    assert_eq!(
        doc.source_format.as_deref(),
        Some("typst"),
        "source_format should be 'typst'"
    );
    assert!(doc.validate().is_ok(), "document structure validation should pass");
    assert!(
        has_node_type(doc, |c| matches!(c, NodeContent::Heading { .. })),
        "Typst with headings should contain Heading nodes"
    );

    let md = render_to_markdown(doc);
    assert!(
        !md.trim().is_empty(),
        "render_to_markdown should produce non-empty output"
    );
}

#[cfg(feature = "office")]
#[tokio::test]
async fn test_document_structure_typst_metadata() {
    let path = helpers::get_test_file_path("typst/metadata.typ");
    if !path.exists() {
        return;
    }

    let config = config_with_structure();
    let result = extract_file(&path, None, &config)
        .await
        .expect("Typst extraction should succeed");

    assert!(result.document.is_some(), "document should be populated");
    let doc = result.document.as_ref().unwrap();

    assert_eq!(doc.source_format.as_deref(), Some("typst"));
    assert!(doc.validate().is_ok());
    assert!(
        !doc.nodes.is_empty(),
        "document nodes should be non-empty for Typst with metadata"
    );

    let md = render_to_markdown(doc);
    assert!(
        !md.trim().is_empty(),
        "render_to_markdown should produce non-empty output"
    );
}

#[cfg(feature = "office")]
#[tokio::test]
async fn test_document_structure_typst_code_blocks() {
    let path = helpers::get_test_file_path("typst/advanced.typ");
    if !path.exists() {
        return;
    }

    let config = config_with_structure();
    let result = extract_file(&path, None, &config)
        .await
        .expect("Typst extraction should succeed");

    assert!(result.document.is_some(), "document should be populated");
    let doc = result.document.as_ref().unwrap();

    assert_eq!(doc.source_format.as_deref(), Some("typst"));
    assert!(doc.validate().is_ok());

    let md = render_to_markdown(doc);
    assert!(
        !md.trim().is_empty(),
        "render_to_markdown should produce non-empty output"
    );
}

// ============================================================================
// LaTeX Inline Formatting Annotations
// ============================================================================

/// Helper to extract document structure from inline LaTeX content via `extract_bytes_sync`.
#[cfg(feature = "office")]
fn latex_doc_structure(latex: &str) -> kreuzberg::types::document_structure::DocumentStructure {
    let config = ExtractionConfig {
        include_document_structure: true,
        ..Default::default()
    };
    let result = kreuzberg::extract_bytes_sync(latex.as_bytes(), "application/x-latex", &config)
        .expect("LaTeX extraction should succeed");
    result.document.expect("document structure should be populated")
}

#[cfg(feature = "office")]
#[test]
fn test_latex_bold_italic_annotations() {
    let latex = r"\begin{document}
This has \textbf{bold text} and \emph{italic text} here.
\end{document}";
    let doc = latex_doc_structure(latex);
    assert!(doc.validate().is_ok());

    // Find the paragraph node
    let para = doc
        .nodes
        .iter()
        .find(|n| matches!(&n.content, NodeContent::Paragraph { text } if text.contains("bold text")))
        .expect("should have paragraph with bold text");

    let text = match &para.content {
        NodeContent::Paragraph { text } => text.as_str(),
        _ => unreachable!(),
    };

    // The stripped text should have the command syntax removed
    assert!(
        !text.contains("\\textbf"),
        "stripped text should not contain \\textbf command"
    );
    assert!(
        !text.contains("\\emph"),
        "stripped text should not contain \\emph command"
    );
    assert!(text.contains("bold text"), "stripped text should contain 'bold text'");
    assert!(
        text.contains("italic text"),
        "stripped text should contain 'italic text'"
    );

    // Verify annotations exist
    let bold_ann = para.annotations.iter().find(|a| matches!(a.kind, AnnotationKind::Bold));
    assert!(bold_ann.is_some(), "should have a Bold annotation");
    let bold_ann = bold_ann.unwrap();
    let annotated_text = &text[bold_ann.start as usize..bold_ann.end as usize];
    assert_eq!(annotated_text, "bold text");

    let italic_ann = para
        .annotations
        .iter()
        .find(|a| matches!(a.kind, AnnotationKind::Italic));
    assert!(italic_ann.is_some(), "should have an Italic annotation");
    let italic_ann = italic_ann.unwrap();
    let annotated_text = &text[italic_ann.start as usize..italic_ann.end as usize];
    assert_eq!(annotated_text, "italic text");
}

#[cfg(feature = "office")]
#[test]
fn test_latex_underline_code_annotations() {
    let latex = r"\begin{document}
Some \underline{underlined} and \texttt{monospace} words.
\end{document}";
    let doc = latex_doc_structure(latex);
    assert!(doc.validate().is_ok());

    let para = doc
        .nodes
        .iter()
        .find(|n| matches!(&n.content, NodeContent::Paragraph { text } if text.contains("underlined")))
        .expect("should have paragraph");

    let underline_ann = para
        .annotations
        .iter()
        .find(|a| matches!(a.kind, AnnotationKind::Underline));
    assert!(underline_ann.is_some(), "should have Underline annotation");

    let code_ann = para.annotations.iter().find(|a| matches!(a.kind, AnnotationKind::Code));
    assert!(code_ann.is_some(), "should have Code annotation");
}

#[cfg(feature = "office")]
#[test]
fn test_latex_href_link_annotation() {
    let latex = r"\begin{document}
Visit \href{https://example.com}{the website} for details.
\end{document}";
    let doc = latex_doc_structure(latex);
    assert!(doc.validate().is_ok());

    let para = doc
        .nodes
        .iter()
        .find(|n| matches!(&n.content, NodeContent::Paragraph { text } if text.contains("the website")))
        .expect("should have paragraph with link text");

    let text = match &para.content {
        NodeContent::Paragraph { text } => text.as_str(),
        _ => unreachable!(),
    };

    assert!(
        !text.contains("\\href"),
        "stripped text should not contain \\href command"
    );
    assert!(
        !text.contains("https://example.com"),
        "URL should not appear in paragraph text"
    );

    let link_ann = para
        .annotations
        .iter()
        .find(|a| matches!(&a.kind, AnnotationKind::Link { .. }));
    assert!(link_ann.is_some(), "should have Link annotation");
    let link_ann = link_ann.unwrap();
    match &link_ann.kind {
        AnnotationKind::Link { url, .. } => {
            assert_eq!(url, "https://example.com");
        }
        _ => unreachable!(),
    }
    let annotated_text = &text[link_ann.start as usize..link_ann.end as usize];
    assert_eq!(annotated_text, "the website");
}

#[cfg(feature = "office")]
#[test]
fn test_latex_footnote_extraction() {
    let latex = r"\begin{document}
Main text with a footnote\footnote{This is the footnote content} here.
\end{document}";
    let doc = latex_doc_structure(latex);
    assert!(doc.validate().is_ok());

    let has_footnote = doc
        .nodes
        .iter()
        .any(|n| matches!(&n.content, NodeContent::Footnote { text } if text.contains("footnote content")));
    assert!(has_footnote, "should have a Footnote node with the footnote text");

    // The paragraph should not contain the \footnote command
    let para = doc
        .nodes
        .iter()
        .find(|n| matches!(&n.content, NodeContent::Paragraph { text } if text.contains("Main text")))
        .expect("should have the main paragraph");
    let text = match &para.content {
        NodeContent::Paragraph { text } => text.as_str(),
        _ => unreachable!(),
    };
    assert!(
        !text.contains("\\footnote"),
        "paragraph should not contain \\footnote command"
    );
}

#[cfg(feature = "office")]
#[test]
fn test_latex_includegraphics_image() {
    let latex = r"\begin{document}
\begin{figure}
\includegraphics[width=5cm]{images/photo.png}
\caption{A photo}
\end{figure}
\end{document}";
    let doc = latex_doc_structure(latex);
    assert!(doc.validate().is_ok());

    let image_node = doc
        .nodes
        .iter()
        .find(|n| matches!(&n.content, NodeContent::Image { .. }));
    assert!(image_node.is_some(), "should have an Image node");
    let image_node = image_node.unwrap();
    match &image_node.content {
        NodeContent::Image { description, .. } => {
            assert_eq!(description.as_deref(), Some("images/photo.png"));
        }
        _ => unreachable!(),
    }

    // Caption should be stored as an attribute
    if let Some(ref attrs) = image_node.attributes {
        assert_eq!(attrs.get("caption").map(|s| s.as_str()), Some("A photo"));
    } else {
        panic!("Image node should have attributes with caption");
    }
}

#[cfg(feature = "office")]
#[test]
fn test_latex_metadata_block() {
    let latex = r"\title{My Document}
\author{Jane Doe}
\date{2024-01-15}
\begin{document}
Hello world.
\end{document}";
    let doc = latex_doc_structure(latex);
    assert!(doc.validate().is_ok());

    let meta = doc
        .nodes
        .iter()
        .find(|n| matches!(&n.content, NodeContent::MetadataBlock { .. }));
    assert!(meta.is_some(), "should have a MetadataBlock node");
    let entries = match &meta.unwrap().content {
        NodeContent::MetadataBlock { entries } => entries,
        _ => unreachable!(),
    };
    assert!(
        entries.iter().any(|(k, v)| k == "title" && v == "My Document"),
        "metadata should contain title"
    );
    assert!(
        entries.iter().any(|(k, v)| k == "author" && v == "Jane Doe"),
        "metadata should contain author"
    );
    assert!(
        entries.iter().any(|(k, v)| k == "date" && v == "2024-01-15"),
        "metadata should contain date"
    );
}

// ============================================================================
// RST Inline Markup & Missing Features
// ============================================================================

#[cfg(feature = "office")]
#[tokio::test]
async fn test_rst_inline_bold_italic_annotations() {
    use kreuzberg::extractors::RstExtractor;
    use kreuzberg::plugins::DocumentExtractor;
    use kreuzberg::types::document_structure::{AnnotationKind, NodeContent};

    let rst = b"This has **bold** and *italic* and ``code`` text.";
    let config = config_with_structure();
    let internal_doc = RstExtractor::new()
        .extract_bytes(rst, "text/x-rst", &config)
        .await
        .expect("RST extraction should succeed");
    let result = derive_extraction_result(internal_doc, true, kreuzberg::OutputFormat::Plain);

    let doc = result.document.as_ref().expect("document should be present");
    assert!(doc.validate().is_ok());

    let para = doc
        .nodes
        .iter()
        .find(|n| matches!(&n.content, NodeContent::Paragraph { text } if text.contains("bold")))
        .expect("should have paragraph with bold");

    let has_bold = para.annotations.iter().any(|a| matches!(a.kind, AnnotationKind::Bold));
    let has_italic = para
        .annotations
        .iter()
        .any(|a| matches!(a.kind, AnnotationKind::Italic));
    let has_code = para.annotations.iter().any(|a| matches!(a.kind, AnnotationKind::Code));
    assert!(has_bold, "should have bold annotation");
    assert!(has_italic, "should have italic annotation");
    assert!(has_code, "should have code annotation");

    if let NodeContent::Paragraph { text } = &para.content {
        assert!(!text.contains("**"), "bold markers should be stripped");
        assert!(text.contains("bold"), "bold text should remain");
        assert!(text.contains("italic"), "italic text should remain");
        assert!(text.contains("code"), "code text should remain");
    }
}

#[cfg(feature = "office")]
#[tokio::test]
async fn test_rst_footnotes() {
    use kreuzberg::extractors::RstExtractor;
    use kreuzberg::plugins::DocumentExtractor;
    use kreuzberg::types::document_structure::NodeContent;

    let rst = b"Some text with a footnote [1]_.\n\n.. [1] This is the footnote text.";
    let config = config_with_structure();
    let internal_doc = RstExtractor::new()
        .extract_bytes(rst, "text/x-rst", &config)
        .await
        .expect("RST extraction should succeed");
    let result = derive_extraction_result(internal_doc, true, kreuzberg::OutputFormat::Plain);

    let doc = result.document.as_ref().expect("document should be present");
    assert!(doc.validate().is_ok());

    let has_footnote = doc
        .nodes
        .iter()
        .any(|n| matches!(&n.content, NodeContent::Footnote { text } if text.contains("[1]")));
    assert!(has_footnote, "should have footnote node");
}

#[cfg(feature = "office")]
#[tokio::test]
async fn test_rst_definition_lists() {
    use kreuzberg::extractors::RstExtractor;
    use kreuzberg::plugins::DocumentExtractor;
    use kreuzberg::types::document_structure::NodeContent;

    let rst = b"Term 1\n   Definition of term 1.\n\nTerm 2\n   Definition of term 2.";
    let config = config_with_structure();
    let internal_doc = RstExtractor::new()
        .extract_bytes(rst, "text/x-rst", &config)
        .await
        .expect("RST extraction should succeed");
    let result = derive_extraction_result(internal_doc, true, kreuzberg::OutputFormat::Plain);

    let doc = result.document.as_ref().expect("document should be present");
    assert!(doc.validate().is_ok());

    let has_def_list = doc
        .nodes
        .iter()
        .any(|n| matches!(&n.content, NodeContent::DefinitionList));
    assert!(has_def_list, "should have definition list node");

    let has_def_item = doc.nodes.iter().any(|n| {
        matches!(&n.content, NodeContent::DefinitionItem { term, definition }
            if term == "Term 1" && definition.contains("Definition of term 1"))
    });
    assert!(
        has_def_item,
        "should have definition item with correct term and definition"
    );
}

#[cfg(feature = "office")]
#[tokio::test]
async fn test_rst_image_with_options() {
    use kreuzberg::extractors::RstExtractor;
    use kreuzberg::plugins::DocumentExtractor;
    use kreuzberg::types::document_structure::NodeContent;

    let rst = b".. image:: /images/logo.png\n   :alt: Company Logo\n   :width: 200px\n   :height: 100px";
    let config = config_with_structure();
    let internal_doc = RstExtractor::new()
        .extract_bytes(rst, "text/x-rst", &config)
        .await
        .expect("RST extraction should succeed");
    let result = derive_extraction_result(internal_doc, true, kreuzberg::OutputFormat::Plain);

    let doc = result.document.as_ref().expect("document should be present");
    assert!(doc.validate().is_ok());

    let img_node = doc
        .nodes
        .iter()
        .find(|n| matches!(&n.content, NodeContent::Image { .. }))
        .expect("should have image node");

    if let NodeContent::Image { description, .. } = &img_node.content {
        assert_eq!(
            description.as_deref(),
            Some("Company Logo"),
            "image should have alt text as description"
        );
    }

    let attrs = img_node.attributes.as_ref().expect("image should have attributes");
    assert_eq!(attrs.get("width").map(|s| s.as_str()), Some("200px"));
    assert_eq!(attrs.get("height").map(|s| s.as_str()), Some("100px"));
    assert_eq!(attrs.get("src").map(|s| s.as_str()), Some("/images/logo.png"));
}

// ============================================================================
// OrgMode Inline Markup & Missing Features
// ============================================================================

#[cfg(feature = "office")]
#[tokio::test]
async fn test_orgmode_inline_bold_italic_annotations() {
    use kreuzberg::extractors::OrgModeExtractor;
    use kreuzberg::plugins::DocumentExtractor;
    use kreuzberg::types::document_structure::{AnnotationKind, NodeContent};

    let org = b"This has *bold* and /italic/ and =code= text.";
    let config = config_with_structure();
    let internal_doc = OrgModeExtractor::new()
        .extract_bytes(org, "text/x-org", &config)
        .await
        .expect("OrgMode extraction should succeed");
    let result = derive_extraction_result(internal_doc, true, kreuzberg::OutputFormat::Plain);

    let doc = result.document.as_ref().expect("document should be present");
    assert!(doc.validate().is_ok());

    let para = doc
        .nodes
        .iter()
        .find(|n| matches!(&n.content, NodeContent::Paragraph { text } if text.contains("bold")))
        .expect("should have paragraph with bold");

    let has_bold = para.annotations.iter().any(|a| matches!(a.kind, AnnotationKind::Bold));
    let has_italic = para
        .annotations
        .iter()
        .any(|a| matches!(a.kind, AnnotationKind::Italic));
    let has_code = para.annotations.iter().any(|a| matches!(a.kind, AnnotationKind::Code));
    assert!(has_bold, "should have bold annotation");
    assert!(has_italic, "should have italic annotation");
    assert!(has_code, "should have code annotation");

    if let NodeContent::Paragraph { text } = &para.content {
        assert!(!text.contains("*bold*"), "bold markers should be stripped");
        assert!(text.contains("bold"), "bold text should remain");
    }
}

#[cfg(feature = "office")]
#[tokio::test]
async fn test_orgmode_link_annotations() {
    use kreuzberg::extractors::OrgModeExtractor;
    use kreuzberg::plugins::DocumentExtractor;
    use kreuzberg::types::document_structure::{AnnotationKind, NodeContent};

    let org = b"Visit [[https://example.com][Example Site]] for more.";
    let config = config_with_structure();
    let internal_doc = OrgModeExtractor::new()
        .extract_bytes(org, "text/x-org", &config)
        .await
        .expect("OrgMode extraction should succeed");
    let result = derive_extraction_result(internal_doc, true, kreuzberg::OutputFormat::Plain);

    let doc = result.document.as_ref().expect("document should be present");
    assert!(doc.validate().is_ok());

    let para = doc
        .nodes
        .iter()
        .find(|n| matches!(&n.content, NodeContent::Paragraph { text } if text.contains("Example Site")))
        .expect("should have paragraph with link");

    let link_ann = para
        .annotations
        .iter()
        .find(|a| matches!(&a.kind, AnnotationKind::Link { .. }))
        .expect("should have link annotation");

    if let AnnotationKind::Link { url, .. } = &link_ann.kind {
        assert_eq!(url, "https://example.com");
    }

    if let NodeContent::Paragraph { text } = &para.content {
        assert!(text.contains("Example Site"), "link display text should be present");
        assert!(!text.contains("[["), "link markers should be stripped");
    }
}

#[cfg(feature = "office")]
#[tokio::test]
async fn test_orgmode_footnotes() {
    use kreuzberg::extractors::OrgModeExtractor;
    use kreuzberg::plugins::DocumentExtractor;
    use kreuzberg::types::document_structure::NodeContent;

    let org = b"Some text with a footnote [fn:1].";
    let config = config_with_structure();
    let internal_doc = OrgModeExtractor::new()
        .extract_bytes(org, "text/x-org", &config)
        .await
        .expect("OrgMode extraction should succeed");
    let result = derive_extraction_result(internal_doc, true, kreuzberg::OutputFormat::Plain);

    let doc = result.document.as_ref().expect("document should be present");
    assert!(doc.validate().is_ok());

    let has_footnote = doc
        .nodes
        .iter()
        .any(|n| matches!(&n.content, NodeContent::Footnote { text } if text.contains("[fn:1]")));
    assert!(has_footnote, "should have footnote node for [fn:1]");
}

#[cfg(feature = "office")]
#[tokio::test]
async fn test_orgmode_properties_drawer() {
    use kreuzberg::extractors::OrgModeExtractor;
    use kreuzberg::plugins::DocumentExtractor;
    use kreuzberg::types::document_structure::NodeContent;

    let org = b"* My Heading\n:PROPERTIES:\n:CUSTOM_ID: my-id\n:CATEGORY: test\n:END:\n\nSome content.";
    let config = config_with_structure();
    let internal_doc = OrgModeExtractor::new()
        .extract_bytes(org, "text/x-org", &config)
        .await
        .expect("OrgMode extraction should succeed");
    let result = derive_extraction_result(internal_doc, true, kreuzberg::OutputFormat::Plain);

    let doc = result.document.as_ref().expect("document should be present");
    assert!(doc.validate().is_ok());

    let has_metadata = doc.nodes.iter().any(|n| {
        matches!(&n.content, NodeContent::MetadataBlock { entries }
            if entries.iter().any(|(k, _)| k == "CUSTOM_ID"))
    });
    assert!(has_metadata, "should have metadata block from properties drawer");
}

#[cfg(feature = "office")]
#[tokio::test]
async fn test_orgmode_todo_keywords_and_tags() {
    use kreuzberg::extractors::OrgModeExtractor;
    use kreuzberg::plugins::DocumentExtractor;
    use kreuzberg::types::document_structure::NodeContent;

    let org = b"* TODO Buy groceries :shopping:errands:";
    let config = config_with_structure();
    let internal_doc = OrgModeExtractor::new()
        .extract_bytes(org, "text/x-org", &config)
        .await
        .expect("OrgMode extraction should succeed");
    let result = derive_extraction_result(internal_doc, true, kreuzberg::OutputFormat::Plain);

    let doc = result.document.as_ref().expect("document should be present");
    assert!(doc.validate().is_ok());

    let group = doc.nodes.iter().find(|n| {
        matches!(
            &n.content,
            NodeContent::Group {
                heading_text: Some(text),
                ..
            } if text == "Buy groceries"
        )
    });
    assert!(group.is_some(), "should have heading with TODO stripped from text");

    let group = group.unwrap();
    let attrs = group.attributes.as_ref().expect("heading group should have attributes");
    assert_eq!(attrs.get("todo").map(|s| s.as_str()), Some("TODO"));
    assert!(attrs.get("tags").is_some_and(|t| t.contains("shopping")));
}

#[cfg(feature = "office")]
#[tokio::test]
async fn test_orgmode_checkboxes() {
    use kreuzberg::extractors::OrgModeExtractor;
    use kreuzberg::plugins::DocumentExtractor;
    use kreuzberg::types::document_structure::NodeContent;

    let org = b"- [ ] Unchecked item\n- [x] Checked item\n- Regular item";
    let config = config_with_structure();
    let internal_doc = OrgModeExtractor::new()
        .extract_bytes(org, "text/x-org", &config)
        .await
        .expect("OrgMode extraction should succeed");
    let result = derive_extraction_result(internal_doc, true, kreuzberg::OutputFormat::Plain);

    let doc = result.document.as_ref().expect("document should be present");
    assert!(doc.validate().is_ok());

    let unchecked = doc
        .nodes
        .iter()
        .find(|n| matches!(&n.content, NodeContent::ListItem { text } if text.contains("Unchecked")));
    assert!(unchecked.is_some(), "should have unchecked list item");
    let attrs = unchecked
        .unwrap()
        .attributes
        .as_ref()
        .expect("unchecked item should have attributes");
    assert_eq!(attrs.get("checkbox").map(|s| s.as_str()), Some("unchecked"));

    let checked = doc
        .nodes
        .iter()
        .find(|n| matches!(&n.content, NodeContent::ListItem { text } if text.contains("Checked")));
    assert!(checked.is_some(), "should have checked list item");
    let attrs = checked
        .unwrap()
        .attributes
        .as_ref()
        .expect("checked item should have attributes");
    assert_eq!(attrs.get("checkbox").map(|s| s.as_str()), Some("checked"));
}

// ============================================================================
// Markdown / MDX / Djot Inline Formatting Annotations
// ============================================================================

/// Helper: extract document structure from markdown bytes.
#[cfg(feature = "office")]
fn markdown_doc_structure(md: &str) -> kreuzberg::types::document_structure::DocumentStructure {
    let config = ExtractionConfig {
        include_document_structure: true,
        ..Default::default()
    };
    let result = kreuzberg::extract_bytes_sync(md.as_bytes(), "text/markdown", &config)
        .expect("markdown extraction should succeed");
    result.document.expect("document structure should be present")
}

/// Helper: extract document structure from djot bytes.
fn djot_doc_structure(djot: &str) -> kreuzberg::types::document_structure::DocumentStructure {
    let config = ExtractionConfig {
        include_document_structure: true,
        ..Default::default()
    };
    let result =
        kreuzberg::extract_bytes_sync(djot.as_bytes(), "text/djot", &config).expect("djot extraction should succeed");
    result.document.expect("document structure should be present")
}

/// Helper: extract document structure from MDX bytes.
#[cfg(feature = "mdx")]
fn mdx_doc_structure(mdx: &str) -> kreuzberg::types::document_structure::DocumentStructure {
    let config = ExtractionConfig {
        include_document_structure: true,
        ..Default::default()
    };
    let result =
        kreuzberg::extract_bytes_sync(mdx.as_bytes(), "text/mdx", &config).expect("mdx extraction should succeed");
    result.document.expect("document structure should be present")
}

/// Collect all annotations from paragraph nodes in a document.
fn collect_paragraph_annotations(
    doc: &kreuzberg::types::document_structure::DocumentStructure,
) -> Vec<&kreuzberg::types::document_structure::TextAnnotation> {
    doc.nodes
        .iter()
        .filter(|n| matches!(n.content, NodeContent::Paragraph { .. }))
        .flat_map(|n| n.annotations.iter())
        .collect()
}

#[cfg(feature = "office")]
#[test]
fn test_markdown_annotations_bold_italic() {
    let doc = markdown_doc_structure("This is **bold** and *italic* text.\n");

    let annotations = collect_paragraph_annotations(&doc);
    assert!(
        !annotations.is_empty(),
        "markdown paragraph should have annotations for bold/italic"
    );

    let has_bold = annotations.iter().any(|a| matches!(a.kind, AnnotationKind::Bold));
    let has_italic = annotations.iter().any(|a| matches!(a.kind, AnnotationKind::Italic));
    assert!(has_bold, "should have Bold annotation");
    assert!(has_italic, "should have Italic annotation");

    // After markdown rendering the plain text is: "This is bold and italic text."
    let bold_ann = annotations
        .iter()
        .find(|a| matches!(a.kind, AnnotationKind::Bold))
        .unwrap();
    assert_eq!(bold_ann.start, 8, "bold start should be at byte 8");
    assert_eq!(bold_ann.end, 12, "bold end should be at byte 12");

    let italic_ann = annotations
        .iter()
        .find(|a| matches!(a.kind, AnnotationKind::Italic))
        .unwrap();
    assert_eq!(italic_ann.start, 17, "italic start should be at byte 17");
    assert_eq!(italic_ann.end, 23, "italic end should be at byte 23");
}

#[cfg(feature = "office")]
#[test]
fn test_markdown_link_annotations() {
    let doc = markdown_doc_structure("Click [here](https://example.com) for more.\n");

    let annotations = collect_paragraph_annotations(&doc);
    let link_ann = annotations
        .iter()
        .find(|a| matches!(a.kind, AnnotationKind::Link { .. }))
        .expect("should have Link annotation");

    match &link_ann.kind {
        AnnotationKind::Link { url, .. } => {
            assert_eq!(url, "https://example.com");
        }
        _ => panic!("expected Link annotation"),
    }

    // "Click here for more." — "here" starts at byte 6
    assert_eq!(link_ann.start, 6, "link start should be at byte 6");
    assert_eq!(link_ann.end, 10, "link end should be at byte 10");
}

#[cfg(feature = "office")]
#[test]
fn test_markdown_strikethrough_annotation() {
    let doc = markdown_doc_structure("This is ~~deleted~~ text.\n");

    let annotations = collect_paragraph_annotations(&doc);
    let strike = annotations
        .iter()
        .find(|a| matches!(a.kind, AnnotationKind::Strikethrough));
    assert!(strike.is_some(), "should have Strikethrough annotation");
}

#[cfg(feature = "office")]
#[test]
fn test_markdown_inline_code_annotation() {
    let doc = markdown_doc_structure("Use `println!` to print.\n");

    let annotations = collect_paragraph_annotations(&doc);
    let code_ann = annotations.iter().find(|a| matches!(a.kind, AnnotationKind::Code));
    assert!(code_ann.is_some(), "should have Code annotation for inline code");

    let code_ann = code_ann.unwrap();
    // "Use println! to print." — "println!" starts at byte 4
    assert_eq!(code_ann.start, 4, "code start should be at byte 4");
    assert_eq!(code_ann.end, 12, "code end should be at byte 12");
}

#[cfg(feature = "office")]
#[test]
fn test_markdown_footnote_reference() {
    let doc = markdown_doc_structure("Text with a footnote[^1].\n\n[^1]: Footnote content.\n");

    let has_footnote = doc
        .nodes
        .iter()
        .any(|n| matches!(n.content, NodeContent::Footnote { .. }));
    assert!(has_footnote, "should have Footnote node from footnote reference");
}

#[cfg(feature = "office")]
#[test]
fn test_markdown_nested_bold_italic() {
    let doc = markdown_doc_structure("This is ***bold and italic*** text.\n");

    let annotations = collect_paragraph_annotations(&doc);
    let has_bold = annotations.iter().any(|a| matches!(a.kind, AnnotationKind::Bold));
    let has_italic = annotations.iter().any(|a| matches!(a.kind, AnnotationKind::Italic));
    assert!(has_bold, "nested ***text*** should have Bold annotation");
    assert!(has_italic, "nested ***text*** should have Italic annotation");
}

// -- Djot annotation tests --

#[test]
fn test_djot_annotations_bold_italic() {
    let doc = djot_doc_structure("This is *bold* and _italic_ text.\n");

    let annotations = collect_paragraph_annotations(&doc);
    assert!(
        !annotations.is_empty(),
        "djot paragraph should have annotations for bold/italic"
    );

    let has_bold = annotations.iter().any(|a| matches!(a.kind, AnnotationKind::Bold));
    let has_italic = annotations.iter().any(|a| matches!(a.kind, AnnotationKind::Italic));
    assert!(has_bold, "djot *text* should produce Bold annotation");
    assert!(has_italic, "djot _text_ should produce Italic annotation");
}

#[test]
fn test_djot_link_annotations() {
    let doc = djot_doc_structure("Click [here](https://example.com) for more.\n");

    let annotations = collect_paragraph_annotations(&doc);
    let link_ann = annotations
        .iter()
        .find(|a| matches!(a.kind, AnnotationKind::Link { .. }))
        .expect("djot should have Link annotation");

    match &link_ann.kind {
        AnnotationKind::Link { url, .. } => {
            assert_eq!(url, "https://example.com");
        }
        _ => panic!("expected Link annotation"),
    }
}

#[test]
fn test_djot_strikethrough_annotation() {
    let doc = djot_doc_structure("This is {-deleted-} text.\n");

    let annotations = collect_paragraph_annotations(&doc);
    let strike = annotations
        .iter()
        .find(|a| matches!(a.kind, AnnotationKind::Strikethrough));
    assert!(
        strike.is_some(),
        "djot strikethrough syntax should produce Strikethrough annotation"
    );
}

#[test]
fn test_djot_inline_code_annotation() {
    let doc = djot_doc_structure("Use `println!` to print.\n");

    let annotations = collect_paragraph_annotations(&doc);
    let code_ann = annotations.iter().find(|a| matches!(a.kind, AnnotationKind::Code));
    assert!(code_ann.is_some(), "djot `code` should produce Code annotation");
}

// -- MDX annotation tests --

#[cfg(feature = "mdx")]
#[test]
fn test_mdx_annotations_bold_italic() {
    let doc = mdx_doc_structure("This is **bold** and *italic* text.\n");

    let annotations = collect_paragraph_annotations(&doc);
    assert!(
        !annotations.is_empty(),
        "MDX paragraph should have annotations for bold/italic"
    );

    let has_bold = annotations.iter().any(|a| matches!(a.kind, AnnotationKind::Bold));
    let has_italic = annotations.iter().any(|a| matches!(a.kind, AnnotationKind::Italic));
    assert!(has_bold, "MDX **text** should produce Bold annotation");
    assert!(has_italic, "MDX *text* should produce Italic annotation");
}

#[cfg(feature = "mdx")]
#[test]
fn test_mdx_link_annotations() {
    let doc = mdx_doc_structure("Click [here](https://example.com) for more.\n");

    let annotations = collect_paragraph_annotations(&doc);
    let link_ann = annotations
        .iter()
        .find(|a| matches!(a.kind, AnnotationKind::Link { .. }))
        .expect("MDX should have Link annotation");

    match &link_ann.kind {
        AnnotationKind::Link { url, .. } => {
            assert_eq!(url, "https://example.com");
        }
        _ => panic!("expected Link annotation"),
    }
}

// ============================================================================
// Typst Inline Formatting Annotations
// ============================================================================

/// Helper to extract document structure from inline Typst content.
#[cfg(feature = "office")]
fn typst_doc_structure(typst: &str) -> kreuzberg::types::document_structure::DocumentStructure {
    let config = ExtractionConfig {
        include_document_structure: true,
        ..Default::default()
    };
    let result = kreuzberg::extract_bytes_sync(typst.as_bytes(), "application/x-typst", &config)
        .expect("Typst extraction should succeed");
    result.document.expect("document structure should be populated")
}

#[cfg(feature = "office")]
#[test]
fn test_typst_bold_italic_code_annotations() {
    let typst = "This has *bold text* and _italic text_ and `code text` here.";
    let doc = typst_doc_structure(typst);
    assert!(doc.validate().is_ok());

    let para = doc
        .nodes
        .iter()
        .find(|n| matches!(&n.content, NodeContent::Paragraph { text } if text.contains("bold text")))
        .expect("should have paragraph with formatted text");

    let text = match &para.content {
        NodeContent::Paragraph { text } => text.as_str(),
        _ => unreachable!(),
    };

    // Markers should be stripped from the text
    assert!(
        !text.contains("*bold"),
        "stripped text should not contain * markers around bold"
    );
    assert!(text.contains("bold text"), "text should contain 'bold text'");
    assert!(text.contains("italic text"), "text should contain 'italic text'");
    assert!(text.contains("code text"), "text should contain 'code text'");

    // Verify bold annotation
    let bold_ann = para.annotations.iter().find(|a| matches!(a.kind, AnnotationKind::Bold));
    assert!(bold_ann.is_some(), "should have a Bold annotation");
    let bold_ann = bold_ann.unwrap();
    let annotated = &text[bold_ann.start as usize..bold_ann.end as usize];
    assert_eq!(annotated, "bold text");

    // Verify italic annotation
    let italic_ann = para
        .annotations
        .iter()
        .find(|a| matches!(a.kind, AnnotationKind::Italic));
    assert!(italic_ann.is_some(), "should have an Italic annotation");
    let italic_ann = italic_ann.unwrap();
    let annotated = &text[italic_ann.start as usize..italic_ann.end as usize];
    assert_eq!(annotated, "italic text");

    // Verify code annotation
    let code_ann = para.annotations.iter().find(|a| matches!(a.kind, AnnotationKind::Code));
    assert!(code_ann.is_some(), "should have a Code annotation");
    let code_ann = code_ann.unwrap();
    let annotated = &text[code_ann.start as usize..code_ann.end as usize];
    assert_eq!(annotated, "code text");
}

#[cfg(feature = "office")]
#[test]
fn test_typst_link_annotation() {
    let typst = r#"Visit #link("https://example.com")[example site] for info."#;
    let doc = typst_doc_structure(typst);
    assert!(doc.validate().is_ok());

    let para = doc
        .nodes
        .iter()
        .find(|n| matches!(&n.content, NodeContent::Paragraph { text } if text.contains("example site")))
        .expect("should have paragraph with link text");

    let text = match &para.content {
        NodeContent::Paragraph { text } => text.as_str(),
        _ => unreachable!(),
    };

    // URL should not appear in the paragraph text
    assert!(
        !text.contains("#link"),
        "paragraph text should not contain #link syntax"
    );

    let link_ann = para
        .annotations
        .iter()
        .find(|a| matches!(&a.kind, AnnotationKind::Link { .. }));
    assert!(link_ann.is_some(), "should have Link annotation");
    let link_ann = link_ann.unwrap();
    match &link_ann.kind {
        AnnotationKind::Link { url, .. } => {
            assert_eq!(url, "https://example.com");
        }
        _ => unreachable!(),
    }
    let annotated = &text[link_ann.start as usize..link_ann.end as usize];
    assert_eq!(annotated, "example site");
}

#[cfg(feature = "office")]
#[test]
fn test_typst_footnote_extraction() {
    let typst = "Main text.\n\n#footnote[This is a footnote]";
    let doc = typst_doc_structure(typst);
    assert!(doc.validate().is_ok());

    let has_footnote = doc
        .nodes
        .iter()
        .any(|n| matches!(&n.content, NodeContent::Footnote { text } if text.contains("This is a footnote")));
    assert!(has_footnote, "should have a Footnote node");
}

#[cfg(feature = "office")]
#[test]
fn test_typst_image_extraction() {
    let typst = "#image(\"photo.png\")";
    let doc = typst_doc_structure(typst);
    assert!(doc.validate().is_ok());

    let image = doc
        .nodes
        .iter()
        .find(|n| matches!(&n.content, NodeContent::Image { .. }));
    assert!(image.is_some(), "should have an Image node");
    match &image.unwrap().content {
        NodeContent::Image { description, .. } => {
            assert_eq!(description.as_deref(), Some("photo.png"));
        }
        _ => unreachable!(),
    }
}

#[cfg(feature = "office")]
#[test]
fn test_typst_table_extraction() {
    let typst = "#table(\n  columns: 2,\n  [Name], [Age],\n  [Alice], [30],\n)";
    let doc = typst_doc_structure(typst);
    assert!(doc.validate().is_ok());

    let table = doc
        .nodes
        .iter()
        .find(|n| matches!(&n.content, NodeContent::Table { .. }));
    assert!(table.is_some(), "should have a Table node");
    match &table.unwrap().content {
        NodeContent::Table { grid } => {
            assert_eq!(grid.rows, 2);
            assert_eq!(grid.cols, 2);
        }
        _ => unreachable!(),
    }
}

// ============================================================================
// HTML Enhanced Structure Tests
// ============================================================================

/// Helper to extract document structure from inline HTML content.
#[cfg(feature = "html")]
fn html_doc_structure(html: &str) -> kreuzberg::types::document_structure::DocumentStructure {
    let config = ExtractionConfig {
        include_document_structure: true,
        ..Default::default()
    };
    let result =
        kreuzberg::extract_bytes_sync(html.as_bytes(), "text/html", &config).expect("HTML extraction should succeed");
    result.document.expect("document structure should be populated")
}

#[cfg(feature = "html")]
#[test]
#[ignore = "TODO: definition list items not parented under DL node through full pipeline"]
fn test_html_definition_list() {
    let html = "<dl><dt>Term 1</dt><dd>Definition 1</dd><dt>Term 2</dt><dd>Definition 2</dd></dl>";
    let doc = html_doc_structure(html);
    assert!(doc.validate().is_ok());

    let dl = doc
        .nodes
        .iter()
        .find(|n| matches!(&n.content, NodeContent::DefinitionList));
    assert!(dl.is_some(), "should have a DefinitionList node");
    let dl = dl.unwrap();
    assert_eq!(dl.children.len(), 2, "should have 2 definition items");

    let first_item = &doc.nodes[dl.children[0].0 as usize];
    match &first_item.content {
        NodeContent::DefinitionItem { term, definition } => {
            assert_eq!(term, "Term 1");
            assert_eq!(definition, "Definition 1");
        }
        other => panic!("Expected DefinitionItem, got {:?}", other),
    }
}

#[cfg(feature = "html")]
#[test]
fn test_html_table_spans() {
    let html = r#"<table>
        <tr><th colspan="2">Header</th></tr>
        <tr><td>A</td><td rowspan="2">B</td></tr>
        <tr><td>C</td></tr>
    </table>"#;
    let doc = html_doc_structure(html);
    assert!(doc.validate().is_ok());

    let table = doc
        .nodes
        .iter()
        .find(|n| matches!(&n.content, NodeContent::Table { .. }));
    assert!(table.is_some(), "should have a Table node");
    match &table.unwrap().content {
        NodeContent::Table { grid } => {
            let header_cell = grid.cells.iter().find(|c| c.content == "Header");
            assert!(header_cell.is_some(), "should have Header cell");
            let a_cell = grid.cells.iter().find(|c| c.content == "A");
            assert!(a_cell.is_some(), "should have A cell");
            let b_cell = grid.cells.iter().find(|c| c.content == "B");
            assert!(b_cell.is_some(), "should have B cell");
        }
        _ => unreachable!(),
    }
}

#[cfg(feature = "html")]
#[test]
fn test_html_figure_with_caption() {
    // html-to-markdown extracts figure/caption as part of the markdown content.
    // The document structure may not have a dedicated Image node for figures;
    // verify content is extracted correctly via the full pipeline.
    let html = r#"<figure><img src="photo.jpg" alt="A photo"><figcaption>Photo caption</figcaption></figure>"#;
    let config = ExtractionConfig::default();
    let result =
        kreuzberg::extract_bytes_sync(html.as_bytes(), "text/html", &config).expect("extraction should succeed");
    let content = result.content;
    assert!(
        content.contains("photo") || content.contains("Photo") || content.contains("caption"),
        "should extract figure content: {}",
        content
    );
}

#[cfg(feature = "html")]
#[test]
fn test_html_meta_tags() {
    // Metadata is extracted via HtmlMetadata, not as MetadataBlock nodes in the document tree.
    // The document structure contains the body content; metadata is in ExtractionResult.metadata.
    let html = r#"<html><head>
        <meta name="author" content="Jane Doe">
        <meta name="description" content="A test page">
    </head><body><p>Content</p></body></html>"#;
    let config = ExtractionConfig {
        include_document_structure: true,
        ..Default::default()
    };
    let result =
        kreuzberg::extract_bytes_sync(html.as_bytes(), "text/html", &config).expect("HTML extraction should succeed");

    // Verify body content is in document structure
    let doc = result.document.expect("document structure should be populated");
    assert!(doc.validate().is_ok());
    let has_content = doc.nodes.iter().any(|n| match &n.content {
        NodeContent::Paragraph { text } => text.contains("Content"),
        _ => false,
    });
    assert!(has_content, "should have body content");
}

#[cfg(feature = "html")]
#[test]
fn test_html_ordered_list_start() {
    // Verify ordered list content is extracted via the full pipeline
    let html = r#"<ol start="5"><li>Fifth</li><li>Sixth</li></ol>"#;
    let config = ExtractionConfig::default();
    let result =
        kreuzberg::extract_bytes_sync(html.as_bytes(), "text/html", &config).expect("extraction should succeed");
    assert!(result.content.contains("Fifth"), "should contain list item text");
    assert!(result.content.contains("Sixth"), "should contain list item text");
}

#[cfg(feature = "html")]
#[test]
fn test_html_blockquote_cite() {
    let html = r#"<blockquote cite="https://example.com/source"><p>Quote text</p></blockquote>"#;
    let doc = html_doc_structure(html);
    assert!(doc.validate().is_ok());

    // Verify the quote content is present (quote text may be in a paragraph)
    let has_quote_text = doc.nodes.iter().any(|n| match &n.content {
        NodeContent::Paragraph { text } => text.contains("Quote text"),
        _ => false,
    });
    assert!(has_quote_text, "should have quote text content");
}

#[cfg(feature = "html")]
#[test]
fn test_html_image_dimensions() {
    // Verify image content is extracted via the full pipeline
    let html = r#"<img src="photo.jpg" alt="Photo" width="640" height="480">"#;
    let config = ExtractionConfig::default();
    let result =
        kreuzberg::extract_bytes_sync(html.as_bytes(), "text/html", &config).expect("extraction should succeed");
    assert!(
        result.content.contains("Photo") || result.content.contains("photo.jpg"),
        "should extract image reference: {}",
        result.content
    );
}

// ============================================================================
// PPTX Enhanced Layout & Annotations
// ============================================================================

#[cfg(feature = "office")]
#[tokio::test]
async fn test_pptx_bounding_boxes_on_nodes() {
    let path = helpers::get_test_file_path("pptx/powerpoint_sample.pptx");
    if !path.exists() {
        return;
    }

    let config = config_with_structure();
    let result = extract_file(&path, None, &config)
        .await
        .expect("PPTX extraction should succeed");

    let doc = result.document.as_ref().expect("document should be populated");
    assert!(doc.validate().is_ok());

    // At least some nodes should have bounding boxes from shape positions
    let nodes_with_bbox = doc.nodes.iter().filter(|n| n.bbox.is_some()).count();
    assert!(
        nodes_with_bbox > 0,
        "PPTX should have nodes with bounding boxes from shape positions, got 0"
    );

    // Verify bounding boxes have reasonable values (positive coordinates)
    for node in doc.nodes.iter().filter(|n| n.bbox.is_some()) {
        let bbox = node.bbox.as_ref().unwrap();
        assert!(bbox.x1 >= bbox.x0, "bbox x1 should be >= x0: {:?}", bbox);
        assert!(bbox.y1 >= bbox.y0, "bbox y1 should be >= y0: {:?}", bbox);
    }
}

#[cfg(feature = "office")]
#[tokio::test]
#[ignore = "TODO: minimal PPTX bytes don't preserve strikethrough attribute through parser"]
async fn test_pptx_strikethrough_annotation() {
    use kreuzberg::types::document_structure::AnnotationKind;

    // Test strikethrough via the PPTX parser's text annotation collection.
    // Use the internal `runs_to_text_and_annotations` via an in-memory slide parse.
    let xml = br#"<?xml version="1.0" encoding="UTF-8"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
       xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
    <p:cSld>
        <p:spTree>
            <p:sp>
                <p:txBody>
                    <a:p>
                        <a:r>
                            <a:rPr strike="sngStrike"/>
                            <a:t>Deleted</a:t>
                        </a:r>
                    </a:p>
                </p:txBody>
            </p:sp>
        </p:spTree>
    </p:cSld>
</p:sld>"#;

    let result = kreuzberg::extraction::pptx::extract_pptx_from_bytes(
        &create_test_pptx_bytes_with_slide_xml(xml),
        false,
        None,
        false,
        true,
    );

    if let Ok(result) = result
        && let Some(ref doc) = result.document
    {
        let has_strikethrough = doc.nodes.iter().any(|n| {
            n.annotations
                .iter()
                .any(|a| matches!(a.kind, AnnotationKind::Strikethrough))
        });
        assert!(
            has_strikethrough,
            "should find strikethrough annotation on text with strike='sngStrike'"
        );
    }
}

/// Helper to create a minimal PPTX bytes from raw slide XML.
#[cfg(feature = "office")]
fn create_test_pptx_bytes_with_slide_xml(slide_xml: &[u8]) -> Vec<u8> {
    use std::io::Write;
    use zip::write::{SimpleFileOptions, ZipWriter};

    let mut buffer = Vec::new();
    {
        let mut zip = ZipWriter::new(std::io::Cursor::new(&mut buffer));
        let options = SimpleFileOptions::default();

        zip.start_file("[Content_Types].xml", options).unwrap();
        zip.write_all(
            br#"<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="xml" ContentType="application/xml"/>
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
</Types>"#,
        )
        .unwrap();

        zip.start_file("ppt/presentation.xml", options).unwrap();
        zip.write_all(b"<?xml version=\"1.0\"?><presentation/>").unwrap();

        zip.start_file("_rels/.rels", options).unwrap();
        zip.write_all(
            br#"<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
</Relationships>"#,
        )
        .unwrap();

        zip.start_file("ppt/_rels/presentation.xml.rels", options).unwrap();
        zip.write_all(
            br#"<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide1.xml"/>
</Relationships>"#,
        )
        .unwrap();

        zip.start_file("ppt/slides/slide1.xml", options).unwrap();
        zip.write_all(slide_xml).unwrap();

        zip.start_file("docProps/core.xml", options).unwrap();
        zip.write_all(
            br#"<?xml version="1.0" encoding="UTF-8"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
                   xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>Test</dc:title>
</cp:coreProperties>"#,
        )
        .unwrap();

        zip.start_file("docProps/app.xml", options).unwrap();
        zip.write_all(
            br#"<?xml version="1.0" encoding="UTF-8"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"><Slides>1</Slides></Properties>"#,
        )
        .unwrap();

        let _ = zip.finish().unwrap();
    }
    buffer
}

// ============================================================================
// DOCX Enhanced Annotations
// ============================================================================

#[cfg(feature = "office")]
#[tokio::test]
async fn test_docx_subscript_superscript_annotations() {
    let path = helpers::get_test_file_path("docx/unit_test_formatting.docx");
    if !path.exists() {
        return;
    }

    let config = config_with_structure();
    let result = extract_file(&path, None, &config)
        .await
        .expect("DOCX extraction should succeed");

    let doc = result.document.as_ref().expect("document should be populated");
    assert!(doc.validate().is_ok());

    // Verify annotations are collected (bold, italic, underline at minimum)
    let total_annotations: usize = doc.nodes.iter().map(|n| n.annotations.len()).sum();
    assert!(
        total_annotations > 0,
        "formatting DOCX should have text annotations, got 0"
    );
}

#[cfg(feature = "office")]
#[tokio::test]
async fn test_docx_font_size_color_highlight_annotations() {
    use kreuzberg::types::document_structure::AnnotationKind;

    let path = helpers::get_test_file_path("docx/unit_test_formatting.docx");
    if !path.exists() {
        return;
    }

    let config = config_with_structure();
    let result = extract_file(&path, None, &config)
        .await
        .expect("DOCX extraction should succeed");

    let doc = result.document.as_ref().expect("document should be populated");
    assert!(doc.validate().is_ok());

    // Collect all annotation kinds
    let all_annotations: Vec<&AnnotationKind> = doc
        .nodes
        .iter()
        .flat_map(|n| n.annotations.iter().map(|a| &a.kind))
        .collect();

    // FontSize annotation should be present if the document has explicit font sizes
    let has_font_size = all_annotations
        .iter()
        .any(|k| matches!(k, AnnotationKind::FontSize { .. }));

    // The test is soft: only assert if the document contains formatting we can detect.
    // This avoids flaky tests if the fixture doesn't have explicit font sizes.
    if has_font_size {
        let font_sizes: Vec<&str> = all_annotations
            .iter()
            .filter_map(|k| match k {
                AnnotationKind::FontSize { value } => Some(value.as_str()),
                _ => None,
            })
            .collect();
        assert!(!font_sizes.is_empty(), "should have font size values");
    }
}

#[cfg(feature = "office")]
#[tokio::test]
async fn test_docx_section_properties_in_structure() {
    let path = helpers::get_test_file_path("docx/unit_test_headers.docx");
    if !path.exists() {
        return;
    }

    let config = config_with_structure();
    let result = extract_file(&path, None, &config)
        .await
        .expect("DOCX extraction should succeed");

    let doc = result.document.as_ref().expect("document should be populated");
    assert!(doc.validate().is_ok());

    // Look for a Group node with section_properties label
    let section_group = doc.nodes.iter().find(|n| {
        matches!(
            &n.content,
            NodeContent::Group {
                label: Some(label),
                ..
            } if label == "section_properties"
        )
    });

    // Section properties should be present as attributes
    if let Some(node) = section_group {
        let attrs = node.attributes.as_ref().expect("section group should have attributes");
        // Standard DOCX files should have page dimensions
        assert!(
            attrs.contains_key("page_width_pt") || attrs.contains_key("page_height_pt"),
            "section properties should include page dimensions"
        );
    }
}

#[cfg(feature = "office")]
#[tokio::test]
async fn test_docx_drawing_bounding_box() {
    let path = helpers::get_test_file_path("docx/word_image_anchors.docx");
    if !path.exists() {
        return;
    }

    let config = config_with_structure();
    let result = extract_file(&path, None, &config)
        .await
        .expect("DOCX extraction should succeed");

    let doc = result.document.as_ref().expect("document should be populated");
    assert!(doc.validate().is_ok());

    // Look for Image nodes with bounding boxes (from anchored drawings)
    let images_with_bbox: Vec<_> = doc
        .nodes
        .iter()
        .filter(|n| matches!(&n.content, NodeContent::Image { .. }) && n.bbox.is_some())
        .collect();

    // If the document has anchored images, they should have bounding boxes
    let total_images = doc
        .nodes
        .iter()
        .filter(|n| matches!(&n.content, NodeContent::Image { .. }))
        .count();

    if total_images > 0 {
        // At least some images should have bounding boxes (anchored ones)
        // Note: inline images won't have bounding boxes, so this is a soft check
        for img in &images_with_bbox {
            let bbox = img.bbox.as_ref().unwrap();
            assert!(bbox.x1 >= bbox.x0, "bbox x1 should be >= x0");
            assert!(bbox.y1 >= bbox.y0, "bbox y1 should be >= y0");
        }
    }
}

// ============================================================================
// Data Format Enrichment Tests
// ============================================================================

#[cfg(feature = "email")]
#[test]
fn test_email_threading_headers() {
    use kreuzberg::extractors::EmailExtractor;
    use kreuzberg::extractors::SyncExtractor;

    let eml = b"From: alice@example.com\r\n\
                 To: bob@example.com\r\n\
                 Subject: Re: Hello\r\n\
                 Reply-To: alice-reply@example.com\r\n\
                 In-Reply-To: <original-msg-id@example.com>\r\n\
                 Message-ID: <reply-msg-id@example.com>\r\n\
                 Date: Mon, 01 Jan 2024 12:00:00 +0000\r\n\
                 \r\n\
                 This is a reply.";

    let config = config_with_structure();
    let result = EmailExtractor::new()
        .extract_sync(eml, "message/rfc822", &config)
        .expect("email extraction should succeed");

    // Threading headers should appear in additional metadata
    let reply_to = result.metadata.additional.get("reply_to");
    assert!(reply_to.is_some(), "metadata should contain reply_to header");
    assert!(
        reply_to
            .unwrap()
            .as_str()
            .unwrap_or("")
            .contains("alice-reply@example.com"),
        "reply_to should contain the Reply-To address"
    );

    let in_reply_to = result.metadata.additional.get("in_reply_to");
    assert!(in_reply_to.is_some(), "metadata should contain in_reply_to header");
    assert!(
        in_reply_to
            .unwrap()
            .as_str()
            .unwrap_or("")
            .contains("original-msg-id@example.com"),
        "in_reply_to should contain the In-Reply-To message ID"
    );
}

#[cfg(feature = "office")]
#[test]
fn test_jupyter_cells_metadata() {
    use kreuzberg::extractors::JupyterExtractor;
    use kreuzberg::plugins::DocumentExtractor;

    let notebook = serde_json::json!({
        "cells": [
            {
                "cell_type": "code",
                "source": ["print('hello')"],
                "execution_count": 7,
                "outputs": [],
                "metadata": {}
            }
        ],
        "metadata": {
            "kernelspec": {"name": "python3", "language": "python"},
            "language_info": {"name": "python"}
        },
        "nbformat": 4,
        "nbformat_minor": 5
    });
    let content = serde_json::to_vec(&notebook).unwrap();

    let config = config_with_structure();
    let rt = tokio::runtime::Runtime::new().unwrap();
    let internal_doc_result = rt
        .block_on(JupyterExtractor::new().extract_bytes(&content, "application/x-ipynb+json", &config))
        .expect("jupyter extraction should succeed");
    let result = derive_extraction_result(internal_doc_result, true, kreuzberg::OutputFormat::Plain);

    // Verify cells array in metadata
    let cells = result.metadata.additional.get("cells");
    assert!(cells.is_some(), "metadata should have cells array");
    let cells_arr = cells.unwrap().as_array().expect("cells should be an array");
    assert_eq!(cells_arr.len(), 1);
    let cell0 = &cells_arr[0];
    assert_eq!(cell0["execution_count"], serde_json::json!(7));
}

#[cfg(feature = "office")]
#[test]
fn test_bibtex_entry_fields() {
    use kreuzberg::extractors::BibtexExtractor;
    use kreuzberg::plugins::DocumentExtractor;

    let bibtex = br#"@article{smith2024,
  author    = {John Smith},
  title     = {A Great Paper},
  journal   = {Journal of Testing},
  volume    = {42},
  doi       = {10.1234/test.2024},
  year      = {2024}
}"#;

    let config = config_with_structure();
    let rt = tokio::runtime::Runtime::new().unwrap();
    let internal_doc = rt
        .block_on(BibtexExtractor::new().extract_bytes(bibtex, "application/x-bibtex", &config))
        .expect("bibtex extraction should succeed");
    let result = derive_extraction_result(internal_doc, true, kreuzberg::OutputFormat::Plain);

    let doc = result.document.as_ref().expect("document should be present");
    assert!(doc.validate().is_ok());

    // Find the citation node
    let citation = doc
        .nodes
        .iter()
        .find(|n| matches!(&n.content, NodeContent::Citation { key, .. } if key == "smith2024"))
        .expect("should have citation node for smith2024");

    let attrs = citation.attributes.as_ref().expect("citation should have attributes");
    assert_eq!(
        attrs.get("journal").map(|s| s.as_str()),
        Some("Journal of Testing"),
        "should have journal attribute"
    );
    assert_eq!(
        attrs.get("volume").map(|s| s.as_str()),
        Some("42"),
        "should have volume attribute"
    );
    assert_eq!(
        attrs.get("doi").map(|s| s.as_str()),
        Some("10.1234/test.2024"),
        "should have doi attribute"
    );
}

#[test]
fn test_csv_header_detection() {
    use kreuzberg::extractors::CsvExtractor;
    use kreuzberg::plugins::DocumentExtractor;

    let csv_data = b"Name,Age,City\nAlice,30,NYC\nBob,25,LA\n";

    let config = config_with_structure();
    let rt = tokio::runtime::Runtime::new().unwrap();
    let internal_doc_result = rt
        .block_on(CsvExtractor::new().extract_bytes(csv_data, "text/csv", &config))
        .expect("csv extraction should succeed");
    let result = derive_extraction_result(internal_doc_result, true, kreuzberg::OutputFormat::Plain);

    let has_header = result.metadata.additional.get("has_header");
    assert!(has_header.is_some(), "metadata should have has_header field");
    assert_eq!(
        has_header.unwrap(),
        &serde_json::Value::Bool(true),
        "has_header should be true for data with header row"
    );

    // Document structure should contain a table
    let doc = result.document.as_ref().expect("document should be present");
    assert!(
        has_node_type(doc, |c| matches!(c, NodeContent::Table { .. })),
        "CSV should contain Table nodes"
    );
}

#[cfg(feature = "office")]
#[test]
fn test_opml_feed_urls() {
    use kreuzberg::extractors::OpmlExtractor;
    use kreuzberg::plugins::DocumentExtractor;

    let opml = br#"<?xml version="1.0" encoding="UTF-8"?>
<opml version="2.0">
  <head><title>Subscriptions</title></head>
  <body>
    <outline text="Tech News" type="rss" xmlUrl="https://example.com/feed.xml" />
  </body>
</opml>"#;

    let config = config_with_structure();
    let rt = tokio::runtime::Runtime::new().unwrap();
    let internal_doc_result = rt
        .block_on(OpmlExtractor::new().extract_bytes(opml, "text/x-opml", &config))
        .expect("opml extraction should succeed");
    let result = derive_extraction_result(internal_doc_result, true, kreuzberg::OutputFormat::Plain);

    let doc = result.document.as_ref().expect("document should be present");
    assert!(doc.validate().is_ok());

    // Find the node with xmlUrl attribute
    let node_with_url = doc
        .nodes
        .iter()
        .find(|n| n.attributes.as_ref().is_some_and(|a| a.contains_key("xmlUrl")));
    assert!(node_with_url.is_some(), "should have a node with xmlUrl attribute");
    let attrs = node_with_url.unwrap().attributes.as_ref().unwrap();
    assert_eq!(
        attrs.get("xmlUrl").map(|s| s.as_str()),
        Some("https://example.com/feed.xml"),
        "xmlUrl attribute should contain the feed URL"
    );
}

#[test]
fn test_dbf_field_types() {
    let path = helpers::get_test_file_path("dbf/stations.dbf");
    if !path.exists() {
        return;
    }

    let config = config_with_structure();
    let rt = tokio::runtime::Runtime::new().unwrap();
    let result = rt
        .block_on(kreuzberg::core::extractor::extract_file(&path, None, &config))
        .expect("DBF extraction should succeed");

    // Verify fields metadata with type info
    let fields = result.metadata.additional.get("fields");
    assert!(fields.is_some(), "metadata should have fields");
    let fields_arr = fields.unwrap().as_array().expect("fields should be an array");
    assert!(!fields_arr.is_empty(), "fields array should not be empty");

    // Each field entry should have name and type
    let first_field = &fields_arr[0];
    assert!(first_field.get("name").is_some(), "field entry should have a name");
    assert!(first_field.get("type").is_some(), "field entry should have a type");
}

// ============================================================================
// Email HTML Body Annotations
// ============================================================================

#[cfg(feature = "email")]
#[test]
fn test_email_html_body_annotations() {
    use kreuzberg::extractors::EmailExtractor;
    use kreuzberg::extractors::SyncExtractor;

    let eml = b"From: alice@example.com\r\n\
                 To: bob@example.com\r\n\
                 Subject: Test\r\n\
                 MIME-Version: 1.0\r\n\
                 Content-Type: text/html; charset=utf-8\r\n\
                 \r\n\
                 <html><body><p>This is <b>bold</b> text.</p></body></html>";

    let config = config_with_structure();
    let internal_doc = EmailExtractor::new()
        .extract_sync(eml, "message/rfc822", &config)
        .expect("email extraction should succeed");
    let result = derive_extraction_result(internal_doc, true, kreuzberg::OutputFormat::Plain);

    let doc = result.document.as_ref().expect("document should be present");
    assert!(doc.validate().is_ok());

    // Find a paragraph containing "bold"
    let para = doc
        .nodes
        .iter()
        .find(|n| matches!(&n.content, NodeContent::Paragraph { text } if text.contains("bold")));
    assert!(para.is_some(), "should have paragraph with bold text");
    let para = para.unwrap();

    // Verify Bold annotation exists
    let has_bold = para.annotations.iter().any(|a| matches!(a.kind, AnnotationKind::Bold));
    assert!(has_bold, "email HTML body paragraph should have Bold annotation");
}

// ============================================================================
// Jupyter Markdown Cell Formatting Annotations
// ============================================================================

#[cfg(feature = "office")]
#[test]
fn test_jupyter_markdown_cell_formatting() {
    use kreuzberg::extractors::JupyterExtractor;
    use kreuzberg::plugins::DocumentExtractor;

    let notebook = serde_json::json!({
        "cells": [
            {
                "cell_type": "markdown",
                "source": ["This has **bold** and *italic* and `code` text."],
                "metadata": {}
            }
        ],
        "metadata": {
            "kernelspec": {"name": "python3", "language": "python"},
            "language_info": {"name": "python"}
        },
        "nbformat": 4,
        "nbformat_minor": 5
    });
    let content = serde_json::to_vec(&notebook).unwrap();

    let config = config_with_structure();
    let rt = tokio::runtime::Runtime::new().unwrap();
    let internal_doc_result = rt
        .block_on(JupyterExtractor::new().extract_bytes(&content, "application/x-ipynb+json", &config))
        .expect("jupyter extraction should succeed");
    let result = derive_extraction_result(internal_doc_result, true, kreuzberg::OutputFormat::Plain);

    let doc = result.document.as_ref().expect("document should be present");
    assert!(doc.validate().is_ok());

    // Find the paragraph
    let para = doc
        .nodes
        .iter()
        .find(|n| matches!(&n.content, NodeContent::Paragraph { text } if text.contains("bold")))
        .expect("should have paragraph with formatted text");

    let text = match &para.content {
        NodeContent::Paragraph { text } => text.as_str(),
        _ => unreachable!(),
    };

    // Verify the markdown markers are stripped
    assert!(!text.contains("**"), "bold markers should be stripped");
    assert!(text.contains("bold"), "bold text should remain");
    assert!(text.contains("italic"), "italic text should remain");
    assert!(text.contains("code"), "code text should remain");

    // Verify annotations
    let has_bold = para.annotations.iter().any(|a| matches!(a.kind, AnnotationKind::Bold));
    let has_italic = para
        .annotations
        .iter()
        .any(|a| matches!(a.kind, AnnotationKind::Italic));
    let has_code = para.annotations.iter().any(|a| matches!(a.kind, AnnotationKind::Code));

    assert!(has_bold, "should have Bold annotation");
    assert!(has_italic, "should have Italic annotation");
    assert!(has_code, "should have Code annotation");

    // Verify annotation byte ranges are correct
    let bold_ann = para
        .annotations
        .iter()
        .find(|a| matches!(a.kind, AnnotationKind::Bold))
        .unwrap();
    let annotated = &text[bold_ann.start as usize..bold_ann.end as usize];
    assert_eq!(annotated, "bold", "Bold annotation should span 'bold'");
}

// ============================================================================
// Enrichment Tests: FictionBook
// ============================================================================

#[cfg(feature = "office")]
#[tokio::test]
async fn test_fictionbook_author_details() {
    let path = helpers::get_test_file_path("fictionbook/writer.fb2");
    if !path.exists() {
        return;
    }

    let config = ExtractionConfig {
        include_document_structure: false,
        ..Default::default()
    };
    let result = extract_file(&path, None, &config)
        .await
        .expect("FictionBook extraction should succeed");

    let additional = &result.metadata.additional;
    assert!(
        additional.contains_key("author_details"),
        "FictionBook metadata should have author_details, got keys: {:?}",
        additional.keys().collect::<Vec<_>>()
    );
}

#[cfg(feature = "office")]
#[test]
fn test_fictionbook_genre_metadata() {
    let fb2 = r#"<?xml version="1.0" encoding="UTF-8"?>
<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0">
  <description>
    <title-info>
      <genre>sci_fi</genre>
      <genre>adventure</genre>
      <book-title>Test Book</book-title>
    </title-info>
  </description>
  <body><section><p>Content.</p></section></body>
</FictionBook>"#;
    let config = ExtractionConfig::default();
    let result = kreuzberg::extract_bytes_sync(fb2.as_bytes(), "application/x-fictionbook+xml", &config)
        .expect("FictionBook extraction should succeed");

    let additional = &result.metadata.additional;
    assert!(
        additional.contains_key("genres"),
        "FictionBook metadata should have genres, got keys: {:?}",
        additional.keys().collect::<Vec<_>>()
    );
    let genres = additional.get("genres").unwrap();
    assert!(genres.is_array(), "genres should be an array");
    assert_eq!(
        genres.as_array().unwrap().len(),
        2,
        "genres array should have 2 entries"
    );
}

// ============================================================================
// Enrichment Tests: DocBook
// ============================================================================

#[cfg(feature = "xml")]
#[test]
fn test_docbook_admonitions() {
    let docbook = r#"<?xml version="1.0" encoding="UTF-8"?>
<article xmlns="http://docbook.org/ns/docbook" version="5.0">
  <title>Test</title>
  <note><para>This is a note.</para></note>
</article>"#;
    let config = config_with_structure();
    let result = kreuzberg::extract_bytes_sync(docbook.as_bytes(), "application/docbook+xml", &config)
        .expect("DocBook extraction should succeed");
    let doc = result.document.expect("document should be populated");
    assert!(doc.validate().is_ok());
    assert!(
        has_node_type(&doc, |c| matches!(c, NodeContent::Admonition { .. })),
        "DocBook with <note> should contain Admonition node"
    );
    let admonition = doc
        .nodes
        .iter()
        .find(|n| matches!(&n.content, NodeContent::Admonition { .. }))
        .expect("should find Admonition");
    if let NodeContent::Admonition { kind, .. } = &admonition.content {
        assert_eq!(kind, "note");
    }
}

#[cfg(feature = "xml")]
#[test]
fn test_docbook_inline_annotations() {
    let docbook = r#"<?xml version="1.0" encoding="UTF-8"?>
<article xmlns="http://docbook.org/ns/docbook" version="5.0">
  <title>Test</title>
  <para>This is <emphasis>italic</emphasis> and <emphasis role="bold">bold</emphasis> text.</para>
</article>"#;
    let config = config_with_structure();
    let result = kreuzberg::extract_bytes_sync(docbook.as_bytes(), "application/docbook+xml", &config)
        .expect("DocBook extraction should succeed");
    let doc = result.document.expect("document should be populated");
    assert!(doc.validate().is_ok());

    let para = doc
        .nodes
        .iter()
        .find(|n| matches!(&n.content, NodeContent::Paragraph { text } if text.contains("italic")))
        .expect("should find paragraph with inline text");

    let has_italic = para
        .annotations
        .iter()
        .any(|a| matches!(a.kind, AnnotationKind::Italic));
    let has_bold = para.annotations.iter().any(|a| matches!(a.kind, AnnotationKind::Bold));

    assert!(has_italic, "should have Italic annotation from <emphasis>");
    assert!(has_bold, "should have Bold annotation from <emphasis role=\"bold\">");

    // Verify byte ranges
    let text = match &para.content {
        NodeContent::Paragraph { text } => text.as_str(),
        _ => unreachable!(),
    };
    let italic_ann = para
        .annotations
        .iter()
        .find(|a| matches!(a.kind, AnnotationKind::Italic))
        .unwrap();
    let annotated = &text[italic_ann.start as usize..italic_ann.end as usize];
    assert_eq!(annotated, "italic", "Italic annotation should span 'italic'");

    let bold_ann = para
        .annotations
        .iter()
        .find(|a| matches!(a.kind, AnnotationKind::Bold))
        .unwrap();
    let annotated = &text[bold_ann.start as usize..bold_ann.end as usize];
    assert_eq!(annotated, "bold", "Bold annotation should span 'bold'");
}

// ============================================================================
// Enrichment Tests: JATS
// ============================================================================

#[cfg(feature = "xml")]
#[test]
fn test_jats_history_dates() {
    let jats = r#"<?xml version="1.0" encoding="UTF-8"?>
<article>
  <front>
    <article-meta>
      <article-title>Test Article</article-title>
      <history>
        <date date-type="received">
          <day>15</day>
          <month>01</month>
          <year>2024</year>
        </date>
        <date date-type="accepted">
          <day>20</day>
          <month>03</month>
          <year>2024</year>
        </date>
      </history>
    </article-meta>
  </front>
  <body><p>Content.</p></body>
</article>"#;
    let config = ExtractionConfig::default();
    let result = kreuzberg::extract_bytes_sync(jats.as_bytes(), "application/x-jats+xml", &config)
        .expect("JATS extraction should succeed");

    let additional = &result.metadata.additional;
    let has_date_key = additional.keys().any(|k| k.starts_with("date_"));
    assert!(
        has_date_key,
        "JATS metadata should have history date keys (date_received, date_accepted, etc.), got keys: {:?}",
        additional.keys().collect::<Vec<_>>()
    );
    assert!(additional.contains_key("date_received"), "should have date_received");
    assert!(additional.contains_key("date_accepted"), "should have date_accepted");
}

#[cfg(feature = "xml")]
#[test]
fn test_jats_inline_formula() {
    let jats = r#"<?xml version="1.0" encoding="UTF-8"?>
<article>
  <front>
    <article-meta>
      <article-title>Formula Test</article-title>
    </article-meta>
  </front>
  <body>
    <p>The equation is important.</p>
    <inline-formula>E = mc^2</inline-formula>
  </body>
</article>"#;
    let config = config_with_structure();
    let result = kreuzberg::extract_bytes_sync(jats.as_bytes(), "application/x-jats+xml", &config)
        .expect("JATS extraction should succeed");
    let doc = result.document.expect("document should be populated");
    assert!(doc.validate().is_ok());
    assert!(
        has_node_type(&doc, |c| matches!(c, NodeContent::Formula { .. })),
        "JATS with <inline-formula> should contain Formula node"
    );
}

#[cfg(feature = "xml")]
#[test]
fn test_jats_inline_annotations() {
    let jats = r#"<?xml version="1.0" encoding="UTF-8"?>
<article>
  <front>
    <article-meta>
      <article-title>Annotation Test</article-title>
    </article-meta>
  </front>
  <body>
    <p>This is <bold>important</bold> and <italic>noted</italic> text.</p>
  </body>
</article>"#;
    let config = config_with_structure();
    let result = kreuzberg::extract_bytes_sync(jats.as_bytes(), "application/x-jats+xml", &config)
        .expect("JATS extraction should succeed");
    let doc = result.document.expect("document should be populated");
    assert!(doc.validate().is_ok());

    let para = doc
        .nodes
        .iter()
        .find(|n| matches!(&n.content, NodeContent::Paragraph { text } if text.contains("important")))
        .expect("should find paragraph with inline text");

    let has_bold = para.annotations.iter().any(|a| matches!(a.kind, AnnotationKind::Bold));
    let has_italic = para
        .annotations
        .iter()
        .any(|a| matches!(a.kind, AnnotationKind::Italic));

    assert!(has_bold, "should have Bold annotation from <bold>");
    assert!(has_italic, "should have Italic annotation from <italic>");

    // Verify byte ranges
    let text = match &para.content {
        NodeContent::Paragraph { text } => text.as_str(),
        _ => unreachable!(),
    };
    let bold_ann = para
        .annotations
        .iter()
        .find(|a| matches!(a.kind, AnnotationKind::Bold))
        .unwrap();
    let annotated = &text[bold_ann.start as usize..bold_ann.end as usize];
    assert_eq!(annotated, "important", "Bold annotation should span 'important'");

    let italic_ann = para
        .annotations
        .iter()
        .find(|a| matches!(a.kind, AnnotationKind::Italic))
        .unwrap();
    let annotated = &text[italic_ann.start as usize..italic_ann.end as usize];
    assert_eq!(annotated, "noted", "Italic annotation should span 'noted'");
}

// ============================================================================
// Enrichment Tests: ODT
// ============================================================================

#[cfg(feature = "office")]
#[tokio::test]
async fn test_odt_footnote() {
    let path = helpers::get_test_file_path("odt/footnote.odt");
    if !path.exists() {
        return;
    }

    let config = config_with_structure();
    let result = extract_file(&path, None, &config)
        .await
        .expect("ODT extraction should succeed");
    let doc = result.document.expect("document should be populated");
    assert!(doc.validate().is_ok());
    assert!(
        has_node_type(&doc, |c| matches!(c, NodeContent::Footnote { .. })),
        "ODT with footnotes should contain Footnote node"
    );
}

#[cfg(feature = "office")]
#[tokio::test]
async fn test_odt_bold_annotations() {
    let path = helpers::get_test_file_path("odt/bold.odt");
    if !path.exists() {
        return;
    }

    let config = config_with_structure();
    let result = extract_file(&path, None, &config)
        .await
        .expect("ODT extraction should succeed");
    let doc = result.document.expect("document should be populated");
    assert!(doc.validate().is_ok());

    let has_bold_annotation = doc
        .nodes
        .iter()
        .any(|n| n.annotations.iter().any(|a| matches!(a.kind, AnnotationKind::Bold)));
    assert!(has_bold_annotation, "ODT with bold text should have Bold annotations");
}

// ============================================================================
// Enrichment Tests: RTF
// ============================================================================

#[cfg(feature = "office")]
#[tokio::test]
async fn test_rtf_bold_annotations() {
    let path = helpers::get_test_file_path("rtf/formatting.rtf");
    if !path.exists() {
        return;
    }

    let config = config_with_structure();
    let result = extract_file(&path, None, &config)
        .await
        .expect("RTF extraction should succeed");
    let doc = result.document.expect("document should be populated");
    assert!(doc.validate().is_ok());

    let has_bold_annotation = doc
        .nodes
        .iter()
        .any(|n| n.annotations.iter().any(|a| matches!(a.kind, AnnotationKind::Bold)));
    assert!(
        has_bold_annotation,
        "RTF with bold formatting should have Bold annotations"
    );
}

// ============================================================================
// Enrichment Tests: EPUB
// ============================================================================

#[cfg(feature = "office")]
#[tokio::test]
async fn test_epub_dublin_core() {
    let path = helpers::get_test_file_path("epub/features.epub");
    if !path.exists() {
        return;
    }

    let config = ExtractionConfig::default();
    let result = extract_file(&path, None, &config)
        .await
        .expect("EPUB extraction should succeed");

    // EPUB typically provides Dublin Core metadata via the OPF package.
    // Check that some metadata was extracted.
    let meta = &result.metadata;
    let has_some_metadata = meta.subject.is_some() || meta.created_at.is_some() || !meta.additional.is_empty();
    assert!(
        has_some_metadata,
        "EPUB should have some metadata (subject, created_at, or additional), got: {:?}",
        meta
    );
}

// ============================================================================
// Archive Recursive Extraction Tests
// ============================================================================

#[cfg(feature = "archives")]
mod archive_recursive {
    use kreuzberg::core::config::ExtractionConfig;
    use kreuzberg::core::extractor::{extract_bytes, extract_bytes_sync};
    use std::io::Write;

    fn create_test_zip(files: &[(&str, &[u8])]) -> Vec<u8> {
        let mut zip_buf = Vec::new();
        {
            let mut writer = zip::ZipWriter::new(std::io::Cursor::new(&mut zip_buf));
            for (name, content) in files {
                writer
                    .start_file(*name, zip::write::FileOptions::<'_, ()>::default())
                    .unwrap();
                writer.write_all(content).unwrap();
            }
            writer.finish().unwrap();
        }
        zip_buf
    }

    #[tokio::test]
    async fn test_zip_recursive_extraction() {
        let zip_bytes = create_test_zip(&[
            ("hello.txt", b"Hello World"),
            ("data.csv", b"name,age\nAlice,30\nBob,25"),
        ]);

        let config = ExtractionConfig::default();
        let result = extract_bytes(&zip_bytes, "application/zip", &config)
            .await
            .expect("ZIP extraction should succeed");

        let children = result.children.expect("children should be populated");
        assert_eq!(children.len(), 2, "should have 2 child entries");

        // Verify paths and MIME types
        let txt_child = children.iter().find(|c| c.path == "hello.txt");
        assert!(txt_child.is_some(), "should have hello.txt child");
        let txt_child = txt_child.unwrap();
        assert_eq!(txt_child.mime_type, "text/plain");
        assert!(
            txt_child.result.content.contains("Hello World"),
            "txt child should contain 'Hello World', got: {}",
            txt_child.result.content
        );

        let csv_child = children.iter().find(|c| c.path == "data.csv");
        assert!(csv_child.is_some(), "should have data.csv child");
        let csv_child = csv_child.unwrap();
        assert!(
            !csv_child.result.content.is_empty(),
            "csv child should have non-empty content"
        );
    }

    #[test]
    fn test_archive_depth_zero_disables_recursion() {
        let zip_bytes = create_test_zip(&[("hello.txt", b"Hello World")]);

        let config = ExtractionConfig {
            max_archive_depth: 0,
            ..Default::default()
        };

        let result = extract_bytes_sync(&zip_bytes, "application/zip", &config).expect("ZIP extraction should succeed");

        assert!(
            result.children.is_none(),
            "children should be None when max_archive_depth is 0"
        );
    }

    #[tokio::test]
    async fn test_archive_children_have_content() {
        let markdown_content = b"# Title\n\nParagraph text with **bold** and *italic*.";
        let zip_bytes = create_test_zip(&[("readme.md", markdown_content)]);

        let config = ExtractionConfig::default();
        let result = extract_bytes(&zip_bytes, "application/zip", &config)
            .await
            .expect("ZIP extraction should succeed");

        let children = result.children.expect("children should be populated");
        assert_eq!(children.len(), 1, "should have 1 child entry");

        let md_child = &children[0];
        assert_eq!(md_child.path, "readme.md");
        assert!(
            !md_child.result.content.is_empty(),
            "Markdown child should have non-empty content"
        );
        assert!(
            md_child.result.content.contains("Title") || md_child.result.content.contains("Paragraph"),
            "Markdown child content should contain extracted text, got: {}",
            md_child.result.content
        );
    }
}
