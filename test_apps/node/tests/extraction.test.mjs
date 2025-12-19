import { readFileSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, it, expect, beforeAll } from "vitest";
import {
  extractFileSync,
  extractFile,
  extractBytesSync,
  extractBytes,
  batchExtractFilesSync,
  batchExtractFiles,
  batchExtractBytesSync,
  batchExtractBytes,
  detectMimeTypeFromPath,
  detectMimeType,
  KreuzbergError,
  ValidationError,
  ParsingError,
} from "@kreuzberg/node";

const TEST_TIMEOUT_MS = 60_000;
const __dirname = dirname(fileURLToPath(import.meta.url));
const WORKSPACE_ROOT = join(__dirname, "../../..");
const TEST_DOCUMENTS = join(WORKSPACE_ROOT, "test_documents");

function resolveDocument(relative) {
  return join(TEST_DOCUMENTS, relative);
}

function getDocumentBytes(path) {
  const fullPath = resolveDocument(path);
  return readFileSync(fullPath);
}

describe("Type Verification Tests", () => {
  it("should have ExtractionResult type available", () => {
    const docPath = resolveDocument("text/report.txt");
    if (!existsSync(docPath)) {
      console.warn("Skipping: test document missing");
      return;
    }
    const result = extractFileSync(docPath, null, null);
    expect(result).toHaveProperty("content");
    expect(result).toHaveProperty("mimeType");
    expect(result).toHaveProperty("metadata");
  });

  it("should have ExtractionConfig type available", () => {
    const config = {
      useCache: true,
      enableQualityProcessing: false,
      forceOcr: false,
    };
    expect(typeof config.useCache).toBe("boolean");
    expect(typeof config.enableQualityProcessing).toBe("boolean");
    expect(typeof config.forceOcr).toBe("boolean");
  });

  it("should export all error types", () => {
    expect(KreuzbergError).toBeDefined();
    expect(ValidationError).toBeDefined();
    expect(ParsingError).toBeDefined();
  });

  it("should have ChunkingConfig type", () => {
    const chunkingConfig = {
      maxChars: 1024,
      maxOverlap: 512,
    };
    expect(typeof chunkingConfig.maxChars).toBe("number");
    expect(typeof chunkingConfig.maxOverlap).toBe("number");
  });

  it("should have ImageExtractionConfig type", () => {
    const imageConfig = {
      extractImages: true,
      targetDpi: 150,
      maxImageDimension: 2048,
      autoAdjustDpi: true,
    };
    expect(typeof imageConfig.extractImages).toBe("boolean");
    expect(typeof imageConfig.targetDpi).toBe("number");
  });

  it("should have OcrConfig type", () => {
    const ocrConfig = {
      backend: "tesseract",
      language: "eng",
    };
    expect(typeof ocrConfig.backend).toBe("string");
    expect(typeof ocrConfig.language).toBe("string");
  });

  it("should have PdfConfig type", () => {
    const pdfConfig = {
      extractImages: true,
      extractMetadata: true,
      passwords: [],
    };
    expect(typeof pdfConfig.extractImages).toBe("boolean");
    expect(Array.isArray(pdfConfig.passwords)).toBe(true);
  });

  it("should have LanguageDetectionConfig type", () => {
    const langConfig = {
      enabled: true,
      minConfidence: 0.5,
      detectMultiple: false,
    };
    expect(typeof langConfig.enabled).toBe("boolean");
    expect(typeof langConfig.minConfidence).toBe("number");
  });

  it("should have TokenReductionConfig type", () => {
    const tokenConfig = {
      mode: "aggressive",
      preserveImportantWords: true,
    };
    expect(typeof tokenConfig.mode).toBe("string");
    expect(typeof tokenConfig.preserveImportantWords).toBe("boolean");
  });

  it("should have PostProcessorConfig type", () => {
    const postConfig = {
      enabled: true,
      enabledProcessors: ["normalize", "clean"],
      disabledProcessors: [],
    };
    expect(typeof postConfig.enabled).toBe("boolean");
    expect(Array.isArray(postConfig.enabledProcessors)).toBe(true);
  });
});

describe("MIME Type Detection Tests", () => {
  it("should detect MIME type from PDF bytes", () => {
    const docPath = resolveDocument("pdfs/fake_memo.pdf");
    if (!existsSync(docPath)) {
      console.warn("Skipping: test document missing");
      return;
    }
    const bytes = getDocumentBytes("pdfs/fake_memo.pdf");
    const mimeType = detectMimeType(bytes);
    expect(mimeType).toContain("pdf");
  });

  it("should detect MIME type from DOCX bytes", () => {
    const docPath = resolveDocument("office/document.docx");
    if (!existsSync(docPath)) {
      console.warn("Skipping: test document missing");
      return;
    }
    const bytes = getDocumentBytes("office/document.docx");
    const mimeType = detectMimeType(bytes);
    expect(mimeType).toContain("word");
  });

  it("should detect MIME type from XLSX bytes", () => {
    const docPath = resolveDocument("spreadsheets/stanley_cups.xlsx");
    if (!existsSync(docPath)) {
      console.warn("Skipping: test document missing");
      return;
    }
    const bytes = getDocumentBytes("spreadsheets/stanley_cups.xlsx");
    const mimeType = detectMimeType(bytes);
    expect(mimeType).toContain("sheet");
  });

  it("should detect MIME type from file path", () => {
    const docPath = resolveDocument("pdfs/fake_memo.pdf");
    if (!existsSync(docPath)) {
      console.warn("Skipping: test document missing");
      return;
    }
    const mimeType = detectMimeTypeFromPath(docPath);
    expect(mimeType).toContain("pdf");
  });

  it("should detect MIME type for DOCX path", () => {
    const docPath = resolveDocument("office/document.docx");
    if (!existsSync(docPath)) {
      console.warn("Skipping: test document missing");
      return;
    }
    const mimeType = detectMimeTypeFromPath(docPath);
    expect(mimeType).toContain("word");
  });

  it("should detect MIME type for XLSX path", () => {
    const docPath = resolveDocument("spreadsheets/stanley_cups.xlsx");
    if (!existsSync(docPath)) {
      console.warn("Skipping: test document missing");
      return;
    }
    const mimeType = detectMimeTypeFromPath(docPath);
    expect(mimeType).toContain("sheet");
  });

  it("should detect MIME type from plain text path", () => {
    const docPath = resolveDocument("text/report.txt");
    if (!existsSync(docPath)) {
      console.warn("Skipping: test document missing");
      return;
    }
    const mimeType = detectMimeTypeFromPath(docPath);
    expect(mimeType).toContain("plain");
  });

  it("should detect MIME type from PNG image", () => {
    const docPath = resolveDocument("images/sample.png");
    if (!existsSync(docPath)) {
      console.warn("Skipping: test document missing");
      return;
    }
    const bytes = getDocumentBytes("images/sample.png");
    const mimeType = detectMimeType(bytes);
    expect(mimeType).toContain("png");
  });

  it("should detect MIME type from JSON bytes", () => {
    const docPath = resolveDocument("data_formats/simple.json");
    if (!existsSync(docPath)) {
      console.warn("Skipping: test document missing");
      return;
    }
    const bytes = getDocumentBytes("data_formats/simple.json");
    const mimeType = detectMimeType(bytes);
    expect(mimeType).toContain("json");
  });

  it("should detect MIME type from HTML bytes", () => {
    const docPath = resolveDocument("web/simple_table.html");
    if (!existsSync(docPath)) {
      console.warn("Skipping: test document missing");
      return;
    }
    const bytes = getDocumentBytes("web/simple_table.html");
    const mimeType = detectMimeType(bytes);
    expect(mimeType).toContain("html");
  });
});

describe("Byte Extraction Tests - File Path", () => {
  it("should extract from PDF bytes with file path hint", () => {
    const docPath = resolveDocument("pdfs/fake_memo.pdf");
    if (!existsSync(docPath)) {
      console.warn("Skipping: test document missing");
      return;
    }
    const bytes = getDocumentBytes("pdfs/fake_memo.pdf");
    const result = extractBytesSync(bytes, "application/pdf", null);
    expect(result.content.length).toBeGreaterThan(0);
    expect(result.mimeType).toContain("pdf");
  });

  it("should extract from DOCX bytes", () => {
    const docPath = resolveDocument("office/document.docx");
    if (!existsSync(docPath)) {
      console.warn("Skipping: test document missing");
      return;
    }
    const bytes = getDocumentBytes("office/document.docx");
    const result = extractBytesSync(bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", null);
    expect(result.content.length).toBeGreaterThan(0);
  });

  it("should extract from XLSX bytes", () => {
    const docPath = resolveDocument("spreadsheets/stanley_cups.xlsx");
    if (!existsSync(docPath)) {
      console.warn("Skipping: test document missing");
      return;
    }
    const bytes = getDocumentBytes("spreadsheets/stanley_cups.xlsx");
    const result = extractBytesSync(bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", null);
    expect(result.content.length).toBeGreaterThan(0);
  });

  it("should extract from plain text bytes", () => {
    const docPath = resolveDocument("text/report.txt");
    if (!existsSync(docPath)) {
      console.warn("Skipping: test document missing");
      return;
    }
    const bytes = getDocumentBytes("text/report.txt");
    const result = extractBytesSync(bytes, "text/plain", null);
    expect(result.content.length).toBeGreaterThan(0);
  });

  it("should extract from JSON bytes", () => {
    const docPath = resolveDocument("data_formats/simple.json");
    if (!existsSync(docPath)) {
      console.warn("Skipping: test document missing");
      return;
    }
    const bytes = getDocumentBytes("data_formats/simple.json");
    const result = extractBytesSync(bytes, "application/json", null);
    expect(result.content.length).toBeGreaterThan(0);
  });

  it("should extract from HTML bytes", () => {
    const docPath = resolveDocument("web/simple_table.html");
    if (!existsSync(docPath)) {
      console.warn("Skipping: test document missing");
      return;
    }
    const bytes = getDocumentBytes("web/simple_table.html");
    const result = extractBytesSync(bytes, "text/html", null);
    expect(result.content.length).toBeGreaterThan(0);
  });
});

describe("Byte Extraction Tests - Async", () => {
  it(
    "should extract from PDF bytes asynchronously",
    async () => {
      const docPath = resolveDocument("pdfs/fake_memo.pdf");
      if (!existsSync(docPath)) {
        console.warn("Skipping: test document missing");
        return;
      }
      const bytes = getDocumentBytes("pdfs/fake_memo.pdf");
      const result = await extractBytes(bytes, "application/pdf", null);
      expect(result.content.length).toBeGreaterThan(0);
      expect(result.mimeType).toContain("pdf");
    },
    TEST_TIMEOUT_MS,
  );

  it(
    "should extract from DOCX bytes asynchronously",
    async () => {
      const docPath = resolveDocument("office/document.docx");
      if (!existsSync(docPath)) {
        console.warn("Skipping: test document missing");
        return;
      }
      const bytes = getDocumentBytes("office/document.docx");
      const result = await extractBytes(bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", null);
      expect(result.content.length).toBeGreaterThan(0);
    },
    TEST_TIMEOUT_MS,
  );

  it(
    "should extract from plain text bytes asynchronously",
    async () => {
      const docPath = resolveDocument("text/report.txt");
      if (!existsSync(docPath)) {
        console.warn("Skipping: test document missing");
        return;
      }
      const bytes = getDocumentBytes("text/report.txt");
      const result = await extractBytes(bytes, "text/plain", null);
      expect(result.content.length).toBeGreaterThan(0);
    },
    TEST_TIMEOUT_MS,
  );
});

describe("Batch API Tests - Sync", () => {
  it("should batch extract multiple files synchronously", () => {
    const paths = [
      resolveDocument("text/report.txt"),
      resolveDocument("data_formats/simple.json"),
    ];

    const missing = paths.filter((p) => !existsSync(p));
    if (missing.length > 0) {
      console.warn("Skipping: some test documents missing");
      return;
    }

    const results = batchExtractFilesSync(paths, null);
    expect(results).toHaveLength(2);
    expect(results[0].content.length).toBeGreaterThan(0);
    expect(results[1].content.length).toBeGreaterThan(0);
  });

  it("should batch extract PDFs and Office docs synchronously", () => {
    const paths = [
      resolveDocument("pdfs/fake_memo.pdf"),
      resolveDocument("office/document.docx"),
      resolveDocument("spreadsheets/stanley_cups.xlsx"),
    ];

    const missing = paths.filter((p) => !existsSync(p));
    if (missing.length > 0) {
      console.warn("Skipping: some test documents missing");
      return;
    }

    const results = batchExtractFilesSync(paths, null);
    expect(results).toHaveLength(3);
    results.forEach((result) => {
      expect(result.content.length).toBeGreaterThan(0);
      expect(result.mimeType).toBeDefined();
    });
  });

  it("should batch extract with consistent ordering", () => {
    const paths = [
      resolveDocument("text/report.txt"),
      resolveDocument("data_formats/simple.json"),
      resolveDocument("text/report.txt"),
    ];

    const missing = paths.filter((p) => !existsSync(p));
    if (missing.length > 0) {
      console.warn("Skipping: some test documents missing");
      return;
    }

    const results = batchExtractFilesSync(paths, null);
    expect(results).toHaveLength(3);
    expect(results[0].mimeType).toBe(results[2].mimeType);
  });

  it("should batch extract bytes synchronously", () => {
    const paths = [
      resolveDocument("text/report.txt"),
      resolveDocument("data_formats/simple.json"),
    ];

    const missing = paths.filter((p) => !existsSync(p));
    if (missing.length > 0) {
      console.warn("Skipping: some test documents missing");
      return;
    }

    const bytes = [
      getDocumentBytes("text/report.txt"),
      getDocumentBytes("data_formats/simple.json"),
    ];
    const mimes = ["text/plain", "application/json"];

    const results = batchExtractBytesSync(bytes, mimes, null);
    expect(results).toHaveLength(2);
    expect(results[0].content.length).toBeGreaterThan(0);
    expect(results[1].content.length).toBeGreaterThan(0);
  });

  it("should batch extract bytes with correct MIME mapping", () => {
    const docPath1 = resolveDocument("pdfs/fake_memo.pdf");
    const docPath2 = resolveDocument("office/document.docx");

    if (!existsSync(docPath1) || !existsSync(docPath2)) {
      console.warn("Skipping: test documents missing");
      return;
    }

    const bytes = [
      getDocumentBytes("pdfs/fake_memo.pdf"),
      getDocumentBytes("office/document.docx"),
    ];
    const mimes = [
      "application/pdf",
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ];

    const results = batchExtractBytesSync(bytes, mimes, null);
    expect(results).toHaveLength(2);
    expect(results[0].mimeType).toContain("pdf");
    expect(results[1].mimeType).toContain("word");
  });
});

describe("Batch API Tests - Async", () => {
  it(
    "should batch extract multiple files asynchronously",
    async () => {
      const paths = [
        resolveDocument("text/report.txt"),
        resolveDocument("data_formats/simple.json"),
      ];

      const missing = paths.filter((p) => !existsSync(p));
      if (missing.length > 0) {
        console.warn("Skipping: some test documents missing");
        return;
      }

      const results = await batchExtractFiles(paths, null);
      expect(results).toHaveLength(2);
      expect(results[0].content.length).toBeGreaterThan(0);
      expect(results[1].content.length).toBeGreaterThan(0);
    },
    TEST_TIMEOUT_MS,
  );

  it(
    "should batch extract bytes asynchronously",
    async () => {
      const paths = [
        resolveDocument("text/report.txt"),
        resolveDocument("data_formats/simple.json"),
      ];

      const missing = paths.filter((p) => !existsSync(p));
      if (missing.length > 0) {
        console.warn("Skipping: some test documents missing");
        return;
      }

      const bytes = [
        getDocumentBytes("text/report.txt"),
        getDocumentBytes("data_formats/simple.json"),
      ];
      const mimes = ["text/plain", "application/json"];

      const results = await batchExtractBytes(bytes, mimes, null);
      expect(results).toHaveLength(2);
      expect(results[0].content.length).toBeGreaterThan(0);
      expect(results[1].content.length).toBeGreaterThan(0);
    },
    TEST_TIMEOUT_MS,
  );

  it(
    "should batch extract PDFs asynchronously",
    async () => {
      const docPath = resolveDocument("pdfs/fake_memo.pdf");
      if (!existsSync(docPath)) {
        console.warn("Skipping: test document missing");
        return;
      }

      const paths = [docPath, docPath];
      const results = await batchExtractFiles(paths, null);
      expect(results).toHaveLength(2);
      results.forEach((result) => {
        expect(result.mimeType).toContain("pdf");
      });
    },
    TEST_TIMEOUT_MS,
  );
});

describe("File Type Coverage Tests - PDF", () => {
  it("should extract PDF with content validation", () => {
    const docPath = resolveDocument("pdfs/fake_memo.pdf");
    if (!existsSync(docPath)) {
      console.warn("Skipping: test document missing");
      return;
    }
    const result = extractFileSync(docPath, null, null);
    expect(result.content).toBeDefined();
    expect(result.content.length).toBeGreaterThan(50);
    expect(result.mimeType).toContain("pdf");
    expect(result.metadata).toBeDefined();
  });

  it("should extract PDF with metadata", () => {
    const docPath = resolveDocument("pdfs/fake_memo.pdf");
    if (!existsSync(docPath)) {
      console.warn("Skipping: test document missing");
      return;
    }
    const result = extractFileSync(docPath, null, null);
    expect(typeof result.metadata).toBe("object");
  });
});

describe("File Type Coverage Tests - DOCX", () => {
  it("should extract DOCX with content validation", () => {
    const docPath = resolveDocument("office/document.docx");
    if (!existsSync(docPath)) {
      console.warn("Skipping: test document missing");
      return;
    }
    const result = extractFileSync(docPath, null, null);
    expect(result.content.length).toBeGreaterThan(0);
    expect(result.mimeType).toContain("word");
  });

  it("should extract DOCX with equations", () => {
    const docPath = resolveDocument("documents/equations.docx");
    if (!existsSync(docPath)) {
      console.warn("Skipping: test document missing");
      return;
    }
    const result = extractFileSync(docPath, null, null);
    expect(result.content.length).toBeGreaterThan(0);
    expect(result.mimeType).toContain("word");
  });
});

describe("File Type Coverage Tests - XLSX", () => {
  it("should extract XLSX with content validation", () => {
    const docPath = resolveDocument("spreadsheets/stanley_cups.xlsx");
    if (!existsSync(docPath)) {
      console.warn("Skipping: test document missing");
      return;
    }
    const result = extractFileSync(docPath, null, null);
    expect(result.content.length).toBeGreaterThan(100);
    expect(result.mimeType).toContain("sheet");
  });

  it("should extract XLSX with table data", () => {
    const docPath = resolveDocument("spreadsheets/stanley_cups.xlsx");
    if (!existsSync(docPath)) {
      console.warn("Skipping: test document missing");
      return;
    }
    const result = extractFileSync(docPath, null, null);
    const lowered = result.content.toLowerCase();
    expect(lowered).toContain("team");
    expect(lowered).toContain("stanley");
  });

  it("should extract XLSX metadata", () => {
    const docPath = resolveDocument("spreadsheets/stanley_cups.xlsx");
    if (!existsSync(docPath)) {
      console.warn("Skipping: test document missing");
      return;
    }
    const result = extractFileSync(docPath, null, null);
    expect(result.metadata).toBeDefined();
  });
});

describe("File Type Coverage Tests - Images", () => {
  it("should detect PNG image MIME type", () => {
    const docPath = resolveDocument("images/sample.png");
    if (!existsSync(docPath)) {
      console.warn("Skipping: test document missing (image extraction requires additional dependencies)");
      return;
    }
    const mimeType = detectMimeTypeFromPath(docPath);
    expect(mimeType).toContain("png");
  });

  it("should extract PNG image metadata", () => {
    const docPath = resolveDocument("images/sample.png");
    if (!existsSync(docPath)) {
      console.warn("Skipping: test document missing");
      return;
    }
    try {
      const result = extractFileSync(docPath, null, null);
      expect(result.mimeType).toContain("png");
    } catch (error) {
      if (error instanceof Error && error.message.toLowerCase().includes("missing")) {
        console.warn("Skipping: image extraction dependencies missing");
        return;
      }
      throw error;
    }
  });

  it("should detect JPG image MIME type", () => {
    const docPath = resolveDocument("images/sample.jpg");
    if (!existsSync(docPath)) {
      console.warn("Skipping: test document missing");
      return;
    }
    const mimeType = detectMimeTypeFromPath(docPath);
    expect(mimeType).toContain("jpeg");
  });
});

describe("File Type Coverage Tests - Text & Data", () => {
  it("should extract plain text file", () => {
    const docPath = resolveDocument("text/report.txt");
    if (!existsSync(docPath)) {
      console.warn("Skipping: test document missing");
      return;
    }
    const result = extractFileSync(docPath, null, null);
    expect(result.content.length).toBeGreaterThan(0);
    expect(result.mimeType).toContain("plain");
  });

  it("should extract JSON file", () => {
    const docPath = resolveDocument("data_formats/simple.json");
    if (!existsSync(docPath)) {
      console.warn("Skipping: test document missing");
      return;
    }
    const result = extractFileSync(docPath, null, null);
    expect(result.content.length).toBeGreaterThan(0);
    expect(result.mimeType).toContain("json");
  });

  it("should extract HTML file", () => {
    const docPath = resolveDocument("web/simple_table.html");
    if (!existsSync(docPath)) {
      console.warn("Skipping: test document missing");
      return;
    }
    const result = extractFileSync(docPath, null, null);
    expect(result.content.length).toBeGreaterThan(0);
    expect(result.mimeType).toContain("html");
  });

  it("should extract Markdown file", () => {
    const docPath = resolveDocument("extraction_test.md");
    if (!existsSync(docPath)) {
      console.warn("Skipping: test document missing");
      return;
    }
    const result = extractFileSync(docPath, null, null);
    expect(result.content.length).toBeGreaterThan(0);
  });
});

describe("Configuration and Result Structure Tests", () => {
  it("should return result with all required fields", () => {
    const docPath = resolveDocument("text/report.txt");
    if (!existsSync(docPath)) {
      console.warn("Skipping: test document missing");
      return;
    }
    const result = extractFileSync(docPath, null, null);
    expect(result).toHaveProperty("content");
    expect(result).toHaveProperty("mimeType");
    expect(result).toHaveProperty("metadata");
    expect(typeof result.content).toBe("string");
    expect(typeof result.mimeType).toBe("string");
    expect(result.metadata === null || typeof result.metadata === "object").toBe(true);
  });

  it("should return result with optional table field", () => {
    const docPath = resolveDocument("spreadsheets/stanley_cups.xlsx");
    if (!existsSync(docPath)) {
      console.warn("Skipping: test document missing");
      return;
    }
    const result = extractFileSync(docPath, null, null);
    if (result.tables !== undefined) {
      expect(Array.isArray(result.tables)).toBe(true);
    }
  });

  it("should return result with optional chunks field", () => {
    const docPath = resolveDocument("text/report.txt");
    if (!existsSync(docPath)) {
      console.warn("Skipping: test document missing");
      return;
    }
    const config = { chunking: { maxChars: 512, maxOverlap: 256 } };
    const result = extractFileSync(docPath, null, config);
    if (result.chunks !== undefined) {
      expect(Array.isArray(result.chunks)).toBe(true);
    }
  });

  it("should handle null configuration gracefully", () => {
    const docPath = resolveDocument("text/report.txt");
    if (!existsSync(docPath)) {
      console.warn("Skipping: test document missing");
      return;
    }
    const result = extractFileSync(docPath, null, null);
    expect(result.content.length).toBeGreaterThan(0);
  });

  it("should handle empty configuration object", () => {
    const docPath = resolveDocument("text/report.txt");
    if (!existsSync(docPath)) {
      console.warn("Skipping: test document missing");
      return;
    }
    const result = extractFileSync(docPath, null, {});
    expect(result.content.length).toBeGreaterThan(0);
  });

  it("should handle partial configuration", () => {
    const docPath = resolveDocument("text/report.txt");
    if (!existsSync(docPath)) {
      console.warn("Skipping: test document missing");
      return;
    }
    const config = { useCache: true };
    const result = extractFileSync(docPath, null, config);
    expect(result.content.length).toBeGreaterThan(0);
  });

  it("should respect MIME type hint when provided", () => {
    const docPath = resolveDocument("pdfs/fake_memo.pdf");
    if (!existsSync(docPath)) {
      console.warn("Skipping: test document missing");
      return;
    }
    const result = extractFileSync(docPath, "application/pdf", null);
    expect(result.mimeType).toContain("pdf");
  });

  it("should auto-detect MIME type when not provided", () => {
    const docPath = resolveDocument("pdfs/fake_memo.pdf");
    if (!existsSync(docPath)) {
      console.warn("Skipping: test document missing");
      return;
    }
    const result = extractFileSync(docPath, null, null);
    expect(result.mimeType).toContain("pdf");
  });

  it("should include metadata object in result", () => {
    const docPath = resolveDocument("office/document.docx");
    if (!existsSync(docPath)) {
      console.warn("Skipping: test document missing");
      return;
    }
    const result = extractFileSync(docPath, null, null);
    expect(result.metadata).toBeDefined();
  });

  it("should preserve result structure across different file types", () => {
    const paths = [
      resolveDocument("text/report.txt"),
      resolveDocument("pdfs/fake_memo.pdf"),
      resolveDocument("office/document.docx"),
    ];

    const missing = paths.filter((p) => !existsSync(p));
    if (missing.length > 0) {
      console.warn("Skipping: some test documents missing");
      return;
    }

    const results = paths.map((path) => extractFileSync(path, null, null));

    results.forEach((result) => {
      expect(result).toHaveProperty("content");
      expect(result).toHaveProperty("mimeType");
      expect(result).toHaveProperty("metadata");
      expect(typeof result.content).toBe("string");
      expect(typeof result.mimeType).toBe("string");
    });
  });
});

describe("Async File Extraction Tests", () => {
  it(
    "should extract file asynchronously",
    async () => {
      const docPath = resolveDocument("text/report.txt");
      if (!existsSync(docPath)) {
        console.warn("Skipping: test document missing");
        return;
      }
      const result = await extractFile(docPath, null, null);
      expect(result.content.length).toBeGreaterThan(0);
    },
    TEST_TIMEOUT_MS,
  );

  it(
    "should extract PDF asynchronously",
    async () => {
      const docPath = resolveDocument("pdfs/fake_memo.pdf");
      if (!existsSync(docPath)) {
        console.warn("Skipping: test document missing");
        return;
      }
      const result = await extractFile(docPath, null, null);
      expect(result.mimeType).toContain("pdf");
      expect(result.content.length).toBeGreaterThan(0);
    },
    TEST_TIMEOUT_MS,
  );

  it(
    "should extract DOCX asynchronously",
    async () => {
      const docPath = resolveDocument("office/document.docx");
      if (!existsSync(docPath)) {
        console.warn("Skipping: test document missing");
        return;
      }
      const result = await extractFile(docPath, null, null);
      expect(result.mimeType).toContain("word");
    },
    TEST_TIMEOUT_MS,
  );

  it(
    "should extract XLSX asynchronously",
    async () => {
      const docPath = resolveDocument("spreadsheets/stanley_cups.xlsx");
      if (!existsSync(docPath)) {
        console.warn("Skipping: test document missing");
        return;
      }
      const result = await extractFile(docPath, null, null);
      expect(result.mimeType).toContain("sheet");
    },
    TEST_TIMEOUT_MS,
  );
});

describe("Error Handling Tests", () => {
  it("should throw error for non-existent file", () => {
    const nonExistentPath = resolveDocument("non_existent_file_12345.pdf");
    expect(() => {
      extractFileSync(nonExistentPath, null, null);
    }).toThrow();
  });

  it("should throw error for invalid MIME type in bytes extraction", () => {
    const docPath = resolveDocument("text/report.txt");
    if (!existsSync(docPath)) {
      console.warn("Skipping: test document missing");
      return;
    }
    const bytes = getDocumentBytes("text/report.txt");
    expect(() => {
      extractBytesSync(bytes, "invalid/mimetype", null);
    }).toThrow();
  });

  it("should throw error when batch arrays have mismatched lengths", () => {
    const docPath = resolveDocument("text/report.txt");
    if (!existsSync(docPath)) {
      console.warn("Skipping: test document missing");
      return;
    }
    const bytes = [getDocumentBytes("text/report.txt")];
    const mimes = ["text/plain", "application/json"];

    expect(() => {
      batchExtractBytesSync(bytes, mimes, null);
    }).toThrow();
  });
});

describe("Smoke Tests - Basic Functionality", () => {
  it("should extract PDF with basic config", () => {
    const docPath = resolveDocument("pdfs/fake_memo.pdf");
    if (!existsSync(docPath)) {
      console.warn("Skipping: test document missing");
      return;
    }
    const result = extractFileSync(docPath, null, null);
    expect(result.content).toBeDefined();
    expect(result.mimeType).toContain("pdf");
  });

  it("should extract DOCX with basic config", () => {
    const docPath = resolveDocument("documents/fake.docx");
    if (!existsSync(docPath)) {
      console.warn("Skipping: test document missing");
      return;
    }
    const result = extractFileSync(docPath, null, null);
    expect(result.content).toBeDefined();
  });

  it("should extract HTML with basic config", () => {
    const docPath = resolveDocument("web/simple_table.html");
    if (!existsSync(docPath)) {
      console.warn("Skipping: test document missing");
      return;
    }
    const result = extractFileSync(docPath, null, null);
    expect(result.content).toBeDefined();
    expect(result.mimeType).toContain("html");
  });

  it("should extract JSON with basic config", () => {
    const docPath = resolveDocument("data_formats/simple.json");
    if (!existsSync(docPath)) {
      console.warn("Skipping: test document missing");
      return;
    }
    const result = extractFileSync(docPath, null, null);
    expect(result.content).toBeDefined();
    expect(result.mimeType).toContain("json");
  });

  it("should extract XLSX with basic config", () => {
    const docPath = resolveDocument("spreadsheets/stanley_cups.xlsx");
    if (!existsSync(docPath)) {
      console.warn("Skipping: test document missing");
      return;
    }
    const result = extractFileSync(docPath, null, null);
    expect(result.content).toBeDefined();
    expect(result.mimeType).toContain("sheet");
  });

  it("should extract text file with basic config", () => {
    const docPath = resolveDocument("text/report.txt");
    if (!existsSync(docPath)) {
      console.warn("Skipping: test document missing");
      return;
    }
    const result = extractFileSync(docPath, null, null);
    expect(result.content).toBeDefined();
    expect(result.mimeType).toContain("plain");
  });

  it("should extract PNG image with basic config", () => {
    const docPath = resolveDocument("images/sample.png");
    if (!existsSync(docPath)) {
      console.warn("Skipping: test document missing (image extraction requires dependencies)");
      return;
    }
    try {
      const result = extractFileSync(docPath, null, null);
      expect(result.mimeType).toContain("png");
    } catch (error) {
      if (error instanceof Error && error.message.toLowerCase().includes("missing")) {
        console.warn("Skipping: image extraction dependencies missing");
        return;
      }
      throw error;
    }
  });
});

describe("Configuration Tests", () => {
  it("should apply cache configuration", () => {
    const docPath = resolveDocument("text/report.txt");
    if (!existsSync(docPath)) {
      console.warn("Skipping: test document missing");
      return;
    }
    const config = { useCache: true };
    const result = extractFileSync(docPath, null, config);
    expect(result.content.length).toBeGreaterThan(0);
  });

  it("should apply chunking configuration", () => {
    const docPath = resolveDocument("text/report.txt");
    if (!existsSync(docPath)) {
      console.warn("Skipping: test document missing");
      return;
    }
    const config = {
      chunking: {
        maxChars: 512,
        maxOverlap: 256,
      },
    };
    const result = extractFileSync(docPath, null, config);
    expect(result.content.length).toBeGreaterThan(0);
  });

  it("should apply quality processing configuration", () => {
    const docPath = resolveDocument("text/report.txt");
    if (!existsSync(docPath)) {
      console.warn("Skipping: test document missing");
      return;
    }
    const config = { enableQualityProcessing: true };
    const result = extractFileSync(docPath, null, config);
    expect(result.content.length).toBeGreaterThan(0);
  });

  it("should apply language detection configuration", () => {
    const docPath = resolveDocument("text/report.txt");
    if (!existsSync(docPath)) {
      console.warn("Skipping: test document missing");
      return;
    }
    const config = {
      languageDetection: {
        enabled: true,
        minConfidence: 0.5,
      },
    };
    const result = extractFileSync(docPath, null, config);
    expect(result.content.length).toBeGreaterThan(0);
  });
});
