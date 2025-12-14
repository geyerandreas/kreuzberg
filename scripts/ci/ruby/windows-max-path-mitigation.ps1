#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Create short path directories
New-Item -ItemType Directory -Path "C:\t" -Force | Out-Null
New-Item -ItemType Directory -Path "C:\b" -Force | Out-Null
New-Item -ItemType Directory -Path "C:\g" -Force | Out-Null

# Configure bundler to use shorter path
Push-Location packages/ruby
bundle config set path "C:\b"
bundle config set no_prune true
Pop-Location

# Export env vars for subsequent steps
Add-Content -Path $env:GITHUB_ENV -Value "CARGO_TARGET_DIR=C:\t"
Add-Content -Path $env:GITHUB_ENV -Value "BUNDLE_PATH=C:\b"
Add-Content -Path $env:GITHUB_ENV -Value "GEM_HOME=C:\g"

Write-Host "Windows MAX_PATH mitigation paths configured:"
Write-Host "  CARGO_TARGET_DIR: C:\t"
Write-Host "  BUNDLE_PATH: C:\b"
Write-Host "  GEM_HOME: C:\g"
