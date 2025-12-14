#!/usr/bin/env bash
set -euo pipefail

label="${1:?label required}"
enable_cache="${2:?enable-cache required (true/false)}"

if [ "$enable_cache" = "true" ]; then
	cache_dir="${GITHUB_WORKSPACE}/.tesseract-cache/${label}"

	echo "TESSERACT_RS_CACHE_DIR=${cache_dir}" >>"$GITHUB_ENV"
	echo "XDG_CACHE_HOME=${GITHUB_WORKSPACE}/.xdg-cache/${label}" >>"$GITHUB_ENV"

	echo "cache-dir=${cache_dir}" >>"$GITHUB_OUTPUT"
	echo "cache-enabled=true" >>"$GITHUB_OUTPUT"

	docker_opts="--env TESSERACT_RS_CACHE_DIR=/io/.tesseract-cache/${label}"
	docker_opts="${docker_opts} --env XDG_CACHE_HOME=/io/.xdg-cache/${label}"
	docker_opts="${docker_opts} --env OPENSSL_LIB_DIR=/usr/lib/x86_64-linux-gnu"
	docker_opts="${docker_opts} --env OPENSSL_INCLUDE_DIR=/usr/include"
	echo "docker-options=${docker_opts}" >>"$GITHUB_OUTPUT"
else
	{
		echo "TESSERACT_RS_CACHE_DIR="
	} >>"$GITHUB_ENV"
	{
		echo "cache-dir="
		echo "cache-enabled=false"
		echo "docker-options="
	} >>"$GITHUB_OUTPUT"
fi
