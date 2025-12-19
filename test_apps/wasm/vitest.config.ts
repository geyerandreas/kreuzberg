import { defineConfig } from 'vitest/config';
import path from 'path';

export default defineConfig({
	test: {
		environment: 'node',
		globals: true,
		coverage: {
			provider: 'v8',
			reporter: ['text', 'json', 'html'],
			exclude: [
				'node_modules/',
				'dist/',
				'**/*.spec.ts',
				'**/*.test.ts',
			],
		},
		include: ['tests/**/*.spec.ts', 'tests/**/*.test.ts'],
		exclude: ['node_modules', 'dist', '.idea', '.git', '.cache'],
		testTimeout: 60000,
		hookTimeout: 60000,
		teardownTimeout: 10000,
		isolate: true,
		threads: true,
		maxThreads: 4,
		minThreads: 1,
	},
	resolve: {
		alias: {
			'@': path.resolve(__dirname, './'),
		},
	},
});
