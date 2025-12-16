#!/usr/bin/env node
/**
 * Post-build script to fix missing type exports in generated .d.ts files
 * Ensures ExtractionConfig and ExtractionResult are exported from the main entry point
 */

import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const distDir = path.join(__dirname, "..", "dist");

/**
 * Fix type exports in a .d.ts or .d.mts file
 * @param {string} filePath - Path to the file to fix
 */
function fixTypeExports(filePath) {
	try {
		if (!fs.existsSync(filePath)) {
			console.warn(`File not found: ${filePath}`);
			return;
		}

		let content = fs.readFileSync(filePath, "utf-8");

		// Determine the correct module reference from the import statement
		let moduleRef = "./types-trZHSOJv.js"; // default
		const importMatch = content.match(/from ['"]\.\/types-trZHSOJv\.(js|mjs)['"]/);
		if (importMatch) {
			moduleRef = `./types-trZHSOJv.${importMatch[1]}`;
		}

		// Build the corrected export statement with all types
		const correctedExport = `export { C as Chunk, d as ChunkMetadata, b as ChunkingConfig, c as ExtractedImage, E as ExtractionConfig, I as ImageExtractionConfig, L as LanguageDetectionConfig, M as Metadata, a as ExtractionResult, f as OcrBackendProtocol, O as OcrConfig, e as PageContent, P as PageExtractionConfig, T as Table } from '${moduleRef}';`;

		// Find and replace the export statement that doesn't include ExtractionConfig
		const lines = content.split("\n");
		let replaced = false;
		let foundCorrectExport = false;

		for (let i = 0; i < lines.length; i++) {
			const line = lines[i];
			if (line.startsWith("export {") && line.includes("from './types-trZHSOJv.")) {
				// Check if it already has "E as ExtractionConfig" (the correctly mangled form)
				if (line.includes("E as ExtractionConfig") && line.includes("a as ExtractionResult")) {
					foundCorrectExport = true;
				} else {
					// Replace with corrected export
					lines[i] = correctedExport;
					replaced = true;
				}
				break;
			}
		}

		if (replaced) {
			content = lines.join("\n");
			fs.writeFileSync(filePath, content);
			console.log(`✓ Fixed type exports in ${path.basename(filePath)}`);
		} else if (foundCorrectExport) {
			console.log(`✓ ${path.basename(filePath)} already has correct exports`);
		} else {
			console.log(`- No changes needed for ${path.basename(filePath)}`);
		}
	} catch (error) {
		console.error(`✗ Error fixing ${filePath}:`, error.message);
		process.exit(1);
	}
}

// Main execution
console.log("Fixing type exports in generated .d.ts files...\n");

fixTypeExports(path.join(distDir, "index.d.ts"));
fixTypeExports(path.join(distDir, "index.d.mts"));

console.log("\nType export fixes complete!");
