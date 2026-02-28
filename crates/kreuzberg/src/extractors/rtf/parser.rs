//! Core RTF parsing logic.

use crate::extractors::rtf::encoding::{decode_windows_1252, parse_hex_byte, parse_rtf_control_word};
use crate::extractors::rtf::formatting::normalize_whitespace;
use crate::extractors::rtf::images::extract_image_metadata;
use crate::extractors::rtf::tables::TableState;
use crate::types::Table;

/// Known RTF destination groups whose content should be skipped entirely.
///
/// These are groups that start with a control word and contain metadata,
/// font tables, style sheets, or binary data — not document body text.
const SKIP_DESTINATIONS: &[&str] = &[
    "fonttbl",
    "colortbl",
    "stylesheet",
    "info",
    "listtable",
    "listoverridetable",
    "generator",
    "filetbl",
    "revtbl",
    "rsidtbl",
    "xmlnstbl",
    "mmathPr",
    "themedata",
    "colorschememapping",
    "datastore",
    "latentstyles",
    "datafield",
    "fldinst",
    "objdata",
    "objclass",
    "panose",
    "bkmkstart",
    "bkmkend",
    "field",
    "wgrffmtfilter",
    "fcharset",
    "pgdsctbl",
];

/// Extract text and image metadata from RTF document.
///
/// This function extracts plain text from an RTF document by:
/// 1. Tracking group nesting depth with a state stack
/// 2. Skipping known destination groups (fonttbl, stylesheet, info, etc.)
/// 3. Skipping `{\*\...}` ignorable destination groups
/// 4. Converting encoded characters to Unicode
/// 5. Extracting text while skipping formatting groups
/// 6. Detecting and extracting image metadata (\pict sections)
/// 7. Normalizing whitespace
pub fn extract_text_from_rtf(content: &str) -> (String, Vec<Table>) {
    let mut result = String::new();
    let mut chars = content.chars().peekable();
    let mut tables: Vec<Table> = Vec::new();
    let mut table_state: Option<TableState> = None;

    // Group state stack: each entry tracks whether the group should be skipped.
    // When skip_depth > 0, all content is suppressed until we return to the
    // enclosing depth.
    let mut group_depth: i32 = 0;
    let mut skip_depth: i32 = 0; // 0 = not skipping; >0 = skip until depth drops below this

    // Track whether the next group is an ignorable destination (\*)
    let mut ignorable_pending = false;
    // Track whether we just entered a new group and the first control word decides skip
    let mut expect_destination = false;

    let ensure_table = |table_state: &mut Option<TableState>| {
        if table_state.is_none() {
            *table_state = Some(TableState::new());
        }
    };

    let finalize_table = |state_opt: &mut Option<TableState>, tables: &mut Vec<Table>| {
        if let Some(state) = state_opt.take()
            && let Some(table) = state.finalize()
        {
            tables.push(table);
        }
    };

    while let Some(ch) = chars.next() {
        match ch {
            '{' => {
                group_depth += 1;
                expect_destination = true;
                // If we're already skipping, just track depth
            }
            '}' => {
                group_depth -= 1;
                expect_destination = false;
                ignorable_pending = false;
                // If we were skipping and just exited the skipped group, stop skipping
                if skip_depth > 0 && group_depth < skip_depth {
                    skip_depth = 0;
                }
                // Add space at group boundary (only when not skipping)
                if skip_depth == 0 && !result.is_empty() && !result.ends_with(' ') && !result.ends_with('\n') {
                    result.push(' ');
                }
            }
            '\\' => {
                if let Some(&next_ch) = chars.peek() {
                    match next_ch {
                        '\\' | '{' | '}' => {
                            chars.next();
                            expect_destination = false;
                            if skip_depth > 0 {
                                continue;
                            }
                            result.push(next_ch);
                        }
                        '\'' => {
                            chars.next();
                            expect_destination = false;
                            let hex1 = chars.next();
                            let hex2 = chars.next();
                            if skip_depth > 0 {
                                continue;
                            }
                            if let (Some(h1), Some(h2)) = (hex1, hex2)
                                && let Some(byte) = parse_hex_byte(h1, h2)
                            {
                                let decoded = decode_windows_1252(byte);
                                result.push(decoded);
                                if let Some(state) = table_state.as_mut()
                                    && state.in_row
                                {
                                    state.current_cell.push(decoded);
                                }
                            }
                        }
                        '*' => {
                            chars.next();
                            // \* marks an ignorable destination — skip the entire group
                            // if we don't recognize the keyword
                            ignorable_pending = true;
                        }
                        _ => {
                            let (control_word, _param) = parse_rtf_control_word(&mut chars);

                            // Check if this control word starts a destination to skip
                            if expect_destination || ignorable_pending {
                                expect_destination = false;

                                if ignorable_pending {
                                    // \* destination: skip entire group unless we specifically handle it
                                    ignorable_pending = false;
                                    if skip_depth == 0 {
                                        skip_depth = group_depth;
                                    }
                                    continue;
                                }

                                if SKIP_DESTINATIONS.contains(&control_word.as_str()) {
                                    if skip_depth == 0 {
                                        skip_depth = group_depth;
                                    }
                                    continue;
                                }
                            }

                            if skip_depth > 0 {
                                continue;
                            }

                            handle_control_word(
                                &control_word,
                                _param,
                                &mut chars,
                                &mut result,
                                &mut table_state,
                                &mut tables,
                                &ensure_table,
                                &finalize_table,
                            );
                        }
                    }
                }
            }
            '\n' | '\r' => {
                // RTF line breaks in the source are not significant
            }
            ' ' | '\t' => {
                if skip_depth > 0 {
                    continue;
                }
                if !result.is_empty() && !result.ends_with(' ') && !result.ends_with('\n') {
                    result.push(' ');
                }
                if let Some(state) = table_state.as_mut()
                    && state.in_row
                    && !state.current_cell.ends_with(' ')
                {
                    state.current_cell.push(' ');
                }
            }
            _ => {
                expect_destination = false;
                if skip_depth > 0 {
                    continue;
                }
                if let Some(state) = table_state.as_ref()
                    && !state.in_row
                    && !state.rows.is_empty()
                {
                    finalize_table(&mut table_state, &mut tables);
                }
                result.push(ch);
                if let Some(state) = table_state.as_mut()
                    && state.in_row
                {
                    state.current_cell.push(ch);
                }
            }
        }
    }

    if table_state.is_some() {
        finalize_table(&mut table_state, &mut tables);
    }

    (normalize_whitespace(&result), tables)
}

/// Handle an RTF control word during parsing.
#[allow(clippy::too_many_arguments)]
fn handle_control_word(
    control_word: &str,
    param: Option<i32>,
    chars: &mut std::iter::Peekable<std::str::Chars>,
    result: &mut String,
    table_state: &mut Option<TableState>,
    tables: &mut Vec<Table>,
    ensure_table: &dyn Fn(&mut Option<TableState>),
    finalize_table: &dyn Fn(&mut Option<TableState>, &mut Vec<Table>),
) {
    match control_word {
        // Unicode escape: \u1234 (signed integer)
        "u" => {
            if let Some(code_num) = param {
                let code_u = if code_num < 0 {
                    (code_num + 65536) as u32
                } else {
                    code_num as u32
                };
                if let Some(c) = char::from_u32(code_u) {
                    result.push(c);
                    if let Some(state) = table_state.as_mut()
                        && state.in_row
                    {
                        state.current_cell.push(c);
                    }
                }
                // Skip the replacement character (usually `?` or next byte)
                if let Some(&next) = chars.peek() {
                    if next != '\\' && next != '{' && next != '}' {
                        chars.next();
                    }
                }
            }
        }
        "pict" => {
            let image_metadata = extract_image_metadata(chars);
            if !image_metadata.is_empty() {
                result.push('!');
                result.push('[');
                result.push_str("image");
                result.push(']');
                result.push('(');
                result.push_str(&image_metadata);
                result.push(')');
                result.push(' ');
                if let Some(state) = table_state.as_mut()
                    && state.in_row
                {
                    state.current_cell.push('!');
                    state.current_cell.push('[');
                    state.current_cell.push_str("image");
                    state.current_cell.push(']');
                    state.current_cell.push('(');
                    state.current_cell.push_str(&image_metadata);
                    state.current_cell.push(')');
                    state.current_cell.push(' ');
                }
            }
        }
        "par" | "line" => {
            if table_state.is_some() {
                finalize_table(table_state, tables);
            }
            if !result.is_empty() && !result.ends_with('\n') {
                result.push('\n');
                result.push('\n');
            }
        }
        "tab" => {
            result.push('\t');
            if let Some(state) = table_state.as_mut()
                && state.in_row
            {
                state.current_cell.push('\t');
            }
        }
        "bullet" => {
            result.push('\u{2022}');
        }
        "lquote" => {
            result.push('\u{2018}');
        }
        "rquote" => {
            result.push('\u{2019}');
        }
        "ldblquote" => {
            result.push('\u{201C}');
        }
        "rdblquote" => {
            result.push('\u{201D}');
        }
        "endash" => {
            result.push('\u{2013}');
        }
        "emdash" => {
            result.push('\u{2014}');
        }
        "trowd" => {
            ensure_table(table_state);
            if let Some(state) = table_state.as_mut() {
                state.start_row();
            }
            if !result.is_empty() && !result.ends_with('\n') {
                result.push('\n');
            }
            if !result.ends_with('|') {
                result.push('|');
                result.push(' ');
            }
        }
        "cell" => {
            if !result.ends_with('|') {
                if !result.ends_with(' ') && !result.is_empty() {
                    result.push(' ');
                }
                result.push('|');
            }
            if !result.ends_with(' ') {
                result.push(' ');
            }
        }
        "row" => {
            ensure_table(table_state);
            if let Some(state) = table_state.as_mut()
                && (state.in_row || !state.current_cell.is_empty())
            {
                state.push_row();
            }
            if !result.ends_with('|') {
                result.push('|');
            }
            if !result.ends_with('\n') {
                result.push('\n');
            }
        }
        _ => {}
    }
}
