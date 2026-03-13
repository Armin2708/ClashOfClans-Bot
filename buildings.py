"""
Building abstraction and upgrade strategy system.

Defines a Building dataclass and an UpgradeStrategy ABC so that adding
new building types (cannons, archer towers, etc.) only requires defining
a new Building + Strategy — no changes to main.py needed.
"""

import time
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional, Tuple, List

from screen import screenshot, tap
from vision import find_button, detect_walls, read_resources_from_village
from utils import find_template, save_debug, load_template
from config import (
    GOLD_STORAGE_FULL, ELIXIR_STORAGE_FULL, EMPTY_TAP, MAX_WALL_UPGRADES,
)

logger = logging.getLogger("coc.buildings")


# ─── BUILDING DATACLASS ──────────────────────────────────────

@dataclass
class Building:
    """Describes a building type the bot can detect and upgrade."""
    name: str
    detect_method: Callable  # (img) -> list of (x, y) positions
    upgrade_templates: Dict[str, Optional[object]]  # resource_name -> loaded template
    panel_button_template: Optional[object]  # template to confirm we opened the right panel


# ─── BUILDING DEFINITIONS ────────────────────────────────────

GOLD_WALL = Building(
    name="wall",
    detect_method=detect_walls,
    upgrade_templates={
        "gold": load_template("templates/buttons/upgrade_wall.png"),
        "elixir": load_template("templates/buttons/upgrade_wall_elixir.png"),
    },
    panel_button_template=load_template("templates/buttons/upgrade_more.png"),
)


# ─── UPGRADE STRATEGY ABC ────────────────────────────────────

class UpgradeStrategy(ABC):
    """Abstract base for building upgrade strategies."""

    @abstractmethod
    def should_upgrade(self, gold: int, elixir: int) -> bool:
        """Return True if resources are sufficient to attempt an upgrade."""
        ...

    @abstractmethod
    def execute_upgrade(self, building: Building) -> int:
        """Execute the upgrade flow. Returns number of upgrades completed (0 on failure)."""
        ...


# ─── WALL UPGRADE STRATEGY ───────────────────────────────────

GEM_TEMPLATE = load_template("templates/buttons/gem_cost.png")


class WallUpgradeStrategy(UpgradeStrategy):
    """
    Upgrade strategy for walls:
      1. Detect walls by color
      2. Tap a wall to open its panel
      3. Tap "Upgrade More" 3 times to select multiple walls
      4. Tap the upgrade button (gold or elixir)
      5. Check for gems on confirmation, then confirm
    """

    def should_upgrade(self, gold: int, elixir: int) -> bool:
        return gold >= GOLD_STORAGE_FULL or elixir >= ELIXIR_STORAGE_FULL

    def execute_upgrade(self, building: Building) -> int:
        # Read resources
        logger.info("[%s] Reading resources...", building.name)
        img = screenshot()
        gold, elixir = read_resources_from_village(img)
        logger.info("[%s] Gold: %d | Elixir: %d", building.name, gold, elixir)

        use_gold = gold >= GOLD_STORAGE_FULL
        use_elixir = elixir >= ELIXIR_STORAGE_FULL

        if not use_gold and not use_elixir:
            logger.info("[%s] Neither gold nor elixir is high enough", building.name)
            return 0

        # Detect building positions
        logger.info("[%s] Detecting positions...", building.name)
        positions = building.detect_method(img)
        logger.info("[%s] Found %d positions", building.name, len(positions))

        if not positions:
            logger.warning("[%s] No positions found", building.name)
            return 0

        save_debug(img, f"debug_{building.name}_before.png", points=positions)

        # Try tapping until we get the panel with the expected button
        panel_pos = None
        attempts_order = list(range(len(positions)))
        mid = len(attempts_order) // 2
        attempts_order = attempts_order[mid:] + attempts_order[:mid]

        for attempt_idx in attempts_order[:10]:
            wx, wy = positions[attempt_idx]
            logger.debug("[%s] Tapping at (%d, %d)...", building.name, wx, wy)
            tap(wx, wy, delay=1.5)

            img = screenshot()

            if building.panel_button_template is not None:
                panel_pos = find_template(img, building.panel_button_template, threshold=0.75)

            if panel_pos is not None:
                break

            logger.debug("[%s] Not the right panel, trying next...", building.name)
            tap(*EMPTY_TAP, delay=0.5)

        if panel_pos is None:
            logger.warning("[%s] Could not open panel after multiple attempts", building.name)
            tap(*EMPTY_TAP, delay=0.5)
            return 0

        # Tap panel button (e.g. "Upgrade More") multiple times
        logger.info("[%s] Found panel button at %s", building.name, panel_pos)
        for i in range(MAX_WALL_UPGRADES):
            logger.debug("[%s] Tapping panel button (%d/%d)...", building.name, i + 1, MAX_WALL_UPGRADES)
            tap(*panel_pos, delay=0.5)

        time.sleep(0.5)

        # Screenshot to find the upgrade button
        img = screenshot()

        # Determine which resource to prefer
        if use_gold and use_elixir:
            prefer_gold = gold >= elixir
        elif use_gold:
            prefer_gold = True
        else:
            prefer_gold = False

        # Find upgrade button
        upgrade_pos = None
        resource_used = None

        gold_tmpl = building.upgrade_templates.get("gold")
        elixir_tmpl = building.upgrade_templates.get("elixir")

        if prefer_gold and gold_tmpl is not None:
            pos = find_template(img, gold_tmpl, threshold=0.75)
            if pos:
                upgrade_pos = pos
                resource_used = "gold"

        if upgrade_pos is None and elixir_tmpl is not None:
            pos = find_template(img, elixir_tmpl, threshold=0.75)
            if pos:
                upgrade_pos = pos
                resource_used = "elixir"

        if upgrade_pos is None and not prefer_gold and gold_tmpl is not None:
            pos = find_template(img, gold_tmpl, threshold=0.75)
            if pos:
                upgrade_pos = pos
                resource_used = "gold"

        if upgrade_pos is None:
            logger.warning("[%s] No upgrade button found", building.name)
            tap(*EMPTY_TAP, delay=0.5)
            return 0

        # Tap upgrade
        logger.info("[%s] Tapping upgrade (%s) at %s...", building.name, resource_used, upgrade_pos)
        tap(*upgrade_pos, delay=1.5)

        # Check for gems on confirmation dialog
        img2 = screenshot()

        if GEM_TEMPLATE is not None:
            dialog_region = img2[600:1400, :]
            if find_template(dialog_region, GEM_TEMPLATE, threshold=0.85):
                logger.warning("[%s] Gem cost detected - canceling!", building.name)
                tap(*EMPTY_TAP, delay=0.5)
                return 0

        # Find and tap confirm button
        confirm_pos = find_button(img2, "confirm_upgrade")
        if confirm_pos:
            logger.info("[%s] Tapping confirm at %s...", building.name, confirm_pos)
            tap(*confirm_pos, delay=1)
        else:
            logger.debug("[%s] No confirm button (direct upgrade)", building.name)

        # Deselect
        tap(*EMPTY_TAP, delay=0.5)

        logger.info("[%s] Upgraded %d walls using %s!", building.name, MAX_WALL_UPGRADES, resource_used)
        return MAX_WALL_UPGRADES
