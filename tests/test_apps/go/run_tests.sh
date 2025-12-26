#!/bin/bash
set -e

export DYLD_LIBRARY_PATH=/Users/naamanhirschfeld/workspace/kreuzberg-dev/kreuzberg/target/release:$DYLD_LIBRARY_PATH
export LD_LIBRARY_PATH=/Users/naamanhirschfeld/workspace/kreuzberg-dev/kreuzberg/target/release:$LD_LIBRARY_PATH
export PKG_CONFIG_PATH=/Users/naamanhirschfeld/workspace/kreuzberg-dev/kreuzberg/crates/kreuzberg-ffi:$PKG_CONFIG_PATH

cd /Users/naamanhirschfeld/workspace/kreuzberg-dev/kreuzberg/test_apps/go
go test -v ./...
