# V1 Release — Feature Trimming, Onboarding & UI Redesign

## Overview

Prepare the Clash of Clans Bot for its first public release by removing incomplete/complex features (walls, troops), adding a first-launch onboarding wizard, and redesigning the UI with a clean tabbed layout using a refined glass aesthetic.

## Goals

- Ship a focused, reliable farming bot without half-baked features
- Guide new users through setup with a polished onboarding flow
- Present a clean, modern UI that's simple to use

## Non-Goals

- Adding new bot capabilities (troop composition, wall upgrades can return in v2)
- Changing the bot's core automation logic (state machine, vision, ADB interaction)
- Cross-platform support (macOS only for v1)

---

## 1. Feature Removals

### 1.1 Wall Upgrade System — Remove Entirely

**Files to delete:**
- `bot/walls.py` — wall upgrade public API
- `bot/buildings.py` — entire file is wall-only code (WallUpgradeStrategy, Building dataclass, detect_walls delegation). Nothing remains after wall removal.
- `templates/buttons/upgrade_wall.png`
- `templates/buttons/upgrade_wall_elixir.png`
- `templates/buttons/upgrade_more.png`
- `templates/walls/` — entire directory

**Files to modify:**
- `bot/vision.py` — remove `detect_walls()` function and wall-related constants (WALL_DEDUP_DIST, wall template references)
- `bot/main.py` — remove wall imports (`from bot.buildings import GOLD_WALL, WallUpgradeStrategy`), remove `UPGRADE_STRATEGIES` list, and **replace the "resources full → upgrade → stop on failure" logic** (lines ~266-286). After wall removal, the bot should simply proceed to attack regardless of resource levels. The `main()` function should behave like `farm_to_max()` — always attack. Consider making `farm_to_max()` the single entry point.
- `bot/settings.py` — remove wall-related default settings: `max_wall_upgrades`, `wall_scales`, `wall_match_threshold`, `wall_dedup_dist`, `wall_sort_row_height`. Remove `wall_dedup_dist` and `wall_sort_row_height` from `_PIXEL_X_KEYS`.
- `bot/config.py` — remove `wall_scales` from `_TUPLE_LIST_KEYS`
- `bot/metrics.py` — remove `record_wall_upgrade()` method (dead code after wall removal)
- `gui/panels/resource_panel.py` — remove wall upgrade slider (max_wall_upgrades: 1-10)
- `tests/test.py` — remove wall-related test cases and imports
- `tests/test_offline.py` — remove wall-related test cases and imports from `bot.walls` / `bot.vision.detect_walls`

### 1.2 Troop System — Remove Entirely

**Files to delete:**
- `gui/panels/army_panel.py` — troop composition editor (entire tab)

**Files to modify:**
- `bot/settings.py` — remove `army_composition` default setting
- `gui/main_window.py` — remove Army tab from the tab widget

**No changes needed:**
- `bot/battle.py` — already implements a composition-agnostic "deploy all" strategy (detects slots, taps each, deploys via rapid-tapping). No composition-aware logic exists here.
- `bot/vision.py` — troop slot detection is needed for "deploy all" and has no composition-matching logic
- `templates/icons/` — keep troop icons (used for slot detection during battle)

---

## 2. Resolution Validation

The base resolution is already 2560×1440 throughout the codebase. No coordinate changes needed.

**Add startup validation:**
- In the onboarding "Connect" step, after a successful ADB connection, automatically check the device resolution via `bot/screen.py` detection methods
- If resolution ≠ 2560×1440, show an error message: "BlueStacks must be set to 2560×1440 resolution. Current: {width}×{height}"
- Block proceeding to the next onboarding step until resolution is correct
- In the Settings tab post-onboarding, resolution detection should be automatic upon successful ADB connection (merged into the connect action, not a separate button)

---

## 3. Onboarding — Card Carousel

### 3.1 Behavior

- Shows on first launch only (persisted via `onboarding_completed: bool` in settings)
- Full-window card carousel with animated slide transitions
- Dot indicators at bottom showing current step
- Back/Next navigation (Next button text changes per step)
- Cannot be skipped — each step must be completed before advancing (except Welcome)

### 3.2 Steps

**Step 1 — Welcome**
- Icon/logo at top
- Title: "Welcome to CoC Bot"
- Subtitle: "Automated farming for Clash of Clans. Let's get you set up in a few steps."
- Button: "Get Started →"

**Step 2 — BlueStacks**
- Title: "Install BlueStacks"
- Body: "CoC Bot works with BlueStacks emulator. Download and install it, then set the resolution to 2560×1440 in BlueStacks settings."
- Action: "Download BlueStacks" button → opens `https://www.bluestacks.com/download` in system browser
- Instruction: Brief numbered steps for setting resolution in BlueStacks
- Button: "I've Installed BlueStacks →"

**Step 3 — Connect**
- Title: "Connect to BlueStacks"
- Body: "Enter the ADB address for your BlueStacks instance. The default is usually localhost:5555."
- Input: ADB device address (pre-filled with `localhost:5555`)
- Action: "Test Connection" button
  - On success + correct resolution: green checkmark, "Connected! Resolution: 2560×1440"
  - On success + wrong resolution: orange warning, "Connected but resolution is {w}×{h}. Please set to 2560×1440."
  - On failure: red error, "Could not connect. Make sure BlueStacks is running."
- Button: "Continue →" (only enabled after successful connection + correct resolution)

**Step 4 — Ready**
- Title: "You're All Set!"
- Subtitle: "CoC Bot is ready to farm. Hit the button below to start."
- Optional: brief tip about starting the bot
- Button: "Launch Bot →" (transitions to main app, sets `onboarding_completed: true`)

### 3.3 Implementation

- New file: `gui/onboarding.py` — `OnboardingWidget` using `QStackedWidget` with custom animated transitions (override `setCurrentIndex` to animate position via `QPropertyAnimation`)
- Glass-styled cards matching the refined glass aesthetic
- `MainWindow` checks `onboarding_completed` on startup — shows onboarding or main app accordingly

---

## 4. Main App — Clean Tabs

### 4.1 Layout

Segmented tab control at the top of the window, three tabs:

#### Dashboard Tab
- **Status banner** — shows current state (Idle / Running / Paused) with colored indicator
  - Running: green, shows "Farming — Attack #N" and elapsed time
  - Paused: yellow, shows "Paused"
  - Idle: gray, shows "Ready to start"
- **Control buttons** — Start (green), Pause/Resume (yellow), Stop (red)
- **Resource cards** — Gold count, Elixir count, Attack count as stat cards
- **Mini activity feed** — last ~5 log lines showing recent actions

#### Settings Tab
Consolidated from old Connection, Discord, and Resources panels:

- **Connection section**
  - ADB device address input + Connect/Disconnect button
  - Connection status indicator
  - Resolution display (read-only, auto-detected on connection)

- **Farm Settings section**
  - Min loot to attack (single threshold, applies to both gold and elixir — matches existing `min_loot_to_attack` setting)
  - Farm target gold
  - Farm target elixir
  - Gold storage full threshold
  - Elixir storage full threshold

- **Discord section**
  - Webhook URL input
  - Test button
  - Enable/disable toggle (new setting: `discord_enabled`, default `true`. `bot/notify.py` checks this before sending webhooks.)

#### Log Tab
- Full scrollable log viewer (monospace font)
- Auto-scroll to bottom
- Clear button
- 5000-line buffer (unchanged)

### 4.2 Visual Style — Refined Glass

- **Background**: dark gradient `rgba(25,25,45)` to `rgba(18,18,38)` — no heavy animated gradients
- **Cards/panels**: `background: rgba(255,255,255,0.06)`, `border: 1px solid rgba(255,255,255,0.1)`, `border-radius: 10px`
- **Tab bar**: segmented control style with subtle background, active tab slightly lighter
- **Text**: primary at `rgba(255,255,255,0.9)`, secondary at `rgba(255,255,255,0.45)`
- **Accent colors**:
  - Gold: `#fbbf24`
  - Elixir: `#c084fc`
  - Active/Running: `#22c55e`
  - Warning/Pause: `#eab308`
  - Error/Stop: `#ef4444`
  - Interactive/Links: `#3b82f6`
- **Font**: system font (SF Pro on macOS), monospace for log
- **No** specular highlights, convex glass effects, or backdrop blur computations — simplified from current Liquid Glass

---

## 5. Files Changed Summary

### New Files
- `gui/onboarding.py` — onboarding card carousel widget

### Deleted Files
- `bot/walls.py`
- `bot/buildings.py`
- `gui/panels/army_panel.py`
- `templates/buttons/upgrade_wall.png`
- `templates/buttons/upgrade_wall_elixir.png`
- `templates/buttons/upgrade_more.png`
- `templates/walls/` (entire directory)

### Modified Files
- `gui/main_window.py` — remove Army tab, add onboarding gate
- `gui/theme.py` — replace Liquid Glass with Refined Glass stylesheet
- `gui/panels/resource_panel.py` — remove wall slider, restructure as farm settings
- `gui/panels/control_panel.py` — full rewrite as Dashboard tab with stat cards (no longer inherits from GlassToolbar)
- `gui/panels/connection_panel.py` — merge into Settings tab, auto-detect resolution on connect
- `gui/panels/discord_panel.py` — merge into Settings tab, add enable/disable toggle
- `gui/panels/log_panel.py` — minimal changes, style update
- `gui/glass.py` — simplify or remove heavy glass rendering (no more backdrop blur, specular highlights)
- `bot/main.py` — remove wall imports/logic, simplify to always-attack behavior
- `bot/vision.py` — remove `detect_walls()` and wall-related constants
- `bot/settings.py` — remove wall/troop settings, add `onboarding_completed` and `discord_enabled`
- `bot/config.py` — remove `wall_scales` from `_TUPLE_LIST_KEYS`
- `bot/metrics.py` — remove `record_wall_upgrade()` dead code
- `bot/notify.py` — check `discord_enabled` setting before sending webhooks
- `tests/test.py` — remove wall-related tests and imports
- `tests/test_offline.py` — remove wall-related tests and imports

### Unchanged
- `bot/screen.py` — resolution detection (already works)
- `bot/battle.py` — already implements "deploy all" (no changes needed)
- `bot/state_machine.py` — unchanged
- `bot/resources.py` — unchanged
- `app.py` — unchanged (theme change flows through `gui/theme.py`)
- `bot/updater.py` — unchanged

---

## 6. Pre-Release Cleanup

- Change `discord_webhook_url` default in `bot/settings.py` from hardcoded URL to empty string `""`
- Check `gui/panels/__init__.py` for explicit imports of deleted panels

---

## 7. Migration

- Existing `~/.cocbot/settings.json` files will have stale keys (wall/troop settings). The settings manager merges with defaults; stale keys persist harmlessly. No migration code needed for v1.
- `onboarding_completed` defaults to `false`, so existing users will see the onboarding on first launch after update. This is acceptable since it also serves as a connection verification step.
