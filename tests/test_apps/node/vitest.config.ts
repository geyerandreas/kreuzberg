import { defineConfig } from "vitest/config";

export default defineConfig({
	test: {
		environment: "node",
		timeout: 120_000,
		include: ["tests/**/*.test.ts"],
		globals: true,
	},
});
