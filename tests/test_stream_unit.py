"""Unit tests for VideoStream — scrcpy client is mocked."""
import collections
import threading
import time
from unittest.mock import MagicMock, patch, call
import numpy as np
import pytest


def _make_frame(h=1440, w=2560):
    return np.zeros((h, w, 3), dtype=np.uint8)


class TestVideoStreamGetFrame:
    def test_returns_latest_frame(self):
        from bot.stream import VideoStream
        stream = VideoStream.__new__(VideoStream)
        frame1 = _make_frame()
        frame2 = _make_frame()
        stream._buffer = collections.deque([frame1, frame2], maxlen=60)
        stream._dead = False
        result = stream.get_frame()
        assert result is frame2

    def test_raises_if_dead(self):
        from bot.stream import VideoStream
        stream = VideoStream.__new__(VideoStream)
        stream._buffer = collections.deque(maxlen=60)
        stream._dead = True
        with pytest.raises(RuntimeError, match="Stream died"):
            stream.get_frame()

    def test_raises_on_timeout(self):
        from bot.stream import VideoStream
        stream = VideoStream.__new__(VideoStream)
        stream._buffer = collections.deque(maxlen=60)
        stream._dead = False
        with pytest.raises(RuntimeError, match="Stream not ready"):
            stream.get_frame(timeout=0.1)


class TestVideoStreamGetClip:
    def test_returns_last_n_frames(self):
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
        from bot.stream import VideoStream
        stream = VideoStream.__new__(VideoStream)
        stream._buffer = collections.deque(maxlen=60)
        frame = _make_frame()
        stream._on_frame(frame)
        assert len(stream._buffer) == 1
        assert stream._buffer[-1] is frame

    def test_none_frame_ignored(self):
        from bot.stream import VideoStream
        stream = VideoStream.__new__(VideoStream)
        stream._buffer = collections.deque(maxlen=60)
        stream._on_frame(None)
        assert len(stream._buffer) == 0

    def test_buffer_respects_maxlen(self):
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
