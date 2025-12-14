#!/usr/bin/env bash
set -euo pipefail

ffi_lib_dir="${1:?ffi-lib-dir is required}"

REPO_ROOT="${GITHUB_WORKSPACE}"
FFI_PATH="${REPO_ROOT}/${ffi_lib_dir}"

# cgo compilation flags
CGO_ENABLED=1
CGO_CFLAGS="-I${REPO_ROOT}/crates/kreuzberg-ffi/include"
CGO_LDFLAGS="-L${FFI_PATH} -lkreuzberg_ffi"

# Add rpath for runtime library resolution (macOS and Linux)
if [ "$RUNNER_OS" = "macOS" ]; then
	CGO_LDFLAGS="${CGO_LDFLAGS} -Wl,-rpath,${FFI_PATH}"
elif [ "$RUNNER_OS" = "Linux" ]; then
	CGO_LDFLAGS="${CGO_LDFLAGS} -Wl,-rpath,${FFI_PATH}"
fi

# Export to GITHUB_ENV
{
	echo "CGO_ENABLED=${CGO_ENABLED}"
	echo "CGO_CFLAGS=${CGO_CFLAGS}"
	echo "CGO_LDFLAGS=${CGO_LDFLAGS}"
} >>"$GITHUB_ENV"

echo "✓ Go cgo environment configured"
