#!/usr/bin/env python3
"""
Grid Calibrator GUI — visually align the 44x44 isometric tile grid
to the empty base template image.

Controls:
  Arrow keys:      move grid anchor (0.5px)
  Shift + Arrows:  move grid anchor (5px)
  W / S:           adjust tile half-width  (±0.01)
  A / D:           adjust tile half-height (±0.01)
  Shift + W/S/A/D: coarse adjust (±0.1)
  Mouse drag:      move grid anchor
  G:               toggle full grid / outline only
  B:               toggle buildable area highlight
  Enter / Space:   save calibration
  R:               reset to defaults
  Q:               save and quit

Saves calibration to training/grid_calibration.json
"""

import json
import sys
from pathlib import Path

import cv2
import numpy as np

# ── Defaults ────────────────────────────────────────────────────────

GRID_SIZE = 44
BUILDABLE_MIN = 0
BUILDABLE_MAX = 43

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TEMPLATE = str(_PROJECT_ROOT / "data/templates/base/empty_base.jpg")
CALIBRATION_FILE = str(_PROJECT_ROOT / "data/calibration/grid_calibration.json")

# Reference values (current hardcoded defaults in base_builder.py)
DEF_TOP_X = 1012.5
DEF_TOP_Y = 137.6
DEF_TILE_HW = 17.38
DEF_TILE_HH = 12.95


# ── Load / Save ─────────────────────────────────────────────────────

def load_calibration() -> dict:
    p = Path(CALIBRATION_FILE)
    if p.exists():
        with open(p) as f:
            return json.load(f)
    return {
        "top_x": DEF_TOP_X,
        "top_y": DEF_TOP_Y,
        "tile_half_w": DEF_TILE_HW,
        "tile_half_h": DEF_TILE_HH,
    }


def save_calibration(cal: dict):
    Path(CALIBRATION_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(CALIBRATION_FILE, "w") as f:
        json.dump(cal, f, indent=2)


# ── Grid rendering ──────────────────────────────────────────────────

def tile_to_screen(tx, ty, top_x, top_y, thw, thh):
    sx = top_x + tx * thw - ty * thw
    sy = top_y + tx * thh + ty * thh
    return int(round(sx)), int(round(sy))


def draw_grid(canvas, top_x, top_y, thw, thh, disp_scale,
              show_full_grid=True, show_buildable=True):
    """Draw the isometric grid overlay on the display canvas."""
    h, w = canvas.shape[:2]

    def ts(tx, ty):
        sx, sy = tile_to_screen(tx, ty, top_x, top_y, thw, thh)
        return int(sx * disp_scale), int(sy * disp_scale)

    # Buildable area highlight
    if show_buildable:
        b_top = ts(BUILDABLE_MIN, BUILDABLE_MIN)
        b_right = ts(BUILDABLE_MAX + 1, BUILDABLE_MIN)
        b_bottom = ts(BUILDABLE_MAX + 1, BUILDABLE_MAX + 1)
        b_left = ts(BUILDABLE_MIN, BUILDABLE_MAX + 1)
        pts = np.array([b_top, b_right, b_bottom, b_left], dtype=np.int32)
        overlay = canvas.copy()
        cv2.fillPoly(overlay, [pts], (40, 80, 40))
        cv2.addWeighted(overlay, 0.2, canvas, 0.8, 0, canvas)
        cv2.polylines(canvas, [pts], True, (0, 200, 0), 2, cv2.LINE_AA)

    # Full grid lines
    if show_full_grid:
        for i in range(GRID_SIZE + 1):
            # Row lines: tile(i, 0) to tile(i, GRID_SIZE)
            p1 = ts(i, 0)
            p2 = ts(i, GRID_SIZE)
            cv2.line(canvas, p1, p2, (0, 140, 140), 1, cv2.LINE_AA)
            # Column lines: tile(0, i) to tile(GRID_SIZE, i)
            p1 = ts(0, i)
            p2 = ts(GRID_SIZE, i)
            cv2.line(canvas, p1, p2, (0, 140, 140), 1, cv2.LINE_AA)

    # Outer diamond (always drawn, thicker)
    d_top = ts(0, 0)
    d_right = ts(GRID_SIZE, 0)
    d_bottom = ts(GRID_SIZE, GRID_SIZE)
    d_left = ts(0, GRID_SIZE)
    pts = np.array([d_top, d_right, d_bottom, d_left], dtype=np.int32)
    cv2.polylines(canvas, [pts], True, (0, 255, 255), 2, cv2.LINE_AA)

    # Anchor point crosshair
    ax, ay = ts(0, 0)
    cv2.drawMarker(canvas, (ax, ay), (0, 0, 255), cv2.MARKER_CROSS, 20, 2)

    # Center point
    cx, cy = ts(GRID_SIZE // 2, GRID_SIZE // 2)
    cv2.drawMarker(canvas, (cx, cy), (255, 0, 255), cv2.MARKER_CROSS, 15, 1)


def render_frame(template, top_x, top_y, thw, thh, disp_scale,
                 show_full_grid, show_buildable):
    """Resize template and draw grid overlay."""
    th, tw = template.shape[:2]
    dw = int(tw * disp_scale)
    dh = int(th * disp_scale)
    canvas = cv2.resize(template, (dw, dh), interpolation=cv2.INTER_AREA)

    draw_grid(canvas, top_x, top_y, thw, thh, disp_scale,
              show_full_grid, show_buildable)

    # HUD background
    cv2.rectangle(canvas, (0, dh - 70), (dw, dh), (0, 0, 0), -1)

    # Values
    cv2.putText(canvas,
                f"top: ({top_x:.1f}, {top_y:.1f})  "
                f"tile_hw: {thw:.2f}  tile_hh: {thh:.2f}",
                (10, dh - 45),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    cv2.putText(canvas,
                "Arrows: move | W/S: tile_hw | A/D: tile_hh | "
                "G: grid | B: buildable | Enter: save | Q: quit",
                (10, dh - 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.38, (160, 160, 160), 1)

    return canvas


# ── Main ────────────────────────────────────────────────────────────

def main():
    template = cv2.imread(DEFAULT_TEMPLATE)
    if template is None:
        print(f"ERROR: Cannot load template: {DEFAULT_TEMPLATE}")
        print("Run from the project root directory.")
        sys.exit(1)

    th, tw = template.shape[:2]
    print(f"Template: {tw}x{th}")

    cal = load_calibration()
    top_x = cal["top_x"]
    top_y = cal["top_y"]
    thw = cal["tile_half_w"]
    thh = cal["tile_half_h"]

    # Display scale — fit in ~1200px wide window
    disp_scale = min(1200 / tw, 900 / th)

    show_full_grid = True
    show_buildable = True

    dragging = False
    drag_start = (0, 0)
    drag_top_x0 = top_x
    drag_top_y0 = top_y

    win_name = "Grid Calibrator"
    cv2.namedWindow(win_name, cv2.WINDOW_AUTOSIZE)

    def on_mouse(event, x, y, flags, param):
        nonlocal dragging, drag_start, drag_top_x0, drag_top_y0
        nonlocal top_x, top_y

        if event == cv2.EVENT_LBUTTONDOWN:
            dragging = True
            drag_start = (x, y)
            drag_top_x0 = top_x
            drag_top_y0 = top_y

        elif event == cv2.EVENT_MOUSEMOVE and dragging:
            dx = (x - drag_start[0]) / disp_scale
            dy = (y - drag_start[1]) / disp_scale
            top_x = drag_top_x0 + dx
            top_y = drag_top_y0 + dy

        elif event == cv2.EVENT_LBUTTONUP:
            dragging = False

    cv2.setMouseCallback(win_name, on_mouse)

    print(f"Grid Calibrator — {GRID_SIZE}x{GRID_SIZE} tiles")
    print(f"Arrows: move anchor | W/S: tile_hw | A/D: tile_hh")
    print(f"G: toggle grid | B: toggle buildable | Enter: save | Q: quit")

    while True:
        frame = render_frame(template, top_x, top_y, thw, thh, disp_scale,
                             show_full_grid, show_buildable)
        cv2.imshow(win_name, frame)
        key = cv2.waitKey(30) & 0xFF

        # Check for shift (we can't reliably detect shift with waitKey,
        # so we use uppercase letters for coarse adjustment)
        fine_move = 0.5
        coarse_move = 5.0
        fine_tile = 0.01
        coarse_tile = 0.1

        if key == ord('q'):
            cal = {"top_x": round(top_x, 1), "top_y": round(top_y, 1),
                   "tile_half_w": round(thw, 2), "tile_half_h": round(thh, 2)}
            save_calibration(cal)
            print(f"Saved: {cal}")
            break

        elif key == 13 or key == ord(' '):  # Enter or Space
            cal = {"top_x": round(top_x, 1), "top_y": round(top_y, 1),
                   "tile_half_w": round(thw, 2), "tile_half_h": round(thh, 2)}
            save_calibration(cal)
            print(f"Saved: {cal}")

        elif key == ord('r'):
            top_x, top_y = DEF_TOP_X, DEF_TOP_Y
            thw, thh = DEF_TILE_HW, DEF_TILE_HH
            print("Reset to defaults")

        elif key == ord('g'):
            show_full_grid = not show_full_grid

        elif key == ord('b'):
            show_buildable = not show_buildable

        # Tile half-width: w/s (fine), W/S (coarse)
        elif key == ord('w'):
            thw += fine_tile
        elif key == ord('W'):
            thw += coarse_tile
        elif key == ord('s'):
            thw = max(1.0, thw - fine_tile)
        elif key == ord('S'):
            thw = max(1.0, thw - coarse_tile)

        # Tile half-height: a/d (fine), A/D (coarse)
        elif key == ord('d'):
            thh += fine_tile
        elif key == ord('D'):
            thh += coarse_tile
        elif key == ord('a'):
            thh = max(1.0, thh - fine_tile)
        elif key == ord('A'):
            thh = max(1.0, thh - coarse_tile)

        # Arrow keys (macOS key codes)
        elif key == 0 or key == 82:  # Up
            top_y -= fine_move
        elif key == 1 or key == 84:  # Down
            top_y += fine_move
        elif key == 2 or key == 81:  # Left
            top_x -= fine_move
        elif key == 3 or key == 83:  # Right
            top_x += fine_move

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
