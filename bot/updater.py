"""Auto-update checker using GitHub Releases API."""

import json
import logging
import os
import urllib.request
import webbrowser
from packaging.version import Version

from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import QThread, Signal, QObject

logger = logging.getLogger("coc.updater")

# Current version — bump this each release to match the GitHub Release tag
APP_VERSION = os.environ.get("APP_VERSION", "1.0.0")

# GitHub repo — releases are checked via the public API (no token needed)
GITHUB_REPO = "Armin2708/ClashOfClans-Bot"
RELEASES_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


class _UpdateCheckWorker(QThread):
    """Background thread that fetches the latest GitHub Release."""
    result_ready = Signal(dict)

    def run(self):
        try:
            req = urllib.request.Request(
                RELEASES_API,
                headers={
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "ClashOfClansBot-Updater",
                },
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            self.result_ready.emit(data)
        except Exception as e:
            logger.debug("Update check failed (non-fatal): %s", e)
            self.result_ready.emit({})


class UpdateChecker(QObject):
    """Check for updates on app launch. Non-blocking, non-intrusive."""

    def __init__(self, parent_window):
        super().__init__(parent_window)
        self._parent = parent_window
        self._worker = None

    def check(self):
        """Start an async update check."""
        self._worker = _UpdateCheckWorker()
        self._worker.result_ready.connect(self._on_result)
        self._worker.start()

    def _on_result(self, data):
        if not data:
            return

        tag = data.get("tag_name", "")  # e.g. "v1.1.0"
        release_notes = data.get("body", "")
        html_url = data.get("html_url", "")  # link to the release page

        if not tag:
            return

        # Strip leading 'v' from tag for version comparison
        remote_version = tag.lstrip("v")

        try:
            if Version(remote_version) <= Version(APP_VERSION):
                logger.debug("App is up to date (v%s)", APP_VERSION)
                return
        except Exception:
            return

        # Find the .dmg asset download URL
        download_url = html_url  # fallback: release page
        for asset in data.get("assets", []):
            if asset.get("name", "").endswith(".dmg"):
                download_url = asset["browser_download_url"]
                break

        logger.info("Update available: v%s -> v%s", APP_VERSION, remote_version)

        msg = QMessageBox(self._parent)
        msg.setWindowTitle("Update Available")
        msg.setText(f"A new version is available: v{remote_version}")
        msg.setInformativeText(
            f"{release_notes}\n\n"
            f"You are running v{APP_VERSION}.\n"
            "Would you like to download the update?"
        )
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.Yes)

        if msg.exec() == QMessageBox.Yes:
            webbrowser.open(download_url)

        self._worker.quit()
        self._worker.wait()
        self._worker = None
