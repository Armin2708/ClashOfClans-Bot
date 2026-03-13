"""
Wall upgrade module — delegates to the building abstraction system.

Keeps upgrade_walls() as the public API for backward compatibility.
"""

from buildings import GOLD_WALL, WallUpgradeStrategy

_strategy = WallUpgradeStrategy()


def upgrade_walls():
    """
    Detect walls, tap one, tap "Upgrade More" 3 times, then upgrade.
    Returns number of walls upgraded (0 or 3).
    """
    return _strategy.execute_upgrade(GOLD_WALL)
