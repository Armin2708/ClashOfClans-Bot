"""Refined Glass theme — clean dark translucent aesthetic.

Simplified from the original Liquid Glass: no heavy gradients, no backdrop
blur, no specular highlights. Dark background with subtle glass cards.
"""

from PySide6.QtWidgets import QApplication

# ── Design tokens ────────────────────────────────────────────────────
_T = {
    # Glass material
    "glass":           "rgba(255, 255, 255, 0.06)",
    "glass_hover":     "rgba(255, 255, 255, 0.10)",
    "glass_pressed":   "rgba(255, 255, 255, 0.14)",
    "glass_deep":      "rgba(255, 255, 255, 0.04)",
    "glass_input":     "rgba(255, 255, 255, 0.06)",

    # Borders
    "border":          "rgba(255, 255, 255, 0.10)",
    "border_subtle":   "rgba(255, 255, 255, 0.06)",
    "border_bright":   "rgba(255, 255, 255, 0.18)",
    "border_focus":    "rgba(59, 130, 246, 0.50)",

    # Text
    "text":            "rgba(255, 255, 255, 0.90)",
    "text2":           "rgba(255, 255, 255, 0.45)",
    "text3":           "rgba(255, 255, 255, 0.25)",

    # Accent colors
    "accent":          "#3b82f6",
    "accent_light":    "rgba(59, 130, 246, 0.15)",
    "success":         "#22c55e",
    "success_light":   "rgba(34, 197, 94, 0.12)",
    "warning":         "#eab308",
    "warning_light":   "rgba(234, 179, 8, 0.12)",
    "danger":          "#ef4444",
    "danger_light":    "rgba(239, 68, 68, 0.12)",

    # Game colors
    "gold":            "#fbbf24",
    "elixir":          "#c084fc",

    # Radii
    "r":               "10px",
    "r_sm":            "8px",
    "r_lg":            "14px",

    # Fonts
    "font":            "'Helvetica Neue', 'SF Pro Display', sans-serif",
    "mono":            "'SF Mono', Menlo, Consolas, monospace",
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
    padding: 8px 24px;
    margin-right: 2px;
    font-weight: 500;
    min-width: 70px;
}}

QTabBar::tab:hover {{
    background: {glass_hover};
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
    background: rgba(255, 255, 255, 0.02);
    border-color: rgba(255, 255, 255, 0.04);
}}

QPushButton[class="accent"] {{
    background: {accent_light};
    border: 1px solid rgba(59, 130, 246, 0.30);
    color: {accent};
    font-weight: 600;
}}

QPushButton[class="accent"]:hover {{
    background: rgba(59, 130, 246, 0.22);
    border-color: rgba(59, 130, 246, 0.45);
}}

QPushButton[class="success"] {{
    background: {success_light};
    border: 1px solid rgba(34, 197, 94, 0.25);
    color: {success};
    font-weight: 600;
}}

QPushButton[class="success"]:hover {{
    background: rgba(34, 197, 94, 0.20);
}}

QPushButton[class="warning"] {{
    background: {warning_light};
    border: 1px solid rgba(234, 179, 8, 0.25);
    color: {warning};
    font-weight: 600;
}}

QPushButton[class="danger"] {{
    background: {danger_light};
    border: 1px solid rgba(239, 68, 68, 0.25);
    color: {danger};
    font-weight: 600;
}}

QPushButton[class="danger"]:hover {{
    background: rgba(239, 68, 68, 0.20);
}}

/* ═══════════════════════ LABEL ═══════════════════════ */
QLabel {{
    background: transparent;
    border: none;
    padding: 0;
}}

/* ═══════════════════════ GROUP BOX ═══════════════════════ */
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
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}}

/* ═══════════════════════ TEXT EDIT / LOG ═══════════════════════ */
QPlainTextEdit {{
    background: rgba(0, 0, 0, 0.25);
    color: rgba(200, 220, 240, 0.85);
    border: 1px solid {border};
    border-radius: {r_sm};
    padding: 10px;
    font-family: {mono};
    font-size: 12px;
    selection-background-color: rgba(59, 130, 246, 0.30);
    selection-color: white;
}}

/* ═══════════════════════ LINE EDIT ═══════════════════════ */
QLineEdit {{
    background: {glass_input};
    color: {text};
    border: 1px solid {border};
    border-radius: {r_sm};
    padding: 6px 12px;
    min-height: 28px;
    selection-background-color: rgba(59, 130, 246, 0.30);
}}

QLineEdit:focus {{
    border-color: {border_focus};
    background: rgba(255, 255, 255, 0.08);
}}

QLineEdit:disabled {{
    color: {text3};
    background: rgba(255, 255, 255, 0.02);
}}

/* ═══════════════════════ SPIN BOX ═══════════════════════ */
QSpinBox, QDoubleSpinBox {{
    background: {glass_input};
    color: {text};
    border: 1px solid {border};
    border-radius: {r_sm};
    padding: 4px 10px;
    min-height: 28px;
}}

QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {border_focus};
    background: rgba(255, 255, 255, 0.08);
}}

QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    background: rgba(255, 255, 255, 0.04);
    border: none;
    border-radius: 4px;
    width: 20px;
    margin: 2px;
}}

QSpinBox::up-button:hover, QSpinBox::down-button:hover,
QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {{
    background: rgba(255, 255, 255, 0.10);
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
    background: rgba(25, 25, 45, 0.95);
    color: {text};
    border: 1px solid {border_bright};
    border-radius: {r_sm};
    selection-background-color: rgba(59, 130, 246, 0.25);
    selection-color: white;
    outline: none;
    padding: 4px;
}}

QComboBox:disabled {{
    color: {text3};
    background: rgba(255, 255, 255, 0.02);
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
    width: 6px;
    margin: 4px 1px;
    border: none;
}}

QScrollBar::handle:vertical {{
    background: rgba(255, 255, 255, 0.12);
    border-radius: 3px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background: rgba(255, 255, 255, 0.22);
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; border: none; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}

QScrollBar:horizontal {{
    background: transparent;
    height: 6px;
    margin: 1px 4px;
    border: none;
}}

QScrollBar::handle:horizontal {{
    background: rgba(255, 255, 255, 0.12);
    border-radius: 3px;
    min-width: 30px;
}}

QScrollBar::handle:horizontal:hover {{
    background: rgba(255, 255, 255, 0.22);
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; border: none; }}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: transparent; }}

/* ═══════════════════════ FRAME ═══════════════════════ */
QFrame {{
    background: transparent;
    border: none;
}}

QFrame[frameShape="4"] {{ background: {border}; max-height: 1px; }}
QFrame[frameShape="5"] {{ background: {border}; max-width: 1px; }}

/* ═══════════════════════ CHECK BOX ═══════════════════════ */
QCheckBox {{ background: transparent; spacing: 8px; }}
QCheckBox::indicator {{ width: 18px; height: 18px; border: 1.5px solid {border_bright}; border-radius: 5px; background: rgba(255,255,255,0.04); }}
QCheckBox::indicator:checked {{ background: {accent}; border-color: {accent}; }}
QCheckBox::indicator:hover {{ border-color: {border_focus}; }}

/* ═══════════════════════ TOOLTIP ═══════════════════════ */
QToolTip {{
    background: rgba(20, 20, 38, 0.95);
    color: {text};
    border: 1px solid {border_bright};
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 12px;
}}

""".format(**_T)


def apply_theme(app: QApplication) -> None:
    """Apply the Refined Glass stylesheet globally."""
    app.setStyleSheet(_CSS)
