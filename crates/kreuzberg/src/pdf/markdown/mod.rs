//! PDF-to-Markdown renderer using segment-level font analysis.
//!
//! Converts PDF documents into structured markdown by analyzing pdfium text segments
//! (pre-merged character runs sharing baseline + font settings) to reconstruct headings,
//! paragraphs, inline formatting, and list items.

mod assembly;
mod bridge;
mod classify;
mod columns;
mod constants;
pub(crate) mod layout_classify;
mod lines;
mod paragraphs;
mod pipeline;
mod regions;
mod render;
pub(crate) mod types;

pub(crate) use pipeline::render_document_as_markdown_with_tables;
pub use render::inject_image_placeholders;
