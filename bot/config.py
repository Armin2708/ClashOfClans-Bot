"""Config shim — delegates all attribute access to Settings singleton."""

from bot.settings import Settings

# Keys whose values must be converted from lists back to tuples
_TUPLE_KEYS = {
    "gold_region", "elixir_region", "game_area", "empty_tap",
    "enemy_loot_x_range", "enemy_loot_y_range",
}

# Keys whose values are lists that should become tuples
_TUPLE_LIST_KEYS = {
    "wall_scales", "enemy_loot_scales",
}

# Dict key whose values (lists) should be converted to tuples
_DICT_TUPLE_VALUE_KEYS = {
    "button_rois",
}


def __getattr__(name):
    key = name.lower()
    settings = Settings()
    value = settings.get(key)
    if value is None:
        raise AttributeError(f"module 'config' has no attribute {name!r}")

    # Convert coordinate regions from lists to tuples
    if key in _TUPLE_KEYS:
        return tuple(value)

    # Convert scale lists to tuples
    if key in _TUPLE_LIST_KEYS:
        return tuple(value)

    # Convert BUTTON_ROIS dict values from lists to tuples
    if key in _DICT_TUPLE_VALUE_KEYS:
        return {k: tuple(v) for k, v in value.items()}

    return value
