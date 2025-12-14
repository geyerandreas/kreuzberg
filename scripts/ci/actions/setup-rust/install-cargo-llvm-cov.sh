#!/usr/bin/env bash
set -euo pipefail

if ! command -v cargo-llvm-cov &>/dev/null; then
	echo "Installing cargo-llvm-cov..."
	cargo install cargo-llvm-cov
else
	echo "cargo-llvm-cov already installed"
fi
