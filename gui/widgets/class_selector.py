"""Searchable class picker for the 2400+ YOLO detection classes.

Provides category filter buttons and a live-search list to quickly
find and select a class name from the full class registry.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QListWidget, QListWidgetItem, QPushButton, QLabel,
)
from PySide6.QtCore import Signal, Qt

from training.generate.class_registry import (
    ALL_CLASSES, CLASS_INDEX,
    HV_DEFENSES, HV_TRAPS, HV_RESOURCES, HV_ARMY, HV_SPECIAL,
    HEROES, HV_TROOPS_ELIXIR, HV_TROOPS_DARK, SUPER_TROOPS,
    SPELLS_ELIXIR, SPELLS_DARK, PETS, HERO_EQUIPMENT, UI_CLASSES,
    LEGACY_ALIASES,
    _leveled, _bucketed, _equipment_leveled,
)


def _build_categories() -> dict[str, set[str]]:
    """Build category name → set of class names."""
    return {
        "All":       set(ALL_CLASSES),
        "Legacy":    set(LEGACY_ALIASES),
        "Defenses":  set(_leveled(HV_DEFENSES)),
        "Traps":     set(_leveled(HV_TRAPS)),
        "Resources": set(_leveled(HV_RESOURCES)),
        "Army":      set(_leveled(HV_ARMY)),
        "Special":   set(_leveled(HV_SPECIAL)),
        "Heroes":    set(_bucketed(HEROES)),
        "Troops":    set(_leveled(HV_TROOPS_ELIXIR) + _leveled(HV_TROOPS_DARK)
                        + SUPER_TROOPS),
        "Spells":    set(_leveled(SPELLS_ELIXIR) + _leveled(SPELLS_DARK)),
        "Pets":      set(_leveled(PETS)),
        "Equipment": set(_equipment_leveled(HERO_EQUIPMENT)),
        "UI":        set(UI_CLASSES),
    }


class ClassSelector(QWidget):
    """Searchable, category-filtered class selector."""

    class_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._categories = _build_categories()
        self._active_category = "All"
        self._last_class = "canon"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Current class display
        self._current_label = QLabel("Selected: --")
        self._current_label.setStyleSheet(
            "color: rgba(255,255,255,0.9); font-weight: bold; padding: 4px;")
        layout.addWidget(self._current_label)

        # Category filter buttons (flow layout, wrap)
        cat_layout = QHBoxLayout()
        cat_layout.setSpacing(2)
        self._cat_buttons: dict[str, QPushButton] = {}
        for cat_name in self._categories:
            btn = QPushButton(cat_name)
            btn.setFixedHeight(24)
            btn.setCheckable(True)
            btn.setChecked(cat_name == "All")
            btn.setStyleSheet("""
                QPushButton {
                    font-size: 10px; padding: 2px 6px;
                    border-radius: 10px;
                    background: rgba(255,255,255,0.06);
                    color: rgba(255,255,255,0.7);
                    border: 1px solid rgba(255,255,255,0.08);
                }
                QPushButton:checked {
                    background: rgba(59,130,246,0.25);
                    color: #3b82f6;
                    border: 1px solid rgba(59,130,246,0.4);
                }
            """)
            btn.clicked.connect(lambda checked, n=cat_name: self._on_category(n))
            cat_layout.addWidget(btn)
            self._cat_buttons[cat_name] = btn
        cat_layout.addStretch()
        # Wrap in a widget for scrollable overflow
        cat_widget = QWidget()
        cat_widget.setLayout(cat_layout)
        layout.addWidget(cat_widget)

        # Search field
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search classes...")
        self._search.textChanged.connect(self._filter_list)
        layout.addWidget(self._search)

        # Class list
        self._list = QListWidget()
        self._list.setAlternatingRowColors(False)
        self._list.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self._list, stretch=1)

        self._populate_list()

    def set_class(self, name: str):
        """Set the currently displayed class (e.g. when a box is selected)."""
        self._current_label.setText(f"Selected: {name}")
        self._last_class = name

    @property
    def last_class(self) -> str:
        return self._last_class

    def _on_category(self, name: str):
        self._active_category = name
        for cat, btn in self._cat_buttons.items():
            btn.setChecked(cat == name)
        self._filter_list()

    def _populate_list(self):
        self._list.clear()
        cat_set = self._categories.get(self._active_category, set(ALL_CLASSES))
        search = self._search.text().lower().strip()
        for cls_name in ALL_CLASSES:
            if cls_name not in cat_set:
                continue
            if search and search not in cls_name:
                continue
            item = QListWidgetItem(f"[{CLASS_INDEX[cls_name]}] {cls_name}")
            item.setData(Qt.ItemDataRole.UserRole, cls_name)
            self._list.addItem(item)

    def _filter_list(self):
        self._populate_list()

    def _on_item_clicked(self, item: QListWidgetItem):
        cls_name = item.data(Qt.ItemDataRole.UserRole)
        if cls_name:
            self._last_class = cls_name
            self._current_label.setText(f"Selected: {cls_name}")
            self.class_changed.emit(cls_name)
