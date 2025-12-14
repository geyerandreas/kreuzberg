#!/usr/bin/env bash
set -euo pipefail

fail=0
for key in LINT_AND_FORMAT UNIT_TESTS BUILD_WASM_TARGETS BUNDLE_SIZE_CHECK TYPE_DEFINITIONS INTEGRATION_TESTS_NODE DENO_TESTS WORKERS_TESTS; do
	val="${!key:-}"
	if [[ "$val" == "failure" ]]; then
		fail=1
	fi
done

if [ "$fail" -eq 1 ]; then
	echo "One or more WASM CI checks failed"
	exit 1
fi

echo "All WASM CI checks passed!"
