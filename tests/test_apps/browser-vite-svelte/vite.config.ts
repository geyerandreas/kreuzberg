import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";

// Custom plugin to handle dynamic WASM imports that are resolved at runtime
function wasmImportPlugin() {
	return {
		name: "wasm-dynamic-import",
		resolveId: (id: string) => {
			// Allow dynamic WASM imports to pass through without resolution
			if (id.includes("kreuzberg_wasm.js") || id.includes("pdfium.js")) {
				return { id, external: true };
			}
			return null;
		},
	};
}

// https://vite.dev/config/
export default defineConfig({
	plugins: [wasmImportPlugin(), svelte()],
});
