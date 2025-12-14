#!/usr/bin/env pwsh

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

rustup default stable-x86_64-pc-windows-gnu

Write-Host "=== Rust toolchain configuration ==="
rustup show
rustc --version --verbose
