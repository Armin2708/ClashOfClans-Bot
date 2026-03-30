"""
Test tool — run each bot component step by step.
Requires an emulator running with CoC open.

Usage:
    python test.py              # Run all non-destructive tests
    python test.py screenshot   # Test screenshot only
    python test.py tap          # Test tapping
    python test.py resources    # Test resource reading
    python test.py buttons      # Test button detection
    python test.py loot         # Test enemy loot reading (must be on scout screen)
    python test.py screen_state # Test screen state detection
    python test.py yolo_speed   # Benchmark YOLO detection speed
    python test.py popups       # Test popup detection
    python test.py templates    # Validate critical templates
    python test.py troop_slots  # Test troop slot detection (must be on battle screen)
    python test.py battle       # Test full battle (DESTRUCTIVE — will attack)
    python test.py surrender    # Test surrender flow (must be on scout/battle screen)
"""

import sys
import cv2
import time

from bot.config import SCREEN_WIDTH, SCREEN_HEIGHT

passed = 0
failed = 0
warnings = 0


def _pass(msg=""):
    global passed
    passed += 1
    print(f"  PASS{': ' + msg if msg else ''}")


def _fail(msg=""):
    global failed
    failed += 1
    print(f"  FAIL{': ' + msg if msg else ''}")


def _warn(msg=""):
    global warnings
    warnings += 1
    print(f"  WARN{': ' + msg if msg else ''}")


# ─── CORE TESTS ──────────────────────────────────────────────

def test_screenshot():
    print("\n>>> TEST: Screenshot")
    print("Taking screenshot from emulator...")
    from bot.screen import screenshot
    img = screenshot()
    cv2.imwrite("test_screenshot.png", img)
    h, w = img.shape[:2]
    print(f"  Image size: {w}x{h}")

    if w == SCREEN_WIDTH and h == SCREEN_HEIGHT:
        _pass(f"Resolution matches config ({SCREEN_WIDTH}x{SCREEN_HEIGHT})")
    else:
        _warn(f"Resolution {w}x{h} differs from config {SCREEN_WIDTH}x{SCREEN_HEIGHT}")

    if img.shape[2] == 3:
        _pass("Image has 3 channels (BGR)")
    else:
        _fail(f"Expected 3 channels, got {img.shape[2]}")

    print("  Saved test_screenshot.png — verify it shows your game")
    return img


def test_tap():
    print("\n>>> TEST: Tap")
    print("Tapping center of screen — watch your emulator...")
    from bot.screen import tap
    tap(1280, 720)
    _pass("Tap sent (visually verify on emulator)")


def test_resources():
    print("\n>>> TEST: Resource Reading")
    print("Make sure you're on the VILLAGE screen")
    from bot.resources import get_resources
    gold, elixir = get_resources()
    print(f"  Gold:   {gold}")
    print(f"  Elixir: {elixir}")

    if gold > 0:
        _pass(f"Gold reading: {gold}")
    else:
        _warn("Gold is 0 — might be correct, but check templates/digits/")

    if elixir > 0:
        _pass(f"Elixir reading: {elixir}")
    else:
        _warn("Elixir is 0 — might be correct, but check templates/digits/")


def test_buttons():
    print("\n>>> TEST: Button Detection")
    print("Make sure you're on the VILLAGE screen")
    from bot.screen import screenshot
    from bot.vision import find_button, detect_screen_state
    img = screenshot()

    state = detect_screen_state(img)
    print(f"  Screen state: {state}")

    if state != "unknown":
        _pass(f"Screen state detected: {state}")
    else:
        _fail("Screen state is 'unknown' — no buttons matched")

    buttons = ["attack_button", "find_match", "start_battle",
               "return_home", "stars_screen", "next_base",
               "confirm_upgrade", "end_battle"]
    found_count = 0
    for name in buttons:
        pos = find_button(img, name)
        status = f"found at {pos}" if pos else "not found"
        print(f"  {name}: {status}")
        if pos:
            found_count += 1

    if found_count > 0:
        _pass(f"Found {found_count} button(s)")
    else:
        _warn("No buttons found — check your templates/ directory")

    if state == "village":
        attack_pos = find_button(img, "attack_button")
        if attack_pos:
            _pass("Attack button found on village screen (expected)")
        else:
            _fail("Attack button NOT found on village screen")


def test_loot():
    print("\n>>> TEST: Enemy Loot Reading")
    print("Make sure you're SCOUTING an enemy base (Next button visible)")
    from bot.screen import screenshot
    from bot.vision import read_enemy_loot
    img = screenshot()

    cv2.imwrite("debug_loot_top_left.png", img[0:600, 0:600])
    print("  Saved debug_loot_top_left.png")

    start = time.time()
    gold, elixir = read_enemy_loot(img)
    elapsed = (time.time() - start) * 1000
    print(f"  Enemy Gold:   {gold}")
    print(f"  Enemy Elixir: {elixir}")
    print(f"  Read time: {elapsed:.0f}ms")

    if gold > 0 or elixir > 0:
        _pass(f"Loot read: gold={gold}, elixir={elixir}")
    else:
        _fail("Both loot values are 0 — check debug_loot_top_left.png")


# ─── NEW TESTS ───────────────────────────────────────────────

def test_screen_state():
    print("\n>>> TEST: Screen State Detection")
    from bot.screen import screenshot
    from bot.vision import detect_screen_state
    img = screenshot()

    start = time.time()
    state = detect_screen_state(img)
    elapsed = (time.time() - start) * 1000
    print(f"  Detected state: {state}")
    print(f"  Detection time: {elapsed:.1f}ms")

    valid_states = ["village", "attack_menu", "army", "battle", "in_battle", "stars", "unknown"]
    if state in valid_states:
        _pass(f"Valid state: {state}")
    else:
        _fail(f"Invalid state: {state}")

    if state != "unknown":
        _pass("State is not 'unknown'")
    else:
        _warn("State is 'unknown' — bot may not recognize current screen")


def test_yolo_speed():
    print("\n>>> TEST: YOLO Detection Speed Benchmark")
    from bot.screen import screenshot
    from bot.vision import detect_screen_state
    img = screenshot()

    iterations = 20
    start = time.time()
    for _ in range(iterations):
        detect_screen_state(img)
    avg_ms = (time.time() - start) / iterations * 1000

    print(f"  {iterations} iterations: avg {avg_ms:.1f}ms per call")

    if avg_ms < 100:
        _pass(f"YOLO detection: {avg_ms:.1f}ms (fast)")
    elif avg_ms < 300:
        _pass(f"YOLO detection: {avg_ms:.1f}ms (acceptable)")
    else:
        _warn(f"YOLO detection: {avg_ms:.1f}ms (slow)")


def test_popups():
    print("\n>>> TEST: Popup Detection")
    from bot.screen import screenshot
    from bot.vision import find_popup
    img = screenshot()

    pos = find_popup(img)
    if pos:
        print(f"  Popup found at {pos}")
        _pass("Popup detected (dismiss it if blocking)")
    else:
        print("  No popup found")
        _pass("No popup on screen (expected in normal state)")


def test_templates():
    print("\n>>> TEST: Critical Template Validation")
    from bot.vision import validate_critical_templates
    try:
        validate_critical_templates()
        _pass("All critical templates present")
    except FileNotFoundError as e:
        _fail(str(e))


def test_troop_slots():
    print("\n>>> TEST: Troop Slot Detection")
    print("Make sure you're on a BATTLE/SCOUT screen with the troop bar visible")
    from bot.screen import screenshot
    from bot.vision import get_troop_slots
    from bot.utils import save_debug
    img = screenshot()

    start = time.time()
    slots = get_troop_slots(img)
    elapsed = (time.time() - start) * 1000
    print(f"  Found {len(slots)} troop slots in {elapsed:.0f}ms")

    if isinstance(slots, list):
        _pass("get_troop_slots() returned a list")
    else:
        _fail(f"get_troop_slots() returned {type(slots)}")

    for i, (x, y) in enumerate(slots):
        print(f"    Slot {i + 1}: ({x}, {y})")

    save_debug(img, "test_troop_slots.png", points=slots)
    print("  Saved test_troop_slots.png — verify circles are on troop icons")

    if len(slots) > 0:
        _pass(f"Detected {len(slots)} slots")
    else:
        _warn("No troop slots found — are you on the battle screen?")


# ─── DESTRUCTIVE TESTS (require confirmation) ───────────────

def test_battle():
    print("\n>>> TEST: Full Battle (DESTRUCTIVE)")
    print("Make sure you're on the VILLAGE screen with troops trained")
    print("Starting in 5 seconds... (Ctrl+C to cancel)")
    time.sleep(5)
    from bot.battle import do_attack
    result = do_attack()
    if result:
        _pass("Battle completed successfully")
    else:
        _warn("Battle returned False — check logs above")


def test_surrender():
    print("\n>>> TEST: Surrender Flow (DESTRUCTIVE)")
    print("Make sure you're on a SCOUT or BATTLE screen")
    print("Starting in 5 seconds... (Ctrl+C to cancel)")
    time.sleep(5)
    from bot.battle import surrender_and_return
    surrender_and_return()
    _pass("Surrender flow completed (verify you're back on village)")


# ─── TEST RUNNER ─────────────────────────────────────────────

def run_all():
    print("=" * 55)
    print("  COC BOT — TEST SUITE")
    print("  Make sure CoC is open on the village screen")
    print("=" * 55)

    # Non-destructive tests (run automatically)
    test_templates()
    test_screenshot()
    input("\nPress Enter to continue to tap test...")
    test_tap()
    input("\nPress Enter to continue to screen state test...")
    test_screen_state()
    input("\nPress Enter to continue to popup test...")
    test_popups()
    input("\nPress Enter to continue to resource test...")
    test_resources()
    input("\nPress Enter to continue to button test...")
    test_buttons()
    input("\nPress Enter to continue to YOLO speed benchmark...")
    test_yolo_speed()

    print_summary()

    print("\n" + "=" * 55)
    print("Basic tests done!")
    print("Destructive tests (require specific game state):")
    print("  python test.py battle       # Full battle (village screen, troops trained)")
    print("  python test.py surrender    # Surrender (scout/battle screen)")
    print("  python test.py loot         # Loot reading (scout screen)")
    print("  python test.py troop_slots  # Troop slots (battle screen)")


def print_summary():
    global passed, failed, warnings
    print(f"\n{'─' * 40}")
    total = passed + failed
    print(f"  Results: {passed}/{total} passed", end="")
    if warnings:
        print(f", {warnings} warning(s)", end="")
    if failed:
        print(f", {failed} FAILED", end="")
    print()
    print(f"{'─' * 40}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"

    tests = {
        "all": run_all,
        "screenshot": test_screenshot,
        "tap": test_tap,
        "resources": test_resources,
        "buttons": test_buttons,
        "loot": test_loot,
        "battle": test_battle,
        "screen_state": test_screen_state,
        "yolo_speed": test_yolo_speed,
        "popups": test_popups,
        "templates": test_templates,
        "troop_slots": test_troop_slots,
        "surrender": test_surrender,
    }

    if cmd in tests:
        tests[cmd]()
        if cmd != "all":
            print_summary()
    else:
        print(f"Unknown test: {cmd}")
        print(f"Available: {', '.join(tests.keys())}")
