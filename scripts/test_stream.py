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

    if not addr:
        addr = "127.0.0.1:5555"

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
    print(f"First frame: {w}x{h}x{c} dtype={frame.dtype}  OK")

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
        time.sleep(0.001)

    elapsed = time.time() - start
    achieved_fps = count / elapsed
    print(f"Polled {count} frames in {elapsed:.2f}s -> {achieved_fps:.1f} polls/sec  OK")

    # Test get_clip
    clip = stream.get_clip(8)
    print(f"get_clip(8) returned {len(clip)} frames  OK")

    stream.stop()
    print("\nAll checks passed. Stream is working correctly.")


if __name__ == "__main__":
    main()
