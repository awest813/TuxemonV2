#!/bin/bash
# Debian/Ubuntu Wine build for Windows cx_Freeze package.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." >/dev/null 2>&1 && pwd)"
cd "$REPO_ROOT"

PYTHON_VERSION="${PYTHON_VERSION:-3.10}"
WINE_PYTHON="wine python${PYTHON_VERSION}"
DIST_DIR="dist/windows_cx_freeze"

if ! command -v wine >/dev/null 2>&1; then
  echo "Error: wine command not found."
  exit 1
fi

# Install dependencies.
$WINE_PYTHON -m pip install -U setuptools wheel cx_Freeze
$WINE_PYTHON -m pip install -U -r requirements.txt

# Clean up .pyc files.
find . -name "*.pyc" -delete

# Build with cx_Freeze.
$WINE_PYTHON buildconfig/setup_cx_freeze.py build

BUILD_PATH="$(find build -type d -name "exe.win*" | head -n 1)"
if [ -z "$BUILD_PATH" ]; then
  echo "Error: Build directory not found."
  exit 1
fi

PYTHON_DLL_WIN="$($WINE_PYTHON -c 'import sys; print(f"{sys.base_prefix}\\python{sys.version_info.major}{sys.version_info.minor}.dll")')"
PYTHON_DLL="$(winepath -u "$PYTHON_DLL_WIN")"
if [ ! -f "$PYTHON_DLL" ]; then
  echo "Error: Python runtime DLL not found at: $PYTHON_DLL"
  exit 1
fi

cp "$PYTHON_DLL" "$BUILD_PATH/"

for file in LICENSE CONTRIBUTING.md CONTRIBUTORS.md ATTRIBUTIONS.md README.md SPYDER_README.md; do
  cp "$file" "$BUILD_PATH/"
done

mkdir -p "$DIST_DIR"
cp -a "$BUILD_PATH"/* "$DIST_DIR"

echo "Windows cx_Freeze build complete."
