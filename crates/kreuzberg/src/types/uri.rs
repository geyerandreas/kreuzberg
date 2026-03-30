//! URI/link types discovered during document extraction.

use serde::{Deserialize, Serialize};

/// A URI/link discovered during document extraction.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "api", derive(utoipa::ToSchema))]
pub struct Uri {
    /// The URL string.
    pub url: String,
    /// Optional display label/text for the link.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub label: Option<String>,
    /// Page where this URI was found (1-indexed).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub page: Option<u32>,
    /// The kind of URI.
    pub kind: UriKind,
}

/// Classification of a discovered URI.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "api", derive(utoipa::ToSchema))]
#[serde(rename_all = "snake_case")]
pub enum UriKind {
    /// Standard hyperlink (<a href>, \href, etc.)
    Hyperlink,
    /// Image reference (src, \includegraphics, etc.)
    Image,
    /// Internal anchor/bookmark reference.
    Anchor,
    /// Academic citation (DOI, arXiv, etc.)
    Citation,
    /// Cross-reference within document.
    Reference,
    /// Email address (mailto:).
    Email,
}
