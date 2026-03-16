"""Army composition editor — clean macOS-native layout.

Left: your army (Troops, Spells, Heroes+Pets) with capacity bars.
Right: vertical scrollable list of all available troops to pick from.
"""

import json
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QScrollArea, QSizePolicy,
    QSpinBox, QFrame, QSplitter, QApplication,
)
from PySide6.QtCore import Qt, Signal, QMimeData, QSize
from PySide6.QtGui import (
    QDrag, QFont, QColor, QPainter, QPixmap, QPalette, QLinearGradient,
    QIcon,
)

from bot.settings import Settings
from bot.utils import resource_path

# ── Icon loading ─────────────────────────────────────────────────────
_ICON_CACHE = {}

def _troop_icon(troop_id, size=28):
    """Load and cache a troop icon as a QPixmap, scaled to size x size."""
    key = (troop_id, size)
    if key in _ICON_CACHE:
        return _ICON_CACHE[key]

    path = resource_path(os.path.join("templates", "icons", f"{troop_id}.png"))
    if os.path.isfile(path):
        pix = QPixmap(path).scaled(
            size, size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    else:
        # Transparent placeholder
        pix = QPixmap(size, size)
        pix.fill(QColor(0, 0, 0, 0))

    _ICON_CACHE[key] = pix
    return pix

# ═══════════════════════════════════════════════════════════════════════
# Data
# ═══════════════════════════════════════════════════════════════════════

TROOP_DATA = [
    # Elixir Troops
    {"id": "barbarian",        "name": "Barbarian",         "space": 1,  "category": "elixir"},
    {"id": "archer",           "name": "Archer",            "space": 1,  "category": "elixir"},
    {"id": "giant",            "name": "Giant",             "space": 5,  "category": "elixir"},
    {"id": "goblin",           "name": "Goblin",            "space": 1,  "category": "elixir"},
    {"id": "wall_breaker",     "name": "Wall Breaker",      "space": 2,  "category": "elixir"},
    {"id": "balloon",          "name": "Balloon",           "space": 5,  "category": "elixir"},
    {"id": "wizard",           "name": "Wizard",            "space": 4,  "category": "elixir"},
    {"id": "healer",           "name": "Healer",            "space": 14, "category": "elixir"},
    {"id": "dragon",           "name": "Dragon",            "space": 20, "category": "elixir"},
    {"id": "pekka",            "name": "P.E.K.K.A",        "space": 25, "category": "elixir"},
    {"id": "baby_dragon",      "name": "Baby Dragon",       "space": 10, "category": "elixir"},
    {"id": "miner",            "name": "Miner",             "space": 6,  "category": "elixir"},
    {"id": "electro_dragon",   "name": "Electro Dragon",    "space": 30, "category": "elixir"},
    {"id": "yeti",             "name": "Yeti",              "space": 18, "category": "elixir"},
    {"id": "dragon_rider",     "name": "Dragon Rider",      "space": 25, "category": "elixir"},
    {"id": "electro_titan",    "name": "Electro Titan",     "space": 32, "category": "elixir"},
    {"id": "root_rider",       "name": "Root Rider",        "space": 20, "category": "elixir"},
    {"id": "thrower",          "name": "Thrower",           "space": 16, "category": "elixir"},
    {"id": "meteor_golem",     "name": "Meteor Golem",      "space": 40, "category": "elixir"},
    # Dark Elixir Troops
    {"id": "minion",           "name": "Minion",            "space": 2,  "category": "dark"},
    {"id": "hog_rider",        "name": "Hog Rider",         "space": 5,  "category": "dark"},
    {"id": "valkyrie",         "name": "Valkyrie",          "space": 8,  "category": "dark"},
    {"id": "golem",            "name": "Golem",             "space": 30, "category": "dark"},
    {"id": "witch",            "name": "Witch",             "space": 12, "category": "dark"},
    {"id": "lava_hound",       "name": "Lava Hound",        "space": 30, "category": "dark"},
    {"id": "bowler",           "name": "Bowler",            "space": 6,  "category": "dark"},
    {"id": "ice_golem",        "name": "Ice Golem",         "space": 15, "category": "dark"},
    {"id": "headhunter",       "name": "Headhunter",        "space": 6,  "category": "dark"},
    {"id": "apprentice_warden","name": "Apprentice Warden", "space": 20, "category": "dark"},
    {"id": "druid",            "name": "Druid",             "space": 16, "category": "dark"},
    {"id": "furnace",          "name": "Furnace",           "space": 18, "category": "dark"},
    # Siege Machines
    {"id": "wall_wrecker",     "name": "Wall Wrecker",      "space": 1,  "category": "siege"},
    {"id": "battle_blimp",     "name": "Battle Blimp",      "space": 1,  "category": "siege"},
    {"id": "stone_slammer",    "name": "Stone Slammer",     "space": 1,  "category": "siege"},
    {"id": "siege_barracks",   "name": "Siege Barracks",    "space": 1,  "category": "siege"},
    {"id": "log_launcher",     "name": "Log Launcher",      "space": 1,  "category": "siege"},
    {"id": "flame_flinger",    "name": "Flame Flinger",     "space": 1,  "category": "siege"},
    {"id": "troop_launcher",   "name": "Troop Launcher",    "space": 1,  "category": "siege"},
    {"id": "battle_drill",     "name": "Battle Drill",      "space": 1,  "category": "siege"},
    # Heroes
    {"id": "barbarian_king",   "name": "Barbarian King",    "space": 0,  "category": "hero"},
    {"id": "archer_queen",     "name": "Archer Queen",      "space": 0,  "category": "hero"},
    {"id": "grand_warden",     "name": "Grand Warden",      "space": 0,  "category": "hero"},
    {"id": "royal_champion",   "name": "Royal Champion",    "space": 0,  "category": "hero"},
    {"id": "minion_prince",    "name": "Minion Prince",     "space": 0,  "category": "hero"},
    {"id": "dragon_duke",      "name": "Dragon Duke",       "space": 0,  "category": "hero"},
    # Hero Pets
    {"id": "lassi",            "name": "L.A.S.S.I",         "space": 0,  "category": "pet"},
    {"id": "electro_owl",      "name": "Electro Owl",       "space": 0,  "category": "pet"},
    {"id": "mighty_yak",       "name": "Mighty Yak",        "space": 0,  "category": "pet"},
    {"id": "unicorn",          "name": "Unicorn",           "space": 0,  "category": "pet"},
    {"id": "frosty",           "name": "Frosty",            "space": 0,  "category": "pet"},
    {"id": "diggy",            "name": "Diggy",             "space": 0,  "category": "pet"},
    {"id": "poison_lizard",    "name": "Poison Lizard",     "space": 0,  "category": "pet"},
    {"id": "phoenix",          "name": "Phoenix",           "space": 0,  "category": "pet"},
    {"id": "spirit_fox",       "name": "Spirit Fox",        "space": 0,  "category": "pet"},
    {"id": "angry_jelly",      "name": "Angry Jelly",       "space": 0,  "category": "pet"},
    {"id": "sneezy",           "name": "Sneezy",            "space": 0,  "category": "pet"},
    {"id": "greedy_raven",     "name": "Greedy Raven",      "space": 0,  "category": "pet"},
    # Elixir Spells
    {"id": "lightning_spell",   "name": "Lightning Spell",   "space": 1,  "category": "spell_elixir"},
    {"id": "healing_spell",     "name": "Healing Spell",     "space": 2,  "category": "spell_elixir"},
    {"id": "rage_spell",        "name": "Rage Spell",        "space": 2,  "category": "spell_elixir"},
    {"id": "jump_spell",        "name": "Jump Spell",        "space": 2,  "category": "spell_elixir"},
    {"id": "freeze_spell",      "name": "Freeze Spell",      "space": 1,  "category": "spell_elixir"},
    {"id": "clone_spell",       "name": "Clone Spell",       "space": 3,  "category": "spell_elixir"},
    {"id": "invisibility_spell","name": "Invisibility Spell","space": 1,  "category": "spell_elixir"},
    {"id": "recall_spell",      "name": "Recall Spell",      "space": 2,  "category": "spell_elixir"},
    {"id": "revive_spell",      "name": "Revive Spell",      "space": 2,  "category": "spell_elixir"},
    {"id": "totem_spell",       "name": "Totem Spell",       "space": 1,  "category": "spell_elixir"},
    # Dark Spells
    {"id": "poison_spell",     "name": "Poison Spell",      "space": 1,  "category": "spell_dark"},
    {"id": "earthquake_spell", "name": "Earthquake Spell",  "space": 1,  "category": "spell_dark"},
    {"id": "haste_spell",      "name": "Haste Spell",       "space": 1,  "category": "spell_dark"},
    {"id": "skeleton_spell",   "name": "Skeleton Spell",    "space": 1,  "category": "spell_dark"},
    {"id": "bat_spell",        "name": "Bat Spell",         "space": 1,  "category": "spell_dark"},
    {"id": "overgrowth_spell", "name": "Overgrowth Spell",  "space": 2,  "category": "spell_dark"},
    {"id": "ice_block_spell",  "name": "Ice Block Spell",   "space": 1,  "category": "spell_dark"},
]

_TROOP_BY_ID = {t["id"]: t for t in TROOP_DATA}

# Category display order and labels for the right-side picker
_PICKER_SECTIONS = [
    ("Elixir Troops",      "elixir"),
    ("Dark Elixir Troops",  "dark"),
    ("Siege Machines",      "siege"),
    ("Heroes",              "hero"),
    ("Hero Pets",           "pet"),
    ("Elixir Spells",       "spell_elixir"),
    ("Dark Spells",         "spell_dark"),
]

# Which categories go to which army section
_TROOP_CATS = {"elixir", "dark", "siege"}
_SPELL_CATS = {"spell_elixir", "spell_dark"}
_HERO_CATS  = {"hero"}
_PET_CATS   = {"pet"}


# ═══════════════════════════════════════════════════════════════════════
# Shared stylesheet — macOS native feel
# ═══════════════════════════════════════════════════════════════════════

def _global_style():
    """Minimal, native macOS-inspired stylesheet."""
    return """
        * {
            font-family: -apple-system, "SF Pro Text", "Helvetica Neue", sans-serif;
        }
    """


# GlassCard is now the real backdrop-blur glass from gui/glass.py
from gui.glass import GlassPanel as GlassCard


# ═══════════════════════════════════════════════════════════════════════
# Capacity bar — thin, elegant progress indicator
# ═══════════════════════════════════════════════════════════════════════

class CapacityBar(QWidget):
    """Thin progress bar showing used / max."""

    def __init__(self, max_val, parent=None):
        super().__init__(parent)
        self._max = max_val
        self._used = 0
        self.setFixedHeight(6)

    @property
    def max_capacity(self):
        return self._max

    @max_capacity.setter
    def max_capacity(self, v):
        self._max = v
        self.update()

    @property
    def used(self):
        return self._used

    @used.setter
    def used(self, v):
        self._used = v
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Track
        p.setBrush(QColor(255, 255, 255, 15))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, 0, w, h, 3, 3)

        # Fill
        if self._max > 0:
            ratio = min(self._used / self._max, 1.0)
            over = self._used > self._max
            color = QColor("#ff453a") if over else QColor("#30d158")
            p.setBrush(color)
            p.drawRoundedRect(0, 0, int(w * ratio), h, 3, 3)
        p.end()


# ═══════════════════════════════════════════════════════════════════════
# Army slot — one troop in your army with quantity +/-
# ═══════════════════════════════════════════════════════════════════════

class ArmySlotWidget(QFrame):
    """Single troop/spell/hero in your army composition."""

    removed = Signal(str)
    changed = Signal()

    def __init__(self, troop, quantity=1, parent=None):
        super().__init__(parent)
        self.troop = troop
        self._qty = quantity
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(36)
        self.setStyleSheet("""
            ArmySlotWidget {
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 8px;
            }
            ArmySlotWidget:hover {
                background: rgba(255,255,255,0.10);
                border-color: rgba(255,255,255,0.18);
            }
        """)

        row = QHBoxLayout(self)
        row.setContentsMargins(6, 0, 6, 0)
        row.setSpacing(6)

        # Icon
        icon_pix = _troop_icon(troop["id"], 26)
        if not icon_pix.isNull():
            icon_lbl = QLabel()
            icon_lbl.setPixmap(icon_pix)
            icon_lbl.setFixedSize(28, 28)
            icon_lbl.setStyleSheet("background: transparent; border: none;")
            row.addWidget(icon_lbl)

        # Name
        name = QLabel(troop["name"])
        name.setStyleSheet("color: rgba(255,255,255,0.9); font-size: 12px; font-weight: 500; background: transparent; border: none;")
        row.addWidget(name, stretch=1)

        show_qty = troop["category"] not in ("hero", "pet")
        if show_qty:
            # Housing per unit
            sp = QLabel(str(troop["space"]))
            sp.setStyleSheet("color: rgba(255,255,255,0.35); font-size: 10px; background: transparent; border: none;")
            sp.setFixedWidth(20)
            sp.setAlignment(Qt.AlignmentFlag.AlignCenter)
            row.addWidget(sp)

            minus = QPushButton("-")
            minus.setFixedSize(22, 22)
            minus.setStyleSheet("""
                QPushButton { background: rgba(255,255,255,0.08); color: white;
                    border-radius: 4px; font-size: 14px; font-weight: bold; border: none; }
                QPushButton:hover { background: rgba(255,255,255,0.18); }
            """)
            minus.clicked.connect(self._dec)
            row.addWidget(minus)

            self._qty_lbl = QLabel(str(quantity))
            self._qty_lbl.setFixedWidth(24)
            self._qty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._qty_lbl.setStyleSheet("color: white; font-size: 13px; font-weight: bold; background: transparent; border: none;")
            row.addWidget(self._qty_lbl)

            plus = QPushButton("+")
            plus.setFixedSize(22, 22)
            plus.setStyleSheet("""
                QPushButton { background: rgba(255,255,255,0.08); color: white;
                    border-radius: 4px; font-size: 14px; font-weight: bold; border: none; }
                QPushButton:hover { background: rgba(255,255,255,0.18); }
            """)
            plus.clicked.connect(self._inc)
            row.addWidget(plus)
        else:
            self._qty_lbl = None

        x_btn = QPushButton("\u00d7")
        x_btn.setFixedSize(22, 22)
        x_btn.setStyleSheet("""
            QPushButton { background: transparent; color: rgba(255,255,255,0.3);
                border: none; font-size: 14px; }
            QPushButton:hover { color: #ff453a; }
        """)
        x_btn.clicked.connect(lambda: self.removed.emit(self.troop["id"]))
        row.addWidget(x_btn)

    @property
    def quantity(self):
        return self._qty

    @quantity.setter
    def quantity(self, v):
        self._qty = max(1, v)
        if self._qty_lbl:
            self._qty_lbl.setText(str(self._qty))
        self.changed.emit()

    @property
    def total_space(self):
        return self.troop["space"] * self._qty

    def _inc(self):
        self.quantity += 1

    def _dec(self):
        if self._qty <= 1:
            self.removed.emit(self.troop["id"])
        else:
            self.quantity -= 1


# ═══════════════════════════════════════════════════════════════════════
# Army section — a titled section with capacity + list of slots
# ═══════════════════════════════════════════════════════════════════════

class ArmySection(GlassCard):
    """One section of the army: Troops, Spells, or Heroes+Pets."""

    changed = Signal()

    def __init__(self, title, accepted_cats, has_capacity=True, max_slots=None, parent=None):
        super().__init__(parent)
        self._accepted = set(accepted_cats)
        self._max_slots = max_slots
        self._slots = []
        self._has_capacity = has_capacity

        self.setAcceptDrops(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        # Header row
        header = QHBoxLayout()
        header.setSpacing(8)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color: rgba(255,255,255,0.85); font-size: 13px; font-weight: 700; letter-spacing: 0.5px; background: transparent;")
        header.addWidget(title_lbl)

        header.addStretch()

        self._count_lbl = QLabel("0")
        self._count_lbl.setStyleSheet("color: rgba(255,255,255,0.45); font-size: 12px; background: transparent;")
        header.addWidget(self._count_lbl)

        layout.addLayout(header)

        # Capacity bar
        if has_capacity:
            self._cap_bar = CapacityBar(300)
            layout.addWidget(self._cap_bar)
        else:
            self._cap_bar = None

        # Slot container
        self._slot_layout = QVBoxLayout()
        self._slot_layout.setSpacing(4)
        self._slot_layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(self._slot_layout)

        # Empty state
        self._empty_lbl = QLabel("Drop or click to add")
        self._empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_lbl.setStyleSheet("color: rgba(255,255,255,0.2); font-size: 11px; font-style: italic; padding: 8px; background: transparent;")
        self._slot_layout.addWidget(self._empty_lbl)

        layout.addStretch()

    def set_capacity(self, val):
        if self._cap_bar:
            self._cap_bar.max_capacity = val

    # ── Drop handling ────────────────────────────────────────────────

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-cocbot-troop"):
            tid = bytes(event.mimeData().data("application/x-cocbot-troop")).decode()
            t = _TROOP_BY_ID.get(tid)
            if t and t["category"] in self._accepted:
                event.acceptProposedAction()
                self.setStyleSheet("border: 1px solid rgba(48,209,88,0.5); border-radius: 12px;")
                return
        event.ignore()

    def dragLeaveEvent(self, event):
        self.setStyleSheet("")

    def dropEvent(self, event):
        self.setStyleSheet("")
        if event.mimeData().hasFormat("application/x-cocbot-troop"):
            tid = bytes(event.mimeData().data("application/x-cocbot-troop")).decode()
            self.add_troop(tid)
            event.acceptProposedAction()

    # ── Troop management ─────────────────────────────────────────────

    def add_troop(self, troop_id):
        t = _TROOP_BY_ID.get(troop_id)
        if not t or t["category"] not in self._accepted:
            return

        # Heroes/pets: no duplicates, check max
        if self._max_slots is not None:
            for s in self._slots:
                if s.troop["id"] == troop_id:
                    return
            if len(self._slots) >= self._max_slots:
                return

        # Troops/spells: increment if exists
        if t["category"] not in ("hero", "pet"):
            for s in self._slots:
                if s.troop["id"] == troop_id:
                    s.quantity += 1
                    return

        slot = ArmySlotWidget(t, 1)
        slot.removed.connect(self._remove)
        slot.changed.connect(self._on_change)
        self._slots.append(slot)
        self._slot_layout.insertWidget(self._slot_layout.count() - 1, slot)  # before stretch
        self._refresh()
        self.changed.emit()

    def _remove(self, troop_id):
        for s in self._slots:
            if s.troop["id"] == troop_id:
                self._slots.remove(s)
                self._slot_layout.removeWidget(s)
                s.deleteLater()
                break
        self._refresh()
        self.changed.emit()

    def _on_change(self):
        self._refresh()
        self.changed.emit()

    def _refresh(self):
        self._empty_lbl.setVisible(len(self._slots) == 0)
        total = sum(s.total_space for s in self._slots)
        count = len(self._slots)
        if self._cap_bar:
            self._cap_bar.used = total
            self._count_lbl.setText(f"{total}/{self._cap_bar.max_capacity}")
        else:
            self._count_lbl.setText(str(count))

    def clear(self):
        for s in list(self._slots):
            self._slots.remove(s)
            self._slot_layout.removeWidget(s)
            s.deleteLater()
        self._refresh()
        self.changed.emit()

    def total_space(self):
        return sum(s.total_space for s in self._slots)

    def get_composition(self):
        return [{"troop": s.troop["id"], "quantity": s.quantity, "order": i}
                for i, s in enumerate(self._slots)]

    def load_composition(self, comp):
        self.blockSignals(True)
        for s in list(self._slots):
            self._slots.remove(s)
            self._slot_layout.removeWidget(s)
            s.deleteLater()
        for entry in sorted(comp, key=lambda e: e.get("order", 0)):
            t = _TROOP_BY_ID.get(entry.get("troop"))
            if t and t["category"] in self._accepted:
                slot = ArmySlotWidget(t, entry.get("quantity", 1))
                slot.removed.connect(self._remove)
                slot.changed.connect(self._on_change)
                self._slots.append(slot)
                self._slot_layout.insertWidget(self._slot_layout.count() - 1, slot)
        self._refresh()
        self.blockSignals(False)


# ═══════════════════════════════════════════════════════════════════════
# Picker button — draggable troop in the right sidebar
# ═══════════════════════════════════════════════════════════════════════

class PickerButton(QPushButton):
    """A troop button in the picker sidebar. Draggable + clickable."""

    def __init__(self, troop, parent=None):
        super().__init__(parent)
        self.troop = troop
        space = f"  [{troop['space']}]" if troop["space"] > 0 else ""
        self.setText(f" {troop['name']}{space}")
        self.setFixedHeight(34)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

        # Set troop icon
        icon_pix = _troop_icon(troop["id"], 24)
        if not icon_pix.isNull():
            self.setIcon(QIcon(icon_pix))
            self.setIconSize(QSize(24, 24))

        self.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.05);
                color: rgba(255,255,255,0.8);
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 8px;
                padding: 0 10px 0 6px;
                font-size: 11px;
                font-weight: 500;
                text-align: left;
            }
            QPushButton:hover {
                background: rgba(255,255,255,0.12);
                border-color: rgba(255,255,255,0.2);
                color: white;
            }
            QPushButton:pressed {
                background: rgba(255,255,255,0.18);
            }
        """)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            drag = QDrag(self)
            mime = QMimeData()
            mime.setData("application/x-cocbot-troop", self.troop["id"].encode())
            drag.setMimeData(mime)
            pix = self.grab()
            drag.setPixmap(pix)
            drag.setHotSpot(event.position().toPoint())
            drag.exec(Qt.DropAction.CopyAction)
        else:
            super().mouseMoveEvent(event)


# ═══════════════════════════════════════════════════════════════════════
# Right-side picker panel
# ═══════════════════════════════════════════════════════════════════════

class PickerPanel(QWidget):
    """Vertical scrollable list of all troops, grouped by category."""

    troop_clicked = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical {
                background: transparent; width: 6px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255,255,255,0.15); border-radius: 3px; min-height: 30px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        for section_name, category in _PICKER_SECTIONS:
            troops = [t for t in TROOP_DATA if t["category"] == category]
            if not troops:
                continue

            lbl = QLabel(section_name.upper())
            lbl.setStyleSheet("""
                color: rgba(255,255,255,0.35);
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 1px;
                padding: 8px 0 2px 4px;
                background: transparent;
            """)
            layout.addWidget(lbl)

            for t in troops:
                btn = PickerButton(t)
                btn.clicked.connect(lambda checked=False, tid=t["id"]: self.troop_clicked.emit(tid))
                layout.addWidget(btn)

        layout.addStretch()
        scroll.setWidget(container)
        outer.addWidget(scroll)


# ═══════════════════════════════════════════════════════════════════════
# Main Army Panel
# ═══════════════════════════════════════════════════════════════════════

class ArmyPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = Settings()
        self._setup_ui()
        self._load_composition()
        self._connect()

    def _setup_ui(self):
        # No local stylesheet — inherit from global Liquid Glass theme

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)

        # ── Left: Your Army ──────────────────────────────────────────
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(16, 16, 8, 16)
        left_layout.setSpacing(10)

        # Capacity settings
        cap_row = QHBoxLayout()
        cap_row.setSpacing(12)

        cap_row.addWidget(self._cap_label("Troop Capacity"))
        self._troop_cap = QSpinBox()
        self._troop_cap.setRange(20, 320)
        self._troop_cap.setValue(self._settings.get("army_troop_capacity", 300))
        self._troop_cap.setStyleSheet(self._spin_css())
        self._troop_cap.setFixedWidth(64)
        cap_row.addWidget(self._troop_cap)

        cap_row.addSpacing(12)

        cap_row.addWidget(self._cap_label("Spell Capacity"))
        self._spell_cap = QSpinBox()
        self._spell_cap.setRange(0, 13)
        self._spell_cap.setValue(self._settings.get("army_spell_capacity", 11))
        self._spell_cap.setStyleSheet(self._spin_css())
        self._spell_cap.setFixedWidth(64)
        cap_row.addWidget(self._spell_cap)

        cap_row.addStretch()

        clear_btn = QPushButton("Clear All")
        clear_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,69,58,0.15); color: #ff453a;
                border: 1px solid rgba(255,69,58,0.3); border-radius: 6px;
                padding: 4px 14px; font-size: 11px; font-weight: 600;
            }
            QPushButton:hover { background: rgba(255,69,58,0.25); }
        """)
        clear_btn.clicked.connect(self._clear_all)
        cap_row.addWidget(clear_btn)

        left_layout.addLayout(cap_row)

        # Scrollable army sections
        army_scroll = QScrollArea()
        army_scroll.setWidgetResizable(True)
        army_scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical {
                background: transparent; width: 6px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255,255,255,0.15); border-radius: 3px; min-height: 30px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)

        sections_widget = QWidget()
        sections_layout = QVBoxLayout(sections_widget)
        sections_layout.setContentsMargins(0, 0, 0, 0)
        sections_layout.setSpacing(10)

        self._troop_section = ArmySection("Troops", _TROOP_CATS, has_capacity=True)
        self._troop_section.set_capacity(self._troop_cap.value())
        sections_layout.addWidget(self._troop_section)

        self._spell_section = ArmySection("Spells", _SPELL_CATS, has_capacity=True)
        self._spell_section.set_capacity(self._spell_cap.value())
        sections_layout.addWidget(self._spell_section)

        self._hero_section = ArmySection("Heroes", _HERO_CATS, has_capacity=False, max_slots=4)
        sections_layout.addWidget(self._hero_section)

        self._pet_section = ArmySection("Pets", _PET_CATS, has_capacity=False, max_slots=4)
        sections_layout.addWidget(self._pet_section)

        sections_layout.addStretch()
        army_scroll.setWidget(sections_widget)
        left_layout.addWidget(army_scroll, stretch=1)

        # ── Right: Picker ────────────────────────────────────────────
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 16, 16, 16)
        right_layout.setSpacing(0)

        picker_title = QLabel("AVAILABLE UNITS")
        picker_title.setStyleSheet("""
            color: rgba(255,255,255,0.4);
            font-size: 10px; font-weight: 700; letter-spacing: 1.5px;
            padding-bottom: 8px; background: transparent;
        """)
        right_layout.addWidget(picker_title)

        self._picker = PickerPanel()
        right_layout.addWidget(self._picker, stretch=1)

        # Splitter
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        root.addWidget(splitter)

    def _connect(self):
        self._picker.troop_clicked.connect(self._on_pick)
        for section in (self._troop_section, self._spell_section, self._hero_section, self._pet_section):
            section.changed.connect(self._save)
        self._troop_cap.valueChanged.connect(self._on_cap_change)
        self._spell_cap.valueChanged.connect(self._on_cap_change)

    def _on_pick(self, troop_id):
        t = _TROOP_BY_ID.get(troop_id)
        if not t:
            return
        cat = t["category"]
        if cat in _TROOP_CATS:
            self._troop_section.add_troop(troop_id)
        elif cat in _SPELL_CATS:
            self._spell_section.add_troop(troop_id)
        elif cat in _HERO_CATS:
            self._hero_section.add_troop(troop_id)
        elif cat in _PET_CATS:
            self._pet_section.add_troop(troop_id)

    def _on_cap_change(self):
        self._troop_section.set_capacity(self._troop_cap.value())
        self._spell_section.set_capacity(self._spell_cap.value())
        self._settings.set("army_troop_capacity", self._troop_cap.value())
        self._settings.set("army_spell_capacity", self._spell_cap.value())
        self._settings.save()

    def _clear_all(self):
        self._troop_section.clear()
        self._spell_section.clear()
        self._hero_section.clear()
        self._pet_section.clear()

    # ── Persistence ──────────────────────────────────────────────────

    def _save(self):
        data = {
            "troops": self._troop_section.get_composition(),
            "heroes": self._hero_section.get_composition(),
            "pets": self._pet_section.get_composition(),
            "spells": self._spell_section.get_composition(),
        }
        self._settings.set("army_composition", data)
        self._settings.save()

    def _load_composition(self):
        comp = self._settings.get("army_composition", {})
        if not comp:
            return
        # Legacy flat list
        if isinstance(comp, list):
            for entry in sorted(comp, key=lambda e: e.get("order", 0)):
                t = _TROOP_BY_ID.get(entry.get("troop"))
                if not t:
                    continue
                cat = t["category"]
                section = None
                if cat in _TROOP_CATS:
                    section = self._troop_section
                elif cat in _SPELL_CATS:
                    section = self._spell_section
                elif cat in _HERO_CATS:
                    section = self._hero_section
                elif cat in _PET_CATS:
                    section = self._pet_section
                if section:
                    section.add_troop(entry["troop"])
                    for s in section._slots:
                        if s.troop["id"] == entry["troop"]:
                            s.quantity = entry.get("quantity", 1)
            return
        # New format
        if "troops" in comp:
            self._troop_section.load_composition(comp["troops"])
        if "spells" in comp:
            self._spell_section.load_composition(comp["spells"])
        if "heroes" in comp:
            self._hero_section.load_composition(comp["heroes"])
        if "pets" in comp:
            self._pet_section.load_composition(comp["pets"])

    # ── Helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _cap_label(text):
        lbl = QLabel(text)
        lbl.setStyleSheet("color: rgba(255,255,255,0.5); font-size: 11px; font-weight: 600; background: transparent;")
        return lbl

    @staticmethod
    def _spin_css():
        return """
            QSpinBox {
                background: rgba(255,255,255,0.08);
                color: white;
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 6px;
                padding: 2px 6px;
                font-size: 12px; font-weight: 600;
            }
            QSpinBox:focus {
                border-color: rgba(10,132,255,0.6);
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 14px;
                border: none;
                background: transparent;
            }
        """
