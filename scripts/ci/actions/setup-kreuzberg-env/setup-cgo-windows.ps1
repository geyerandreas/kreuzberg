param(
  [Parameter(Mandatory = $true)]
  [string]$FfiLibDir
)

$ErrorActionPreference = "Stop"

$REPO_ROOT = $env:GITHUB_WORKSPACE
$FFI_PATH = Join-Path $REPO_ROOT $FfiLibDir

# Try Windows GNU target first
$GNU_TARGET_PATH = Join-Path $REPO_ROOT "target/x86_64-pc-windows-gnu/release"
if (Test-Path $GNU_TARGET_PATH) {
  $FFI_PATH = $GNU_TARGET_PATH
}

# cgo settings for Windows GNU
$CGO_ENABLED = "1"
$CGO_CFLAGS = "-I$(Join-Path $REPO_ROOT 'crates/kreuzberg-ffi/include')"
$CGO_LDFLAGS = "-L$FFI_PATH -lkreuzberg_ffi -static-libgcc -static-libstdc++"

Add-Content -Path $env:GITHUB_ENV -Value "CGO_ENABLED=$CGO_ENABLED"
Add-Content -Path $env:GITHUB_ENV -Value "CGO_CFLAGS=$CGO_CFLAGS"
Add-Content -Path $env:GITHUB_ENV -Value "CGO_LDFLAGS=$CGO_LDFLAGS"

Write-Host "✓ Go cgo environment configured (Windows)"
