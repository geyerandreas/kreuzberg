#!/usr/bin/env bash

set -euo pipefail

# Install cross-compilation toolchain (no multiarch needed)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd)}"

source "$REPO_ROOT/scripts/lib/retry.sh"

echo "::group::Installing aarch64 Linux cross toolchain"

if ! retry_with_backoff sudo apt-get update; then
	echo "::error::apt-get update failed after retries" >&2
	exit 1
fi

if ! retry_with_backoff_timeout 900 sudo apt-get install -y \
	gcc-aarch64-linux-gnu \
	g++-aarch64-linux-gnu \
	binutils-aarch64-linux-gnu \
	pkg-config-aarch64-linux-gnu; then
	echo "::error::apt-get install cross toolchain failed" >&2
	exit 1
fi

echo "::endgroup::"

{
	echo "CC_aarch64_unknown_linux_gnu=aarch64-linux-gnu-gcc"
	echo "CXX_aarch64_unknown_linux_gnu=aarch64-linux-gnu-g++"
	echo "AR_aarch64_unknown_linux_gnu=aarch64-linux-gnu-ar"
	echo "CARGO_TARGET_AARCH64_UNKNOWN_LINUX_GNU_LINKER=aarch64-linux-gnu-gcc"
} >>"${GITHUB_ENV:?GITHUB_ENV not set}"

{
	echo "PKG_CONFIG_ALLOW_CROSS=1"
	echo "PKG_CONFIG_aarch64_unknown_linux_gnu=aarch64-linux-gnu-pkg-config"
} >>"${GITHUB_ENV:?GITHUB_ENV not set}"
