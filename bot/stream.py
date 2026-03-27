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
        clip  = stream.get_clip(8)   # last 8 frames, oldest -> newest
        stream.stop()
    """

    def __init__(self, device_address: str, fps: int = 60, buffer_size: int = 60):
        self._device = device_address
        self._fps = fps
        self._buffer: collections.deque = collections.deque(maxlen=buffer_size)
        self._client = None
        self._dead = False

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

    def get_frame(self, timeout: float = 5.0) -> np.ndarray:
        """Return the latest BGR frame.

        Blocks up to timeout seconds waiting for the first frame.
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

    def get_clip(self, n: int) -> list:
        """Return the last n frames as a list (oldest -> newest).

        Returns fewer than n frames if the buffer is not yet full.
        """
        frames = list(self._buffer)
        return frames[-n:] if frames else []

    def _on_frame(self, frame) -> None:
        if frame is not None:
            self._buffer.append(frame)

    def _on_disconnect(self) -> None:
        logger.error("Video stream disconnected unexpectedly")
        self._dead = True
