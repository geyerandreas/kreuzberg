$ErrorActionPreference = "Stop"

$workspace = ridk exec bash -lc "cygpath -au '$env:GITHUB_WORKSPACE'"
$rubydir = "$workspace/packages/ruby"
$rubyPlatform = ruby -e "puts Gem::Platform.local.to_s"

ridk exec bash -lc "cd $rubydir && set -euo pipefail; mkdir -p pkg; stage_dir=\"tmp/$rubyPlatform/stage\"; if [ ! -f \"\$stage_dir/kreuzberg.gemspec\" ]; then echo \"Stage directory \$stage_dir missing\" >&2; exit 1; fi; (cd \"\$stage_dir\" && gem build kreuzberg.gemspec); mv \"\$stage_dir\"/kreuzberg-*.gem pkg/"

$gemFile = Get-ChildItem -Path "packages\\ruby\\pkg" -Filter "kreuzberg-*.gem" | Select-Object -First 1
if ($null -eq $gemFile) {
  throw "No gem file found in packages/ruby/pkg"
}
Add-Content -Path $env:GITHUB_OUTPUT -Value "gem-path=$env:GITHUB_WORKSPACE\\packages\\ruby\\pkg\\$($gemFile.Name)"
