# GitHub Release Pipeline Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Push a git tag like `v1.0.0` and have GitHub Actions automatically build a macOS DMG and publish it as a GitHub Release.

**Architecture:** A single GitHub Actions workflow triggered by `v*` tags. The workflow extracts the version from the tag, patches it into the spec and updater, runs the existing `build_macos.sh`, and uploads the DMG as a release asset. Version is derived from the tag — no manual version bumping needed.

**Tech Stack:** GitHub Actions (macos-latest runner), existing build_macos.sh, gh CLI for release creation.

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `.github/workflows/release.yml` | Create | GitHub Actions workflow triggered by `v*` tags |
| `build_macos.sh` | Modify | Accept `VERSION` env var instead of hardcoded `1.0.0` |
| `bot/updater.py` | Modify | Read version from env var at build time, baked into bundle |
| `ClashOfClansBot.spec` | Modify | Read version from `VERSION` env var for Info.plist |

---

## Chunk 1: Version Parameterization

### Task 1: Make build_macos.sh accept VERSION from environment

**Files:**
- Modify: `build_macos.sh:17`

- [ ] **Step 1: Update VERSION assignment to use env var with fallback**

Change line 17 from:
```bash
VERSION="1.0.0"
```
to:
```bash
VERSION="${VERSION:-1.0.0}"
```

This means `VERSION=2.0.0 ./build_macos.sh` works, and bare `./build_macos.sh` still defaults to `1.0.0`.

- [ ] **Step 2: Verify build still works locally**

Run: `./build_macos.sh 2>&1 | tail -5`
Expected: Build completes, DMG named `ClashOfClansBot-1.0.0.dmg`

- [ ] **Step 3: Commit**

```bash
git add build_macos.sh
git commit -m "build: accept VERSION env var in build script"
```

### Task 2: Make ClashOfClansBot.spec read version from environment

**Files:**
- Modify: `ClashOfClansBot.spec:1-6` and `:121-125`

- [ ] **Step 1: Add version reading at top of spec**

After line 4 (`import os`), add:
```python
VERSION = os.environ.get('VERSION', '1.0.0')
```

- [ ] **Step 2: Replace hardcoded versions in info_plist**

Change lines 124-125 from:
```python
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
```
to:
```python
        'CFBundleVersion': VERSION,
        'CFBundleShortVersionString': VERSION,
```

- [ ] **Step 3: Commit**

```bash
git add ClashOfClansBot.spec
git commit -m "build: read version from VERSION env var in spec"
```

### Task 3: Make bot/updater.py version configurable at build time

**Files:**
- Modify: `bot/updater.py:15`

The PyInstaller bundle bakes in the Python source at build time, so we read the env var during the build and it gets frozen into the binary.

- [ ] **Step 1: Change APP_VERSION to read from environment**

Change line 15 from:
```python
APP_VERSION = "1.0.0"
```
to:
```python
APP_VERSION = os.environ.get("APP_VERSION", "1.0.0")
```

Also add `import os` at the top (line 3, after `import json`):
```python
import os
```

- [ ] **Step 2: Update build_macos.sh to export APP_VERSION before PyInstaller**

In `build_macos.sh`, before the PyInstaller call (before line 111 `echo "=== Step 4:..."`), add:
```bash
# Export version so bot/updater.py picks it up at build time
export VERSION
export APP_VERSION="${VERSION}"
```

- [ ] **Step 3: Commit**

```bash
git add bot/updater.py build_macos.sh
git commit -m "build: derive app version from tag via env var"
```

---

## Chunk 2: GitHub Actions Workflow

### Task 4: Create the release workflow

**Files:**
- Create: `.github/workflows/release.yml`

- [ ] **Step 1: Create the workflow file**

```yaml
name: Build & Release macOS DMG

on:
  push:
    tags:
      - 'v*'

permissions:
  contents: write

jobs:
  build:
    runs-on: macos-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python 3.13
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'

      - name: Extract version from tag
        id: version
        run: echo "version=${GITHUB_REF_NAME#v}" >> "$GITHUB_OUTPUT"

      - name: Install Python dependencies
        run: |
          python -m venv .venv
          .venv/bin/pip install -r requirements.txt pyinstaller

      - name: Install system dependencies
        run: |
          brew install tesseract create-dmg

      - name: Build DMG
        env:
          VERSION: ${{ steps.version.outputs.version }}
          APP_VERSION: ${{ steps.version.outputs.version }}
        run: |
          chmod +x build_macos.sh
          ./build_macos.sh

      - name: Verify DMG exists
        run: |
          DMG_FILE="ClashOfClansBot-${{ steps.version.outputs.version }}.dmg"
          if [ ! -f "$DMG_FILE" ]; then
            echo "ERROR: $DMG_FILE not found"
            ls -la *.dmg 2>/dev/null || echo "No DMG files found"
            exit 1
          fi
          echo "DMG_FILE=$DMG_FILE" >> "$GITHUB_ENV"
          ls -lh "$DMG_FILE"

      - name: Create GitHub Release
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          gh release create "${{ github.ref_name }}" \
            "${{ env.DMG_FILE }}" \
            --title "ClashOfClans Bot ${{ github.ref_name }}" \
            --generate-notes
```

- [ ] **Step 2: Verify YAML syntax**

Run: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/release.yml'))" 2>&1 || python3 -c "import json; print('YAML check skipped, no pyyaml')"`

If no pyyaml available, visually confirm indentation is correct.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/release.yml
git commit -m "ci: add GitHub Actions release workflow for macOS DMG"
```

---

## Chunk 3: Test the Full Pipeline

### Task 5: Push and trigger a test release

- [ ] **Step 1: Push all commits to main**

```bash
git push origin main
```

- [ ] **Step 2: Create and push a test tag**

```bash
git tag v1.0.0
git push origin v1.0.0
```

- [ ] **Step 3: Monitor the GitHub Actions run**

```bash
gh run list --limit 1
gh run watch
```

Expected: Workflow runs, builds DMG, creates release with DMG attached.

- [ ] **Step 4: Verify the release**

```bash
gh release view v1.0.0
```

Expected: Release exists with `ClashOfClansBot-1.0.0.dmg` as an asset.

- [ ] **Step 5: Test the updater sees the release**

Launch the locally installed app. The updater (`bot/updater.py`) calls the GitHub Releases API — it should now find the release (though since versions match, it won't prompt for update).

---

## Summary of Release Workflow (for future reference)

```bash
# 1. Make your changes, commit
git add . && git commit -m "feat: whatever"

# 2. Tag with the new version
git tag v1.1.0

# 3. Push code and tag
git push origin main --tags

# 4. GitHub Actions builds and publishes automatically
# Monitor at: https://github.com/Armin2708/ClashOfClans-Bot/actions
```
