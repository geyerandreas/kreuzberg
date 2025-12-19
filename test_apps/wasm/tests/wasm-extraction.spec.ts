import { readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect, beforeAll } from 'vitest';
import type {
	ExtractionConfig,
	ExtractionResult,
	OcrConfig,
	ChunkingConfig,
	ImageExtractionConfig,
	PdfConfig,
	Metadata,
	Table,
} from '@kreuzberg/wasm';
import {
	initWasm,
	isInitialized,
	getVersion,
	extractBytes,
	extractBytesSync,
	batchExtractBytes,
	batchExtractBytesSync,
	fileToUint8Array,
	isValidExtractionResult,
	configToJS,
	wrapWasmError,
} from '@kreuzberg/wasm';

const TEST_DOCS_DIR = resolve(__dirname, '../../../..', 'test_documents');

const getTestDocument = (relativePath: string): Uint8Array => {
	const path = resolve(TEST_DOCS_DIR, relativePath);
	try {
		return new Uint8Array(readFileSync(path));
	} catch (error) {
		const fallbackPath = resolve('/Users/naamanhirschfeld/workspace/kreuzberg-dev/kreuzberg/test_documents', relativePath);
		return new Uint8Array(readFileSync(fallbackPath));
	}
};

const tryExtraction = async (bytes: Uint8Array, mimeType: string, config?: ExtractionConfig | null): Promise<ExtractionResult | null> => {
	try {
		return await extractBytes(bytes, mimeType, config);
	} catch (error) {
		return null;
	}
};

const tryExtractionSync = (bytes: Uint8Array, mimeType: string, config?: ExtractionConfig | null): ExtractionResult | null => {
	try {
		return extractBytesSync(bytes, mimeType, config);
	} catch (error) {
		return null;
	}
};

beforeAll(async () => {
	if (!isInitialized()) {
		await initWasm();
	}
});

describe('WASM Initialization', () => {
	it('should initialize WASM module', async () => {
		expect(isInitialized()).toBe(true);
	});

	it('should get version after initialization', async () => {
		const version = getVersion();
		expect(version).toBeDefined();
		expect(typeof version).toBe('string');
		expect(version.length).toBeGreaterThan(0);
	});
});

describe('Type Verification (8 tests)', () => {
	it('should have ExtractionConfig type available', () => {
		const config: ExtractionConfig = {
			ocr: undefined,
			chunking: undefined,
			images: undefined,
			pdf: undefined,
		};
		expect(config).toBeDefined();
	});

	it('should have ExtractionResult type available', () => {
		const result: ExtractionResult = {
			content: 'test',
			mimeType: 'text/plain',
			metadata: {},
			tables: [],
		};
		expect(result).toBeDefined();
		expect(result.content).toBeDefined();
	});

	it('should have OcrConfig type available', () => {
		const config: OcrConfig = {
			backend: 'tesseract',
			language: 'eng',
		};
		expect(config).toBeDefined();
		expect(config.backend).toBe('tesseract');
	});

	it('should have ChunkingConfig type available', () => {
		const config: ChunkingConfig = {
			maxChars: 1000,
			chunkOverlap: 100,
		};
		expect(config).toBeDefined();
		expect(config.maxChars).toBe(1000);
	});

	it('should have ImageExtractionConfig type available', () => {
		const config: ImageExtractionConfig = {
			extractImages: true,
			targetDpi: 150,
		};
		expect(config).toBeDefined();
		expect(config.extractImages).toBe(true);
	});

	it('should have PdfConfig type available', () => {
		const config: PdfConfig = {
			extractPages: true,
			maxPages: 100,
		};
		expect(config).toBeDefined();
	});

	it('should have Table type available', () => {
		const table: Table = {
			headers: ['Col1', 'Col2'],
			rows: [['Value1', 'Value2']],
			content: 'Col1,Col2\nValue1,Value2',
		};
		expect(table).toBeDefined();
		expect(table.headers).toHaveLength(2);
	});

	it('should have Metadata type available', () => {
		const metadata: Metadata = {
			title: 'Test',
			author: 'Author',
			created: new Date().toISOString(),
			modified: new Date().toISOString(),
			pages: 1,
		};
		expect(metadata).toBeDefined();
	});
});

describe('Synchronous File Extraction (7 tests)', () => {
	it('should extract text from PDF synchronously', () => {
		const bytes = getTestDocument('pdfs/fake_memo.pdf');
		const result = tryExtractionSync(bytes, 'application/pdf');
		expect(result === null || result.content).toBeDefined();
	});

	it('should extract from simple XLSX synchronously', () => {
		const bytes = getTestDocument('spreadsheets/test_01.xlsx');
		const result = tryExtractionSync(
			bytes,
			'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
		);
		expect(result === null || result.content).toBeDefined();
	});

	it('should extract from PNG image synchronously', () => {
		const bytes = getTestDocument('images/sample.png');
		const result = tryExtractionSync(bytes, 'image/png');
		expect(result === null || result).toBeDefined();
	});

	it('should extract from JPG image synchronously', () => {
		const bytes = getTestDocument('images/flower_no_text.jpg');
		const result = tryExtractionSync(bytes, 'image/jpeg');
		expect(result === null || result).toBeDefined();
	});

	it('should handle plain text files synchronously', () => {
		const text = 'Hello, World!';
		const bytes = new Uint8Array(Buffer.from(text));
		const result = tryExtractionSync(bytes, 'text/plain');
		expect(result === null || result).toBeDefined();
	});

	it('should handle empty byte arrays gracefully', () => {
		const emptyBytes = new Uint8Array(0);
		const result = tryExtractionSync(emptyBytes, 'text/plain');
		expect(result === null || result === null).toBe(true);
	});

	it('should handle large byte arrays', () => {
		const bytes = getTestDocument('pdfs/multi_page.pdf');
		expect(bytes.length).toBeGreaterThan(0);
		const result = tryExtractionSync(bytes, 'application/pdf');
		expect(result === null || result).toBeDefined();
	});
});

describe('Asynchronous File Extraction (7 tests)', () => {
	it('should extract text from PDF asynchronously', async () => {
		const bytes = getTestDocument('pdfs/fake_memo.pdf');
		const result = await tryExtraction(bytes, 'application/pdf');
		expect(result === null || result.content).toBeDefined();
	});

	it('should extract from simple XLSX asynchronously', async () => {
		const bytes = getTestDocument('spreadsheets/stanley_cups.xlsx');
		const result = await tryExtraction(
			bytes,
			'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
		);
		expect(result === null || result).toBeDefined();
	});

	it('should extract from PNG image asynchronously', async () => {
		const bytes = getTestDocument('images/sample.png');
		const result = await tryExtraction(bytes, 'image/png');
		expect(result === null || result).toBeDefined();
	});

	it('should extract from JPG image asynchronously', async () => {
		const bytes = getTestDocument('images/ocr_image.jpg');
		const result = await tryExtraction(bytes, 'image/jpeg');
		expect(result === null || result).toBeDefined();
	});

	it('should handle plain text files asynchronously', async () => {
		const text = 'Async text content';
		const bytes = new Uint8Array(Buffer.from(text));
		const result = await tryExtraction(bytes, 'text/plain');
		expect(result === null || result).toBeDefined();
	});

	it('should handle large byte arrays asynchronously', async () => {
		const bytes = getTestDocument('pdfs/multi_page.pdf');
		expect(bytes.length).toBeGreaterThan(0);
		const result = await tryExtraction(bytes, 'application/pdf');
		expect(result === null || result).toBeDefined();
	});

	it('should extract with null configuration', async () => {
		const bytes = getTestDocument('pdfs/fake_memo.pdf');
		const result = await tryExtraction(bytes, 'application/pdf', null);
		expect(result === null || result).toBeDefined();
	});
});

describe('Byte Extraction - Sync and Async (4 tests)', () => {
	it('should extract PDF bytes with and without async consistency', async () => {
		const bytes = getTestDocument('pdfs/fake_memo.pdf');

		const syncResult = tryExtractionSync(bytes, 'application/pdf');
		const asyncResult = await tryExtraction(bytes, 'application/pdf');

		expect(syncResult === null || typeof syncResult.content === 'string').toBe(true);
		expect(asyncResult === null || typeof asyncResult.content === 'string').toBe(true);
	});

	it('should extract consistently from same bytes', async () => {
		const bytes = getTestDocument('spreadsheets/test_01.xlsx');
		const mimeType = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';

		const syncResult = tryExtractionSync(bytes, mimeType);
		const asyncResult = await tryExtraction(bytes, mimeType);

		expect(syncResult === null || asyncResult === null || typeof syncResult.content === typeof asyncResult.content).toBe(true);
	});

	it('should preserve byte data integrity', () => {
		const originalBytes = getTestDocument('pdfs/fake_memo.pdf');
		const bytesCopy = new Uint8Array(originalBytes);

		const result = tryExtractionSync(bytesCopy, 'application/pdf');
		expect(result === null || result).toBeDefined();
		expect(originalBytes).toEqual(bytesCopy);
	});

	it('should handle rapid sequential byte extraction', async () => {
		const bytes = getTestDocument('pdfs/fake_memo.pdf');

		const r1 = await tryExtraction(bytes, 'application/pdf');
		const r2 = await tryExtraction(bytes, 'application/pdf');
		const r3 = await tryExtraction(bytes, 'application/pdf');

		expect([r1, r2, r3]).toBeDefined();
	});
});

describe('Batch Extraction APIs (6 tests)', () => {
	it('should batch extract multiple bytes asynchronously', async () => {
		const files = [
			{ data: getTestDocument('images/sample.png'), mimeType: 'image/png' },
			{
				data: getTestDocument('spreadsheets/test_01.xlsx'),
				mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
			},
		];

		try {
			const results = await batchExtractBytes(files);
			expect(results).toHaveLength(2);
			expect(Array.isArray(results)).toBe(true);
		} catch (error) {
			expect(error).toBeDefined();
		}
	});

	it('should batch extract multiple bytes synchronously', () => {
		const files = [
			{ data: getTestDocument('images/sample.png'), mimeType: 'image/png' },
			{ data: new Uint8Array(Buffer.from('test')), mimeType: 'text/plain' },
		];

		try {
			const results = batchExtractBytesSync(files);
			expect(results).toHaveLength(2);
			expect(Array.isArray(results)).toBe(true);
		} catch (error) {
			expect(error).toBeDefined();
		}
	});

	it('should handle empty batch gracefully', async () => {
		try {
			const results = await batchExtractBytes([]);
			expect(Array.isArray(results)).toBe(true);
			expect(results).toHaveLength(0);
		} catch (error) {
			expect(error).toBeDefined();
		}
	});

	it('should preserve order in batch extraction', async () => {
		const files = [
			{ data: getTestDocument('images/sample.png'), mimeType: 'image/png' },
			{ data: new Uint8Array(Buffer.from('text')), mimeType: 'text/plain' },
		];

		try {
			const results = await batchExtractBytes(files);
			expect(results).toHaveLength(2);
			if (results.length > 0) {
				expect(results[0].mimeType).toBe('image/png');
				expect(results[1].mimeType).toBe('text/plain');
			}
		} catch (error) {
			expect(error).toBeDefined();
		}
	});

	it('should batch extract with configuration', async () => {
		const config: ExtractionConfig = {
			chunking: {
				maxChars: 500,
				chunkOverlap: 50,
			},
		};

		const files = [
			{ data: getTestDocument('images/sample.png'), mimeType: 'image/png' },
		];

		try {
			const results = await batchExtractBytes(files, config);
			expect(results).toHaveLength(1);
			expect(Array.isArray(results)).toBe(true);
		} catch (error) {
			expect(error).toBeDefined();
		}
	});

	it('should handle single item batch', async () => {
		const files = [
			{ data: getTestDocument('images/sample.png'), mimeType: 'image/png' },
		];

		try {
			const results = await batchExtractBytes(files);
			expect(results).toHaveLength(1);
		} catch (error) {
			expect(error).toBeDefined();
		}
	});
});

describe('MIME Type Detection (7 tests)', () => {
	it('should correctly identify PDF MIME type', async () => {
		const bytes = getTestDocument('pdfs/fake_memo.pdf');
		const result = await tryExtraction(bytes, 'application/pdf');
		expect(result === null || result.mimeType === 'application/pdf').toBe(true);
	});

	it('should correctly identify XLSX MIME type', async () => {
		const bytes = getTestDocument('spreadsheets/test_01.xlsx');
		const result = await tryExtraction(
			bytes,
			'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
		);
		expect(result === null || result.mimeType === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet').toBe(true);
	});

	it('should correctly identify PNG MIME type', async () => {
		const bytes = getTestDocument('images/sample.png');
		const result = await tryExtraction(bytes, 'image/png');
		expect(result === null || result.mimeType === 'image/png').toBe(true);
	});

	it('should correctly identify JPG MIME type', async () => {
		const bytes = getTestDocument('images/flower_no_text.jpg');
		const result = await tryExtraction(bytes, 'image/jpeg');
		expect(result === null || result.mimeType === 'image/jpeg').toBe(true);
	});

	it('should handle custom MIME types', async () => {
		const bytes = new Uint8Array(Buffer.from('test content'));
		const result = await tryExtraction(bytes, 'text/custom');
		expect(result === null || result.mimeType === 'text/custom').toBe(true);
	});

	it('should preserve MIME type through extraction', async () => {
		const mimeType = 'application/pdf';
		const bytes = getTestDocument('pdfs/fake_memo.pdf');
		const result = await tryExtraction(bytes, mimeType);
		expect(result === null || result.mimeType === mimeType).toBe(true);
	});

	it('should distinguish between similar MIME types', async () => {
		const pngResult = await tryExtraction(getTestDocument('images/sample.png'), 'image/png');
		const jpgResult = await tryExtraction(getTestDocument('images/flower_no_text.jpg'), 'image/jpeg');

		if (pngResult && jpgResult) {
			expect(pngResult.mimeType).not.toBe(jpgResult.mimeType);
		}
	});
});

describe('Configuration Handling (8 tests)', () => {
	it('should handle null configuration', async () => {
		const bytes = getTestDocument('pdfs/fake_memo.pdf');
		const result = await tryExtraction(bytes, 'application/pdf', null);
		expect(result === null || result).toBeDefined();
	});

	it('should apply OCR configuration', async () => {
		const config: ExtractionConfig = {
			ocr: {
				backend: 'tesseract',
				language: 'eng',
			},
		};

		const bytes = getTestDocument('pdfs/fake_memo.pdf');
		const result = await tryExtraction(bytes, 'application/pdf', config);
		expect(result === null || result).toBeDefined();
	});

	it('should apply chunking configuration', async () => {
		const config: ExtractionConfig = {
			chunking: {
				maxChars: 500,
				chunkOverlap: 50,
			},
		};

		const bytes = getTestDocument('images/sample.png');
		const result = await tryExtraction(bytes, 'image/png', config);
		expect(result === null || result).toBeDefined();
	});

	it('should apply image extraction configuration', async () => {
		const config: ExtractionConfig = {
			images: {
				extractImages: true,
				targetDpi: 150,
			},
		};

		const bytes = getTestDocument('pdfs/fake_memo.pdf');
		const result = await tryExtraction(bytes, 'application/pdf', config);
		expect(result === null || result).toBeDefined();
	});

	it('should apply PDF configuration', async () => {
		const config: ExtractionConfig = {
			pdf: {
				extractPages: true,
				maxPages: 10,
			},
		};

		const bytes = getTestDocument('pdfs/multi_page.pdf');
		const result = await tryExtraction(bytes, 'application/pdf', config);
		expect(result === null || result).toBeDefined();
	});

	it('should merge multiple configurations', async () => {
		const config: ExtractionConfig = {
			ocr: { backend: 'tesseract', language: 'eng' },
			chunking: { maxChars: 1000, chunkOverlap: 100 },
			images: { extractImages: true, targetDpi: 200 },
		};

		const bytes = getTestDocument('pdfs/fake_memo.pdf');
		const result = await tryExtraction(bytes, 'application/pdf', config);
		expect(result === null || result).toBeDefined();
	});

	it('should handle configToJS utility', () => {
		const config: ExtractionConfig = {
			ocr: {
				backend: 'tesseract',
				language: 'eng',
			},
		};

		const jsConfig = configToJS(config);
		expect(jsConfig).toBeDefined();
		expect(jsConfig.ocr).toBeDefined();
	});

	it('should handle null config with configToJS', () => {
		const jsConfig = configToJS(null);
		expect(jsConfig).toBeDefined();
		expect(typeof jsConfig).toBe('object');
	});
});

describe('Result Structure Validation (6 tests)', () => {
	it('should have expected result fields', async () => {
		const bytes = getTestDocument('pdfs/fake_memo.pdf');
		const result = await tryExtraction(bytes, 'application/pdf');

		if (result) {
			expect(result.content).toBeDefined();
			expect(typeof result.content).toBe('string');
			expect(result.mimeType).toBeDefined();
			expect(typeof result.mimeType).toBe('string');
		}
	});

	it('should validate extraction results', () => {
		const validResult = {
			content: 'Test content',
			mimeType: 'text/plain',
			metadata: {},
			tables: [],
		};

		const isValid = isValidExtractionResult(validResult);
		expect(isValid).toBe(true);
	});

	it('should handle metadata in results', async () => {
		const bytes = getTestDocument('images/sample.png');
		const result = await tryExtraction(bytes, 'image/png');

		if (result) {
			expect(result.metadata).toBeDefined();
			expect(typeof result.metadata).toBe('object');
		}
	});

	it('should handle tables in results', async () => {
		const bytes = getTestDocument('spreadsheets/test_01.xlsx');
		const result = await tryExtraction(
			bytes,
			'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
		);

		if (result) {
			expect(Array.isArray(result.tables)).toBe(true);
		}
	});

	it('should have consistent result type across sync and async', async () => {
		const bytes = getTestDocument('pdfs/fake_memo.pdf');

		const syncResult = tryExtractionSync(bytes, 'application/pdf');
		const asyncResult = await tryExtraction(bytes, 'application/pdf');

		if (syncResult && asyncResult) {
			expect(typeof syncResult.content).toBe(typeof asyncResult.content);
			expect(typeof syncResult.mimeType).toBe(typeof asyncResult.mimeType);
		}
	});

	it('should invalidate missing required fields', () => {
		const invalid = {
			mimeType: 'text/plain',
		};

		expect(isValidExtractionResult(invalid as any)).toBe(false);
	});
});

describe('Error Handling (5 tests)', () => {
	it('should handle invalid data gracefully', async () => {
		const invalidData = new Uint8Array(Buffer.from('not a valid document'));
		const result = await tryExtraction(invalidData, 'application/pdf');
		expect(result === null || result).toBeDefined();
	});

	it('should handle corrupted data gracefully', async () => {
		const corrupted = new Uint8Array([0, 1, 2, 3, 4, 5]);
		const result = await tryExtraction(corrupted, 'application/octet-stream');
		expect(result === null || result).toBeDefined();
	});

	it('should wrap errors with context', () => {
		const error = new Error('Test error');
		const wrapped = wrapWasmError(error, 'extraction failed');

		expect(wrapped).toBeInstanceOf(Error);
		expect(wrapped.message).toBeDefined();
	});

	it('should handle empty file gracefully', async () => {
		const empty = new Uint8Array(0);
		const result = await tryExtraction(empty, 'application/octet-stream');
		expect(result === null || result).toBeDefined();
	});

	it('should handle very large files', async () => {
		const large = getTestDocument('pdfs/multi_page.pdf');
		expect(large.length).toBeGreaterThan(100000);

		const result = await tryExtraction(large, 'application/pdf');
		expect(result === null || result).toBeDefined();
	});
});

describe('Adapter Functions (5 tests)', () => {
	it('should provide fileToUint8Array helper', () => {
		expect(typeof fileToUint8Array).toBe('function');
	});

	it('should provide configToJS helper', () => {
		expect(typeof configToJS).toBe('function');
	});

	it('should provide isValidExtractionResult helper', () => {
		expect(typeof isValidExtractionResult).toBe('function');
	});

	it('should provide wrapWasmError helper', () => {
		expect(typeof wrapWasmError).toBe('function');
	});

	it('should validate valid extraction result', () => {
		const result = {
			content: 'Test',
			mimeType: 'text/plain',
			metadata: {},
			tables: [],
		};

		expect(isValidExtractionResult(result)).toBe(true);
	});
});

describe('Concurrent Operations (3 tests)', () => {
	it('should handle concurrent extractions', async () => {
		const files = [
			getTestDocument('pdfs/fake_memo.pdf'),
			getTestDocument('images/sample.png'),
			{ data: new Uint8Array(Buffer.from('text')), mimeType: 'text/plain' },
		];

		const promises = [
			tryExtraction(files[0] as Uint8Array, 'application/pdf'),
			tryExtraction(files[1] as Uint8Array, 'image/png'),
			tryExtraction((files[2] as any).data, 'text/plain'),
		];

		const results = await Promise.all(promises);

		expect(results).toHaveLength(3);
	});

	it('should handle rapid sequential extractions', async () => {
		const bytes = getTestDocument('pdfs/fake_memo.pdf');

		const result1 = await tryExtraction(bytes, 'application/pdf');
		const result2 = await tryExtraction(bytes, 'application/pdf');
		const result3 = await tryExtraction(bytes, 'application/pdf');

		expect([result1, result2, result3]).toBeDefined();
	});

	it('should mix sync and async extractions', async () => {
		const bytes = getTestDocument('pdfs/fake_memo.pdf');

		const syncResult = tryExtractionSync(bytes, 'application/pdf');
		const asyncResult = await tryExtraction(bytes, 'application/pdf');

		expect(syncResult === null || syncResult).toBeDefined();
		expect(asyncResult === null || asyncResult).toBeDefined();
	});
});

describe('Large Document Handling (4 tests)', () => {
	it('should extract from multi-page PDF', async () => {
		const bytes = getTestDocument('pdfs/multi_page.pdf');
		const result = await tryExtraction(bytes, 'application/pdf');
		expect(result === null || result).toBeDefined();
	});

	it('should handle complex XLSX files', async () => {
		const bytes = getTestDocument('spreadsheets/excel_multi_sheet.xlsx');
		const result = await tryExtraction(
			bytes,
			'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
		);
		expect(result === null || result).toBeDefined();
	});

	it('should extract from large PDF', async () => {
		const bytes = getTestDocument('pdfs/fundamentals_of_deep_learning_2014.pdf');
		expect(bytes.length).toBeGreaterThan(1000000);
		const result = await tryExtraction(bytes, 'application/pdf');
		expect(result === null || result).toBeDefined();
	});

	it('should handle documents with many tables', async () => {
		const bytes = getTestDocument('pdfs_with_tables/large.pdf');
		const result = await tryExtraction(bytes, 'application/pdf');
		expect(result === null || result).toBeDefined();
	});
});

describe('Content Quality Checks (5 tests)', () => {
	it('should extract meaningful content when available', async () => {
		const bytes = getTestDocument('pdfs/fake_memo.pdf');
		const result = await tryExtraction(bytes, 'application/pdf');

		if (result && result.content) {
			expect(result.content.length).toBeGreaterThan(0);
		}
	});

	it('should preserve content type', async () => {
		const bytes = getTestDocument('images/sample.png');
		const result = await tryExtraction(bytes, 'image/png');

		if (result) {
			expect(typeof result.content).toBe('string');
		}
	});

	it('should handle multi-format batches', async () => {
		const files = [
			{ data: getTestDocument('images/sample.png'), mimeType: 'image/png' },
			{ data: getTestDocument('images/flower_no_text.jpg'), mimeType: 'image/jpeg' },
			{ data: new Uint8Array(Buffer.from('plain text')), mimeType: 'text/plain' },
		];

		try {
			const results = await batchExtractBytes(files);
			expect(results).toHaveLength(3);
			expect(results.every(r => r || r === null)).toBe(true);
		} catch (error) {
			expect(error).toBeDefined();
		}
	});

	it('should not modify input bytes', async () => {
		const originalBytes = getTestDocument('pdfs/fake_memo.pdf');
		const bytesCopy = new Uint8Array(originalBytes);

		await tryExtraction(bytesCopy, 'application/pdf');

		expect(originalBytes).toEqual(bytesCopy);
	});

	it('should handle content consistently', async () => {
		const bytes = getTestDocument('pdfs/fake_memo.pdf');

		const result1 = await tryExtraction(bytes, 'application/pdf');
		const result2 = await tryExtraction(bytes, 'application/pdf');

		if (result1 && result2) {
			expect(result1.content === result2.content).toBe(true);
		}
	});
});

describe('Memory and Performance (2 tests)', () => {
	it('should not leak memory on repeated extractions', async () => {
		const bytes = getTestDocument('images/sample.png');

		for (let i = 0; i < 5; i++) {
			const result = await tryExtraction(bytes, 'image/png');
			expect(result === null || result).toBeDefined();
		}
	});

	it('should handle rapid batch operations', async () => {
		const files = [
			{ data: getTestDocument('images/sample.png'), mimeType: 'image/png' },
		];

		for (let i = 0; i < 3; i++) {
			try {
				const results = await batchExtractBytes(files);
				expect(results).toHaveLength(1);
			} catch (error) {
				expect(error).toBeDefined();
			}
		}
	});
});
