"""
Resource reading — reads gold and elixir from the village screen.
Uses the vision module's screenshot-driven detection.
"""

import logging
from screen import screenshot
from vision import read_resources_from_village

logger = logging.getLogger("coc.resources")


def get_resources():
    """Take a screenshot and return (gold, elixir)."""
    img = screenshot()
    gold, elixir = read_resources_from_village(img)
    logger.info("Gold: %d | Elixir: %d", gold, elixir)
    return gold, elixir
