"""
Resource reading — reads gold and elixir from the village screen.
Uses the vision module's screenshot-driven detection.
"""

from screen import screenshot
from vision import read_resources_from_village


def get_resources():
    """Take a screenshot and return (gold, elixir)."""
    img = screenshot()
    gold, elixir = read_resources_from_village(img)
    print(f"[Resources] Gold: {gold} | Elixir: {elixir}")
    return gold, elixir
