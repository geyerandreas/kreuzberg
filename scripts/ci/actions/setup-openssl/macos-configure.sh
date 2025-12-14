#!/usr/bin/env bash
set -euo pipefail

prefix="$(brew --prefix openssl@3 2>/dev/null || brew --prefix openssl 2>/dev/null || true)"
if [ -z "$prefix" ]; then
	echo "Failed to locate Homebrew OpenSSL prefix" >&2
	exit 1
fi

{
	echo "OPENSSL_DIR=$prefix"
	echo "OPENSSL_LIB_DIR=$prefix/lib"
	echo "OPENSSL_INCLUDE_DIR=$prefix/include"
	echo "PKG_CONFIG_PATH=$prefix/lib/pkgconfig:${PKG_CONFIG_PATH:-}"
} >>"$GITHUB_ENV"
