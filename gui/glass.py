"""Glass widget stubs — CSS-styled containers, no backdrop blur engine.

These are lightweight QWidget subclasses that rely on the global stylesheet
for their appearance. The previous blur/specular rendering engine has been
removed in favor of pure CSS glass effects defined in gui/theme.py.
"""

from PySide6.QtWidgets import QWidget


class GlassWidget(QWidget):
    """Base glass container — styled via the global stylesheet."""

    def __init__(self, parent=None, **kw):
        super().__init__(parent)


class GlassPanel(GlassWidget):
    """Glass container panel — card/group styling."""
    pass


class GlassToolbar(GlassWidget):
    """Glass toolbar container."""
    pass


class GlassButton(GlassWidget):
    """Small glass element for buttons/badges."""
    pass
