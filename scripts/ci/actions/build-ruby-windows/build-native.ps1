$ErrorActionPreference = "Stop"

$workspace = ridk exec bash -lc "cygpath -au '$env:GITHUB_WORKSPACE'"
$rubydir = "$workspace/packages/ruby"
$rubyPlatform = ruby -e "puts Gem::Platform.local.to_s"

ridk exec bash -lc "cd $rubydir && export RUSTUP_TOOLCHAIN=stable-gnu CC=x86_64-w64-mingw32-gcc CXX=x86_64-w64-mingw32-g++ && bundle exec rake native:kreuzberg:$rubyPlatform"
