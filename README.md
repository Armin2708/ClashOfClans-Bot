# Clash of Clans Bot

Automated Clash of Clans farming bot that uses YOLOv11 for screen detection, ADB for device control, and a PySide6 desktop GUI. Designed to run against BlueStacks or any Android emulator with ADB access.

---

## Features

- **YOLO-based detection** — recognizes buildings, buttons, and game states using a trained YOLOv11 model (no fragile template matching)
- **ADB screenrecord stream** — real-time video feed via `adb exec-out screenrecord` piped through `ffmpeg`, with auto-reconnect
- **State machine** — robust game state tracking (Village, Attack Menu, Army, Searching, Scouting, Battle, Results) with timeout recovery
- **Farming loop** — automated search, scout, attack, and loot cycle with configurable thresholds
- **Desktop GUI** — PySide6 app with Dashboard, Settings, Log, and Label & Train tabs
- **Onboarding wizard** — guides first-time setup (ADB path, emulator connection, model download)
- **Synthetic training pipeline** — generate thousands of labeled base images from building sprites on an isometric grid
- **Sprite calibrator** — PySide6 tool with drag handles to precisely fit each sprite to its tile diamond
- **2633 building classes** — full TH18 class registry covering all buildings, levels, and variants

---

## Quick Start

### Prerequisites

- Python 3.10+
- An Android emulator (BlueStacks recommended) with Clash of Clans installed
- ADB (Android Debug Bridge) accessible from terminal
- ffmpeg installed (`brew install ffmpeg`)

### Install

```bash
git clone <repo-url>
cd clashofclans
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Run

```bash
# GUI mode (recommended)
python app.py

# Headless CLI
python -m bot.main          # continuous farming loop
python -m bot.main farm     # farm to loot target then stop
```

---

## Project Structure

```
clashofclans/
├── app.py                          # GUI entry point
├── requirements.txt                # Python dependencies
│
├── bot/                            # Core bot logic
│   ├── main.py                     # Main farming loop
│   ├── battle.py                   # Attack execution
│   ├── config.py                   # Resolution-scaled coordinates
│   ├── detector.py                 # YOLOv11 inference wrapper
│   ├── metrics.py                  # Loot tracking & statistics
│   ├── notify.py                   # Notification system
│   ├── resources.py                # Loot reading (OCR)
│   ├── screen.py                   # Screen state detection
│   ├── settings.py                 # Settings singleton (~/.cocbot/settings.json)
│   ├── state_machine.py            # GameState enum & transitions
│   ├── stream.py                   # ADB screenrecord video stream
│   ├── updater.py                  # Auto-update checker
│   ├── utils.py                    # Template loading, debug tools
│   └── vision.py                   # YOLO detection + digit OCR
│
├── gui/                            # PySide6 desktop GUI
│   ├── main_window.py              # Main window with tab layout
│   ├── onboarding.py               # First-run setup wizard
│   ├── bot_worker.py               # Background bot thread
│   ├── glass.py                    # Frosted glass effect
│   ├── log_handler.py              # Log stream to GUI
│   ├── theme.py                    # Dark theme styling
│   ├── panels/
│   │   ├── control_panel.py        # Start/stop, status dashboard
│   │   ├── settings_panel.py       # Settings editor
│   │   ├── log_panel.py            # Live log viewer
│   │   └── labeling_panel.py       # Label & Train tab
│   ├── widgets/
│   │   ├── annotation_canvas.py    # Bounding box annotation widget
│   │   └── class_selector.py       # Building class picker
│   └── workers/
│       └── train_worker.py         # Background YOLO training thread
│
├── training/                       # YOLO training pipeline
│   ├── train.py                    # Train script (ultralytics)
│   ├── dataset_manager.py          # Labeled dataset I/O
│   ├── generate/                   # Synthetic data generation
│   │   ├── base_builder.py         # Isometric grid-based base generator
│   │   ├── building_tiles.py       # Tile footprint definitions (single source of truth)
│   │   └── class_registry.py       # 2633-class registry (TH18)
│   └── collect/                    # Data collection from external sources
│       ├── capture_frames.py       # Screenshot capture during bot runs
│       ├── collect_bases.py        # Automated base scouting + capture
│       ├── download_dataset.py     # HuggingFace dataset download
│       ├── download_roboflow.py    # Roboflow Universe download
│       ├── merge_datasets.py       # Multi-source dataset merger
│       └── scrape_wiki.py          # Fandom wiki sprite scraper
│
├── tools/                          # Interactive utilities
│   ├── sprite_calibrator.py        # PySide6 sprite sizing tool (drag handles + folder tree)
│   ├── grid_calibrator.py          # OpenCV isometric grid alignment tool
│   ├── base_editor.py              # Interactive base layout editor
│   ├── calibrate.py                # Auto-calibration via wall detection
│   ├── download_icons.py           # Troop/spell icon downloader
│   ├── extract_digits.py           # Digit template extractor
│   ├── extract_templates.py        # Button/popup template extractor
│   ├── extract_wall.py             # Wall template extractor
│   └── find_buttons.py             # Debug coordinate finder
│
├── tests/                          # Test suites
│   ├── test_vision_yolo.py         # YOLO detection unit tests
│   ├── test_detector.py            # Detector class tests
│   ├── test_stream_unit.py         # Stream unit tests
│   ├── test_stream_integration.py  # Live stream integration test
│   ├── test_offline.py             # Offline reference image tests
│   ├── test.py                     # Live single-feature tests
│   └── test_all.py                 # Full live test suite
│
├── data/                           # Non-code assets
│   ├── sprites/                    # Building sprite PNGs
│   │   ├── defense/                # Air defense, cannon, tesla, etc.
│   │   ├── resource/               # Gold mine, elixir storage, etc.
│   │   ├── army/                   # Army camp, barracks, lab, etc.
│   │   ├── trap/                   # Bombs, spring traps, etc.
│   │   └── other/                  # Town hall, walls, clan castle, etc.
│   ├── templates/                  # Detection templates
│   │   ├── base/                   # Empty base background image
│   │   ├── buttons/                # UI button templates
│   │   ├── digits/                 # OCR digit templates (0-9)
│   │   ├── icons/                  # Troop & spell icons
│   │   └── popups/                 # Popup close button templates
│   ├── models/                     # Trained YOLO weights (.pt)
│   └── calibration/                # Calibration data
│       ├── grid_calibration.json   # Isometric grid anchor & tile sizes
│       ├── sprite_scales.json      # Per-sprite scale & offset corrections
│       └── confirmed_sprites.json  # Sprites verified as true-to-tile
│
├── build/                          # Build configuration
│   ├── build_macos.sh              # macOS .app + .dmg build script
│   ├── ClashOfClansBot.spec        # PyInstaller spec
│   ├── icon.icns                   # App icon
│   └── start.sh                    # Launch helper
│
├── docs/                           # Documentation
│   ├── SETUP.md                    # Detailed setup guide
│   ├── FLOW.md                     # Bot flow diagrams
│   └── SYNTHETIC_BASE_SPEC.md      # Synthetic data generation spec
│
├── datasets/                       # Training data (gitignored)
└── .github/workflows/release.yml   # GitHub Actions release pipeline
```

---

## Architecture

### Detection: YOLOv11

All screen detection uses a trained YOLOv11 model (`bot/detector.py` + `bot/vision.py`). The model recognizes buildings, UI buttons, and game elements. Digit OCR for loot values uses template matching as a fallback.

### Video Stream

`bot/stream.py` pipes `adb exec-out screenrecord --output-format=h264 -` through `ffmpeg` into a numpy ring buffer. No scrcpy dependency. Auto-reconnects on disconnect or when Android hits its 3-minute recording limit.

### State Machine

`bot/state_machine.py` defines a `GameState` enum with automatic timeout recovery:

| State | Description | Timeout Action |
|-------|-------------|----------------|
| VILLAGE | Home village idle | Start attack flow |
| ATTACK_MENU | "Find a Match" screen | Tap find match |
| ARMY | Army composition screen | Start search |
| SEARCHING | Matchmaking queue | Wait |
| SCOUTING | Viewing enemy base | Scout or next |
| BATTLE_ACTIVE | Attack in progress | Wait for end |
| RESULTS | Post-battle results | Return home |
| UNKNOWN | Unrecognized screen | Recovery actions |

### Settings

All configuration lives in `~/.cocbot/settings.json`, managed by a thread-safe singleton (`bot/settings.py`). The GUI settings panel provides a visual editor.

---

## Training Pipeline

### 1. Collect Data

```bash
# Scrape building sprites from the wiki
python -m training.collect.scrape_wiki --category all

# Capture screenshots during live bot runs
python -m training.collect.collect_bases --count 500

# Download public datasets
python -m training.collect.download_dataset
python -m training.collect.download_roboflow
```

### 2. Calibrate Sprites

```bash
# Align the isometric grid to the base template
python tools/grid_calibrator.py

# Resize/position each sprite on its tile diamond
python tools/sprite_calibrator.py
```

The sprite calibrator is a PySide6 app with:
- Folder tree sidebar (defense, resource, army, trap, other)
- Drag the sprite box to move
- Drag corner handles to resize
- Arrow keys for 1px precision
- Saves to `data/calibration/sprite_scales.json`

### 3. Generate Synthetic Data

```bash
# Generate labeled training images with sprites on the isometric grid
python -m training.generate.base_builder --count 1000 --preview
```

The base builder places sprites at correct tile positions using a 44x44 isometric grid calibrated to the game's coordinate system. Each building uses its calibrated scale and offset for pixel-accurate placement. YOLO labels are auto-generated.

### 4. Train

```bash
python training/train.py --data datasets/synthetic_bases/dataset.yaml --epochs 100
```

Best weights are saved to `data/models/coc.pt`.

---

## Calibration Tools

| Tool | Purpose | UI |
|------|---------|-----|
| `tools/sprite_calibrator.py` | Resize & position sprites on tile diamonds | PySide6 (drag handles) |
| `tools/grid_calibrator.py` | Align isometric grid to base template | OpenCV (keyboard + mouse) |
| `tools/base_editor.py` | Interactively place buildings on the grid | OpenCV |

Calibration data is stored in `data/calibration/`:
- `grid_calibration.json` — grid anchor point and tile dimensions
- `sprite_scales.json` — per-sprite scale factor and pixel offset
- `confirmed_sprites.json` — sprites verified as correct at default scale

---

## Running Tests

```bash
# Unit tests (no emulator needed)
pytest tests/test_vision_yolo.py tests/test_detector.py tests/test_stream_unit.py -v

# Offline tests with reference images
python tests/test_offline.py

# Live tests (requires emulator with CoC open)
python tests/test.py
python tests/test_all.py
```

---

## Build & Release

```bash
# Build macOS .app bundle + .dmg
./build/build_macos.sh
```

Uses PyInstaller. Bundles ADB and Tesseract automatically. GitHub Actions builds and publishes releases on `v*` tags.

---

## Tech Stack

- **Python 3.10+**
- **YOLOv11** (ultralytics) — object detection
- **OpenCV** — image processing, template matching
- **PySide6** — desktop GUI
- **ADB** — Android device control
- **ffmpeg** — video stream decoding
- **Tesseract** — OCR fallback

---

## License

Private project. Not for distribution.
