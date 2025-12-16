# PDFium Linking Strategies

Kreuzberg supports multiple PDFium linking strategies for different deployment needs. Choose the strategy that best fits your use case.

**Note:** Language bindings (Python, TypeScript, Ruby, Java, Go) automatically bundle PDFium. No configuration required.

## Quick Decision Matrix

Choose your PDFium linking strategy based on your use case:

| Strategy | Feature | Download | Link Type | Binary Size | Runtime Deps | Default For | Use Case | Complexity |
|----------|---------|----------|-----------|-------------|--------------|-------------|----------|------------|
| **Bundled** | `bundled-pdfium` | Yes | Dynamic | ~150 MB | None | Rust crate (default) | Development, production | Simple |
| **Static** | `static-pdfium` | Yes | Static | ~200 MB | None | Docker, musl, CLI | Single binary distribution | Medium |
| **System** | `system-pdfium` | No | Dynamic | ~40 MB | System libpdfium | Package managers | Linux distros, system integration | Complex |

**Breaking Change in v4.0.0-rc.10:**
- Feature names changed: `pdf-*` → `*-pdfium`
  - `pdf-static` → `static-pdfium`
  - `pdf-bundled` → `bundled-pdfium`
  - `pdf-system` → `system-pdfium`
- `full-bundled` removed (use `full` + `bundled-pdfium`)
- Default changed to `bundled-pdfium` (was download + dynamic)

**Quick recommendations:**

- **Local development?** Use default `bundled-pdfium` (works out of the box)
- **Ship single executable?** Use `static-pdfium` (larger binary, no runtime deps)
- **System integration?** Use `system-pdfium` (requires system installation, smallest binary)

## Strategy Details

### Bundled (Default)

Bundled linking downloads PDFium at build time and embeds it in your executable. The library is extracted to a temporary directory at runtime on first use.

#### When to Use

- Local development and testing
- Production deployments with consistent binary
- Self-contained applications that users run directly
- Portable executables (no installation needed)

#### Configuration

=== "Cargo.toml"

    ```toml
    [dependencies]
    kreuzberg = { version = "4.0", features = ["bundled-pdfium"] }
    ```

=== "Command Line"

    ```bash
    cargo build --features bundled-pdfium
    cargo run --features bundled-pdfium
    ```

#### How It Works

1. **Build time**: PDFium is downloaded from `bblanchon/pdfium-binaries` (version 7578)
2. **First run**: Library is extracted to system temporary directory (e.g., `/tmp/kreuzberg-pdfium/`)
3. **Runtime**: Extracted library is dynamically loaded from temp directory
4. **Subsequent runs**: Library reused from temp directory if it still exists

#### Benefits

- Self-contained executable (portable)
- Single binary distribution
- Dynamic linking performance (no startup overhead)
- Library can be updated by clearing temp directory
- Automatic extraction (no user setup needed)
- Zero runtime dependencies

#### Tradeoffs

- Binary slightly larger than dynamic (~150 MB vs ~40 MB)
- First run slower (extraction overhead)
- Requires writable temporary directory
- If temp directory is cleared, re-extraction on next run

#### Platform Notes

=== "Linux"

    ```bash
    # Bundled library extracted to /tmp/kreuzberg-pdfium/
    cargo build --release --features bundled-pdfium

    # Binary size: 150-180 MB
    ./target/release/your-app

    # Check extracted library
    ls -la /tmp/kreuzberg-pdfium/libpdfium.so
    ```

=== "macOS"

    ```bash
    # Bundled library extracted to /tmp/kreuzberg-pdfium/
    cargo build --release --features bundled-pdfium

    # Binary size: 150-180 MB
    ./target/release/your-app

    # Check extracted library
    ls -la /tmp/kreuzberg-pdfium/libpdfium.dylib
    ```

=== "Windows"

    ```bash
    # Bundled library extracted to TEMP\kreuzberg-pdfium\
    cargo build --release --features bundled-pdfium

    # Binary size: 150-180 MB
    your-app.exe

    # Check extracted library
    dir %TEMP%\kreuzberg-pdfium\pdfium.dll
    ```

#### Environment Variables

| Variable | Purpose | Example |
|----------|---------|---------|
| `PDFIUM_VERSION` | Override PDFium version | `7578` |
| `TMPDIR` | Override temp directory for extraction | `/var/tmp` |

#### Testing

```bash
# Build with bundled linking
cargo build --release --features bundled-pdfium

# Verify binary contains bundled pdfium
strings target/release/libkreuzberg.so | grep -i "pdfium" | head -5

# First run (extraction happens)
cargo run --release --features bundled-pdfium

# Verify extraction
ls -la /tmp/kreuzberg-pdfium/

# Second run (uses cached library)
cargo run --release --features bundled-pdfium

# Test with custom temp directory
TMPDIR=/var/tmp cargo test --release --features bundled-pdfium

# Clean up
rm -rf /tmp/kreuzberg-pdfium/
```

---

### Static

Static linking embeds PDFium directly in your binary at compile time. No runtime library dependency.

#### When to Use

- Single-binary distribution (entire executable fits in one file)
- Docker/musl deployments where you can't rely on dynamic libraries
- Guaranteed version compatibility (no runtime mismatches)
- Air-gapped deployments
- CLI applications

#### Configuration

=== "Cargo.toml"

    ```toml
    [dependencies]
    kreuzberg = { version = "4.0", features = ["static-pdfium"] }
    ```

=== "Command Line"

    ```bash
    cargo build --release --features static-pdfium
    cargo run --features static-pdfium
    ```

#### How It Works

1. **Build time**: PDFium is downloaded from `paulocoutinhox/pdfium-lib` (version 7442b)
2. **Linking**: Static library `libpdfium.a` is embedded in your binary during linking
3. **Runtime**: No external library needed; everything is self-contained

#### Benefits

- Zero runtime dependencies
- Single executable file (everything included)
- No library path configuration needed
- Guaranteed version consistency
- Easy distribution and deployment

#### Tradeoffs

- **Significantly larger binary** (~200+ MB)
- Slower build times (larger linking)
- Slower program startup (larger binary to load)
- All applications using the library include their own copy
- Harder to update PDFium (requires recompilation)

#### Platform Notes

=== "Linux"

    ```bash
    # Static linking includes pdfium.a in binary
    # Binary size: 200-250 MB
    cargo build --release --features static-pdfium

    # No LD_LIBRARY_PATH needed
    ./target/release/your-app
    ```

=== "macOS"

    ```bash
    # Static linking includes pdfium.a in binary
    # Binary size: 200-250 MB
    cargo build --release --features static-pdfium

    # No DYLD_LIBRARY_PATH needed
    ./target/release/your-app
    ```

=== "Windows"

    ```bash
    # Static linking includes pdfium.lib in binary
    # Requires MSVC runtime
    cargo build --release --features static-pdfium

    your-app.exe
    ```

#### Environment Variables

| Variable | Purpose |
|----------|---------|
| `PDFIUM_STATIC_VERSION` | Override PDFium static version | `7442b` |

#### Testing

```bash
# Build with static linking
cargo build --release --features static-pdfium

# Verify static linking (no external pdfium dependency)
ldd target/release/libkreuzberg.so | grep pdfium  # Should NOT appear
otool -L target/release/libkreuzberg.dylib | grep pdfium  # Should NOT appear

# Binary size check
ls -lh target/release/libkreuzberg.so   # ~200+ MB
ls -lh target/release/libkreuzberg.dylib  # ~200+ MB

# Run without any library path setup
cargo test --release --features static-pdfium
```

---

### System

System PDFium linking uses a PDFium library installed on your system (or in a custom location). This requires no downloads and keeps binaries small.

#### When to Use

- Package manager distributions (system manages PDFium)
- Linux distribution packages
- System integration where PDFium is centrally managed
- Development on systems with PDFium pre-installed
- Environments where binary downloads are restricted

#### Configuration

=== "Cargo.toml"

    ```toml
    [dependencies]
    kreuzberg = { version = "4.0", features = ["system-pdfium"] }
    ```

=== "Command Line"

    ```bash
    cargo build --features system-pdfium
    cargo run --features system-pdfium
    ```

#### How It Works

1. **Build time**: Kreuzberg searches for system PDFium using `pkg-config`
2. **Detection**: Looks for `pdfium.pc` pkg-config file
3. **Linking**: Links against system `libpdfium.so`/`dylib` by version
4. **Fallback**: If pkg-config unavailable, uses environment variables
5. **Runtime**: System library must be in standard search paths

#### Benefits

- Zero downloads (uses existing system installation)
- Smallest binary size (~40 MB)
- Faster builds (no download or embed)
- Centralized PDFium management
- Ideal for package distributions
- System can manage security updates for PDFium

#### Tradeoffs

- **Requires system PDFium installation** (manual or via package manager)
- Version mismatch risk if system version different than expected
- Less control over PDFium version
- Requires admin/sudo for installation
- Not suitable for portable distributions

#### Platform Notes

=== "Linux"

    ```bash
    # Requires system PDFium with pkg-config
    # See "System Installation Guide" section below

    cargo build --features system-pdfium

    # Verify system linking
    ldd target/debug/libkreuzberg.so | grep pdfium
    # Output: libpdfium.so.* => /usr/local/lib/libpdfium.so.*
    ```

=== "macOS"

    ```bash
    # Requires system PDFium with pkg-config
    # See "System Installation Guide" section below

    cargo build --features system-pdfium

    # Verify system linking
    otool -L target/debug/libkreuzberg.dylib | grep pdfium
    # Output: /usr/local/lib/libpdfium.dylib
    ```

=== "Windows"

    ```bash
    # System PDFium not recommended on Windows
    # Use bundled or static linking instead
    # pkg-config support limited on Windows
    ```

#### Environment Variables

| Variable | Purpose | Example |
|----------|---------|---------|
| `KREUZBERG_PDFIUM_SYSTEM_PATH` | Override system pdfium library path | `/opt/pdfium/lib` |
| `KREUZBERG_PDFIUM_SYSTEM_INCLUDE` | Override system pdfium include path | `/opt/pdfium/include` |
| `PKG_CONFIG_PATH` | Add to pkg-config search path | `/usr/local/lib/pkgconfig` |

#### Testing

```bash
# Verify system pdfium is installed
pkg-config --modversion pdfium
pkg-config --cflags --libs pdfium

# Build with system pdfium
cargo build --features system-pdfium

# Verify linking
ldd target/debug/libkreuzberg.so | grep pdfium

# Test
cargo test --features system-pdfium

# Using custom paths
KREUZBERG_PDFIUM_SYSTEM_PATH=/opt/pdfium/lib \
KREUZBERG_PDFIUM_SYSTEM_INCLUDE=/opt/pdfium/include \
cargo build --features system-pdfium
```

---

## System Installation Guide

This section covers installing system PDFium for the `system-pdfium` feature.

### Linux (Ubuntu/Debian)

#### Automated Installation

```bash
# Download and run system installation script
sudo bash scripts/install-system-pdfium-linux.sh

# Verify installation
pkg-config --modversion pdfium
ldconfig -p | grep pdfium
```

**Script environment variables:**

```bash
# Custom installation prefix (default: /usr/local)
PREFIX=/opt/pdfium sudo bash scripts/install-system-pdfium-linux.sh

# Custom PDFium version (default: 7529)
PDFIUM_VERSION=7525 sudo bash scripts/install-system-pdfium-linux.sh
```

#### Manual Installation

```bash
#!/bin/bash
set -e

PDFIUM_VERSION=7529
PREFIX=/usr/local

# Download pdfium
cd /tmp
wget "https://github.com/bblanchon/pdfium-binaries/releases/download/chromium/${PDFIUM_VERSION}/pdfium-linux-x64.tgz"
tar xzf pdfium-linux-x64.tgz

# Install library
sudo install -m 0755 lib/libpdfium.so "${PREFIX}/lib/"
sudo ldconfig

# Install headers
sudo mkdir -p "${PREFIX}/include/pdfium"
sudo cp -r include/* "${PREFIX}/include/pdfium/"

# Create pkg-config file
sudo tee "${PREFIX}/lib/pkgconfig/pdfium.pc" > /dev/null <<EOF
prefix=${PREFIX}
exec_prefix=\${prefix}
libdir=\${exec_prefix}/lib
includedir=\${prefix}/include/pdfium

Name: PDFium
Description: PDF rendering library
Version: ${PDFIUM_VERSION}
Libs: -L\${libdir} -lpdfium
Cflags: -I\${includedir}
EOF

# Refresh library cache
sudo ldconfig

# Verify
pkg-config --modversion pdfium
```

#### Verification

```bash
# Check library is installed
ls -la /usr/local/lib/libpdfium.so

# Check headers
ls -la /usr/local/include/pdfium/

# Check pkg-config
pkg-config --modversion pdfium
pkg-config --cflags pdfium
pkg-config --libs pdfium

# Verify library can be loaded
ldconfig -p | grep pdfium
# Output should include: libpdfium.so => /usr/local/lib/libpdfium.so
```

### macOS

#### Automated Installation

```bash
# Download and run system installation script
sudo bash scripts/install-system-pdfium-macos.sh

# Verify installation
pkg-config --modversion pdfium
```

#### Manual Installation

```bash
#!/bin/bash
set -e

PDFIUM_VERSION=7529
PREFIX=/usr/local
ARCH=$(uname -m)  # arm64 or x86_64

# Download pdfium (adjust for your architecture)
cd /tmp
curl -L "https://github.com/bblanchon/pdfium-binaries/releases/download/chromium/${PDFIUM_VERSION}/pdfium-mac-${ARCH}.tgz" \
  -o pdfium.tgz
tar xzf pdfium.tgz

# Install library
sudo install -m 0755 lib/libpdfium.dylib "${PREFIX}/lib/"

# Install headers
sudo mkdir -p "${PREFIX}/include/pdfium"
sudo cp -r include/* "${PREFIX}/include/pdfium/"

# Create pkg-config file
sudo mkdir -p "${PREFIX}/lib/pkgconfig"
sudo tee "${PREFIX}/lib/pkgconfig/pdfium.pc" > /dev/null <<EOF
prefix=${PREFIX}
exec_prefix=\${prefix}
libdir=\${exec_prefix}/lib
includedir=\${prefix}/include/pdfium

Name: PDFium
Description: PDF rendering library
Version: ${PDFIUM_VERSION}
Libs: -L\${libdir} -lpdfium
Cflags: -I\${includedir}
EOF

# Verify
pkg-config --modversion pdfium
```

#### Verification

```bash
# Check library is installed
ls -la /usr/local/lib/libpdfium.dylib

# Check headers
ls -la /usr/local/include/pdfium/

# Check pkg-config
pkg-config --modversion pdfium
pkg-config --cflags pdfium
pkg-config --libs pdfium

# Test linking
otool -L /usr/local/lib/libpdfium.dylib
```

### Installation Troubleshooting

#### "pkg-config: command not found"

```bash
# Install pkg-config

# Ubuntu/Debian
sudo apt-get install pkg-config

# macOS
brew install pkg-config
```

#### "PDFium not found" (after installation)

**Linux:**

```bash
# Update library cache
sudo ldconfig

# Verify cache
ldconfig -p | grep pdfium

# Add to PKG_CONFIG_PATH if using custom prefix
export PKG_CONFIG_PATH=/opt/pdfium/lib/pkgconfig:$PKG_CONFIG_PATH
pkg-config --exists pdfium && echo "Found" || echo "Not found"
```

**macOS:**

```bash
# Update library symlinks if needed
brew link --overwrite libpdfium || true

# Verify pkg-config file
cat /usr/local/lib/pkgconfig/pdfium.pc

# Check PKG_CONFIG_PATH
echo $PKG_CONFIG_PATH

# Add if needed
export PKG_CONFIG_PATH=/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH
```

#### "libpdfium.so: cannot open shared object file" (at runtime)

**Linux:**

```bash
# Ensure library cache is updated
sudo ldconfig

# Verify library location
ldconfig -p | grep pdfium

# Add to library search path if needed
export LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH
./your-app
```

**macOS:**

```bash
# Check library exists
ls -la /usr/local/lib/libpdfium.dylib

# Check permissions
chmod 755 /usr/local/lib/libpdfium.dylib

# Verify with otool
otool -L /usr/local/lib/libpdfium.dylib

# Test loading
python3 -c "import ctypes; ctypes.CDLL('/usr/local/lib/libpdfium.dylib')"
```

---

## Testing Configuration

Test that your PDFium configuration works correctly.

### Basic Build Test

```bash
# Test default (bundled)
cargo build --features bundled-pdfium
cargo test --features bundled-pdfium

# Test static
cargo build --release --features static-pdfium
cargo test --release --features static-pdfium

# Test system (after installation)
cargo build --features system-pdfium
cargo test --features system-pdfium
```

### PDF Extraction Test

Create a simple test with a sample PDF:

=== "Rust"

    ```rust
    #[test]
    fn test_pdf_extraction() {
        use kreuzberg::{Kreuzberg, Config};

        let config = Config::default().with_pdf();
        let kreuzberg = Kreuzberg::new(config);

        // Use a sample PDF or test fixture
        let result = kreuzberg.extract_text("sample.pdf");
        assert!(result.is_ok());
    }
    ```

=== "Command"

    ```bash
    # Run PDF-related tests
    cargo test --features bundled-pdfium pdf
    cargo test --features static-pdfium pdf
    cargo test --features system-pdfium pdf
    ```

### Linking Verification

=== "Linux"

    ```bash
    # Check bundled linking (default)
    cargo build --features bundled-pdfium
    ldd target/debug/libkreuzberg.so | grep pdfium

    # Check static linking
    cargo build --release --features static-pdfium
    ldd target/release/libkreuzberg.so | grep pdfium || echo "✓ Static"

    # Check system linking
    cargo build --features system-pdfium
    ldd target/debug/libkreuzberg.so | grep /usr/local/lib/libpdfium.so
    ```

=== "macOS"

    ```bash
    # Check bundled linking (default)
    cargo build --features bundled-pdfium
    otool -L target/debug/libkreuzberg.dylib | grep pdfium

    # Check static linking
    cargo build --release --features static-pdfium
    otool -L target/release/libkreuzberg.dylib | grep pdfium || echo "✓ Static"

    # Check system linking
    cargo build --features system-pdfium
    otool -L target/debug/libkreuzberg.dylib | grep /usr/local/lib/libpdfium.dylib
    ```

### Binary Size Comparison

```bash
# Compare binary sizes
echo "=== Binary Sizes ===" && \
cargo build --release --features bundled-pdfium 2>/dev/null && \
ls -lh target/release/libkreuzberg.so && \
cargo build --release --features static-pdfium 2>/dev/null && \
ls -lh target/release/libkreuzberg.so && \
cargo build --release --features system-pdfium 2>/dev/null && \
ls -lh target/release/libkreuzberg.so
```

---

## CI/CD Integration

Configure your CI/CD pipeline to test PDFium linking.

### GitHub Actions

#### Test All Strategies

```yaml
name: PDFium Linking Tests

on: [push, pull_request]

jobs:
  test-pdfium-strategies:
    name: Test PDFium Strategy - ${{ matrix.strategy }}
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest]
        strategy: [bundled, static, system]
        exclude:
          # System PDFium not available on all platforms
          - os: windows-latest
            strategy: system

    steps:
      - uses: actions/checkout@v4

      - uses: dtolnay/rust-toolchain@stable

      - name: Install system pdfium (Linux)
        if: matrix.os == 'ubuntu-latest' && matrix.strategy == 'system'
        run: |
          sudo bash scripts/install-system-pdfium-linux.sh
          pkg-config --modversion pdfium

      - name: Install system pdfium (macOS)
        if: matrix.os == 'macos-latest' && matrix.strategy == 'system'
        run: |
          sudo bash scripts/install-system-pdfium-macos.sh
          pkg-config --modversion pdfium

      - name: Build Bundled
        if: matrix.strategy == 'bundled'
        run: cargo build --release --features bundled-pdfium

      - name: Build Static
        if: matrix.strategy == 'static'
        run: cargo build --release --features static-pdfium

      - name: Build System
        if: matrix.strategy == 'system'
        run: cargo build --features system-pdfium

      - name: Run Tests (Bundled)
        if: matrix.strategy == 'bundled'
        run: cargo test --release --features bundled-pdfium

      - name: Run Tests (Static)
        if: matrix.strategy == 'static'
        run: cargo test --release --features static-pdfium

      - name: Run Tests (Bundled)
        if: matrix.strategy == 'bundled'
        run: cargo test --release --features bundled-pdfium

      - name: Run Tests (System)
        if: matrix.strategy == 'system'
        run: cargo test --features system-pdfium
```

### Docker

#### Multi-Stage Build (Bundled)

```dockerfile
# Stage 1: Build
FROM rust:latest as builder

WORKDIR /app
COPY . .

# Download and bundle pdfium at build time
RUN cargo build --release --features bundled-pdfium

# Stage 2: Runtime
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y \
    libstdc++6 \
    && rm -rf /var/lib/apt/lists/*

# Copy built application
COPY --from=builder /app/target/release/kreuzberg /usr/local/bin/

# Library is bundled in binary, no need to copy separately

ENTRYPOINT ["kreuzberg"]
```

#### Single-Stage Build (Static)

```dockerfile
FROM rust:latest as builder

WORKDIR /app
COPY . .

# Static linking - no runtime library needed
RUN cargo build --release --features static-pdfium

# Final image just needs runtime support
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y \
    libstdc++6 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/target/release/kreuzberg /usr/local/bin/

ENTRYPOINT ["kreuzberg"]
```

#### System Installation

```dockerfile
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y \
    libpdfium \
    libstdc++6 \
    && rm -rf /var/lib/apt/lists/*

COPY . /app
WORKDIR /app

# Build against system PDFium
RUN cargo build --release --features system-pdfium

# Minimal runtime image
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y \
    libstdc++6 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/target/release/kreuzberg /usr/local/bin/

ENTRYPOINT ["kreuzberg"]
```

---

## Troubleshooting

### Build Errors

#### "feature `bundled-pdfium` not found"

**Problem:** You're trying to use PDFium features but they're not enabled.

**Solution:**

```bash
# Ensure feature is specified
cargo build --features bundled-pdfium

# If in Cargo.toml, verify syntax
[dependencies]
kreuzberg = { version = "4.0", features = ["bundled-pdfium"] }
```

#### Multiple linking features enabled

**Problem:** You enabled multiple linking features at once.

**Solution:** Only one of `static-pdfium`, `bundled-pdfium`, `system-pdfium` can be enabled.

```bash
# Wrong (mutually exclusive)
cargo build --features static-pdfium,pdf-bundled

# Correct (pick one)
cargo build --features static-pdfium
cargo build --features bundled-pdfium
cargo build --features system-pdfium
```

#### "pkg-config not found" (system strategy)

**Problem:** System PDFium not installed or pkg-config not available.

**Solution:**

```bash
# Install pkg-config
sudo apt-get install pkg-config  # Ubuntu/Debian
brew install pkg-config  # macOS

# Install system PDFium
sudo bash scripts/install-system-pdfium-linux.sh

# Verify
pkg-config --modversion pdfium
```

#### "PDFium not found" (system strategy)

**Problem:** Build fails because system PDFium can't be located.

**Solution:**

```bash
# Use environment variables to specify location
export KREUZBERG_PDFIUM_SYSTEM_PATH=/path/to/pdfium/lib
export KREUZBERG_PDFIUM_SYSTEM_INCLUDE=/path/to/pdfium/include
cargo build --features system-pdfium

# Or update PKG_CONFIG_PATH
export PKG_CONFIG_PATH=/path/to/pdfium/lib/pkgconfig:$PKG_CONFIG_PATH
cargo build --features system-pdfium

# Verify detection
pkg-config --exists pdfium && echo "Found" || echo "Not found"
```

### Runtime Errors

#### "libpdfium.so: cannot open shared object file" (Linux)

**Problem:** Runtime can't find PDFium library.

**Solution:**

```bash
# Update library cache
sudo ldconfig

# Verify library is registered
ldconfig -p | grep pdfium

# Add to search path if custom installation
export LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH
./your-app
```

#### "dyld: Library not loaded" (macOS)

**Problem:** Runtime can't find PDFium dylib.

**Solution:**

```bash
# Check library exists
ls -la /usr/local/lib/libpdfium.dylib

# Check permissions
chmod 755 /usr/local/lib/libpdfium.dylib

# Add to search path if needed
export DYLD_LIBRARY_PATH=/usr/local/lib:$DYLD_LIBRARY_PATH
./your-app

# Verify with otool
otool -L /usr/local/lib/libpdfium.dylib
```

#### "libstdc++.so.6: version not found" (Linux)

**Problem:** System C++ library version mismatch.

**Solution:**

```bash
# Check available C++ library
ldconfig -p | grep libstdc++

# Use bundled or static linking instead
cargo build --release --features bundled-pdfium
cargo build --release --features static-pdfium
```

### Development Issues

#### Rebuilding with different strategy

**Problem:** You switched strategies but old build artifacts remain.

**Solution:**

```bash
# Clean build cache
cargo clean

# Rebuild with new strategy
cargo build --features static-pdfium
```

#### Bundled library extraction fails

**Problem:** Temp directory not writable or insufficient permissions.

**Solution:**

```bash
# Check temp directory
echo $TMPDIR  # macOS/Linux
echo %TEMP%   # Windows

# Use custom temp directory
export TMPDIR=/var/tmp
./your-app

# Ensure permissions
mkdir -p /tmp/kreuzberg-pdfium
chmod 777 /tmp/kreuzberg-pdfium
```

---

## Migration Guide

Switch between linking strategies safely.

### From Bundled to Static

```bash
# Step 1: Update Cargo.toml
# Change from:
kreuzberg = { version = "4.0", features = ["bundled-pdfium"] }
# To:
kreuzberg = { version = "4.0", features = ["static-pdfium"] }

# Step 2: Clean and rebuild
cargo clean
cargo build --release --features static-pdfium

# Step 3: Test
cargo test --release --features static-pdfium

# Step 4: Verify no extracted files
ls -la /tmp/kreuzberg-pdfium/  # Should not exist
```

### From Bundled to System

**Prerequisites:** System PDFium must be installed first.

```bash
# Step 1: Install system PDFium
sudo bash scripts/install-system-pdfium-linux.sh

# Step 2: Verify
pkg-config --modversion pdfium

# Step 3: Update Cargo.toml
kreuzberg = { version = "4.0", features = ["system-pdfium"] }

# Step 4: Clean and rebuild
cargo clean
cargo build --features system-pdfium

# Step 5: Test
cargo test --features system-pdfium

# Step 6: Verify system linking
ldd target/debug/libkreuzberg.so | grep /usr/local/lib/libpdfium.so
```

### From Static to Bundled

```bash
# Step 1: Update Cargo.toml
# Change from:
kreuzberg = { version = "4.0", features = ["static-pdfium"] }
# To:
kreuzberg = { version = "4.0", features = ["bundled-pdfium"] }

# Step 2: Clean and rebuild
cargo clean
cargo build --features bundled-pdfium

# Step 3: Test (first run extracts)
cargo test --features bundled-pdfium

# Step 4: Verify extraction
ls -la /tmp/kreuzberg-pdfium/libpdfium.so  # Should exist
```

### From System to Bundled

```bash
# Step 1: Update Cargo.toml
# Change from:
kreuzberg = { version = "4.0", features = ["system-pdfium"] }
# To:
kreuzberg = { version = "4.0", features = ["bundled-pdfium"] }

# Step 2: Clean build artifacts
cargo clean

# Step 3: Rebuild
cargo build --release --features bundled-pdfium

# Step 4: Test
cargo test --release --features bundled-pdfium

# Step 5: Verify bundled extraction
ls -la /tmp/kreuzberg-pdfium/
```

---

## Best Practices

### Choose Strategy by Use Case

| Use Case | Recommended | Rationale |
|----------|-------------|-----------|
| Local development | Dynamic | Fastest builds, easy to debug |
| Container image | Dynamic | Library in image, no setup needed |
| Standalone binary | Static | Single file, no dependencies |
| CI/CD pipeline | Dynamic | Consistent, reproducible |
| Package distribution | System | OS manages dependencies |
| Embedded systems | Static | No external dependencies |
| Desktop application | Bundled | Single executable, portable |
| Cloud functions | Static | Cold start optimized |
| Kubernetes pods | Dynamic | Image-based deployment |

### Environment Setup

Always document environment variables in your project:

```bash
# .env.example for development
LD_LIBRARY_PATH=/path/to/pdfium/lib
DYLD_LIBRARY_PATH=/path/to/pdfium/lib
TMPDIR=/var/tmp
PKG_CONFIG_PATH=/usr/local/lib/pkgconfig
```

### CI/CD Recommendations

Test all strategies in CI:

```bash
# Test matrix
- Strategy: dynamic, os: [ubuntu, macos, windows]
- Strategy: static, os: [ubuntu, macos, windows]
- Strategy: bundled, os: [ubuntu, macos, windows]
- Strategy: system, os: [ubuntu, macos]  # Linux + macOS only
```

### Documentation for Users

Document your chosen strategy in project README:

```markdown
## Dependencies

PDFium is downloaded and linked dynamically at build time.

To use a different strategy:

**Static linking (single binary):**
```bash
cargo build --release --features static-pdfium
```

**System PDFium (requires installation):**
```bash
sudo bash scripts/install-system-pdfium-linux.sh
cargo build --features system-pdfium
```

See [PDFium Configuration Guide](docs/guides/pdfium-linking.md) for details.
```

---

## Additional Resources

- [Kreuzberg PDF Extraction Guide](extraction.md)
- [Kreuzberg Docker Deployment](docker.md)
- [PDFium Official Documentation](https://pdfium.googlesource.com/pdfium)
- [bblanchon/pdfium-binaries Releases](https://github.com/bblanchon/pdfium-binaries/releases)
