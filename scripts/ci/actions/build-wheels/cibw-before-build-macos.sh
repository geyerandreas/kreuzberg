#!/usr/bin/env bash
set -euo pipefail

python -m pip install --upgrade pip maturin build

determine_arch() {
	if [ -n "${CIBW_BUILD:-}" ]; then
		case "${CIBW_BUILD}" in
		*-macosx_arm64*)
			echo "arm64"
			return
			;;
		*-macosx_x86_64*)
			echo "x86_64"
			return
			;;
		*-macosx_universal2*)
			echo "arm64"
			return
			;;
		esac
	fi
	if [ -n "${CIBUILDWHEEL_ARCH:-}" ]; then
		echo "${CIBUILDWHEEL_ARCH}"
		return
	fi
	uname -m
}

ARCH="$(determine_arch)"
ORT_DIR="/tmp/onnxruntime/macos/${ARCH}"

export ORT_STRATEGY=system
export ORT_LIB_LOCATION="${ORT_DIR}/onnxruntime"
export ORT_SKIP_DOWNLOAD=1
export ORT_PREFER_DYNAMIC_LINK=0
