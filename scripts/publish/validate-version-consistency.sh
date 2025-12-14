#!/usr/bin/env bash
set -euo pipefail

expected="${1:-${EXPECTED_VERSION:-}}"
if [ -z "$expected" ]; then
	echo "Usage: $0 <expected-version> (or set EXPECTED_VERSION)" >&2
	exit 2
fi

errors=0

echo "Expected version: $expected"
echo "----------------------------------------"

# Rust workspace (Cargo.toml)
cargo_version="$(grep '^version' Cargo.toml | head -1 | cut -d'"' -f2)"
echo "Cargo.toml: $cargo_version"
[ "$cargo_version" = "$expected" ] || {
	echo "❌ Cargo.toml mismatch"
	errors=$((errors + 1))
}

# Root package.json
root_version="$(jq -r '.version' package.json)"
echo "package.json (root): $root_version"
[ "$root_version" = "$expected" ] || {
	echo "❌ package.json (root) mismatch"
	errors=$((errors + 1))
}

# WASM package.json
wasm_version="$(jq -r '.version' crates/kreuzberg-wasm/package.json)"
echo "crates/kreuzberg-wasm/package.json: $wasm_version"
[ "$wasm_version" = "$expected" ] || {
	echo "❌ WASM package.json mismatch"
	errors=$((errors + 1))
}

# Node package.json
node_version="$(jq -r '.version' crates/kreuzberg-node/package.json)"
echo "crates/kreuzberg-node/package.json: $node_version"
[ "$node_version" = "$expected" ] || {
	echo "❌ Node package.json mismatch"
	errors=$((errors + 1))
}

# Python pyproject.toml
python_version="$(grep '^version' packages/python/pyproject.toml | head -1 | cut -d'"' -f2)"
echo "packages/python/pyproject.toml: $python_version"
[ "$python_version" = "$expected" ] || {
	echo "❌ Python pyproject.toml mismatch"
	errors=$((errors + 1))
}

# Ruby version.rb
ruby_version="$(grep "VERSION =" packages/ruby/lib/kreuzberg/version.rb | cut -d"'" -f2)"
echo "packages/ruby/lib/kreuzberg/version.rb: $ruby_version"
[ "$ruby_version" = "$expected" ] || {
	echo "❌ Ruby version.rb mismatch"
	errors=$((errors + 1))
}

# Java pom.xml (first <version> tag is the project version)
java_version="$(grep '<version>' packages/java/pom.xml | head -1 | sed 's/.*<version>\\(.*\\)<\\/version>.*/\\1/')"
echo "packages/java/pom.xml: $java_version"
[ "$java_version" = "$expected" ] || {
	echo "❌ Java pom.xml mismatch"
	errors=$((errors + 1))
}

# C# Kreuzberg.csproj
csharp_version="$(grep '<Version>' packages/csharp/Kreuzberg/Kreuzberg.csproj | head -1 | sed 's/.*<Version>\\(.*\\)<\\/Version>.*/\\1/')"
echo "packages/csharp/Kreuzberg/Kreuzberg.csproj: $csharp_version"
[ "$csharp_version" = "$expected" ] || {
	echo "❌ C# csproj mismatch"
	errors=$((errors + 1))
}

# Go doc.go version comment
go_version="$(grep 'This binding targets Kreuzberg' packages/go/kreuzberg/doc.go | sed 's/.*Kreuzberg \\([^ ]*\\).*/\\1/')"
echo "packages/go/kreuzberg/doc.go: $go_version"
[ "$go_version" = "$expected" ] || {
	echo "❌ Go doc.go mismatch"
	errors=$((errors + 1))
}

echo "----------------------------------------"
if [ "$errors" -gt 0 ]; then
	echo "❌ $errors version mismatches found"
	exit 1
fi

echo "✅ All 9 version sources consistent: $expected"
