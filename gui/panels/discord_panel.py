"""Discord webhook configuration panel."""

import json
import urllib.request
import urllib.error

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QFormLayout,
    QLineEdit, QPushButton, QLabel, QHBoxLayout,
)

from bot.settings import Settings


class DiscordPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = Settings()
        self._build_ui()
        self._load_settings()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        group = QGroupBox("Discord Settings")
        form = QFormLayout()

        self._url_input = QLineEdit()
        self._url_input.setPlaceholderText("https://discord.com/api/webhooks/...")
        self._url_input.textChanged.connect(self._on_url_changed)
        form.addRow("Webhook URL:", self._url_input)

        btn_row = QHBoxLayout()
        self._test_btn = QPushButton("Test")
        self._test_btn.clicked.connect(self._on_test)
        btn_row.addWidget(self._test_btn)
        btn_row.addStretch()
        form.addRow(btn_row)

        self._status = QLabel("")
        form.addRow("Status:", self._status)

        group.setLayout(form)
        layout.addWidget(group)
        layout.addStretch()

    def _load_settings(self):
        url = self._settings.get("discord_webhook_url", "")
        self._url_input.setText(url)

    def _on_url_changed(self, text):
        self._settings.set("discord_webhook_url", text.strip())
        self._settings.save()

    def _on_test(self):
        url = self._url_input.text().strip()
        if not url:
            self._status.setText("No webhook URL set")
            self._status.setStyleSheet("color: #FF3B30; font-weight: 600;")
            return

        try:
            payload = json.dumps({"content": "COC Bot: test message"}).encode()
            req = urllib.request.Request(
                url,
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "COC-Bot/1.0",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status < 300:
                    self._status.setText("Working")
                    self._status.setStyleSheet("color: #34C759; font-weight: 600;")
                else:
                    self._status.setText(f"Failed: HTTP {resp.status}")
                    self._status.setStyleSheet("color: #FF3B30; font-weight: 600;")
        except urllib.error.HTTPError as e:
            self._status.setText(f"Failed: HTTP {e.code}")
            self._status.setStyleSheet("color: #FF3B30; font-weight: 600;")
        except Exception as e:
            self._status.setText(f"Failed: {e}")
            self._status.setStyleSheet("color: #FF3B30; font-weight: 600;")
