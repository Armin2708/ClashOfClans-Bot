"""ADB connection configuration panel."""

import subprocess
import re

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QFormLayout,
    QLineEdit, QPushButton, QLabel, QHBoxLayout,
)
from PySide6.QtCore import Signal

from bot.settings import Settings


class ConnectionPanel(QWidget):
    connection_status_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = Settings()
        self._build_ui()
        self._load_settings()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        group = QGroupBox("ADB Settings")
        form = QFormLayout()

        self._adb_path = QLineEdit()
        self._adb_path.setPlaceholderText("adb")
        form.addRow("ADB Path:", self._adb_path)

        self._device_addr = QLineEdit()
        self._device_addr.setPlaceholderText("localhost:5555")
        form.addRow("Device Address:", self._device_addr)

        btn_row = QHBoxLayout()
        self._connect_btn = QPushButton("Connect")
        self._connect_btn.clicked.connect(self._on_connect)
        btn_row.addWidget(self._connect_btn)

        self._detect_btn = QPushButton("Detect Resolution")
        self._detect_btn.clicked.connect(self._on_detect_resolution)
        btn_row.addWidget(self._detect_btn)
        form.addRow(btn_row)

        self._status = QLabel("Not connected")
        form.addRow("Status:", self._status)

        group.setLayout(form)
        layout.addWidget(group)
        layout.addStretch()

    def _load_settings(self):
        self._adb_path.setText(self._settings.get("adb_path", "adb"))
        self._device_addr.setText(self._settings.get("device_address", ""))

    def _on_connect(self):
        adb = self._adb_path.text().strip() or "adb"
        addr = self._device_addr.text().strip()

        self._settings.set("adb_path", adb)
        self._settings.set("device_address", addr)
        self._settings.save()

        if not addr:
            self._status.setText("No device address specified")
            self._status.setStyleSheet("color: #FF3B30; font-weight: 600;")
            self.connection_status_changed.emit(False)
            return

        try:
            result = subprocess.run(
                [adb, "connect", addr],
                capture_output=True, text=True, timeout=10,
            )
            output = result.stdout.strip()
            if "connected" in output.lower():
                self._status.setText(f"Connected: {addr}")
                self._status.setStyleSheet("color: #34C759; font-weight: 600;")
                self.connection_status_changed.emit(True)
            else:
                self._status.setText(f"Failed: {output or result.stderr.strip()}")
                self._status.setStyleSheet("color: #FF3B30; font-weight: 600;")
                self.connection_status_changed.emit(False)
        except FileNotFoundError:
            self._status.setText(f"ADB not found at '{adb}'")
            self._status.setStyleSheet("color: #FF3B30; font-weight: 600;")
            self.connection_status_changed.emit(False)
        except subprocess.TimeoutExpired:
            self._status.setText("Connection timed out")
            self._status.setStyleSheet("color: #FF3B30; font-weight: 600;")
            self.connection_status_changed.emit(False)

    def _on_detect_resolution(self):
        adb = self._adb_path.text().strip() or "adb"
        addr = self._device_addr.text().strip()

        def _build_cmd(*args):
            cmd = [adb]
            if addr:
                cmd += ["-s", addr]
            cmd += list(args)
            return cmd

        w, h = None, None
        try:
            # Method 1: wm size
            result = subprocess.run(
                _build_cmd("shell", "wm", "size"),
                capture_output=True, text=True, timeout=10,
            )
            match = re.search(r"(\d+)x(\d+)", result.stdout)
            if match:
                w, h = int(match.group(1)), int(match.group(2))

            # Method 2: dumpsys display
            if not w:
                result = subprocess.run(
                    _build_cmd("shell", "dumpsys", "display"),
                    capture_output=True, text=True, timeout=10,
                )
                match = re.search(r"real\s+(\d+)\s*x\s*(\d+)", result.stdout)
                if match:
                    w, h = int(match.group(1)), int(match.group(2))

            # Method 3: screenshot dimensions
            if not w:
                result = subprocess.run(
                    _build_cmd("exec-out", "screencap", "-p"),
                    capture_output=True, timeout=10,
                )
                if result.stdout:
                    from PIL import Image
                    import io
                    img = Image.open(io.BytesIO(result.stdout))
                    w, h = img.size

            if w and h:
                self._settings.set("screen_width", w)
                self._settings.set("screen_height", h)
                self._settings.save()
                self._status.setText(f"Resolution: {w}x{h}")
                self._status.setStyleSheet("color: #34C759; font-weight: 600;")
            else:
                self._status.setText("Could not detect resolution")
                self._status.setStyleSheet("color: #FF3B30; font-weight: 600;")
        except FileNotFoundError:
            self._status.setText(f"ADB not found at '{adb}'")
            self._status.setStyleSheet("color: #FF3B30; font-weight: 600;")
        except subprocess.TimeoutExpired:
            self._status.setText("Detection timed out")
            self._status.setStyleSheet("color: #FF3B30; font-weight: 600;")
