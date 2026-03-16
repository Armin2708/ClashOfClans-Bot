"""
Debug tool — draws grid lines and coordinates on reference screenshots
so you can identify exact pixel positions of buttons.

Usage:
    python find_buttons.py ref_village.png
    python find_buttons.py ref_battle.png
    python find_buttons.py all

Opens the image and overlays a grid with coordinates.
Look at the output image to find button positions.
"""

import cv2
import numpy as np
import sys
import os


def annotate_image(path):
    """Draw grid and coordinates on an image for position finding."""
    img = cv2.imread(path)
    if img is None:
        print(f"Cannot read {path}")
        return

    h, w = img.shape[:2]
    out = img.copy()

    # Draw grid every 10% of width/height
    for pct in range(0, 101, 10):
        x = int(w * pct / 100)
        y = int(h * pct / 100)

        # Vertical lines
        cv2.line(out, (x, 0), (x, h), (0, 255, 0), 1)
        cv2.putText(out, f"x={x}", (x + 5, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # Horizontal lines
        cv2.line(out, (0, y), (w, y), (0, 255, 0), 1)
        cv2.putText(out, f"y={y}", (5, y + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    # Finer grid every 5% with thinner lines
    for pct in range(5, 100, 10):
        x = int(w * pct / 100)
        y = int(h * pct / 100)
        cv2.line(out, (x, 0), (x, h), (0, 128, 0), 1)
        cv2.line(out, (0, y), (w, y), (0, 128, 0), 1)

    basename = os.path.splitext(os.path.basename(path))[0]
    out_path = f"grid_{basename}.png"
    cv2.imwrite(out_path, out)
    print(f"Saved {out_path} ({w}x{h}) — open it to find button positions")


def show_crops(path):
    """Show what's at key regions of the image."""
    img = cv2.imread(path)
    if img is None:
        return

    h, w = img.shape[:2]
    basename = os.path.splitext(os.path.basename(path))[0]

    # Save crops of each corner and edge for quick inspection
    regions = {
        "top_left": (0, 0, w // 3, h // 4),
        "top_center": (w // 3, 0, 2 * w // 3, h // 4),
        "top_right": (2 * w // 3, 0, w, h // 4),
        "bottom_left": (0, 3 * h // 4, w // 3, h),
        "bottom_center": (w // 3, 3 * h // 4, 2 * w // 3, h),
        "bottom_right": (2 * w // 3, 3 * h // 4, w, h),
    }

    for name, (x1, y1, x2, y2) in regions.items():
        crop = img[y1:y2, x1:x2]
        out_path = f"crop_{basename}_{name}.png"
        cv2.imwrite(out_path, crop)
        print(f"  {out_path} ({x2-x1}x{y2-y1})")


def main():
    if len(sys.argv) < 2:
        print("Usage: python find_buttons.py <image.png|all>")
        return

    if sys.argv[1] == "all":
        refs = [f for f in os.listdir(".") if f.startswith("ref_") and f.endswith(".png")]
        for ref in sorted(refs):
            print(f"\n=== {ref} ===")
            annotate_image(ref)
            show_crops(ref)
    else:
        path = sys.argv[1]
        annotate_image(path)
        show_crops(path)


if __name__ == "__main__":
    main()
