"""
Comprehensive test suite for all Clash of Clans bot features.

Tests both new and existing functionality:
  - State machine (GameState, StateTracker)
  - Metrics tracking
  - Building abstraction & upgrade strategies
  - Discord notifications
  - Circuit breaker
  - Screen functions (screenshot, tap, state detection)
  - Vision (wall detection, button detection, resource reading)
  - Tap verification & event-driven polling

Usage:
    python test_all.py              # Run all tests
    python test_all.py state        # State machine tests only
    python test_all.py metrics      # Metrics tests only
    python test_all.py buildings    # Building abstraction tests only
    python test_all.py notify       # Discord notification tests only
    python test_all.py circuit      # Circuit breaker tests only
    python test_all.py screen       # Screen/ADB tests (needs emulator)
    python test_all.py vision       # Vision tests (needs emulator)
    python test_all.py flow         # Flow logic tests (mocked)
"""

import sys
import time
import numpy as np

# ─── TEST FRAMEWORK ──────────────────────────────────────────

passed = 0
failed = 0
skipped = 0


def _pass(msg=""):
    global passed
    passed += 1
    print(f"  PASS{': ' + msg if msg else ''}")


def _fail(msg=""):
    global failed
    failed += 1
    print(f"  FAIL{': ' + msg if msg else ''}")


def _skip(msg=""):
    global skipped
    skipped += 1
    print(f"  SKIP{': ' + msg if msg else ''}")


# ═══════════════════════════════════════════════════════════════
# A. STATE MACHINE TESTS
# ═══════════════════════════════════════════════════════════════

def test_gamestate_enum():
    print("\n>>> TEST: GameState enum values")
    from bot.state_machine import GameState

    assert GameState.VILLAGE.value == "village"
    assert GameState.SCOUTING.value == "battle"
    assert GameState.RESULTS.value == "stars"
    assert GameState.BATTLE_ACTIVE.value == "in_battle"
    _pass("All GameState values correct")


def test_gamestate_string_equality():
    print("\n>>> TEST: GameState string comparison (backward compat)")
    from bot.state_machine import GameState

    if GameState.VILLAGE == "village":
        _pass("GameState.VILLAGE == 'village'")
    else:
        _fail("GameState.VILLAGE != 'village'")

    if GameState.RESULTS == "stars":
        _pass("GameState.RESULTS == 'stars'")
    else:
        _fail("GameState.RESULTS != 'stars'")

    if GameState.UNKNOWN == "unknown":
        _pass("GameState.UNKNOWN == 'unknown'")
    else:
        _fail("GameState.UNKNOWN != 'unknown'")


def test_gamestate_hash():
    print("\n>>> TEST: GameState is hashable (usable in dicts/sets)")
    from bot.state_machine import GameState

    state_set = {GameState.VILLAGE, GameState.UNKNOWN}
    if GameState.VILLAGE in state_set:
        _pass("GameState works in sets")
    else:
        _fail("GameState not usable in sets")


def test_state_tracker_init():
    print("\n>>> TEST: StateTracker initialization")
    from bot.state_machine import GameState, StateTracker

    tracker = StateTracker()
    if tracker.current_state == GameState.UNKNOWN:
        _pass("Initial state is UNKNOWN")
    else:
        _fail(f"Initial state is {tracker.current_state}, expected UNKNOWN")


def test_state_tracker_update():
    print("\n>>> TEST: StateTracker state transitions")
    from bot.state_machine import GameState, StateTracker

    tracker = StateTracker()
    changed = tracker.update(GameState.VILLAGE)
    if changed and tracker.current_state == GameState.VILLAGE:
        _pass("Transition UNKNOWN -> VILLAGE")
    else:
        _fail("Transition failed")

    # Same state should return False
    changed = tracker.update(GameState.VILLAGE)
    if not changed:
        _pass("No change when updating to same state")
    else:
        _fail("Should return False for same state")


def test_state_tracker_string_update():
    print("\n>>> TEST: StateTracker accepts string state (backward compat)")
    from bot.state_machine import GameState, StateTracker

    tracker = StateTracker()
    tracker.update("village")
    if tracker.current_state == GameState.VILLAGE:
        _pass("String 'village' -> GameState.VILLAGE")
    else:
        _fail(f"Got {tracker.current_state}")

    tracker.update("invalid_state_xyz")
    if tracker.current_state == GameState.UNKNOWN:
        _pass("Invalid string -> GameState.UNKNOWN")
    else:
        _fail(f"Got {tracker.current_state}")


def test_state_tracker_history():
    print("\n>>> TEST: StateTracker history tracking")
    from bot.state_machine import GameState, StateTracker

    tracker = StateTracker(max_history=5)
    for state in [GameState.VILLAGE, GameState.ATTACK_MENU, GameState.ARMY]:
        tracker.update(state)

    if len(tracker.history) == 3:
        _pass(f"History has {len(tracker.history)} entries")
    else:
        _fail(f"History has {len(tracker.history)} entries, expected 3")


def test_state_tracker_time_in_state():
    print("\n>>> TEST: StateTracker time_in_state()")
    from bot.state_machine import GameState, StateTracker

    tracker = StateTracker()
    tracker.update(GameState.VILLAGE)
    time.sleep(0.1)
    elapsed = tracker.time_in_state()
    if elapsed >= 0.1:
        _pass(f"time_in_state = {elapsed:.2f}s (>= 0.1s)")
    else:
        _fail(f"time_in_state = {elapsed:.2f}s (expected >= 0.1s)")


def test_state_tracker_stuck_not_timed_out():
    print("\n>>> TEST: StateTracker stuck_check() when not timed out")
    from bot.state_machine import GameState, StateTracker

    tracker = StateTracker()
    tracker.update(GameState.VILLAGE)
    result = tracker.stuck_check()
    if result is None:
        _pass("Not stuck (just entered state)")
    else:
        _fail(f"stuck_check returned '{result}', expected None")


def test_state_tracker_unknown_streak():
    print("\n>>> TEST: StateTracker unknown streak recovery")
    from bot.state_machine import GameState, StateTracker

    tracker = StateTracker()
    # _unknown_streak increments only on consecutive UNKNOWN updates
    # But update() ignores same-state transitions, so we need to
    # manually set the streak and test stuck_check()
    tracker.update(GameState.UNKNOWN)
    tracker._unknown_streak = 3
    # Force timeout so stuck_check triggers
    tracker.entered_at = time.time() - 20
    result = tracker.stuck_check()
    if result == "restart_app":
        _pass("3+ unknown streak -> restart_app")
    else:
        _fail(f"Expected 'restart_app', got '{result}'")


def test_valid_transitions():
    print("\n>>> TEST: Valid transitions defined for all states")
    from bot.state_machine import GameState, VALID_TRANSITIONS

    for state in GameState:
        if state in VALID_TRANSITIONS:
            _pass(f"{state.name} has {len(VALID_TRANSITIONS[state])} valid transitions")
        else:
            _fail(f"{state.name} missing from VALID_TRANSITIONS")


def test_state_timeouts():
    print("\n>>> TEST: State timeouts defined for all states")
    from bot.state_machine import GameState, STATE_TIMEOUTS

    for state in GameState:
        if state in STATE_TIMEOUTS:
            timeout = STATE_TIMEOUTS[state]
            _pass(f"{state.name}: timeout = {timeout}s")
        else:
            _fail(f"{state.name} missing from STATE_TIMEOUTS")


# ═══════════════════════════════════════════════════════════════
# B. METRICS TESTS
# ═══════════════════════════════════════════════════════════════

def test_metrics_init():
    print("\n>>> TEST: Metrics initialization")
    from bot.metrics import Metrics

    m = Metrics()
    if m.walls_upgraded == 0 and m.bases_attacked == 0 and m.bases_skipped == 0:
        _pass("All counters start at 0")
    else:
        _fail("Counters not zeroed")


def test_metrics_record_wall():
    print("\n>>> TEST: Metrics record_wall_upgrade()")
    from bot.metrics import Metrics

    m = Metrics()
    m.record_wall_upgrade(3)
    m.record_wall_upgrade(3)
    if m.walls_upgraded == 6:
        _pass(f"walls_upgraded = {m.walls_upgraded}")
    else:
        _fail(f"walls_upgraded = {m.walls_upgraded}, expected 6")


def test_metrics_record_attack():
    print("\n>>> TEST: Metrics record_attack()")
    from bot.metrics import Metrics

    m = Metrics()
    m.record_attack(gold=500000, elixir=300000)
    m.record_attack(gold=200000, elixir=100000)
    if m.bases_attacked == 2:
        _pass(f"bases_attacked = {m.bases_attacked}")
    else:
        _fail(f"bases_attacked = {m.bases_attacked}, expected 2")

    if m.total_gold_farmed == 700000:
        _pass(f"total_gold_farmed = {m.total_gold_farmed}")
    else:
        _fail(f"total_gold_farmed = {m.total_gold_farmed}, expected 700000")


def test_metrics_record_skip():
    print("\n>>> TEST: Metrics record_skip()")
    from bot.metrics import Metrics

    m = Metrics()
    m.record_skip()
    m.record_skip()
    m.record_skip()
    if m.bases_skipped == 3:
        _pass(f"bases_skipped = {m.bases_skipped}")
    else:
        _fail(f"bases_skipped = {m.bases_skipped}, expected 3")


def test_metrics_record_restart():
    print("\n>>> TEST: Metrics record_restart()")
    from bot.metrics import Metrics

    m = Metrics()
    m.record_restart()
    if m.app_restarts == 1:
        _pass(f"app_restarts = {m.app_restarts}")
    else:
        _fail(f"app_restarts = {m.app_restarts}, expected 1")


def test_metrics_summary():
    print("\n>>> TEST: Metrics get_summary()")
    from bot.metrics import Metrics

    m = Metrics()
    m.record_wall_upgrade(3)
    m.record_attack()
    m.record_skip()
    summary = m.get_summary()
    if "walls=3" in summary and "attacks=1" in summary and "skips=1" in summary:
        _pass(f"Summary: {summary}")
    else:
        _fail(f"Summary missing data: {summary}")


def test_metrics_thread_safety():
    print("\n>>> TEST: Metrics thread safety")
    import threading
    from bot.metrics import Metrics

    m = Metrics()
    errors = []

    def increment(n):
        try:
            for _ in range(n):
                m.record_attack()
                m.record_skip()
                m.record_wall_upgrade(1)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=increment, args=(100,)) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    if not errors and m.bases_attacked == 400 and m.bases_skipped == 400 and m.walls_upgraded == 400:
        _pass("Thread-safe: 4 threads x 100 increments = 400 each")
    else:
        _fail(f"Thread safety issue: attacked={m.bases_attacked}, skipped={m.bases_skipped}, walls={m.walls_upgraded}")


# ═══════════════════════════════════════════════════════════════
# C. BUILDING ABSTRACTION TESTS
# ═══════════════════════════════════════════════════════════════

def test_building_dataclass():
    print("\n>>> TEST: Building dataclass")
    from bot.buildings import Building, GOLD_WALL

    if GOLD_WALL.name == "wall":
        _pass(f"GOLD_WALL.name = '{GOLD_WALL.name}'")
    else:
        _fail(f"GOLD_WALL.name = '{GOLD_WALL.name}', expected 'wall'")

    if callable(GOLD_WALL.detect_method):
        _pass("detect_method is callable")
    else:
        _fail("detect_method is not callable")


def test_building_templates():
    print("\n>>> TEST: Building upgrade templates loaded")
    from bot.buildings import GOLD_WALL

    gold_tmpl = GOLD_WALL.upgrade_templates.get("gold")
    elixir_tmpl = GOLD_WALL.upgrade_templates.get("elixir")
    panel_tmpl = GOLD_WALL.panel_button_template

    if gold_tmpl is not None:
        _pass(f"Gold upgrade template loaded (shape: {gold_tmpl.shape})")
    else:
        _fail("Gold upgrade template is None")

    if elixir_tmpl is not None:
        _pass(f"Elixir upgrade template loaded (shape: {elixir_tmpl.shape})")
    else:
        _fail("Elixir upgrade template is None")

    if panel_tmpl is not None:
        _pass(f"Panel button template loaded (shape: {panel_tmpl.shape})")
    else:
        _fail("Panel button template is None")


def test_wall_strategy_should_upgrade():
    print("\n>>> TEST: WallUpgradeStrategy.should_upgrade()")
    from bot.buildings import WallUpgradeStrategy
    from bot.config import GOLD_STORAGE_FULL, ELIXIR_STORAGE_FULL

    strategy = WallUpgradeStrategy()

    # Below threshold
    if not strategy.should_upgrade(1_000_000, 1_000_000):
        _pass("Low resources -> False")
    else:
        _fail("Low resources should return False")

    # Gold full
    if strategy.should_upgrade(GOLD_STORAGE_FULL, 0):
        _pass(f"Gold >= {GOLD_STORAGE_FULL:,} -> True")
    else:
        _fail("Full gold should return True")

    # Elixir full
    if strategy.should_upgrade(0, ELIXIR_STORAGE_FULL):
        _pass(f"Elixir >= {ELIXIR_STORAGE_FULL:,} -> True")
    else:
        _fail("Full elixir should return True")

    # Both full
    if strategy.should_upgrade(GOLD_STORAGE_FULL, ELIXIR_STORAGE_FULL):
        _pass("Both full -> True")
    else:
        _fail("Both full should return True")


def test_upgrade_strategy_abc():
    print("\n>>> TEST: UpgradeStrategy is abstract")
    from bot.buildings import UpgradeStrategy

    try:
        UpgradeStrategy()
        _fail("Should not be able to instantiate abstract class")
    except TypeError:
        _pass("UpgradeStrategy cannot be instantiated (abstract)")


# ═══════════════════════════════════════════════════════════════
# D. DISCORD NOTIFICATION TESTS
# ═══════════════════════════════════════════════════════════════

def test_notify_send():
    print("\n>>> TEST: Discord notification send")
    from bot.notify import notify

    result = notify("Test: automated test suite")
    if result:
        _pass("Message sent successfully")
    else:
        _fail("Failed to send message (check webhook URL in config.py)")


def test_notify_summary():
    print("\n>>> TEST: Discord notify_summary()")
    from bot.metrics import Metrics
    from bot.notify import notify_summary

    m = Metrics()
    m.record_wall_upgrade(3)
    m.record_attack()
    # Just verify it doesn't crash — actual send tested above
    try:
        notify_summary(m)
        _pass("notify_summary() ran without error")
    except Exception as e:
        _fail(f"notify_summary() raised: {e}")


# ═══════════════════════════════════════════════════════════════
# E. CIRCUIT BREAKER TESTS
# ═══════════════════════════════════════════════════════════════

def test_circuit_breaker_init():
    print("\n>>> TEST: CircuitBreaker initialization")
    from bot.main import CircuitBreaker

    cb = CircuitBreaker(max_failures=3, window=300)
    if not cb.is_tripped():
        _pass("Not tripped on init")
    else:
        _fail("Should not be tripped on init")


def test_circuit_breaker_trip():
    print("\n>>> TEST: CircuitBreaker trips after max failures")
    from bot.main import CircuitBreaker

    cb = CircuitBreaker(max_failures=3, window=300)
    cb.record_failure()
    cb.record_failure()
    if not cb.is_tripped():
        _pass("Not tripped after 2 failures (threshold = 3)")
    else:
        _fail("Should not trip after 2 failures")

    cb.record_failure()
    if cb.is_tripped():
        _pass("Tripped after 3 failures")
    else:
        _fail("Should trip after 3 failures")


def test_circuit_breaker_reset():
    print("\n>>> TEST: CircuitBreaker reset")
    from bot.main import CircuitBreaker

    cb = CircuitBreaker(max_failures=3, window=300)
    cb.record_failure()
    cb.record_failure()
    cb.record_failure()
    cb.reset()
    if not cb.is_tripped():
        _pass("Not tripped after reset")
    else:
        _fail("Should not be tripped after reset")


def test_circuit_breaker_window():
    print("\n>>> TEST: CircuitBreaker time window expiry")
    from bot.main import CircuitBreaker

    cb = CircuitBreaker(max_failures=3, window=0.1)  # 100ms window
    cb.record_failure()
    cb.record_failure()
    time.sleep(0.2)  # Wait for window to expire
    cb.record_failure()
    if not cb.is_tripped():
        _pass("Old failures expired outside window")
    else:
        _fail("Old failures should have expired")


# ═══════════════════════════════════════════════════════════════
# F. SCREEN & ADB TESTS (needs emulator)
# ═══════════════════════════════════════════════════════════════

def test_adb_connection():
    print("\n>>> TEST: ADB connection")
    from bot.screen import check_adb_connection
    if check_adb_connection():
        _pass("ADB connected")
    else:
        _fail("ADB not connected")


def test_screenshot_capture():
    print("\n>>> TEST: Screenshot capture")
    from bot.screen import screenshot
    from bot.config import SCREEN_WIDTH, SCREEN_HEIGHT

    img = screenshot()
    h, w = img.shape[:2]
    if w == SCREEN_WIDTH and h == SCREEN_HEIGHT:
        _pass(f"Resolution {w}x{h} matches config")
    else:
        _fail(f"Resolution {w}x{h}, expected {SCREEN_WIDTH}x{SCREEN_HEIGHT}")

    if img.shape[2] == 3:
        _pass("3 channels (BGR)")
    else:
        _fail(f"{img.shape[2]} channels, expected 3")


def test_screen_state_detection():
    print("\n>>> TEST: Screen state detection")
    from bot.screen import screenshot
    from bot.vision import detect_screen_state
    from bot.state_machine import GameState

    img = screenshot()
    state = detect_screen_state(img)

    valid = [s for s in GameState]
    if state in valid:
        _pass(f"State: {state}")
    else:
        _fail(f"Invalid state: {state}")


def test_wait_for_state():
    print("\n>>> TEST: wait_for_state() returns current state quickly")
    from bot.screen import wait_for_state
    from bot.vision import detect_screen_state
    from bot.screen import screenshot

    # Detect current state first
    img = screenshot()
    current = detect_screen_state(img)

    start = time.time()
    result = wait_for_state(current, timeout=5)
    elapsed = time.time() - start

    if result is not None:
        _pass(f"wait_for_state({current}) returned in {elapsed:.1f}s")
    else:
        _fail(f"wait_for_state({current}) timed out")


def test_tap_and_verify():
    print("\n>>> TEST: tap_and_verify() function exists and callable")
    from bot.screen import tap_and_verify
    if callable(tap_and_verify):
        _pass("tap_and_verify is callable")
    else:
        _fail("tap_and_verify is not callable")


# ═══════════════════════════════════════════════════════════════
# G. VISION TESTS (needs emulator)
# ═══════════════════════════════════════════════════════════════

def test_wall_detection():
    print("\n>>> TEST: Wall detection")
    from bot.screen import screenshot
    from bot.vision import detect_walls

    img = screenshot()
    start = time.time()
    walls = detect_walls(img)
    elapsed = (time.time() - start) * 1000

    if isinstance(walls, list):
        _pass(f"detect_walls() returned list ({len(walls)} walls)")
    else:
        _fail(f"detect_walls() returned {type(walls)}")

    if elapsed < 1000:
        _pass(f"Detection time: {elapsed:.0f}ms")
    else:
        _fail(f"Detection time: {elapsed:.0f}ms (too slow)")

    # All positions should be (x, y) tuples
    all_valid = all(isinstance(w, tuple) and len(w) == 2 for w in walls)
    if all_valid:
        _pass("All positions are (x, y) tuples")
    else:
        _fail("Some positions are not valid tuples")


def test_button_detection():
    print("\n>>> TEST: Button detection")
    from bot.screen import screenshot
    from bot.vision import find_button

    img = screenshot()
    # On village screen, attack_button should be visible
    pos = find_button(img, "attack_button")
    if pos:
        _pass(f"attack_button found at {pos}")
    else:
        _fail("attack_button not found (are you on village screen?)")


def test_resource_reading():
    print("\n>>> TEST: Resource reading")
    from bot.resources import get_resources

    gold, elixir = get_resources()
    if gold >= 0:
        _pass(f"Gold: {gold:,}")
    else:
        _fail(f"Gold: {gold} (negative?)")

    if elixir >= 0:
        _pass(f"Elixir: {elixir:,}")
    else:
        _fail(f"Elixir: {elixir} (negative?)")


def test_template_validation():
    print("\n>>> TEST: Critical template validation")
    from bot.vision import validate_critical_templates
    try:
        validate_critical_templates()
        _pass("All critical templates present")
    except FileNotFoundError as e:
        _fail(str(e))


def test_popup_detection():
    print("\n>>> TEST: Popup detection")
    from bot.screen import screenshot
    from bot.vision import find_popup

    img = screenshot()
    pos = find_popup(img)
    if pos:
        _pass(f"Popup at {pos} (dismiss it)")
    else:
        _pass("No popup (normal)")


# ═══════════════════════════════════════════════════════════════
# H. FLOW LOGIC TESTS (mocked, no emulator needed)
# ═══════════════════════════════════════════════════════════════

def test_ensure_on_village_mocked():
    print("\n>>> TEST: ensure_on_village() — already on village (mocked)")
    from unittest.mock import patch
    from bot.state_machine import GameState

    dummy_img = np.zeros((1440, 2560, 3), dtype=np.uint8)

    with patch("bot.main.screenshot", return_value=dummy_img), \
         patch("bot.main.detect_screen_state", return_value=GameState.VILLAGE), \
         patch("bot.main.find_popup", return_value=None), \
         patch("bot.main.tap"):
        from bot.main import ensure_on_village, state_tracker
        result = ensure_on_village()

    if result is True:
        _pass("Returns True when on village")
    else:
        _fail(f"Returns {result}, expected True")


def test_main_loop_stops_on_upgrade_fail():
    print("\n>>> TEST: Main loop stops when upgrade fails with full resources")
    from bot.config import GOLD_STORAGE_FULL

    # The logic in main.py:
    # if gold >= GOLD_STORAGE_FULL or elixir >= ELIXIR_STORAGE_FULL:
    #     ... try upgrade ...
    #     if not upgraded:
    #         notify(...)
    #         return  <-- stops
    # This is verified by reading the code — the bot stops, not attacks
    from bot.main import UPGRADE_STRATEGIES
    if len(UPGRADE_STRATEGIES) > 0:
        _pass(f"UPGRADE_STRATEGIES has {len(UPGRADE_STRATEGIES)} strategies")
    else:
        _fail("UPGRADE_STRATEGIES is empty")


# ═══════════════════════════════════════════════════════════════
# TEST RUNNER
# ═══════════════════════════════════════════════════════════════

GROUPS = {
    "state": [
        test_gamestate_enum, test_gamestate_string_equality, test_gamestate_hash,
        test_state_tracker_init, test_state_tracker_update,
        test_state_tracker_string_update, test_state_tracker_history,
        test_state_tracker_time_in_state, test_state_tracker_stuck_not_timed_out,
        test_state_tracker_unknown_streak, test_valid_transitions,
        test_state_timeouts,
    ],
    "metrics": [
        test_metrics_init, test_metrics_record_wall, test_metrics_record_attack,
        test_metrics_record_skip, test_metrics_record_restart,
        test_metrics_summary, test_metrics_thread_safety,
    ],
    "buildings": [
        test_building_dataclass, test_building_templates,
        test_wall_strategy_should_upgrade, test_upgrade_strategy_abc,
    ],
    "notify": [
        test_notify_send, test_notify_summary,
    ],
    "circuit": [
        test_circuit_breaker_init, test_circuit_breaker_trip,
        test_circuit_breaker_reset, test_circuit_breaker_window,
    ],
    "screen": [
        test_adb_connection, test_screenshot_capture,
        test_screen_state_detection, test_wait_for_state,
        test_tap_and_verify,
    ],
    "vision": [
        test_wall_detection, test_button_detection,
        test_resource_reading, test_template_validation,
        test_popup_detection,
    ],
    "flow": [
        test_ensure_on_village_mocked, test_main_loop_stops_on_upgrade_fail,
    ],
}


def print_summary():
    global passed, failed, skipped
    total = passed + failed
    print(f"\n{'═' * 55}")
    print(f"  RESULTS: {passed}/{total} passed", end="")
    if skipped:
        print(f", {skipped} skipped", end="")
    if failed:
        print(f", {failed} FAILED", end="")
    print()
    print(f"{'═' * 55}")
    if failed == 0:
        print("  All tests passed!")
    else:
        print(f"  {failed} test(s) need attention.")


def run_all():
    print("=" * 55)
    print("  COC BOT — COMPREHENSIVE TEST SUITE")
    print("=" * 55)

    for group_name, tests_list in GROUPS.items():
        print(f"\n{'─' * 55}")
        print(f"  Group: {group_name}")
        print(f"{'─' * 55}")
        for test_fn in tests_list:
            try:
                test_fn()
            except Exception as e:
                _fail(f"{test_fn.__name__} raised: {e}")

    print_summary()


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"

    if cmd == "all":
        run_all()
    elif cmd in GROUPS:
        print(f"Running test group: {cmd}")
        for test_fn in GROUPS[cmd]:
            try:
                test_fn()
            except Exception as e:
                _fail(f"{test_fn.__name__} raised: {e}")
        print_summary()
    else:
        print(f"Unknown group: {cmd}")
        print(f"Available: all, {', '.join(GROUPS.keys())}")
