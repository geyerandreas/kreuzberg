$target = $args[0]
if ([string]::IsNullOrWhiteSpace($target)) { throw "Usage: package-windows.ps1 <target>" }

$stage = "cli-$target"
Remove-Item -Recurse -Force $stage -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $stage | Out-Null
Copy-Item "target/$target/release/kreuzberg.exe" $stage
Copy-Item LICENSE $stage
Copy-Item README.md $stage
Compress-Archive -Path "$stage/*" -DestinationPath "$stage.zip" -Force
Remove-Item -Recurse -Force $stage
Add-Content -Path $env:GITHUB_OUTPUT -Value "archive-path=$env:GITHUB_WORKSPACE/$stage.zip"
