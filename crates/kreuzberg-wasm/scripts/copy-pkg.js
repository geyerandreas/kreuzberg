#!/usr/bin/env node
/**
 * Post-build script to copy pkg directory to dist and fix import paths
 */

import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const pkg = path.join(__dirname, "..", "pkg");
const dist = path.join(__dirname, "..", "dist");
const distPkg = path.join(dist, "pkg");

// Copy pkg directory to dist/pkg
if (fs.existsSync(pkg)) {
	fs.cpSync(pkg, distPkg, { recursive: true, force: true });
	console.log("Copied pkg directory to dist/pkg");
} else {
	console.warn("pkg directory not found");
	process.exit(1);
}

// Fix import paths in dist/index.js and dist/index.cjs
const files = [
	path.join(dist, "index.js"),
	path.join(dist, "index.cjs"),
];

for (const file of files) {
	if (fs.existsSync(file)) {
		let content = fs.readFileSync(file, "utf-8");
		const original = content;

		// Replace ../pkg/ with ./pkg/
		content = content.replace(/import\("\.\.\/pkg\/kreuzberg_wasm\.js"\)/g, 'import("./pkg/kreuzberg_wasm.js")');

		if (content !== original) {
			fs.writeFileSync(file, content);
			console.log(`Fixed import paths in ${path.basename(file)}`);
		}
	}
}

console.log("Copy and path fixing complete!");
