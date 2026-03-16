"""
Extract wall templates from the village screen.

Takes a screenshot and auto-extracts wall templates by cropping
known wall positions.

Usage:
    python extract_wall.py              # Auto-extract from live screenshot
    python extract_wall.py <x> <y>      # Manually crop a wall at pixel (x, y)
    python extract_wall.py <x> <y> <sz> # Same with custom size (default 34)
"""

import cv2
import sys
import os

from bot.screen import screenshot


def auto_extract(img):
    """
    Auto-extract wall templates from the screenshot.
    Saves multiple small crops from the wall grid area.
    """
    os.makedirs("templates/walls", exist_ok=True)
    h, w = img.shape[:2]

    # Gold wall: (1560, 440) was good. Try neighbors along the grid diagonal.
    gold_positions = [
        (1560, 440), (1595, 460), (1630, 480),
        (1525, 420), (1490, 400),
    ]

    # White wall: (2080, 480) was good. Try neighbors.
    white_positions = [
        (2080, 480), (2115, 500), (2045, 460),
    ]

    size = 34
    half = size // 2
    saved = 0

    for i, (x, y) in enumerate(gold_positions):
        x1 = max(0, x - half)
        y1 = max(0, y - half)
        x2 = min(w, x + half)
        y2 = min(h, y + half)
        crop = img[y1:y2, x1:x2]
        if crop.size == 0:
            continue
        path = f"templates/walls/wall_gold_{i}.png"
        cv2.imwrite(path, crop)
        print(f"  Saved {path} ({x2-x1}x{y2-y1}) from ({x},{y})")
        saved += 1

    for i, (x, y) in enumerate(white_positions):
        x1 = max(0, x - half)
        y1 = max(0, y - half)
        x2 = min(w, x + half)
        y2 = min(h, y + half)
        crop = img[y1:y2, x1:x2]
        if crop.size == 0:
            continue
        path = f"templates/walls/wall_white_{i}.png"
        cv2.imwrite(path, crop)
        print(f"  Saved {path} ({x2-x1}x{y2-y1}) from ({x},{y})")
        saved += 1

    print(f"\nSaved {saved} wall templates")
    print("Run: python test.py walls")


def manual_extract(img, x, y, size=34):
    """Crop a single wall at the given coordinates."""
    os.makedirs("templates/walls", exist_ok=True)
    h, w = img.shape[:2]
    half = size // 2
    x1 = max(0, x - half)
    y1 = max(0, y - half)
    x2 = min(w, x + half)
    y2 = min(h, y + half)

    crop = img[y1:y2, x1:x2]
    existing = len([f for f in os.listdir("templates/walls") if f.endswith(".png")])
    path = f"templates/walls/wall_{existing}.png"
    cv2.imwrite(path, crop)
    print(f"Saved {path} ({x2-x1}x{y2-y1}) from ({x},{y})")
    print("Run: python test.py walls")


def main():
    img = screenshot()
    h, w = img.shape[:2]
    print(f"Screenshot: {w}x{h}")

    if len(sys.argv) >= 3:
        x = int(sys.argv[1])
        y = int(sys.argv[2])
        size = int(sys.argv[3]) if len(sys.argv) > 3 else 34
        manual_extract(img, x, y, size)
    else:
        print("Auto-extracting wall templates...")
        auto_extract(img)


if __name__ == "__main__":
    main()
