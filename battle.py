"""
Battle module — fully screenshot-driven attack sequence.

Flow:
  Village → Attack → Find a Match → Army → Start Battle → Clouds →
  Scout base → Check loot → Skip or Attack → Stars → Return Home
"""

import time
from screen import screenshot, tap, swipe
from vision import (
    find_button, detect_screen_state, read_enemy_loot,
    get_deploy_corner, get_troop_slots, find_popup
)
from config import (
    MIN_LOOT_TO_ATTACK, BATTLE_CHECK_INTERVAL, BATTLE_TIMEOUT,
    MAX_BASE_SKIPS, SCOUT_WAIT, TROOP_BAR_Y_RATIO,
    DEPLOY_SWIPE_X1, DEPLOY_SWIPE_Y1, DEPLOY_SWIPE_X2, DEPLOY_SWIPE_Y2,
    DEPLOY_SWIPE_DURATION, DEPLOY_SWIPE_ROUNDS,
    FALLBACK_TROOP_SLOTS, FALLBACK_TROOP_X_START, FALLBACK_TROOP_X_SPACING,
)


_cached_buttons = {}


def _find_and_cache(img, button_name):
    """Find a button, cache its position for future use."""
    if button_name in _cached_buttons:
        return _cached_buttons[button_name]
    pos = find_button(img, button_name)
    if pos:
        _cached_buttons[button_name] = pos
        print(f"[Battle] Cached {button_name} at {pos}")
    return pos


def _get_button(button_name, delay=2):
    """Find a button (cached or via screenshot), tap it, and return success."""
    if button_name in _cached_buttons:
        pos = _cached_buttons[button_name]
        print(f"[Battle] Using cached {button_name} at {pos}")
    else:
        print(f"[Battle] Taking screenshot to find {button_name}...")
        img = screenshot()
        pos = _find_and_cache(img, button_name)
    if pos:
        tap(*pos, delay=delay)
        return True
    print(f"[Battle] {button_name} not found!")
    return False


def enter_battle():
    """From village, navigate through Attack → Find a Match → Army → Start Battle."""
    if not _get_button("attack_button", delay=2):
        return False
    if not _get_button("find_match", delay=2):
        return False
    if not _get_button("start_battle", delay=3):
        return False

    # Wait for clouds to clear (opponent found)
    print("[Battle] Searching for opponent...")
    if not wait_for_scout():
        print("[Battle] Search timed out")
        return False

    return True


def wait_for_scout(timeout=30):
    """Wait until we land on an enemy base (scouting or active battle)."""
    start = time.time()
    while time.time() - start < timeout:
        img = screenshot()
        state = detect_screen_state(img)
        if state == "battle":
            print("[Battle] Landed on enemy base (scouting)")
            return True
        if state == "in_battle":
            print("[Battle] Landed directly in battle")
            return True
        time.sleep(2)
    return False


def scout_and_decide(img):
    """
    Scout the current base using the provided screenshot.
    Check if loot meets threshold.
    If yes, attack. If no, skip to next base.
    Returns (True, None) if we attacked, (False, next_img) with fresh screenshot of next base.
    """
    gold, elixir = read_enemy_loot(img)
    print(f"[Scout] Enemy loot — Gold: {gold}, Elixir: {elixir}")

    if gold >= MIN_LOOT_TO_ATTACK or elixir >= MIN_LOOT_TO_ATTACK:
        print(f"[Scout] Loot meets threshold ({MIN_LOOT_TO_ATTACK})! Attacking...")
        deploy_troops(img)
        return True, None
    else:
        print("[Scout] Loot too low, skipping to next base...")
        next_img = skip_base(img)
        return False, next_img


def skip_base(img):
    """
    Tap the 'Next' button to skip to another base.
    Waits for the next base to load, then takes and returns a fresh screenshot.
    """
    pos = find_button(img, "next_base")
    if pos:
        tap(*pos, delay=1)
        time.sleep(SCOUT_WAIT)
        print("[Scout] Taking screenshot of next base...")
        return screenshot()
    else:
        print("[Scout] Next button not found!")
        time.sleep(2)
        return screenshot()


def deploy_troops(img):
    """Select each troop slot and deploy all troops to the top corner."""
    # Swipe left to make sure the deploy zone (top-left corner) is accessible
    print("[Deploy] Swiping left to expose deploy zone...")
    swipe(DEPLOY_SWIPE_X1, DEPLOY_SWIPE_Y1, DEPLOY_SWIPE_X2, DEPLOY_SWIPE_Y2, DEPLOY_SWIPE_DURATION)
    time.sleep(0.5)
    swipe(DEPLOY_SWIPE_X1, DEPLOY_SWIPE_Y1, DEPLOY_SWIPE_X2, DEPLOY_SWIPE_Y2, DEPLOY_SWIPE_DURATION)
    time.sleep(1)

    # Take a fresh screenshot after repositioning
    img = screenshot()

    print("[Deploy] Detecting troop slots...")
    troop_slots = get_troop_slots(img)
    deploy_points = get_deploy_corner(img)

    if not troop_slots:
        print("[Deploy] No troop slots found! Using fallback...")
        h, w = img.shape[:2]
        troop_slots = [
            (FALLBACK_TROOP_X_START + i * FALLBACK_TROOP_X_SPACING, int(h * TROOP_BAR_Y_RATIO))
            for i in range(FALLBACK_TROOP_SLOTS)
        ]

    print(f"[Deploy] Found {len(troop_slots)} troop slots")
    print(f"[Deploy] Deploying to {len(deploy_points)} points in top corner")

    for slot_idx, (sx, sy) in enumerate(troop_slots):
        print(f"[Deploy] Selecting troop slot {slot_idx + 1}...")
        tap(sx, sy, delay=0.3)

        # Rapid-tap all deployment points
        for (dx, dy) in deploy_points:
            tap(dx, dy, delay=0.05)

        time.sleep(0.2)

    # Swipe troop bar left to reveal more troops and deploy them too
    h, w = img.shape[:2]
    bar_y = int(h * TROOP_BAR_Y_RATIO)
    for swipe_round in range(DEPLOY_SWIPE_ROUNDS):
        print(f"[Deploy] Swiping troop bar left (round {swipe_round + 1})...")
        swipe(w // 2, bar_y, w // 4, bar_y, 300)
        time.sleep(0.5)

        img = screenshot()
        new_slots = get_troop_slots(img)
        deploy_points = get_deploy_corner(img)

        if not new_slots:
            print("[Deploy] No more troop slots found")
            break

        print(f"[Deploy] Found {len(new_slots)} more troop slots")
        for slot_idx, (sx, sy) in enumerate(new_slots):
            print(f"[Deploy] Selecting extra troop slot {slot_idx + 1}...")
            tap(sx, sy, delay=0.3)

            for (dx, dy) in deploy_points:
                tap(dx, dy, delay=0.05)

            time.sleep(0.2)

    print("[Deploy] All troops deployed!")


def wait_for_battle_end():
    """
    Called AFTER troops have been deployed.
    Waits for the battle to end by screenshotting periodically.
    Looks for the stars/results screen.
    """
    print(f"[Battle] Troops deployed — now checking every {BATTLE_CHECK_INTERVAL}s for battle end...")
    start = time.time()

    while time.time() - start < BATTLE_TIMEOUT:
        time.sleep(BATTLE_CHECK_INTERVAL)
        elapsed = int(time.time() - start)
        print(f"[Battle] Screenshot at {elapsed}s — checking if battle ended...")
        img = screenshot()

        state = detect_screen_state(img)
        if state == "stars":
            print("[Battle] Battle ended! Stars screen detected.")
            return True

    print("[Battle] Battle timeout reached")
    return False


def return_home():
    """Tap Return Home on the results screen."""
    print("[Battle] Looking for Return Home button...")

    for attempt in range(5):
        img = screenshot()
        pos = find_button(img, "return_home")
        if pos:
            print(f"[Battle] Found Return Home at {pos}")
            tap(*pos, delay=3)
            time.sleep(3)
            return True
        # Tap center to dismiss any overlay
        h, w = img.shape[:2]
        tap(w // 2, h // 2, delay=2)

    print("[Battle] Could not find Return Home")
    return False


def surrender_and_return():
    """Exit an active scouting/battle screen by surrendering, then return home."""
    print("[Battle] Surrendering and returning home...")
    img = screenshot()

    # Try tapping End Battle to surrender
    pos = find_button(img, "end_battle")
    if pos:
        tap(*pos, delay=2)
        # Look for surrender confirmation
        img2 = screenshot()
        confirm = find_button(img2, "confirm_upgrade")
        if confirm:
            tap(*confirm, delay=3)
        time.sleep(3)

    return_home()


def do_attack():
    """
    Full attack cycle:
    1. Enter battle screens
    2. Screenshot first enemy base
    3. Scout bases — screenshot each one, check loot, skip if too low
    4. When loot is good, deploy troops
    5. THEN start interval screenshots to wait for battle end
    6. Return home
    """
    global _cached_buttons
    _cached_buttons = {}

    if not enter_battle():
        return False

    # Take initial screenshot of the first enemy base
    time.sleep(2)
    print("[Scout] Taking screenshot of first enemy base...")
    img = screenshot()

    # Scout bases until we find one worth attacking
    for i in range(MAX_BASE_SKIPS):
        print(f"\n[Scout] Base #{i + 1}...")
        attacked, next_img = scout_and_decide(img)
        if attacked:
            break
        img = next_img
    else:
        print("[Battle] Skipped too many bases, surrendering...")
        surrender_and_return()
        return False

    wait_for_battle_end()
    time.sleep(3)
    return_home()
    return True
