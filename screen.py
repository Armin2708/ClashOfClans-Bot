import subprocess
import cv2
import numpy as np
import time
from PIL import Image
import io

from config import ADB_PATH, GAME_PACKAGE


def screenshot(max_retries=3, backoff=1):
    """Capture the current screen and return as a numpy array (BGR).
    Retries on failure with exponential backoff."""
    for attempt in range(max_retries):
        try:
            result = subprocess.run(
                [ADB_PATH, "exec-out", "screencap", "-p"],
                capture_output=True
            )
            if result.returncode != 0:
                raise RuntimeError(f"ADB screencap failed: {result.stderr.decode()}")
            if not result.stdout:
                raise RuntimeError("ADB returned empty screenshot")
            image = Image.open(io.BytesIO(result.stdout))
            return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        except Exception as e:
            if attempt < max_retries - 1:
                wait = backoff * (2 ** attempt)
                print(f"[Screen] Screenshot failed (attempt {attempt + 1}/{max_retries}), retrying in {wait}s: {e}")
                time.sleep(wait)
            else:
                raise


def tap(x, y, delay=0.3):
    """Tap at screen coordinates (x, y)."""
    result = subprocess.run([ADB_PATH, "shell", "input", "tap", str(x), str(y)])
    if result.returncode != 0:
        print(f"[Screen] Warning: tap({x}, {y}) failed")
    time.sleep(delay)


def swipe(x1, y1, x2, y2, duration=300):
    """Swipe from (x1,y1) to (x2,y2) over duration milliseconds."""
    result = subprocess.run([
        ADB_PATH, "shell", "input", "swipe",
        str(x1), str(y1), str(x2), str(y2), str(duration)
    ])
    if result.returncode != 0:
        print(f"[Screen] Warning: swipe failed")
    time.sleep(0.5)


def open_app(package=None):
    """Launch Clash of Clans."""
    package = package or GAME_PACKAGE
    subprocess.run([
        ADB_PATH, "shell", "monkey", "-p", package,
        "-c", "android.intent.category.LAUNCHER", "1"
    ])
    time.sleep(10)


def force_stop_app(package=None):
    """Force-stop the app."""
    package = package or GAME_PACKAGE
    subprocess.run([ADB_PATH, "shell", "am", "force-stop", package])


def restart_app(package=None):
    """Force-stop and relaunch the app."""
    print("[Screen] Force-restarting app...")
    force_stop_app(package)
    time.sleep(2)
    open_app(package)


def is_app_running(package=None):
    """Check if CoC is the foreground app."""
    package = package or GAME_PACKAGE
    result = subprocess.run(
        [ADB_PATH, "shell", "pidof", package],
        capture_output=True, text=True
    )
    return result.returncode == 0
