"""
Offline test suite — runs without an emulator using saved reference images.
Tests vision logic, flow decisions, edge cases, and performance benchmarks.

Usage:
    python test_offline.py                # Run all offline tests
    python test_offline.py screen         # Screen state detection tests
    python test_offline.py resources      # Resource reading tests
    python test_offline.py loot           # Enemy loot reading tests
    python test_offline.py walls          # Wall detection tests
    python test_offline.py templates      # Template validation tests
    python test_offline.py roi            # ROI correctness tests
    python test_offline.py flow           # Flow logic tests (mocked)
    python test_offline.py benchmark      # Performance benchmarks
"""

import sys
import os
import cv2
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


def _load_ref(name):
    """Load a reference image, return None if missing."""
    path = f"ref_{name}.png"
    if not os.path.exists(path):
        return None
    return cv2.imread(path)


# ─── A. SCREEN STATE DETECTION ───────────────────────────────

def test_screen_states():
    print("\n>>> TEST GROUP: Screen State Detection (reference images)")
    from vision import detect_screen_state

    cases = [
        ("village", "village"),
        ("attack_menu", "attack_menu"),
        ("army", "army"),
        ("battle", "battle"),
        ("results", "stars"),
    ]

    for ref_name, expected_state in cases:
        img = _load_ref(ref_name)
        if img is None:
            _skip(f"ref_{ref_name}.png not found")
            continue

        state = detect_screen_state(img)
        if state == expected_state:
            _pass(f"ref_{ref_name}.png → '{state}'")
        else:
            _fail(f"ref_{ref_name}.png → '{state}', expected '{expected_state}'")


def test_unknown_state():
    print("\n>>> TEST: Unknown screen state (blank image)")
    from vision import detect_screen_state

    # Create a blank image
    blank = np.zeros((1440, 2560, 3), dtype=np.uint8)
    state = detect_screen_state(blank)
    if state == "unknown":
        _pass("Blank image → 'unknown'")
    else:
        _fail(f"Blank image → '{state}', expected 'unknown'")

    # Random noise image
    noise = np.random.randint(0, 255, (1440, 2560, 3), dtype=np.uint8)
    state = detect_screen_state(noise)
    if state == "unknown":
        _pass("Noise image → 'unknown'")
    else:
        _fail(f"Noise image → '{state}', expected 'unknown'")


# ─── B. RESOURCE READING ────────────────────────────────────

def test_read_village_resources():
    print("\n>>> TEST: Resource reading from ref_village.png")
    from vision import read_resources_from_village

    img = _load_ref("village")
    if img is None:
        _skip("ref_village.png not found")
        return

    gold, elixir = read_resources_from_village(img)
    print(f"  Gold: {gold}, Elixir: {elixir}")

    if gold > 0:
        _pass(f"Gold read: {gold}")
    else:
        _fail("Gold is 0 from ref_village.png")

    if elixir > 0:
        _pass(f"Elixir read: {elixir}")
    else:
        _fail("Elixir is 0 from ref_village.png")


def test_read_zero_resources():
    print("\n>>> TEST: Resource reading from blank crop")
    from vision import read_resources_from_village

    # Create a black image (no digits visible)
    blank = np.zeros((1440, 2560, 3), dtype=np.uint8)
    gold, elixir = read_resources_from_village(blank)

    if gold == 0:
        _pass("Gold is 0 for blank image")
    else:
        _fail(f"Gold is {gold} for blank image, expected 0")

    if elixir == 0:
        _pass("Elixir is 0 for blank image")
    else:
        _fail(f"Elixir is {elixir} for blank image, expected 0")


# ─── C. ENEMY LOOT READING ──────────────────────────────────

def test_read_enemy_loot():
    print("\n>>> TEST: Enemy loot reading from ref_battle.png")
    from vision import read_enemy_loot

    img = _load_ref("battle")
    if img is None:
        _skip("ref_battle.png not found")
        return

    gold, elixir = read_enemy_loot(img)
    print(f"  Enemy Gold: {gold}, Enemy Elixir: {elixir}")

    if gold > 0 or elixir > 0:
        _pass(f"Loot detected: gold={gold}, elixir={elixir}")
    else:
        _fail("Both loot values are 0 from ref_battle.png")


def test_read_enemy_loot_early_exit():
    print("\n>>> TEST: Enemy loot early exit performance")
    from vision import read_enemy_loot

    img = _load_ref("battle")
    if img is None:
        _skip("ref_battle.png not found")
        return

    # Time the function — it should be fast due to early exit
    runs = 5
    start = time.time()
    for _ in range(runs):
        read_enemy_loot(img)
    avg_ms = (time.time() - start) / runs * 1000
    print(f"  Average time: {avg_ms:.0f}ms over {runs} runs")

    if avg_ms < 2000:
        _pass(f"Loot reading averages {avg_ms:.0f}ms (< 2s)")
    else:
        _fail(f"Loot reading averages {avg_ms:.0f}ms (too slow, > 2s)")


# ─── D. WALL DETECTION ──────────────────────────────────────

def test_detect_walls_village():
    print("\n>>> TEST: Wall detection from ref_village.png")
    from vision import detect_walls

    img = _load_ref("village")
    if img is None:
        _skip("ref_village.png not found")
        return

    walls = detect_walls(img)
    print(f"  Found {len(walls)} walls")

    if isinstance(walls, list):
        _pass("detect_walls() returns a list")
    else:
        _fail(f"detect_walls() returned {type(walls)}")

    if len(walls) > 0:
        _pass(f"Detected {len(walls)} walls from village image")
    else:
        _fail("No walls detected from ref_village.png")

    # Check all positions are valid tuples
    all_valid = all(isinstance(w, tuple) and len(w) == 2 for w in walls)
    if all_valid:
        _pass("All wall positions are (x, y) tuples")
    else:
        _fail("Some wall positions are not valid (x, y) tuples")


def test_detect_walls_empty():
    print("\n>>> TEST: Wall detection from non-village image")
    from vision import detect_walls

    img = _load_ref("battle")
    if img is None:
        _skip("ref_battle.png not found")
        return

    walls = detect_walls(img)
    print(f"  Found {len(walls)} walls (expected 0 or very few)")

    # Battle screen should have no walls (or very few false positives)
    if len(walls) <= 5:
        _pass(f"Few/no walls on battle screen ({len(walls)} found)")
    else:
        _fail(f"Too many walls on battle screen ({len(walls)} found — likely false positives)")


# ─── E. TEMPLATE VALIDATION ─────────────────────────────────

def test_validate_critical_templates():
    print("\n>>> TEST: Critical template validation")
    from vision import validate_critical_templates

    try:
        validate_critical_templates()
        _pass("All critical templates present")
    except FileNotFoundError as e:
        _fail(str(e))


def test_validate_missing_template():
    print("\n>>> TEST: Missing template detection")
    from vision import get_template, _TEMPLATES

    # Ensure templates are loaded
    get_template("gem_cost")

    from vision import _TEMPLATES as templates
    if templates is None:
        _skip("Templates not loaded")
        return

    # Temporarily remove a critical template
    original = templates.get("gem_cost")
    templates["gem_cost"] = None

    from vision import validate_critical_templates
    try:
        validate_critical_templates()
        _fail("Should have raised FileNotFoundError for missing gem_cost")
    except FileNotFoundError:
        _pass("FileNotFoundError raised for missing gem_cost")

    # Restore
    templates["gem_cost"] = original


# ─── F. ROI MATCHING CORRECTNESS ────────────────────────────

def test_roi_correctness():
    print("\n>>> TEST GROUP: ROI matching correctness")
    from vision import _find_in_roi, get_template, _get_template_gray
    from utils import find_template
    from config import SCREEN_DETECT_THRESHOLD, BUTTON_ROIS

    # Test with each reference image that has known buttons
    ref_button_map = {
        "village": "attack_button",
        "battle": "next_base",
        "results": "return_home",
    }

    for ref_name, expected_button in ref_button_map.items():
        img = _load_ref(ref_name)
        if img is None:
            _skip(f"ref_{ref_name}.png not found")
            continue

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # ROI-based result
        roi_result = _find_in_roi(gray, expected_button, SCREEN_DETECT_THRESHOLD)

        # Full-image result
        full_result = find_template(img, get_template(expected_button), threshold=SCREEN_DETECT_THRESHOLD)

        # Both should find (or both miss) the button
        roi_found = roi_result is not None
        full_found = full_result is not None

        if roi_found == full_found:
            if roi_found:
                # Check positions are close (within 5px tolerance for ROI offset rounding)
                dx = abs(roi_result[0] - full_result[0])
                dy = abs(roi_result[1] - full_result[1])
                if dx <= 5 and dy <= 5:
                    _pass(f"ref_{ref_name}.png: {expected_button} — ROI and full-image agree at ~{roi_result}")
                else:
                    _fail(f"ref_{ref_name}.png: {expected_button} — ROI={roi_result} vs full={full_result} (off by {dx},{dy})")
            else:
                _pass(f"ref_{ref_name}.png: {expected_button} — both miss (expected if template doesn't match)")
        else:
            _fail(f"ref_{ref_name}.png: {expected_button} — ROI found={roi_found}, full found={full_found}")


def test_roi_all_buttons():
    print("\n>>> TEST: All ROI regions are within screen bounds")
    from config import BUTTON_ROIS, SCREEN_WIDTH, SCREEN_HEIGHT

    for name, (x1, y1, x2, y2) in BUTTON_ROIS.items():
        valid = (0 <= x1 < x2 <= SCREEN_WIDTH and 0 <= y1 < y2 <= SCREEN_HEIGHT)
        if valid:
            size = (x2 - x1) * (y2 - y1)
            full_size = SCREEN_WIDTH * SCREEN_HEIGHT
            ratio = size / full_size * 100
            _pass(f"{name}: ({x1},{y1})-({x2},{y2}) — {ratio:.1f}% of screen")
        else:
            _fail(f"{name}: ({x1},{y1})-({x2},{y2}) — out of bounds!")


# ─── G. FLOW LOGIC (MOCKED) ─────────────────────────────────

def test_scout_and_decide_attack():
    print("\n>>> TEST: scout_and_decide() — loot above threshold")

    from unittest.mock import patch, MagicMock
    from config import MIN_LOOT_TO_ATTACK

    img = _load_ref("battle")
    if img is None:
        # Create a dummy image
        img = np.zeros((1440, 2560, 3), dtype=np.uint8)

    high_loot = (2_000_000, 500_000)

    with patch("battle.read_enemy_loot", return_value=high_loot), \
         patch("battle.deploy_troops") as mock_deploy:
        from battle import scout_and_decide
        attacked, next_img = scout_and_decide(img)

    if attacked is True:
        _pass("scout_and_decide returned (True, ...) for high loot")
    else:
        _fail(f"scout_and_decide returned attacked={attacked}, expected True")

    if mock_deploy.called:
        _pass("deploy_troops() was called")
    else:
        _fail("deploy_troops() was NOT called")

    if next_img is None:
        _pass("next_img is None (expected after attack)")
    else:
        _fail("next_img should be None after attacking")


def test_scout_and_decide_skip():
    print("\n>>> TEST: scout_and_decide() — loot below threshold")

    from unittest.mock import patch, MagicMock

    img = _load_ref("battle")
    if img is None:
        img = np.zeros((1440, 2560, 3), dtype=np.uint8)

    low_loot = (100_000, 50_000)
    fake_next_img = np.zeros((1440, 2560, 3), dtype=np.uint8)

    with patch("battle.read_enemy_loot", return_value=low_loot), \
         patch("battle.deploy_troops") as mock_deploy, \
         patch("battle.skip_base", return_value=fake_next_img):
        from battle import scout_and_decide
        attacked, next_img = scout_and_decide(img)

    if attacked is False:
        _pass("scout_and_decide returned (False, ...) for low loot")
    else:
        _fail(f"scout_and_decide returned attacked={attacked}, expected False")

    if not mock_deploy.called:
        _pass("deploy_troops() was NOT called (correct)")
    else:
        _fail("deploy_troops() should NOT be called for low loot")

    if next_img is not None:
        _pass("next_img returned (screenshot of next base)")
    else:
        _fail("next_img should not be None when skipping")


def test_upgrade_walls_low_resources():
    print("\n>>> TEST: WallUpgradeStrategy — resources below threshold")

    from buildings import WallUpgradeStrategy

    strategy = WallUpgradeStrategy()

    if not strategy.should_upgrade(1_000_000, 500_000):
        _pass("should_upgrade() returned False for low resources")
    else:
        _fail("should_upgrade() should return False for low resources")

    if strategy.should_upgrade(25_000_000, 500_000):
        _pass("should_upgrade() returned True for high gold")
    else:
        _fail("should_upgrade() should return True for high gold")


def test_ensure_on_village_already_there():
    print("\n>>> TEST: ensure_on_village() — already on village")

    from unittest.mock import patch

    dummy_img = np.zeros((1440, 2560, 3), dtype=np.uint8)

    with patch("main.screenshot", return_value=dummy_img), \
         patch("main.detect_screen_state", return_value="village"), \
         patch("main.tap") as mock_tap:
        from main import ensure_on_village
        result = ensure_on_village()

    if result is True:
        _pass("ensure_on_village() returned True")
    else:
        _fail(f"ensure_on_village() returned {result}, expected True")

    if not mock_tap.called:
        _pass("No taps needed (already on village)")
    else:
        _fail(f"tap() called {mock_tap.call_count} times (should be 0)")


# ─── H. PERFORMANCE BENCHMARKS ──────────────────────────────

def test_benchmark_screen_detect():
    print("\n>>> BENCHMARK: detect_screen_state()")
    from vision import detect_screen_state

    img = _load_ref("village")
    if img is None:
        _skip("ref_village.png not found")
        return

    # Warmup
    for _ in range(3):
        detect_screen_state(img)

    runs = 100
    start = time.time()
    for _ in range(runs):
        detect_screen_state(img)
    avg_ms = (time.time() - start) / runs * 1000

    print(f"  {runs} iterations: avg {avg_ms:.1f}ms per call")

    if avg_ms < 50:
        _pass(f"Screen detection: {avg_ms:.1f}ms (fast)")
    elif avg_ms < 150:
        _pass(f"Screen detection: {avg_ms:.1f}ms (acceptable)")
    else:
        _fail(f"Screen detection: {avg_ms:.1f}ms (too slow, > 150ms)")


def test_benchmark_loot_reading():
    print("\n>>> BENCHMARK: read_enemy_loot()")
    from vision import read_enemy_loot

    img = _load_ref("battle")
    if img is None:
        _skip("ref_battle.png not found")
        return

    # Warmup
    for _ in range(2):
        read_enemy_loot(img)

    runs = 10
    start = time.time()
    for _ in range(runs):
        read_enemy_loot(img)
    avg_ms = (time.time() - start) / runs * 1000

    print(f"  {runs} iterations: avg {avg_ms:.0f}ms per call")

    if avg_ms < 1000:
        _pass(f"Loot reading: {avg_ms:.0f}ms (fast)")
    elif avg_ms < 2000:
        _pass(f"Loot reading: {avg_ms:.0f}ms (acceptable)")
    else:
        _fail(f"Loot reading: {avg_ms:.0f}ms (too slow, > 2s)")


def test_benchmark_wall_detect():
    print("\n>>> BENCHMARK: detect_walls()")
    from vision import detect_walls

    img = _load_ref("village")
    if img is None:
        _skip("ref_village.png not found")
        return

    # Warmup
    detect_walls(img)

    runs = 10
    start = time.time()
    for _ in range(runs):
        detect_walls(img)
    avg_ms = (time.time() - start) / runs * 1000

    print(f"  {runs} iterations: avg {avg_ms:.0f}ms per call")

    if avg_ms < 1000:
        _pass(f"Wall detection: {avg_ms:.0f}ms (fast)")
    elif avg_ms < 2000:
        _pass(f"Wall detection: {avg_ms:.0f}ms (acceptable)")
    else:
        _fail(f"Wall detection: {avg_ms:.0f}ms (too slow, > 2s)")


def test_benchmark_resource_reading():
    print("\n>>> BENCHMARK: read_resources_from_village()")
    from vision import read_resources_from_village

    img = _load_ref("village")
    if img is None:
        _skip("ref_village.png not found")
        return

    # Warmup
    read_resources_from_village(img)

    runs = 20
    start = time.time()
    for _ in range(runs):
        read_resources_from_village(img)
    avg_ms = (time.time() - start) / runs * 1000

    print(f"  {runs} iterations: avg {avg_ms:.0f}ms per call")

    if avg_ms < 500:
        _pass(f"Resource reading: {avg_ms:.0f}ms (fast)")
    elif avg_ms < 1000:
        _pass(f"Resource reading: {avg_ms:.0f}ms (acceptable)")
    else:
        _fail(f"Resource reading: {avg_ms:.0f}ms (too slow, > 1s)")


# ─── TEST RUNNER ─────────────────────────────────────────────

def run_group(name, tests_list):
    for test_fn in tests_list:
        test_fn()


GROUPS = {
    "screen": [test_screen_states, test_unknown_state],
    "resources": [test_read_village_resources, test_read_zero_resources],
    "loot": [test_read_enemy_loot, test_read_enemy_loot_early_exit],
    "walls": [test_detect_walls_village, test_detect_walls_empty],
    "templates": [test_validate_critical_templates, test_validate_missing_template],
    "roi": [test_roi_correctness, test_roi_all_buttons],
    "flow": [
        test_scout_and_decide_attack, test_scout_and_decide_skip,
        test_upgrade_walls_low_resources, test_ensure_on_village_already_there,
    ],
    "benchmark": [
        test_benchmark_screen_detect, test_benchmark_loot_reading,
        test_benchmark_wall_detect, test_benchmark_resource_reading,
    ],
}


def run_all():
    print("=" * 55)
    print("  COC BOT — OFFLINE TEST SUITE")
    print("  No emulator required — uses reference images")
    print("=" * 55)

    for group_name, tests_list in GROUPS.items():
        print(f"\n{'─' * 55}")
        print(f"  Group: {group_name}")
        print(f"{'─' * 55}")
        for test_fn in tests_list:
            test_fn()

    print_summary()


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


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"

    if cmd == "all":
        run_all()
    elif cmd in GROUPS:
        print(f"Running test group: {cmd}")
        for test_fn in GROUPS[cmd]:
            test_fn()
        print_summary()
    else:
        print(f"Unknown group: {cmd}")
        print(f"Available: all, {', '.join(GROUPS.keys())}")
