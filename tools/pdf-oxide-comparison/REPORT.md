# pdf_oxide vs Kreuzberg (pdfium) — Evaluation Report

**Date:** 2026-03-01
**pdf_oxide version:** 0.3.11 (pure Rust)
**Kreuzberg version:** 4.4.1 (pdfium-render FFI)
**Platform:** macOS Darwin 25.3.0, Apple Silicon (aarch64), release mode
**Test corpus:** 18 curated PDFs with text layers from `test_documents/pdf/`

---

## Executive Summary

pdf_oxide is **2–12x faster** than kreuzberg's pdfium backend for text extraction. However, it has **significant text quality issues** that make it unsuitable as a drop-in replacement:

- **Word spacing defects** — words frequently merged together ("introducesDocling", "destinationmachine")
- **Encoding failures** — complete extraction failure on some font encodings (Google Docs exports, tiny.pdf)
- **RTL text reversal** — Arabic text extracted in reverse character order
- **Reading order corruption** — multi-column and slide layouts scrambled
- **Markdown over-segmentation** — headings aggressively over-detected, paragraphs fragmented

Kreuzberg (pdfium) produces consistently cleaner, more usable text across all document types tested, with the notable exception of one German-language PDF where pdfium had encoding issues that pdf_oxide handled correctly.

---

## 1. Speed Benchmark

20 iterations per file, release mode, with 2-iteration warmup.

| File | Kreuzberg | pdf_oxide | Speedup |
|------|-----------|-----------|---------|
| docling.pdf | 106.43ms | 8.63ms | **12.3x** |
| fake_memo.pdf | 253us | 88us | 2.9x |
| google_doc_document.pdf | 1.22ms | 751us | 1.6x |
| code_and_formula.pdf | 2.64ms | 727us | 3.6x |
| sample_contract.pdf | 7.54ms | 1.52ms | 5.0x |
| test_article.pdf | 23.04ms | 7.69ms | 3.0x |
| searchable.pdf | 1.09ms | 278us | 3.9x |
| multi_page.pdf | 4.39ms | 964us | 4.6x |
| right_to_left_01.pdf | 1.69ms | 360us | 4.7x |
| non_ascii_text.pdf | 27.52ms | 17.78ms | 1.5x |
| copy_protected.pdf | 6.29ms | 1.25ms | 5.0x |
| perfect_hash_functions_slides.pdf | 1.71ms | 383us | 4.5x |
| the_hideous_name_1985_pike85hideous.pdf | 5.86ms | 1.17ms | 5.0x |
| program_design_in_the_unix_environment.pdf | 5.21ms | 2.46ms | 2.1x |
| 5_level_paging (Intel spec) | 16.37ms | 4.50ms | 3.6x |
| scanned.pdf | 1.91ms | 877us | 2.2x |
| tiny.pdf | 291us | 154us | 1.9x |
| large.pdf | 12.83ms | 6.39ms | 2.0x |

| Metric | Kreuzberg | pdf_oxide |
|--------|-----------|-----------|
| **Average per file** | 12.57ms | 3.11ms |
| **Overall speedup** | — | **4.0x** |
| **Range** | — | 1.5x – 12.3x |

**Verdict:** pdf_oxide is consistently faster. The speedup is real and significant — averaging 4x across our test corpus. The biggest win is on docling.pdf (12.3x), likely due to its structure tree which pdfium processes more carefully.

---

## 2. Text Extraction Correctness

### 2.1 Quantitative Summary

| File | K-words | O-words | Jaccard | Notes |
|------|---------|---------|---------|-------|
| docling.pdf | 2,567 | 2,772 | 76.2% | Word merging in pdf_oxide |
| fake_memo.pdf | 34 | 34 | **100.0%** | Perfect match |
| google_doc_document.pdf | 121 | 99 | **1.4%** | pdf_oxide: complete encoding failure |
| code_and_formula.pdf | 118 | 122 | 84.6% | Minor differences |
| sample_contract.pdf | 1,376 | 1,488 | 86.6% | Word splitting in pdf_oxide |
| test_article.pdf | 3,838 | 3,795 | 94.4% | Good agreement |
| searchable.pdf | 223 | 224 | **99.6%** | Near-perfect |
| multi_page.pdf | 676 | 679 | 85.6% | Reading order issues in pdf_oxide |
| right_to_left_01.pdf | 163 | 161 | **1.6%** | pdf_oxide: reversed RTL characters |
| non_ascii_text.pdf | 2,818 | 1,535 | **4.1%** | Encoding differences (see §2.3) |
| copy_protected.pdf | 430 | 439 | 79.5% | |
| perfect_hash_functions_slides.pdf | 264 | 256 | 75.1% | Slide layout scrambled in pdf_oxide |
| the_hideous_name.pdf | 1,523 | 1,601 | 73.8% | Word merging in pdf_oxide |
| program_design_unix.pdf | 1,331 | 1,427 | 75.3% | |
| 5_level_paging (Intel) | 1,534 | 1,726 | 76.5% | |
| scanned.pdf | 361 | 368 | 93.9% | Good agreement |
| tiny.pdf | 29 | 1 | **0.0%** | pdf_oxide: complete encoding failure |
| large.pdf | 2,093 | 2,240 | 77.4% | |

**Average Jaccard:** 65.5% across 18 files.

### 2.2 Critical Failures in pdf_oxide

#### Complete encoding failures (Jaccard < 5%)

**google_doc_document.pdf (1.4%):** pdf_oxide extracts 4 lines of garbled text:
```
20201 estimateBESCFSRSAEUITANAINFCACJBVPVCR-Pnfa a8lhriexiplrlseaoenoaoau28at...
```
Kreuzberg extracts the full document correctly — title, Python Zen, table with 5 countries.
**Root cause:** Google Docs exports use embedded fonts with custom encoding that pdf_oxide cannot decode.

**tiny.pdf (0.0%):** pdf_oxide extracts one line of garbage:
```
S/TNCF:03:12B39ao20178aioaemabr02.hdml6etslpreyeimeulreTn1sFBeih.dpromeS...
```
Kreuzberg extracts clean text including a table (Water Freezing Point: 0/32, Boiling: 100/212).
**Root cause:** Font encoding lookup failure — raw glyph IDs emitted instead of Unicode.

**right_to_left_01.pdf (1.6%):** pdf_oxide reverses Arabic character order:
- Kreuzberg: `تحسين اإلنتاجية` (correct logical order)
- pdf_oxide: `ةيجاتنلإا نيسحت` (reversed — every word is backwards)
**Root cause:** Physical page order extracted instead of logical Unicode order.

#### Word merging defects (Jaccard 70–85%)

Across many documents, pdf_oxide merges adjacent words:

| Document | pdf_oxide output | Expected |
|----------|-----------------|----------|
| docling.pdf | `introducesDocling` | `introduces Docling` |
| docling.pdf | `relying pypdfiumon` | `relying on pypdfium` |
| hideous_name.pdf | `destinationmachine` | `destination machine` |
| hideous_name.pdf | `helporganizeas` | `help organize as` |
| multi_page.pdf | `professi\nonal` | `professional` |
| sample_contract.pdf | `th is Section` | `this Section` |
| slides.pdf | `CS@VTthere are key values` | `CS@VT there are key values` |

### 2.3 One Case Where pdf_oxide Wins

**non_ascii_text.pdf (4.1% Jaccard):** This German-language document exposes a pdfium encoding issue:
- Kreuzberg: `+HUDXVJHEHU *HPHLQGHYHUZDOWXQJ` — character-shifted gibberish (ROT-like encoding error)
- pdf_oxide: `Spatenstich für neue Hackschnitzelheizung` — correct, readable German with proper umlauts

Kreuzberg's output is 30% larger (87K vs 66K chars) because the encoding corruption inflates character representation. **pdf_oxide is clearly superior here** — it correctly decodes the font encoding that pdfium mishandles.

---

## 3. Markdown Quality

### 3.1 Structure Detection

| File | K-headings | O-headings | K-paragraphs | O-paragraphs |
|------|-----------|-----------|-------------|-------------|
| docling.pdf | 3 | 198 | 95 | 608 |
| fake_memo.pdf | 0 | 0 | 1 | 4 |
| google_doc_document.pdf | 2 | 16 | 5 | 16 |
| code_and_formula.pdf | 2 | 4 | 11 | 13 |
| sample_contract.pdf | 4 | 0 | 192 | 81 |
| searchable.pdf | 2 | 2 | 5 | 8 |
| multi_page.pdf | 11 | 0 | 78 | 121 |

pdf_oxide massively over-detects headings (198 vs 3 for docling.pdf) — nearly every bold span becomes a heading. Kreuzberg uses font-size clustering to identify true document headings.

### 3.2 Qualitative Comparison

**Kreuzberg markdown** (docling.pdf):
```markdown
# Docling Technical Report

Version 1.0 Christoph Auer...

Abstract

This technical report introduces Docling, an easy to use, self-contained...

1 Introduction

Converting PDF documents back into a machine-processable format...
```

**pdf_oxide markdown** (docling.pdf):
```markdown
## arXiv:2408.09869v5  [cs.CL]  9 Dec 2024

### Docling Technical Report

Version1.0

**Christoph Auer Maksym**Lysak AhmedNassar MicheleDolfi...
```

Key differences:
- pdf_oxide has word-merging in markdown too ("Version1.0", "AhmedNassar")
- pdf_oxide aggressively bolds author names, breaking them across bold boundaries
- pdf_oxide generates 1,287 lines vs kreuzberg's 198 lines — 6.5x inflation
- Kreuzberg maintains clean heading hierarchy; pdf_oxide fragments it

**Reading order in markdown:**
For searchable.pdf, pdf_oxide places the document title *at the end* instead of the beginning, and the subtitle appears mid-document. Kreuzberg preserves correct top-to-bottom order.

**Code block handling:**
- Kreuzberg: `function add(a, b) { return a + b; }` (correct)
- pdf_oxide: `functionadd( a , b) { returna+b; }` (spaces removed from identifiers)

### 3.3 Markdown Verdict

Kreuzberg produces markdown that is suitable for RAG pipelines, LLM consumption, and human reading. pdf_oxide's markdown has word-merging artifacts, scrambled reading order, over-segmented headings, and 5–7x line count inflation that would degrade chunking and retrieval quality.

---

## 4. Summary Scorecard

| Dimension | Kreuzberg (pdfium) | pdf_oxide | Winner |
|-----------|-------------------|-----------|--------|
| **Speed** | 12.57ms avg | 3.11ms avg (4.0x faster) | **pdf_oxide** |
| **Text correctness (overall)** | Consistent, clean | Word merging, encoding failures | **Kreuzberg** |
| **Font encoding robustness** | 1 failure (German) | 3 failures (GDocs, tiny, RTL) | **Kreuzberg** |
| **RTL text** | Correct logical order | Reversed characters | **Kreuzberg** |
| **Non-ASCII European** | 1 encoding failure | Correct | **pdf_oxide** |
| **Word spacing** | Excellent | Systematic merging defects | **Kreuzberg** |
| **Markdown structure** | Accurate headings, clean | Over-segmented, scrambled | **Kreuzberg** |
| **Reading order** | Correct | Corrupted on multi-column/slides | **Kreuzberg** |
| **Production readiness** | Yes | No — needs significant post-processing | **Kreuzberg** |

---

## 5. Conclusions

1. **Speed is real** — pdf_oxide delivers a genuine 4x speedup. For latency-sensitive applications, this matters.

2. **Text quality is not there yet** — pdf_oxide has fundamental issues with word boundary detection, font encoding, and RTL text that would require substantial post-processing to match pdfium quality. The word-merging problem alone would break NLP tokenization, search indexing, and RAG retrieval.

3. **Not a drop-in replacement** — Switching from pdfium to pdf_oxide would regress extraction quality on at least 3 document types (Google Docs exports, embedded-font PDFs, RTL documents) and introduce word-spacing artifacts across most documents.

4. **Worth watching** — pdf_oxide is a young project (v0.3.x) with impressive performance characteristics. If the word-spacing and encoding issues are fixed, it could become a compelling pdfium alternative, especially given its pure-Rust implementation (no FFI, no system dependency).

5. **One bright spot** — pdf_oxide correctly handles the German non-ASCII PDF that pdfium fails on, suggesting its font decoding takes a different (sometimes better) approach for certain encoding schemes.

---

## Appendix: Files

All extracted text and markdown outputs are in `/tmp/pdf_oxide_comparison/`:
- `{stem}_kreuzberg.txt` / `{stem}_pdf_oxide.txt` — raw text extraction
- `{stem}_kreuzberg.md` / `{stem}_pdf_oxide.md` — markdown extraction

Comparison tool source: `tools/pdf-oxide-comparison/`
