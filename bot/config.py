"""Config shim — delegates all attribute access to Settings singleton.
Automatically scales pixel coordinates to the detected screen resolution."""

from bot.settings import (
    Settings, BASE_WIDTH, BASE_HEIGHT,
    _COORDINATE_KEYS, _PIXEL_X_KEYS, _PIXEL_Y_KEYS, _PIXEL_AREA_KEYS,
)

# Keys whose values are lists that should become tuples (non-pixel)
_TUPLE_LIST_KEYS = {
    "wall_scales", "enemy_loot_scales",
}

# Dict key whose values (lists) should be converted to tuples
_DICT_TUPLE_VALUE_KEYS = {
    "button_rois",
}


def _scale_ratios():
    """Return (width_ratio, height_ratio) based on current screen vs base."""
    settings = Settings()
    sw = settings.get("screen_width", BASE_WIDTH)
    sh = settings.get("screen_height", BASE_HEIGHT)
    return sw / BASE_WIDTH, sh / BASE_HEIGHT


def _scale_button_rois(rois, rx, ry):
    """Scale all button ROI dicts: {name: [x1, y1, x2, y2]}."""
    return {
        k: tuple(int(v * rx) if i % 2 == 0 else int(v * ry) for i, v in enumerate(vals))
        for k, vals in rois.items()
    }


def __getattr__(name):
    key = name.lower()
    settings = Settings()
    value = settings.get(key)
    if value is None:
        raise AttributeError(f"module 'config' has no attribute {name!r}")

    rx, ry = _scale_ratios()
    no_scale = (rx == 1.0 and ry == 1.0)

    # Convert BUTTON_ROIS dict values and scale coordinates
    if key in _DICT_TUPLE_VALUE_KEYS:
        if no_scale:
            return {k: tuple(v) for k, v in value.items()}
        return _scale_button_rois(value, rx, ry)

    # Convert and scale coordinate regions [x, y, x, y] or [x, y]
    if key in _COORDINATE_KEYS:
        if no_scale:
            return tuple(value)
        # Special: x-only and y-only range pairs
        if key == "enemy_loot_x_range":
            return tuple(int(v * rx) for v in value)
        if key == "enemy_loot_y_range":
            return tuple(int(v * ry) for v in value)
        # General: alternating x, y values
        return tuple(
            int(v * rx) if i % 2 == 0 else int(v * ry)
            for i, v in enumerate(value)
        )

    # Scale single-value pixel keys
    if key in _PIXEL_X_KEYS:
        return value if no_scale else int(value * rx)

    if key in _PIXEL_Y_KEYS:
        return value if no_scale else int(value * ry)

    if key in _PIXEL_AREA_KEYS:
        return value if no_scale else int(value * rx * ry)

    # Non-pixel tuple keys (scales, etc.)
    if key in _TUPLE_LIST_KEYS:
        return tuple(value)

    # Any remaining list-type settings that need tuple conversion
    if isinstance(value, list):
        return tuple(value)

    return value
