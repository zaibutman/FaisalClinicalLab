"""Production build script for Faisal Clinical Laboratory (Task R1).

Cleans previous artifacts and runs PyInstaller against ``faisal_lab.spec`` to
produce the onedir Windows executable under ``dist/FaisalClinicalLaboratory/``.

Usage (from the project root, using the project's virtual environment)::

    .venv\\Scripts\\python.exe build.py            # clean + build
    .venv\\Scripts\\python.exe build.py --clean     # clean only

This script only orchestrates packaging; it does not touch application logic.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

BASE_DIR: Path = Path(__file__).resolve().parent
SPEC_FILE: Path = BASE_DIR / "faisal_lab.spec"
DIST_DIR: Path = BASE_DIR / "dist"
BUILD_DIR: Path = BASE_DIR / "build"
APP_DIR_NAME: str = "FaisalClinicalLaboratory"


def _rmtree(path: Path) -> None:
    """Remove a directory tree if it exists, reporting what happened."""
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)
        print(f"  removed {path.relative_to(BASE_DIR)}")
    else:
        print(f"  (absent) {path.relative_to(BASE_DIR)}")


def _remove_pycache() -> None:
    """Delete every __pycache__ directory under the project."""
    removed = 0
    for cache in BASE_DIR.rglob("__pycache__"):
        # Never walk into the virtual environment.
        if ".venv" in cache.parts:
            continue
        shutil.rmtree(cache, ignore_errors=True)
        removed += 1
    print(f"  removed {removed} __pycache__ director(y/ies)")


def clean() -> None:
    """Remove old build/, dist/, and __pycache__ artifacts."""
    print("Cleaning previous artifacts...")
    _rmtree(BUILD_DIR)
    _rmtree(DIST_DIR)
    _remove_pycache()


def build() -> int:
    """Run PyInstaller against the spec. Returns the process exit code."""
    if not SPEC_FILE.exists():
        print(f"ERROR: spec file not found: {SPEC_FILE}")
        return 1

    print("Running PyInstaller...")
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", str(SPEC_FILE)]
    print("  " + " ".join(cmd))
    result = subprocess.run(cmd, cwd=str(BASE_DIR))
    return result.returncode


def main() -> int:
    """Entry point: clean (always) then build (unless --clean)."""
    clean_only = "--clean" in sys.argv[1:]

    clean()
    if clean_only:
        print("\nClean complete (build skipped: --clean).")
        return 0

    code = build()
    exe = DIST_DIR / APP_DIR_NAME / f"{APP_DIR_NAME}.exe"
    if code == 0 and exe.exists():
        print("\nBUILD SUCCEEDED")
        print(f"  Executable: {exe}")
        print(f"  Folder:     {DIST_DIR / APP_DIR_NAME}")
        return 0

    print("\nBUILD FAILED")
    print(f"  PyInstaller exit code: {code}")
    if not exe.exists():
        print(f"  Expected executable not found: {exe}")
    return code or 1


if __name__ == "__main__":
    raise SystemExit(main())
