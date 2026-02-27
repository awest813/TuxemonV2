#!/bin/bash
# Debian/Ubuntu Wine build for Windows PyInstaller package.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." >/dev/null 2>&1 && pwd)"
cd "$REPO_ROOT"

PYTHON_VERSION="${PYTHON_VERSION:-3.10}"
WINE_PYTHON="wine python${PYTHON_VERSION}"
BUILD_DIR="build/tuxemon"

if ! command -v wine >/dev/null 2>&1; then
  echo "Error: wine command not found."
  exit 1
fi

# Run setup script.
buildconfig/setup_wine_debian10.sh

# Install dependencies.
$WINE_PYTHON -m pip install -U setuptools wheel pyinstaller
$WINE_PYTHON -m pip install -U -r requirements.txt

# Clean up .pyc files.
find . -name "*.pyc" -delete

# Build with PyInstaller.
wine pyinstaller buildconfig/pyinstaller/tuxemon.spec

if [ ! -d "$BUILD_DIR" ]; then
  echo "Error: Build directory not found."
  exit 1
fi

PYTHON_DLL_WIN="$($WINE_PYTHON -c 'import sys; print(f"{sys.base_prefix}\\python{sys.version_info.major}{sys.version_info.minor}.dll")')"
PYTHON_DLL="$(winepath -u "$PYTHON_DLL_WIN")"
if [ ! -f "$PYTHON_DLL" ]; then
  echo "Error: Python runtime DLL not found at: $PYTHON_DLL"
  exit 1
fi

cp "$PYTHON_DLL" "$BUILD_DIR/"

for file in LICENSE CONTRIBUTING.md CONTRIBUTORS.md ATTRIBUTIONS.md README.md SPYDER_README.md; do
  cp "$file" "$BUILD_DIR/"
done

echo "Windows PyInstaller build complete."
