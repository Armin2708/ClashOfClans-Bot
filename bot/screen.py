import subprocess
import cv2
import numpy as np
import time
import random
import logging
from PIL import Image
import io

from bot.config import ADB_PATH, GAME_PACKAGE, SCREEN_WIDTH, SCREEN_HEIGHT
from bot.settings import Settings

logger = logging.getLogger("coc.screen")


def _adb_cmd(*args):
    """Build an ADB command list, inserting -s <device> when configured."""
    cmd = [ADB_PATH]
    device = Settings().get("device_address", "")
    if device:
        cmd += ["-s", device]
    cmd += list(args)
    return cmd


def check_adb_connection():
    """Verify ADB is connected to an emulator and screen resolution matches config.
    If a device_address is configured, runs 'adb connect' first to ensure the
    TCP connection is alive (not just listed in 'adb devices')."""
    device = Settings().get("device_address", "")

    # If a device address is configured, actively connect (re-establish TCP link)
    if device:
        try:
            result = subprocess.run(
                [ADB_PATH, "connect", device],
                capture_output=True, text=True, timeout=10
            )
            output = result.stdout.strip().lower()
            if "connected" in output or "already connected" in output:
                logger.info("ADB connect: %s", result.stdout.strip())
            else:
                logger.warning("ADB connect returned: %s", result.stdout.strip())
        except Exception as e:
            logger.warning("ADB connect failed: %s", e)

    try:
        result = subprocess.run(
            _adb_cmd("devices"), capture_output=True, text=True, timeout=10
        )
        lines = [l.strip() for l in result.stdout.strip().split("\n")[1:] if l.strip()]
        connected = [l for l in lines if "device" in l and "offline" not in l]
        if not connected:
            logger.error("No ADB devices connected")
            return False
        logger.info("ADB connected: %s", connected[0].split()[0])
    except Exception as e:
        logger.error("ADB connection check failed: %s", e)
        return False

    # Verify the connection actually works (shell responds)
    try:
        result = subprocess.run(
            _adb_cmd("shell", "echo", "ok"),
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0 or "ok" not in result.stdout:
            logger.error("ADB shell not responding (device listed but connection dead)")
            return False
    except Exception as e:
        logger.error("ADB shell test failed: %s", e)
        return False

    w, h = _detect_resolution()
    if w and h:
        from bot.settings import BASE_WIDTH, BASE_HEIGHT
        settings = Settings()
        settings.set("screen_width", w)
        settings.set("screen_height", h)
        if (w, h) == (BASE_WIDTH, BASE_HEIGHT):
            logger.info("Screen resolution verified: %dx%d", w, h)
        else:
            logger.info("Screen resolution detected: %dx%d (base: %dx%d, scaling enabled)",
                        w, h, BASE_WIDTH, BASE_HEIGHT)
    else:
        logger.warning("Could not detect screen resolution, using defaults")

    return True


def _detect_resolution():
    """Detect emulator resolution via wm size, dumpsys display, or screenshot.
    Returns (width, height) or (None, None)."""
    # Method 1: wm size
    try:
        result = subprocess.run(
            _adb_cmd("shell", "wm", "size"), capture_output=True, text=True, timeout=10
        )
        for line in result.stdout.strip().split("\n"):
            if "size" in line.lower():
                parts = line.split(":")[-1].strip().split("x")
                if len(parts) == 2:
                    return int(parts[0]), int(parts[1])
    except Exception:
        pass

    # Method 2: dumpsys display
    try:
        result = subprocess.run(
            _adb_cmd("shell", "dumpsys", "display"),
            capture_output=True, text=True, timeout=10
        )
        import re
        match = re.search(r'real\s+(\d+)\s*x\s*(\d+)', result.stdout)
        if match:
            return int(match.group(1)), int(match.group(2))
    except Exception:
        pass

    # Method 3: take a screenshot and check its dimensions
    try:
        img = screenshot(max_retries=1)
        if img is not None:
            h, w = img.shape[:2]
            return w, h
    except Exception:
        pass

    return None, None


def screenshot(max_retries=3, backoff=1):
    """Capture the current screen and return as a numpy array (BGR).
    Retries on failure with exponential backoff."""
    for attempt in range(max_retries):
        try:
            result = subprocess.run(
                _adb_cmd("exec-out", "screencap", "-p"),
                capture_output=True,
                timeout=10
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
                logger.warning("Screenshot failed (attempt %d/%d), retrying in %ds: %s",
                               attempt + 1, max_retries, wait, e)
                time.sleep(wait)
            else:
                raise


def tap(x, y, delay=0.3, max_retries=3):
    """Tap at screen coordinates (x, y) with human-like jitter.
    Retries up to max_retries times with backoff on failure."""
    jitter_x = x + random.randint(-10, 10)
    jitter_y = y + random.randint(-10, 10)
    jitter_delay = delay * random.uniform(0.5, 1.5)

    for attempt in range(max_retries):
        result = subprocess.run(
            _adb_cmd("shell", "input", "tap", str(jitter_x), str(jitter_y)),
            timeout=10
        )
        if result.returncode == 0:
            break
        wait = 0.5 * (2 ** attempt)
        logger.warning("tap(%d, %d) failed (attempt %d/%d), retrying in %.1fs",
                        x, y, attempt + 1, max_retries, wait)
        time.sleep(wait)
    else:
        logger.warning("tap(%d, %d) failed after %d attempts", x, y, max_retries)

    time.sleep(jitter_delay)


def swipe(x1, y1, x2, y2, duration=300):
    """Swipe from (x1,y1) to (x2,y2) over duration milliseconds."""
    result = subprocess.run(
        _adb_cmd("shell", "input", "swipe",
                 str(x1), str(y1), str(x2), str(y2), str(duration)),
        timeout=10)
    if result.returncode != 0:
        logger.warning("Swipe failed")
    time.sleep(0.5)


def open_app(package=None):
    """Launch Clash of Clans."""
    package = package or GAME_PACKAGE
    subprocess.run(
        _adb_cmd("shell", "monkey", "-p", package,
                 "-c", "android.intent.category.LAUNCHER", "1"),
        timeout=10)
    time.sleep(10)


def force_stop_app(package=None):
    """Force-stop the app."""
    package = package or GAME_PACKAGE
    subprocess.run(_adb_cmd("shell", "am", "force-stop", package), timeout=10)


def restart_app(package=None):
    """Force-stop and relaunch the app."""
    logger.info("Force-restarting app...")
    force_stop_app(package)
    time.sleep(2)
    open_app(package)


def is_app_running(package=None):
    """Check if CoC is the foreground app."""
    package = package or GAME_PACKAGE
    result = subprocess.run(
        _adb_cmd("shell", "pidof", package),
        capture_output=True, text=True,
        timeout=10
    )
    return result.returncode == 0


def wait_for_state(target_state, timeout=10, poll_interval=0.5):
    """Poll screenshots until screen state matches target_state.
    Returns the matching screenshot, or None on timeout."""
    from bot.vision import detect_screen_state
    start = time.time()
    while time.time() - start < timeout:
        img = screenshot()
        state = detect_screen_state(img)
        if state == target_state:
            return img
        time.sleep(poll_interval)
    return None


def tap_and_verify(x, y, expected_state, timeout=5, delay=0.3):
    """Tap at (x, y) then verify the screen transitioned to expected_state.
    Returns the verified screenshot, or None if verification failed."""
    tap(x, y, delay=delay)
    return wait_for_state(expected_state, timeout=timeout)
