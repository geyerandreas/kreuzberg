$ErrorActionPreference = "Stop"
$vcpkgRoot = "C:\vcpkg\installed\x64-windows-static-md"

Write-Host "Configuring OpenSSL environment variables..." -ForegroundColor Green

# Final verification before setting environment
if (-not (Test-Path $vcpkgRoot)) {
  Write-Error "vcpkg OpenSSL installation not found at: $vcpkgRoot"
  exit 1
}

# Set environment variables
$envVars = @{
  "VCPKG_ROOT"          = "C:\vcpkg"
  "OPENSSL_DIR"         = $vcpkgRoot
  "OPENSSL_ROOT_DIR"    = $vcpkgRoot
  "OPENSSL_LIB_DIR"     = "$vcpkgRoot\lib"
  "OPENSSL_INCLUDE_DIR" = "$vcpkgRoot\include"
  "OPENSSL_STATIC"      = "1"
}

foreach ($key in $envVars.Keys) {
  $value = $envVars[$key]
  Write-Host "  Setting $key=$value"
  Add-Content -Path $env:GITHUB_ENV -Value "$key=$value"
}

Write-Host "OpenSSL environment configuration completed" -ForegroundColor Green
Write-Host "Summary:" -ForegroundColor Green
Write-Host "  OPENSSL_DIR=$vcpkgRoot"
Write-Host "  OPENSSL_LIB_DIR=$vcpkgRoot\lib"
Write-Host "  OPENSSL_INCLUDE_DIR=$vcpkgRoot\include"
Write-Host "  OPENSSL_STATIC=1"
