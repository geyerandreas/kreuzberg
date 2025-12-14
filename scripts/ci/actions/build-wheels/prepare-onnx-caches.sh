#!/usr/bin/env bash
set -euo pipefail

if [ "${RUNNER_OS}" = "Linux" ]; then
	archs="x86_64 aarch64"
	base="/tmp/onnxruntime/linux"
elif [ "${RUNNER_OS}" = "macOS" ]; then
	archs="x86_64 arm64"
	base="/tmp/onnxruntime/macos"
else
	exit 0
fi

mkdir -p "${base}"
for arch in ${archs}; do
	case "${RUNNER_OS}:${arch}" in
	Linux:x86_64)
		ort_url="https://cdn.pyke.io/0/pyke:ort-rs/ms@1.22.0/x86_64-unknown-linux-gnu.tgz"
		;;
	Linux:aarch64)
		ort_url="https://cdn.pyke.io/0/pyke:ort-rs/ms@1.22.0/aarch64-unknown-linux-gnu.tgz"
		;;
	macOS:x86_64)
		ort_url="https://cdn.pyke.io/0/pyke:ort-rs/ms@1.22.0/x86_64-apple-darwin.tgz"
		;;
	macOS:arm64)
		ort_url="https://cdn.pyke.io/0/pyke:ort-rs/ms@1.22.0/aarch64-apple-darwin.tgz"
		;;
	*)
		echo "Skipping unsupported combination ${RUNNER_OS}:${arch}"
		continue
		;;
	esac
	dest="${base}/${arch}"
	if [ ! -f "${dest}/onnxruntime/lib/libonnxruntime.a" ]; then
		mkdir -p "${dest}"
		curl -fsSL "${ort_url}" | tar -xz -C "${dest}"
	fi
done
