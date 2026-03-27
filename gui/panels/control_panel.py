"""Dashboard panel — bot controls, status, resources, and activity feed."""

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame, QPlainTextEdit,
)


class DashboardPanel(QWidget):
    """Main dashboard tab with controls and live stats."""

    start_requested = Signal(str)
    stop_requested = Signal()
    pause_requested = Signal()
    resume_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._paused = False
        self._attack_count = 0
        self._build_ui()
        self._connect_signals()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ── Status Banner ──
        self._status_frame = QFrame()
        self._status_frame.setStyleSheet(
            "QFrame { background: rgba(255,255,255,0.04); "
            "border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; }"
        )
        status_layout = QHBoxLayout(self._status_frame)
        status_layout.setContentsMargins(16, 12, 16, 12)

        self._status_dot = QLabel()
        self._status_dot.setFixedSize(10, 10)
        self._status_dot.setStyleSheet(
            "background: rgba(255,255,255,0.25); border-radius: 5px; border: none;"
        )
        status_layout.addWidget(self._status_dot)

        self._status_label = QLabel("Ready to start")
        self._status_label.setStyleSheet("font-size: 14px; font-weight: 600;")
        status_layout.addWidget(self._status_label)
        status_layout.addStretch()

        layout.addWidget(self._status_frame)

        # ── Controls Row ──
        ctrl_layout = QHBoxLayout()
        ctrl_layout.setSpacing(8)

        self.start_btn = QPushButton("Start")
        self.start_btn.setProperty("class", "success")
        self.start_btn.setFixedHeight(36)

        self.pause_btn = QPushButton("Pause")
        self.pause_btn.setProperty("class", "warning")
        self.pause_btn.setFixedHeight(36)
        self.pause_btn.setEnabled(False)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setProperty("class", "danger")
        self.stop_btn.setFixedHeight(36)
        self.stop_btn.setEnabled(False)

        ctrl_layout.addWidget(self.start_btn)
        ctrl_layout.addWidget(self.pause_btn)
        ctrl_layout.addWidget(self.stop_btn)
        ctrl_layout.addStretch()

        layout.addLayout(ctrl_layout)

        # ── Resource Cards ──
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(10)

        self._gold_card = self._make_card("GOLD", "0", "#fbbf24")
        self._elixir_card = self._make_card("ELIXIR", "0", "#c084fc")
        self._attacks_card = self._make_card("ATTACKS", "0", "#22c55e")

        cards_layout.addWidget(self._gold_card["frame"])
        cards_layout.addWidget(self._elixir_card["frame"])
        cards_layout.addWidget(self._attacks_card["frame"])

        layout.addLayout(cards_layout)

        # ── Mini Activity Feed ──
        feed_label = QLabel("Recent Activity")
        feed_label.setStyleSheet("color: rgba(255,255,255,0.45); font-size: 11px; "
                                 "font-weight: 600; letter-spacing: 0.5px;")
        layout.addWidget(feed_label)

        self._activity_feed = QPlainTextEdit()
        self._activity_feed.setReadOnly(True)
        self._activity_feed.setMaximumBlockCount(50)
        self._activity_feed.setFixedHeight(160)
        layout.addWidget(self._activity_feed)

        layout.addStretch()

    def _make_card(self, title, value, color):
        frame = QFrame()
        frame.setStyleSheet(
            "QFrame { background: rgba(255,255,255,0.04); "
            "border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; }"
        )
        card_layout = QVBoxLayout(frame)
        card_layout.setContentsMargins(16, 14, 16, 14)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            "color: rgba(255,255,255,0.40); font-size: 10px; "
            "font-weight: 600; letter-spacing: 1px; border: none;"
        )
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        value_lbl = QLabel(value)
        value_lbl.setStyleSheet(
            f"color: {color}; font-size: 24px; font-weight: 700; border: none;"
        )
        value_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card_layout.addWidget(title_lbl)
        card_layout.addWidget(value_lbl)

        return {"frame": frame, "value": value_lbl}

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
        self._set_status("Starting...", "#eab308")
        self.start_requested.emit("farm")

    def _on_stop(self):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setText("Pause")
        self._paused = False
        self._set_status("Stopped", "rgba(255,255,255,0.25)")
        self.stop_requested.emit()

    def _on_pause_toggle(self):
        if self._paused:
            self._paused = False
            self.pause_btn.setText("Pause")
            self._set_status("Resumed", "#22c55e")
            self.resume_requested.emit()
        else:
            self._paused = True
            self.pause_btn.setText("Resume")
            self._set_status("Paused", "#eab308")
            self.pause_requested.emit()

    def _set_status(self, text, dot_color):
        self._status_label.setText(text)
        self._status_dot.setStyleSheet(
            f"background: {dot_color}; border-radius: 5px; border: none;"
        )

    # ── Public API (called by MainWindow) ──

    def update_status(self, text):
        color = "#22c55e" if "running" in text.lower() or "attack" in text.lower() or "farm" in text.lower() else "#eab308"
        self._set_status(text, color)

    def update_resources(self, gold, elixir):
        self._gold_card["value"].setText(f"{gold:,}")
        self._elixir_card["value"].setText(f"{elixir:,}")

    def update_metrics(self, text):
        # Parse attack count from metrics string
        import re
        m = re.search(r"attacks=(\d+)", text)
        if m:
            self._attack_count = int(m.group(1))
            self._attacks_card["value"].setText(str(self._attack_count))

    def append_activity(self, line):
        self._activity_feed.appendPlainText(line)

    def on_bot_stopped(self, reason):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setText("Pause")
        self._paused = False
        self._set_status(f"Stopped — {reason}", "rgba(255,255,255,0.25)")
