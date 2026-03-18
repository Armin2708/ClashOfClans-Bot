"""
Battle module — fully screenshot-driven attack sequence.

Flow:
  Village → Attack → Find a Match → Army → Start Battle → Clouds →
  Scout base → Check loot → Skip or Attack → Stars → Return Home
"""

import time
import logging
from bot.screen import screenshot, tap, swipe, wait_for_state, tap_and_verify
from bot.vision import (
    find_button, detect_screen_state, read_enemy_loot,
    get_deploy_corner, get_troop_slots, find_popup,
    auto_capture_template
)
import bot.config as config
from bot.state_machine import GameState

logger = logging.getLogger("coc.battle")


def _find_button_fresh(button_name):
    """Find a button via a fresh screenshot (no caching)."""
    img = screenshot()
    return find_button(img, button_name)


def _tap_button(button_name, expected_state=None, delay=2, verify_timeout=5):
    """Find a button via fresh screenshot, tap it, and optionally verify state change."""
    logger.debug("Taking screenshot to find %s...", button_name)
    img = screenshot()
    pos = find_button(img, button_name)
    if not pos:
        logger.warning("%s not found!", button_name)
        return False

    if expected_state:
        result = tap_and_verify(*pos, expected_state=expected_state, timeout=verify_timeout, delay=delay)
        if result is None:
            logger.warning("%s tapped but state didn't change to %s", button_name, expected_state)
            return False
        return True
    else:
        tap(*pos, delay=delay)
        return True


def enter_battle():
    """From village, navigate through Attack → Find a Match → Army → Start Battle."""
    if not _tap_button("attack_button", delay=2):
        return False
    if not _tap_button("find_match", delay=2):
        return False
    if not _tap_button("start_battle", delay=3):
        return False

    # Wait for clouds to clear (opponent found)
    logger.info("Searching for opponent...")
    if not wait_for_scout():
        logger.warning("Search timed out")
        return False

    return True


def wait_for_scout(timeout=30):
    """Wait until we land on an enemy base (scouting or active battle)."""
    start = time.time()
    while time.time() - start < timeout:
        img = screenshot()
        state = detect_screen_state(img)
        if state == GameState.SCOUTING:
            logger.info("Landed on enemy base (scouting)")
            return True
        if state == GameState.BATTLE_ACTIVE:
            logger.info("Landed directly in battle")
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
    logger.info("Enemy loot — Gold: %d, Elixir: %d", gold, elixir)

    if gold >= config.MIN_LOOT_TO_ATTACK or elixir >= config.MIN_LOOT_TO_ATTACK:
        logger.info("Loot meets threshold (%d)! Attacking...", config.MIN_LOOT_TO_ATTACK)
        deploy_troops(img)
        return True, None
    else:
        logger.info("Loot too low, skipping to next base...")
        next_img = skip_base(img)
        return False, next_img


def skip_base(img):
    """
    Tap the 'Next' button to skip to another base.
    Waits for the next base to load, then takes and returns a fresh screenshot.
    Falls back to tapping the center of the Next button ROI if template matching fails.
    """
    pos = find_button(img, "next_base")
    if not pos:
        # Fallback: tap center of the Next button ROI region.
        # The next_base template often fails because it captures a variable
        # gold cost number instead of the stable button graphic.
        roi = config.BUTTON_ROIS.get("next_base")
        if roi:
            x1, y1, x2, y2 = roi
            pos = ((x1 + x2) // 2, (y1 + y2) // 2)
            logger.info("Next button template miss — tapping ROI center (%d, %d)", *pos)
        else:
            logger.warning("Next button not found and no ROI fallback!")
            time.sleep(2)
            return screenshot()

    tap(*pos, delay=1)
    # Poll for scouting state instead of fixed sleep
    result = wait_for_state(GameState.SCOUTING, timeout=config.SCOUT_WAIT + 2, poll_interval=0.5)
    if result is not None:
        logger.debug("Next base loaded")
        return result
    logger.debug("Taking screenshot of next base...")
    return screenshot()


def deploy_troops(img):
    """Select each troop slot and deploy all troops to the top corner."""
    # Swipe left to make sure the deploy zone (top-left corner) is accessible
    logger.info("Swiping left to expose deploy zone...")
    swipe(config.DEPLOY_SWIPE_X1, config.DEPLOY_SWIPE_Y1, config.DEPLOY_SWIPE_X2, config.DEPLOY_SWIPE_Y2, config.DEPLOY_SWIPE_DURATION)
    time.sleep(0.5)
    swipe(config.DEPLOY_SWIPE_X1, config.DEPLOY_SWIPE_Y1, config.DEPLOY_SWIPE_X2, config.DEPLOY_SWIPE_Y2, config.DEPLOY_SWIPE_DURATION)
    time.sleep(1)

    # Take a fresh screenshot after repositioning
    img = screenshot()

    logger.debug("Detecting troop slots...")
    troop_slots = get_troop_slots(img)
    deploy_points = get_deploy_corner(img)

    if not troop_slots:
        logger.warning("No troop slots found! Using fallback...")
        h, w = img.shape[:2]
        troop_slots = [
            (config.FALLBACK_TROOP_X_START + i * config.FALLBACK_TROOP_X_SPACING, int(h * config.TROOP_BAR_Y_RATIO))
            for i in range(config.FALLBACK_TROOP_SLOTS)
        ]

    logger.info("Found %d troop slots", len(troop_slots))
    logger.info("Deploying to %d points in top corner", len(deploy_points))

    for slot_idx, (sx, sy) in enumerate(troop_slots):
        logger.debug("Selecting troop slot %d...", slot_idx + 1)
        tap(sx, sy, delay=0.3)

        # Rapid-tap all deployment points
        for (dx, dy) in deploy_points:
            tap(dx, dy, delay=0.05)

        time.sleep(0.2)

    # Swipe troop bar left to reveal more troops and deploy them too
    h, w = img.shape[:2]
    bar_y = int(h * config.TROOP_BAR_Y_RATIO)
    for swipe_round in range(config.DEPLOY_SWIPE_ROUNDS):
        logger.debug("Swiping troop bar left (round %d)...", swipe_round + 1)
        swipe(w // 2, bar_y, w // 4, bar_y, 300)
        time.sleep(0.5)

        img = screenshot()
        new_slots = get_troop_slots(img)
        deploy_points = get_deploy_corner(img)

        if not new_slots:
            logger.debug("No more troop slots found")
            break

        logger.debug("Found %d more troop slots", len(new_slots))
        for slot_idx, (sx, sy) in enumerate(new_slots):
            logger.debug("Selecting extra troop slot %d...", slot_idx + 1)
            tap(sx, sy, delay=0.3)

            for (dx, dy) in deploy_points:
                tap(dx, dy, delay=0.05)

            time.sleep(0.2)

    logger.info("All troops deployed!")


def wait_for_battle_end():
    """
    Called AFTER troops have been deployed.
    Polls for the battle to end by screenshotting periodically.
    Looks for the stars/results screen.
    """
    logger.info("Troops deployed — checking every %ds for battle end...", config.BATTLE_CHECK_INTERVAL)
    start = time.time()

    while time.time() - start < config.BATTLE_TIMEOUT:
        # Check first, then sleep (not sleep first)
        elapsed = int(time.time() - start)
        logger.debug("Screenshot at %ds — checking if battle ended...", elapsed)
        img = screenshot()

        state = detect_screen_state(img)
        if state == GameState.RESULTS:
            logger.info("Battle ended! Stars screen detected.")
            return True

        time.sleep(config.BATTLE_CHECK_INTERVAL)

    logger.warning("Battle timeout reached")
    return False


def return_home():
    """Tap Return Home on the results screen."""
    logger.info("Looking for Return Home button...")

    for attempt in range(5):
        img = screenshot()
        pos = find_button(img, "return_home")
        if pos:
            logger.info("Found Return Home at %s", pos)
            result = tap_and_verify(*pos, expected_state=GameState.VILLAGE, timeout=5, delay=2)
            if result is not None:
                logger.info("Back on village screen")
                return True
            # State didn't verify but tap succeeded, continue checking
            return True
        # Tap center to dismiss any overlay
        h, w = img.shape[:2]
        tap(w // 2, h // 2, delay=1)

    logger.warning("Could not find Return Home")
    return False


def surrender_and_return():
    """Exit an active scouting/battle screen by surrendering, then return home."""
    logger.info("Surrendering and returning home...")
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
        # Wait for stars screen instead of fixed sleep
        wait_for_state(GameState.RESULTS, timeout=5)

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
    if not enter_battle():
        return False

    # Wait for the first enemy base to load
    logger.info("Waiting for first enemy base...")
    img = wait_for_state(GameState.SCOUTING, timeout=5)
    if img is None:
        logger.debug("Taking screenshot of first enemy base...")
        img = screenshot()

    # Auto-capture the Next button template from the live scouting screen.
    # This keeps the template current even when game UI or costs change.
    auto_capture_template(img, "next_base")

    # Scout bases until we find one worth attacking
    consecutive_skip_failures = 0
    for i in range(config.MAX_BASE_SKIPS):
        logger.info("Base #%d...", i + 1)
        attacked, next_img = scout_and_decide(img)
        if attacked:
            break
        # Detect stuck loop: if loot values are identical, the base didn't change
        if next_img is not None:
            new_gold, new_elixir = read_enemy_loot(next_img)
            old_gold, old_elixir = read_enemy_loot(img)
            if new_gold == old_gold and new_elixir == old_elixir:
                consecutive_skip_failures += 1
                logger.warning("Same base detected after skip (%d/%d)", consecutive_skip_failures, 3)
                if consecutive_skip_failures >= 3:
                    logger.error("Stuck on same base — Next button likely broken. Surrendering.")
                    surrender_and_return()
                    return False
            else:
                consecutive_skip_failures = 0
        img = next_img
    else:
        logger.warning("Skipped too many bases, surrendering...")
        surrender_and_return()
        return False

    wait_for_battle_end()
    return_home()
    return True
