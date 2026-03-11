pub mod tsv_parser;

// Re-export table utilities from the non-ocr-gated module
pub use crate::pdf::table_reconstruct::{HocrWord, post_process_table, reconstruct_table, table_to_markdown};
pub use tsv_parser::extract_words_from_tsv;
