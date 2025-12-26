#!/usr/bin/env bash
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo "===== Kreuzberg CLI Installation Test ====="
echo

# Check if cargo is available
if ! command -v cargo &>/dev/null; then
	echo -e "${RED}✗ cargo not found. Please install Rust toolchain.${NC}"
	exit 1
fi

echo -e "${GREEN}✓ cargo found${NC}"

# Install kreuzberg-cli from crates.io
echo
echo "Installing kreuzberg-cli from crates.io..."
if cargo install kreuzberg-cli --force; then
	echo -e "${GREEN}✓ Installation successful${NC}"
else
	echo -e "${RED}✗ Installation failed${NC}"
	exit 1
fi

# Verify binary is in PATH
echo
echo "Verifying kreuzberg binary..."
if command -v kreuzberg &>/dev/null; then
	echo -e "${GREEN}✓ kreuzberg binary found in PATH${NC}"
else
	echo -e "${RED}✗ kreuzberg binary not found in PATH${NC}"
	exit 1
fi

# Check version
echo
echo "Checking version..."
if kreuzberg --version; then
	echo -e "${GREEN}✓ Version check successful${NC}"
else
	echo -e "${RED}✗ Version check failed${NC}"
	exit 1
fi

# Check help output
echo
echo "Checking help output..."
if kreuzberg --help >/dev/null; then
	echo -e "${GREEN}✓ Help output successful${NC}"
else
	echo -e "${RED}✗ Help output failed${NC}"
	exit 1
fi

echo
echo -e "${GREEN}===== CLI Installation Test PASSED =====${NC}"
