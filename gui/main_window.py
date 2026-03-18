"""Main application window — Refined Glass with onboarding gate."""

import logging

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTabWidget, QStackedWidget,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QLinearGradient, QColor

from gui.log_handler import LogSignalEmitter, QtLogHandler
from gui.bot_worker import BotWorker, BotMode
from gui.panels.control_panel import DashboardPanel
from gui.panels.settings_panel import SettingsPanel
from gui.panels.log_panel import LogPanel
from gui.onboarding import OnboardingWidget
from bot.settings import Settings
from bot.updater import UpdateChecker


class _GradientBackground(QWidget):
    """Dark gradient background for the app."""

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        grad = QLinearGradient(0, 0, self.width(), self.height())
        grad.setColorAt(0.0, QColor(25, 25, 45))
        grad.setColorAt(0.5, QColor(20, 22, 40))
        grad.setColorAt(1.0, QColor(18, 18, 38))
        p.fillRect(self.rect(), grad)
        p.end()


class MainWindow(QMainWindow):
    """Main window with onboarding gate and 3-tab layout."""

    def __init__(self):
        super().__init__()
        self.worker = None
        self._settings = Settings()

        self.setWindowTitle("Clash of Clans Bot")
        self.setMinimumSize(900, 650)

        # Gradient background
        central = _GradientBackground()
        central.setObjectName("_central")
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Stack: onboarding or main app
        self._stack = QStackedWidget()
        layout.addWidget(self._stack)

        # Onboarding
        self._onboarding = OnboardingWidget()
        self._onboarding.completed.connect(self._on_onboarding_done)
        self._stack.addWidget(self._onboarding)

        # Main app container
        self._main_widget = QWidget()
        main_layout = QVBoxLayout(self._main_widget)
        main_layout.setContentsMargins(12, 10, 12, 12)
        main_layout.setSpacing(8)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        self.dashboard = DashboardPanel()
        self.tabs.addTab(self.dashboard, "Dashboard")

        self.settings_panel = SettingsPanel()
        self.tabs.addTab(self.settings_panel, "Settings")

        self.log_panel = LogPanel()
        self.tabs.addTab(self.log_panel, "Log")

        main_layout.addWidget(self.tabs, stretch=1)
        self._stack.addWidget(self._main_widget)

        # Show onboarding or main app
        if self._settings.get("onboarding_completed", False):
            self._stack.setCurrentWidget(self._main_widget)
        else:
            self._stack.setCurrentWidget(self._onboarding)

        # Log handler
        self._log_emitter = LogSignalEmitter()
        self._log_handler = QtLogHandler(self._log_emitter)
        self._log_handler.setLevel(logging.INFO)
        logging.getLogger("coc").addHandler(self._log_handler)
        self._log_emitter.log_message.connect(self._on_log_message)

        # Control signals
        self.dashboard.start_requested.connect(self._start_bot)
        self.dashboard.stop_requested.connect(self._stop_bot)
        self.dashboard.pause_requested.connect(self._pause_bot)
        self.dashboard.resume_requested.connect(self._resume_bot)

        # Update checker
        self._update_checker = UpdateChecker(self)
        self._update_checker.check()

    def _on_onboarding_done(self):
        self._settings.set("onboarding_completed", True)
        self._settings.save()
        self._stack.setCurrentWidget(self._main_widget)

    def _on_log_message(self, line):
        self.log_panel.append_log(line)
        self.dashboard.append_activity(line)

    def _start_bot(self, mode_name):
        mode = BotMode.FARM if mode_name == "farm" else BotMode.NORMAL
        self.worker = BotWorker(mode)
        self.worker.status_changed.connect(self.dashboard.update_status)
        self.worker.resources_updated.connect(self.dashboard.update_resources)
        self.worker.metrics_updated.connect(self.dashboard.update_metrics)
        self.worker.error_occurred.connect(self.dashboard.update_status)
        self.worker.bot_stopped.connect(self.dashboard.on_bot_stopped)
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
