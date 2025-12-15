import { defineConfig } from "tsup";

export default defineConfig({
	entry: [
		"typescript/index.ts",
		"typescript/runtime.ts",
		"typescript/adapters/wasm-adapter.ts",
		"typescript/ocr/registry.ts",
		"typescript/ocr/tesseract-wasm-backend.ts",
	],
	format: ["esm", "cjs"],
	bundle: true,
	dts: {
		compilerOptions: {
			skipLibCheck: true,
			skipDefaultLibCheck: true,
		},
	},
	splitting: false,
	sourcemap: true,
	clean: true,
	shims: false,
	platform: "neutral",
	target: "es2022",
	external: ["@kreuzberg/core", /\.wasm$/, /@kreuzberg\/wasm-.*/, /\.\.\/pkg\/.*/, "./index.js", "../index.js"],
});
