#!/usr/bin/env python3
"""
Base Editor GUI — interactively place and resize building sprites
on the isometric grid over the empty base template.

Each building sits on a green-filled tile diamond. Click to select,
drag to move, scroll to resize, right-click to delete.

Controls:
  Left click:        select building / drag to move
  Scroll wheel:      resize selected building's scale
  Right click:       delete building under cursor
  1-4:               set brush tile size (1x1, 2x2, 3x3, 4x4)
  B:                 open building picker (cycles through types)
  Tab:               cycle to next building type in picker
  G:                 toggle grid overlay
  T:                 toggle green tile diamonds
  Enter:             save layout
  Z:                 undo last action
  C:                 clear all buildings
  Q:                 save and quit

  Left panel shows building palette — click to select type.
"""

import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from training.generate.building_tiles import BUILDING_TILES
from training.generate.base_builder import IsometricGrid, BUILDABLE_MIN, BUILDABLE_MAX

# ── Config ──────────────────────────────────────────────────────────

TEMPLATE_PATH = "data/templates/base/empty_base.jpg"
CALIBRATION_FILE = "data/calibration/grid_calibration.json"
SCALES_FILE = "data/calibration/sprite_scales.json"
LAYOUT_FILE = "data/calibration/base_layout.json"
SPRITES_DIR = "data/sprites"

# Display
PALETTE_W = 200
MIN_WIN_W = 1000
MIN_WIN_H = 700

# Tile diamond colors
TILE_FILL_COLOR = (40, 120, 40)      # green fill
TILE_OUTLINE_COLOR = (60, 180, 60)   # green outline
SELECTED_COLOR = (0, 200, 255)       # yellow for selected
GRID_COLOR = (0, 100, 100)           # subtle cyan grid


# ── Grid calibration ────────────────────────────────────────────────

def load_grid_calibration():
    p = Path(CALIBRATION_FILE)
    if p.exists():
        with open(p) as f:
            return json.load(f)
    return {"top_x": 1012.5, "top_y": 137.6, "tile_half_w": 17.38, "tile_half_h": 12.95}


# ── Sprite loading ──────────────────────────────────────────────────

def load_sprite_scales():
    p = Path(SCALES_FILE)
    if p.exists():
        with open(p) as f:
            raw = json.load(f)
        result = {}
        for name, cfg in raw.items():
            if isinstance(cfg, (int, float)):
                result[name] = {"scale": cfg, "ox": 0, "oy": 0}
            else:
                result[name] = {
                    "scale": cfg.get("scale", 1.0),
                    "ox": cfg.get("ox", 0),
                    "oy": cfg.get("oy", 0),
                }
        return result
    return {}


def measure_base_width(img_bgra):
    h, w = img_bgra.shape[:2]
    alpha = img_bgra[:, :, 3]
    bottom_start = int(h * 0.65)
    bottom_alpha = alpha[bottom_start:, :]
    col_has_pixels = np.any(bottom_alpha > 30, axis=0)
    if not col_has_pixels.any():
        return w
    cols = np.where(col_has_pixels)[0]
    return cols[-1] - cols[0] + 1


def load_all_sprites():
    """Load all sprites grouped by building type.
    Returns {btype: [{name, image, level, base_w, cal_scale, cal_ox, cal_oy}, ...]}
    """
    sprites_dir = Path(SPRITES_DIR)
    scales = load_sprite_scales()
    sprites = {}

    for png in sorted(sprites_dir.rglob("*.png")):
        if png.name.startswith("._"):
            continue

        # Determine building type from folder name
        btype = png.parent.name
        if btype not in BUILDING_TILES:
            continue

        img = cv2.imread(str(png), cv2.IMREAD_UNCHANGED)
        if img is None or len(img.shape) < 3 or img.shape[2] != 4:
            continue

        level_str = png.stem.rsplit("_", 1)[-1]
        level = int(level_str) if level_str.isdigit() else 0

        cal = scales.get(png.stem, {})

        if btype not in sprites:
            sprites[btype] = []

        sprites[btype].append({
            "name": png.stem,
            "image": img,
            "level": level,
            "base_w": measure_base_width(img),
            "cal_scale": cal.get("scale", 1.0),
            "cal_ox": cal.get("ox", 0),
            "cal_oy": cal.get("oy", 0),
        })

    # Sort each type by level descending
    for btype in sprites:
        sprites[btype].sort(key=lambda s: s["level"], reverse=True)

    return sprites


# ── Placed building ─────────────────────────────────────────────────

class PlacedBuilding:
    def __init__(self, btype, tx, ty, sprite_data, scale_override=None):
        self.btype = btype
        self.tx = tx
        self.ty = ty
        self.tile_size = BUILDING_TILES.get(btype, 3)
        self.sprite = sprite_data
        self.scale_override = scale_override  # extra scale on top of calibration

    def occupied_tiles(self):
        tiles = set()
        for dx in range(self.tile_size):
            for dy in range(self.tile_size):
                tiles.add((self.tx + dx, self.ty + dy))
        return tiles


# ── Layout save/load ────────────────────────────────────────────────

def save_layout(buildings):
    data = []
    for b in buildings:
        data.append({
            "btype": b.btype,
            "tx": b.tx,
            "ty": b.ty,
            "sprite_name": b.sprite["name"],
            "scale_override": b.scale_override,
        })
    Path(LAYOUT_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(LAYOUT_FILE, "w") as f:
        json.dump(data, f, indent=2)
    return len(data)


def load_layout(all_sprites):
    p = Path(LAYOUT_FILE)
    if not p.exists():
        return []

    with open(p) as f:
        data = json.load(f)

    buildings = []
    for entry in data:
        btype = entry["btype"]
        if btype not in all_sprites:
            continue
        # Find matching sprite
        sprite = None
        for s in all_sprites[btype]:
            if s["name"] == entry.get("sprite_name"):
                sprite = s
                break
        if sprite is None:
            sprite = all_sprites[btype][0]

        b = PlacedBuilding(btype, entry["tx"], entry["ty"], sprite,
                           entry.get("scale_override"))
        buildings.append(b)

    return buildings


# ── Rendering ───────────────────────────────────────────────────────

class BaseEditor:
    def __init__(self):
        self.template = cv2.imread(TEMPLATE_PATH)
        if self.template is None:
            print(f"ERROR: Cannot load {TEMPLATE_PATH}")
            sys.exit(1)

        self.tmpl_h, self.tmpl_w = self.template.shape[:2]

        cal = load_grid_calibration()
        self.grid = IsometricGrid(self.tmpl_w, self.tmpl_h)

        self.all_sprites = load_all_sprites()
        print(f"Loaded {sum(len(v) for v in self.all_sprites.values())} sprites "
              f"from {len(self.all_sprites)} types")

        # Build sorted type list for palette
        self.type_list = sorted(self.all_sprites.keys(),
                                key=lambda t: (BUILDING_TILES.get(t, 3), t))

        self.buildings: list[PlacedBuilding] = load_layout(self.all_sprites)
        self.undo_stack: list[list[dict]] = []
        self.selected_idx = -1
        self.selected_type_idx = 0
        self.selected_level_idx = 0  # index into sprite variants

        # Display
        self.disp_scale = min(
            (MIN_WIN_W - PALETTE_W) / self.tmpl_w,
            MIN_WIN_H / self.tmpl_h,
        )
        self.canvas_w = int(self.tmpl_w * self.disp_scale)
        self.canvas_h = int(self.tmpl_h * self.disp_scale)

        self.show_grid = True
        self.show_tiles = True

        # Drag state
        self.dragging = False
        self.drag_offset = (0, 0)

        # Hover tile
        self.hover_tx = -1
        self.hover_ty = -1

    def _push_undo(self):
        """Save current state for undo."""
        state = []
        for b in self.buildings:
            state.append({
                "btype": b.btype, "tx": b.tx, "ty": b.ty,
                "sprite_name": b.sprite["name"],
                "scale_override": b.scale_override,
            })
        self.undo_stack.append(state)
        if len(self.undo_stack) > 50:
            self.undo_stack.pop(0)

    def _pop_undo(self):
        if not self.undo_stack:
            return
        state = self.undo_stack.pop()
        self.buildings.clear()
        for entry in state:
            btype = entry["btype"]
            if btype not in self.all_sprites:
                continue
            sprite = None
            for s in self.all_sprites[btype]:
                if s["name"] == entry["sprite_name"]:
                    sprite = s
                    break
            if sprite is None:
                sprite = self.all_sprites[btype][0]
            self.buildings.append(PlacedBuilding(
                btype, entry["tx"], entry["ty"], sprite,
                entry.get("scale_override")))
        self.selected_idx = -1

    def screen_to_tile(self, sx, sy):
        """Convert display pixel coords to tile coords."""
        # Undo display scale
        px = sx / self.disp_scale
        py = sy / self.disp_scale

        # Inverse of tile_to_screen:
        # px = top_x + tx * thw - ty * thw
        # py = top_y + tx * thh + ty * thh
        g = self.grid
        dx = px - g.top_x
        dy = py - g.top_y

        # Solve: dx = (tx - ty) * thw, dy = (tx + ty) * thh
        if g.thw == 0 or g.thh == 0:
            return 0, 0
        tx = (dx / g.thw + dy / g.thh) / 2
        ty = (dy / g.thh - dx / g.thw) / 2
        return tx, ty

    def tile_to_display(self, tx, ty):
        """Convert tile coords to display pixel coords."""
        sx, sy = self.grid.tile_to_screen(tx, ty)
        return int(sx * self.disp_scale), int(sy * self.disp_scale)

    def find_building_at_tile(self, tx, ty):
        """Find building index whose tile footprint contains (tx, ty)."""
        itx, ity = int(tx), int(ty)
        for i in range(len(self.buildings) - 1, -1, -1):
            b = self.buildings[i]
            if (b.tx <= itx < b.tx + b.tile_size and
                b.ty <= ity < b.ty + b.tile_size):
                return i
        return -1

    def _current_btype(self):
        return self.type_list[self.selected_type_idx % len(self.type_list)]

    def _current_sprite(self):
        btype = self._current_btype()
        variants = self.all_sprites[btype]
        idx = self.selected_level_idx % len(variants)
        return variants[idx]

    def draw_tile_diamond(self, canvas, tx, ty, size, fill_color, outline_color, thickness=1):
        """Draw an NxN tile diamond with fill and outline."""
        top = self.tile_to_display(tx, ty)
        right = self.tile_to_display(tx + size, ty)
        bottom = self.tile_to_display(tx + size, ty + size)
        left = self.tile_to_display(tx, ty + size)
        pts = np.array([top, right, bottom, left], dtype=np.int32)

        if fill_color is not None:
            overlay = canvas.copy()
            cv2.fillPoly(overlay, [pts], fill_color)
            cv2.addWeighted(overlay, 0.35, canvas, 0.65, 0, canvas)

        cv2.polylines(canvas, [pts], True, outline_color, thickness, cv2.LINE_AA)

    def render_sprite(self, canvas, building):
        """Render a single building sprite onto the canvas."""
        spr = building.sprite
        ts = building.tile_size
        g = self.grid

        scr_x, scr_y = g.tile_to_screen(
            building.tx + ts / 2, building.ty + ts / 2)

        img = spr["image"]
        sh, sw = img.shape[:2]
        dw = g.diamond_width(ts)
        game_scale = dw / spr["base_w"] * spr["cal_scale"]
        if building.scale_override is not None:
            game_scale *= building.scale_override
        full_scale = game_scale * self.disp_scale

        nw = max(4, int(sw * full_scale))
        nh = max(4, int(sh * full_scale))
        scaled = cv2.resize(img, (nw, nh),
                            interpolation=cv2.INTER_AREA if full_scale < 1 else cv2.INTER_LINEAR)

        dh = g.diamond_height(ts)
        diamond_bottom = int((scr_y + dh / 2) * self.disp_scale)
        pcx = int(scr_x * self.disp_scale) + int(spr["cal_ox"] * self.disp_scale)
        pcy = diamond_bottom - nh // 2 + int(spr["cal_oy"] * self.disp_scale)

        px, py = pcx - nw // 2, pcy - nh // 2
        ch, cw = canvas.shape[:2]
        x1, y1 = max(0, px), max(0, py)
        x2, y2 = min(cw, px + nw), min(ch, py + nh)
        if x2 > x1 and y2 > y1:
            sx1, sy1 = x1 - px, y1 - py
            region = scaled[sy1:sy1 + (y2 - y1), sx1:sx1 + (x2 - x1)]
            a = region[:, :, 3:4].astype(np.float32) / 255.0
            b = region[:, :, :3]
            dst = canvas[y1:y2, x1:x2]
            canvas[y1:y2, x1:x2] = (
                b.astype(np.float32) * a +
                dst.astype(np.float32) * (1 - a)
            ).astype(np.uint8)

    def render(self):
        """Render the full editor frame."""
        # Resize template
        canvas = cv2.resize(self.template, (self.canvas_w, self.canvas_h),
                            interpolation=cv2.INTER_AREA)

        # Grid overlay
        if self.show_grid:
            for i in range(0, 45, 2):  # Every other line for performance
                p1 = self.tile_to_display(i, 0)
                p2 = self.tile_to_display(i, 44)
                cv2.line(canvas, p1, p2, GRID_COLOR, 1, cv2.LINE_AA)
                p1 = self.tile_to_display(0, i)
                p2 = self.tile_to_display(44, i)
                cv2.line(canvas, p1, p2, GRID_COLOR, 1, cv2.LINE_AA)

        # Sort buildings back-to-front for rendering
        sorted_indices = sorted(range(len(self.buildings)),
                                key=lambda i: self.buildings[i].ty + self.buildings[i].tx)

        for idx in sorted_indices:
            b = self.buildings[idx]

            # Draw green tile diamond under building
            if self.show_tiles:
                is_selected = (idx == self.selected_idx)
                fill = TILE_FILL_COLOR
                outline = SELECTED_COLOR if is_selected else TILE_OUTLINE_COLOR
                thick = 2 if is_selected else 1
                self.draw_tile_diamond(canvas, b.tx, b.ty, b.tile_size,
                                       fill, outline, thick)

            # Draw sprite
            self.render_sprite(canvas, b)

        # Hover tile preview (ghost of current brush)
        if 0 <= self.hover_tx <= 40 and 0 <= self.hover_ty <= 40:
            btype = self._current_btype()
            ts = BUILDING_TILES.get(btype, 3)
            self.draw_tile_diamond(canvas, int(self.hover_tx), int(self.hover_ty),
                                   ts, None, (100, 200, 255), 1)

        # ── Side palette ──
        palette = np.full((self.canvas_h, PALETTE_W, 3), (30, 30, 30), dtype=np.uint8)

        # Title
        cv2.putText(palette, "Buildings", (10, 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # Current selection info
        btype = self._current_btype()
        ts = BUILDING_TILES.get(btype, 3)
        spr = self._current_sprite()
        cv2.putText(palette, f"> {btype}", (10, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 200), 1)
        cv2.putText(palette, f"  {ts}x{ts} | {spr['name']}", (10, 68),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (180, 180, 180), 1)

        # List building types (scrollable region)
        y_start = 90
        visible = (self.canvas_h - y_start - 100) // 16
        scroll_offset = max(0, self.selected_type_idx - visible // 2)

        for i in range(scroll_offset, min(len(self.type_list), scroll_offset + visible)):
            t = self.type_list[i]
            ts_i = BUILDING_TILES.get(t, 3)
            y = y_start + (i - scroll_offset) * 16
            color = (0, 255, 200) if i == self.selected_type_idx else (150, 150, 150)
            prefix = ">" if i == self.selected_type_idx else " "
            cv2.putText(palette, f"{prefix} {t} ({ts_i})", (5, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.32, color, 1)

        # Bottom HUD
        hud_y = self.canvas_h - 80
        cv2.line(palette, (0, hud_y - 5), (PALETTE_W, hud_y - 5), (80, 80, 80), 1)
        cv2.putText(palette, f"Placed: {len(self.buildings)}", (10, hud_y + 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

        if self.selected_idx >= 0:
            sb = self.buildings[self.selected_idx]
            so = sb.scale_override or 1.0
            cv2.putText(palette, f"Sel: {sb.sprite['name']}", (10, hud_y + 28),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 200), 1)
            cv2.putText(palette, f"Scale: {so:.2f}", (10, hud_y + 44),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 200, 200), 1)
        else:
            cv2.putText(palette, "Click grid to place", (10, hud_y + 28),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, (120, 120, 120), 1)

        cv2.putText(palette, "Tab:type Scroll:size G:grid T:tiles", (5, hud_y + 65),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.28, (100, 100, 100), 1)
        cv2.putText(palette, "Z:undo Enter:save Q:quit", (5, hud_y + 78),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.28, (100, 100, 100), 1)

        # Combine
        frame = np.hstack([canvas, palette])
        return frame

    def run(self):
        win = "Base Editor"
        cv2.namedWindow(win, cv2.WINDOW_AUTOSIZE)

        def on_mouse(event, x, y, flags, param):
            # Only handle clicks on the canvas area (not palette)
            on_canvas = x < self.canvas_w

            if on_canvas:
                tx, ty = self.screen_to_tile(x, y)
                self.hover_tx = tx
                self.hover_ty = ty
            else:
                self.hover_tx = -1
                self.hover_ty = -1

                # Palette click — select building type
                if event == cv2.EVENT_LBUTTONDOWN:
                    y_start = 90
                    visible = (self.canvas_h - y_start - 100) // 16
                    scroll_offset = max(0, self.selected_type_idx - visible // 2)
                    row = (y - y_start) // 16 + scroll_offset
                    if 0 <= row < len(self.type_list):
                        self.selected_type_idx = row
                        self.selected_level_idx = 0
                return

            if event == cv2.EVENT_LBUTTONDOWN and on_canvas:
                tx, ty = self.screen_to_tile(x, y)
                hit = self.find_building_at_tile(tx, ty)

                if hit >= 0:
                    # Select existing building
                    self.selected_idx = hit
                    b = self.buildings[hit]
                    self.dragging = True
                    self.drag_offset = (tx - b.tx, ty - b.ty)
                else:
                    # Place new building
                    itx, ity = int(tx), int(ty)
                    btype = self._current_btype()
                    spr = self._current_sprite()
                    self._push_undo()
                    b = PlacedBuilding(btype, itx, ity, spr)
                    self.buildings.append(b)
                    self.selected_idx = len(self.buildings) - 1

            elif event == cv2.EVENT_MOUSEMOVE and self.dragging:
                if self.selected_idx >= 0:
                    tx, ty = self.screen_to_tile(x, y)
                    b = self.buildings[self.selected_idx]
                    new_tx = int(tx - self.drag_offset[0])
                    new_ty = int(ty - self.drag_offset[1])
                    if b.tx != new_tx or b.ty != new_ty:
                        if not hasattr(self, '_drag_undo_pushed'):
                            self._push_undo()
                            self._drag_undo_pushed = True
                        b.tx = new_tx
                        b.ty = new_ty

            elif event == cv2.EVENT_LBUTTONUP:
                self.dragging = False
                if hasattr(self, '_drag_undo_pushed'):
                    del self._drag_undo_pushed

            elif event == cv2.EVENT_RBUTTONDOWN and on_canvas:
                tx, ty = self.screen_to_tile(x, y)
                hit = self.find_building_at_tile(tx, ty)
                if hit >= 0:
                    self._push_undo()
                    self.buildings.pop(hit)
                    if self.selected_idx == hit:
                        self.selected_idx = -1
                    elif self.selected_idx > hit:
                        self.selected_idx -= 1

            elif event == cv2.EVENT_MOUSEWHEEL and on_canvas:
                if self.selected_idx >= 0:
                    b = self.buildings[self.selected_idx]
                    so = b.scale_override or 1.0
                    if flags > 0:
                        so += 0.03
                    else:
                        so = max(0.2, so - 0.03)
                    b.scale_override = round(so, 3)

        cv2.setMouseCallback(win, on_mouse)

        print(f"Base Editor — {len(self.buildings)} buildings loaded")
        print("Click to place, drag to move, scroll to resize, right-click to delete")

        while True:
            frame = self.render()
            cv2.imshow(win, frame)
            key = cv2.waitKey(30) & 0xFF

            if key == ord('q'):
                n = save_layout(self.buildings)
                print(f"Saved {n} buildings to {LAYOUT_FILE}")
                break

            elif key == 13:  # Enter
                n = save_layout(self.buildings)
                print(f"Saved {n} buildings to {LAYOUT_FILE}")

            elif key == ord('g'):
                self.show_grid = not self.show_grid

            elif key == ord('t'):
                self.show_tiles = not self.show_tiles

            elif key == ord('z'):
                self._pop_undo()

            elif key == ord('c'):
                self._push_undo()
                self.buildings.clear()
                self.selected_idx = -1
                print("Cleared all buildings")

            elif key == 9:  # Tab — next building type
                self.selected_type_idx = (self.selected_type_idx + 1) % len(self.type_list)
                self.selected_level_idx = 0

            elif key == ord('`'):  # backtick — prev building type
                self.selected_type_idx = (self.selected_type_idx - 1) % len(self.type_list)
                self.selected_level_idx = 0

            elif key == ord('l'):  # L — cycle level variant
                btype = self._current_btype()
                variants = self.all_sprites[btype]
                self.selected_level_idx = (self.selected_level_idx + 1) % len(variants)

            elif key == ord('1'):
                # Find first 1x1 type
                for i, t in enumerate(self.type_list):
                    if BUILDING_TILES.get(t) == 1:
                        self.selected_type_idx = i
                        break
            elif key == ord('2'):
                for i, t in enumerate(self.type_list):
                    if BUILDING_TILES.get(t) == 2:
                        self.selected_type_idx = i
                        break
            elif key == ord('3'):
                for i, t in enumerate(self.type_list):
                    if BUILDING_TILES.get(t) == 3:
                        self.selected_type_idx = i
                        break
            elif key == ord('4'):
                for i, t in enumerate(self.type_list):
                    if BUILDING_TILES.get(t) == 4:
                        self.selected_type_idx = i
                        break

            # Delete selected with backspace/delete
            elif key == 8 or key == 127:
                if self.selected_idx >= 0:
                    self._push_undo()
                    self.buildings.pop(self.selected_idx)
                    self.selected_idx = -1

            # Deselect with Escape
            elif key == 27:
                self.selected_idx = -1

        cv2.destroyAllWindows()


if __name__ == "__main__":
    editor = BaseEditor()
    editor.run()
