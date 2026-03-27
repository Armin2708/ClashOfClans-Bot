"""QThread wrapper for the bot's main loop with stop/pause support."""

import threading
import logging
import time
from enum import Enum, auto

from PySide6.QtCore import QThread, Signal

logger = logging.getLogger("coc.worker")


class BotMode(Enum):
    FARM = auto()


class BotWorker(QThread):
    """Runs the bot loop in a background thread."""

    status_changed = Signal(str)
    resources_updated = Signal(int, int)
    metrics_updated = Signal(str)
    error_occurred = Signal(str)
    bot_stopped = Signal(str)

    def __init__(self, mode=BotMode.FARM):
        super().__init__()
        self.mode = mode
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()  # start in running state

    def stop(self):
        """Request the bot to stop."""
        logger.info("Stop requested")
        self._stop_event.set()
        self._pause_event.set()  # unpause so the loop can exit

    def pause(self):
        """Pause the bot loop."""
        logger.info("Pause requested")
        self._pause_event.clear()
        self.status_changed.emit("Paused")

    def resume(self):
        """Resume the bot loop."""
        logger.info("Resume requested")
        self._pause_event.set()
        self.status_changed.emit("Resumed")

    def _interruptible_sleep(self, seconds):
        """Sleep that can be interrupted by a stop request."""
        self._stop_event.wait(timeout=seconds)

    def _should_stop(self):
        return self._stop_event.is_set()

    def run(self):
        """Main bot loop — adapted from main.py's main() and farm_to_max()."""
        # Import bot modules inside run() to avoid circular imports
        from bot.screen import (
            screenshot, open_app, is_app_running, tap, restart_app,
            wait_for_state, check_adb_connection,
        )
        from bot.screen import init_stream, shutdown_stream
        from bot.vision import (
            find_popup, detect_screen_state, validate_critical_templates,
        )
        from bot.resources import get_resources
        from bot.battle import do_attack, return_home, wait_for_battle_end
        from bot.config import (
            APP_LAUNCH_WAIT, EMPTY_TAP,
            CIRCUIT_BREAKER_MAX_FAILURES, CIRCUIT_BREAKER_WINDOW,
            MAX_UNKNOWN_STATE_STREAK, FARM_TARGET_GOLD, FARM_TARGET_ELIXIR,
        )
        from bot.notify import notify, notify_summary
        from bot.state_machine import GameState, StateTracker
        from bot.metrics import metrics

        # -- Local helpers (same as main.py but using self for sleep) --

        def dismiss_popups():
            img = screenshot()
            pos = find_popup(img)
            if pos:
                logger.info("Dismissing popup at %s", pos)
                tap(*pos, delay=1)
                return True
            return False

        def ensure_game_running():
            if not is_app_running():
                logger.info("Game not running, opening...")
                open_app()
                metrics.record_restart()
                if wait_for_state(GameState.VILLAGE, timeout=APP_LAUNCH_WAIT) is None:
                    self._interruptible_sleep(5)
                for _ in range(3):
                    if self._should_stop():
                        return
                    dismiss_popups()
                    self._interruptible_sleep(1)

        def ensure_on_village():
            for attempt in range(5):
                if self._should_stop():
                    return False
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

                pos = find_popup(img)
                if pos:
                    tap(*pos, delay=1)
                    continue
                tap(*EMPTY_TAP, delay=1)

            logger.warning("Cannot reach village after 5 attempts, force-restarting app...")
            restart_app()
            metrics.record_restart()
            circuit_breaker.record_failure()
            self._interruptible_sleep(APP_LAUNCH_WAIT)
            for _ in range(3):
                if self._should_stop():
                    return False
                dismiss_popups()
                self._interruptible_sleep(1)

            img = screenshot()
            state = detect_screen_state(img)
            state_tracker.update(state)
            return state == GameState.VILLAGE

        # -- Circuit breaker (local instance) --
        class CircuitBreaker:
            def __init__(self, max_failures, window):
                self.max_failures = max_failures
                self.window = window
                self._failure_times = []

            def record_failure(self):
                now = time.time()
                self._failure_times.append(now)
                cutoff = now - self.window
                self._failure_times = [t for t in self._failure_times if t > cutoff]

            def is_tripped(self):
                now = time.time()
                cutoff = now - self.window
                recent = [t for t in self._failure_times if t > cutoff]
                return len(recent) >= self.max_failures

        circuit_breaker = CircuitBreaker(CIRCUIT_BREAKER_MAX_FAILURES, CIRCUIT_BREAKER_WINDOW)
        state_tracker = StateTracker()

        init_stream()

        try:
            self.status_changed.emit("Starting...")

            # ADB health check
            if not check_adb_connection():
                self.error_occurred.emit("ADB health check failed — cannot start bot")
                self.bot_stopped.emit("ADB health check failed")
                return

            validate_critical_templates()
            ensure_game_running()
            if self._should_stop():
                self.bot_stopped.emit("Stopped before loop started")
                return

            if wait_for_state(GameState.VILLAGE, timeout=10) is None:
                self._interruptible_sleep(3)

            self.status_changed.emit("Farm mode started")
            notify(f"Farm mode started — target: {FARM_TARGET_GOLD:,} gold, {FARM_TARGET_ELIXIR:,} elixir")

            unknown_streak = 0
            loop_count = 0

            while not self._should_stop():
                # Wait if paused
                self._pause_event.wait()
                if self._should_stop():
                    break

                loop_count += 1
                mode_label = "FARM"
                logger.info("=" * 30 + " %s #%d " + "=" * 30, mode_label, loop_count)

                # Circuit breaker
                if circuit_breaker.is_tripped():
                    msg = f"Circuit breaker tripped ({CIRCUIT_BREAKER_MAX_FAILURES} failures in {CIRCUIT_BREAKER_WINDOW}s)"
                    logger.error(msg)
                    self.error_occurred.emit(msg)
                    metrics.log_final()
                    self.bot_stopped.emit(msg)
                    return

                # Periodic metrics
                metrics.maybe_log_hourly()
                self.metrics_updated.emit(metrics.get_summary())

                # Stuck state recovery
                recovery = state_tracker.stuck_check()
                if recovery:
                    logger.warning("State tracker: %s — recovery=%s", state_tracker, recovery)
                    self.status_changed.emit(f"Recovery: {recovery}")
                    if recovery == "restart_app":
                        restart_app()
                        metrics.record_restart()
                        circuit_breaker.record_failure()
                        self._interruptible_sleep(APP_LAUNCH_WAIT)
                    elif recovery == "go_home":
                        return_home()
                    elif recovery == "dismiss":
                        dismiss_popups()
                    elif recovery == "tap_empty":
                        tap(*EMPTY_TAP, delay=1)

                # Ensure village
                dismiss_popups()
                if not ensure_on_village():
                    unknown_streak += 1
                    logger.warning("Can't get to village screen (streak: %d/%d)",
                                   unknown_streak, MAX_UNKNOWN_STATE_STREAK)
                    if unknown_streak >= MAX_UNKNOWN_STATE_STREAK:
                        restart_app()
                        metrics.record_restart()
                        circuit_breaker.record_failure()
                        unknown_streak = 0
                        self._interruptible_sleep(APP_LAUNCH_WAIT)
                    else:
                        self._interruptible_sleep(5)
                    continue

                unknown_streak = 0
                state_tracker.update(GameState.VILLAGE)

                # Read resources
                self.status_changed.emit("Checking resources...")
                gold, elixir = get_resources()
                self.resources_updated.emit(gold, elixir)
                logger.info("Resources — Gold: %d, Elixir: %d", gold, elixir)

                # Farm mode: check target
                if gold >= FARM_TARGET_GOLD and elixir >= FARM_TARGET_ELIXIR:
                    msg = f"Farm target reached! Gold: {gold:,}, Elixir: {elixir:,}"
                    logger.info(msg)
                    notify(msg)
                    self.status_changed.emit(msg)
                    metrics.log_final()
                    self.bot_stopped.emit(msg)
                    return

                # Keep attacking
                self.status_changed.emit(
                    f"Farming... (need Gold: {max(0, FARM_TARGET_GOLD - gold):,} more, "
                    f"Elixir: {max(0, FARM_TARGET_ELIXIR - elixir):,} more)"
                )
                attacked = do_attack()
                if attacked:
                    metrics.record_attack()

            # Clean exit
            reason = "Stopped by user"
            logger.info(reason)
            metrics.log_final()
            notify_summary(metrics)
            self.bot_stopped.emit(reason)

        except Exception as e:
            logger.exception("Bot crashed: %s", e)
            self.error_occurred.emit(str(e))
            metrics.log_final()
            self.bot_stopped.emit(f"Crashed: {e}")
        finally:
            shutdown_stream()
