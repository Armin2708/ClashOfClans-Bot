# ADB Screenrecord Stream Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the mss screen-capture VideoStream with an ADB screenrecord stream so the bot can capture frames in the background without requiring BlueStacks to be visible.

**Architecture:** Two chained subprocesses run in a daemon thread — `adb exec-out screenrecord --output-format=h264 -` pipes a raw H.264 stream into `ffmpeg`, which decodes it to BGR24 raw frames that are pushed into a ring buffer. The public `VideoStream` interface (`start/stop/get_frame/get_clip`) is unchanged so no callers need to be updated. Auto-reconnects on stream death.

**Tech Stack:** Python 3.13, subprocess (stdlib), numpy, ffmpeg (system binary via Homebrew)

---

## File Map

| File | Change |
|------|--------|
| `bot/stream.py` | Full rewrite — replace mss with adb+ffmpeg pipeline |
| `bot/screen.py` | Remove resize hack in `screenshot()`; simplify `init_stream()` |
| `bot/settings.py` | Remove `bluestacks_region`; rename `stream_fps` → keep (unused but harmless) |
| `requirements.txt` | Remove `mss>=9.0` and `pyobjc-framework-Quartz>=9.0` |
| `tests/test_stream_unit.py` | Remove mss-specific tests; unit tests still pass via `__new__` bypass |

---

### Task 1: Rewrite bot/stream.py

**Files:**
- Modify: `bot/stream.py`
- Test: `tests/test_stream_unit.py`

- [ ] **Step 1: Run existing unit tests to establish baseline**

```bash
.venv/bin/python -m pytest tests/test_stream_unit.py -v
```
Expected: all 9 tests PASS (they use `__new__` bypass, independent of implementation)

- [ ] **Step 2: Rewrite bot/stream.py**

```python
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


def _adb_base():
    """Return base ADB command list, inserting -s <device> when configured."""
    from bot.settings import Settings
    s = Settings()
    adb = s.get("adb_path", "adb")
    device = s.get("device_address", "")
    cmd = [adb]
    if device:
        cmd += ["-s", device]
    return cmd


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
        stream.start()          # blocks until resolution is known
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
                    "--time-limit=0",
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
```

- [ ] **Step 3: Run unit tests — all must still pass**

```bash
.venv/bin/python -m pytest tests/test_stream_unit.py -v
```
Expected: 9 tests PASS. The tests use `VideoStream.__new__` and manipulate `_buffer`/`_dead` directly — they are independent of the capture backend.

- [ ] **Step 4: Commit**

```bash
git add bot/stream.py
git commit -m "feat: replace mss VideoStream with adb screenrecord + ffmpeg pipeline"
```

---

### Task 2: Update bot/screen.py

**Files:**
- Modify: `bot/screen.py`

- [ ] **Step 1: Remove the resize hack from screenshot() and simplify init_stream()**

In `bot/screen.py`, replace `init_stream()` and `screenshot()`:

```python
def init_stream() -> None:
    """Create and start the video stream. Call once before the bot loop."""
    global _stream
    settings = Settings()
    fps = settings.get("stream_fps", 30)
    buf = settings.get("stream_buffer_size", 60)
    _stream = VideoStream(fps=fps, buffer_size=buf)
    _stream.start()


def screenshot() -> np.ndarray:
    """Return the latest frame from the video stream as a BGR numpy array."""
    return _stream.get_frame()
```

Also remove the unused PIL/io imports if present (check top of file — `from PIL import Image` and `import io` were from the old ADB screencap implementation).

- [ ] **Step 2: Verify no leftover mss or Quartz imports**

```bash
grep -n "mss\|Quartz\|PIL\|bluestacks_region\|BASE_WIDTH\|BASE_HEIGHT" bot/screen.py
```
Expected: no matches (or only the `BASE_WIDTH/BASE_HEIGHT` import in `check_adb_connection` which is fine).

- [ ] **Step 3: Commit**

```bash
git add bot/screen.py
git commit -m "fix: remove mss resize hack from screenshot(), simplify init_stream()"
```

---

### Task 3: Clean up settings and requirements

**Files:**
- Modify: `bot/settings.py`
- Modify: `requirements.txt`

- [ ] **Step 1: Remove bluestacks_region from settings.py DEFAULTS**

In `bot/settings.py`, in the `DEFAULTS` dict, replace:

```python
    # Video stream
    "stream_fps": 60,
    "stream_buffer_size": 60,
    "bluestacks_region": None,  # [x, y, w, h] — None = auto-detect via Quartz
```

with:

```python
    # Video stream
    "stream_fps": 30,
    "stream_buffer_size": 60,
```

- [ ] **Step 2: Remove mss and Quartz from requirements.txt**

Replace:
```
mss>=9.0
pyobjc-framework-Quartz>=9.0
```
with nothing (delete both lines).

- [ ] **Step 3: Uninstall the removed packages from venv**

```bash
.venv/bin/pip uninstall mss pyobjc-framework-Quartz -y
```

- [ ] **Step 4: Commit**

```bash
git add bot/settings.py requirements.txt
git commit -m "chore: remove mss/Quartz dependencies, drop bluestacks_region setting"
```

---

### Task 4: Integration smoke test

**Files:**
- Read: `scripts/test_stream.py`

- [ ] **Step 1: Verify ffmpeg is installed**

```bash
ffmpeg -version 2>&1 | head -1
```
Expected output contains `ffmpeg version`. If missing: `brew install ffmpeg`

- [ ] **Step 2: Run the integration test with BlueStacks open**

```bash
.venv/bin/python scripts/test_stream.py
```
Expected output:
```
Starting stream (auto-detect BlueStacks window) @ 30fps ...
Waiting for first frame ...
First frame: 2560x1440x3 dtype=uint8  OK
Measuring FPS for 2 seconds ...
Polled N frames in 2.00s -> N.N polls/sec  OK
get_clip(8) returned 8 frames  OK

All checks passed. Stream is working correctly.
```

- [ ] **Step 3: Run full unit test suite**

```bash
.venv/bin/python -m pytest tests/ -v
```
Expected: all tests PASS

- [ ] **Step 4: Run the app**

```bash
./start.sh
```
Expected: GUI opens, bot starts, logs show frames being captured and state detection working.

- [ ] **Step 5: Final commit**

```bash
git add scripts/test_stream.py
git commit -m "test: update stream integration test for adb screenrecord backend"
```
