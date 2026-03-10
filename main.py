"""
Clash of Clans Automation Bot — Main Loop

Flow:
  1. Screenshot village → read resources
  2. If gold OR elixir is full → upgrade walls
     a. Screenshot → detect walls by color
     b. Tap wall → screenshot wall info → tap upgrade
     c. Screenshot confirm → check no gems → tap confirm
     d. Re-screenshot to refresh remaining wall positions
  3. If resources not full (or wall upgrade failed) → go attack
     a. Screenshot → tap Attack → screenshot → tap Find a Match
     b. Screenshot army → tap Start Battle
     c. Screenshot enemy base → read loot
     d. If loot >= 1M gold or elixir → deploy troops to top corner
     e. If loot too low → tap Next, repeat
     f. Every 30s screenshot → check for stars screen
     g. Stars detected → tap Return Home
  4. Back to step 1
"""

import time
from screen import screenshot, open_app, is_app_running, tap, restart_app
from vision import (
    find_popup, detect_screen_state, read_resources_from_village,
    validate_critical_templates,
)
from resources import get_resources
from walls import upgrade_walls
from battle import do_attack, return_home, wait_for_battle_end
from config import GOLD_STORAGE_FULL, ELIXIR_STORAGE_FULL, LOOP_DELAY, APP_LAUNCH_WAIT, EMPTY_TAP


def dismiss_popups():
    """Screenshot and dismiss any popup blocking the screen."""
    img = screenshot()
    pos = find_popup(img)
    if pos:
        print(f"[Main] Dismissing popup at {pos}")
        tap(*pos, delay=1)
        return True
    return False


def ensure_game_running():
    """Make sure CoC is open."""
    if not is_app_running():
        print("[Main] Game not running, opening...")
        open_app()
        time.sleep(APP_LAUNCH_WAIT)
        for _ in range(3):
            dismiss_popups()
            time.sleep(1)


def ensure_on_village():
    """Make sure we're on the village screen. Dismiss anything in the way.
    Escalates to app restart if initial attempts fail."""
    for attempt in range(5):
        img = screenshot()
        state = detect_screen_state(img)

        if state == "village":
            return True

        if state == "stars":
            return_home()
            continue

        if state == "in_battle":
            print("[Main] Detected active battle, waiting for it to end...")
            wait_for_battle_end()
            return_home()
            continue

        # Try dismissing popups
        pos = find_popup(img)
        if pos:
            tap(*pos, delay=1)
            continue

        # Tap empty area to dismiss menus
        tap(*EMPTY_TAP, delay=1)

    # Escalation: force restart the app
    print("[Main] Cannot reach village after 5 attempts, force-restarting app...")
    restart_app()
    time.sleep(APP_LAUNCH_WAIT)
    for _ in range(3):
        dismiss_popups()
        time.sleep(1)

    img = screenshot()
    return detect_screen_state(img) == "village"


def main():
    print("=" * 55)
    print("  CLASH OF CLANS AUTOMATION BOT")
    print("  Screenshot-driven — no hardcoded positions")
    print("=" * 55)

    # Validate safety-critical templates before starting
    validate_critical_templates()

    ensure_game_running()
    time.sleep(3)

    loop_count = 0

    while True:
        loop_count += 1
        print(f"\n{'=' * 55}")
        print(f"  LOOP #{loop_count}")
        print(f"{'=' * 55}")

        # Make sure we're on the village screen
        dismiss_popups()
        if not ensure_on_village():
            print("[Main] Can't get to village screen, retrying...")
            time.sleep(5)
            continue

        # Step 1: Screenshot and read resources
        print("\n[Main] Checking resources...")
        gold, elixir = get_resources()

        # Step 2: If either resource is full, upgrade walls
        if gold >= GOLD_STORAGE_FULL or elixir >= ELIXIR_STORAGE_FULL:
            print(f"\n[Main] Resources full! Gold: {gold}, Elixir: {elixir}")
            print("[Main] → Upgrading walls...")
            walls_done = upgrade_walls()
            time.sleep(2)

            # If no walls were upgraded but resources are still full,
            # force an attack to prevent infinite loop
            if walls_done == 0:
                print("[Main] No walls upgraded — attacking to spend resources")
                do_attack()
                time.sleep(5)
                continue

            # Re-check resources after upgrading
            gold, elixir = get_resources()

        # Step 3: If neither resource is full, go attack
        if gold < GOLD_STORAGE_FULL and elixir < ELIXIR_STORAGE_FULL:
            print(f"\n[Main] Resources not full — Gold: {gold}, Elixir: {elixir}")
            print("[Main] → Going to attack...")
            do_attack()
            time.sleep(5)

        time.sleep(LOOP_DELAY)


if __name__ == "__main__":
    main()
