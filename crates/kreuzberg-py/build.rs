use std::env;
use std::path::PathBuf;

fn main() {
    let target = env::var("TARGET").unwrap();
    let profile = env::var("PROFILE").unwrap_or_else(|_| "release".to_string());
    let profile_dir = match profile.as_str() {
        "dev" | "test" => "debug",
        other => other,
    };

    // Try to locate kreuzberg-ffi library built alongside this crate
    let cargo_manifest_dir = env::var("CARGO_MANIFEST_DIR").unwrap();
    let manifest_path = PathBuf::from(&cargo_manifest_dir);

    // Prefer host target layout, but include target-triple layout for cross builds.
    // IMPORTANT: Only search lib directories, NOT deps directories.
    // The deps/ directories may contain dylibs with hardcoded install_name paths,
    // which causes ImportError on macOS when users install the wheel.
    if let Some(workspace_root) = manifest_path.parent().and_then(|p| p.parent()) {
        let host_lib_dir = workspace_root.join("target").join(profile_dir);
        let target_lib_dir = workspace_root.join("target").join(&target).join(profile_dir);

        // Try to find the static library and link it directly on Unix-like systems
        // to avoid the linker preferring dylib over static lib.
        if !target.contains("windows") {
            let static_lib_name = if target.contains("windows") {
                "kreuzberg_ffi.lib"
            } else {
                "libkreuzberg_ffi.a"
            };

            // Check both host and target lib directories for the static library
            for lib_dir in [&host_lib_dir, &target_lib_dir] {
                let static_lib = lib_dir.join(static_lib_name);
                if static_lib.exists() {
                    // Found static library, link it directly by passing the full path
                    println!("cargo:rustc-link-arg={}", static_lib.display());
                    // Don't add the library search path or -l flag
                    // Jump to rpath configuration
                    if target.contains("darwin") {
                        println!("cargo:rustc-link-arg=-Wl,-rpath,@loader_path");
                    } else if target.contains("linux") {
                        println!("cargo:rustc-link-arg=-Wl,-rpath,$ORIGIN");
                    }
                    println!("cargo:rerun-if-changed=build.rs");
                    return;
                }
            }
        }

        // Fallback: Add search paths and link only if a static library exists.
        let static_lib_name = if target.contains("windows") {
            "kreuzberg_ffi.lib"
        } else {
            "libkreuzberg_ffi.a"
        };
        let mut found_static = false;
        for dir in [host_lib_dir, target_lib_dir] {
            if dir.exists() {
                println!("cargo:rustc-link-search=native={}", dir.display());
                if dir.join(static_lib_name).exists() {
                    found_static = true;
                }
            }
        }
        if found_static {
            println!("cargo:rustc-link-lib=static=kreuzberg_ffi");
            if target.contains("darwin") {
                println!("cargo:rustc-link-arg=-Wl,-rpath,@loader_path");
            } else if target.contains("linux") {
                println!("cargo:rustc-link-arg=-Wl,-rpath,$ORIGIN");
            }
            println!("cargo:rerun-if-changed=build.rs");
            return;
        }
    }

    println!("cargo:rerun-if-changed=build.rs");
}
