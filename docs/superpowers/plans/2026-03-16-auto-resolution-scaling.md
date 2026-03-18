# Auto Resolution Scaling Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make all pixel coordinates automatically scale to the detected emulator resolution so the bot works on any screen size, not just 2560x1440.

**Architecture:** Add a scaling layer in `bot/config.py` that intercepts coordinate lookups and multiplies them by `(actual_resolution / base_resolution)`. The base resolution (2560x1440) stays in defaults. Resolution is detected once at startup via `bot/screen._detect_resolution()` (already implemented). Hardcoded pixel values in `bot/vision.py` and `bot/buildings.py` are converted to use config-based scaled values.

**Tech Stack:** Python, OpenCV, existing bot infrastructure.

---

## Chunk 1: Core Scaling Infrastructure

### Task 1: Add resolution scaling to bot/config.py

**Files:**
- Modify: `bot/config.py`
- Modify: `bot/settings.py` (add base resolution constants and scaled-keys registry)

- [ ] **Step 1: Add base resolution constants and scaling key sets to settings.py**

Add at the top of `bot/settings.py`, after the imports:

```python
# Base resolution all pixel coordinates are authored for
BASE_WIDTH = 2560
BASE_HEIGHT = 1440

# Settings keys containing pixel coordinates that must be scaled
# Keys with (x, y, x, y) or (x, y) tuples — scale x by width ratio, y by height ratio
_COORDINATE_KEYS = {
    "gold_region", "elixir_region", "game_area", "empty_tap",
    "enemy_loot_x_range",  # x-only pair
    "enemy_loot_y_range",  # y-only pair
}

# Keys with single pixel values that scale by width ratio
_PIXEL_X_KEYS = {
    "fallback_troop_x_start", "fallback_troop_x_spacing",
    "troop_bar_x_start", "troop_bar_x_end",
    "deploy_swipe_x1", "deploy_swipe_x2",
    "wall_dedup_dist", "wall_sort_row_height",
}

# Keys with single pixel values that scale by height ratio
_PIXEL_Y_KEYS = {
    "enemy_loot_strip_height", "enemy_loot_y_step", "enemy_loot_y_dedup",
    "deploy_swipe_y1", "deploy_swipe_y2",
}

# Keys with pixel area values that scale by (width_ratio * height_ratio)
_PIXEL_AREA_KEYS = {
    "troop_slot_min_area", "troop_slot_max_area",
}
```

- [ ] **Step 2: Add scaling logic to bot/config.py**

Replace the entire `bot/config.py` with:

```python
"""Config shim — delegates all attribute access to Settings singleton.
Automatically scales pixel coordinates to the detected screen resolution."""

from bot.settings import (
    Settings, BASE_WIDTH, BASE_HEIGHT,
    _COORDINATE_KEYS, _PIXEL_X_KEYS, _PIXEL_Y_KEYS, _PIXEL_AREA_KEYS,
)

# Keys whose values must be converted from lists back to tuples
_TUPLE_KEYS = {
    "gold_region", "elixir_region", "game_area", "empty_tap",
    "enemy_loot_x_range", "enemy_loot_y_range",
}

# Keys whose values are lists that should become tuples
_TUPLE_LIST_KEYS = {
    "wall_scales", "enemy_loot_scales",
}

# Dict key whose values (lists) should be converted to tuples
_DICT_TUPLE_VALUE_KEYS = {
    "button_rois",
}


def _scale_ratios():
    """Return (width_ratio, height_ratio) based on current screen vs base."""
    settings = Settings()
    sw = settings.get("screen_width", BASE_WIDTH)
    sh = settings.get("screen_height", BASE_HEIGHT)
    return sw / BASE_WIDTH, sh / BASE_HEIGHT


def _scale_coordinate_list(value, rx, ry):
    """Scale a coordinate list [x, y, ...] alternating x/y values."""
    scaled = []
    for i, v in enumerate(value):
        if i % 2 == 0:
            scaled.append(int(v * rx))
        else:
            scaled.append(int(v * ry))
    return scaled


def _scale_button_rois(rois, rx, ry):
    """Scale all button ROI dicts: {name: [x1, y1, x2, y2]}."""
    return {
        k: tuple(int(v * rx) if i % 2 == 0 else int(v * ry) for i, v in enumerate(vals))
        for k, vals in rois.items()
    }


def __getattr__(name):
    key = name.lower()
    settings = Settings()
    value = settings.get(key)
    if value is None:
        raise AttributeError(f"module 'config' has no attribute {name!r}")

    rx, ry = _scale_ratios()
    no_scale = (rx == 1.0 and ry == 1.0)

    # Convert BUTTON_ROIS dict values and scale coordinates
    if key in _DICT_TUPLE_VALUE_KEYS:
        if no_scale:
            return {k: tuple(v) for k, v in value.items()}
        return _scale_button_rois(value, rx, ry)

    # Convert and scale coordinate regions [x, y, x, y] or [x, y]
    if key in _COORDINATE_KEYS:
        if no_scale:
            return tuple(value)
        # Special: x-only and y-only range pairs
        if key == "enemy_loot_x_range":
            return tuple(int(v * rx) for v in value)
        if key == "enemy_loot_y_range":
            return tuple(int(v * ry) for v in value)
        return tuple(_scale_coordinate_list(value, rx, ry))

    # Scale single-value pixel keys
    if key in _PIXEL_X_KEYS:
        if no_scale:
            return value
        return int(value * rx)

    if key in _PIXEL_Y_KEYS:
        if no_scale:
            return value
        return int(value * ry)

    if key in _PIXEL_AREA_KEYS:
        if no_scale:
            return value
        return int(value * rx * ry)

    # Non-pixel tuple keys
    if key in _TUPLE_KEYS:
        return tuple(value)

    if key in _TUPLE_LIST_KEYS:
        return tuple(value)

    return value
```

- [ ] **Step 3: Verify imports still work**

Run: `.venv/bin/python -c "from bot.config import BUTTON_ROIS, GOLD_REGION, SCREEN_WIDTH; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add bot/config.py bot/settings.py
git commit -m "feat: add auto-scaling for pixel coordinates based on screen resolution"
```

---

### Task 2: Update resolution detection to store detected values

**Files:**
- Modify: `bot/screen.py`

- [ ] **Step 1: Update check_adb_connection to save detected resolution**

In `check_adb_connection()`, after calling `_detect_resolution()`, save the detected resolution to Settings so the config scaling picks it up:

```python
    w, h = _detect_resolution()
    if w and h:
        settings = Settings()
        settings.set("screen_width", w)
        settings.set("screen_height", h)
        if (w, h) == (SCREEN_WIDTH, SCREEN_HEIGHT) or (h, w) == (SCREEN_WIDTH, SCREEN_HEIGHT):
            logger.info("Screen resolution verified: %dx%d", w, h)
        else:
            logger.info("Screen resolution detected: %dx%d (base: %dx%d, scaling enabled)",
                         w, h, SCREEN_WIDTH, SCREEN_HEIGHT)
    else:
        logger.warning("Could not detect screen resolution, using defaults")
```

Note: Import `Settings` from `bot.settings` at the top of screen.py.

- [ ] **Step 2: Commit**

```bash
git add bot/screen.py
git commit -m "feat: auto-save detected resolution to settings for coordinate scaling"
```

---

### Task 3: Fix hardcoded pixel values in bot/vision.py

**Files:**
- Modify: `bot/vision.py`

- [ ] **Step 1: Replace hardcoded wall detection constants**

In `detect_walls()`, the values `100`, `60`, and `80 < area < 1000` are hardcoded for 2560x1440. Replace them with scaled values using config imports.

Add to the existing config imports at the top:
```python
from bot.config import SCREEN_WIDTH, SCREEN_HEIGHT
```

In `detect_walls()`, replace the hardcoded values:

```python
    # Scale pixel thresholds to current resolution
    from bot.settings import BASE_WIDTH, BASE_HEIGHT
    scale = (SCREEN_WIDTH * SCREEN_HEIGHT) / (BASE_WIDTH * BASE_HEIGHT)
    min_wall_area = int(80 * scale)
    max_wall_area = int(1000 * scale)
    neighbor_dist = int(100 * (SCREEN_WIDTH / BASE_WIDTH))
    strict_dist = int(60 * (SCREEN_WIDTH / BASE_WIDTH))
```

Then use `min_wall_area`, `max_wall_area`, `neighbor_dist`, `strict_dist` in place of the literals.

- [ ] **Step 2: Commit**

```bash
git add bot/vision.py
git commit -m "fix: scale hardcoded wall detection thresholds to screen resolution"
```

---

### Task 4: Fix hardcoded pixel values in bot/buildings.py

**Files:**
- Modify: `bot/buildings.py`

- [ ] **Step 1: Replace hardcoded dialog_region crop**

Find the line:
```python
dialog_region = img2[600:1400, :]
```

Replace with scaled values:
```python
from bot.config import SCREEN_HEIGHT
from bot.settings import BASE_HEIGHT
sy = SCREEN_HEIGHT / BASE_HEIGHT
dialog_region = img2[int(600 * sy):int(1400 * sy), :]
```

- [ ] **Step 2: Commit**

```bash
git add bot/buildings.py
git commit -m "fix: scale hardcoded dialog region crop to screen resolution"
```

---

### Task 5: Smoke test

- [ ] **Step 1: Run the app locally and verify no crashes**

Run: `.venv/bin/python app.py`
- Click "Detect Resolution" — should show 1920x1080 (green)
- Start bot in farm mode — should not crash with OpenCV assertion errors

- [ ] **Step 2: Verify scaling math is correct**

Run:
```python
.venv/bin/python -c "
from bot.settings import Settings
s = Settings()
s.set('screen_width', 1920)
s.set('screen_height', 1080)
from bot.config import BUTTON_ROIS, GOLD_REGION, GAME_AREA
print('BUTTON_ROIS:', BUTTON_ROIS)
print('GOLD_REGION:', GOLD_REGION)
print('GAME_AREA:', GAME_AREA)
"
```

Expected output (scaled from 2560x1440 by 0.75x0.75):
- `attack_button` ROI: (0, 787, 375, 1080) approximately
- `GOLD_REGION`: (1575, 41, 1875, 78) approximately
- `GAME_AREA`: (90, 187, 1800, 937) approximately

- [ ] **Step 3: Final commit**

```bash
git commit -m "test: verify auto-scaling works for 1920x1080"
```
