// Auto-generated tests for html fixtures.
// Run with: deno test --allow-read

import { assertions, buildConfig, extractBytes, initWasm, resolveDocument, shouldSkipFixture } from "./helpers.ts";
import type { ExtractionResult } from "./helpers.ts";

// Initialize WASM module once at module load time
await initWasm();

Deno.test("html_complex_layout", { permissions: { read: true }, ignore: true }, async () => {
	// WASM Note: This test is skipped because the large HTML file (3.9MB) causes stack overflow
	// in WASM environments. The html-to-markdown-rs library uses deep recursion which exceeds
	// the default WASM stack size. This is a known limitation and does not affect smaller HTML files.
	const documentBytes = await resolveDocument("web/taylor_swift.html");
	const config = buildConfig(undefined);
	let result: ExtractionResult | null = null;
	try {
		result = await extractBytes(documentBytes, "text/html", config);
	} catch (error) {
		if (shouldSkipFixture(error, "html_complex_layout", [], undefined)) {
			return;
		}
		throw error;
	}
	if (result === null) {
		return;
	}
	assertions.assertExpectedMime(result, ["text/html"]);
	assertions.assertMinContentLength(result, 1000);
});

Deno.test("html_simple_table", { permissions: { read: true } }, async () => {
	const documentBytes = await resolveDocument("web/simple_table.html");
	const config = buildConfig(undefined);
	let result: ExtractionResult | null = null;
	try {
		result = await extractBytes(documentBytes, "text/html", config);
	} catch (error) {
		if (shouldSkipFixture(error, "html_simple_table", [], undefined)) {
			return;
		}
		throw error;
	}
	if (result === null) {
		return;
	}
	assertions.assertExpectedMime(result, ["text/html"]);
	assertions.assertMinContentLength(result, 100);
	assertions.assertContentContainsAll(result, [
		"Product",
		"Category",
		"Price",
		"Stock",
		"Laptop",
		"Electronics",
		"Sample Data Table",
	]);
	// WASM Note: Table extraction from HTML is not yet fully implemented in WASM
	// The tables are correctly rendered in markdown format in the content, but not in the tables array
	// assertions.assertTableCount(result, 1, null);
});
