"""Simple metrics tracking for the bot."""

import time
import logging
import threading

logger = logging.getLogger("coc.metrics")

METRICS_LOG_INTERVAL = 3600  # log summary every hour


class Metrics:
    """Track bot performance counters."""

    def __init__(self):
        self.walls_upgraded = 0
        self.bases_attacked = 0
        self.bases_skipped = 0
        self.total_gold_farmed = 0
        self.total_elixir_farmed = 0
        self.app_restarts = 0
        self._start_time = time.time()
        self._last_log_time = time.time()
        self._lock = threading.Lock()

    def record_wall_upgrade(self, count=1):
        with self._lock:
            self.walls_upgraded += count

    def record_attack(self, gold=0, elixir=0):
        with self._lock:
            self.bases_attacked += 1
            self.total_gold_farmed += gold
            self.total_elixir_farmed += elixir

    def record_skip(self):
        with self._lock:
            self.bases_skipped += 1

    def record_restart(self):
        with self._lock:
            self.app_restarts += 1

    def get_summary(self):
        with self._lock:
            uptime = int(time.time() - self._start_time)
            hours = uptime // 3600
            minutes = (uptime % 3600) // 60
            return (
                f"Metrics (uptime {hours}h{minutes}m): "
                f"walls={self.walls_upgraded}, "
                f"attacks={self.bases_attacked}, "
                f"skips={self.bases_skipped}, "
                f"gold={self.total_gold_farmed:,}, "
                f"elixir={self.total_elixir_farmed:,}, "
                f"restarts={self.app_restarts}"
            )

    def maybe_log_hourly(self):
        """Log metrics summary if an hour has passed since last log."""
        now = time.time()
        if now - self._last_log_time >= METRICS_LOG_INTERVAL:
            self._last_log_time = now
            logger.info(self.get_summary())

    def log_final(self):
        """Log metrics on bot shutdown."""
        logger.info("Final %s", self.get_summary())


# Global metrics instance
metrics = Metrics()
