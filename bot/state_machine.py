"""
State machine for tracking game state with timeouts and recovery.

GameState enum values match the strings returned by vision.detect_screen_state()
for backward compatibility.
"""

import time
from enum import Enum
from collections import deque


class GameState(Enum):
    VILLAGE = "village"
    ATTACK_MENU = "attack_menu"
    ARMY = "army"
    SEARCHING = "searching"
    SCOUTING = "battle"
    BATTLE_ACTIVE = "in_battle"
    RESULTS = "stars"
    UNKNOWN = "unknown"

    def __eq__(self, other):
        if isinstance(other, str):
            return self.value == other
        return super().__eq__(other)

    def __hash__(self):
        return hash(self.value)


# Valid state transitions: state -> set of states it can transition to
VALID_TRANSITIONS = {
    GameState.VILLAGE: {GameState.ATTACK_MENU, GameState.VILLAGE, GameState.UNKNOWN},
    GameState.ATTACK_MENU: {GameState.ARMY, GameState.VILLAGE, GameState.UNKNOWN},
    GameState.ARMY: {GameState.SEARCHING, GameState.VILLAGE, GameState.UNKNOWN},
    GameState.SEARCHING: {GameState.SCOUTING, GameState.BATTLE_ACTIVE, GameState.VILLAGE, GameState.UNKNOWN},
    GameState.SCOUTING: {GameState.SCOUTING, GameState.BATTLE_ACTIVE, GameState.RESULTS, GameState.VILLAGE, GameState.UNKNOWN},
    GameState.BATTLE_ACTIVE: {GameState.BATTLE_ACTIVE, GameState.RESULTS, GameState.VILLAGE, GameState.UNKNOWN},
    GameState.RESULTS: {GameState.VILLAGE, GameState.RESULTS, GameState.UNKNOWN},
    GameState.UNKNOWN: {s for s in GameState},  # UNKNOWN can go anywhere
}

# Timeout per state in seconds — if stuck longer than this, recovery is needed
STATE_TIMEOUTS = {
    GameState.VILLAGE: 300,
    GameState.ATTACK_MENU: 30,
    GameState.ARMY: 30,
    GameState.SEARCHING: 60,
    GameState.SCOUTING: 120,
    GameState.BATTLE_ACTIVE: 180,
    GameState.RESULTS: 30,
    GameState.UNKNOWN: 10,
}


class StateTracker:
    """Tracks current game state, time entered, and state history."""

    def __init__(self, max_history=20):
        self.current_state = GameState.UNKNOWN
        self.entered_at = time.time()
        self.history = deque(maxlen=max_history)
        self._unknown_streak = 0

    def update(self, new_state):
        """Update the current state. Returns True if state changed."""
        if not isinstance(new_state, GameState):
            # Convert string to GameState for backward compat
            try:
                new_state = GameState(new_state)
            except ValueError:
                new_state = GameState.UNKNOWN

        if new_state == self.current_state:
            return False

        now = time.time()
        duration = now - self.entered_at
        self.history.append((self.current_state, self.entered_at, duration))

        if new_state == GameState.UNKNOWN:
            self._unknown_streak += 1
        else:
            self._unknown_streak = 0

        self.current_state = new_state
        self.entered_at = now
        return True

    def time_in_state(self):
        """Seconds spent in the current state."""
        return time.time() - self.entered_at

    def is_timed_out(self):
        """Check if we've exceeded the timeout for the current state."""
        timeout = STATE_TIMEOUTS.get(self.current_state, 30)
        return self.time_in_state() > timeout

    def stuck_check(self):
        """Check if stuck and return a recovery action string, or None if OK.

        Recovery actions:
          'restart_app' — stuck in UNKNOWN 3+ times in a row
          'dismiss'     — timed out in UNKNOWN (try dismissing popups)
          'go_home'     — timed out in RESULTS
          'surrender'   — timed out in BATTLE_ACTIVE or SCOUTING
          'tap_empty'   — timed out in ATTACK_MENU or ARMY
          None          — not stuck
        """
        if not self.is_timed_out():
            return None

        if self._unknown_streak >= 3:
            return "restart_app"

        state = self.current_state
        if state == GameState.UNKNOWN:
            return "dismiss"
        if state == GameState.RESULTS:
            return "go_home"
        if state in (GameState.BATTLE_ACTIVE, GameState.SCOUTING):
            return "surrender"
        if state in (GameState.ATTACK_MENU, GameState.ARMY):
            return "tap_empty"
        if state == GameState.SEARCHING:
            return "restart_app"
        if state == GameState.VILLAGE:
            return "tap_empty"

        return None

    def __repr__(self):
        elapsed = int(self.time_in_state())
        return f"StateTracker({self.current_state.name}, {elapsed}s)"
