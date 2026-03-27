"""
Clash of Clans Automation Bot — Main Loop

Flow:
  1. Ensure game is running and on village screen
  2. Attack: find a match, scout for loot, deploy troops
  3. Wait for battle to end, return home
  4. Back to step 1
"""

import time
import logging
import sys
from bot.screen import (
    screenshot, open_app, is_app_running, tap, restart_app,
    wait_for_state, check_adb_connection,
)
from bot.vision import (
    find_popup, detect_screen_state, read_resources_from_village,
    validate_critical_templates,
)
from bot.resources import get_resources
from bot.battle import do_attack, return_home, wait_for_battle_end
from bot.config import (
    LOOP_DELAY, APP_LAUNCH_WAIT, EMPTY_TAP,
    CIRCUIT_BREAKER_MAX_FAILURES, CIRCUIT_BREAKER_WINDOW, MAX_UNKNOWN_STATE_STREAK,
    FARM_TARGET_GOLD, FARM_TARGET_ELIXIR,
)
from bot.notify import notify, notify_summary
from bot.state_machine import GameState, StateTracker
from bot.metrics import metrics


def setup_logging():
    """Configure logging with file handler (bot.log) and stdout handler."""
    root = logging.getLogger("coc")
    root.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler
    fh = logging.FileHandler("bot.log", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    root.addHandler(fh)

    # Stdout handler
    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(logging.INFO)
    sh.setFormatter(formatter)
    root.addHandler(sh)


logger = logging.getLogger("coc.main")

# Global state tracker
state_tracker = StateTracker()

class CircuitBreaker:
    """Track consecutive failures within a time window. Trip if too many."""

    def __init__(self, max_failures=CIRCUIT_BREAKER_MAX_FAILURES,
                 window=CIRCUIT_BREAKER_WINDOW):
        self.max_failures = max_failures
        self.window = window
        self._failure_times = []

    def record_failure(self):
        now = time.time()
        self._failure_times.append(now)
        # Prune old failures outside the window
        cutoff = now - self.window
        self._failure_times = [t for t in self._failure_times if t > cutoff]

    def is_tripped(self):
        now = time.time()
        cutoff = now - self.window
        recent = [t for t in self._failure_times if t > cutoff]
        return len(recent) >= self.max_failures

    def reset(self):
        self._failure_times = []


circuit_breaker = CircuitBreaker()


def dismiss_popups():
    """Screenshot and dismiss any popup blocking the screen."""
    img = screenshot()
    pos = find_popup(img)
    if pos:
        logger.info("Dismissing popup at %s", pos)
        tap(*pos, delay=1)
        return True
    return False


def ensure_game_running():
    """Make sure CoC is open."""
    if not is_app_running():
        logger.info("Game not running, opening...")
        open_app()
        metrics.record_restart()
        # Poll for village instead of fixed APP_LAUNCH_WAIT
        if wait_for_state(GameState.VILLAGE, timeout=APP_LAUNCH_WAIT) is None:
            time.sleep(5)
        for _ in range(3):
            dismiss_popups()
            time.sleep(1)


def ensure_on_village():
    """Make sure we're on the village screen. Dismiss anything in the way.
    Escalates to app restart if initial attempts fail."""
    for attempt in range(5):
        img = screenshot()
        state = detect_screen_state(img)
        state_tracker.update(state)

        if state == GameState.VILLAGE:
            return True

        if state == GameState.RESULTS:
            return_home()
            continue

        if state == GameState.BATTLE_ACTIVE:
            logger.info("Detected active battle, waiting for it to end...")
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
    logger.warning("Cannot reach village after 5 attempts, force-restarting app...")
    restart_app()
    metrics.record_restart()
    circuit_breaker.record_failure()
    time.sleep(APP_LAUNCH_WAIT)
    for _ in range(3):
        dismiss_popups()
        time.sleep(1)

    img = screenshot()
    state = detect_screen_state(img)
    state_tracker.update(state)
    return state == GameState.VILLAGE


def main():
    setup_logging()

    logger.info("=" * 55)
    logger.info("  CLASH OF CLANS AUTOMATION BOT")
    logger.info("  Screenshot-driven — no hardcoded positions")
    logger.info("=" * 55)

    # ADB health check
    if not check_adb_connection():
        logger.error("ADB health check failed — cannot start bot")
        notify("Bot failed to start: ADB health check failed")
        return

    # Validate safety-critical templates before starting
    validate_critical_templates()

    ensure_game_running()
    # Wait for village to load instead of fixed sleep
    if wait_for_state(GameState.VILLAGE, timeout=10) is None:
        time.sleep(3)

    notify("Bot started")
    unknown_streak = 0
    loop_count = 0

    try:
        while True:
            loop_count += 1
            logger.info("=" * 40 + " LOOP #%d " + "=" * 40, loop_count)

            # Check circuit breaker
            if circuit_breaker.is_tripped():
                logger.error("Circuit breaker tripped: %d restarts failed in %d seconds",
                             CIRCUIT_BREAKER_MAX_FAILURES, CIRCUIT_BREAKER_WINDOW)
                notify(f"Bot stopped: circuit breaker tripped ({CIRCUIT_BREAKER_MAX_FAILURES} "
                       f"failures in {CIRCUIT_BREAKER_WINDOW}s)")
                return

            # Log metrics periodically
            metrics.maybe_log_hourly()

            # Check for stuck state and recover
            recovery = state_tracker.stuck_check()
            if recovery:
                logger.warning("State tracker: %s — recovery=%s", state_tracker, recovery)
                if recovery == "restart_app":
                    logger.warning("Stuck too long, restarting app...")
                    restart_app()
                    metrics.record_restart()
                    circuit_breaker.record_failure()
                    time.sleep(APP_LAUNCH_WAIT)
                elif recovery == "go_home":
                    return_home()
                elif recovery == "dismiss":
                    dismiss_popups()
                elif recovery == "tap_empty":
                    tap(*EMPTY_TAP, delay=1)

            # Make sure we're on the village screen
            dismiss_popups()
            if not ensure_on_village():
                unknown_streak += 1
                logger.warning("Can't get to village screen (streak: %d/%d)",
                               unknown_streak, MAX_UNKNOWN_STATE_STREAK)
                if unknown_streak >= MAX_UNKNOWN_STATE_STREAK:
                    logger.warning("Unknown state persisted %d times, restarting app...",
                                   MAX_UNKNOWN_STATE_STREAK)
                    restart_app()
                    metrics.record_restart()
                    circuit_breaker.record_failure()
                    unknown_streak = 0
                    time.sleep(APP_LAUNCH_WAIT)
                else:
                    time.sleep(5)
                continue

            unknown_streak = 0
            state_tracker.update(GameState.VILLAGE)

            # Step 1: Screenshot and read resources
            logger.info("Checking resources...")
            gold, elixir = get_resources()

            # Step 2: Attack
            logger.info("Going to attack...")
            attacked = do_attack()
            if attacked:
                metrics.record_attack()

    except KeyboardInterrupt:
        logger.info("Bot stopped by user (Ctrl+C)")
        notify("Bot stopped by user")
    except Exception as e:
        logger.exception("Bot crashed with unhandled exception: %s", e)
        notify(f"Bot crashed: {e}")
    finally:
        metrics.log_final()
        notify_summary(metrics)


def farm_to_max():
    """Attack repeatedly until both gold and elixir reach FARM_TARGET (31M).
    Does not upgrade walls — purely farms resources then stops."""
    setup_logging()

    logger.info("=" * 55)
    logger.info("  FARM MODE — target: Gold %d, Elixir %d",
                FARM_TARGET_GOLD, FARM_TARGET_ELIXIR)
    logger.info("=" * 55)

    if not check_adb_connection():
        logger.error("ADB health check failed")
        notify("Farm mode failed: ADB health check failed")
        return

    validate_critical_templates()
    ensure_game_running()
    if wait_for_state(GameState.VILLAGE, timeout=10) is None:
        time.sleep(3)

    notify(f"Farm mode started — target: {FARM_TARGET_GOLD:,} gold, {FARM_TARGET_ELIXIR:,} elixir")
    unknown_streak = 0
    loop_count = 0

    try:
        while True:
            loop_count += 1
            logger.info("=" * 30 + " FARM LOOP #%d " + "=" * 30, loop_count)

            if circuit_breaker.is_tripped():
                logger.error("Circuit breaker tripped")
                notify("Farm mode stopped: circuit breaker tripped")
                return

            metrics.maybe_log_hourly()

            recovery = state_tracker.stuck_check()
            if recovery:
                logger.warning("State tracker: %s — recovery=%s", state_tracker, recovery)
                if recovery == "restart_app":
                    restart_app()
                    metrics.record_restart()
                    circuit_breaker.record_failure()
                    time.sleep(APP_LAUNCH_WAIT)
                elif recovery == "go_home":
                    return_home()
                elif recovery == "dismiss":
                    dismiss_popups()
                elif recovery == "tap_empty":
                    tap(*EMPTY_TAP, delay=1)

            dismiss_popups()
            if not ensure_on_village():
                unknown_streak += 1
                if unknown_streak >= MAX_UNKNOWN_STATE_STREAK:
                    restart_app()
                    metrics.record_restart()
                    circuit_breaker.record_failure()
                    unknown_streak = 0
                    time.sleep(APP_LAUNCH_WAIT)
                else:
                    time.sleep(5)
                continue

            unknown_streak = 0
            state_tracker.update(GameState.VILLAGE)

            # Check resources
            gold, elixir = get_resources()
            logger.info("Resources — Gold: %d, Elixir: %d", gold, elixir)

            # Target reached?
            if gold >= FARM_TARGET_GOLD and elixir >= FARM_TARGET_ELIXIR:
                logger.info("FARM TARGET REACHED! Gold: %d, Elixir: %d", gold, elixir)
                notify(f"Farm target reached! Gold: {gold:,}, Elixir: {elixir:,}")
                metrics.log_final()
                return

            # Keep attacking
            logger.info("Farming... (need Gold: %d more, Elixir: %d more)",
                        max(0, FARM_TARGET_GOLD - gold),
                        max(0, FARM_TARGET_ELIXIR - elixir))
            attacked = do_attack()
            if attacked:
                metrics.record_attack()

    except KeyboardInterrupt:
        logger.info("Farm mode stopped by user (Ctrl+C)")
        notify("Farm mode stopped by user")
    except Exception as e:
        logger.exception("Farm mode crashed: %s", e)
        notify(f"Farm mode crashed: {e}")
    finally:
        metrics.log_final()
        notify_summary(metrics)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "farm":
        farm_to_max()
    else:
        main()
