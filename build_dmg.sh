#!/usr/bin/env bash
# Build calc.app and wrap it in a .dmg for macOS.
# Requires: the project .venv with PyQt6 (see README), plus macOS `hdiutil`.
set -euo pipefail
cd "$(dirname "$0")"

VERSION="1.0.0"
ARCH="$(uname -m)"   # arm64 on Apple Silicon
DMG="calc-${VERSION}-${ARCH}.dmg"
PY=".venv/bin/python"

[ -x "$PY" ] || { echo "error: missing .venv — run: python3 -m venv .venv && .venv/bin/pip install PyQt6" >&2; exit 1; }

# Icon: regenerate if missing (deterministic from make_icon.py).
[ -f calc.icns ] || "$PY" make_icon.py

"$PY" -c "import PyInstaller" 2>/dev/null || .venv/bin/pip install --quiet pyinstaller

rm -rf build dist
"$PY" -m PyInstaller \
  --noconfirm --clean \
  --windowed \
  --name calc \
  --osx-bundle-identifier org.calc.gui \
  --icon calc.icns \
  --add-data "calc:calc_engine" \
  calc_gui.py

# Version the bundle (PyInstaller leaves these unset) and sign ad-hoc.
/usr/libexec/PlistBuddy \
  -c "Set :CFBundleShortVersionString $VERSION" \
  -c "Add :CFBundleVersion string $VERSION" \
  "dist/calc.app/Contents/Info.plist"
codesign --force --deep --sign - "dist/calc.app"
codesign --verify --verbose=2 "dist/calc.app"

# Stage: calc.app + Applications alias (drag-to-install).
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
cp -R "dist/calc.app" "$STAGE/"
ln -s /Applications "$STAGE/Applications"

hdiutil create -volname "calc" -srcfolder "$STAGE" -ov -format UDZO \
  "dist/$DMG" >/dev/null

echo "built: dist/$DMG ($(du -h "dist/$DMG" | cut -f1))"
