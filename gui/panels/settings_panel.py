"""Settings panel — consolidated connection, farm, and discord settings."""

import subprocess
import re
import json
import urllib.request
import urllib.error

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QFormLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QSpinBox, QCheckBox, QScrollArea,
)
from PySide6.QtCore import Qt

from bot.settings import Settings, BASE_WIDTH, BASE_HEIGHT


class SettingsPanel(QWidget):
    """Consolidated settings: connection, farm thresholds, discord."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = Settings()
        self._build_ui()
        self._load_settings()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        outer.addWidget(scroll)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        scroll.setWidget(container)

        # ── Connection ──
        conn_group = QGroupBox("Connection")
        conn_form = QFormLayout()

        self._device_addr = QLineEdit()
        self._device_addr.setPlaceholderText("localhost:5555")
        conn_form.addRow("Device Address:", self._device_addr)

        btn_row = QHBoxLayout()
        self._connect_btn = QPushButton("Connect")
        self._connect_btn.setProperty("class", "accent")
        self._connect_btn.clicked.connect(self._on_connect)
        btn_row.addWidget(self._connect_btn)
        btn_row.addStretch()
        conn_form.addRow(btn_row)

        self._conn_status = QLabel("Not connected")
        self._conn_status.setStyleSheet("font-weight: 500;")
        conn_form.addRow("Status:", self._conn_status)

        self._resolution_label = QLabel("—")
        conn_form.addRow("Resolution:", self._resolution_label)

        conn_group.setLayout(conn_form)
        layout.addWidget(conn_group)

        # ── Farm Settings ──
        farm_group = QGroupBox("Farm Settings")
        farm_form = QFormLayout()

        farm_form.addRow(
            "Min Loot to Attack:",
            self._create_spinbox("min_loot_to_attack", 0, 20_000_000, 100_000),
        )
        farm_form.addRow(
            "Farm Target Gold:",
            self._create_spinbox("farm_target_gold", 0, 50_000_000, 1_000_000),
        )
        farm_form.addRow(
            "Farm Target Elixir:",
            self._create_spinbox("farm_target_elixir", 0, 50_000_000, 1_000_000),
        )
        farm_form.addRow(
            "Gold Storage Full:",
            self._create_spinbox("gold_storage_full", 0, 50_000_000, 1_000_000),
        )
        farm_form.addRow(
            "Elixir Storage Full:",
            self._create_spinbox("elixir_storage_full", 0, 50_000_000, 1_000_000),
        )

        farm_group.setLayout(farm_form)
        layout.addWidget(farm_group)

        # ── Discord ──
        discord_group = QGroupBox("Discord Notifications")
        discord_form = QFormLayout()

        self._discord_enabled = QCheckBox("Enable Discord notifications")
        self._discord_enabled.stateChanged.connect(
            lambda s: self._save("discord_enabled", s == Qt.CheckState.Checked.value)
        )
        discord_form.addRow(self._discord_enabled)

        self._webhook_url = QLineEdit()
        self._webhook_url.setEchoMode(QLineEdit.EchoMode.Password)
        self._webhook_url.setPlaceholderText("https://discord.com/api/webhooks/...")
        self._webhook_url.textChanged.connect(
            lambda t: self._save("discord_webhook_url", t.strip())
        )
        discord_form.addRow("Webhook URL:", self._webhook_url)

        test_row = QHBoxLayout()
        self._test_btn = QPushButton("Test Webhook")
        self._test_btn.clicked.connect(self._on_test_webhook)
        test_row.addWidget(self._test_btn)

        self._discord_status = QLabel("")
        test_row.addWidget(self._discord_status)
        test_row.addStretch()
        discord_form.addRow(test_row)

        discord_group.setLayout(discord_form)
        layout.addWidget(discord_group)

        layout.addStretch()

    def _load_settings(self):
        self._device_addr.setText(self._settings.get("device_address", ""))
        self._discord_enabled.setChecked(self._settings.get("discord_enabled", True))
        self._webhook_url.setText(self._settings.get("discord_webhook_url", ""))

    def _create_spinbox(self, key, min_val, max_val, step):
        spinbox = QSpinBox()
        spinbox.setRange(min_val, max_val)
        spinbox.setSingleStep(step)
        spinbox.setValue(self._settings.get(key, 0))
        spinbox.valueChanged.connect(lambda v: self._save(key, v))
        return spinbox

    def _save(self, key, value):
        self._settings.set(key, value)
        self._settings.save()

    def _on_connect(self):
        addr = self._device_addr.text().strip()
        adb = self._settings.get("adb_path", "adb")

        self._settings.set("device_address", addr)
        self._settings.save()

        if not addr:
            self._conn_status.setText("No device address specified")
            self._conn_status.setStyleSheet("color: #ef4444; font-weight: 500;")
            return

        try:
            result = subprocess.run(
                [adb, "connect", addr],
                capture_output=True, text=True, timeout=10,
            )
            output = result.stdout.strip()
            if "connected" in output.lower():
                self._conn_status.setText(f"Connected to {addr}")
                self._conn_status.setStyleSheet("color: #22c55e; font-weight: 500;")
                # Auto-detect resolution
                self._detect_resolution(adb, addr)
            else:
                self._conn_status.setText(f"Failed: {output or result.stderr.strip()}")
                self._conn_status.setStyleSheet("color: #ef4444; font-weight: 500;")
        except FileNotFoundError:
            self._conn_status.setText(f"ADB not found at '{adb}'")
            self._conn_status.setStyleSheet("color: #ef4444; font-weight: 500;")
        except subprocess.TimeoutExpired:
            self._conn_status.setText("Connection timed out")
            self._conn_status.setStyleSheet("color: #ef4444; font-weight: 500;")

    def _detect_resolution(self, adb, addr):
        def _cmd(*args):
            cmd = [adb]
            if addr:
                cmd += ["-s", addr]
            cmd += list(args)
            return cmd

        w, h = None, None
        try:
            result = subprocess.run(
                _cmd("shell", "wm", "size"),
                capture_output=True, text=True, timeout=10,
            )
            match = re.search(r"(\d+)x(\d+)", result.stdout)
            if match:
                w, h = int(match.group(1)), int(match.group(2))

            if not w:
                result = subprocess.run(
                    _cmd("shell", "dumpsys", "display"),
                    capture_output=True, text=True, timeout=10,
                )
                match = re.search(r"real\s+(\d+)\s*x\s*(\d+)", result.stdout)
                if match:
                    w, h = int(match.group(1)), int(match.group(2))

            if w and h:
                self._settings.set("screen_width", w)
                self._settings.set("screen_height", h)
                self._settings.save()

                if w == BASE_WIDTH and h == BASE_HEIGHT:
                    self._resolution_label.setText(f"{w}x{h}")
                    self._resolution_label.setStyleSheet("color: #22c55e; font-weight: 500;")
                else:
                    self._resolution_label.setText(
                        f"{w}x{h} (expected {BASE_WIDTH}x{BASE_HEIGHT})"
                    )
                    self._resolution_label.setStyleSheet("color: #eab308; font-weight: 500;")
            else:
                self._resolution_label.setText("Could not detect")
                self._resolution_label.setStyleSheet("color: #ef4444; font-weight: 500;")
        except Exception:
            self._resolution_label.setText("Detection failed")
            self._resolution_label.setStyleSheet("color: #ef4444; font-weight: 500;")

    def _on_test_webhook(self):
        url = self._webhook_url.text().strip()
        if not url:
            self._discord_status.setText("No URL")
            self._discord_status.setStyleSheet("color: #ef4444; font-weight: 500;")
            return

        try:
            payload = json.dumps({"content": "CoC Bot: test message"}).encode()
            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json", "User-Agent": "COC-Bot/1.0"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status < 300:
                    self._discord_status.setText("Working!")
                    self._discord_status.setStyleSheet("color: #22c55e; font-weight: 500;")
                else:
                    self._discord_status.setText(f"HTTP {resp.status}")
                    self._discord_status.setStyleSheet("color: #ef4444; font-weight: 500;")
        except urllib.error.HTTPError as e:
            self._discord_status.setText(f"HTTP {e.code}")
            self._discord_status.setStyleSheet("color: #ef4444; font-weight: 500;")
        except Exception as e:
            self._discord_status.setText(f"Error: {e}")
            self._discord_status.setStyleSheet("color: #ef4444; font-weight: 500;")
