$ErrorActionPreference = "Stop"

$taskVersion = $args[0]
if ([string]::IsNullOrWhiteSpace($taskVersion)) {
  throw "Usage: windows.ps1 <taskVersion>"
}

$taskBinDir = "$env:USERPROFILE\AppData\Local\task"
New-Item -ItemType Directory -Force -Path $taskBinDir | Out-Null

$taskExe = "$taskBinDir\task.exe"

if (-not (Test-Path $taskExe)) {
  $releases = "https://api.github.com/repos/go-task/task/releases/tags/v$taskVersion"
  $release = Invoke-RestMethod -Uri $releases
  $asset = $release.assets | Where-Object { $_.name -match "windows_amd64\.zip" } | Select-Object -First 1

  if ($asset) {
    $downloadUrl = $asset.browser_download_url
    $zipPath = "$taskBinDir\task.zip"
    Invoke-WebRequest -Uri $downloadUrl -OutFile $zipPath
    Expand-Archive -Path $zipPath -DestinationPath $taskBinDir -Force
    Remove-Item $zipPath
  } else {
    throw "Could not find Windows amd64 release for Task v$taskVersion"
  }
}

"$taskBinDir" | Out-File -FilePath $env:GITHUB_PATH -Encoding utf8 -Append
