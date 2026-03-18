#!/bin/bash
# Build ClashOfClansBot as a fully self-contained macOS .app + .dmg installer.
# Automatically downloads and bundles ADB and Tesseract so the user needs
# NOTHING pre-installed — just double-click the .app.
#
# Usage:
#   chmod +x build_macos.sh
#   ./build_macos.sh
#
# Prerequisites (build machine only):
#   pip install pyinstaller
#   brew install create-dmg    (optional, for DMG creation)

set -e

APP_NAME="ClashOfClansBot"
VERSION="${VERSION:-1.0.0}"
TOOLS_DIR="tools"

echo "=== Step 1: Clean previous builds ==="
rm -rf build dist "${APP_NAME}"*.dmg "${TOOLS_DIR}"

echo "=== Step 2: Download & bundle ADB (Android Platform Tools) ==="
mkdir -p "${TOOLS_DIR}"

# Detect architecture
ARCH=$(uname -m)
if [ "$ARCH" = "arm64" ]; then
    ADB_URL="https://dl.google.com/android/repository/platform-tools-latest-darwin.zip"
else
    ADB_URL="https://dl.google.com/android/repository/platform-tools-latest-darwin.zip"
fi

echo "Downloading Android Platform Tools..."
curl -sL "$ADB_URL" -o /tmp/platform-tools.zip
unzip -qo /tmp/platform-tools.zip -d /tmp/
cp /tmp/platform-tools/adb "${TOOLS_DIR}/adb"
# ADB also needs these libraries alongside it
find /tmp/platform-tools -name "*.dylib" -exec cp {} "${TOOLS_DIR}/" \; 2>/dev/null || true
chmod +x "${TOOLS_DIR}/adb"
rm -rf /tmp/platform-tools /tmp/platform-tools.zip
echo "Bundled: ${TOOLS_DIR}/adb"

echo "=== Step 3: Download & bundle Tesseract ==="
# Use Homebrew to get Tesseract binary + eng language data, then copy into tools/
if ! command -v brew &> /dev/null; then
    echo "WARNING: Homebrew not found. Installing Tesseract requires brew."
    echo "Install Homebrew first: https://brew.sh"
    echo "Skipping Tesseract bundling — users will need it installed separately."
else
    # Ensure tesseract is installed on the build machine
    if ! brew list tesseract &> /dev/null; then
        echo "Installing tesseract via Homebrew (build machine only)..."
        brew install tesseract
    fi

    # Copy the tesseract binary
    TESS_BIN=$(brew --prefix tesseract)/bin/tesseract
    if [ -f "$TESS_BIN" ]; then
        cp "$TESS_BIN" "${TOOLS_DIR}/tesseract"
        chmod +x "${TOOLS_DIR}/tesseract"
        echo "Bundled: ${TOOLS_DIR}/tesseract"

        # Copy tessdata (language files)
        TESSDATA_DIR=$(brew --prefix tesseract)/share/tessdata
        if [ -d "$TESSDATA_DIR" ]; then
            mkdir -p "${TOOLS_DIR}/tessdata"
            cp "$TESSDATA_DIR"/eng.* "${TOOLS_DIR}/tessdata/" 2>/dev/null || true
            cp "$TESSDATA_DIR"/osd.* "${TOOLS_DIR}/tessdata/" 2>/dev/null || true
            echo "Bundled: ${TOOLS_DIR}/tessdata/"
        fi

        # Copy dylib dependencies so tesseract works outside of Homebrew.
        # Use @loader_path so libs resolve relative to the binary/dylib that
        # loads them, not the PyInstaller executable (which is in a different dir).
        echo "Bundling Tesseract dylib dependencies..."
        TESS_LIBS=$(otool -L "${TOOLS_DIR}/tesseract" | grep -E '/opt|/usr/local' | awk '{print $1}')
        for lib in $TESS_LIBS; do
            if [ -f "$lib" ]; then
                LIB_NAME=$(basename "$lib")
                cp "$lib" "${TOOLS_DIR}/${LIB_NAME}"
                install_name_tool -change "$lib" "@loader_path/${LIB_NAME}" "${TOOLS_DIR}/tesseract" 2>/dev/null || true
            fi
        done

        # Recursively fix dependencies (up to 3 levels deep for full chain)
        for _pass in 1 2 3; do
            CHANGED=0
            for bundled_lib in "${TOOLS_DIR}"/*.dylib; do
                [ -f "$bundled_lib" ] || continue
                DEP_LIBS=$(otool -L "$bundled_lib" | grep -E '/opt|/usr/local' | awk '{print $1}')
                for dep in $DEP_LIBS; do
                    if [ -f "$dep" ]; then
                        DEP_NAME=$(basename "$dep")
                        if [ ! -f "${TOOLS_DIR}/${DEP_NAME}" ]; then
                            cp "$dep" "${TOOLS_DIR}/${DEP_NAME}"
                            CHANGED=1
                        fi
                        install_name_tool -change "$dep" "@loader_path/${DEP_NAME}" "$bundled_lib" 2>/dev/null || true
                    fi
                done
            done
            [ "$CHANGED" -eq 0 ] && break
        done
        echo "Dylib dependencies bundled."
    else
        echo "WARNING: Could not find tesseract binary at $TESS_BIN"
    fi
fi

# Export version so bot/updater.py and .spec pick it up at build time
export VERSION
export APP_VERSION="${VERSION}"

echo "=== Step 4: Build .app bundle with PyInstaller ==="
# Use venv pyinstaller if available, otherwise fall back to PATH
if [ -x ".venv/bin/pyinstaller" ]; then
    .venv/bin/pyinstaller --noconfirm "${APP_NAME}.spec"
else
    pyinstaller --noconfirm "${APP_NAME}.spec"
fi

echo "=== Step 5: Verify .app was created ==="
if [ ! -d "dist/${APP_NAME}.app" ]; then
    echo "ERROR: dist/${APP_NAME}.app not found. Build failed."
    exit 1
fi

echo "=== Step 5b: Ad-hoc code signing ==="
# macOS adds synthetic FinderInfo xattrs to .framework dirs which break
# codesign --deep. Fix: sign inner frameworks individually, strip the
# top-level FinderInfo, then sign the outer app without --deep.
find "dist/${APP_NAME}.app/Contents/Frameworks" -name "*.framework" -type d \
    -exec codesign --force -s - {} \; 2>/dev/null || true
find "dist/${APP_NAME}.app" -name "*.dylib" -type f \
    -exec codesign --force -s - {} \; 2>/dev/null || true
find "dist/${APP_NAME}.app" -name "*.so" -type f \
    -exec codesign --force -s - {} \; 2>/dev/null || true
xattr -cr "dist/${APP_NAME}.app"
codesign --force -s - "dist/${APP_NAME}.app"
echo "Ad-hoc signed: dist/${APP_NAME}.app"

# Show what's inside the tools bundle
echo ""
echo "Bundled tools:"
ls -lh "dist/${APP_NAME}.app/Contents/Resources/"*tools* 2>/dev/null || \
ls -lh "dist/${APP_NAME}/"tools/ 2>/dev/null || \
echo "(tools directory will be inside the app bundle)"
echo ""
echo "Built: dist/${APP_NAME}.app"

echo "=== Step 6: Create DMG installer ==="
if command -v create-dmg &> /dev/null; then
    # Build create-dmg args
    DMG_ARGS=(
        --volname "${APP_NAME} ${VERSION}"
        --window-pos 200 120
        --window-size 600 400
        --icon-size 100
        --icon "${APP_NAME}.app" 150 190
        --app-drop-link 450 190
        --hide-extension "${APP_NAME}.app"
    )

    # Add volume icon and background if icon.icns exists
    if [ -f "icon.icns" ]; then
        DMG_ARGS+=(--volicon "icon.icns")
    fi

    # Add background image if it exists (e.g. a 600x400 PNG)
    if [ -f "dmg_background.png" ]; then
        DMG_ARGS+=(--background "dmg_background.png")
    fi

    create-dmg "${DMG_ARGS[@]}" \
        "${APP_NAME}-${VERSION}.dmg" \
        "dist/${APP_NAME}.app"
    echo ""
    echo "============================================="
    echo "  Done! Your installer is ready:"
    echo "  ${APP_NAME}-${VERSION}.dmg"
    echo "============================================="
else
    echo ""
    echo "create-dmg not found. Install with: brew install create-dmg"
    echo "Your .app is ready at: dist/${APP_NAME}.app"
fi

# Clean up tools dir (it's now inside the .app)
rm -rf "${TOOLS_DIR}"
