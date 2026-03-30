#!/usr/bin/env python3
"""
Sprite Calibrator GUI (PySide6) — resize and position each building
sprite to fit its isometric tile diamond.

Left sidebar: folder tree of all sprites — click to jump.
Main area: sprite on green tile diamond with drag handles.
  - Drag inside box: move sprite
  - Drag corner handles: resize sprite
  - Arrow keys: fine nudge (1px)
  - Enter: save + next
  - R: reset
"""

import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PySide6.QtCore import Qt, QRectF, QPointF, Signal
from PySide6.QtGui import QImage, QPixmap, QPainter, QColor, QPen, QBrush, QFont, QPolygonF, QShortcut
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QTreeWidget, QTreeWidgetItem, QLabel, QPushButton, QStatusBar,
    QSplitter,
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from training.generate.building_tiles import BUILDING_TILES

# ── Config ──────────────────────────────────────────────────────────

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCALES_FILE = str(_PROJECT_ROOT / "data/calibration/sprite_scales.json")
CONFIRMED_FILE = str(_PROJECT_ROOT / "data/calibration/confirmed_sprites.json")
GRID_CAL_FILE = str(_PROJECT_ROOT / "data/calibration/grid_calibration.json")

HANDLE_SIZE = 7


def load_grid_cal():
    p = Path(GRID_CAL_FILE)
    if p.exists():
        with open(p) as f:
            cal = json.load(f)
        return cal["tile_half_w"], cal["tile_half_h"]
    return 17.38, 12.95


THW, THH = load_grid_cal()


# ── Sprite data ─────────────────────────────────────────────────────

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


def load_sprites():
    confirmed = {}
    if Path(CONFIRMED_FILE).exists():
        with open(CONFIRMED_FILE) as f:
            confirmed = json.load(f)

    sprites_dir = _PROJECT_ROOT / "data/sprites"
    all_sprites = []
    folder_tree = {}

    for png in sorted(sprites_dir.rglob("*.png")):
        if png.name.startswith("._"):
            continue
        btype = png.parent.name
        if btype not in BUILDING_TILES:
            continue

        category = png.parent.parent.name
        if category == "sprites":
            category = "other"

        name = png.stem
        level_str = name.rsplit("_", 1)[-1]
        level = int(level_str) if level_str.isdigit() else -1

        img = cv2.imread(str(png), cv2.IMREAD_UNCHANGED)
        if img is None or len(img.shape) < 3 or img.shape[2] != 4:
            continue

        idx = len(all_sprites)
        all_sprites.append({
            "name": name, "btype": btype, "category": category,
            "level": level, "image": img,
            "base_w": measure_base_width(img),
            "tile_size": BUILDING_TILES[btype],
        })

        if category not in folder_tree:
            folder_tree[category] = {}
        if btype not in folder_tree[category]:
            folder_tree[category][btype] = []
        folder_tree[category][btype].append(idx)

    return all_sprites, folder_tree


def load_scales():
    if Path(SCALES_FILE).exists():
        with open(SCALES_FILE) as f:
            return json.load(f)
    return {}


def save_scales(scales):
    Path(SCALES_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(SCALES_FILE, "w") as f:
        json.dump(scales, f, indent=2)


def get_cfg(scales, name):
    cfg = scales.get(name, {})
    if isinstance(cfg, (int, float)):
        return cfg, 0, 0
    return cfg.get("scale", 1.0), cfg.get("ox", 0), cfg.get("oy", 0)


def set_cfg(scales, name, s, ox, oy):
    scales[name] = {"scale": round(s, 3), "ox": round(ox, 1), "oy": round(oy, 1)}


# ── Canvas Widget ───────────────────────────────────────────────────

class SpriteCanvas(QWidget):
    sprite_changed = Signal()

    def __init__(self, sprites, scales):
        super().__init__()
        self.sprites = sprites
        self.scales = scales
        self.idx = 0
        self.setMinimumSize(600, 550)
        self.setFocusPolicy(Qt.StrongFocus)

        # Drag state
        self._dragging = False
        self._resizing = False
        self._drag_start = QPointF()
        self._start_ox = 0.0
        self._start_oy = 0.0
        self._start_scale = 1.0
        self._bbox = QRectF()  # sprite bbox in widget coords
        self._disp_scale = 1.0

    def current_sprite(self):
        return self.sprites[self.idx] if self.sprites else None

    def get_cfg(self):
        spr = self.current_sprite()
        if not spr:
            return 1.0, 0, 0
        return get_cfg(self.scales, spr["name"])

    def set_cfg(self, s, ox, oy):
        spr = self.current_sprite()
        if spr:
            set_cfg(self.scales, spr["name"], s, ox, oy)
            self.update()

    def _compute_layout(self):
        """Compute diamond and sprite positions."""
        spr = self.current_sprite()
        if not spr:
            return None

        w, h = self.width(), self.height()
        ts = spr["tile_size"]
        dw = 2 * ts * THW
        dh = 2 * ts * THH

        disp_scale = min(w * 0.55 / dw, h * 0.35 / dh)
        self._disp_scale = disp_scale

        cx = w / 2
        diamond_bottom = h * 0.72
        hw = dw / 2 * disp_scale
        hh = dh / 2 * disp_scale
        diamond_cy = diamond_bottom - hh

        s, ox, oy = self.get_cfg()
        img = spr["image"]
        sh, sw = img.shape[:2]
        base_w = spr["base_w"]

        game_scale = dw / base_w * s
        full_scale = game_scale * disp_scale
        nw = max(2, sw * full_scale)
        nh = max(2, sh * full_scale)

        paste_x = cx - nw / 2 + ox * disp_scale
        paste_y = diamond_bottom - nh + oy * disp_scale

        return {
            "cx": cx, "diamond_cy": diamond_cy, "hw": hw, "hh": hh,
            "diamond_bottom": diamond_bottom,
            "paste_x": paste_x, "paste_y": paste_y,
            "nw": nw, "nh": nh, "full_scale": full_scale,
            "disp_scale": disp_scale,
        }

    def paintEvent(self, event):
        spr = self.current_sprite()
        if not spr:
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        # Background
        p.fillRect(0, 0, w, h, QColor(40, 40, 40))

        layout = self._compute_layout()
        if not layout:
            return

        cx = layout["cx"]
        dcy = layout["diamond_cy"]
        hw = layout["hw"]
        hh = layout["hh"]

        # Draw individual tile diamonds within the footprint
        ts = spr["tile_size"]
        ds = layout["disp_scale"]
        tw = THW * ds  # half-width of one tile in screen px
        th = THH * ds  # half-height of one tile in screen px
        diamond_bottom = layout["diamond_bottom"]

        for row in range(ts):
            for col in range(ts):
                # Isometric offset from top-center of the footprint diamond
                # row goes down-right, col goes down-left
                tcx = cx + (col - row) * tw
                tcy = (dcy - hh) + (col + row + 1) * th
                tile = QPolygonF([
                    QPointF(tcx, tcy - th),
                    QPointF(tcx + tw, tcy),
                    QPointF(tcx, tcy + th),
                    QPointF(tcx - tw, tcy),
                ])
                p.setBrush(QBrush(QColor(40, 110, 40, 130)))
                p.setPen(QPen(QColor(60, 200, 60), 1.5))
                p.drawPolygon(tile)

        # Render sprite
        img = spr["image"]
        sh, sw = img.shape[:2]
        nw, nh = int(layout["nw"]), int(layout["nh"])
        if nw < 2 or nh < 2:
            return

        scaled = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA)
        # BGRA -> RGBA for Qt
        rgba = cv2.cvtColor(scaled, cv2.COLOR_BGRA2RGBA)
        qimg = QImage(rgba.data, nw, nh, nw * 4, QImage.Format_RGBA8888)
        px = int(layout["paste_x"])
        py = int(layout["paste_y"])
        p.drawImage(px, py, qimg)

        # Bounding box
        self._bbox = QRectF(px, py, nw, nh)
        pen = QPen(QColor(0, 200, 255), 2)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawRect(self._bbox)

        # Corner handles
        hs = HANDLE_SIZE
        for corner in [self._bbox.topLeft(), self._bbox.topRight(),
                       self._bbox.bottomLeft(), self._bbox.bottomRight()]:
            handle = QRectF(corner.x() - hs, corner.y() - hs, hs * 2, hs * 2)
            p.setBrush(QBrush(QColor(0, 200, 255)))
            p.setPen(QPen(QColor(255, 255, 255), 1))
            p.drawRect(handle)

        # Info text
        p.setPen(QColor(255, 255, 255))
        p.setFont(QFont("Helvetica", 14, QFont.Bold))
        p.drawText(10, 25, spr["name"])

        p.setFont(QFont("Helvetica", 11))
        p.setPen(QColor(180, 180, 180))
        ts = spr["tile_size"]
        p.drawText(10, 45, f"{spr['btype']} {ts}x{ts}")

        s, ox, oy = self.get_cfg()
        p.setPen(QColor(200, 200, 200))
        p.setFont(QFont("Helvetica", 12))
        p.drawText(10, h - 40, f"Scale: {s:.2f}   Offset: ({ox:.0f}, {oy:.0f})")

        p.setPen(QColor(120, 120, 120))
        p.setFont(QFont("Helvetica", 10))
        p.drawText(10, h - 15, "Drag box: move  |  Drag corners: resize  |  Arrows: nudge  |  Enter: save+next")

        idx_text = f"[{self.idx + 1}/{len(self.sprites)}]"
        p.setPen(QColor(200, 200, 200))
        p.setFont(QFont("Helvetica", 12))
        p.drawText(w - 90, 25, idx_text)

        p.end()

    def _hit_corner(self, pos):
        """Returns True if pos hits any corner handle."""
        hs = HANDLE_SIZE + 5
        for corner in [self._bbox.topLeft(), self._bbox.topRight(),
                       self._bbox.bottomLeft(), self._bbox.bottomRight()]:
            if abs(pos.x() - corner.x()) <= hs and abs(pos.y() - corner.y()) <= hs:
                return True
        return False

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        pos = event.position()

        if self._hit_corner(pos):
            self._resizing = True
            self._drag_start = pos
            s, ox, oy = self.get_cfg()
            self._start_scale = s
        elif self._bbox.contains(pos):
            self._dragging = True
            self._drag_start = pos
            s, ox, oy = self.get_cfg()
            self._start_ox = ox
            self._start_oy = oy

    def mouseMoveEvent(self, event):
        pos = event.position()

        # Update cursor
        if self._hit_corner(pos):
            self.setCursor(Qt.SizeFDiagCursor)
        elif self._bbox.contains(pos):
            self.setCursor(Qt.SizeAllCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

        if self._dragging:
            dx = pos.x() - self._drag_start.x()
            dy = pos.y() - self._drag_start.y()
            ds = self._disp_scale
            if ds > 0:
                self.set_cfg(self.get_cfg()[0],
                             self._start_ox + dx / ds,
                             self._start_oy + dy / ds)
                self.sprite_changed.emit()

        elif self._resizing:
            bcx = self._bbox.center().x()
            bcy = self._bbox.center().y()
            dist_now = max(abs(pos.x() - bcx), abs(pos.y() - bcy))
            dist_start = max(abs(self._drag_start.x() - bcx),
                             abs(self._drag_start.y() - bcy))
            if dist_start > 5:
                ratio = dist_now / dist_start
                new_scale = max(0.1, self._start_scale * ratio)
                s, ox, oy = self.get_cfg()
                self.set_cfg(new_scale, ox, oy)
                self.sprite_changed.emit()

    def mouseReleaseEvent(self, event):
        self._dragging = False
        self._resizing = False

    def keyPressEvent(self, event):
        s, ox, oy = self.get_cfg()
        k = event.key()

        if k == Qt.Key_Up:
            self.set_cfg(s, ox, oy - 1)
        elif k == Qt.Key_Down:
            self.set_cfg(s, ox, oy + 1)
        elif k == Qt.Key_Left:
            self.set_cfg(s, ox - 1, oy)
        elif k == Qt.Key_Right:
            self.set_cfg(s, ox + 1, oy)
        elif k == Qt.Key_R:
            self.set_cfg(1.0, 0, 0)
        else:
            event.ignore()
            return
        self.sprite_changed.emit()


# ── Main Window ─────────────────────────────────────────────────────

class CalibratorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sprite Calibrator")
        self.setMinimumSize(950, 600)

        self.sprites, self.folder_tree = load_sprites()
        self.scales = load_scales()

        # Sidebar tree
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setFont(QFont("Helvetica", 12))
        self.tree.setStyleSheet("""
            QTreeWidget {
                background-color: #1e1e1e;
                color: #cccccc;
                border: none;
                outline: none;
            }
            QTreeWidget::item {
                padding: 3px 0;
            }
            QTreeWidget::item:selected {
                background-color: #2d5a2d;
                color: #80ffb0;
            }
            QTreeWidget::item:hover {
                background-color: #2a2a3a;
            }
        """)
        self._build_tree()
        self.tree.itemClicked.connect(self._on_tree_click)

        # Canvas
        self.canvas = SpriteCanvas(self.sprites, self.scales)
        self.canvas.sprite_changed.connect(self._update_status)

        # Layout
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.tree)
        splitter.addWidget(self.canvas)
        splitter.setSizes([260, 650])
        self.setCentralWidget(splitter)

        # Status bar
        self.status = QStatusBar()
        self.status.setFont(QFont("Helvetica", 11))
        self.status.setStyleSheet("color: #aaa; background: #1a1a1a;")
        self.setStatusBar(self.status)
        self._update_status()

        # Shortcuts
        QShortcut(Qt.Key_Return, self, self._save_next)
        QShortcut(Qt.Key_Enter, self, self._save_next)
        QShortcut(Qt.Key_Space, self, self._save_current)
        QShortcut(Qt.Key_N, self, self._next)
        QShortcut(Qt.Key_P, self, self._prev)
        QShortcut(Qt.Key_Q, self, self._quit_save)

        # Dark theme
        self.setStyleSheet("QMainWindow { background: #1a1a1a; }")

        print(f"Loaded {len(self.sprites)} sprites (THW={THW:.2f}, THH={THH:.2f})")

    def _build_tree(self):
        cat_order = ["defense", "resource", "army", "trap", "other"]
        self._tree_items = {}  # sprite_idx -> QTreeWidgetItem

        for cat in cat_order:
            if cat not in self.folder_tree:
                continue
            cat_item = QTreeWidgetItem([cat.upper()])
            cat_item.setFont(0, QFont("Helvetica", 12, QFont.Bold))
            cat_item.setForeground(0, QColor(140, 190, 255))
            self.tree.addTopLevelItem(cat_item)

            for btype in sorted(self.folder_tree[cat].keys()):
                indices = self.folder_tree[cat][btype]
                ts = BUILDING_TILES.get(btype, "?")
                bt_item = QTreeWidgetItem([f"{btype} ({ts}x{ts})"])
                bt_item.setForeground(0, QColor(100, 180, 150))
                cat_item.addChild(bt_item)

                for si in indices:
                    spr = self.sprites[si]
                    spr_item = QTreeWidgetItem([spr["name"]])
                    spr_item.setData(0, Qt.UserRole, si)
                    bt_item.addChild(spr_item)
                    self._tree_items[si] = spr_item

    def _on_tree_click(self, item, column):
        si = item.data(0, Qt.UserRole)
        if si is not None:
            self.canvas.idx = si
            self.canvas.update()
            self._update_status()

    def _highlight_tree(self):
        idx = self.canvas.idx
        if idx in self._tree_items:
            item = self._tree_items[idx]
            self.tree.setCurrentItem(item)
            self.tree.scrollToItem(item)

    def _update_status(self):
        spr = self.canvas.current_sprite()
        if spr:
            s, ox, oy = get_cfg(self.scales, spr["name"])
            self.status.showMessage(
                f"  {spr['name']}  |  Scale: {s:.3f}  Offset: ({ox:.0f}, {oy:.0f})  |  "
                f"[{self.canvas.idx + 1}/{len(self.sprites)}]")

    def _save_current(self):
        spr = self.canvas.current_sprite()
        if spr:
            save_scales(self.scales)
            s, ox, oy = get_cfg(self.scales, spr["name"])
            print(f"Saved {spr['name']}: scale={s:.3f} offset=({ox:.0f},{oy:.0f})")

    def _save_next(self):
        self._save_current()
        if self.canvas.idx < len(self.sprites) - 1:
            self.canvas.idx += 1
            self.canvas.update()
            self._highlight_tree()
            self._update_status()

    def _next(self):
        if self.canvas.idx < len(self.sprites) - 1:
            self.canvas.idx += 1
            self.canvas.update()
            self._highlight_tree()
            self._update_status()

    def _prev(self):
        if self.canvas.idx > 0:
            self.canvas.idx -= 1
            self.canvas.update()
            self._highlight_tree()
            self._update_status()

    def _quit_save(self):
        save_scales(self.scales)
        print(f"Saved {len(self.scales)} configs to {SCALES_FILE}")
        self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Dark palette
    from PySide6.QtGui import QPalette
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(26, 26, 26))
    palette.setColor(QPalette.WindowText, QColor(200, 200, 200))
    palette.setColor(QPalette.Base, QColor(30, 30, 30))
    palette.setColor(QPalette.Text, QColor(200, 200, 200))
    app.setPalette(palette)

    win = CalibratorWindow()
    win.show()
    sys.exit(app.exec())
