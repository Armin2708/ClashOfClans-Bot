"""Simplified glass widgets — CSS-styled containers without heavy rendering."""

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt


class GlassWidget(QWidget):
    """Simple translucent container widget."""

    def __init__(self, parent=None, **kw):
        super().__init__(parent)
        self.setAutoFillBackground(False)


class GlassPanel(GlassWidget):
    """Glass container panel."""
    pass


class GlassToolbar(GlassWidget):
    """Glass toolbar."""
    pass


class GlassButton(GlassWidget):
    """Glass button element."""
    pass
