"""Bot control toolbar — Liquid Glass with real backdrop blur."""

from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QHBoxLayout, QPushButton, QComboBox, QLabel, QFrame,
)

from gui.glass import GlassToolbar


class ControlPanel(GlassToolbar):
    """Compact glass toolbar for bot controls and live status."""

    start_requested = Signal(str)
    stop_requested = Signal()
    pause_requested = Signal()
    resume_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent,
                         blur_radius=24,
                         corner_radius=14,
                         tint_color=QColor(255, 255, 255, 30),
                         border_color=QColor(255, 255, 255, 80),
                         specular_opacity=0.25)
        self._paused = False
        self._log_panel = None
        self.setFixedHeight(48)
        self._build_ui()
        self._connect_signals()

    def set_log_panel(self, log_panel):
        self._log_panel = log_panel

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 6, 14, 6)
        layout.setSpacing(8)

        self.start_btn = QPushButton("Start")
        self.stop_btn = QPushButton("Stop")
        self.pause_btn = QPushButton("Pause")

        self.stop_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)

        for btn in (self.start_btn, self.stop_btn, self.pause_btn):
            btn.setFixedHeight(30)
            layout.addWidget(btn)

        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.VLine)
        sep1.setFixedHeight(24)
        layout.addWidget(sep1)

        mode_lbl = QLabel("Mode:")
        layout.addWidget(mode_lbl)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Normal", "Farm"])
        self.mode_combo.setFixedWidth(100)
        layout.addWidget(self.mode_combo)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setFixedHeight(24)
        layout.addWidget(sep2)

        self.state_label = QLabel("Idle")
        self.state_label.setStyleSheet("font-weight: 600;")
        layout.addWidget(self.state_label)

        layout.addStretch()

        self.resource_label = QLabel("")
        self.resource_label.setStyleSheet("font-size: 12px;")
        layout.addWidget(self.resource_label)

        sep3 = QFrame()
        sep3.setFrameShape(QFrame.Shape.VLine)
        sep3.setFixedHeight(24)
        layout.addWidget(sep3)

        self.metrics_label = QLabel("")
        self.metrics_label.setStyleSheet("font-size: 12px;")
        layout.addWidget(self.metrics_label)

    def _connect_signals(self):
        self.start_btn.clicked.connect(self._on_start)
        self.stop_btn.clicked.connect(self._on_stop)
        self.pause_btn.clicked.connect(self._on_pause_toggle)

    def _on_start(self):
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.pause_btn.setEnabled(True)
        self.pause_btn.setText("Pause")
        self._paused = False
        self.mode_combo.setEnabled(False)
        self.state_label.setText("Starting...")
        self.start_requested.emit(self.mode_combo.currentText().lower())

    def _on_stop(self):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setText("Pause")
        self._paused = False
        self.mode_combo.setEnabled(True)
        self.state_label.setText("Stopped")
        self.stop_requested.emit()

    def _on_pause_toggle(self):
        if self._paused:
            self._paused = False
            self.pause_btn.setText("Pause")
            self.resume_requested.emit()
        else:
            self._paused = True
            self.pause_btn.setText("Resume")
            self.pause_requested.emit()

    def update_status(self, text: str):
        self.state_label.setText(text)

    def update_resources(self, gold: int, elixir: int):
        self.resource_label.setText(f"Gold {gold:,}  |  Elixir {elixir:,}")

    def update_metrics(self, text: str):
        self.metrics_label.setText(text)

    def append_log(self, line: str):
        if self._log_panel is not None:
            self._log_panel.append_log(line)

    def on_bot_stopped(self, reason: str):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setText("Pause")
        self._paused = False
        self.mode_combo.setEnabled(True)
        self.state_label.setText(f"Stopped — {reason}")
