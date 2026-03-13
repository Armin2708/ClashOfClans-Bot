"""Discord webhook notifications."""

import urllib.request
import json
import logging
import time

from config import DISCORD_WEBHOOK_URL

logger = logging.getLogger("coc.notify")


def notify(message, max_retries=2):
    """Send a message to Discord via webhook with retry logic."""
    for attempt in range(max_retries):
        try:
            data = json.dumps({"content": message}).encode("utf-8")
            req = urllib.request.Request(
                DISCORD_WEBHOOK_URL,
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "COC-Bot/1.0",
                },
            )
            urllib.request.urlopen(req, timeout=10)
            logger.info("Sent: %s", message)
            return True
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning("Failed to send (attempt %d/%d): %s", attempt + 1, max_retries, e)
                time.sleep(2)
            else:
                logger.error("Failed to send after %d attempts: %s", max_retries, e)
    return False


def notify_summary(metrics):
    """Send a periodic metrics summary to Discord."""
    summary = metrics.get_summary()
    notify(f"Bot Status: {summary}")
