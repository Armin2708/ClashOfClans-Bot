"""
Wall upgrade module — screenshot-driven wall detection and upgrading.

Flow:
  1. Screenshot village → read resources → detect wall positions
  2. Pick upgrade resource based on which you have more of (gold or elixir)
  3. Tap a wall → screenshot → find the right upgrade button (gold or elixir)
  4. Tap upgrade → screenshot → check for gems → tap confirm
  5. After upgrading, re-screenshot to refresh wall positions
"""

import time
import cv2
from screen import screenshot, tap
from vision import find_button, detect_walls, find_popup, read_resources_from_village
from utils import find_template, save_debug, load_template
from config import GOLD_STORAGE_FULL, ELIXIR_STORAGE_FULL, WALL_MATCH_THRESHOLD, EMPTY_TAP

# Load gem template for safety check
GEM_TEMPLATE = load_template("templates/buttons/gem_cost.png")

# Load upgrade button templates
UPGRADE_GOLD_TEMPLATE = load_template("templates/buttons/upgrade_wall.png")
UPGRADE_ELIXIR_TEMPLATE = load_template("templates/buttons/upgrade_wall_elixir.png")


def try_upgrade_wall(wall_x, wall_y, use_gold=True, use_elixir=True):
    """
    Attempt to upgrade a single wall:
    1. Tap the wall
    2. Screenshot → find the right upgrade button (gold or elixir)
    3. Tap upgrade
    4. Screenshot → check for gems, find confirm
    5. Tap confirm (only if no gems)

    use_gold/use_elixir control which resource to try.
    Tries the preferred resource first, falls back to the other if available.

    Returns True if upgraded, False if skipped.
    """
    # Tap the wall
    tap(wall_x, wall_y, delay=1)

    # Screenshot the wall info panel
    print(f"  [Wall] Taking screenshot of wall info at ({wall_x}, {wall_y})...")
    img = screenshot()

    # Find the right upgrade button using template matching
    upgrade_pos = None
    resource_used = None

    if use_gold and UPGRADE_GOLD_TEMPLATE is not None:
        pos = find_template(img, UPGRADE_GOLD_TEMPLATE, threshold=WALL_MATCH_THRESHOLD)
        if pos:
            upgrade_pos = pos
            resource_used = "gold"

    if upgrade_pos is None and use_elixir and UPGRADE_ELIXIR_TEMPLATE is not None:
        pos = find_template(img, UPGRADE_ELIXIR_TEMPLATE, threshold=WALL_MATCH_THRESHOLD)
        if pos:
            upgrade_pos = pos
            resource_used = "elixir"

    if upgrade_pos is None:
        print("  [Wall] No upgrade button found")
        tap(*EMPTY_TAP, delay=0.5)
        return False

    # Tap upgrade
    print(f"  [Wall] Tapping upgrade ({resource_used}) at {upgrade_pos}...")
    tap(*upgrade_pos, delay=1)

    # Screenshot the confirm screen
    print("  [Wall] Taking screenshot of confirm screen...")
    img2 = screenshot()

    # SAFETY: Double-check for gems on confirmation dialog.
    # Only search the dialog area (y:600-1400) to avoid matching the HUD gem counter.
    if GEM_TEMPLATE is not None:
        dialog_region = img2[600:1400, :]
        if find_template(dialog_region, GEM_TEMPLATE, threshold=0.85):
            print("  [Wall] Gem cost on confirm screen, canceling!")
            tap(*EMPTY_TAP, delay=0.5)
            return False

    # Find and tap confirm button
    confirm_pos = find_button(img2, "confirm_upgrade")
    if confirm_pos:
        print(f"  [Wall] Tapping confirm at {confirm_pos}...")
        tap(*confirm_pos, delay=0.5)
    else:
        # Sometimes tapping upgrade directly upgrades without confirm
        print("  [Wall] No confirm button (direct upgrade)")

    print(f"  [Wall] Upgraded wall at ({wall_x}, {wall_y}) using {resource_used}!")
    return True


def upgrade_walls():
    """
    Detect all walls from a fresh screenshot, then try to upgrade each one.
    Checks resources first to decide whether to use gold, elixir, or both.
    After upgrading, re-scan to get updated wall positions.

    Returns number of walls upgraded.
    """
    # First check resources
    print("[Walls] Reading resources...")
    img = screenshot()
    gold, elixir = read_resources_from_village(img)
    print(f"[Walls] Gold: {gold} | Elixir: {elixir}")

    use_gold = gold >= GOLD_STORAGE_FULL
    use_elixir = elixir >= ELIXIR_STORAGE_FULL

    if not use_gold and not use_elixir:
        print("[Walls] Neither gold nor elixir is full enough to upgrade walls")
        return 0

    resource_str = []
    if use_gold:
        resource_str.append("gold")
    if use_elixir:
        resource_str.append("elixir")
    print(f"[Walls] Will upgrade using: {' and '.join(resource_str)}")

    # Detect walls
    print("[Walls] Detecting wall positions...")
    wall_positions = detect_walls(img)
    print(f"[Walls] Found {len(wall_positions)} upgradeable walls")

    if not wall_positions:
        print("[Walls] No walls to upgrade")
        return 0

    # Save debug image
    save_debug(img, "debug_walls_before.png", points=wall_positions)
    print("[Walls] Saved debug_walls_before.png")

    upgrades_done = 0

    for i, (wx, wy) in enumerate(wall_positions):
        print(f"\n[Walls] Trying wall {i + 1}/{len(wall_positions)} at ({wx}, {wy})...")

        if try_upgrade_wall(wx, wy, use_gold=use_gold, use_elixir=use_elixir):
            upgrades_done += 1
            time.sleep(1)

            # After each upgrade, re-read resources
            img = screenshot()
            gold, elixir = read_resources_from_village(img)
            print(f"[Walls] Resources — Gold: {gold}, Elixir: {elixir}")

            # Update which resources we can still use
            use_gold = gold >= GOLD_STORAGE_FULL
            use_elixir = elixir >= ELIXIR_STORAGE_FULL

            if not use_gold and not use_elixir:
                print("[Walls] Resources too low for more upgrades")
                break

    # Deselect
    tap(*EMPTY_TAP, delay=0.5)

    # Re-scan walls to get updated positions
    print(f"\n[Walls] Taking fresh screenshot of remaining walls...")
    img = screenshot()
    remaining = detect_walls(img)
    save_debug(img, "debug_walls_after.png", points=remaining)
    print(f"[Walls] {len(remaining)} walls remaining to upgrade")
    print(f"[Walls] Saved debug_walls_after.png")

    print(f"\n[Walls] Upgraded {upgrades_done} walls this round")
    return upgrades_done
