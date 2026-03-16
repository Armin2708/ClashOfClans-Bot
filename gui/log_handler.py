"""Custom logging handler that emits log records as Qt signals."""

import logging
from PySide6.QtCore import QObject, Signal


class LogSignalEmitter(QObject):
    """Emits formatted log messages as Qt signals."""
    log_message = Signal(str)


class QtLogHandler(logging.Handler):
    """Logging handler that forwards records to a LogSignalEmitter."""

    def __init__(self, emitter):
        super().__init__()
        self.emitter = emitter
        self.setFormatter(logging.Formatter(
            "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
            datefmt="%H:%M:%S",
        ))

    def emit(self, record):
        try:
            msg = self.format(record)
            self.emitter.log_message.emit(msg)
        except Exception:
            self.handleError(record)
