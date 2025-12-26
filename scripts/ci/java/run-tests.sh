#!/usr/bin/env bash
#
# Run Java tests with Maven
# Used by: ci-java.yaml - Run Java tests step
#
# Java FFM API requires Rust FFI libraries at runtime, so this script
# configures library paths before executing Maven tests.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd)}"

source "$REPO_ROOT/scripts/lib/common.sh"
source "$REPO_ROOT/scripts/lib/library-paths.sh"

validate_repo_root "$REPO_ROOT" || exit 1
setup_rust_ffi_paths "$REPO_ROOT"

echo "=== Running Java tests ==="
cd "$REPO_ROOT/packages/java"

# Enable comprehensive test debugging
# -X: debug mode
# -e: errors with full stack traces
# -DtrimStackTrace=false: preserve full stack traces
# -Dsurefire.printSummary=true: print test summary
# -Dsurefire.useFile=false: output to console instead of file
# Additional Maven opts for JVM diagnostics
export MAVEN_OPTS="${MAVEN_OPTS:-} \
  -XX:+UnlockDiagnosticVMOptions \
  -XX:+LogVMOutput \
  -XX:LogFile=test-jvm.log \
  -XX:+PrintGCDetails \
  -XX:+PrintCommandLineFlags \
  -Xlog:os=info:file=test-jvm-os.log"

# Log test environment
echo "=== Test Environment ==="
echo "JAVA_HOME: ${JAVA_HOME:-not set}"
echo "DYLD_LIBRARY_PATH: ${DYLD_LIBRARY_PATH:-not set}"
echo "LD_LIBRARY_PATH: ${LD_LIBRARY_PATH:-not set}"
echo "KREUZBERG_FFI_DIR: ${KREUZBERG_FFI_DIR:-not set}"
echo ""

echo "Maven test invocation:"
mvn -X -e -B \
	-DtrimStackTrace=false \
	-Dsurefire.useFile=false \
	-Dsurefire.printSummary=true \
	-Dtest.verbose=true \
	test ||
	{
		echo ""
		echo "=== Test Execution Failed - Collecting Diagnostics ==="

		if [ -f test-jvm.log ]; then
			echo "=== JVM Log (last 150 lines) ==="
			tail -150 test-jvm.log || true
			echo ""
		fi

		if [ -f test-jvm-os.log ]; then
			echo "=== OS Log (last 50 lines) ==="
			tail -50 test-jvm-os.log || true
			echo ""
		fi

		# Collect heap dump info if it exists
		if [ -d target/jvm-crash ]; then
			echo "=== JVM Crash Artifacts Found ==="
			ls -lh target/jvm-crash/ || true
			echo ""

			if [ -f target/jvm-crash/heapdump.hprof ]; then
				echo "=== Heap Dump Info ==="
				file target/jvm-crash/heapdump.hprof || true
				ls -lh target/jvm-crash/heapdump.hprof || true
			fi
		fi

		exit 1
	}

echo ""
echo "Java tests complete"
