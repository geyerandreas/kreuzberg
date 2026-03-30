//! Unified rendering of document content to output formats.
//!
//! ## New API (`InternalDocument`-based)
//!
//! - [`render_markdown`] — CommonMark Markdown
//! - [`render_djot`] — Djot markup
//! - [`render_html`] — Direct HTML
//! - [`render_plain`] — Plain text (no formatting)
//!
//! ## Legacy API (`DocumentStructure`-based) — deprecated
//!
//! - [`render_to_markdown`] — Old tree-based Markdown renderer
//! - [`render_to_plain`] — Old tree-based plain text renderer

pub(crate) mod common;
mod djot;
mod html;
#[allow(clippy::module_inception)]
mod markdown;
mod new_markdown;
mod new_plain;
mod plain;

// New InternalDocument-based renderers
pub use djot::render_djot;
pub use html::render_html;
pub use new_markdown::render_markdown;
pub use new_plain::render_plain;

// Legacy DocumentStructure-based renderers (deprecated)
#[deprecated(note = "Use render_markdown(doc: &InternalDocument) instead")]
pub use markdown::render_to_markdown;
#[deprecated(note = "Use render_plain(doc: &InternalDocument) instead")]
pub use plain::render_to_plain;
