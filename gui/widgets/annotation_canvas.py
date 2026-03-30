"""Interactive annotation canvas for bounding-box labeling.

Uses QGraphicsView/QGraphicsScene for built-in hit testing, selection,
drag, resize handles, and pan/zoom.
"""

from __future__ import annotations

import hashlib
from enum import Enum, auto

from PySide6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsRectItem,
    QGraphicsEllipseItem, QGraphicsPixmapItem, QGraphicsSimpleTextItem,
)
from PySide6.QtCore import Qt, Signal, QRectF, QPointF
from PySide6.QtGui import (
    QPen, QBrush, QColor, QPainter, QPixmap, QImage, QFont,
)

import numpy as np


# ── Interaction mode ─────────────────────────────────────────────────

class Mode(Enum):
    SELECT = auto()
    DRAW = auto()


# ── Color helper ─────────────────────────────────────────────────────

_CLASS_COLORS: dict[str, QColor] = {}


def _color_for_class(name: str) -> QColor:
    """Deterministic bright color derived from the class name."""
    if name not in _CLASS_COLORS:
        h = int(hashlib.md5(name.encode()).hexdigest()[:8], 16)
        _CLASS_COLORS[name] = QColor.fromHsv(h % 360, 200, 240)
    return _CLASS_COLORS[name]


# ── Handle item (resize grip) ───────────────────────────────────────

_HANDLE_SIZE = 8


class HandleItem(QGraphicsEllipseItem):
    """Small circle at a corner or edge midpoint for resizing the parent BBoxItem."""

    # Position constants
    TL, TC, TR = 0, 1, 2
    ML, MR = 3, 4
    BL, BC, BR = 5, 6, 7

    def __init__(self, position: int, parent: BBoxItem):
        r = _HANDLE_SIZE / 2
        super().__init__(-r, -r, _HANDLE_SIZE, _HANDLE_SIZE, parent)
        self._pos_id = position
        self.setBrush(QBrush(QColor(255, 255, 255, 200)))
        self.setPen(QPen(QColor(0, 0, 0, 180), 1))
        self.setFlag(self.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(self.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setCursor(self._cursor_for_pos(position))
        self.setZValue(10)
        self.setVisible(False)

    @staticmethod
    def _cursor_for_pos(pos: int):
        diag = {0: Qt.CursorShape.SizeFDiagCursor, 2: Qt.CursorShape.SizeBDiagCursor,
                5: Qt.CursorShape.SizeBDiagCursor, 7: Qt.CursorShape.SizeFDiagCursor}
        horiz = {3: Qt.CursorShape.SizeHorCursor, 4: Qt.CursorShape.SizeHorCursor}
        vert = {1: Qt.CursorShape.SizeVerCursor, 6: Qt.CursorShape.SizeVerCursor}
        return diag.get(pos) or horiz.get(pos) or vert.get(pos, Qt.CursorShape.ArrowCursor)

    def itemChange(self, change, value):
        if change == self.GraphicsItemChange.ItemPositionHasChanged:
            self._apply_resize()
        return super().itemChange(change, value)

    def _apply_resize(self):
        parent: BBoxItem = self.parentItem()
        if not parent:
            return
        rect = parent.rect()
        p = self.pos()
        x, y = p.x(), p.y()

        new = QRectF(rect)
        pid = self._pos_id
        if pid in (HandleItem.TL, HandleItem.ML, HandleItem.BL):
            new.setLeft(x)
        if pid in (HandleItem.TR, HandleItem.MR, HandleItem.BR):
            new.setRight(x)
        if pid in (HandleItem.TL, HandleItem.TC, HandleItem.TR):
            new.setTop(y)
        if pid in (HandleItem.BL, HandleItem.BC, HandleItem.BR):
            new.setBottom(y)

        # Enforce minimum size
        if new.width() < 8:
            new.setWidth(8)
        if new.height() < 8:
            new.setHeight(8)

        parent.setRect(new.normalized())
        parent.update_handles()
        parent.update_label()


# ── Bounding box item ────────────────────────────────────────────────

class BBoxItem(QGraphicsRectItem):
    """Interactive bounding box on the canvas."""

    def __init__(self, rect: QRectF, class_name: str, confidence: float = 0.0,
                 is_prediction: bool = True):
        super().__init__(rect)
        self.class_name = class_name
        self.confidence = confidence
        self.is_prediction = is_prediction

        self.setFlag(self.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(self.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(self.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setZValue(5)

        # Handles (created once, shown/hidden on selection)
        self._handles: list[HandleItem] = []
        for i in range(8):
            self._handles.append(HandleItem(i, self))

        # Label tag
        self._label = QGraphicsSimpleTextItem(self)
        self._label.setZValue(11)
        font = QFont("Helvetica Neue", 9)
        font.setBold(True)
        self._label.setFont(font)

        self._update_style()
        self.update_handles()
        self.update_label()

    def _update_style(self):
        color = _color_for_class(self.class_name)
        pen = QPen(color, 2)
        if self.is_prediction:
            pen.setStyle(Qt.PenStyle.DashLine)
        self.setPen(pen)
        fill = QColor(color)
        fill.setAlpha(30)
        self.setBrush(QBrush(fill))

    def update_handles(self):
        r = self.rect()
        positions = [
            r.topLeft(), QPointF(r.center().x(), r.top()), r.topRight(),
            QPointF(r.left(), r.center().y()), QPointF(r.right(), r.center().y()),
            r.bottomLeft(), QPointF(r.center().x(), r.bottom()), r.bottomRight(),
        ]
        for handle, pos in zip(self._handles, positions):
            handle.setPos(pos)

    def update_label(self):
        conf_str = f" {self.confidence:.0%}" if self.confidence > 0 else ""
        self._label.setText(f"{self.class_name}{conf_str}")
        self._label.setBrush(QBrush(QColor(255, 255, 255, 220)))
        r = self.rect()
        self._label.setPos(r.x() + 2, r.y() - 16)

    def set_class(self, name: str):
        self.class_name = name
        self.is_prediction = False
        self.confidence = 0.0
        self._update_style()
        self.update_label()

    def itemChange(self, change, value):
        if change == self.GraphicsItemChange.ItemSelectedHasChanged:
            selected = bool(value)
            for h in self._handles:
                h.setVisible(selected)
            # Thicker border when selected
            pen = self.pen()
            pen.setWidth(3 if selected else 2)
            self.setPen(pen)
        return super().itemChange(change, value)

    def paint(self, painter, option, widget=None):
        # Override to suppress the default dashed selection rectangle
        option.state &= ~option.state.State_Selected
        super().paint(painter, option, widget)


# ── Annotation canvas ────────────────────────────────────────────────

class AnnotationCanvas(QGraphicsView):
    """Zoomable, pannable canvas for image annotation with bounding boxes."""

    box_selected = Signal(object)   # BBoxItem or None
    box_created = Signal(object)    # BBoxItem
    boxes_changed = Signal()        # any modification

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet("background: rgba(0,0,0,0.3); border: none;")

        self._pixmap_item: QGraphicsPixmapItem | None = None
        self._image_bgr: np.ndarray | None = None
        self._mode = Mode.SELECT
        self._drawing = False
        self._draw_start: QPointF | None = None
        self._draw_rect: QGraphicsRectItem | None = None
        self._panning = False
        self._pan_start: QPointF | None = None
        self._last_class = "canon"

        self._scene.selectionChanged.connect(self._on_selection_changed)

    # ── Public API ────────────────────────────────────────────────

    @property
    def mode(self) -> Mode:
        return self._mode

    @mode.setter
    def mode(self, m: Mode):
        self._mode = m
        if m == Mode.DRAW:
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    @property
    def image_bgr(self) -> np.ndarray | None:
        return self._image_bgr

    def load_image(self, bgr: np.ndarray):
        """Display a BGR numpy array on the canvas."""
        self._image_bgr = bgr
        h, w = bgr.shape[:2]
        bytes_per_line = w * 3
        qimg = QImage(bgr.data, w, h, bytes_per_line, QImage.Format.Format_BGR888)
        pixmap = QPixmap.fromImage(qimg)

        self.clear_boxes()
        if self._pixmap_item:
            self._scene.removeItem(self._pixmap_item)
        self._pixmap_item = self._scene.addPixmap(pixmap)
        self._pixmap_item.setZValue(0)
        self._scene.setSceneRect(0, 0, w, h)
        self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def add_box(self, x1: int, y1: int, x2: int, y2: int,
                class_name: str, confidence: float = 0.0,
                is_prediction: bool = True) -> BBoxItem:
        rect = QRectF(x1, y1, x2 - x1, y2 - y1)
        box = BBoxItem(rect, class_name, confidence, is_prediction)
        self._scene.addItem(box)
        self.boxes_changed.emit()
        return box

    def get_boxes(self) -> list[BBoxItem]:
        return [item for item in self._scene.items() if isinstance(item, BBoxItem)]

    def clear_boxes(self):
        for item in self.get_boxes():
            self._scene.removeItem(item)
        self.boxes_changed.emit()

    def selected_box(self) -> BBoxItem | None:
        sel = [i for i in self._scene.selectedItems() if isinstance(i, BBoxItem)]
        return sel[0] if sel else None

    # ── Events ────────────────────────────────────────────────────

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)

    def mousePressEvent(self, event):
        # Middle button pan
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = True
            self._pan_start = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return

        if self._mode == Mode.DRAW and event.button() == Qt.MouseButton.LeftButton:
            pos = self.mapToScene(event.position().toPoint())
            self._drawing = True
            self._draw_start = pos
            self._draw_rect = QGraphicsRectItem(QRectF(pos, pos))
            self._draw_rect.setPen(QPen(QColor(255, 255, 255, 180), 1, Qt.PenStyle.DashLine))
            self._draw_rect.setBrush(QBrush(QColor(255, 255, 255, 30)))
            self._draw_rect.setZValue(20)
            self._scene.addItem(self._draw_rect)
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._panning and self._pan_start:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - int(delta.x()))
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - int(delta.y()))
            event.accept()
            return

        if self._drawing and self._draw_start and self._draw_rect:
            pos = self.mapToScene(event.position().toPoint())
            self._draw_rect.setRect(QRectF(self._draw_start, pos).normalized())
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton and self._panning:
            self._panning = False
            self.setCursor(Qt.CursorShape.CrossCursor if self._mode == Mode.DRAW
                           else Qt.CursorShape.ArrowCursor)
            event.accept()
            return

        if self._drawing and self._draw_rect:
            rect = self._draw_rect.rect()
            self._scene.removeItem(self._draw_rect)
            self._draw_rect = None
            self._drawing = False

            if rect.width() >= 10 and rect.height() >= 10:
                # Clamp to image bounds
                if self._pixmap_item:
                    img_rect = self._pixmap_item.boundingRect()
                    rect = rect.intersected(img_rect)

                box = BBoxItem(rect, self._last_class, 0.0, False)
                self._scene.addItem(box)
                box.setSelected(True)
                self.box_created.emit(box)
                self.boxes_changed.emit()
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete or event.key() == Qt.Key.Key_Backspace:
            for item in list(self._scene.selectedItems()):
                if isinstance(item, BBoxItem):
                    self._scene.removeItem(item)
            self.boxes_changed.emit()
            event.accept()
            return
        if event.key() == Qt.Key.Key_Escape:
            self._scene.clearSelection()
            event.accept()
            return
        super().keyPressEvent(event)

    def _on_selection_changed(self):
        box = self.selected_box()
        self.box_selected.emit(box)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._pixmap_item and not self._image_bgr is None:
            self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
