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

		// Detect the actual types file name from imports
		let moduleRef = null;
		const moduleAlias = null;

		// Look for imports from the types file (could be types-*.mjs or types-*.d.mts)
		const typeImportMatch = content.match(/import\s+{([^}]+)}\s+from\s+['"](\.\/(types-[^\s'"]+))['"];?/);
		if (typeImportMatch) {
			const importPath = typeImportMatch[2];
			// Extract the module reference without extension
			const baseModule = importPath.replace(/\.(mjs|d\.mts|d\.ts|js)$/, "");
			// For .d.mts files, reference .d.mts; for .d.ts files, use .js
			if (filePath.endsWith(".d.mts")) {
				moduleRef = `${baseModule}.d.mts`;
			} else {
				moduleRef = `${baseModule}.js`;
			}

			// Parse the named imports to get type aliases
			const imports = typeImportMatch[1];
			// This regex captures the mappings like "E as ExtractionConfig"
		}

		if (!moduleRef) {
			console.log(`- Could not determine types module for ${path.basename(filePath)}`);
			return;
		}

		// Build the corrected import and export statements with all types
		// For declaration files, use .d.ts extension to reference other declaration files
		let importModuleRef = moduleRef;
		if (!filePath.endsWith(".d.mts") && !filePath.endsWith(".d.cts")) {
			// For .d.ts files, change .js to .d.ts
			importModuleRef = moduleRef.replace(/\.js$/, ".d.ts");
		}
		const correctedImport = `import { E as ExtractionConfig, a as ExtractionResult } from '${importModuleRef}';`;
		const correctedExport = `export { C as Chunk, b as ChunkingConfig, c as ChunkMetadata, d as ExtractedImage, I as ImageExtractionConfig, L as LanguageDetectionConfig, M as Metadata, O as OcrBackendProtocol, e as OcrConfig, P as PageContent, f as PageExtractionConfig, g as PdfConfig, h as PostProcessorConfig, T as Table, i as TesseractConfig, j as TokenReductionConfig, E as ExtractionConfig, a as ExtractionResult } from '${importModuleRef}';`;

		// Find and replace both import and export statements
		const lines = content.split("\n");
		let replaced = false;
		let foundCorrectExport = false;
		let importFixed = false;
		let duplicateRemoved = false;
		let runtimeFixed = false;

		for (let i = 0; i < lines.length; i++) {
			let line = lines[i];

			// Fix import statement
			if (line.startsWith("import {") && /from\s+['"]\.\/types-[^'"]+['"]/.test(line)) {
				// Check if the import already uses the correct extension
				if (!line.includes(importModuleRef)) {
					lines[i] = correctedImport;
					importFixed = true;
				}
			}

			// Fix export statement from types file
			if (line.startsWith("export {") && /from\s+['"]\.\/types-[^'"]+['"]/.test(line)) {
				// Check if it already has both key types and correct module ref
				if (line.includes("ExtractionConfig") && line.includes("ExtractionResult") && line.includes(importModuleRef)) {
					foundCorrectExport = true;
				} else if (line.includes("from")) {
					// Replace with corrected export
					lines[i] = correctedExport;
					replaced = true;
				}
			}

			// Remove duplicate export at the end that re-exports ExtractionConfig and ExtractionResult
			// This is typically: export { ExtractionConfig, ExtractionResult, batchExtractBytes, ... };
			if (
				line.startsWith("export {") &&
				!line.includes("from") &&
				line.includes("ExtractionConfig") &&
				line.includes("ExtractionResult")
			) {
				// Remove ExtractionConfig and ExtractionResult from this export
				const exportContent = line.match(/export\s+\{([^}]+)\}/)?.[1];
				if (exportContent) {
					const exports = exportContent
						.split(",")
						.map((e) => e.trim())
						.filter((e) => {
							return e !== "ExtractionConfig" && e !== "ExtractionResult";
						});
					if (exports.length > 0) {
						lines[i] = `export { ${exports.join(", ")} };`;
						duplicateRemoved = true;
					} else {
						// If no other exports, remove the line entirely
						lines[i] = "";
						duplicateRemoved = true;
					}
				}
			}

			// Fix runtime exports to use 'type' keyword for type-only exports
			// export { RuntimeType, WasmCapabilities, ... } from './runtime.js'
			// should be: export { type RuntimeType, type WasmCapabilities, ... } from './runtime.d.ts'
			if (line.includes("from './runtime") && (line.includes("RuntimeType") || line.includes("WasmCapabilities"))) {
				// Replace the export to add 'type' keyword before type-only exports
				line = line.replace(/(\sRuntimeType(?=\s*,|\s*\}|\s*from))/g, " type RuntimeType");
				line = line.replace(/(\sWasmCapabilities(?=\s*,|\s*\}|\s*from))/g, " type WasmCapabilities");
				// Fix the module reference to point to declaration files for type-only exports
				// This is crucial for type checkers to find the type definitions
				if (filePath.endsWith(".d.mts")) {
					line = line.replace(/from\s+['"]\.\/runtime\.js['"]/, "from './runtime.d.mts'");
				} else if (filePath.endsWith(".d.cts")) {
					line = line.replace(/from\s+['"]\.\/runtime\.cjs['"]/, "from './runtime.d.cts'");
				} else if (filePath.endsWith(".d.ts")) {
					// For regular .d.ts files, also point to .d.ts
					line = line.replace(/from\s+['"]\.\/runtime\.js['"]/, "from './runtime.d.ts'");
				}
				lines[i] = line;
				runtimeFixed = true;
			}

			// Fix runtime.mjs references to runtime.d.mts for .d.mts files
			// export { RuntimeType, ... } from './runtime.mjs' should be './runtime.d.mts'
			if (filePath.endsWith(".d.mts") && line.includes("from './runtime.mjs'") && line.includes("RuntimeType")) {
				line = line.replace("from './runtime.mjs'", "from './runtime.d.mts'");
				lines[i] = line;
				runtimeFixed = true;
			}

			// Fix other .mjs references in .d.mts files to .d.mts
			if (filePath.endsWith(".d.mts") && /from\s+['"]\.\/(adapters|ocr)\/[^'"]+\.mjs['"]/.test(line)) {
				line = line.replace(/\.mjs'/g, ".d.mts'").replace(/\.mjs"/g, '.d.mts"');
				lines[i] = line;
				runtimeFixed = true;
			}
		}

		if (replaced || importFixed || duplicateRemoved || runtimeFixed) {
			content = lines.join("\n");
			fs.writeFileSync(filePath, content);
			const changes = [];
			if (importFixed) changes.push("imports");
			if (replaced) changes.push("exports");
			if (duplicateRemoved) changes.push("duplicates");
			if (runtimeFixed) changes.push("module references");
			console.log(`✓ Fixed type ${changes.join(" and ")} in ${path.basename(filePath)}`);
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

/**
 * Recursively find all .d.ts, .d.mts, and .d.cts files
 * @param {string} dir - Directory to search
 * @returns {string[]} Array of file paths
 */
function findTypeDefinitions(dir) {
	const files = [];
	const entries = fs.readdirSync(dir, { withFileTypes: true });

	for (const entry of entries) {
		const fullPath = path.join(dir, entry.name);
		if (entry.isDirectory()) {
			files.push(...findTypeDefinitions(fullPath));
		} else if (entry.name.endsWith(".d.ts") || entry.name.endsWith(".d.mts") || entry.name.endsWith(".d.cts")) {
			files.push(fullPath);
		}
	}

	return files;
}

// Main execution
console.log("Fixing type exports in generated .d.ts files...\n");

const typeFiles = findTypeDefinitions(distDir);
for (const file of typeFiles) {
	fixTypeExports(file);
}

// Fix any remaining .mjs references in .d.mts files to .d.mts
console.log("\nFixing remaining type references in .d.mts files...");
const dmtsFiles = typeFiles.filter((f) => f.endsWith(".d.mts"));
for (const file of dmtsFiles) {
	try {
		let content = fs.readFileSync(file, "utf-8");
		const originalContent = content;

		// Fix types-*.mjs references to types-*.d.mts
		content = content.replace(/types-([^'"/]+)\.mjs/g, "types-$1.d.mts");

		if (content !== originalContent) {
			fs.writeFileSync(file, content);
			console.log(`✓ Fixed remaining references in ${path.basename(file)}`);
		}
	} catch (error) {
		console.error(`✗ Error fixing ${file}:`, error.message);
	}
}

console.log("\nType export fixes complete!");
