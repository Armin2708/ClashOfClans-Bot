# V1 Release Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Strip walls/troops, add onboarding wizard, and redesign the UI for a focused v1 farming bot release.

**Architecture:** Remove wall/troop code paths from bot backend and GUI, create a new onboarding carousel widget gating first launch, consolidate the remaining panels into a 3-tab layout (Dashboard/Settings/Log) with a refined glass aesthetic.

**Tech Stack:** Python 3.8+, PySide6 (Qt 6), OpenCV, ADB

---

## Task 1: Remove Wall Upgrade System (Backend)

**Files:**
- Delete: `bot/walls.py`
- Delete: `bot/buildings.py`
- Modify: `bot/vision.py:26-29` (remove wall imports), `bot/vision.py:519-586` (remove `detect_walls()`)
- Modify: `bot/settings.py:27-28` (remove wall keys from `_PIXEL_X_KEYS`), `bot/settings.py:54,68,129-131` (remove wall defaults)
- Modify: `bot/config.py:10-11` (remove `wall_scales` from `_TUPLE_LIST_KEYS`)
- Modify: `bot/metrics.py:16,26-28,51` (remove `walls_upgraded` field and `record_wall_upgrade()`)
- Modify: `bot/main.py:34,74-77,265-286` (remove wall imports, `UPGRADE_STRATEGIES`, wall upgrade logic)
- Modify: `gui/bot_worker.py:70,167,282-309` (remove wall imports and normal-mode upgrade logic)

- [ ] **Step 1: Delete `bot/walls.py` and `bot/buildings.py`**

```bash
rm bot/walls.py bot/buildings.py
```

- [ ] **Step 2: Remove wall imports and `detect_walls()` from `bot/vision.py`**

Remove from line 28: `WALL_MATCH_THRESHOLD, WALL_SCALES, WALL_DEDUP_DIST, WALL_SORT_ROW_HEIGHT,`

The import block (lines 26-35) should become (remove `GAME_AREA` too — it's only used by `detect_walls()`):
```python
from bot.config import (
    TEMPLATE_THRESHOLD, SCREEN_DETECT_THRESHOLD,
    GOLD_REGION, ELIXIR_REGION,
    ENEMY_LOOT_X_RANGE, ENEMY_LOOT_Y_RANGE, ENEMY_LOOT_STRIP_HEIGHT,
    # ... keep remaining imports unchanged
)
```

Delete the entire `detect_walls()` function (lines 519-586) and its section header comment (lines 518-520).

- [ ] **Step 3: Remove wall settings from `bot/settings.py`**

Remove from `_PIXEL_X_KEYS` (line 27-28):
```python
    "wall_dedup_dist", "wall_sort_row_height",
```

Remove from `DEFAULTS`:
- Line 54: `"max_wall_upgrades": 3,`
- Line 68: `"wall_match_threshold": 0.8,`
- Lines 129-131 (NOT line 128 which is `game_area` — keep that):
```python
    "wall_scales": [0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.5],
    "wall_dedup_dist": 25,
    "wall_sort_row_height": 30,
```

Change `discord_webhook_url` default (line 137) from the hardcoded URL to:
```python
    "discord_webhook_url": "",
```

- [ ] **Step 4: Remove `wall_scales` from `bot/config.py`**

Change line 10-11 from:
```python
_TUPLE_LIST_KEYS = {
    "wall_scales", "enemy_loot_scales",
}
```
to:
```python
_TUPLE_LIST_KEYS = {
    "enemy_loot_scales",
}
```

- [ ] **Step 5: Remove wall metrics from `bot/metrics.py`**

Remove `self.walls_upgraded = 0` (line 16).
Remove `record_wall_upgrade()` method (lines 26-28).
Remove `walls={self.walls_upgraded}, ` from `get_summary()` (line 51).

- [ ] **Step 6: Remove wall logic from `bot/main.py`**

Remove line 34:
```python
from bot.buildings import GOLD_WALL, WallUpgradeStrategy
```

Remove lines 74-77:
```python
UPGRADE_STRATEGIES = [
    (GOLD_WALL, WallUpgradeStrategy()),
]
```

Replace lines 265-295 (the wall upgrade + conditional attack block) with:
```python
            # Step 2: Attack
            logger.info("Going to attack...")
            attacked = do_attack()
            if attacked:
                metrics.record_attack()
```

Also remove the now-unused imports: `GOLD_STORAGE_FULL`, `ELIXIR_STORAGE_FULL` from line 37 (only if no longer referenced — check `farm_to_max()` still uses them? No, `farm_to_max()` uses `FARM_TARGET_*` not storage full. But `main()` still uses them in the removed block. Remove them.)

Updated line 37 import:
```python
from bot.config import (
    LOOP_DELAY, APP_LAUNCH_WAIT, EMPTY_TAP,
    CIRCUIT_BREAKER_MAX_FAILURES, CIRCUIT_BREAKER_WINDOW, MAX_UNKNOWN_STATE_STREAK,
    FARM_TARGET_GOLD, FARM_TARGET_ELIXIR,
)
```

- [ ] **Step 7: Remove wall logic from `gui/bot_worker.py`**

Remove line 70:
```python
        from bot.buildings import GOLD_WALL, WallUpgradeStrategy
```

Remove line 167:
```python
        upgrade_strategies = [(GOLD_WALL, WallUpgradeStrategy())]
```

Update the config import block (lines 72-76) to remove `GOLD_STORAGE_FULL`, `ELIXIR_STORAGE_FULL`:
```python
        from bot.config import (
            APP_LAUNCH_WAIT, EMPTY_TAP,
            CIRCUIT_BREAKER_MAX_FAILURES, CIRCUIT_BREAKER_WINDOW,
            MAX_UNKNOWN_STATE_STREAK, FARM_TARGET_GOLD, FARM_TARGET_ELIXIR,
        )
```

Replace the normal mode block (lines 282-316) with simple attack logic:
```python
                else:
                    # Normal mode: just attack
                    self.status_changed.emit("Attacking...")
                    logger.info("Going to attack...")
                    attacked = do_attack()
                    if attacked:
                        metrics.record_attack()
```

- [ ] **Step 8: Delete wall template files**

```bash
rm templates/buttons/upgrade_wall.png templates/buttons/upgrade_wall_elixir.png templates/buttons/upgrade_more.png
rm -rf templates/walls/
```

- [ ] **Step 9: Verify bot still imports cleanly**

Run:
```bash
cd /Users/arminrad/Desktop/ClashOfClans-Bot && python -c "from bot.main import main; from bot.vision import find_button; print('OK')"
```
Expected: `OK` with no import errors.

- [ ] **Step 10: Commit**

```bash
git add -A && git commit -m "feat(v1): remove wall upgrade system entirely"
```

---

## Task 2: Remove Troop Composition System

**Files:**
- Delete: `gui/panels/army_panel.py`
- Modify: `bot/settings.py:146` (remove `army_composition`)
- Modify: `gui/main_window.py:14,67` (remove Army tab)

- [ ] **Step 1: Delete `gui/panels/army_panel.py`**

```bash
rm gui/panels/army_panel.py
```

- [ ] **Step 2: Remove `army_composition` from `bot/settings.py`**

Remove line 146:
```python
    "army_composition": [],
```

- [ ] **Step 3: Remove Army tab from `gui/main_window.py`**

Remove line 14:
```python
from gui.panels.army_panel import ArmyPanel
```

Remove line 67:
```python
        self.tabs.addTab(ArmyPanel(), "Army")
```

- [ ] **Step 4: Verify GUI launches**

Run:
```bash
cd /Users/arminrad/Desktop/ClashOfClans-Bot && python -c "from gui.main_window import MainWindow; print('OK')"
```
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat(v1): remove troop composition system"
```

---

## Task 3: Update Tests

**Files:**
- Modify: `tests/test.py`
- Modify: `tests/test_offline.py`
- Modify: `tests/test_all.py`

- [ ] **Step 1: Read test files to identify wall/troop references**

Read `tests/test.py`, `tests/test_offline.py`, and `tests/test_all.py`. Remove:
- Any `from bot.walls import ...` or `from bot.buildings import ...`
- Any `from bot.vision import detect_walls`
- Any test functions/methods that test wall detection or wall upgrading
- Any references to `army_composition`

For `tests/test_all.py` specifically:
- Remove the entire "C. BUILDING ABSTRACTION TESTS" section (functions `test_building_dataclass`, `test_building_templates`, `test_wall_strategy_should_upgrade`, `test_upgrade_strategy_abc`)
- Remove `test_wall_detection` from vision tests section (G)
- Remove `test_main_loop_stops_on_upgrade_fail` from flow tests section (H)
- Remove `test_metrics_record_wall` from metrics tests section (B)
- Update `test_metrics_init` to not check `walls_upgraded`
- Update `test_metrics_summary` to not check `walls=` in summary
- Update `test_metrics_thread_safety` to not call `record_wall_upgrade()`
- Update `test_notify_summary` to not call `record_wall_upgrade()`
- Remove `"buildings"` from the GROUPS dict
- Remove wall test functions from `"vision"` and `"flow"` groups
- Remove wall metric test from `"metrics"` group

- [ ] **Step 2: Run remaining tests**

```bash
cd /Users/arminrad/Desktop/ClashOfClans-Bot && python -m pytest tests/ -v 2>&1 | head -50
```

Fix any remaining import errors.

- [ ] **Step 3: Commit**

```bash
git add -A && git commit -m "test: remove wall and troop tests"
```

---

## Task 4: Add Settings for Onboarding and Discord Toggle

**Files:**
- Modify: `bot/settings.py` (add `onboarding_completed`, `discord_enabled`)
- Modify: `bot/notify.py` (check `discord_enabled`)

- [ ] **Step 1: Add new settings to `bot/settings.py`**

Add to `DEFAULTS` dict (after `"device_address": ""`):
```python
    "onboarding_completed": False,
    "discord_enabled": True,
```

- [ ] **Step 2: Update `bot/notify.py` to check `discord_enabled`**

Update the `notify()` function to check the setting:
```python
def notify(message, max_retries=2):
    """Send a message to Discord via webhook with retry logic."""
    from bot.settings import Settings
    settings = Settings()
    if not settings.get("discord_enabled", True):
        return False
    url = settings.get("discord_webhook_url", "")
    if not url:
        return False
    for attempt in range(max_retries):
        try:
            data = json.dumps({"content": message}).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "COC-Bot/1.0",
                },
            )
            urllib.request.urlopen(req, timeout=10)
            logger.info("Sent: %s", message)
            return True
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning("Failed to send (attempt %d/%d): %s", attempt + 1, max_retries, e)
                time.sleep(2)
            else:
                logger.error("Failed to send after %d attempts: %s", max_retries, e)
    return False
```

Key changes: reads URL from Settings instead of config (avoids crash on empty URL), checks `discord_enabled`.

**Keep `notify_summary()` unchanged** — it calls `notify()` which now handles the enabled check internally. Also keep `import bot.config as config` removed since `notify()` now reads the URL from Settings directly.

- [ ] **Step 3: Verify import**

```bash
cd /Users/arminrad/Desktop/ClashOfClans-Bot && python -c "from bot.notify import notify; print('OK')"
```

- [ ] **Step 4: Commit**

```bash
git add bot/settings.py bot/notify.py && git commit -m "feat(v1): add onboarding_completed and discord_enabled settings"
```

---

## ⚠️ Task Ordering Note

**Tasks 6-8 must be executed in this order: 7 → 8 → 6.**
Task 6 (main window rewrite) imports `SettingsPanel` (created in Task 7) and `OnboardingWidget` (created in Task 8). Execute Task 7 Step 1 first (create settings_panel.py), then Task 8 (create onboarding.py), then Task 6 (rewrite main_window.py), then Task 7 Steps 2-4 (delete old panels).

---

## Task 5: Redesign Theme — Refined Glass

**Files:**
- Rewrite: `gui/theme.py`
- Simplify: `gui/glass.py`

- [ ] **Step 1: Rewrite `gui/theme.py` with Refined Glass tokens and stylesheet**

Replace the entire file with the new refined glass design:

```python
"""Refined Glass theme — clean dark translucent aesthetic.

Simplified from the original Liquid Glass: no heavy gradients, no backdrop
blur, no specular highlights. Dark background with subtle glass cards.
"""

from PySide6.QtWidgets import QApplication

# ── Design tokens ────────────────────────────────────────────────────
_T = {
    # Glass material
    "glass":           "rgba(255, 255, 255, 0.06)",
    "glass_hover":     "rgba(255, 255, 255, 0.10)",
    "glass_pressed":   "rgba(255, 255, 255, 0.14)",
    "glass_deep":      "rgba(255, 255, 255, 0.04)",
    "glass_input":     "rgba(255, 255, 255, 0.06)",

    # Borders
    "border":          "rgba(255, 255, 255, 0.10)",
    "border_subtle":   "rgba(255, 255, 255, 0.06)",
    "border_bright":   "rgba(255, 255, 255, 0.18)",
    "border_focus":    "rgba(59, 130, 246, 0.50)",

    # Text
    "text":            "rgba(255, 255, 255, 0.90)",
    "text2":           "rgba(255, 255, 255, 0.45)",
    "text3":           "rgba(255, 255, 255, 0.25)",

    # Accent colors
    "accent":          "#3b82f6",
    "accent_light":    "rgba(59, 130, 246, 0.15)",
    "success":         "#22c55e",
    "success_light":   "rgba(34, 197, 94, 0.12)",
    "warning":         "#eab308",
    "warning_light":   "rgba(234, 179, 8, 0.12)",
    "danger":          "#ef4444",
    "danger_light":    "rgba(239, 68, 68, 0.12)",

    # Game colors
    "gold":            "#fbbf24",
    "elixir":          "#c084fc",

    # Radii
    "r":               "10px",
    "r_sm":            "8px",
    "r_lg":            "14px",

    # Fonts
    "font":            "-apple-system, 'SF Pro Display', 'Helvetica Neue', sans-serif",
    "mono":            "'SF Mono', Menlo, Consolas, monospace",
}

# ── Stylesheet ───────────────────────────────────────────────────────
_CSS = """

/* ═══════════════════════ GLOBAL ═══════════════════════ */
QMainWindow {{
    background: transparent;
}}

QWidget {{
    color: {text};
    font-family: {font};
    font-size: 13px;
    background: transparent;
}}

QWidget#_central {{
    background: transparent;
}}

/* ═══════════════════════ TAB WIDGET ═══════════════════════ */
QTabWidget {{
    background: transparent;
}}

QTabWidget::pane {{
    background: {glass};
    border: 1px solid {border};
    border-radius: {r};
    top: -1px;
}}

QTabBar {{
    background: transparent;
    qproperty-drawBase: 0;
}}

QTabBar::tab {{
    background: {glass_deep};
    color: {text2};
    border: 1px solid {border_subtle};
    border-bottom: none;
    border-top-left-radius: {r_sm};
    border-top-right-radius: {r_sm};
    padding: 8px 24px;
    margin-right: 2px;
    font-weight: 500;
    min-width: 70px;
}}

QTabBar::tab:hover {{
    background: {glass_hover};
    color: {text};
    border-color: {border};
}}

QTabBar::tab:selected {{
    background: {glass_hover};
    color: white;
    border: 1px solid {border_bright};
    border-bottom: none;
    font-weight: 600;
}}

/* ═══════════════════════ PUSH BUTTON ═══════════════════════ */
QPushButton {{
    background: {glass};
    color: {text};
    border: 1px solid {border};
    border-radius: {r_sm};
    padding: 6px 20px;
    font-weight: 500;
    min-height: 28px;
}}

QPushButton:hover {{
    background: {glass_hover};
    border-color: {border_bright};
}}

QPushButton:pressed {{
    background: {glass_pressed};
}}

QPushButton:disabled {{
    color: {text3};
    background: rgba(255, 255, 255, 0.02);
    border-color: rgba(255, 255, 255, 0.04);
}}

QPushButton[class="accent"] {{
    background: {accent_light};
    border: 1px solid rgba(59, 130, 246, 0.30);
    color: {accent};
    font-weight: 600;
}}

QPushButton[class="accent"]:hover {{
    background: rgba(59, 130, 246, 0.22);
    border-color: rgba(59, 130, 246, 0.45);
}}

QPushButton[class="success"] {{
    background: {success_light};
    border: 1px solid rgba(34, 197, 94, 0.25);
    color: {success};
    font-weight: 600;
}}

QPushButton[class="success"]:hover {{
    background: rgba(34, 197, 94, 0.20);
}}

QPushButton[class="warning"] {{
    background: {warning_light};
    border: 1px solid rgba(234, 179, 8, 0.25);
    color: {warning};
    font-weight: 600;
}}

QPushButton[class="danger"] {{
    background: {danger_light};
    border: 1px solid rgba(239, 68, 68, 0.25);
    color: {danger};
    font-weight: 600;
}}

QPushButton[class="danger"]:hover {{
    background: rgba(239, 68, 68, 0.20);
}}

/* ═══════════════════════ LABEL ═══════════════════════ */
QLabel {{
    background: transparent;
    border: none;
    padding: 0;
}}

/* ═══════════════════════ GROUP BOX ═══════════════════════ */
QGroupBox {{
    background: {glass};
    border: 1px solid {border};
    border-radius: {r};
    margin-top: 16px;
    padding: 20px 16px 14px 16px;
    font-weight: 600;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 14px;
    color: {text2};
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}}

/* ═══════════════════════ TEXT EDIT / LOG ═══════════════════════ */
QPlainTextEdit {{
    background: rgba(0, 0, 0, 0.25);
    color: rgba(200, 220, 240, 0.85);
    border: 1px solid {border};
    border-radius: {r_sm};
    padding: 10px;
    font-family: {mono};
    font-size: 12px;
    selection-background-color: rgba(59, 130, 246, 0.30);
    selection-color: white;
}}

/* ═══════════════════════ LINE EDIT ═══════════════════════ */
QLineEdit {{
    background: {glass_input};
    color: {text};
    border: 1px solid {border};
    border-radius: {r_sm};
    padding: 6px 12px;
    min-height: 28px;
    selection-background-color: rgba(59, 130, 246, 0.30);
}}

QLineEdit:focus {{
    border-color: {border_focus};
    background: rgba(255, 255, 255, 0.08);
}}

QLineEdit:disabled {{
    color: {text3};
    background: rgba(255, 255, 255, 0.02);
}}

/* ═══════════════════════ SPIN BOX ═══════════════════════ */
QSpinBox, QDoubleSpinBox {{
    background: {glass_input};
    color: {text};
    border: 1px solid {border};
    border-radius: {r_sm};
    padding: 4px 10px;
    min-height: 28px;
}}

QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {border_focus};
    background: rgba(255, 255, 255, 0.08);
}}

QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    background: rgba(255, 255, 255, 0.04);
    border: none;
    border-radius: 4px;
    width: 20px;
    margin: 2px;
}}

QSpinBox::up-button:hover, QSpinBox::down-button:hover,
QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {{
    background: rgba(255, 255, 255, 0.10);
}}

/* ═══════════════════════ COMBO BOX ═══════════════════════ */
QComboBox {{
    background: {glass};
    color: {text};
    border: 1px solid {border};
    border-radius: {r_sm};
    padding: 5px 14px;
    min-height: 28px;
    min-width: 80px;
}}

QComboBox:hover {{
    background: {glass_hover};
    border-color: {border_bright};
}}

QComboBox::drop-down {{
    border: none;
    width: 26px;
    border-top-right-radius: {r_sm};
    border-bottom-right-radius: {r_sm};
}}

QComboBox::down-arrow {{
    image: none;
    border: none;
    width: 0; height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {text2};
    margin-right: 8px;
}}

QComboBox QAbstractItemView {{
    background: rgba(25, 25, 45, 0.95);
    color: {text};
    border: 1px solid {border_bright};
    border-radius: {r_sm};
    selection-background-color: rgba(59, 130, 246, 0.25);
    selection-color: white;
    outline: none;
    padding: 4px;
}}

QComboBox:disabled {{
    color: {text3};
    background: rgba(255, 255, 255, 0.02);
}}

/* ═══════════════════════ SCROLL ═══════════════════════ */
QScrollArea {{
    background: transparent;
    border: none;
}}

QScrollArea > QWidget > QWidget {{
    background: transparent;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 4px 1px;
    border: none;
}}

QScrollBar::handle:vertical {{
    background: rgba(255, 255, 255, 0.12);
    border-radius: 3px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background: rgba(255, 255, 255, 0.22);
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; border: none; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}

QScrollBar:horizontal {{
    background: transparent;
    height: 6px;
    margin: 1px 4px;
    border: none;
}}

QScrollBar::handle:horizontal {{
    background: rgba(255, 255, 255, 0.12);
    border-radius: 3px;
    min-width: 30px;
}}

QScrollBar::handle:horizontal:hover {{
    background: rgba(255, 255, 255, 0.22);
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; border: none; }}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: transparent; }}

/* ═══════════════════════ FRAME ═══════════════════════ */
QFrame {{
    background: transparent;
    border: none;
}}

QFrame[frameShape="4"] {{ background: {border}; max-height: 1px; }}
QFrame[frameShape="5"] {{ background: {border}; max-width: 1px; }}

/* ═══════════════════════ CHECK BOX ═══════════════════════ */
QCheckBox {{ background: transparent; spacing: 8px; }}
QCheckBox::indicator {{ width: 18px; height: 18px; border: 1.5px solid {border_bright}; border-radius: 5px; background: rgba(255,255,255,0.04); }}
QCheckBox::indicator:checked {{ background: {accent}; border-color: {accent}; }}
QCheckBox::indicator:hover {{ border-color: {border_focus}; }}

/* ═══════════════════════ TOOLTIP ═══════════════════════ */
QToolTip {{
    background: rgba(20, 20, 38, 0.95);
    color: {text};
    border: 1px solid {border_bright};
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 12px;
}}

""".format(**_T)


def apply_theme(app: QApplication) -> None:
    """Apply the Refined Glass stylesheet globally."""
    app.setStyleSheet(_CSS)
```

- [ ] **Step 2: Simplify `gui/glass.py`**

Replace the entire heavy rendering engine with a simple glass panel that uses CSS-only styling (no backdrop blur, no timer, no pixmap capture):

```python
"""Simplified glass widgets — CSS-styled containers without heavy rendering."""

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt


class GlassWidget(QWidget):
    """Simple translucent container widget."""

    def __init__(self, parent=None, **kw):
        super().__init__(parent)
        self.setAutoFillBackground(False)


class GlassPanel(GlassWidget):
    """Glass container panel."""
    pass


class GlassToolbar(GlassWidget):
    """Glass toolbar."""
    pass


class GlassButton(GlassWidget):
    """Glass button element."""
    pass
```

- [ ] **Step 3: Verify theme applies**

```bash
cd /Users/arminrad/Desktop/ClashOfClans-Bot && python -c "
from PySide6.QtWidgets import QApplication
import sys
app = QApplication(sys.argv)
from gui.theme import apply_theme
apply_theme(app)
print('Theme OK')
"
```

- [ ] **Step 4: Commit**

```bash
git add gui/theme.py gui/glass.py && git commit -m "feat(v1): refined glass theme, simplified glass widgets"
```

---

## Task 6: Redesign Main Window and Dashboard

**Files:**
- Rewrite: `gui/main_window.py`
- Rewrite: `gui/panels/control_panel.py`

- [ ] **Step 1: Rewrite `gui/main_window.py`**

Replace with clean 3-tab layout + onboarding gate:

```python
"""Main application window — Refined Glass with onboarding gate."""

import logging

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTabWidget, QStackedWidget,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QLinearGradient, QColor

from gui.log_handler import LogSignalEmitter, QtLogHandler
from gui.bot_worker import BotWorker, BotMode
from gui.panels.control_panel import DashboardPanel
from gui.panels.settings_panel import SettingsPanel
from gui.panels.log_panel import LogPanel
from gui.onboarding import OnboardingWidget
from bot.settings import Settings
from bot.updater import UpdateChecker


class _GradientBackground(QWidget):
    """Dark gradient background for the app."""

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        grad = QLinearGradient(0, 0, self.width(), self.height())
        grad.setColorAt(0.0, QColor(25, 25, 45))
        grad.setColorAt(0.5, QColor(20, 22, 40))
        grad.setColorAt(1.0, QColor(18, 18, 38))
        p.fillRect(self.rect(), grad)
        p.end()


class MainWindow(QMainWindow):
    """Main window with onboarding gate and 3-tab layout."""

    def __init__(self):
        super().__init__()
        self.worker = None
        self._settings = Settings()

        self.setWindowTitle("Clash of Clans Bot")
        self.setMinimumSize(900, 650)

        # Gradient background
        central = _GradientBackground()
        central.setObjectName("_central")
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Stack: onboarding or main app
        self._stack = QStackedWidget()
        layout.addWidget(self._stack)

        # Onboarding
        self._onboarding = OnboardingWidget()
        self._onboarding.completed.connect(self._on_onboarding_done)
        self._stack.addWidget(self._onboarding)

        # Main app container
        self._main_widget = QWidget()
        main_layout = QVBoxLayout(self._main_widget)
        main_layout.setContentsMargins(12, 10, 12, 12)
        main_layout.setSpacing(8)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        self.dashboard = DashboardPanel()
        self.tabs.addTab(self.dashboard, "Dashboard")

        self.settings_panel = SettingsPanel()
        self.tabs.addTab(self.settings_panel, "Settings")

        self.log_panel = LogPanel()
        self.tabs.addTab(self.log_panel, "Log")

        main_layout.addWidget(self.tabs, stretch=1)
        self._stack.addWidget(self._main_widget)

        # Show onboarding or main app
        if self._settings.get("onboarding_completed", False):
            self._stack.setCurrentWidget(self._main_widget)
        else:
            self._stack.setCurrentWidget(self._onboarding)

        # Log handler
        self._log_emitter = LogSignalEmitter()
        self._log_handler = QtLogHandler(self._log_emitter)
        self._log_handler.setLevel(logging.INFO)
        logging.getLogger("coc").addHandler(self._log_handler)
        self._log_emitter.log_message.connect(self._on_log_message)

        # Control signals
        self.dashboard.start_requested.connect(self._start_bot)
        self.dashboard.stop_requested.connect(self._stop_bot)
        self.dashboard.pause_requested.connect(self._pause_bot)
        self.dashboard.resume_requested.connect(self._resume_bot)

        # Update checker
        self._update_checker = UpdateChecker(self)
        self._update_checker.check()

    def _on_onboarding_done(self):
        self._settings.set("onboarding_completed", True)
        self._settings.save()
        self._stack.setCurrentWidget(self._main_widget)

    def _on_log_message(self, line):
        self.log_panel.append_log(line)
        self.dashboard.append_activity(line)

    def _start_bot(self, mode_name):
        mode = BotMode.FARM if mode_name == "farm" else BotMode.NORMAL
        self.worker = BotWorker(mode)
        self.worker.status_changed.connect(self.dashboard.update_status)
        self.worker.resources_updated.connect(self.dashboard.update_resources)
        self.worker.metrics_updated.connect(self.dashboard.update_metrics)
        self.worker.error_occurred.connect(self.dashboard.update_status)
        self.worker.bot_stopped.connect(self.dashboard.on_bot_stopped)
        self.worker.start()

    def _stop_bot(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(5000)
            self.worker = None

    def _pause_bot(self):
        if self.worker and self.worker.isRunning():
            self.worker.pause()

    def _resume_bot(self):
        if self.worker and self.worker.isRunning():
            self.worker.resume()

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(5000)
        event.accept()
```

- [ ] **Step 2: Rewrite `gui/panels/control_panel.py` as `DashboardPanel`**

Replace with a full dashboard tab containing status banner, controls, resource cards, and mini activity feed:

```python
"""Dashboard panel — bot controls, status, resources, and activity feed."""

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox,
    QLabel, QFrame, QPlainTextEdit,
)


class DashboardPanel(QWidget):
    """Main dashboard tab with controls and live stats."""

    start_requested = Signal(str)
    stop_requested = Signal()
    pause_requested = Signal()
    resume_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._paused = False
        self._attack_count = 0
        self._build_ui()
        self._connect_signals()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ── Status Banner ──
        self._status_frame = QFrame()
        self._status_frame.setStyleSheet(
            "QFrame { background: rgba(255,255,255,0.04); "
            "border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; }"
        )
        status_layout = QHBoxLayout(self._status_frame)
        status_layout.setContentsMargins(16, 12, 16, 12)

        self._status_dot = QLabel()
        self._status_dot.setFixedSize(10, 10)
        self._status_dot.setStyleSheet(
            "background: rgba(255,255,255,0.25); border-radius: 5px; border: none;"
        )
        status_layout.addWidget(self._status_dot)

        self._status_label = QLabel("Ready to start")
        self._status_label.setStyleSheet("font-size: 14px; font-weight: 600;")
        status_layout.addWidget(self._status_label)
        status_layout.addStretch()

        layout.addWidget(self._status_frame)

        # ── Controls Row ──
        ctrl_layout = QHBoxLayout()
        ctrl_layout.setSpacing(8)

        self.start_btn = QPushButton("Start")
        self.start_btn.setProperty("class", "success")
        self.start_btn.setFixedHeight(36)

        self.pause_btn = QPushButton("Pause")
        self.pause_btn.setProperty("class", "warning")
        self.pause_btn.setFixedHeight(36)
        self.pause_btn.setEnabled(False)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setProperty("class", "danger")
        self.stop_btn.setFixedHeight(36)
        self.stop_btn.setEnabled(False)

        mode_lbl = QLabel("Mode:")
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Normal", "Farm"])
        self.mode_combo.setFixedWidth(100)

        ctrl_layout.addWidget(self.start_btn)
        ctrl_layout.addWidget(self.pause_btn)
        ctrl_layout.addWidget(self.stop_btn)
        ctrl_layout.addWidget(mode_lbl)
        ctrl_layout.addWidget(self.mode_combo)
        ctrl_layout.addStretch()

        layout.addLayout(ctrl_layout)

        # ── Resource Cards ──
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(10)

        self._gold_card = self._make_card("GOLD", "0", "#fbbf24")
        self._elixir_card = self._make_card("ELIXIR", "0", "#c084fc")
        self._attacks_card = self._make_card("ATTACKS", "0", "#22c55e")

        cards_layout.addWidget(self._gold_card["frame"])
        cards_layout.addWidget(self._elixir_card["frame"])
        cards_layout.addWidget(self._attacks_card["frame"])

        layout.addLayout(cards_layout)

        # ── Mini Activity Feed ──
        feed_label = QLabel("Recent Activity")
        feed_label.setStyleSheet("color: rgba(255,255,255,0.45); font-size: 11px; "
                                 "font-weight: 600; letter-spacing: 0.5px;")
        layout.addWidget(feed_label)

        self._activity_feed = QPlainTextEdit()
        self._activity_feed.setReadOnly(True)
        self._activity_feed.setMaximumBlockCount(50)
        self._activity_feed.setFixedHeight(160)
        layout.addWidget(self._activity_feed)

        layout.addStretch()

    def _make_card(self, title, value, color):
        frame = QFrame()
        frame.setStyleSheet(
            "QFrame { background: rgba(255,255,255,0.04); "
            "border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; }"
        )
        card_layout = QVBoxLayout(frame)
        card_layout.setContentsMargins(16, 14, 16, 14)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            "color: rgba(255,255,255,0.40); font-size: 10px; "
            "font-weight: 600; letter-spacing: 1px; border: none;"
        )
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        value_lbl = QLabel(value)
        value_lbl.setStyleSheet(
            f"color: {color}; font-size: 24px; font-weight: 700; border: none;"
        )
        value_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card_layout.addWidget(title_lbl)
        card_layout.addWidget(value_lbl)

        return {"frame": frame, "value": value_lbl}

    def _connect_signals(self):
        self.start_btn.clicked.connect(self._on_start)
        self.stop_btn.clicked.connect(self._on_stop)
        self.pause_btn.clicked.connect(self._on_pause_toggle)

    def _on_start(self):
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.pause_btn.setEnabled(True)
        self.pause_btn.setText("Pause")
        self._paused = False
        self.mode_combo.setEnabled(False)
        self._set_status("Starting...", "#eab308")
        self.start_requested.emit(self.mode_combo.currentText().lower())

    def _on_stop(self):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setText("Pause")
        self._paused = False
        self.mode_combo.setEnabled(True)
        self._set_status("Stopped", "rgba(255,255,255,0.25)")
        self.stop_requested.emit()

    def _on_pause_toggle(self):
        if self._paused:
            self._paused = False
            self.pause_btn.setText("Pause")
            self._set_status("Resumed", "#22c55e")
            self.resume_requested.emit()
        else:
            self._paused = True
            self.pause_btn.setText("Resume")
            self._set_status("Paused", "#eab308")
            self.pause_requested.emit()

    def _set_status(self, text, dot_color):
        self._status_label.setText(text)
        self._status_dot.setStyleSheet(
            f"background: {dot_color}; border-radius: 5px; border: none;"
        )

    # ── Public API (called by MainWindow) ──

    def update_status(self, text):
        color = "#22c55e" if "running" in text.lower() or "attack" in text.lower() or "farm" in text.lower() else "#eab308"
        self._set_status(text, color)

    def update_resources(self, gold, elixir):
        self._gold_card["value"].setText(f"{gold:,}")
        self._elixir_card["value"].setText(f"{elixir:,}")

    def update_metrics(self, text):
        # Parse attack count from metrics string
        import re
        m = re.search(r"attacks=(\d+)", text)
        if m:
            self._attack_count = int(m.group(1))
            self._attacks_card["value"].setText(str(self._attack_count))

    def append_activity(self, line):
        self._activity_feed.appendPlainText(line)

    def on_bot_stopped(self, reason):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setText("Pause")
        self._paused = False
        self.mode_combo.setEnabled(True)
        self._set_status(f"Stopped — {reason}", "rgba(255,255,255,0.25)")
```

- [ ] **Step 3: Commit**

```bash
git add gui/main_window.py gui/panels/control_panel.py && git commit -m "feat(v1): redesign main window with dashboard and onboarding gate"
```

---

## Task 7: Create Settings Panel (Consolidated)

**Files:**
- Create: `gui/panels/settings_panel.py`
- Delete: `gui/panels/resource_panel.py`
- Delete: `gui/panels/connection_panel.py`
- Delete: `gui/panels/discord_panel.py`

- [ ] **Step 1: Create `gui/panels/settings_panel.py`**

Consolidates Connection, Farm Settings, and Discord into one scrollable panel:

```python
"""Settings panel — consolidated connection, farm, and discord settings."""

import subprocess
import re
import json
import urllib.request
import urllib.error

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QFormLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QSpinBox, QCheckBox, QScrollArea,
)
from PySide6.QtCore import Qt

from bot.settings import Settings, BASE_WIDTH, BASE_HEIGHT


class SettingsPanel(QWidget):
    """Consolidated settings: connection, farm thresholds, discord."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = Settings()
        self._build_ui()
        self._load_settings()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        outer.addWidget(scroll)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        scroll.setWidget(container)

        # ── Connection ──
        conn_group = QGroupBox("Connection")
        conn_form = QFormLayout()

        self._device_addr = QLineEdit()
        self._device_addr.setPlaceholderText("localhost:5555")
        conn_form.addRow("Device Address:", self._device_addr)

        btn_row = QHBoxLayout()
        self._connect_btn = QPushButton("Connect")
        self._connect_btn.setProperty("class", "accent")
        self._connect_btn.clicked.connect(self._on_connect)
        btn_row.addWidget(self._connect_btn)
        btn_row.addStretch()
        conn_form.addRow(btn_row)

        self._conn_status = QLabel("Not connected")
        self._conn_status.setStyleSheet("font-weight: 500;")
        conn_form.addRow("Status:", self._conn_status)

        self._resolution_label = QLabel("—")
        conn_form.addRow("Resolution:", self._resolution_label)

        conn_group.setLayout(conn_form)
        layout.addWidget(conn_group)

        # ── Farm Settings ──
        farm_group = QGroupBox("Farm Settings")
        farm_form = QFormLayout()

        farm_form.addRow(
            "Min Loot to Attack:",
            self._create_spinbox("min_loot_to_attack", 0, 20_000_000, 100_000),
        )
        farm_form.addRow(
            "Farm Target Gold:",
            self._create_spinbox("farm_target_gold", 0, 50_000_000, 1_000_000),
        )
        farm_form.addRow(
            "Farm Target Elixir:",
            self._create_spinbox("farm_target_elixir", 0, 50_000_000, 1_000_000),
        )
        farm_form.addRow(
            "Gold Storage Full:",
            self._create_spinbox("gold_storage_full", 0, 50_000_000, 1_000_000),
        )
        farm_form.addRow(
            "Elixir Storage Full:",
            self._create_spinbox("elixir_storage_full", 0, 50_000_000, 1_000_000),
        )

        farm_group.setLayout(farm_form)
        layout.addWidget(farm_group)

        # ── Discord ──
        discord_group = QGroupBox("Discord Notifications")
        discord_form = QFormLayout()

        self._discord_enabled = QCheckBox("Enable Discord notifications")
        self._discord_enabled.stateChanged.connect(
            lambda s: self._save("discord_enabled", s == Qt.CheckState.Checked.value)
        )
        discord_form.addRow(self._discord_enabled)

        self._webhook_url = QLineEdit()
        self._webhook_url.setPlaceholderText("https://discord.com/api/webhooks/...")
        self._webhook_url.textChanged.connect(
            lambda t: self._save("discord_webhook_url", t.strip())
        )
        discord_form.addRow("Webhook URL:", self._webhook_url)

        test_row = QHBoxLayout()
        self._test_btn = QPushButton("Test Webhook")
        self._test_btn.clicked.connect(self._on_test_webhook)
        test_row.addWidget(self._test_btn)

        self._discord_status = QLabel("")
        test_row.addWidget(self._discord_status)
        test_row.addStretch()
        discord_form.addRow(test_row)

        discord_group.setLayout(discord_form)
        layout.addWidget(discord_group)

        layout.addStretch()

    def _load_settings(self):
        self._device_addr.setText(self._settings.get("device_address", ""))
        self._discord_enabled.setChecked(self._settings.get("discord_enabled", True))
        self._webhook_url.setText(self._settings.get("discord_webhook_url", ""))

    def _create_spinbox(self, key, min_val, max_val, step):
        spinbox = QSpinBox()
        spinbox.setRange(min_val, max_val)
        spinbox.setSingleStep(step)
        spinbox.setValue(self._settings.get(key, 0))
        spinbox.valueChanged.connect(lambda v: self._save(key, v))
        return spinbox

    def _save(self, key, value):
        self._settings.set(key, value)
        self._settings.save()

    def _on_connect(self):
        addr = self._device_addr.text().strip()
        adb = self._settings.get("adb_path", "adb")

        self._settings.set("device_address", addr)
        self._settings.save()

        if not addr:
            self._conn_status.setText("No device address specified")
            self._conn_status.setStyleSheet("color: #ef4444; font-weight: 500;")
            return

        try:
            result = subprocess.run(
                [adb, "connect", addr],
                capture_output=True, text=True, timeout=10,
            )
            output = result.stdout.strip()
            if "connected" in output.lower():
                self._conn_status.setText(f"Connected to {addr}")
                self._conn_status.setStyleSheet("color: #22c55e; font-weight: 500;")
                # Auto-detect resolution
                self._detect_resolution(adb, addr)
            else:
                self._conn_status.setText(f"Failed: {output or result.stderr.strip()}")
                self._conn_status.setStyleSheet("color: #ef4444; font-weight: 500;")
        except FileNotFoundError:
            self._conn_status.setText(f"ADB not found at '{adb}'")
            self._conn_status.setStyleSheet("color: #ef4444; font-weight: 500;")
        except subprocess.TimeoutExpired:
            self._conn_status.setText("Connection timed out")
            self._conn_status.setStyleSheet("color: #ef4444; font-weight: 500;")

    def _detect_resolution(self, adb, addr):
        def _cmd(*args):
            cmd = [adb]
            if addr:
                cmd += ["-s", addr]
            cmd += list(args)
            return cmd

        w, h = None, None
        try:
            result = subprocess.run(
                _cmd("shell", "wm", "size"),
                capture_output=True, text=True, timeout=10,
            )
            match = re.search(r"(\d+)x(\d+)", result.stdout)
            if match:
                w, h = int(match.group(1)), int(match.group(2))

            if not w:
                result = subprocess.run(
                    _cmd("shell", "dumpsys", "display"),
                    capture_output=True, text=True, timeout=10,
                )
                match = re.search(r"real\s+(\d+)\s*x\s*(\d+)", result.stdout)
                if match:
                    w, h = int(match.group(1)), int(match.group(2))

            if w and h:
                self._settings.set("screen_width", w)
                self._settings.set("screen_height", h)
                self._settings.save()

                if w == BASE_WIDTH and h == BASE_HEIGHT:
                    self._resolution_label.setText(f"{w}x{h}")
                    self._resolution_label.setStyleSheet("color: #22c55e; font-weight: 500;")
                else:
                    self._resolution_label.setText(
                        f"{w}x{h} (expected {BASE_WIDTH}x{BASE_HEIGHT})"
                    )
                    self._resolution_label.setStyleSheet("color: #eab308; font-weight: 500;")
            else:
                self._resolution_label.setText("Could not detect")
                self._resolution_label.setStyleSheet("color: #ef4444; font-weight: 500;")
        except Exception:
            self._resolution_label.setText("Detection failed")
            self._resolution_label.setStyleSheet("color: #ef4444; font-weight: 500;")

    def _on_test_webhook(self):
        url = self._webhook_url.text().strip()
        if not url:
            self._discord_status.setText("No URL")
            self._discord_status.setStyleSheet("color: #ef4444; font-weight: 500;")
            return

        try:
            payload = json.dumps({"content": "CoC Bot: test message"}).encode()
            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json", "User-Agent": "COC-Bot/1.0"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status < 300:
                    self._discord_status.setText("Working!")
                    self._discord_status.setStyleSheet("color: #22c55e; font-weight: 500;")
                else:
                    self._discord_status.setText(f"HTTP {resp.status}")
                    self._discord_status.setStyleSheet("color: #ef4444; font-weight: 500;")
        except urllib.error.HTTPError as e:
            self._discord_status.setText(f"HTTP {e.code}")
            self._discord_status.setStyleSheet("color: #ef4444; font-weight: 500;")
        except Exception as e:
            self._discord_status.setText(f"Error: {e}")
            self._discord_status.setStyleSheet("color: #ef4444; font-weight: 500;")
```

- [ ] **Step 2: Delete old panels**

```bash
rm gui/panels/resource_panel.py gui/panels/connection_panel.py gui/panels/discord_panel.py
```

- [ ] **Step 3: Verify settings panel imports**

```bash
cd /Users/arminrad/Desktop/ClashOfClans-Bot && python -c "from gui.panels.settings_panel import SettingsPanel; print('OK')"
```

- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "feat(v1): consolidated settings panel, remove old panels"
```

---

## Task 8: Create Onboarding Carousel

**Files:**
- Create: `gui/onboarding.py`

- [ ] **Step 1: Create `gui/onboarding.py`**

Card carousel with 4 steps: Welcome → BlueStacks → Connect → Ready:

```python
"""First-launch onboarding — card carousel with slide animations."""

import subprocess
import re
import webbrowser

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QStackedWidget, QSizePolicy,
)
from PySide6.QtCore import (
    Signal, Qt, QPropertyAnimation, QEasingCurve, QPoint, QParallelAnimationGroup,
)
from PySide6.QtGui import QFont

from bot.settings import Settings, BASE_WIDTH, BASE_HEIGHT


class _DotIndicator(QWidget):
    """Dot progress indicator for carousel steps."""

    def __init__(self, count, parent=None):
        super().__init__(parent)
        self._count = count
        self._current = 0
        layout = QHBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(8)
        self._dots = []
        for i in range(count):
            dot = QLabel()
            dot.setFixedSize(8, 8)
            layout.addWidget(dot)
            self._dots.append(dot)
        self._update()

    def set_current(self, index):
        self._current = index
        self._update()

    def _update(self):
        for i, dot in enumerate(self._dots):
            if i == self._current:
                dot.setStyleSheet(
                    "background: #3b82f6; border-radius: 4px; border: none;"
                )
            else:
                dot.setStyleSheet(
                    "background: rgba(255,255,255,0.15); border-radius: 4px; border: none;"
                )


class _BaseCard(QWidget):
    """Base card for onboarding steps."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            "QWidget { background: rgba(255,255,255,0.06); "
            "border: 1px solid rgba(255,255,255,0.10); border-radius: 14px; }"
        )


class OnboardingWidget(QWidget):
    """Full-window onboarding carousel."""

    completed = Signal()

    BLUESTACKS_URL = "https://www.bluestacks.com/download"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = Settings()
        self._current = 0
        self._animating = False
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Card container (fixed size for animation)
        self._card_container = QWidget()
        self._card_container.setFixedSize(500, 420)
        self._card_container.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(self._card_container, alignment=Qt.AlignmentFlag.AlignCenter)

        # Create cards as children of card_container
        self._cards = [
            self._make_welcome_card(),
            self._make_bluestacks_card(),
            self._make_connect_card(),
            self._make_ready_card(),
        ]

        for card in self._cards:
            card.setParent(self._card_container)
            card.setGeometry(0, 0, 500, 420)
            card.hide()

        self._cards[0].show()

        # Dots
        self._dots = _DotIndicator(4)
        layout.addWidget(self._dots, alignment=Qt.AlignmentFlag.AlignCenter)

        # Navigation buttons
        nav = QHBoxLayout()
        self._back_btn = QPushButton("Back")
        self._back_btn.setFixedWidth(100)
        self._back_btn.clicked.connect(self._go_back)
        self._back_btn.setVisible(False)

        self._next_btn = QPushButton("Get Started")
        self._next_btn.setProperty("class", "accent")
        self._next_btn.setFixedWidth(200)
        self._next_btn.setFixedHeight(40)
        self._next_btn.clicked.connect(self._go_next)

        nav.addWidget(self._back_btn)
        nav.addStretch()
        nav.addWidget(self._next_btn)
        layout.addLayout(nav)

    def _make_welcome_card(self):
        card = _BaseCard()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(30, 40, 30, 30)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon = QLabel("\u2694\uFE0F")
        icon.setFont(QFont("", 48))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("border: none; background: transparent;")
        layout.addWidget(icon)

        title = QLabel("Welcome to CoC Bot")
        title.setStyleSheet(
            "font-size: 24px; font-weight: 700; color: rgba(255,255,255,0.92); "
            "border: none; background: transparent;"
        )
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        sub = QLabel(
            "Automated farming for Clash of Clans.\n"
            "Let's get you set up in a few steps."
        )
        sub.setStyleSheet(
            "font-size: 14px; color: rgba(255,255,255,0.50); "
            "border: none; background: transparent;"
        )
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setWordWrap(True)
        layout.addWidget(sub)
        layout.addStretch()

        return card

    def _make_bluestacks_card(self):
        card = _BaseCard()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(30, 30, 30, 30)

        title = QLabel("Install BlueStacks")
        title.setStyleSheet(
            "font-size: 22px; font-weight: 700; color: rgba(255,255,255,0.92); "
            "border: none; background: transparent;"
        )
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        body = QLabel(
            "CoC Bot works with BlueStacks emulator.\n"
            "Download and install it, then configure:\n\n"
            "1. Open BlueStacks Settings\n"
            "2. Go to Display tab\n"
            "3. Set resolution to 2560 x 1440\n"
            "4. Install Clash of Clans from Play Store"
        )
        body.setStyleSheet(
            "font-size: 13px; color: rgba(255,255,255,0.55); line-height: 1.6; "
            "border: none; background: transparent;"
        )
        body.setWordWrap(True)
        layout.addWidget(body)
        layout.addStretch()

        dl_btn = QPushButton("Download BlueStacks")
        dl_btn.setProperty("class", "accent")
        dl_btn.setFixedHeight(36)
        dl_btn.clicked.connect(lambda: webbrowser.open(self.BLUESTACKS_URL))
        layout.addWidget(dl_btn)

        return card

    def _make_connect_card(self):
        card = _BaseCard()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(30, 30, 30, 30)

        title = QLabel("Connect to BlueStacks")
        title.setStyleSheet(
            "font-size: 22px; font-weight: 700; color: rgba(255,255,255,0.92); "
            "border: none; background: transparent;"
        )
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        body = QLabel(
            "Enter the ADB address for your BlueStacks instance.\n"
            "The default is usually localhost:5555."
        )
        body.setStyleSheet(
            "font-size: 13px; color: rgba(255,255,255,0.55); "
            "border: none; background: transparent;"
        )
        body.setWordWrap(True)
        layout.addWidget(body)

        self._addr_input = QLineEdit()
        self._addr_input.setPlaceholderText("localhost:5555")
        self._addr_input.setText("localhost:5555")
        layout.addWidget(self._addr_input)

        test_btn = QPushButton("Test Connection")
        test_btn.setProperty("class", "accent")
        test_btn.setFixedHeight(36)
        test_btn.clicked.connect(self._test_connection)
        layout.addWidget(test_btn)

        self._connect_status = QLabel("")
        self._connect_status.setStyleSheet("border: none; background: transparent;")
        self._connect_status.setWordWrap(True)
        layout.addWidget(self._connect_status)

        layout.addStretch()
        return card

    def _make_ready_card(self):
        card = _BaseCard()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(30, 40, 30, 30)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon = QLabel("\u2705")
        icon.setFont(QFont("", 48))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("border: none; background: transparent;")
        layout.addWidget(icon)

        title = QLabel("You're All Set!")
        title.setStyleSheet(
            "font-size: 24px; font-weight: 700; color: rgba(255,255,255,0.92); "
            "border: none; background: transparent;"
        )
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        sub = QLabel(
            "CoC Bot is ready to farm.\n"
            "Head to the Dashboard and hit Start!"
        )
        sub.setStyleSheet(
            "font-size: 14px; color: rgba(255,255,255,0.50); "
            "border: none; background: transparent;"
        )
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setWordWrap(True)
        layout.addWidget(sub)
        layout.addStretch()

        return card

    def _test_connection(self):
        addr = self._addr_input.text().strip()
        adb = self._settings.get("adb_path", "adb")

        if not addr:
            self._connect_status.setText("Please enter an address.")
            self._connect_status.setStyleSheet(
                "color: #ef4444; font-weight: 500; border: none; background: transparent;"
            )
            return

        try:
            result = subprocess.run(
                [adb, "connect", addr],
                capture_output=True, text=True, timeout=10,
            )
            if "connected" not in result.stdout.lower():
                self._connect_status.setText(
                    "Could not connect. Make sure BlueStacks is running."
                )
                self._connect_status.setStyleSheet(
                    "color: #ef4444; font-weight: 500; border: none; background: transparent;"
                )
                return

            # Check resolution
            res = subprocess.run(
                [adb, "-s", addr, "shell", "wm", "size"],
                capture_output=True, text=True, timeout=10,
            )
            match = re.search(r"(\d+)x(\d+)", res.stdout)
            if match:
                w, h = int(match.group(1)), int(match.group(2))
                self._settings.set("device_address", addr)
                self._settings.set("screen_width", w)
                self._settings.set("screen_height", h)
                self._settings.save()

                if w == BASE_WIDTH and h == BASE_HEIGHT:
                    self._connect_status.setText(
                        f"Connected! Resolution: {w}x{h}"
                    )
                    self._connect_status.setStyleSheet(
                        "color: #22c55e; font-weight: 500; border: none; background: transparent;"
                    )
                    self._next_btn.setEnabled(True)
                else:
                    self._connect_status.setText(
                        f"Connected but resolution is {w}x{h}.\n"
                        f"Please set BlueStacks to {BASE_WIDTH}x{BASE_HEIGHT}."
                    )
                    self._connect_status.setStyleSheet(
                        "color: #eab308; font-weight: 500; border: none; background: transparent;"
                    )
                    self._next_btn.setEnabled(False)
            else:
                self._settings.set("device_address", addr)
                self._settings.save()
                self._connect_status.setText(
                    "Connected! (Could not verify resolution)"
                )
                self._connect_status.setStyleSheet(
                    "color: #eab308; font-weight: 500; border: none; background: transparent;"
                )

        except FileNotFoundError:
            self._connect_status.setText(f"ADB not found at '{adb}'")
            self._connect_status.setStyleSheet(
                "color: #ef4444; font-weight: 500; border: none; background: transparent;"
            )
        except subprocess.TimeoutExpired:
            self._connect_status.setText("Connection timed out.")
            self._connect_status.setStyleSheet(
                "color: #ef4444; font-weight: 500; border: none; background: transparent;"
            )

    def _go_next(self):
        if self._animating:
            return

        if self._current == 2:
            # On connect page, require successful connection
            status_text = self._connect_status.text()
            if not status_text.startswith("Connected!"):
                return

        if self._current >= 3:
            self.completed.emit()
            return

        self._animate_to(self._current + 1, direction=1)

    def _go_back(self):
        if self._animating or self._current <= 0:
            return
        self._animate_to(self._current - 1, direction=-1)

    def _animate_to(self, new_index, direction=1):
        self._animating = True
        w = self._card_container.width()

        old_card = self._cards[self._current]
        new_card = self._cards[new_index]

        # Position new card off-screen
        new_card.setGeometry(direction * w, 0, w, self._card_container.height())
        new_card.show()

        group = QParallelAnimationGroup(self)

        # Slide old card out
        anim_old = QPropertyAnimation(old_card, b"pos")
        anim_old.setDuration(300)
        anim_old.setStartValue(QPoint(0, 0))
        anim_old.setEndValue(QPoint(-direction * w, 0))
        anim_old.setEasingCurve(QEasingCurve.Type.OutCubic)
        group.addAnimation(anim_old)

        # Slide new card in
        anim_new = QPropertyAnimation(new_card, b"pos")
        anim_new.setDuration(300)
        anim_new.setStartValue(QPoint(direction * w, 0))
        anim_new.setEndValue(QPoint(0, 0))
        anim_new.setEasingCurve(QEasingCurve.Type.OutCubic)
        group.addAnimation(anim_new)

        def on_done():
            old_card.hide()
            self._current = new_index
            self._animating = False
            self._update_nav()

        group.finished.connect(on_done)
        group.start()

    def _update_nav(self):
        self._dots.set_current(self._current)
        self._back_btn.setVisible(self._current > 0)

        labels = ["Get Started", "I've Installed BlueStacks", "Continue", "Launch Bot"]
        self._next_btn.setText(labels[self._current])

        # Disable next on connect page until connection succeeds
        if self._current == 2:
            status_text = self._connect_status.text()
            self._next_btn.setEnabled(status_text.startswith("Connected!"))
        else:
            self._next_btn.setEnabled(True)
```

- [ ] **Step 2: Verify onboarding imports**

```bash
cd /Users/arminrad/Desktop/ClashOfClans-Bot && python -c "from gui.onboarding import OnboardingWidget; print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add gui/onboarding.py && git commit -m "feat(v1): onboarding card carousel with slide animations"
```

---

## Task 9: Integration Test — Full App Launch

**Files:** None (verification only)

- [ ] **Step 1: Verify full app can be imported and constructed**

```bash
cd /Users/arminrad/Desktop/ClashOfClans-Bot && python -c "
import sys
from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)
from gui.theme import apply_theme
apply_theme(app)
from gui.main_window import MainWindow
window = MainWindow()
print('Window created successfully')
print('Tabs:', window.tabs.count())
print('Tab 0:', window.tabs.tabText(0))
print('Tab 1:', window.tabs.tabText(1))
print('Tab 2:', window.tabs.tabText(2))
"
```

Expected:
```
Window created successfully
Tabs: 3
Tab 0: Dashboard
Tab 1: Settings
Tab 2: Log
```

- [ ] **Step 2: Run any remaining tests**

```bash
cd /Users/arminrad/Desktop/ClashOfClans-Bot && python -m pytest tests/ -v 2>&1 | tail -20
```

Fix any failures.

- [ ] **Step 3: Visual smoke test**

```bash
cd /Users/arminrad/Desktop/ClashOfClans-Bot && python app.py
```

Verify:
- Onboarding shows (if `onboarding_completed` is false)
- Cards slide with animation
- After completing onboarding, 3-tab layout appears
- Dashboard has Start/Pause/Stop buttons and resource cards
- Settings has Connection, Farm Settings, Discord sections
- Log tab has log viewer with clear button
- Theme looks correct (dark background, subtle glass borders)

- [ ] **Step 4: Final commit if any fixes were needed**

```bash
git add -A && git commit -m "fix(v1): integration fixes from smoke test"
```

---

## Task 10: Cleanup and Final Commit

- [ ] **Step 1: Check `gui/panels/__init__.py` for stale imports**

```bash
cat gui/panels/__init__.py
```

If it contains explicit imports of deleted panels (army_panel, resource_panel, connection_panel, discord_panel), remove them. Currently it's empty, so no changes expected.

- [ ] **Step 2: Verify no references to deleted files remain**

```bash
cd /Users/arminrad/Desktop/ClashOfClans-Bot && grep -r "army_panel\|walls\.\|buildings\.\|resource_panel\|connection_panel\|discord_panel" --include="*.py" -l
```

Should return no files (except this plan file if it's .py, which it's not).

- [ ] **Step 3: Verify no import errors across the codebase**

```bash
cd /Users/arminrad/Desktop/ClashOfClans-Bot && python -c "
import bot.main
import bot.battle
import bot.vision
import bot.screen
import bot.config
import bot.settings
import bot.metrics
import bot.notify
import bot.state_machine
import bot.resources
import gui.main_window
import gui.theme
import gui.glass
import gui.onboarding
import gui.panels.control_panel
import gui.panels.settings_panel
import gui.panels.log_panel
print('All imports OK')
"
```

- [ ] **Step 4: Check `.gitignore` includes `.superpowers/`**

```bash
grep -q "\.superpowers" .gitignore 2>/dev/null || echo ".superpowers/" >> .gitignore
```

- [ ] **Step 5: Commit cleanup**

```bash
git add .gitignore gui/panels/__init__.py && git commit -m "chore(v1): cleanup stale references and gitignore"
```
