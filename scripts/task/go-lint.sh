#!/usr/bin/env bash
set -euo pipefail

mode="${1:-check}"

root="$(git rev-parse --show-toplevel)"
go_dir="$root/packages/go/v4"

cd "$go_dir"
export PKG_CONFIG_PATH="$root/crates/kreuzberg-ffi:${PKG_CONFIG_PATH:-}"
export DYLD_LIBRARY_PATH="$root/target/debug:${DYLD_LIBRARY_PATH:-}"
export LD_LIBRARY_PATH="$root/target/debug:${LD_LIBRARY_PATH:-}"

case "$mode" in
fix)
	go fmt ./...
	golangci-lint run --config "$root/.golangci.yml" --fix ./...
	;;
check)
	"$root/scripts/go/format_check.sh"
	golangci-lint run --config "$root/.golangci.yml" ./...
	;;
*)
	echo "Usage: $0 [fix|check]" >&2
	exit 2
	;;
esac
