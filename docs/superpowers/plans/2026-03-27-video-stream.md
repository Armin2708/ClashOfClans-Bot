# Video Stream Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace ADB screencap with a continuous 60fps scrcpy video stream from BlueStacks, making `screenshot()` return a live frame instead of a slow on-demand PNG capture.

**Architecture:** A new `bot/stream.py` holds `VideoStream` which wraps py-scrcpy-client, decodes H.264 frames in a background thread, and stores them in a rolling deque. `bot/screen.py`'s `screenshot()` is replaced with a one-liner that calls `_stream.get_frame()`. All other modules (`vision.py`, `battle.py`, etc.) are untouched.

**Tech Stack:** py-scrcpy-client (`scrcpy` on PyPI), collections.deque, threading, OpenCV numpy arrays (BGR).

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `bot/stream.py` | **Create** | `VideoStream` class — scrcpy connection, frame buffer, get_frame/get_clip |
| `bot/screen.py` | **Modify** | Replace `screenshot()`, add `init_stream`/`shutdown_stream`, remove screencap method 3 from `_detect_resolution()` |
| `gui/bot_worker.py` | **Modify** | Call `init_stream()` before main loop, `shutdown_stream()` in finally |
| `bot/settings.py` | **Modify** | Add `stream_fps: 60`, `stream_buffer_size: 60` to DEFAULTS |
| `requirements.txt` | **Modify** | Add `scrcpy` dependency |
| `scripts/test_stream.py` | **Create** | Standalone integration test — start stream, grab frames, print FPS |
| `tests/test_stream_unit.py` | **Create** | Unit tests for VideoStream with mocked scrcpy client |

---

## Task 1: Add dependency and settings

**Files:**
- Modify: `requirements.txt`
- Modify: `bot/settings.py`

- [ ] **Step 1: Add scrcpy to requirements**

Open `requirements.txt` and add the new dependency:

```
opencv-python>=4.8.0
numpy>=1.20.0
pytesseract>=0.3.10
Pillow>=9.0.0
PySide6>=6.6.0
packaging>=21.0
scrcpy>=2.0
```

- [ ] **Step 2: Install it**

```bash
pip install scrcpy
```

Expected: installs `scrcpy` and its `av` (PyAV) dependency for H.264 decoding. No errors.

- [ ] **Step 3: Add stream settings to DEFAULTS in `bot/settings.py`**

Find the `DEFAULTS` dict (line 40) and add after `"device_address": ""`,:

```python
    # Video stream
    "stream_fps": 60,
    "stream_buffer_size": 60,   # 1 second of history at 60fps
```

- [ ] **Step 4: Commit**

```bash
git add requirements.txt bot/settings.py
git commit -m "feat: add scrcpy dependency and stream settings"
```

---

## Task 2: Create `bot/stream.py`

**Files:**
- Create: `bot/stream.py`
- Create: `tests/test_stream_unit.py`

- [ ] **Step 1: Write the failing unit test**

Create `tests/test_stream_unit.py`:

```python
"""Unit tests for VideoStream — scrcpy client is mocked."""
import collections
import threading
import time
from unittest.mock import MagicMock, patch, call
import numpy as np
import pytest


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_frame(h=1440, w=2560):
    return np.zeros((h, w, 3), dtype=np.uint8)


# ── tests ─────────────────────────────────────────────────────────────────────

class TestVideoStreamGetFrame:
    def test_returns_latest_frame(self):
        """get_frame() returns the most recently buffered frame."""
        from bot.stream import VideoStream

        stream = VideoStream.__new__(VideoStream)
        frame1 = _make_frame()
        frame2 = _make_frame()
        stream._buffer = collections.deque([frame1, frame2], maxlen=60)
        stream._dead = False

        result = stream.get_frame()
        assert result is frame2

    def test_raises_if_dead(self):
        """get_frame() raises RuntimeError immediately when stream is dead."""
        from bot.stream import VideoStream

        stream = VideoStream.__new__(VideoStream)
        stream._buffer = collections.deque(maxlen=60)
        stream._dead = True

        with pytest.raises(RuntimeError, match="Stream died"):
            stream.get_frame()

    def test_raises_on_timeout(self):
        """get_frame() raises RuntimeError if no frame arrives within timeout."""
        from bot.stream import VideoStream

        stream = VideoStream.__new__(VideoStream)
        stream._buffer = collections.deque(maxlen=60)
        stream._dead = False

        with pytest.raises(RuntimeError, match="Stream not ready"):
            stream.get_frame(timeout=0.1)


class TestVideoStreamGetClip:
    def test_returns_last_n_frames(self):
        """get_clip(n) returns the last n frames oldest-to-newest."""
        from bot.stream import VideoStream

        stream = VideoStream.__new__(VideoStream)
        frames = [_make_frame() for _ in range(10)]
        stream._buffer = collections.deque(frames, maxlen=60)
        stream._dead = False

        clip = stream.get_clip(3)
        assert len(clip) == 3
        assert clip[0] is frames[7]
        assert clip[2] is frames[9]

    def test_returns_all_when_fewer_than_n(self):
        """get_clip(n) returns all frames when buffer has fewer than n."""
        from bot.stream import VideoStream

        stream = VideoStream.__new__(VideoStream)
        frames = [_make_frame() for _ in range(5)]
        stream._buffer = collections.deque(frames, maxlen=60)
        stream._dead = False

        clip = stream.get_clip(20)
        assert len(clip) == 5

    def test_empty_buffer_returns_empty_list(self):
        from bot.stream import VideoStream

        stream = VideoStream.__new__(VideoStream)
        stream._buffer = collections.deque(maxlen=60)
        stream._dead = False

        assert stream.get_clip(5) == []


class TestVideoStreamOnFrame:
    def test_frame_appended_to_buffer(self):
        """_on_frame() appends non-None frames to the buffer."""
        from bot.stream import VideoStream

        stream = VideoStream.__new__(VideoStream)
        stream._buffer = collections.deque(maxlen=60)

        frame = _make_frame()
        stream._on_frame(frame)
        assert len(stream._buffer) == 1
        assert stream._buffer[-1] is frame

    def test_none_frame_ignored(self):
        """_on_frame() ignores None frames (scrcpy sends None on first call)."""
        from bot.stream import VideoStream

        stream = VideoStream.__new__(VideoStream)
        stream._buffer = collections.deque(maxlen=60)

        stream._on_frame(None)
        assert len(stream._buffer) == 0

    def test_buffer_respects_maxlen(self):
        """Buffer evicts oldest frames when full."""
        from bot.stream import VideoStream

        stream = VideoStream.__new__(VideoStream)
        stream._buffer = collections.deque(maxlen=3)

        frames = [_make_frame() for _ in range(5)]
        for f in frames:
            stream._on_frame(f)

        assert len(stream._buffer) == 3
        assert list(stream._buffer) == frames[2:]


class TestVideoStreamOnDisconnect:
    def test_sets_dead_flag(self):
        from bot.stream import VideoStream

        stream = VideoStream.__new__(VideoStream)
        stream._dead = False
        stream._on_disconnect()
        assert stream._dead is True
```

- [ ] **Step 2: Run the test — confirm it fails**

```bash
pytest tests/test_stream_unit.py -v
```

Expected: `ModuleNotFoundError: No module named 'bot.stream'` — the module doesn't exist yet.

- [ ] **Step 3: Create `bot/stream.py`**

```python
"""Continuous video stream from BlueStacks via scrcpy protocol."""

import collections
import logging
import time

import numpy as np
import scrcpy

logger = logging.getLogger("coc.stream")


class VideoStream:
    """Wraps py-scrcpy-client to provide a continuous frame buffer.

    Usage:
        stream = VideoStream("127.0.0.1:5555", fps=60, buffer_size=60)
        stream.start()
        frame = stream.get_frame()   # latest BGR numpy array
        clip  = stream.get_clip(8)   # last 8 frames, oldest → newest
        stream.stop()
    """

    def __init__(self, device_address: str, fps: int = 60, buffer_size: int = 60):
        self._device = device_address
        self._fps = fps
        self._buffer: collections.deque = collections.deque(maxlen=buffer_size)
        self._client: scrcpy.Client | None = None
        self._dead = False

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Connect to the device and begin streaming frames."""
        self._dead = False
        self._client = scrcpy.Client(device=self._device, max_fps=self._fps)
        self._client.add_listener(scrcpy.EVENT_FRAME, self._on_frame)
        self._client.add_listener(scrcpy.EVENT_DISCONNECT, self._on_disconnect)
        self._client.start(threaded=True)
        logger.info("Video stream started: %s @ %dfps", self._device, self._fps)

    def stop(self) -> None:
        """Disconnect and clean up."""
        if self._client is not None:
            self._client.stop()
            self._client = None
        logger.info("Video stream stopped")

    # ── frame access ──────────────────────────────────────────────────────────

    def get_frame(self, timeout: float = 5.0) -> np.ndarray:
        """Return the latest BGR frame.

        Blocks up to *timeout* seconds waiting for the first frame.
        Raises RuntimeError if the stream is dead or no frame arrives in time.
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self._dead:
                raise RuntimeError("Stream died — check BlueStacks and ADB connection")
            if self._buffer:
                return self._buffer[-1]
            time.sleep(0.05)
        raise RuntimeError(
            f"Stream not ready: no frame received within {timeout}s. "
            "Is BlueStacks running and ADB connected?"
        )

    def get_clip(self, n: int) -> list[np.ndarray]:
        """Return the last *n* frames as a list (oldest → newest).

        Returns fewer than *n* frames if the buffer is not yet full.
        """
        frames = list(self._buffer)
        return frames[-n:] if frames else []

    # ── internal callbacks ────────────────────────────────────────────────────

    def _on_frame(self, frame: np.ndarray | None) -> None:
        if frame is not None:
            self._buffer.append(frame)

    def _on_disconnect(self) -> None:
        logger.error("Video stream disconnected unexpectedly")
        self._dead = True
```

- [ ] **Step 4: Run the tests — confirm they pass**

```bash
pytest tests/test_stream_unit.py -v
```

Expected output:
```
tests/test_stream_unit.py::TestVideoStreamGetFrame::test_returns_latest_frame PASSED
tests/test_stream_unit.py::TestVideoStreamGetFrame::test_raises_if_dead PASSED
tests/test_stream_unit.py::TestVideoStreamGetFrame::test_raises_on_timeout PASSED
tests/test_stream_unit.py::TestVideoStreamGetClip::test_returns_last_n_frames PASSED
tests/test_stream_unit.py::TestVideoStreamGetClip::test_returns_all_when_fewer_than_n PASSED
tests/test_stream_unit.py::TestVideoStreamGetClip::test_empty_buffer_returns_empty_list PASSED
tests/test_stream_unit.py::TestVideoStreamOnFrame::test_frame_appended_to_buffer PASSED
tests/test_stream_unit.py::TestVideoStreamOnFrame::test_none_frame_ignored PASSED
tests/test_stream_unit.py::TestVideoStreamOnFrame::test_buffer_respects_maxlen PASSED
tests/test_stream_unit.py::TestVideoStreamOnDisconnect::test_sets_dead_flag PASSED

10 passed
```

- [ ] **Step 5: Commit**

```bash
git add bot/stream.py tests/test_stream_unit.py
git commit -m "feat: add VideoStream with scrcpy frame buffer"
```

---

## Task 3: Update `bot/screen.py`

**Files:**
- Modify: `bot/screen.py`

Three changes:
1. Add module-level `_stream` + `init_stream()` + `shutdown_stream()`
2. Replace `screenshot()` body
3. Remove Method 3 (screenshot fallback) from `_detect_resolution()` — it would call `screenshot()` before the stream is initialized

- [ ] **Step 1: Add stream singleton and helpers**

After the logger line (line 13), add:

```python
from bot.stream import VideoStream

_stream: VideoStream | None = None


def init_stream() -> None:
    """Create and start the video stream. Call once before the bot loop."""
    global _stream
    settings = Settings()
    addr = settings.get("device_address", "127.0.0.1:5555")
    fps  = settings.get("stream_fps", 60)
    buf  = settings.get("stream_buffer_size", 60)
    _stream = VideoStream(addr, fps=fps, buffer_size=buf)
    _stream.start()


def shutdown_stream() -> None:
    """Stop the video stream. Call in the bot's finally block."""
    global _stream
    if _stream is not None:
        _stream.stop()
        _stream = None
```

- [ ] **Step 2: Replace `screenshot()`**

Replace the entire `screenshot(max_retries=3, backoff=1)` function (lines 133–156) with:

```python
def screenshot() -> np.ndarray:
    """Return the latest frame from the video stream as a BGR numpy array."""
    return _stream.get_frame()
```

- [ ] **Step 3: Remove Method 3 from `_detect_resolution()`**

`_detect_resolution()` has three fallback methods. Method 3 calls `screenshot()` before the stream exists. Remove it — methods 1 and 2 (`wm size` and `dumpsys display`) are sufficient.

Replace the entire `_detect_resolution()` function (lines 92–130) with:

```python
def _detect_resolution():
    """Detect emulator resolution via wm size or dumpsys display.
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

    return None, None
```

- [ ] **Step 4: Remove now-unused imports**

`PIL` and `io` were only used by the old `screenshot()`. Remove these lines from the top of `screen.py`:

```python
from PIL import Image
import io
```

- [ ] **Step 5: Commit**

```bash
git add bot/screen.py
git commit -m "feat: replace ADB screencap with video stream in screen.py"
```

---

## Task 4: Update `gui/bot_worker.py`

**Files:**
- Modify: `gui/bot_worker.py`

- [ ] **Step 1: Add stream init before the main loop**

In `BotWorker.run()`, the first imports happen inside the function. After the existing imports block (around line 78), add:

```python
        from bot.screen import init_stream, shutdown_stream
```

Then, before the `try:` block that starts the main loop, call:

```python
        init_stream()
```

The full beginning of `run()` after this change looks like:

```python
    def run(self):
        from bot.screen import (
            screenshot, open_app, is_app_running, tap, restart_app,
            wait_for_state, check_adb_connection,
        )
        from bot.screen import init_stream, shutdown_stream
        from bot.vision import (
            find_popup, detect_screen_state, validate_critical_templates,
        )
        # ... rest of imports ...

        init_stream()

        try:
            self.status_changed.emit("Starting...")
            # ... existing code ...
```

- [ ] **Step 2: Add stream shutdown to the finally block**

The `run()` method currently has `except Exception as e:` but no `finally`. Add a `finally` block after the `except`:

```python
        except Exception as e:
            logger.exception("Bot crashed: %s", e)
            self.error_occurred.emit(str(e))
            metrics.log_final()
            self.bot_stopped.emit(f"Crashed: {e}")
        finally:
            shutdown_stream()
```

- [ ] **Step 3: Commit**

```bash
git add gui/bot_worker.py
git commit -m "feat: init and shutdown video stream in BotWorker lifecycle"
```

---

## Task 5: Create integration test script

**Files:**
- Create: `scripts/test_stream.py`

- [ ] **Step 1: Create the test script**

```python
"""
Integration test for the video stream.
Run with BlueStacks open and ADB connected:

    python scripts/test_stream.py

Prints achieved FPS and confirms frames are valid BGR numpy arrays.
"""

import sys
import time
import numpy as np

sys.path.insert(0, ".")  # run from repo root

from bot.settings import Settings
from bot.stream import VideoStream


def main():
    settings = Settings()
    addr = settings.get("device_address", "127.0.0.1:5555")
    fps  = settings.get("stream_fps", 60)
    buf  = settings.get("stream_buffer_size", 60)

    print(f"Connecting to {addr} @ {fps}fps ...")
    stream = VideoStream(addr, fps=fps, buffer_size=buf)
    stream.start()

    # Wait for first frame
    print("Waiting for first frame ...")
    try:
        frame = stream.get_frame(timeout=10)
    except RuntimeError as e:
        print(f"FAILED: {e}")
        stream.stop()
        sys.exit(1)

    h, w, c = frame.shape
    print(f"First frame: {w}x{h}x{c} dtype={frame.dtype}  ✓")

    # Measure FPS over 2 seconds
    print("Measuring FPS for 2 seconds ...")
    count = 0
    start = time.time()
    deadline = start + 2.0
    while time.time() < deadline:
        f = stream.get_frame()
        assert f is not None, "get_frame() returned None"
        assert f.shape == (h, w, c), f"Frame shape changed: {f.shape}"
        count += 1
        time.sleep(0.001)  # ~1000 polls/sec max

    elapsed = time.time() - start
    achieved_fps = count / elapsed
    print(f"Polled {count} frames in {elapsed:.2f}s → {achieved_fps:.1f} polls/sec  ✓")

    # Test get_clip
    clip = stream.get_clip(8)
    print(f"get_clip(8) returned {len(clip)} frames  ✓")

    stream.stop()
    print("\nAll checks passed. Stream is working correctly.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it against live BlueStacks**

Make sure BlueStacks is open with Clash of Clans (or any screen). Then:

```bash
python scripts/test_stream.py
```

Expected output:
```
Connecting to 127.0.0.1:5555 @ 60fps ...
Waiting for first frame ...
First frame: 2560x1440x3 dtype=uint8  ✓
Measuring FPS for 2 seconds ...
Polled 120+ frames in 2.00s → 60.0 polls/sec  ✓
get_clip(8) returned 8 frames  ✓

All checks passed. Stream is working correctly.
```

If `device_address` is empty in your settings, temporarily set it:
```python
# Top of test script, after imports:
Settings().set("device_address", "127.0.0.1:5555")
```

- [ ] **Step 3: Commit**

```bash
git add scripts/test_stream.py
git commit -m "test: add video stream integration test script"
```

---

## Task 6: Smoke test the full bot

**Files:** none — validation only

- [ ] **Step 1: Run the unit test suite to confirm nothing broke**

```bash
pytest tests/ -v
```

Expected: all existing tests pass, 10 new stream unit tests pass.

- [ ] **Step 2: Launch the GUI and start the bot**

```bash
python app.py
```

Click Start. Watch the log panel. Confirm:
- No `RuntimeError` about stream
- "Video stream started: 127.0.0.1:5555 @ 60fps" appears in logs
- Bot progresses through normal states (village detected, attack entered, etc.)
- On Stop, "Video stream stopped" appears in logs

- [ ] **Step 3: Final commit if any fixes were needed**

```bash
git add -p
git commit -m "fix: <describe any issues found during smoke test>"
```
