"""Apple Liquid Glass theme (iOS 26 / macOS Tahoe style).

Light translucent glass panels floating over a vibrant gradient background.
Glass is nearly clear with bright specular edge highlights — the background
colour bleeds through, giving each panel a tinted, refractive look.
"""

from PySide6.QtWidgets import QApplication

# ── Design tokens ────────────────────────────────────────────────────
_T = {
    # Glass material
    "glass":           "rgba(255, 255, 255, 0.18)",
    "glass_hover":     "rgba(255, 255, 255, 0.25)",
    "glass_pressed":   "rgba(255, 255, 255, 0.30)",
    "glass_deep":      "rgba(255, 255, 255, 0.12)",
    "glass_input":     "rgba(255, 255, 255, 0.10)",

    # Borders — specular highlight
    "border":          "rgba(255, 255, 255, 0.35)",
    "border_subtle":   "rgba(255, 255, 255, 0.20)",
    "border_bright":   "rgba(255, 255, 255, 0.55)",

    # Text
    "text":            "rgba(255, 255, 255, 0.95)",
    "text2":           "rgba(255, 255, 255, 0.65)",
    "text3":           "rgba(255, 255, 255, 0.40)",
    "text_dark":       "rgba(0, 0, 0, 0.70)",

    # Accent
    "accent":          "#007AFF",
    "accent_light":    "rgba(0, 122, 255, 0.25)",
    "danger":          "#FF3B30",
    "danger_light":    "rgba(255, 59, 48, 0.20)",
    "success":         "#34C759",

    # Radii
    "r":               "16px",
    "r_sm":            "10px",
    "r_lg":            "22px",
    "r_pill":          "100px",

    # Fonts
    "font":            "'Helvetica Neue', 'SF Pro Display', 'Segoe UI', sans-serif",
    "mono":            "Menlo, Consolas, 'Courier New', monospace",
}

# ── Stylesheet ───────────────────────────────────────────────────────
_CSS = """

/* ═══════════════════════ GLOBAL ═══════════════════════ */
QMainWindow {{
    background: transparent;
}}

QWidget {{
    color: {text};
    font-family: {font};
    font-size: 13px;
    background: transparent;
}}

QWidget#_central {{
    background: transparent;
}}

/* ═══════════════════════ TAB WIDGET ═══════════════════════ */
QTabWidget {{
    background: transparent;
}}

QTabWidget::pane {{
    background: {glass};
    border: 1px solid {border};
    border-radius: {r};
    top: -1px;
}}

QTabBar {{
    background: transparent;
    qproperty-drawBase: 0;
}}

QTabBar::tab {{
    background: {glass_deep};
    color: {text2};
    border: 1px solid {border_subtle};
    border-bottom: none;
    border-top-left-radius: {r_sm};
    border-top-right-radius: {r_sm};
    padding: 7px 22px;
    margin-right: 3px;
    font-weight: 500;
    min-width: 60px;
}}

QTabBar::tab:hover {{
    background: {glass};
    color: {text};
    border-color: {border};
}}

QTabBar::tab:selected {{
    background: {glass_hover};
    color: white;
    border: 1px solid {border_bright};
    border-bottom: none;
    font-weight: 600;
}}

/* ═══════════════════════ PUSH BUTTON ═══════════════════════ */
QPushButton {{
    background: {glass};
    color: {text};
    border: 1px solid {border};
    border-radius: {r_sm};
    padding: 6px 20px;
    font-weight: 500;
    min-height: 28px;
}}

QPushButton:hover {{
    background: {glass_hover};
    border-color: {border_bright};
}}

QPushButton:pressed {{
    background: {glass_pressed};
}}

QPushButton:disabled {{
    color: {text3};
    background: rgba(255, 255, 255, 0.06);
    border-color: rgba(255, 255, 255, 0.10);
}}

QPushButton[class="accent"] {{
    background: {accent_light};
    border: 1px solid rgba(0, 122, 255, 0.45);
    color: white;
}}

QPushButton[class="accent"]:hover {{
    background: rgba(0, 122, 255, 0.35);
    border-color: rgba(0, 122, 255, 0.65);
}}

QPushButton[class="danger"] {{
    background: {danger_light};
    border: 1px solid rgba(255, 59, 48, 0.40);
    color: {danger};
}}

QPushButton[class="danger"]:hover {{
    background: rgba(255, 59, 48, 0.30);
}}

/* ═══════════════════════ LABEL ═══════════════════════ */
QLabel {{
    background: transparent;
    border: none;
    padding: 0;
}}

/* ═══════════════════════ GROUP BOX (glass card) ═══════════════════════ */
QGroupBox {{
    background: {glass};
    border: 1px solid {border};
    border-radius: {r};
    margin-top: 16px;
    padding: 20px 16px 14px 16px;
    font-weight: 600;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 14px;
    color: {text2};
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.5px;
}}

/* ═══════════════════════ TEXT EDIT / LOG ═══════════════════════ */
QPlainTextEdit {{
    background: rgba(0, 0, 0, 0.20);
    color: rgba(230, 240, 255, 0.90);
    border: 1px solid {border_subtle};
    border-radius: {r_sm};
    padding: 10px;
    font-family: {mono};
    font-size: 12px;
    selection-background-color: rgba(0, 122, 255, 0.35);
    selection-color: white;
}}

/* ═══════════════════════ LINE EDIT ═══════════════════════ */
QLineEdit {{
    background: {glass_input};
    color: {text};
    border: 1px solid {border_subtle};
    border-radius: {r_sm};
    padding: 6px 12px;
    min-height: 28px;
    selection-background-color: rgba(0, 122, 255, 0.35);
}}

QLineEdit:focus {{
    border-color: rgba(0, 122, 255, 0.60);
    background: rgba(255, 255, 255, 0.14);
}}

QLineEdit:disabled {{
    color: {text3};
    background: rgba(255, 255, 255, 0.04);
}}

/* ═══════════════════════ SPIN BOX ═══════════════════════ */
QSpinBox, QDoubleSpinBox {{
    background: {glass_input};
    color: {text};
    border: 1px solid {border_subtle};
    border-radius: {r_sm};
    padding: 4px 10px;
    min-height: 28px;
}}

QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: rgba(0, 122, 255, 0.60);
    background: rgba(255, 255, 255, 0.14);
}}

QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    background: rgba(255, 255, 255, 0.08);
    border: none;
    border-radius: 4px;
    width: 20px;
    margin: 2px;
}}

QSpinBox::up-button:hover, QSpinBox::down-button:hover,
QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {{
    background: rgba(255, 255, 255, 0.18);
}}

/* ═══════════════════════ COMBO BOX ═══════════════════════ */
QComboBox {{
    background: {glass};
    color: {text};
    border: 1px solid {border};
    border-radius: {r_sm};
    padding: 5px 14px;
    min-height: 28px;
    min-width: 80px;
}}

QComboBox:hover {{
    background: {glass_hover};
    border-color: {border_bright};
}}

QComboBox::drop-down {{
    border: none;
    width: 26px;
    border-top-right-radius: {r_sm};
    border-bottom-right-radius: {r_sm};
}}

QComboBox::down-arrow {{
    image: none;
    border: none;
    width: 0; height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {text2};
    margin-right: 8px;
}}

QComboBox QAbstractItemView {{
    background: rgba(40, 40, 60, 0.92);
    color: {text};
    border: 1px solid {border};
    border-radius: {r_sm};
    selection-background-color: rgba(0, 122, 255, 0.30);
    selection-color: white;
    outline: none;
    padding: 4px;
}}

QComboBox:disabled {{
    color: {text3};
    background: rgba(255, 255, 255, 0.06);
}}

/* ═══════════════════════ SCROLL ═══════════════════════ */
QScrollArea {{
    background: transparent;
    border: none;
}}

QScrollArea > QWidget > QWidget {{
    background: transparent;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 7px;
    margin: 4px 1px;
    border: none;
}}

QScrollBar::handle:vertical {{
    background: rgba(255, 255, 255, 0.20);
    border-radius: 3px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background: rgba(255, 255, 255, 0.35);
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; border: none; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}

QScrollBar:horizontal {{
    background: transparent;
    height: 7px;
    margin: 1px 4px;
    border: none;
}}

QScrollBar::handle:horizontal {{
    background: rgba(255, 255, 255, 0.20);
    border-radius: 3px;
    min-width: 30px;
}}

QScrollBar::handle:horizontal:hover {{
    background: rgba(255, 255, 255, 0.35);
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; border: none; }}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: transparent; }}

/* ═══════════════════════ FRAME ═══════════════════════ */
QFrame {{
    background: transparent;
    border: none;
}}

QFrame[frameShape="4"] {{ background: {border_subtle}; max-height: 1px; }}
QFrame[frameShape="5"] {{ background: {border_subtle}; max-width: 1px; }}

/* ═══════════════════════ SPLITTER ═══════════════════════ */
QSplitter::handle {{ background: {border_subtle}; }}
QSplitter::handle:horizontal {{ width: 1px; }}
QSplitter::handle:vertical {{ height: 1px; }}

/* ═══════════════════════ CHECK BOX ═══════════════════════ */
QCheckBox {{ background: transparent; spacing: 8px; }}
QCheckBox::indicator {{ width: 18px; height: 18px; border: 1.5px solid {border}; border-radius: 5px; background: rgba(255,255,255,0.08); }}
QCheckBox::indicator:checked {{ background: {accent}; border-color: {accent}; }}
QCheckBox::indicator:hover {{ border-color: {border_bright}; }}

/* ═══════════════════════ TOOLTIP ═══════════════════════ */
QToolTip {{
    background: rgba(30, 30, 50, 0.92);
    color: {text};
    border: 1px solid {border};
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 12px;
}}

/* ═══════════════════════ HEADER / TABLE ═══════════════════════ */
QHeaderView::section {{
    background: {glass_deep};
    color: {text2};
    border: none;
    border-right: 1px solid {border_subtle};
    border-bottom: 1px solid {border_subtle};
    padding: 6px 12px;
    font-weight: 600;
    font-size: 12px;
}}

QTableView, QTreeView, QListView {{
    background: rgba(0, 0, 0, 0.12);
    alternate-background-color: rgba(255, 255, 255, 0.03);
    border: 1px solid {border_subtle};
    border-radius: {r_sm};
    gridline-color: rgba(255, 255, 255, 0.06);
    selection-background-color: rgba(0, 122, 255, 0.25);
    selection-color: white;
    outline: none;
}}

/* ═══════════════════════ MENU ═══════════════════════ */
QMenuBar {{ background: transparent; color: {text}; border-bottom: 1px solid {border_subtle}; }}
QMenuBar::item:selected {{ background: rgba(255,255,255,0.12); border-radius: 6px; }}
QMenu {{ background: rgba(30,30,50,0.92); color: {text}; border: 1px solid {border}; border-radius: {r_sm}; padding: 4px; }}
QMenu::item {{ padding: 6px 28px 6px 14px; border-radius: 6px; }}
QMenu::item:selected {{ background: rgba(0,122,255,0.25); }}
QMenu::separator {{ height: 1px; background: {border_subtle}; margin: 4px 8px; }}

""".format(**_T)


def apply_theme(app: QApplication) -> None:
    """Apply the Liquid Glass stylesheet globally."""
    app.setStyleSheet(_CSS)
