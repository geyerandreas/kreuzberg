#!/usr/bin/env bash
set -euo pipefail

mode="${1:?mode is required (full|minimal)}"
ffi_lib_dir="${2:?ffi-lib-dir is required}"

REPO_ROOT="${GITHUB_WORKSPACE}"
echo "REPO_ROOT=${REPO_ROOT}" >>"$GITHUB_ENV"

# Initialize path variables
LD_LIBRARY_PATH="${REPO_ROOT}/${ffi_lib_dir}:${LD_LIBRARY_PATH:-}"
DYLD_LIBRARY_PATH="${REPO_ROOT}/${ffi_lib_dir}:${DYLD_LIBRARY_PATH:-}"
DYLD_FALLBACK_LIBRARY_PATH="${REPO_ROOT}/${ffi_lib_dir}:${DYLD_FALLBACK_LIBRARY_PATH:-}"
PKG_CONFIG_PATH="${REPO_ROOT}/crates/kreuzberg-ffi:${PKG_CONFIG_PATH:-}"

# Add PDFium paths if KREUZBERG_PDFIUM_PREBUILT is set
if [ -n "${KREUZBERG_PDFIUM_PREBUILT:-}" ]; then
	LD_LIBRARY_PATH="${KREUZBERG_PDFIUM_PREBUILT}/lib:${LD_LIBRARY_PATH}"
	DYLD_LIBRARY_PATH="${KREUZBERG_PDFIUM_PREBUILT}/lib:${DYLD_LIBRARY_PATH}"
	DYLD_FALLBACK_LIBRARY_PATH="${KREUZBERG_PDFIUM_PREBUILT}/lib:${DYLD_FALLBACK_LIBRARY_PATH}"
	echo "✓ PDFium paths configured"
fi

# Add ONNX Runtime paths if ORT_LIB_LOCATION is set (only for full mode)
if [ "${mode}" = "full" ] && [ -n "${ORT_LIB_LOCATION:-}" ]; then
	LD_LIBRARY_PATH="${ORT_LIB_LOCATION}:${LD_LIBRARY_PATH}"
	DYLD_LIBRARY_PATH="${ORT_LIB_LOCATION}:${DYLD_LIBRARY_PATH}"
	DYLD_FALLBACK_LIBRARY_PATH="${ORT_LIB_LOCATION}:${DYLD_FALLBACK_LIBRARY_PATH}"
	echo "✓ ONNX Runtime paths configured"
fi

# Export to GITHUB_ENV for persistence
{
	echo "LD_LIBRARY_PATH=${LD_LIBRARY_PATH}"
	echo "DYLD_LIBRARY_PATH=${DYLD_LIBRARY_PATH}"
	echo "DYLD_FALLBACK_LIBRARY_PATH=${DYLD_FALLBACK_LIBRARY_PATH}"
	echo "PKG_CONFIG_PATH=${PKG_CONFIG_PATH}"
} >>"$GITHUB_ENV"

# Output for action consumers
{
	echo "ld-library-path=${LD_LIBRARY_PATH}"
	echo "pkg-config-path=${PKG_CONFIG_PATH}"
} >>"$GITHUB_OUTPUT"

echo "✓ Unix library paths configured"
