#!/usr/bin/env python3
"""
Data collection bot — scouts bases and captures screenshots for training.

Uses template matching for navigation (no YOLO needed). Enters battle
search, screenshots each base, taps Next to skip, and repeats.

Usage:
    python -m training.collect_bases --count 500
    python -m training.collect_bases --count 1000 --output datasets/bases
    python -m training.collect_bases --count 200 --auto-label
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import time
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger("coc.collect")

DEFAULT_OUTPUT = "datasets/bases"
TEMPLATE_DIR = Path("data/templates/buttons")


# ── ADB helpers ──────────────────────────────────────────────────────

def _screencap():
    """Take a screenshot via adb screencap."""
    raw = subprocess.run(
        ["adb", "exec-out", "screencap", "-p"],
        capture_output=True, timeout=10,
    ).stdout
    arr = np.frombuffer(raw, dtype=np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


def _tap(x, y, delay=0.5):
    """Tap via adb input."""
    subprocess.run(["adb", "shell", "input", "tap", str(int(x)), str(int(y))],
                   timeout=5)
    time.sleep(delay)


# ── Template matching ────────────────────────────────────────────────

def _find_template(img, template_name: str, threshold: float = 0.7):
    """Find a button via template matching. Returns (x, y) center or None."""
    tpl_path = TEMPLATE_DIR / f"{template_name}.png"
    if not tpl_path.exists():
        return None
    template = cv2.imread(str(tpl_path))
    if template is None:
        return None

    # Scale template if image resolution differs from base 2560x1440
    h_img, w_img = img.shape[:2]
    scale_x = w_img / 2560
    scale_y = h_img / 1440
    if abs(scale_x - 1.0) > 0.05 or abs(scale_y - 1.0) > 0.05:
        th, tw = template.shape[:2]
        template = cv2.resize(template, (int(tw * scale_x), int(th * scale_y)))

    result = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)
    if max_val >= threshold:
        th, tw = template.shape[:2]
        cx = max_loc[0] + tw // 2
        cy = max_loc[1] + th // 2
        return (cx, cy)
    return None


def _detect_state(img):
    """Simple state detection via template matching."""
    if _find_template(img, "next_base"):
        return "scouting"
    if _find_template(img, "attack_button"):
        return "village"
    if _find_template(img, "end_battle"):
        return "scouting"
    if _find_template(img, "find_match"):
        return "attack_menu"
    if _find_template(img, "start_battle"):
        return "army"
    if _find_template(img, "stars_screen"):
        return "results"
    if _find_template(img, "return_home"):
        return "results"
    return "unknown"


def _tap_button(template_name: str, delay=2.0) -> bool:
    """Screenshot, find button, tap it. Returns True if found and tapped."""
    img = _screencap()
    pos = _find_template(img, template_name)
    if pos:
        _tap(*pos, delay=delay)
        return True
    return False


def _wait_for_state(target: str, timeout: float = 30) -> bool:
    """Poll screenshots until we reach the target state."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        img = _screencap()
        if img is not None and _detect_state(img) == target:
            return True
        time.sleep(2)
    return False


# ── Main collection ──────────────────────────────────────────────────

def collect_bases(count: int, output_dir: str = DEFAULT_OUTPUT,
                  auto_label: bool = False):
    """Scout bases and save screenshots."""

    out = Path(output_dir)
    (out / "images").mkdir(parents=True, exist_ok=True)
    if auto_label:
        (out / "labels").mkdir(parents=True, exist_ok=True)

    print(f"Collecting {count} base screenshots -> {out.resolve()}")

    # Check current state
    img = _screencap()
    if img is None:
        print("ADB screencap failed. Is the device connected?")
        return
    state = _detect_state(img)
    print(f"Current state: {state}")

    if state != "village":
        print("Not on village screen. Please navigate to your village and retry.")
        return

    # Navigate: Attack -> Find Match -> Start Battle
    print("Entering battle search...")
    if not _tap_button("attack_button", delay=2):
        print("Attack button not found!")
        return

    if not _tap_button("find_match", delay=2):
        print("Find Match button not found!")
        return

    if not _tap_button("start_battle", delay=3):
        print("Start Battle button not found!")
        return

    # Wait for first base
    print("Waiting for first base...")
    if not _wait_for_state("scouting", timeout=30):
        print("Timed out waiting for first base")
        return

    # Auto-label setup
    detector = None
    if auto_label:
        try:
            from bot.detector import Detector
            label_model = Path("data/models/coc_synthetic.pt")
            if not label_model.exists():
                label_model = Path("data/models/coc.pt")
            detector = Detector(str(label_model), confidence=0.15)
            print(f"Auto-labeling with {len(detector._model.names)} classes")
        except Exception as e:
            print(f"Auto-label disabled: {e}")

    # Main collection loop
    collected = 0
    skip_failures = 0
    start_time = time.time()

    print(f"\nStarting collection...")
    print(f"{'─' * 50}")

    while collected < count:
        try:
            # Screenshot
            img = _screencap()
            if img is None:
                time.sleep(1)
                continue

            state = _detect_state(img)
            if state != "scouting":
                time.sleep(1)
                continue

            # Save screenshot
            timestamp = int(time.time() * 1000)
            img_name = f"base_{timestamp}.jpg"
            img_path = out / "images" / img_name
            cv2.imwrite(str(img_path), img, [cv2.IMWRITE_JPEG_QUALITY, 95])
            collected += 1

            # Auto-label
            det_count = "-"
            if detector:
                detections = detector.predict(img)
                h, w = img.shape[:2]
                lines = []
                for d in detections:
                    cx = (d.x1 + d.x2) / 2 / w
                    cy = (d.y1 + d.y2) / 2 / h
                    nw = (d.x2 - d.x1) / w
                    nh = (d.y2 - d.y1) / h
                    cls_id = list(detector._model.names.keys())[
                        list(detector._model.names.values()).index(d.cls)
                    ] if d.cls in detector._model.names.values() else 0
                    lines.append(f"{cls_id} {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}")
                lbl_path = out / "labels" / f"base_{timestamp}.txt"
                lbl_path.write_text("\n".join(lines))
                det_count = len(detections)

            elapsed = time.time() - start_time
            rate = collected / elapsed * 60 if elapsed > 0 else 0
            print(f"  [{collected}/{count}] {img_name} "
                  f"({det_count} det) [{rate:.1f}/min]")

            # Skip to next base
            pos = _find_template(img, "next_base")
            if pos:
                _tap(*pos, delay=0.5)
                skip_failures = 0
            else:
                skip_failures += 1
                if skip_failures >= 5:
                    print("  Too many skip failures, re-entering search...")
                    _tap_button("end_battle", delay=3)
                    _wait_for_state("village", timeout=15)
                    time.sleep(2)
                    _tap_button("attack_button", delay=2)
                    _tap_button("find_match", delay=2)
                    _tap_button("start_battle", delay=3)
                    _wait_for_state("scouting", timeout=30)
                    skip_failures = 0

            # Wait for next base to load
            time.sleep(3)

        except KeyboardInterrupt:
            print("\nStopped by user")
            break
        except Exception as e:
            logger.error("Error: %s", e)
            time.sleep(2)

    # Go home
    print(f"\n{'─' * 50}")
    print("Ending search...")
    _tap_button("end_battle", delay=3)
    time.sleep(3)
    _tap_button("return_home", delay=3)

    elapsed = time.time() - start_time
    print(f"\nDone!")
    print(f"  Collected: {collected} screenshots")
    print(f"  Time: {elapsed/60:.1f} minutes")
    print(f"  Rate: {collected/elapsed*60:.1f} bases/min")
    print(f"  Output: {out.resolve()}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Collect base screenshots for training")
    p.add_argument("--count", type=int, default=500,
                   help="Number of bases to screenshot (default: 500)")
    p.add_argument("--output", default=DEFAULT_OUTPUT,
                   help=f"Output directory (default: {DEFAULT_OUTPUT})")
    p.add_argument("--auto-label", action="store_true",
                   help="Auto-label using synthetic model")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s",
                        datefmt="%H:%M:%S")
    collect_bases(args.count, args.output, args.auto_label)
