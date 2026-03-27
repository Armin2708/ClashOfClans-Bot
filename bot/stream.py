"""Continuous video stream via adb screenrecord piped through ffmpeg.

Background-capable: uses ADB TCP, does not require BlueStacks to be visible.

Pipeline:
    adb exec-out screenrecord --output-format=h264 -
        | ffmpeg -f h264 -i pipe:0 -f rawvideo -pix_fmt bgr24 -
        → numpy frames pushed into ring buffer

Auto-reconnects if either subprocess dies (e.g. ADB disconnect or
Android's built-in 3-minute screenrecord limit).
"""
import collections
import logging
import subprocess
import threading
import time

import numpy as np

logger = logging.getLogger("coc.stream")

_RECONNECT_DELAY = 2.0  # seconds between reconnect attempts
_cached_device: str = ""   # cached auto-detected device serial


def _adb_base():
    """Return base ADB command list with -s <device> when needed.

    If device_address is not configured in settings, auto-detects by
    preferring TCP devices (e.g. localhost:5555 = BlueStacks). Result
    is cached so device listing only runs once per process.
    """
    global _cached_device
    from bot.settings import Settings
    s = Settings()
    adb = s.get("adb_path", "adb")
    device = s.get("device_address", "")
    if not device:
        if not _cached_device:
            _cached_device = _auto_detect_device(adb)
        device = _cached_device
    cmd = [adb]
    if device:
        cmd += ["-s", device]
    return cmd


def _auto_detect_device(adb: str) -> str:
    """Return the best ADB device serial, preferring TCP (BlueStacks).

    With a single device, returns its serial. With multiple devices,
    prefers any TCP address (host:port). Returns "" on failure.
    """
    try:
        result = subprocess.run(
            [adb, "devices"], capture_output=True, text=True, timeout=5
        )
        lines = [
            l.strip() for l in result.stdout.strip().splitlines()[1:]
            if l.strip() and "\tdevice" in l
        ]
        if len(lines) == 1:
            return lines[0].split()[0]
        for line in lines:
            serial = line.split()[0]
            if ":" in serial:   # TCP device like localhost:5555
                return serial
        if lines:
            return lines[0].split()[0]
    except Exception as e:
        logger.warning("Device auto-detection failed: %s", e)
    return ""


def _query_resolution():
    """Return (width, height) of Android display via `adb shell wm size`.

    Returns (None, None) on failure.
    """
    try:
        result = subprocess.run(
            _adb_base() + ["shell", "wm", "size"],
            capture_output=True, text=True, timeout=10,
        )
        for line in result.stdout.strip().splitlines():
            if "size" in line.lower():
                parts = line.split(":")[-1].strip().split("x")
                if len(parts) == 2:
                    return int(parts[0]), int(parts[1])
    except Exception as e:
        logger.warning("Resolution query failed: %s", e)
    return None, None


class VideoStream:
    """Continuous frame buffer fed by adb screenrecord + ffmpeg.

    Usage::

        stream = VideoStream(buffer_size=60)
        stream.start()               # queries ADB resolution, starts thread
        frame = stream.get_frame()   # latest BGR numpy array
        stream.stop()
    """

    def __init__(self, fps: int = 30, buffer_size: int = 60):
        # fps is unused (rate is set by the device) but kept for API compat
        self._fps = fps
        self._buffer: collections.deque = collections.deque(maxlen=buffer_size)
        self._dead: bool = False
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._width: int | None = None
        self._height: int | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Query ADB resolution and start the capture thread.

        Raises RuntimeError if ADB is not connected.
        """
        w, h = _query_resolution()
        if w is None:
            raise RuntimeError(
                "Cannot start stream: ADB resolution query failed. "
                "Is ADB connected and BlueStacks running?"
            )
        self._width = w
        self._height = h
        logger.info("Stream resolution: %dx%d", w, h)
        self._stop_event.clear()
        self._dead = False
        self._thread = threading.Thread(
            target=self._capture_loop, daemon=True, name="adb-stream"
        )
        self._thread.start()

    def stop(self) -> None:
        """Signal the capture thread to stop and wait for it to finish."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def get_frame(self, timeout: float = 5.0) -> np.ndarray:
        """Return the most recent BGR frame.

        Blocks up to *timeout* seconds waiting for the first frame.
        Raises RuntimeError if the stream has died or timed out.
        """
        if self._dead:
            raise RuntimeError("Stream died")
        if not self._buffer:
            deadline = time.monotonic() + timeout
            while not self._buffer:
                if self._dead:
                    raise RuntimeError("Stream died")
                if time.monotonic() > deadline:
                    raise RuntimeError(
                        f"Stream not ready: no frames within {timeout}s timeout"
                    )
                time.sleep(0.05)
        return self._buffer[-1]

    def get_clip(self, n: int) -> list:
        """Return the last *n* frames as a list, oldest → newest."""
        frames = list(self._buffer)
        return frames[-n:] if len(frames) >= n else frames

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _capture_loop(self) -> None:
        """Background thread: run adb+ffmpeg, push frames, auto-reconnect."""
        frame_bytes = self._width * self._height * 3  # BGR24 = 3 bytes/pixel

        while not self._stop_event.is_set():
            adb_proc = None
            ff_proc = None
            try:
                adb_cmd = _adb_base() + [
                    "exec-out", "screenrecord",
                    "--output-format=h264",
                    "--time-limit=180",
                    "-",
                ]
                ff_cmd = [
                    "ffmpeg", "-loglevel", "quiet",
                    "-f", "h264", "-i", "pipe:0",
                    "-f", "rawvideo", "-pix_fmt", "bgr24",
                    "-",
                ]
                adb_proc = subprocess.Popen(
                    adb_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                )
                ff_proc = subprocess.Popen(
                    ff_cmd,
                    stdin=adb_proc.stdout,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                )
                # Close parent's copy so ffmpeg's close propagates SIGPIPE to adb
                adb_proc.stdout.close()

                logger.info("ADB screenrecord stream started")

                while not self._stop_event.is_set():
                    raw = ff_proc.stdout.read(frame_bytes)
                    if len(raw) < frame_bytes:
                        logger.warning(
                            "Stream ended (got %d/%d bytes) — reconnecting in %.1fs",
                            len(raw), frame_bytes, _RECONNECT_DELAY,
                        )
                        break
                    frame = np.frombuffer(raw, dtype=np.uint8).reshape(
                        (self._height, self._width, 3)
                    )
                    self._buffer.append(frame)

            except Exception as e:
                logger.warning(
                    "Stream error: %s — reconnecting in %.1fs", e, _RECONNECT_DELAY
                )
            finally:
                for proc in (ff_proc, adb_proc):
                    if proc is not None:
                        try:
                            proc.terminate()
                        except Exception:
                            pass

            if not self._stop_event.is_set():
                time.sleep(_RECONNECT_DELAY)

        self._dead = True
        logger.info("ADB screenrecord stream stopped")
