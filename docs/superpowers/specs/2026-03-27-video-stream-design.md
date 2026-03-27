# Video Stream — Design Spec
**Date:** 2026-03-27
**Phase:** 1 of 3 (Vision pipeline foundation)

## Goal

Replace ADB screencap (`adb exec-out screencap -p`, 200–500ms per frame) with a
continuous scrcpy video stream over localhost. The bot gets a live 60fps feed from
BlueStacks instead of polling for snapshots. Every downstream module (`vision.py`,
`battle.py`, etc.) stays unchanged — they call `screenshot()` and get a BGR numpy
array back, same as before.

## Context

- BlueStacks runs locally; ADB connects to `127.0.0.1:5555` (or whatever
  `device_address` is set to in settings).
- ADB is still used for **input** (tap, swipe, app control). Only screencap is replaced.
- This is the foundation for Phase 2 (YOLOv8 building detection) and Phase 3 (RL).
  `get_clip(n)` is added now at zero cost so video models can use it later.

## Architecture

```
BlueStacks (localhost)
       │  H.264 stream (scrcpy protocol)
       ▼
  bot/stream.py — VideoStream
       │  get_frame() → BGR numpy array
       │  get_clip(n) → list of N frames
       ▼
  bot/screen.py — screenshot()
       │  (unchanged signature)
       ▼
  vision.py / battle.py / resources.py  (zero changes)
```

## Files Changed

| File | Change |
|------|--------|
| `bot/stream.py` | **New.** `VideoStream` class. |
| `bot/screen.py` | Replace `screenshot()` body. Remove screencap code. Add stream init/stop helpers. |
| `gui/bot_worker.py` | Start stream before main loop, stop in finally block. |
| `bot/settings.py` | Add `stream_fps`, `stream_buffer_size` defaults. |
| `requirements.txt` | Add `scrcpy` (py-scrcpy-client). |

## `bot/stream.py` — VideoStream

```python
class VideoStream:
    def __init__(self, device_address: str, fps: int = 60, buffer_size: int = 60)
    def start(self) -> None        # connect, begin decoding frames
    def stop(self) -> None         # disconnect cleanly
    def get_frame(self) -> np.ndarray   # latest BGR frame; blocks up to 5s on startup
    def get_clip(self, n: int) -> list[np.ndarray]  # last N frames (oldest → newest)
```

**Frame buffer:** `collections.deque(maxlen=buffer_size)`. Background thread appends
every decoded frame. `get_frame()` returns `buffer[-1]`. `get_clip(n)` returns
`list(buffer)[-n:]` — returns whatever is available if buffer not yet full.

**Lifecycle:** `start()` creates the scrcpy client pointed at `device_address`,
registers a frame callback that appends to the deque, starts the client in a
background thread. `stop()` calls `client.stop()`.

**Module-level singleton:** `_stream: VideoStream | None = None` in `screen.py`.
`init_stream()` creates and starts it. `shutdown_stream()` stops it.

## `bot/screen.py` — Changes

**Remove:** the entire `screenshot()` implementation (subprocess call to
`adb exec-out screencap -p`, PNG decode, retry logic).

**Replace with:**
```python
def screenshot() -> np.ndarray:
    return _stream.get_frame()
```

**Add:**
```python
def init_stream() -> None:
    global _stream
    addr = Settings().get("device_address", "127.0.0.1:5555")
    fps  = Settings().get("stream_fps", 60)
    buf  = Settings().get("stream_buffer_size", 60)
    _stream = VideoStream(addr, fps=fps, buffer_size=buf)
    _stream.start()

def shutdown_stream() -> None:
    if _stream:
        _stream.stop()
```

All other functions (`tap`, `swipe`, `open_app`, `check_adb_connection`, etc.) are
unchanged — they still use ADB shell commands.

## `gui/bot_worker.py` — Changes

In `run()`, before the main loop:
```python
from bot.screen import init_stream, shutdown_stream
init_stream()
```

In the `finally` block (already exists for cleanup):
```python
shutdown_stream()
```

## Settings Additions (`bot/settings.py`)

```python
"stream_fps": 60,
"stream_buffer_size": 60,   # 1 second of history at 60fps
```

`device_address` already exists in DEFAULTS (`""`). The stream uses it directly.

## Error Handling

| Scenario | Behaviour |
|----------|-----------|
| First frame not ready | `get_frame()` polls at 100ms intervals for up to 5s, then raises `RuntimeError("Stream not ready")` |
| Stream dies mid-session | scrcpy callback thread sets `_dead` flag; `get_frame()` raises `RuntimeError("Stream died")` |
| RuntimeError propagates | Caught by `BotWorker.run()` except block → `error_occurred` signal → circuit breaker stops bot |

No silent fallback to screencap — fail loudly so the user knows the stream dropped.

## Dependencies

```
scrcpy>=2.0   # py-scrcpy-client on PyPI
```

py-scrcpy-client requires `av` (PyAV) for H.264 decoding, which pulls in ffmpeg
binaries automatically on install. No separate ffmpeg install needed.

## Testing

Manual test script `scripts/test_stream.py`:
1. Start stream
2. Grab 10 frames, assert each is a non-empty BGR numpy array with correct dimensions
3. Print achieved FPS over 2 seconds
4. Stop stream cleanly

This can be run standalone: `python scripts/test_stream.py`

## What This Enables

- **Now:** 60fps live feed, ~16ms latency vs 200–500ms. All existing bot logic faster.
- **Phase 2:** `get_clip(n)` feeds N frames to YOLOv8 video model for building detection.
- **Phase 3:** Continuous frame stream feeds RL agent state observations.
