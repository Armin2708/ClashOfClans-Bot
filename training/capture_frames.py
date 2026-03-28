#!/usr/bin/env python3
"""
Capture screenshots during live bot runs for building the YOLO training dataset.

Saves each screenshot as a JPG + JSON metadata file. Screenshots should then
be uploaded to Roboflow (free tier) for manual annotation of UI classes
not covered by the public building dataset.

Two ways to use:
  1. Standalone: run alongside the bot in a separate terminal
     python training/capture_frames.py --interval 5 --output datasets/captured

  2. Programmatic: call capture_one() from key bot events
     from training.capture_frames import capture_one
     capture_one("scouting")  # saves one screenshot with hint label

Output per screenshot:
  datasets/captured/20260327_143201_123456_scouting.jpg
  datasets/captured/20260327_143201_123456_scouting.json  <- state + hint
"""

import json
import time
import threading
import argparse
from pathlib import Path
from datetime import datetime

_output_dir = Path("datasets/captured")
_stop_event = threading.Event()


def capture_one(hint: str = "auto", output_dir: Path | None = None) -> Path | None:
    """Save one screenshot + metadata. Returns the image path, or None on error."""
    try:
        from bot.screen import screenshot
        from bot.vision import detect_screen_state
        import cv2

        out = output_dir or _output_dir
        out.mkdir(parents=True, exist_ok=True)

        img = screenshot()
        state = str(detect_screen_state(img))
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        stem = f"{ts}_{hint}"

        img_path = out / f"{stem}.jpg"
        cv2.imwrite(str(img_path), img, [cv2.IMWRITE_JPEG_QUALITY, 95])

        meta = {"timestamp": ts, "state": state, "hint": hint}
        (out / f"{stem}.json").write_text(json.dumps(meta, indent=2))

        return img_path
    except Exception as e:
        print(f"[capture] Error: {e}")
        return None


def _capture_loop(interval: float, output_dir: Path) -> None:
    print(f"[capture] Saving to {output_dir}/ every {interval}s  (Ctrl+C to stop)")
    count = 0
    while not _stop_event.is_set():
        path = capture_one("auto", output_dir)
        if path:
            count += 1
            print(f"[capture] #{count}  {path.name}")
        time.sleep(interval)


def run_standalone(interval: float = 5.0, output_dir: str = "datasets/captured") -> None:
    """Run capture loop in the foreground until Ctrl+C."""
    _stop_event.clear()
    out = Path(output_dir)
    try:
        _capture_loop(interval, out)
    except KeyboardInterrupt:
        print(f"\n[capture] Stopped. {len(list(out.glob('*.jpg')))} screenshots saved.")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Capture bot screenshots for YOLO labeling")
    p.add_argument("--interval", type=float, default=5.0,
                   help="Seconds between captures (default: 5)")
    p.add_argument("--output", default="datasets/captured",
                   help="Output directory (default: datasets/captured)")
    args = p.parse_args()
    run_standalone(args.interval, args.output)
