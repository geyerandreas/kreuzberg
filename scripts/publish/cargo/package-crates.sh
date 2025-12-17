#!/usr/bin/env bash

set -euo pipefail

release_version="${RELEASE_VERSION:-unknown}"

tesseract_packaged=0
tesseract_status=0
cargo package -p kreuzberg-tesseract --allow-dirty || tesseract_status=$?

if [ "$tesseract_status" -eq 0 ]; then
	tesseract_packaged=1
else
	echo "::warning::Skipping kreuzberg-tesseract crate packaging."
fi

core_status=0
core_packaged=0
cargo package -p kreuzberg --allow-dirty || core_status=$?

if [ "$core_status" -ne 0 ]; then
	echo "::warning::kreuzberg crate packaging failed verification (likely due to prerelease dependency indexing). Retrying with --no-verify."
	core_status=0
	cargo package -p kreuzberg --allow-dirty --no-verify || core_status=$?
fi

if [ "$core_status" -eq 0 ]; then
	core_packaged=1
fi

cli_packaged=0
cli_status=0
cargo package -p kreuzberg-cli --allow-dirty --no-verify || cli_status=$?

if [ "$cli_status" -eq 0 ]; then
	cli_packaged=1
else
	echo "::warning::Skipping kreuzberg-cli crate packaging; kreuzberg ${release_version} is not yet available on crates.io."
fi

mkdir -p crate-artifacts
if [ "$tesseract_packaged" -eq 1 ]; then
	cp target/package/kreuzberg-tesseract-*.crate crate-artifacts/
fi
if [ "$core_packaged" -eq 1 ]; then
	cp target/package/kreuzberg-*.crate crate-artifacts/
else
	echo "::warning::kreuzberg crate could not be packaged. It will need to be packaged after tesseract-rs is published and indexed."
fi
if [ "$cli_packaged" -eq 1 ]; then
	cp target/package/kreuzberg-cli-*.crate crate-artifacts/
fi
