import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from src.logger import get_logger

logger = get_logger(__name__)


def get_package_size(package_name: str, extra_deps: list[str] | None = None) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        venv_path = temp_path / "test_env"

        try:
            subprocess.run(
                [sys.executable, "-m", "venv", str(venv_path)],
                check=True,
                capture_output=True,
            )

            if sys.platform == "win32":
                pip_path = venv_path / "Scripts" / "pip"
                venv_path / "Scripts" / "python"
            else:
                pip_path = venv_path / "bin" / "pip"
                venv_path / "bin" / "python"

            install_cmd = [str(pip_path), "install", package_name]
            if extra_deps:
                install_cmd.extend(extra_deps)

            result = subprocess.run(install_cmd, check=False, capture_output=True, text=True)

            if result.returncode != 0:
                return {"error": result.stderr}

            site_packages = (
                venv_path / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"
            )
            if not site_packages.exists():
                site_packages = venv_path / "Lib" / "site-packages"

            if site_packages.exists():
                total_size = sum(f.stat().st_size for f in site_packages.rglob("*") if f.is_file())
                size_mb = total_size / (1024 * 1024)

                list_result = subprocess.run(
                    [str(pip_path), "list", "--format=json"],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                packages = json.loads(list_result.stdout) if list_result.returncode == 0 else []

                return {
                    "size_bytes": total_size,
                    "size_mb": round(size_mb, 2),
                    "packages": packages,
                    "package_count": len(packages),
                }
            return {"error": "Could not find site-packages directory"}

        except subprocess.CalledProcessError as e:
            return {"error": str(e)}
        except Exception as e:
            logger.error(
                "Failed to check package installation size",
                package=package_name,
                error=str(e),
            )
            return {"error": str(e)}


def main() -> None:
    libraries = {
        "kreuzberg": {
            "package": "kreuzberg",
            "description": "Comprehensive text extraction library",
        },
        "docling": {
            "package": "docling",
            "description": "IBM's document processing library",
        },
        "markitdown": {
            "package": "markitdown",
            "description": "Microsoft's markdown converter",
        },
        "unstructured": {
            "package": "unstructured",
            "description": "Unstructured.io document processing",
        },
    }

    results = {}

    for lib_name, lib_info in libraries.items():
        size_info = get_package_size(lib_info["package"])
        results[lib_name] = {
            "package": lib_info["package"],
            "description": lib_info["description"],
            **size_info,
        }

    with Path("installation_sizes.json").open("w") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    main()
