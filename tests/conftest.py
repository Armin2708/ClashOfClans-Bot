"""Shared test fixtures and module stubs."""
import sys
from unittest.mock import MagicMock

# Stub the scrcpy package so bot.stream can be imported without the native
# dependency installed.  The unit tests bypass __init__ via __new__ and never
# call start()/stop(), so a MagicMock is sufficient.
if "scrcpy" not in sys.modules:
    _scrcpy = MagicMock()
    _scrcpy.EVENT_FRAME = "frame"
    _scrcpy.EVENT_DISCONNECT = "disconnect"
    sys.modules["scrcpy"] = _scrcpy
