"""Log viewer panel -- a dedicated tab for bot output."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit, QPushButton, QLabel,
)


class LogPanel(QWidget):
    """Read-only log viewer with a clear button."""

    MAX_LOG_LINES = 5000

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Header row with title and clear button
        header = QHBoxLayout()
        title = QLabel("Bot Log")
        title.setStyleSheet("font-weight: 600; font-size: 14px;")
        header.addWidget(title)
        header.addStretch()

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setFixedWidth(70)
        self.clear_btn.setProperty("class", "danger")
        self.clear_btn.clicked.connect(self._clear_log)
        header.addWidget(self.clear_btn)

        layout.addLayout(header)

        # Log text area
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(self.MAX_LOG_LINES)
        self.log_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(self.log_view, stretch=1)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def append_log(self, line: str) -> None:
        """Append a single line and auto-scroll to the bottom."""
        self.log_view.appendPlainText(line)
        self.log_view.moveCursor(QTextCursor.MoveOperation.End)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _clear_log(self):
        self.log_view.clear()
