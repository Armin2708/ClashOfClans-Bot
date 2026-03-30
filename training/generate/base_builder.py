#!/usr/bin/env python3
"""
Synthetic base builder — generates realistic CoC base images on the
empty base template with perfect YOLO bounding box labels.

Each building is placed on the isometric grid at its correct NxN tile
footprint. Sprites are scaled so their width matches the isometric
diamond width of their tile footprint.

Usage:
    python -m training.base_builder --count 1000
    python -m training.base_builder --count 500 --preview
    python -m training.base_builder --count 2000 --img-size 640
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import cv2
import numpy as np

from training.generate.building_tiles import BUILDING_TILES, TH15_COMPOSITION

# ── Template calibration ────────────────────────────────────────────
# Values loaded from training/grid_calibration.json if available,
# otherwise using hardcoded defaults. Run tools/grid_calibrator.py
# to visually calibrate the grid to the empty base template.

_GRID_CAL_FILE = Path("data/calibration/grid_calibration.json")

_REF_W = 2000
_REF_H = 1500

if _GRID_CAL_FILE.exists():
    with open(_GRID_CAL_FILE) as _f:
        _cal = json.load(_f)
    _REF_TOP_X = _cal["top_x"]
    _REF_TOP_Y = _cal["top_y"]
    _REF_TILE_HW = _cal["tile_half_w"]
    _REF_TILE_HH = _cal["tile_half_h"]
else:
    _REF_TOP_X = 1012.5
    _REF_TOP_Y = 137.6
    _REF_TILE_HW = 17.38
    _REF_TILE_HH = 12.95

DEFAULT_TEMPLATE = "data/templates/base/empty_base.jpg"

# ── Grid constants ──────────────────────────────────────────────────

GRID_SIZE = 44
BUILDABLE_MIN = 0       # entire 44x44 grid is placeable
BUILDABLE_MAX = 43      # GRID_SIZE - 1

# BUILDING_TILES and TH15_COMPOSITION imported from training.generate.building_tiles
# (single source of truth for all tile footprint sizes)


# ── Isometric grid ──────────────────────────────────────────────────

class IsometricGrid:
    """44x44 isometric tile grid calibrated to the empty base template.

    The grid is anchored at the top corner (tile 0,0). Each tile step
    in the X direction moves (+thw, +thh) on screen. Each tile step
    in the Y direction moves (-thw, +thh) on screen.
    """

    def __init__(self, screen_w: int, screen_h: int):
        self.screen_w = screen_w
        self.screen_h = screen_h

        sx = screen_w / _REF_W
        sy = screen_h / _REF_H

        # Top corner of the diamond in screen pixels
        self.top_x = _REF_TOP_X * sx
        self.top_y = _REF_TOP_Y * sy

        # Pixel offset per tile in each isometric axis
        self.thw = _REF_TILE_HW * sx  # x-step per tile-X / negative x-step per tile-Y
        self.thh = _REF_TILE_HH * sy  # y-step per tile (both axes go down)

        self._occupied: set[tuple[int, int]] = set()

    def tile_to_screen(self, tx: float, ty: float) -> tuple[int, int]:
        """Convert tile coords to screen pixel coords.

        tile(0,0) = top corner of the diamond.
        +X goes screen-right and screen-down.
        +Y goes screen-left and screen-down.
        """
        sx = self.top_x + tx * self.thw - ty * self.thw
        sy = self.top_y + tx * self.thh + ty * self.thh
        return int(sx), int(sy)

    def diamond_width(self, tile_size: int) -> float:
        """Screen pixel width of an NxN tile diamond."""
        return tile_size * self.thw * 2

    def diamond_height(self, tile_size: int) -> float:
        """Screen pixel height of an NxN tile diamond."""
        return tile_size * self.thh * 2

    def can_place(self, tx: int, ty: int, size: int) -> bool:
        for dx in range(size):
            for dy in range(size):
                gx, gy = tx + dx, ty + dy
                if gx < BUILDABLE_MIN or gx > BUILDABLE_MAX:
                    return False
                if gy < BUILDABLE_MIN or gy > BUILDABLE_MAX:
                    return False
                if (gx, gy) in self._occupied:
                    return False
        return True

    def place(self, tx: int, ty: int, size: int):
        for dx in range(size):
            for dy in range(size):
                self._occupied.add((tx + dx, ty + dy))

    def find_position(self, size: int, attempts: int = 100) -> tuple[int, int] | None:
        hi = BUILDABLE_MAX - size + 1
        for _ in range(attempts):
            tx = random.randint(BUILDABLE_MIN, hi)
            ty = random.randint(BUILDABLE_MIN, hi)
            if self.can_place(tx, ty, size):
                return tx, ty
        return None


# ── Sprite loading ───────────────────────────────────────────────────

def _get_building_type(filename: str) -> str:
    """'cannon_15' → 'cannon', 'archer_tower_geared_12' → 'archer_tower_geared'."""
    parts = filename.rsplit("_", 1)
    if len(parts) == 2 and parts[1].isdigit():
        return parts[0]
    return filename


def _load_sprite_scales() -> dict[str, dict]:
    """Load calibrated sprite scales from sprite_scales.json."""
    scales_file = Path("data/calibration/sprite_scales.json")
    if scales_file.exists():
        with open(scales_file) as f:
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


def _measure_base_width(img_bgra: np.ndarray) -> int:
    """Measure the width of the building's base footprint from the bottom portion."""
    h, w = img_bgra.shape[:2]
    alpha = img_bgra[:, :, 3]
    bottom_start = int(h * 0.65)
    bottom_alpha = alpha[bottom_start:, :]
    col_has_pixels = np.any(bottom_alpha > 30, axis=0)
    if not col_has_pixels.any():
        return w
    cols = np.where(col_has_pixels)[0]
    return cols[-1] - cols[0] + 1


def load_sprites(sprite_dir: Path) -> dict[str, list[dict]]:
    """Load sprites grouped by building type.
    Returns {building_type: [{name, image, level, base_w, cal_scale, cal_ox, cal_oy}, ...]}."""
    sprites: dict[str, list[dict]] = {}
    sprite_scales = _load_sprite_scales()

    for png in sorted(sprite_dir.rglob("*.png")):
        if png.name.startswith("._"):
            continue

        btype = _get_building_type(png.stem)
        if btype not in BUILDING_TILES:
            folder = png.parent.name
            if folder in BUILDING_TILES:
                btype = folder
            else:
                continue

        img = cv2.imread(str(png), cv2.IMREAD_UNCHANGED)
        if img is None:
            continue

        # Ensure BGRA
        if len(img.shape) == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGRA)
        elif img.shape[2] == 3:
            alpha = np.full(img.shape[:2], 255, dtype=np.uint8)
            img = np.dstack([img, alpha])

        if btype not in sprites:
            sprites[btype] = []

        level_str = png.stem.rsplit("_", 1)[-1]
        level = int(level_str) if level_str.isdigit() else 0

        cal = sprite_scales.get(png.stem, {})

        sprites[btype].append({
            "name": png.stem,
            "image": img,
            "level": level,
            "base_w": _measure_base_width(img),
            "cal_scale": cal.get("scale", 1.0),
            "cal_ox": cal.get("ox", 0),
            "cal_oy": cal.get("oy", 0),
        })

    return sprites


# ── Compositing ──────────────────────────────────────────────────────

def _scale_sprite_to_footprint(
    sprite_bgra: np.ndarray,
    tile_size: int,
    grid: IsometricGrid,
    base_w: int,
    cal_scale: float = 1.0,
) -> np.ndarray:
    """Scale a sprite using its calibrated base_w and scale factor.

    The calibrated scale was set so the sprite visually fits its
    isometric diamond tile. base_w is the measured footprint width
    of the sprite, and cal_scale is the manual correction factor.
    """
    diamond_w = grid.diamond_width(tile_size)
    # game_scale maps the sprite's base footprint to the diamond width,
    # then cal_scale applies the manual correction from the calibrator
    game_scale = diamond_w / base_w * cal_scale
    # Tiny jitter for visual variety
    game_scale *= random.uniform(0.97, 1.03)

    h_orig, w_orig = sprite_bgra.shape[:2]
    new_w = max(6, int(w_orig * game_scale))
    new_h = max(6, int(h_orig * game_scale))

    interp = cv2.INTER_AREA if game_scale < 1.0 else cv2.INTER_LINEAR
    return cv2.resize(sprite_bgra, (new_w, new_h), interpolation=interp)


def _paste_sprite(
    canvas: np.ndarray,
    sprite_bgra: np.ndarray,
    cx: int, cy: int,
) -> tuple[int, int, int, int]:
    """Alpha-blend a BGRA sprite onto BGR canvas centered at (cx, cy).
    Returns tight (x1, y1, x2, y2) bounding box of visible pixels."""

    hs, ws = sprite_bgra.shape[:2]
    hc, wc = canvas.shape[:2]

    x, y = cx - ws // 2, cy - hs // 2
    x1, y1 = max(0, x), max(0, y)
    x2, y2 = min(wc, x + ws), min(hc, y + hs)
    if x2 <= x1 or y2 <= y1:
        return (0, 0, 0, 0)

    sx1, sy1 = x1 - x, y1 - y
    sx2, sy2 = sx1 + (x2 - x1), sy1 + (y2 - y1)

    region = sprite_bgra[sy1:sy2, sx1:sx2]
    alpha = region[:, :, 3:4].astype(np.float32) / 255.0
    bgr = region[:, :, :3]

    dst = canvas[y1:y2, x1:x2]
    canvas[y1:y2, x1:x2] = (
        bgr.astype(np.float32) * alpha +
        dst.astype(np.float32) * (1.0 - alpha)
    ).astype(np.uint8)

    # Tight bbox from opaque pixels
    mask = region[:, :, 3] > 30
    if not mask.any():
        return (0, 0, 0, 0)
    rows = np.any(mask, axis=1)
    cols = np.any(mask, axis=0)
    rmin, rmax = np.where(rows)[0][[0, -1]]
    cmin, cmax = np.where(cols)[0][[0, -1]]
    return (x1 + cmin, y1 + rmin, x1 + cmax + 1, y1 + rmax + 1)


# ── Base generation ──────────────────────────────────────────────────

def _pick_composition() -> list[tuple[str, int]]:
    result = []
    for btype, (lo, hi) in TH15_COMPOSITION.items():
        n = random.randint(lo, hi)
        if n > 0:
            result.append((btype, n))
    return result


def generate_base(
    sprites: dict[str, list[dict]],
    template: np.ndarray,
) -> tuple[np.ndarray, list[dict]]:
    """Generate one synthetic base on the template.

    Returns (bgr_image, annotations) where annotations are:
        [{"class_name": str, "class_name_base": str,
          "cx": float, "cy": float, "nw": float, "nh": float}, ...]
    """
    h, w = template.shape[:2]
    canvas = template.copy()
    grid = IsometricGrid(w, h)
    annotations = []

    composition = _pick_composition()
    # Place large buildings first → better packing
    composition.sort(key=lambda x: BUILDING_TILES.get(x[0], 3), reverse=True)

    # First pass: assign grid positions for all buildings
    placements: list[tuple[str, int, int, int, dict]] = []  # (btype, tx, ty, tile_size, sprite_data)

    for btype, count in composition:
        if btype == "wall":
            continue

        tile_size = BUILDING_TILES.get(btype, 3)
        if btype not in sprites:
            continue
        available = sprites[btype]

        for _ in range(count):
            pos = grid.find_position(tile_size)
            if pos is None:
                break

            tx, ty = pos
            grid.place(tx, ty, tile_size)
            spr = random.choice(available)
            placements.append((btype, tx, ty, tile_size, spr))

    # Second pass: render back-to-front (sort by ty+tx so buildings
    # closer to the camera (higher ty) are drawn on top)
    placements.sort(key=lambda p: p[2] + p[1])

    for btype, tx, ty, tile_size, spr in placements:
        # Screen position: center of the NxN tile diamond
        scr_x, scr_y = grid.tile_to_screen(
            tx + tile_size / 2,
            ty + tile_size / 2,
        )

        scaled = _scale_sprite_to_footprint(
            spr["image"], tile_size, grid,
            base_w=spr["base_w"],
            cal_scale=spr["cal_scale"],
        )

        # Buildings rise above their footprint in isometric view.
        # Anchor the sprite so its bottom edge aligns with the
        # bottom corner of the tile diamond, then apply calibrated offset.
        sprite_h = scaled.shape[0]
        diamond_h = grid.diamond_height(tile_size)
        # Bottom of diamond is at scr_y + diamond_h/2
        # Bottom of sprite should be there → sprite center_y = bottom - sprite_h/2
        paste_y = int(scr_y + diamond_h / 2 - sprite_h / 2)

        # Apply calibrated pixel offsets
        paste_x_adj = scr_x + int(spr["cal_ox"])
        paste_y_adj = paste_y + int(spr["cal_oy"])

        bbox = _paste_sprite(canvas, scaled, paste_x_adj, paste_y_adj)
        bx1, by1, bx2, by2 = bbox
        if bx2 <= bx1 or by2 <= by1:
            continue

        bw, bh = bx2 - bx1, by2 - by1
        if bw < 4 or bh < 4:
            continue

        annotations.append({
            "class_name": spr["name"],
            "class_name_base": btype,
            "cx": max(0.001, min(0.999, (bx1 + bx2) / 2 / w)),
            "cy": max(0.001, min(0.999, (by1 + by2) / 2 / h)),
            "nw": bw / w,
            "nh": bh / h,
        })

    canvas = _augment(canvas)
    return canvas, annotations


def _augment(img: np.ndarray) -> np.ndarray:
    if random.random() < 0.4:
        shift = random.randint(-12, 12)
        img = np.clip(img.astype(np.int16) + shift, 0, 255).astype(np.uint8)
    if random.random() < 0.3:
        f = random.uniform(0.92, 1.08)
        m = img.mean()
        img = np.clip((img.astype(np.float32) - m) * f + m, 0, 255).astype(np.uint8)
    return img


# ── Dataset generation ───────────────────────────────────────────────

def generate_dataset(
    count: int,
    sprite_dir: str = "data/sprites",
    output_dir: str = "datasets/synthetic_bases",
    template_path: str = DEFAULT_TEMPLATE,
    img_size: int | None = None,
    val_ratio: float = 0.15,
    preview: bool = False,
):
    sprite_path = Path(sprite_dir)
    output_path = Path(output_dir)

    print("Loading sprites...")
    sprites = load_sprites(sprite_path)
    n_sprites = sum(len(v) for v in sprites.values())
    print(f"  {n_sprites} sprites from {len(sprites)} building types")

    print("Loading template...")
    template = cv2.imread(str(template_path))
    if template is None:
        print(f"ERROR: Cannot load template: {template_path}")
        return
    th, tw = template.shape[:2]
    print(f"  Template: {tw}x{th}")

    # Preview tile grid info
    grid = IsometricGrid(tw, th)
    print(f"  Tile half-w: {grid.thw:.1f}px, half-h: {grid.thh:.1f}px")
    print(f"  3x3 diamond: {grid.diamond_width(3):.0f}x{grid.diamond_height(3):.0f}px")
    print(f"  4x4 diamond: {grid.diamond_width(4):.0f}x{grid.diamond_height(4):.0f}px")

    all_sprite_names = sorted(set(
        s["name"] for variants in sprites.values() for s in variants
    ))
    class_index = {name: i for i, name in enumerate(all_sprite_names)}
    print(f"  {len(class_index)} unique classes")

    n_val = max(1, int(count * val_ratio))
    n_train = count - n_val

    for split in ("train", "val"):
        (output_path / split / "images").mkdir(parents=True, exist_ok=True)
        (output_path / split / "labels").mkdir(parents=True, exist_ok=True)
    if preview:
        (output_path / "preview").mkdir(parents=True, exist_ok=True)

    print(f"\nGenerating {count} images ({n_train} train, {n_val} val)...")

    total_boxes = 0
    classes_seen: set[str] = set()

    for i in range(count):
        split = "val" if i < n_val else "train"
        canvas, annotations = generate_base(sprites, template)

        out_img = canvas
        if img_size:
            out_img = cv2.resize(canvas, (img_size, img_size))

        name = f"base_{i:05d}.jpg"
        cv2.imwrite(
            str(output_path / split / "images" / name),
            out_img, [cv2.IMWRITE_JPEG_QUALITY, 92],
        )

        lines = []
        for ann in annotations:
            sn = ann["class_name"]
            if sn not in class_index:
                continue
            lines.append(
                f"{class_index[sn]} {ann['cx']:.6f} {ann['cy']:.6f} "
                f"{ann['nw']:.6f} {ann['nh']:.6f}"
            )
            classes_seen.add(sn)
        (output_path / split / "labels" / f"base_{i:05d}.txt").write_text(
            "\n".join(lines))

        total_boxes += len(annotations)

        if preview and i < 30:
            prev = out_img.copy()
            ph, pw = prev.shape[:2]
            for ann in annotations:
                cx, cy, nw, nh = ann["cx"], ann["cy"], ann["nw"], ann["nh"]
                ts = BUILDING_TILES.get(ann["class_name_base"], 3)
                # Color by tile size: green=3x3, blue=4x4, yellow=2x2, red=1x1
                colors = {1: (0, 0, 255), 2: (0, 255, 255),
                          3: (0, 255, 0), 4: (255, 150, 0)}
                color = colors.get(ts, (255, 255, 255))
                px1 = int((cx - nw / 2) * pw)
                py1 = int((cy - nh / 2) * ph)
                px2 = int((cx + nw / 2) * pw)
                py2 = int((cy + nh / 2) * ph)
                cv2.rectangle(prev, (px1, py1), (px2, py2), color, 2)
                label = f"{ann['class_name_base']}({ts}x{ts})"
                cv2.putText(prev, label, (px1, max(py1 - 4, 12)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.35, color, 1)
            cv2.imwrite(str(output_path / "preview" / name), prev)

        if (i + 1) % 100 == 0 or i == count - 1:
            avg = total_boxes / (i + 1)
            print(f"  [{i+1}/{count}] {total_boxes} boxes, "
                  f"{len(classes_seen)} classes, avg {avg:.0f}/image")

    yaml_path = output_path / "dataset.yaml"
    yaml_path.write_text(
        f"# Synthetic CoC base dataset ({count} images, {len(all_sprite_names)} classes)\n"
        f"# Generated by training/base_builder.py\n\n"
        f"path: {output_path.resolve()}\n"
        f"train: train/images\n"
        f"val: val/images\n\n"
        f"nc: {len(all_sprite_names)}\n"
        f"names: {all_sprite_names}\n"
    )

    print(f"\nDone!")
    print(f"  Images: {count} ({n_train} train, {n_val} val)")
    print(f"  Boxes:  {total_boxes} (avg {total_boxes / count:.0f}/image)")
    print(f"  Classes: {len(classes_seen)} / {len(all_sprite_names)}")
    print(f"  Output: {output_path.resolve()}")
    print(f"\nTrain: python training/train.py --data {yaml_path} --epochs 100")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--count", type=int, default=1000)
    p.add_argument("--sprites", default="data/sprites")
    p.add_argument("--output", default="datasets/synthetic_bases")
    p.add_argument("--template", default=DEFAULT_TEMPLATE)
    p.add_argument("--img-size", type=int, default=None)
    p.add_argument("--val-ratio", type=float, default=0.15)
    p.add_argument("--preview", action="store_true")
    args = p.parse_args()

    generate_dataset(
        count=args.count, sprite_dir=args.sprites,
        output_dir=args.output, template_path=args.template,
        img_size=args.img_size, val_ratio=args.val_ratio,
        preview=args.preview,
    )
