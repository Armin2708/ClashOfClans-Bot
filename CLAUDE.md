# Clash of Clans Bot

Automated Clash of Clans farming bot with YOLO-based screen detection, ADB control, and a PySide6 GUI.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the GUI
python app.py

# Run the bot headless (CLI)
python -m bot.main          # normal loop
python -m bot.main farm     # farm to target then stop
```

## Running Tests

```bash
# Unit tests (no emulator needed)
pytest tests/test_vision_yolo.py tests/test_detector.py tests/test_stream_unit.py -v

# Offline tests with reference images
python tests/test_offline.py

# Live tests (requires running emulator with CoC open)
python tests/test.py
python tests/test_all.py
```

## Architecture

### Detection: YOLO (not templates)
All screen detection uses YOLOv11 (`bot/detector.py` + `bot/vision.py`). The old OpenCV template matching system was removed. `bot/utils.py` retains `load_template` only for digit OCR templates.

### Video Stream: ADB screenrecord
`bot/stream.py` pipes `adb exec-out screenrecord` through `ffmpeg` into a ring buffer. No scrcpy dependency. Auto-reconnects on disconnect or Android's 3-minute limit.

### Settings: Singleton backed by JSON
`bot/settings.py` — all config lives in `~/.cocbot/settings.json`. `bot/config.py` is a shim that auto-scales pixel coordinates to detected screen resolution.

### Screen State Machine
`bot/state_machine.py` — `GameState` enum with timeouts and recovery actions. States: VILLAGE, ATTACK_MENU, ARMY, SEARCHING, SCOUTING, BATTLE_ACTIVE, RESULTS, UNKNOWN.

### GUI
PySide6 app (`app.py` → `gui/main_window.py`). Tabs: Dashboard, Settings, Log, Label & Train. Onboarding wizard on first run.

## Training Pipeline

```bash
# Collect base screenshots (requires emulator)
python -m training.collect.collect_bases --count 500

# Download public dataset
python -m training.collect.download_dataset

# Generate synthetic training data
python -m training.generate.base_builder --count 1000 --preview

# Train YOLO model
python training/train.py --data datasets/public/dataset.yaml --epochs 50
```

Model weights go to `data/models/coc.pt`. Class registry: `training/generate/class_registry.py` (2633 classes, TH18).

## Calibration Tools

```bash
# Visually calibrate the isometric grid overlay
python tools/grid_calibrator.py

# Resize/position sprites on their tile diamonds
python tools/sprite_calibrator.py
```

Calibration data saved to `data/calibration/`.

## Build

```bash
# macOS .app + .dmg
./build/build_macos.sh
```

Uses PyInstaller. Bundles ADB + Tesseract automatically. GitHub Actions releases on `v*` tags.

## Key Directories

- `bot/` — core bot logic (battle, screen, vision, stream, settings)
- `gui/` — PySide6 GUI (panels, widgets, workers)
- `training/` — YOLO training pipeline
  - `generate/` — synthetic data generation (base_builder, building_tiles, class_registry)
  - `collect/` — data collection (screenshots, downloads, scraping, merging)
- `tools/` — interactive utilities (calibrators, template extractors)
- `tests/` — unit, offline, and live test suites
- `data/` — all non-code assets
  - `sprites/` — building sprite PNGs (defense, resource, army, trap, other)
  - `templates/` — OCR digits, button images, base template
  - `models/` — trained YOLO weights
  - `calibration/` — grid + sprite calibration JSONs
- `build/` — PyInstaller spec, build scripts, app icon
- `datasets/` — training data (gitignored)
