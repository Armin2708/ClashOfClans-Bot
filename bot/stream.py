"""Continuous video stream from BlueStacks window via mss screen capture (macOS)."""

import collections
import logging
import threading
import time

import cv2
import mss
import numpy as np

logger = logging.getLogger("coc.stream")


def _find_bluestacks_region():
    """Auto-detect the BlueStacks window bounds on macOS using Quartz.
    Returns (x, y, width, height) or None if not found.
    """
    try:
        from Quartz import CGWindowListCopyWindowInfo, kCGWindowListOptionOnScreenOnly, kCGNullWindowID
        windows = CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly, kCGNullWindowID)
        for win in windows:
            owner = win.get("kCGWindowOwnerName", "")
            if "bluestacks" in owner.lower():
                bounds = win.get("kCGWindowBounds", {})
                x = int(bounds.get("X", 0))
                y = int(bounds.get("Y", 0))
                w = int(bounds.get("Width", 0))
                h = int(bounds.get("Height", 0))
                if w > 100 and h > 100:
                    logger.info("Found BlueStacks window: %dx%d at (%d, %d)", w, h, x, y)
                    return x, y, w, h
        logger.warning("BlueStacks window not found — is it running?")
    except ImportError:
        logger.warning("pyobjc-framework-Quartz not available for window auto-detection")
    except Exception as e:
        logger.warning("Window auto-detection failed: %s", e)
    return None


class VideoStream:
    """Captures the BlueStacks window at ~60fps using mss screen capture.

    Usage:
        stream = VideoStream(fps=60, buffer_size=60)
        stream.start()
        frame = stream.get_frame()   # latest BGR numpy array
        clip  = stream.get_clip(8)   # last 8 frames, oldest -> newest
        stream.stop()
    """

    def __init__(self, region=None, fps: int = 60, buffer_size: int = 60):
        self._region = region  # (x, y, w, h) or None = auto-detect
        self._fps = fps
        self._buffer: collections.deque = collections.deque(maxlen=buffer_size)
        self._thread = None
        self._stop_event = threading.Event()
        self._dead = False

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Auto-detect BlueStacks window and start the capture thread."""
        if self._region is None:
            self._region = _find_bluestacks_region()
        if self._region is None:
            raise RuntimeError(
                "Could not auto-detect BlueStacks window. "
                "Set bluestacks_region in settings: [x, y, width, height]"
            )
        self._dead = False
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        logger.info("Video stream started @ %dfps region=%s", self._fps, self._region)

    def stop(self) -> None:
        """Stop the capture thread cleanly."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None
        logger.info("Video stream stopped")

    # ── frame access ──────────────────────────────────────────────────────────

    def get_frame(self, timeout: float = 5.0) -> np.ndarray:
        """Return the latest BGR frame.

        Blocks up to timeout seconds waiting for the first frame.
        Raises RuntimeError if the stream dies or no frame arrives in time.
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self._dead:
                raise RuntimeError("Stream died — is BlueStacks still running?")
            if self._buffer:
                return self._buffer[-1]
            time.sleep(0.05)
        raise RuntimeError(
            f"Stream not ready: no frame received within {timeout}s. "
            "Is BlueStacks running?"
        )

    def get_clip(self, n: int) -> list:
        """Return the last n frames as a list (oldest -> newest).

        Returns fewer than n frames if the buffer is not yet full.
        """
        frames = list(self._buffer)
        return frames[-n:] if frames else []

    # ── capture loop ──────────────────────────────────────────────────────────

    def _capture_loop(self) -> None:
        """Background thread: grab frames from the BlueStacks window at target FPS."""
        x, y, w, h = self._region
        monitor = {"left": x, "top": y, "width": w, "height": h}
        interval = 1.0 / self._fps

        try:
            with mss.mss() as sct:
                while not self._stop_event.is_set():
                    t0 = time.perf_counter()

                    raw = sct.grab(monitor)
                    frame = cv2.cvtColor(np.array(raw), cv2.COLOR_BGRA2BGR)
                    self._buffer.append(frame)

                    # Throttle to target FPS
                    elapsed = time.perf_counter() - t0
                    sleep_time = interval - elapsed
                    if sleep_time > 0:
                        time.sleep(sleep_time)

        except Exception as e:
            logger.error("Capture loop died: %s", e)
            self._dead = True
