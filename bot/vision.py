"""
Vision module — screenshot-driven detection for all game screens.
Every function takes a screenshot, figures out what's on screen, and returns data.

Templates are loaded lazily (on first use) so extract_templates.py can be
run before this module is imported.

Performance notes:
  - All template matching uses grayscale (3x less data than BGR)
  - detect_screen_state() crops to button ROI regions before matching (~100-200x smaller)
  - read_enemy_loot() converts loot area to gray once, early-exits after 2 numbers
"""

import cv2
import numpy as np
import os
import re
import logging
import pytesseract
from bot.screen import screenshot
from bot.utils import find_template, load_template, load_template_gray, save_debug, writable_path
from bot.state_machine import GameState

logger = logging.getLogger("coc.vision")
from bot.config import (
    TEMPLATE_THRESHOLD, SCREEN_DETECT_THRESHOLD,
    GOLD_REGION, ELIXIR_REGION,
    ENEMY_LOOT_X_RANGE, ENEMY_LOOT_Y_RANGE, ENEMY_LOOT_STRIP_HEIGHT,
    ENEMY_LOOT_Y_STEP, ENEMY_LOOT_Y_DEDUP, ENEMY_LOOT_SCALES,
    TROOP_BAR_Y_RATIO, DEPLOY_NUM_POINTS,
    DEPLOY_X_START, DEPLOY_X_END, DEPLOY_Y_START, DEPLOY_Y_END,
    TROOP_SLOT_MIN_AREA, TROOP_SLOT_MAX_AREA,
    TROOP_SLOT_MIN_ASPECT, TROOP_SLOT_MAX_ASPECT,
    TROOP_SLOT_MIN_DIST, TROOP_SLOT_GRAY_THRESH,
    TROOP_BAR_X_START, TROOP_BAR_X_END,
    BUTTON_ROIS, SCREEN_WIDTH, SCREEN_HEIGHT,
)


# ─── TEMPLATE LOADING (lazy) ─────────────────────────────────

_TEMPLATES = None       # BGR templates (for general use)
_TEMPLATES_GRAY = None  # Grayscale templates (for fast matching)
_TOWNHALL_TEMPLATES = None


def _load_templates():
    global _TEMPLATES, _TEMPLATES_GRAY

    names = [
        "attack_button", "find_match", "start_battle",
        "stars_screen", "return_home",
        "confirm_upgrade", "gem_cost", "next_base",
        "end_battle", "close_x", "okay_button", "later_button",
        "loot_gold", "loot_elixir",
    ]
    paths = {
        "attack_button": "templates/buttons/attack_button.png",
        "find_match": "templates/buttons/find_match.png",
        "start_battle": "templates/buttons/start_battle.png",
        "stars_screen": "templates/buttons/stars_screen.png",
        "return_home": "templates/buttons/return_home.png",
        "confirm_upgrade": "templates/buttons/confirm_upgrade.png",
        "gem_cost": "templates/buttons/gem_cost.png",
        "next_base": "templates/buttons/next_base.png",
        "end_battle": "templates/buttons/end_battle.png",
        "close_x": "templates/popups/close_x.png",
        "okay_button": "templates/popups/okay_button.png",
        "later_button": "templates/popups/later_button.png",
        "loot_gold": "templates/buttons/loot_gold.png",
        "loot_elixir": "templates/buttons/loot_elixir.png",
    }

    # Scale templates to match current resolution if different from base
    from bot.settings import BASE_WIDTH, BASE_HEIGHT
    rx = SCREEN_WIDTH / BASE_WIDTH
    ry = SCREEN_HEIGHT / BASE_HEIGHT
    need_scale = (rx != 1.0 or ry != 1.0)
    if need_scale:
        logger.info("Scaling templates by %.2fx%.2f for %dx%d", rx, ry, SCREEN_WIDTH, SCREEN_HEIGHT)

    _TEMPLATES = {}
    _TEMPLATES_GRAY = {}
    for name in names:
        bgr = load_template(paths[name])
        if bgr is not None and need_scale:
            h, w = bgr.shape[:2]
            new_w, new_h = max(1, int(w * rx)), max(1, int(h * ry))
            bgr = cv2.resize(bgr, (new_w, new_h), interpolation=cv2.INTER_AREA)
        _TEMPLATES[name] = bgr
        if bgr is not None:
            _TEMPLATES_GRAY[name] = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        else:
            _TEMPLATES_GRAY[name] = None


def _reload_template(name):
    """Reload a single template from disk into the in-memory caches."""
    global _TEMPLATES, _TEMPLATES_GRAY
    if _TEMPLATES is None:
        _load_templates()
        return

    paths = {
        "next_base": "templates/buttons/next_base.png",
    }
    path = paths.get(name)
    if not path:
        return

    from bot.settings import BASE_WIDTH, BASE_HEIGHT
    rx = SCREEN_WIDTH / BASE_WIDTH
    ry = SCREEN_HEIGHT / BASE_HEIGHT

    bgr = load_template(path)
    if bgr is not None and (rx != 1.0 or ry != 1.0):
        h, w = bgr.shape[:2]
        new_w, new_h = max(1, int(w * rx)), max(1, int(h * ry))
        bgr = cv2.resize(bgr, (new_w, new_h), interpolation=cv2.INTER_AREA)
    _TEMPLATES[name] = bgr
    if bgr is not None:
        _TEMPLATES_GRAY[name] = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    else:
        _TEMPLATES_GRAY[name] = None


# Crop coordinates for auto-capture (at base 2560x1440 resolution).
# These define a tight region around the button content, smaller than the
# search ROI so template matching has room to locate it.
_AUTO_CAPTURE_REGIONS = {
    "next_base": (2250, 1020, 2490, 1160),  # matches extract_templates.py
}

_auto_captured = set()  # track which templates have been captured this session


def auto_capture_template(img, button_name):
    """
    Crop a button template from a live screenshot and save it to disk.
    Coordinates are scaled from base resolution to match the screenshot.
    The saved template is stored at base resolution so _load_templates()
    can scale it correctly on any device.

    Returns True if a template was captured, False otherwise.
    """
    if button_name in _auto_captured:
        return False

    region = _AUTO_CAPTURE_REGIONS.get(button_name)
    if not region:
        return False

    from bot.settings import BASE_WIDTH, BASE_HEIGHT
    rx = SCREEN_WIDTH / BASE_WIDTH
    ry = SCREEN_HEIGHT / BASE_HEIGHT

    # Scale crop coordinates to actual screen resolution
    bx1, by1, bx2, by2 = region
    x1, y1 = int(bx1 * rx), int(by1 * ry)
    x2, y2 = int(bx2 * rx), int(by2 * ry)

    h, w = img.shape[:2]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)

    crop = img[y1:y2, x1:x2]
    if crop.size == 0:
        logger.warning("Auto-capture: empty crop for %s", button_name)
        return False

    # Resize back to base resolution dimensions for consistent storage
    base_w = bx2 - bx1
    base_h = by2 - by1
    if rx != 1.0 or ry != 1.0:
        crop = cv2.resize(crop, (base_w, base_h), interpolation=cv2.INTER_AREA)

    rel_path = f"templates/buttons/{button_name}.png"
    path = writable_path(rel_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cv2.imwrite(path, crop)
    logger.info("Auto-captured template: %s (%dx%d)", path, base_w, base_h)

    # Reload into memory
    _reload_template(button_name)
    _auto_captured.add(button_name)
    return True


def get_template(name):
    global _TEMPLATES
    if _TEMPLATES is None:
        _load_templates()
    return _TEMPLATES.get(name)


def _get_template_gray(name):
    """Get a pre-converted grayscale template for fast matching."""
    global _TEMPLATES_GRAY
    if _TEMPLATES_GRAY is None:
        _load_templates()
    return _TEMPLATES_GRAY.get(name)


def get_townhall_templates():
    global _TOWNHALL_TEMPLATES
    if _TOWNHALL_TEMPLATES is None:
        from bot.settings import BASE_WIDTH, BASE_HEIGHT
        rx = SCREEN_WIDTH / BASE_WIDTH
        ry = SCREEN_HEIGHT / BASE_HEIGHT
        need_scale = (rx != 1.0 or ry != 1.0)
        _TOWNHALL_TEMPLATES = []
        for i in range(7, 17):
            t = load_template(f"templates/townhall/th_{i}.png")
            if t is not None:
                if need_scale:
                    h, w = t.shape[:2]
                    t = cv2.resize(t, (max(1, int(w * rx)), max(1, int(h * ry))),
                                   interpolation=cv2.INTER_AREA)
                _TOWNHALL_TEMPLATES.append(t)
    return _TOWNHALL_TEMPLATES


def validate_critical_templates():
    """Check that safety-critical templates exist at startup.
    Raises FileNotFoundError if any are missing."""
    critical = ["end_battle", "return_home", "stars_screen"]
    missing = []
    for name in critical:
        if get_template(name) is None:
            missing.append(name)
    if missing:
        raise FileNotFoundError(
            f"CRITICAL: Missing template(s): {', '.join(missing)}. "
            f"These are required for safe bot operation. "
            f"Check your templates/ directory."
        )
    logger.info("All critical templates validated: %s", ", ".join(critical))


# ─── SCREEN STATE DETECTION ─────────────────────────────────

def _find_in_roi(img_gray, button_name, threshold):
    """Match a button template within its ROI region for speed.
    Returns (x, y) in full-image coordinates, or None."""
    tmpl = _get_template_gray(button_name)
    if tmpl is None:
        return None

    roi = BUTTON_ROIS.get(button_name)
    if roi:
        x1, y1, x2, y2 = roi
        # Clamp ROI to image bounds
        ih, iw = img_gray.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(iw, x2), min(ih, y2)
        crop = img_gray[y1:y2, x1:x2]
        th, tw = tmpl.shape[:2]
        if crop.shape[0] < th or crop.shape[1] < tw:
            # ROI too small for template — fall back to full image
            crop = img_gray
            x1, y1 = 0, 0
        result = cv2.matchTemplate(crop, tmpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        if max_val >= threshold:
            th, tw = tmpl.shape[:2]
            return (max_loc[0] + tw // 2 + x1, max_loc[1] + th // 2 + y1)
        return None
    else:
        # No ROI defined — fall back to full image
        result = cv2.matchTemplate(img_gray, tmpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        if max_val >= threshold:
            th, tw = tmpl.shape[:2]
            return (max_loc[0] + tw // 2, max_loc[1] + th // 2)
        return None


def detect_screen_state(img):
    """
    Figure out which screen we're on.
    Returns a GameState enum. Enum values match the old string returns
    for backward compatibility (e.g. GameState.VILLAGE == "village").

    Uses ROI-cropped grayscale matching for speed (~8x faster than full-image BGR).
    """
    # Convert to grayscale once for all checks
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img

    th = SCREEN_DETECT_THRESHOLD

    # Stars/results screen — check first since it overlays everything
    if _find_in_roi(gray, "stars_screen", th):
        return GameState.RESULTS
    if _find_in_roi(gray, "return_home", th):
        return GameState.RESULTS

    # Next base button = scouting an enemy base
    if _find_in_roi(gray, "next_base", th):
        return GameState.SCOUTING

    # End Battle button appears on BOTH scouting and active battle screens.
    # Distinguish by checking for enemy loot icons (only on scouting screen).
    if _find_in_roi(gray, "end_battle", th):
        if (_find_in_roi(gray, "loot_gold", th) or
                _find_in_roi(gray, "loot_elixir", th)):
            return GameState.SCOUTING
        return GameState.BATTLE_ACTIVE

    # Start Battle / Attack on army screen (green button bottom-right)
    if _find_in_roi(gray, "start_battle", th):
        return GameState.ARMY

    # Find a Match = attack menu
    if _find_in_roi(gray, "find_match", th):
        return GameState.ATTACK_MENU

    # Attack button = village screen
    if _find_in_roi(gray, "attack_button", th):
        return GameState.VILLAGE

    return GameState.UNKNOWN


# ─── DIGIT TEMPLATE MATCHING ─────────────────────────────────

_DIGIT_TEMPLATES = None


def _load_digit_templates():
    """Load digit templates 0-9 from templates/digits/ as grayscale.
    Scales them to match current screen resolution."""
    global _DIGIT_TEMPLATES
    from bot.settings import BASE_WIDTH, BASE_HEIGHT
    rx = SCREEN_WIDTH / BASE_WIDTH
    ry = SCREEN_HEIGHT / BASE_HEIGHT
    need_scale = (rx != 1.0 or ry != 1.0)

    _DIGIT_TEMPLATES = {}
    for d in range(10):
        t = load_template(f"templates/digits/{d}.png")
        if t is not None:
            if need_scale:
                h, w = t.shape[:2]
                new_w, new_h = max(1, int(w * rx)), max(1, int(h * ry))
                t = cv2.resize(t, (new_w, new_h), interpolation=cv2.INTER_AREA)
            _DIGIT_TEMPLATES[d] = cv2.cvtColor(t, cv2.COLOR_BGR2GRAY)
    if _DIGIT_TEMPLATES:
        logger.info("Loaded digit templates: %s", sorted(_DIGIT_TEMPLATES.keys()))


def _read_number_template(crop, extra_scales=None, is_gray=False):
    """
    Read a number from a cropped image using digit template matching.
    The crop should contain white digits on a dark background.
    Returns the number as an integer, or None if nothing found.

    If is_gray=True, the crop is already grayscale (skips conversion).
    """
    global _DIGIT_TEMPLATES
    if _DIGIT_TEMPLATES is None:
        _load_digit_templates()

    if not _DIGIT_TEMPLATES:
        # Fall back to OCR if no digit templates
        return _ocr_number(crop)

    if is_gray:
        gray = crop
    elif len(crop.shape) == 3:
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    else:
        gray = crop

    all_matches = []  # list of (x_position, digit_value, confidence, scaled_width)

    scales = extra_scales or [0.9, 1.0, 1.1]

    for digit, template in _DIGIT_TEMPLATES.items():
        for scale in scales:
            th, tw = template.shape[:2]
            sh, sw = int(th * scale), int(tw * scale)
            if sh > gray.shape[0] or sw > gray.shape[1]:
                continue
            scaled = cv2.resize(template, (sw, sh))

            result = cv2.matchTemplate(gray, scaled, cv2.TM_CCOEFF_NORMED)
            locations = np.where(result >= TEMPLATE_THRESHOLD)

            for y, x in zip(*locations):
                conf = result[y, x]
                all_matches.append((x, digit, conf, sw))

    # Sort by confidence (highest first) so best matches win
    all_matches.sort(key=lambda m: -m[2])

    # Deduplicate: for each match, only keep it if no existing match
    # is within half a digit width at the same position
    digits_found = []
    for x, digit, conf, sw in all_matches:
        min_dist = sw * 0.4
        if not any(abs(x - ex) < min_dist for ex, _, _ in digits_found):
            digits_found.append((x, digit, conf))

    # Sort by x position (left to right)
    digits_found.sort(key=lambda d: d[0])
    number_str = "".join(str(d) for _, d, _ in digits_found)

    if not number_str:
        return None

    try:
        return int(number_str)
    except ValueError:
        return None


def _ocr_number(crop):
    """Fallback: OCR a cropped image region to extract a number."""
    if crop.size == 0:
        return 0

    if len(crop.shape) == 3:
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    else:
        gray = crop
    big = cv2.resize(gray, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)

    _, thresh = cv2.threshold(big, 180, 255, cv2.THRESH_BINARY)
    kernel = np.ones((3, 3), np.uint8)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    padded = cv2.copyMakeBorder(thresh, 30, 30, 30, 30, cv2.BORDER_CONSTANT, value=0)

    text = pytesseract.image_to_string(
        padded, config="--psm 7 -c tessedit_char_whitelist=0123456789"
    )
    text = text.strip().replace(" ", "").replace(",", "").replace(".", "")

    if not text:
        return None

    try:
        return int(text)
    except ValueError:
        return None


# ─── RESOURCE READING (VILLAGE) ──────────────────────────────

def read_resources_from_village(img):
    """
    Read gold and elixir from the village screen.
    Resources are in the TOP-RIGHT corner in dark rounded boxes.
    Uses digit template matching for reliable reading of the game font.
    """
    gx1, gy1, gx2, gy2 = GOLD_REGION
    gold_region = img[gy1:gy2, gx1:gx2]
    gold = _read_number_template(gold_region)
    if gold is None:
        logger.warning("Could not read gold, defaulting to 0")
        gold = 0

    ex1, ey1, ex2, ey2 = ELIXIR_REGION
    elixir_region = img[ey1:ey2, ex1:ex2]
    elixir = _read_number_template(elixir_region)
    if elixir is None:
        logger.warning("Could not read elixir, defaulting to 0")
        elixir = 0

    return gold, elixir


# ─── ENEMY LOOT READING (BATTLE SCOUT) ───────────────────────

def read_enemy_loot(img):
    """
    Read the enemy base available loot from the scouting screen.
    Scans the top-left area in horizontal strips to find lines containing numbers.
    First number line = gold, second = elixir.

    Performance: converts loot area to grayscale once, early-exits after 2 numbers.
    Returns (gold, elixir).
    """
    loot_x1, loot_x2 = ENEMY_LOOT_X_RANGE
    loot_y1, loot_y2 = ENEMY_LOOT_Y_RANGE

    # Convert the entire loot area to grayscale once (avoids repeated conversions)
    loot_area = img[loot_y1:loot_y2, loot_x1:loot_x2]
    if len(loot_area.shape) == 3:
        loot_gray = cv2.cvtColor(loot_area, cv2.COLOR_BGR2GRAY)
    else:
        loot_gray = loot_area

    numbers_found = []

    for y_offset in range(0, loot_y2 - loot_y1, ENEMY_LOOT_Y_STEP):
        strip = loot_gray[y_offset:y_offset + ENEMY_LOOT_STRIP_HEIGHT, :]
        if strip.size == 0:
            continue
        value = _read_number_template(strip, extra_scales=ENEMY_LOOT_SCALES, is_gray=True)
        if value is not None and value > 1000:  # Real loot numbers are at least 4 digits
            abs_y = y_offset + loot_y1
            if not any(abs(abs_y - prev_y) < ENEMY_LOOT_Y_DEDUP for prev_y, _ in numbers_found):
                numbers_found.append((abs_y, value))
                # Early exit: we only need gold and elixir
                if len(numbers_found) >= 2:
                    break

    gold = numbers_found[0][1] if len(numbers_found) > 0 else 0
    elixir = numbers_found[1][1] if len(numbers_found) > 1 else 0

    return gold, elixir


# ─── BUTTON FINDING ──────────────────────────────────────────

def find_button(img, button_name):
    """Find a button on screen by template. Returns (x, y) or None.
    Uses the ROI region when available for consistency with detect_screen_state().
    """
    # Try ROI-based matching first (same path as detect_screen_state)
    roi = BUTTON_ROIS.get(button_name)
    if roi:
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img
        result = _find_in_roi(gray, button_name, TEMPLATE_THRESHOLD)
        if result:
            return result
    # Fall back to full-image multi-scale matching
    return find_template(img, get_template(button_name))


def find_popup(img):
    """Check for any dismissable popup. Returns (x, y) to tap, or None."""
    for name in ["close_x", "okay_button", "later_button"]:
        pos = find_template(img, get_template(name))
        if pos:
            return pos
    return None


# ─── DEPLOYMENT ──────────────────────────────────────────────

def get_deploy_corner(img):
    """
    Returns a list of (x, y) points along the top-left corner of the
    battle map for troop deployment.
    """
    h, w = img.shape[:2]
    points = []
    for i in range(DEPLOY_NUM_POINTS):
        t = i / (DEPLOY_NUM_POINTS - 1)
        x = int(w * DEPLOY_X_START + t * (w * (DEPLOY_X_END - DEPLOY_X_START)))
        y = int(h * DEPLOY_Y_START - t * (h * (DEPLOY_Y_START - DEPLOY_Y_END)))
        points.append((x, y))
    return points


def get_troop_slots(img):
    """
    Detect troop slots in the deployment bar at the bottom.
    Returns list of (x, y) for each troop slot.

    Only scans the actual troop icon row (below category tabs like
    super troops/siege machines) and within X bounds to avoid
    edge UI elements like the surrender button.
    """
    h, w = img.shape[:2]
    bar_y = int(h * TROOP_BAR_Y_RATIO)
    x_start = TROOP_BAR_X_START
    x_end = min(TROOP_BAR_X_END, w)
    bar = img[bar_y:, x_start:x_end]

    gray = cv2.cvtColor(bar, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, TROOP_SLOT_GRAY_THRESH, 255, cv2.THRESH_BINARY)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    slots = []
    for c in contours:
        area = cv2.contourArea(c)
        if TROOP_SLOT_MIN_AREA < area < TROOP_SLOT_MAX_AREA:
            x, y, cw, ch = cv2.boundingRect(c)
            aspect = cw / max(ch, 1)
            if TROOP_SLOT_MIN_ASPECT < aspect < TROOP_SLOT_MAX_ASPECT:
                cx = x + cw // 2 + x_start  # offset back to full-image coords
                cy = y + ch // 2 + bar_y
                if not any(abs(cx - sx) < TROOP_SLOT_MIN_DIST for sx, _ in slots):
                    slots.append((cx, cy))

    slots.sort(key=lambda s: s[0])
    return slots
