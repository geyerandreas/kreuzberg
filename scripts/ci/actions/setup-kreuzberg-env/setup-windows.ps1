param(
  [Parameter(Mandatory = $true)]
  [string]$Mode,
  [Parameter(Mandatory = $true)]
  [string]$FfiLibDir
)

$ErrorActionPreference = "Stop"

$REPO_ROOT = $env:GITHUB_WORKSPACE
$env:REPO_ROOT = $REPO_ROOT
[System.Environment]::SetEnvironmentVariable("REPO_ROOT", $REPO_ROOT, "Process")

$FFI_PATH = Join-Path $REPO_ROOT $FfiLibDir

# Initialize PATH variable
$env:PATH = "$FFI_PATH;$env:PATH"

# For Windows GNU target
if (Test-Path "target/x86_64-pc-windows-gnu/release") {
  $env:PATH = "$(Join-Path $REPO_ROOT 'target/x86_64-pc-windows-gnu/release');$env:PATH"
  Write-Host "✓ Windows GNU target paths configured"
}

# Add PDFium paths if available
if ($env:KREUZBERG_PDFIUM_PREBUILT) {
  $env:PATH = "$env:KREUZBERG_PDFIUM_PREBUILT/bin;$env:PATH"
  Write-Host "✓ PDFium paths configured"
}

# Add ONNX Runtime paths if available (only for full mode)
if ($Mode -eq "full" -and $env:ORT_LIB_LOCATION) {
  $env:PATH = "$env:ORT_LIB_LOCATION;$env:PATH"
  Write-Host "✓ ONNX Runtime paths configured"
}

# Export to GITHUB_ENV for persistence
Add-Content -Path $env:GITHUB_ENV -Value "PATH=$env:PATH"
Add-Content -Path $env:GITHUB_ENV -Value "REPO_ROOT=$REPO_ROOT"

Write-Host "✓ Windows library paths configured"
