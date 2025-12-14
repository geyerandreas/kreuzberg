#!/usr/bin/env bash
set -euo pipefail

./target/release/benchmark-harness run \
	--fixtures benchmark-results/ \
	--output benchmark-output/ \
	--format html
