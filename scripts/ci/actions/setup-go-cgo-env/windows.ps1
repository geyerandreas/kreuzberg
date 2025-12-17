$ErrorActionPreference = "Stop"

$ffiLibDir = $args[0]
if ([string]::IsNullOrWhiteSpace($ffiLibDir)) { $ffiLibDir = "target/release" }

$repoRoot = $env:GITHUB_WORKSPACE
$ffiPath = Join-Path $repoRoot $ffiLibDir

$gnuTargetPath = Join-Path $repoRoot "target/x86_64-pc-windows-gnu/release"
if (Test-Path $gnuTargetPath) {
  $ffiPath = $gnuTargetPath
  Write-Host "Using Windows GNU target path: $ffiPath"
} elseif (-not (Test-Path $ffiPath)) {
  throw "Error: FFI library directory not found: $ffiPath"
}

$env:PATH = "${ffiPath};$($env:PATH)"
$pkgConfigPath = "$(Join-Path $repoRoot 'crates/kreuzberg-ffi');$env:PKG_CONFIG_PATH"
$cgoEnabled = "1"
$cgoCflags = "-I$(Join-Path $repoRoot 'crates/kreuzberg-ffi/include')"
$cgoLdflags = "-L$ffiPath -lkreuzberg_ffi -static-libgcc -static-libstdc++ -lws2_32 -luserenv -lbcrypt"

Add-Content -Path $env:GITHUB_ENV -Value "PATH=$env:PATH"
Add-Content -Path $env:GITHUB_ENV -Value "PKG_CONFIG_PATH=$pkgConfigPath"
Add-Content -Path $env:GITHUB_ENV -Value "CGO_ENABLED=$cgoEnabled"
Add-Content -Path $env:GITHUB_ENV -Value "CGO_CFLAGS=$cgoCflags"
Add-Content -Path $env:GITHUB_ENV -Value "CGO_LDFLAGS=$cgoLdflags"

Write-Host "✓ Go cgo environment configured (Windows)"
Write-Host "  FFI Library Path: $ffiPath"
Write-Host "  PKG_CONFIG_PATH: $pkgConfigPath"
Write-Host "  CGO_LDFLAGS: $cgoLdflags"
