import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const rootDir = path.join(__dirname, "..");
const pkgDir = path.join(rootDir, "node_modules/@kreuzberg/wasm/dist/pkg");
const srcDir = path.join(__dirname, "../../..", "kreuzberg/crates/kreuzberg-wasm/pkg");

function copyWasmFiles() {
	try {
		if (!fs.existsSync(pkgDir)) {
			fs.mkdirSync(pkgDir, { recursive: true });
		}

		if (!fs.existsSync(srcDir)) {
			console.warn("Warning: WASM source directory not found at:", srcDir);
			console.warn("Ensure kreuzberg/crates/kreuzberg-wasm has been built with: npm run build");
			return;
		}

		const files = fs.readdirSync(srcDir);
		const wasmFiles = files.filter(
			(f) => f.startsWith("kreuzberg_wasm") || f === "LICENSE" || f === "README.md" || f === "package.json",
		);

		for (const file of wasmFiles) {
			const src = path.join(srcDir, file);
			const dest = path.join(pkgDir, file);

			if (fs.statSync(src).isFile()) {
				fs.copyFileSync(src, dest);
				console.log(`Copied ${file}`);
			}
		}

		console.log("WASM binaries setup complete!");
	} catch (error) {
		console.error("Error setting up WASM binaries:", error.message);
		process.exit(1);
	}
}

copyWasmFiles();
