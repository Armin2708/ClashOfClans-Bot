"""Liquid Glass rendering engine — true 3D convex-lens effect.

Each glass element looks like a physical slab of glass sitting on the
surface: bright specular highlight on top catching the light, gradually
fading to a subtle shadow at the bottom, with a border that varies in
brightness around the perimeter (bright top, dim sides, dark bottom).
"""

from PySide6.QtWidgets import QWidget, QGraphicsBlurEffect, QGraphicsScene, QGraphicsPixmapItem
from PySide6.QtCore import Qt, QRect, QRectF, QPoint, QTimer, QPointF
from PySide6.QtGui import (
    QPainter, QColor, QLinearGradient, QRadialGradient, QConicalGradient,
    QPixmap, QPainterPath, QPen, QBrush,
)


def _blur_pixmap(pixmap, radius):
    """Gaussian blur a QPixmap via QGraphicsScene offscreen render."""
    if pixmap.isNull() or radius < 1:
        return pixmap

    scene = QGraphicsScene()
    item = QGraphicsPixmapItem(pixmap)
    effect = QGraphicsBlurEffect()
    effect.setBlurRadius(radius)
    effect.setBlurHints(QGraphicsBlurEffect.BlurHint.QualityHint)
    item.setGraphicsEffect(effect)
    scene.addItem(item)

    result = QPixmap(pixmap.size())
    result.fill(QColor(0, 0, 0, 0))
    p = QPainter(result)
    scene.render(p, QRectF(result.rect()), QRectF(pixmap.rect()))
    p.end()
    return result


def _capture_behind(widget):
    """Grab the pixels behind this widget from the window."""
    top = widget.window()
    if not top:
        return QPixmap()
    pos = widget.mapTo(top, QPoint(0, 0))
    return top.grab(QRect(pos, widget.size()))


class GlassWidget(QWidget):
    """Widget with real backdrop-blur and 3D convex-glass rendering.

    The glass effect has these layers (bottom to top):
      1. Blurred backdrop (the background behind the widget, blurred)
      2. Base tint (semi-transparent white for the glass material)
      3. Top highlight (bright gradient fading down — light catching the top)
      4. Bottom shadow (dark gradient fading up — shadow at the bottom)
      5. Inner glow (radial light from top-center)
      6. Varying-brightness border (bright top → dim bottom, like light
         refracting around the edge of a convex lens)
      7. Top rim line (sharp specular highlight)
      8. Drop shadow (painted below the glass to lift it off the surface)
    """

    def __init__(self, parent=None, **kw):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAutoFillBackground(False)

        self.blur_radius    = kw.get("blur_radius", 28)
        self.tint_color     = kw.get("tint_color", QColor(255, 255, 255, 38))
        self.corner_radius  = kw.get("corner_radius", 18)
        self.specular       = kw.get("specular", 0.40)       # top highlight strength
        self.shadow_opacity = kw.get("shadow_opacity", 0.15)  # bottom shadow strength
        self.border_top     = kw.get("border_top", QColor(255, 255, 255, 140))   # bright
        self.border_bottom  = kw.get("border_bottom", QColor(255, 255, 255, 35)) # dim
        self.border_width   = kw.get("border_width", 1.5)
        self.drop_shadow    = kw.get("drop_shadow", True)

        self._bg_cache = QPixmap()
        self._cache_key = None

        self._timer = QTimer(self)
        self._timer.setInterval(200)
        self._timer.timeout.connect(self._refresh_bg)

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_bg()
        self._timer.start()

    def hideEvent(self, event):
        self._timer.stop()
        super().hideEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._cache_key = None
        self._refresh_bg()

    def _refresh_bg(self):
        if not self.isVisible() or self.width() < 2 or self.height() < 2:
            return
        key = (self.mapToGlobal(QPoint(0, 0)).x(),
               self.mapToGlobal(QPoint(0, 0)).y(),
               self.width(), self.height())
        if key == self._cache_key and not self._bg_cache.isNull():
            return
        raw = _capture_behind(self)
        if raw.isNull():
            return
        self._bg_cache = _blur_pixmap(raw, self.blur_radius)
        self._cache_key = key
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        r = self.corner_radius
        bw = self.border_width

        # Inset rect (inside the drop shadow margin)
        margin = 4 if self.drop_shadow else 0
        gx, gy = margin, margin
        gw, gh = w - margin * 2, h - margin * 2

        # ── 0) Drop shadow ──────────────────────────────────────────
        if self.drop_shadow and gh > 0 and gw > 0:
            shadow_path = QPainterPath()
            shadow_path.addRoundedRect(QRectF(gx + 2, gy + 3, gw, gh), r, r)
            p.setPen(Qt.PenStyle.NoPen)
            # Layered soft shadow
            for i, (dx, dy, blur_a) in enumerate([
                (0, 2, 18), (0, 4, 12), (0, 6, 8),
            ]):
                sp = QPainterPath()
                sp.addRoundedRect(QRectF(gx + dx, gy + dy + i, gw, gh), r, r)
                p.fillPath(sp, QColor(0, 0, 0, blur_a))

        # Clip to glass shape
        glass_rect = QRectF(gx, gy, gw, gh)
        clip = QPainterPath()
        clip.addRoundedRect(glass_rect, r, r)
        p.setClipPath(clip)

        # ── 1) Blurred backdrop ─────────────────────────────────────
        if not self._bg_cache.isNull():
            scaled = self._bg_cache.scaled(
                gw, gh,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            p.drawPixmap(gx, gy, scaled)

        # ── 2) Base tint ────────────────────────────────────────────
        p.fillRect(glass_rect, self.tint_color)

        # ── 3) Top specular highlight ───────────────────────────────
        #    Bright white at the very top, fading to nothing by ~40%
        top_spec = QLinearGradient(0, gy, 0, gy + gh * 0.45)
        a = int(255 * self.specular)
        top_spec.setColorAt(0.0, QColor(255, 255, 255, a))
        top_spec.setColorAt(0.15, QColor(255, 255, 255, int(a * 0.5)))
        top_spec.setColorAt(0.45, QColor(255, 255, 255, 0))
        p.fillRect(glass_rect, top_spec)

        # ── 4) Bottom shadow ────────────────────────────────────────
        #    Dark at the bottom edge, fading up — gives the convex 3D look
        bot_shadow = QLinearGradient(0, gy + gh, 0, gy + gh * 0.6)
        sa = int(255 * self.shadow_opacity)
        bot_shadow.setColorAt(0.0, QColor(0, 0, 0, sa))
        bot_shadow.setColorAt(0.3, QColor(0, 0, 0, int(sa * 0.4)))
        bot_shadow.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.fillRect(glass_rect, bot_shadow)

        # ── 5) Inner glow — radial light from top-center ───────────
        glow = QRadialGradient(gx + gw * 0.5, gy, gw * 0.6)
        glow.setColorAt(0.0, QColor(255, 255, 255, 30))
        glow.setColorAt(0.5, QColor(255, 255, 255, 8))
        glow.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.fillRect(glass_rect, glow)

        # ── 6) Varying-brightness border ────────────────────────────
        #    The border is brightest at the top (light source) and
        #    dimmest at the bottom, like light refracting around glass.
        p.setClipping(False)
        border_rect = QRectF(gx + bw / 2, gy + bw / 2,
                             gw - bw, gh - bw)

        # We draw the border as a rounded rect with a gradient pen.
        # Qt doesn't support gradient pens on rounded rects directly,
        # so we draw four segments with interpolated colors.

        # Top border — brightest
        p.setPen(QPen(self.border_top, bw))
        p.setBrush(Qt.BrushStyle.NoBrush)
        top_path = QPainterPath()
        top_path.moveTo(gx + r, gy + bw / 2)
        top_path.lineTo(gx + gw - r, gy + bw / 2)
        p.drawPath(top_path)

        # Top corners
        # Top-left arc
        tl_path = QPainterPath()
        tl_path.arcMoveTo(QRectF(gx + bw / 2, gy + bw / 2, r * 2, r * 2), 90)
        tl_path.arcTo(QRectF(gx + bw / 2, gy + bw / 2, r * 2, r * 2), 90, 90)
        p.drawPath(tl_path)

        # Top-right arc
        tr_path = QPainterPath()
        tr_path.arcMoveTo(QRectF(gx + gw - r * 2 - bw / 2, gy + bw / 2, r * 2, r * 2), 0)
        tr_path.arcTo(QRectF(gx + gw - r * 2 - bw / 2, gy + bw / 2, r * 2, r * 2), 0, 90)
        p.drawPath(tr_path)

        # Side borders — mid brightness
        mid_color = QColor(
            (self.border_top.red() + self.border_bottom.red()) // 2,
            (self.border_top.green() + self.border_bottom.green()) // 2,
            (self.border_top.blue() + self.border_bottom.blue()) // 2,
            (self.border_top.alpha() + self.border_bottom.alpha()) // 2,
        )
        p.setPen(QPen(mid_color, bw))

        # Left side
        left_path = QPainterPath()
        left_path.moveTo(gx + bw / 2, gy + r)
        left_path.lineTo(gx + bw / 2, gy + gh - r)
        p.drawPath(left_path)

        # Right side
        right_path = QPainterPath()
        right_path.moveTo(gx + gw - bw / 2, gy + r)
        right_path.lineTo(gx + gw - bw / 2, gy + gh - r)
        p.drawPath(right_path)

        # Bottom border — dimmest
        p.setPen(QPen(self.border_bottom, bw))

        bottom_path = QPainterPath()
        bottom_path.moveTo(gx + r, gy + gh - bw / 2)
        bottom_path.lineTo(gx + gw - r, gy + gh - bw / 2)
        p.drawPath(bottom_path)

        # Bottom-left arc
        bl_path = QPainterPath()
        bl_path.arcMoveTo(QRectF(gx + bw / 2, gy + gh - r * 2 - bw / 2, r * 2, r * 2), 180)
        bl_path.arcTo(QRectF(gx + bw / 2, gy + gh - r * 2 - bw / 2, r * 2, r * 2), 180, 90)
        p.drawPath(bl_path)

        # Bottom-right arc
        br_path = QPainterPath()
        br_path.arcMoveTo(QRectF(gx + gw - r * 2 - bw / 2, gy + gh - r * 2 - bw / 2, r * 2, r * 2), 270)
        br_path.arcTo(QRectF(gx + gw - r * 2 - bw / 2, gy + gh - r * 2 - bw / 2, r * 2, r * 2), 270, 90)
        p.drawPath(br_path)

        # ── 7) Top rim — sharp specular line ────────────────────────
        rim_a = int(255 * self.specular * 0.7)
        p.setPen(QPen(QColor(255, 255, 255, rim_a), 1.0))
        p.drawLine(
            QPointF(gx + r + 4, gy + 1.0),
            QPointF(gx + gw - r - 4, gy + 1.0),
        )

        p.end()


class GlassPanel(GlassWidget):
    """Glass container panel — card/group with 3D depth."""

    def __init__(self, parent=None, **kw):
        kw.setdefault("blur_radius", 30)
        kw.setdefault("corner_radius", 20)
        kw.setdefault("tint_color", QColor(255, 255, 255, 42))
        kw.setdefault("specular", 0.35)
        kw.setdefault("shadow_opacity", 0.18)
        kw.setdefault("border_top", QColor(255, 255, 255, 130))
        kw.setdefault("border_bottom", QColor(255, 255, 255, 30))
        kw.setdefault("drop_shadow", True)
        super().__init__(parent, **kw)


class GlassToolbar(GlassWidget):
    """Thin glass toolbar with subtle 3D pop."""

    def __init__(self, parent=None, **kw):
        kw.setdefault("blur_radius", 24)
        kw.setdefault("corner_radius", 14)
        kw.setdefault("tint_color", QColor(255, 255, 255, 32))
        kw.setdefault("specular", 0.30)
        kw.setdefault("shadow_opacity", 0.12)
        kw.setdefault("border_top", QColor(255, 255, 255, 110))
        kw.setdefault("border_bottom", QColor(255, 255, 255, 25))
        kw.setdefault("drop_shadow", True)
        super().__init__(parent, **kw)


class GlassButton(GlassWidget):
    """Small glass element for buttons/badges."""

    def __init__(self, parent=None, **kw):
        kw.setdefault("blur_radius", 16)
        kw.setdefault("corner_radius", 12)
        kw.setdefault("tint_color", QColor(255, 255, 255, 35))
        kw.setdefault("specular", 0.25)
        kw.setdefault("shadow_opacity", 0.10)
        kw.setdefault("border_top", QColor(255, 255, 255, 100))
        kw.setdefault("border_bottom", QColor(255, 255, 255, 20))
        kw.setdefault("drop_shadow", False)
        super().__init__(parent, **kw)
