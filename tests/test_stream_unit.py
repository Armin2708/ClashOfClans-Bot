"""Unit tests for VideoStream — capture thread not started, buffer manipulated directly."""
import collections
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
        assert stream.get_frame() is frame2

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


class TestVideoStreamBuffer:
    def test_buffer_respects_maxlen(self):
        from bot.stream import VideoStream
        stream = VideoStream.__new__(VideoStream)
        stream._buffer = collections.deque(maxlen=3)
        frames = [_make_frame() for _ in range(5)]
        for f in frames:
            stream._buffer.append(f)
        assert len(stream._buffer) == 3
        assert list(stream._buffer) == frames[2:]

    def test_dead_flag_default_false(self):
        from bot.stream import VideoStream
        stream = VideoStream(fps=60, buffer_size=60)
        assert stream._dead is False

    def test_constructor_sets_fps_and_buffer_size(self):
        from bot.stream import VideoStream
        stream = VideoStream(fps=30, buffer_size=90)
        assert stream._fps == 30
        assert stream._buffer.maxlen == 90
