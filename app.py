"""Entry point for the Clash of Clans Bot GUI."""

import sys
import os
import logging
import shutil
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from gui.main_window import MainWindow
from gui.theme import apply_theme


def _configure_bundled_tools():
    """When running from a PyInstaller bundle, configure paths to bundled
    ADB and Tesseract binaries so the app is fully self-contained."""
    bundle_dir = getattr(sys, '_MEIPASS', None)
    if not bundle_dir:
        return

    # --- ADB ---
    bundled_adb = os.path.join(bundle_dir, "tools", "adb")
    if os.path.isfile(bundled_adb):
        os.environ["PATH"] = os.path.join(bundle_dir, "tools") + os.pathsep + os.environ.get("PATH", "")
        from bot.settings import Settings
        s = Settings()
        if s.get("adb_path") == "adb":
            s.set("adb_path", bundled_adb)

    # --- Tesseract ---
    bundled_tess = os.path.join(bundle_dir, "tools", "tesseract")
    if os.path.isfile(bundled_tess):
        import pytesseract
        pytesseract.pytesseract.tesseract_cmd = bundled_tess
        # Ensure tesseract finds its own dylibs (not OpenCV's conflicting ones)
        tools_path = os.path.join(bundle_dir, "tools")
        os.environ["DYLD_LIBRARY_PATH"] = tools_path + os.pathsep + os.environ.get("DYLD_LIBRARY_PATH", "")
        # Tesseract needs TESSDATA_PREFIX to find language data
        tessdata = os.path.join(bundle_dir, "tools", "tessdata")
        if os.path.isdir(tessdata):
            os.environ["TESSDATA_PREFIX"] = tessdata


def main():
    _configure_bundled_tools()

    # Log to a writable location (user's home, not inside the .app bundle)
    log_path = os.path.join(os.path.expanduser("~"), ".cocbot", "bot.log")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    root = logging.getLogger("coc")
    root.setLevel(logging.DEBUG)
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    root.addHandler(fh)

    app = QApplication(sys.argv)
    app.styleHints().setColorScheme(Qt.ColorScheme.Dark)
    apply_theme(app)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
