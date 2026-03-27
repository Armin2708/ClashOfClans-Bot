"""Settings singleton backed by ~/.cocbot/settings.json."""

import json
import os
import threading

_SETTINGS_DIR = os.path.expanduser("~/.cocbot")
_SETTINGS_FILE = os.path.join(_SETTINGS_DIR, "settings.json")

# Base resolution all pixel coordinates are authored for
BASE_WIDTH = 2560
BASE_HEIGHT = 1440

# Settings keys containing pixel coordinates that must be scaled.
# Keys with (x, y, x, y) or (x, y) tuples — scale x by width ratio, y by height ratio
_COORDINATE_KEYS = {
    "gold_region", "elixir_region", "game_area", "empty_tap",
    "enemy_loot_x_range",  # x-only pair
    "enemy_loot_y_range",  # y-only pair
}

# Keys with single pixel values that scale by width ratio
_PIXEL_X_KEYS = {
    "fallback_troop_x_start", "fallback_troop_x_spacing",
    "troop_bar_x_start", "troop_bar_x_end",
    "deploy_swipe_x1", "deploy_swipe_x2",
}

# Keys with single pixel values that scale by height ratio
_PIXEL_Y_KEYS = {
    "enemy_loot_strip_height", "enemy_loot_y_step", "enemy_loot_y_dedup",
    "deploy_swipe_y1", "deploy_swipe_y2",
}

# Keys with pixel area values that scale by (width_ratio * height_ratio)
_PIXEL_AREA_KEYS = {
    "troop_slot_min_area", "troop_slot_max_area",
}

DEFAULTS = {
    # Screen resolution
    "screen_width": 2560,
    "screen_height": 1440,

    # ADB
    "adb_path": "adb",
    "game_package": "com.supercell.clashofclans",

    # Thresholds
    "min_loot_to_attack": 1_000_000,
    "gold_storage_full": 24_000_000,
    "elixir_storage_full": 24_000_000,
    "farm_target_gold": 31_000_000,
    "farm_target_elixir": 31_000_000,

    # Timing
    "battle_check_interval": 2,
    "loop_delay": 0,
    "app_launch_wait": 15,
    "scout_wait": 3,
    "battle_timeout": 180,

    # Template matching
    "template_threshold": 0.75,
    "screen_detect_threshold": 0.72,

    # Button ROI regions
    "button_rois": {
        "attack_button":  [0, 1050, 500, 1440],
        "find_match":     [50, 1000, 800, 1300],
        "start_battle":   [1800, 1050, 2560, 1440],
        "stars_screen":   [800, 200, 1700, 800],
        "return_home":    [800, 900, 1700, 1400],
        "next_base":      [2000, 950, 2560, 1440],
        "end_battle":     [0, 1000, 500, 1440],
        "loot_gold":      [0, 100, 200, 350],
        "loot_elixir":    [0, 200, 200, 450],
    },

    # Resource regions
    "gold_region": [2100, 55, 2500, 105],
    "elixir_region": [2100, 180, 2500, 240],

    # Enemy loot
    "enemy_loot_x_range": [80, 400],
    "enemy_loot_y_range": [150, 450],
    "enemy_loot_strip_height": 50,
    "enemy_loot_y_step": 10,
    "enemy_loot_y_dedup": 50,
    "enemy_loot_scales": [0.9, 1.0, 1.2, 1.5, 2.0],

    # Troop deployment
    "troop_bar_y_ratio": 0.91,
    "deploy_num_points": 15,
    "deploy_x_start": 0.1,
    "deploy_x_end": 0.4,
    "deploy_y_start": 0.35,
    "deploy_y_end": 0.10,
    "deploy_swipe_rounds": 3,
    "fallback_troop_slots": 8,
    "fallback_troop_x_start": 100,
    "fallback_troop_x_spacing": 80,

    # Troop slot detection
    "troop_slot_min_area": 1000,
    "troop_slot_max_area": 50000,
    "troop_slot_min_aspect": 0.5,
    "troop_slot_max_aspect": 2.0,
    "troop_slot_min_dist": 60,
    "troop_slot_gray_thresh": 80,
    "troop_bar_x_start": 100,
    "troop_bar_x_end": 2400,

    # Battle scouting
    "max_base_skips": 30,

    # Deploy swipe
    "deploy_swipe_x1": 800,
    "deploy_swipe_y1": 700,
    "deploy_swipe_x2": 1600,
    "deploy_swipe_y2": 700,
    "deploy_swipe_duration": 500,

    # Wall detection
    "game_area": [120, 250, 2400, 1250],

    # Neutral tap
    "empty_tap": [20, 700],

    # Discord
    "discord_webhook_url": "",
    "discord_enabled": True,

    # Onboarding
    "onboarding_completed": False,

    # Crash recovery
    "circuit_breaker_max_failures": 3,
    "circuit_breaker_window": 300,
    "max_unknown_state_streak": 3,

    # New keys
    "device_address": "",

    # Video stream
    "stream_fps": 30,
    "stream_buffer_size": 60,
}


class Settings:
    """Singleton settings manager backed by JSON file."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._data = {}
        self._file_lock = threading.Lock()
        self._load()

    def _load(self):
        """Load settings from JSON file, merging with defaults."""
        self._data = dict(DEFAULTS)
        if os.path.exists(_SETTINGS_FILE):
            try:
                with open(_SETTINGS_FILE, "r") as f:
                    stored = json.load(f)
                self._data.update(stored)
            except (json.JSONDecodeError, OSError):
                pass

    def get(self, key, default=None):
        """Get a setting value."""
        return self._data.get(key, default)

    def set(self, key, value):
        """Set a setting value (thread-safe)."""
        with self._file_lock:
            self._data[key] = value

    def save(self):
        """Write settings to disk (thread-safe)."""
        with self._file_lock:
            os.makedirs(_SETTINGS_DIR, exist_ok=True)
            with open(_SETTINGS_FILE, "w") as f:
                json.dump(self._data, f, indent=2)

    def reset(self):
        """Reset all settings to defaults."""
        with self._file_lock:
            self._data = dict(DEFAULTS)
