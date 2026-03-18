"""Main application window — true Liquid Glass with backdrop blur."""

import logging

from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QTabWidget, QTabBar
from PySide6.QtCore import Qt, QPoint, QRectF
from PySide6.QtGui import QPainter, QLinearGradient, QColor, QPainterPath

from gui.log_handler import LogSignalEmitter, QtLogHandler
from gui.bot_worker import BotWorker, BotMode
from gui.panels.control_panel import ControlPanel
from gui.panels.connection_panel import ConnectionPanel
from gui.panels.discord_panel import DiscordPanel
from gui.panels.resource_panel import ResourcePanel
from gui.panels.log_panel import LogPanel
from bot.updater import UpdateChecker


class _GradientBackground(QWidget):
    """Paints a vivid iOS 26-style gradient across the entire window."""

    # Soft, muted gradient — cool teal-blue to gentle lavender-rose
    _STOPS = [
        (0.00, QColor(70,  110, 170)),   # muted steel blue
        (0.30, QColor(100, 120, 180)),   # soft periwinkle
        (0.55, QColor(140, 125, 175)),   # gentle lavender
        (0.80, QColor(170, 135, 165)),   # dusty mauve
        (1.00, QColor(185, 150, 160)),   # warm rose-grey
    ]

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        grad = QLinearGradient(0, 0, self.width(), self.height())
        for pos, color in self._STOPS:
            grad.setColorAt(pos, color)
        p.fillRect(self.rect(), grad)
        p.end()


class MainWindow(QMainWindow):
    """Main window for the Clash of Clans Bot."""

    def __init__(self):
        super().__init__()
        self.worker = None

        self.setWindowTitle("Clash of Clans Bot")
        self.setMinimumSize(1100, 750)

        # Gradient background
        central = _GradientBackground()
        central.setObjectName("_central")
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(8)

        # Control toolbar
        self.control_panel = ControlPanel()
        layout.addWidget(self.control_panel)

        # Tabs — full height
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.addTab(ConnectionPanel(), "Connection")
        self.tabs.addTab(DiscordPanel(), "Discord")
        self.tabs.addTab(ResourcePanel(), "Resources")

        self.log_panel = LogPanel()
        self.tabs.addTab(self.log_panel, "Log")

        layout.addWidget(self.tabs, stretch=1)

        # Wire log panel
        self.control_panel.set_log_panel(self.log_panel)

        # Log handler
        self._log_emitter = LogSignalEmitter()
        self._log_handler = QtLogHandler(self._log_emitter)
        self._log_handler.setLevel(logging.INFO)
        logging.getLogger("coc").addHandler(self._log_handler)
        self._log_emitter.log_message.connect(self.control_panel.append_log)

        # Control signals
        self.control_panel.start_requested.connect(self._start_bot)
        self.control_panel.stop_requested.connect(self._stop_bot)
        self.control_panel.pause_requested.connect(self._pause_bot)
        self.control_panel.resume_requested.connect(self._resume_bot)

        # Update checker
        self._update_checker = UpdateChecker(self)
        self._update_checker.check()

    def _start_bot(self, mode_name):
        mode = BotMode.FARM if mode_name == "farm" else BotMode.NORMAL
        self.worker = BotWorker(mode)
        self.worker.status_changed.connect(self.control_panel.update_status)
        self.worker.resources_updated.connect(self.control_panel.update_resources)
        self.worker.metrics_updated.connect(self.control_panel.update_metrics)
        self.worker.error_occurred.connect(self.control_panel.update_status)
        self.worker.bot_stopped.connect(self.control_panel.on_bot_stopped)
        self.worker.start()

    def _stop_bot(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(5000)
            self.worker = None

    def _pause_bot(self):
        if self.worker and self.worker.isRunning():
            self.worker.pause()

    def _resume_bot(self):
        if self.worker and self.worker.isRunning():
            self.worker.resume()

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(5000)
        event.accept()

    def set_tab_widget(self, index, widget):
        name = self.tabs.tabText(index)
        self.tabs.removeTab(index)
        self.tabs.insertTab(index, widget, name)
