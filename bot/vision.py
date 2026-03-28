"""
Vision module — YOLO-driven detection for all game screens.

Replaces OpenCV template matching with YOLOv11 inference.
Public API is unchanged — all callers (battle.py, main.py, screen.py)
require no modifications.

Digit OCR (read_enemy_loot, read_resources_from_village) is retained
unchanged as it is effective for reading game font digits.
"""

import cv2
import numpy as np
import logging
import threading
import pytesseract
from bot.state_machine import GameState
from bot.utils import load_template

logger = logging.getLogger("coc.vision")

from bot.config import (
    TEMPLATE_THRESHOLD,
    GOLD_REGION, ELIXIR_REGION,
    ENEMY_LOOT_X_RANGE, ENEMY_LOOT_Y_RANGE, ENEMY_LOOT_STRIP_HEIGHT,
    ENEMY_LOOT_Y_STEP, ENEMY_LOOT_Y_DEDUP, ENEMY_LOOT_SCALES,
    DEPLOY_NUM_POINTS, DEPLOY_X_START, DEPLOY_X_END, DEPLOY_Y_START, DEPLOY_Y_END,
    SCREEN_WIDTH, SCREEN_HEIGHT,
)


# ─── YOLO DETECTOR (lazy singleton) ───────────────────────────

_detector = None
_detector_lock = threading.Lock()

# Maps legacy button names used by battle.py / main.py → YOLO class names
_BUTTON_CLASS_MAP = {
    "attack_button":   "btn_attack",
    "find_match":      "btn_find_match",
    "start_battle":    "btn_start_battle",
    "stars_screen":    "hud_results",
    "return_home":     "btn_return_home",
    "next_base":       "btn_next_base",
    "end_battle":      "btn_end_battle",
    "confirm_upgrade": "btn_confirm",
    "gem_cost":        "loot_gem",
    "close_x":         "btn_close",
    "okay_button":     "btn_okay",
    "later_button":    "btn_later",
    "loot_gold":       "loot_gold",
    "loot_elixir":     "loot_elixir",
}


def _get_detector():
    """Return the lazy-loaded Detector singleton (double-checked locking)."""
    global _detector
    if _detector is not None:
        return _detector
    with _detector_lock:
        if _detector is not None:
            return _detector
        from bot.settings import Settings
        settings = Settings()
        model_path = settings.get("yolo_model_path", "models/coc.pt")
        confidence = settings.get("yolo_confidence_threshold", 0.45)
        from bot.detector import Detector
        _detector = Detector(model_path, confidence)
    return _detector


# ─── SCREEN STATE DETECTION ───────────────────────────────────

def detect_screen_state(img):
    """
    Determine which screen is currently visible.
    Returns a GameState enum. Enum values are backward-compatible strings.
    """
    dets = _get_detector().predict(img)
    cls_set = {d.cls for d in dets}

    # Results screen overlays everything — check first
    if "hud_results" in cls_set or "btn_return_home" in cls_set:
        return GameState.RESULTS

    # Next base button = scouting an enemy base
    if "btn_next_base" in cls_set:
        return GameState.SCOUTING

    # End battle + loot = scouting; end battle alone = in-battle
    if "btn_end_battle" in cls_set:
        if "loot_gold" in cls_set or "loot_elixir" in cls_set:
            return GameState.SCOUTING
        return GameState.BATTLE_ACTIVE

    # Army selection screen
    if "btn_start_battle" in cls_set:
        return GameState.ARMY

    # Attack menu
    if "btn_find_match" in cls_set:
        return GameState.ATTACK_MENU

    # Village
    if "btn_attack" in cls_set or "hud_village" in cls_set:
        return GameState.VILLAGE

    return GameState.UNKNOWN


# ─── BUTTON FINDING ───────────────────────────────────────────

def find_button(img, button_name):
    """Find a button by legacy name. Returns (x, y) center or None."""
    yolo_cls = _BUTTON_CLASS_MAP.get(button_name)
    if yolo_cls is None:
        logger.warning("find_button: unknown button name '%s'", button_name)
        return None
    det = _get_detector().find(img, yolo_cls)
    return det.center if det else None


def find_popup(img):
    """Detect any dismissable popup. Returns (x, y) to tap, or None."""
    for cls in ("btn_close", "btn_okay", "btn_later"):
        det = _get_detector().find(img, cls)
        if det:
            return det.center
    return None


# ─── DEPLOYMENT ───────────────────────────────────────────────

def get_deploy_corner(img):
    """Return a list of (x, y) deployment points along the top-left battle edge."""
    h, w = img.shape[:2]
    points = []
    for i in range(DEPLOY_NUM_POINTS):
        t = i / (DEPLOY_NUM_POINTS - 1)
        x = int(w * DEPLOY_X_START + t * (w * (DEPLOY_X_END - DEPLOY_X_START)))
        y = int(h * DEPLOY_Y_START - t * (h * (DEPLOY_Y_START - DEPLOY_Y_END)))
        points.append((x, y))
    return points


def get_troop_slots(img):
    """Detect troop slot icons in the bottom deployment bar. Returns [(x,y)] sorted by x."""
    dets = _get_detector().find_all(img, "troop_slot")
    slots = [d.center for d in dets]
    slots.sort(key=lambda s: s[0])
    return slots


# ─── DIGIT OCR (unchanged — for loot and resource reading) ────

_DIGIT_TEMPLATES = None


def _load_digit_templates():
    """Load digit templates 0-9 from templates/digits/ as grayscale."""
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
                t = cv2.resize(t, (max(1, int(w * rx)), max(1, int(h * ry))),
                               interpolation=cv2.INTER_AREA)
            _DIGIT_TEMPLATES[d] = cv2.cvtColor(t, cv2.COLOR_BGR2GRAY)
    if _DIGIT_TEMPLATES:
        logger.info("Loaded digit templates: %s", sorted(_DIGIT_TEMPLATES.keys()))


def _read_number_template(crop, extra_scales=None, is_gray=False):
    """Read a number from a cropped image using digit template matching."""
    global _DIGIT_TEMPLATES
    if _DIGIT_TEMPLATES is None:
        _load_digit_templates()
    if not _DIGIT_TEMPLATES:
        return _ocr_number(crop)

    gray = crop if is_gray else (
        cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if len(crop.shape) == 3 else crop
    )

    all_matches = []
    for digit, template in _DIGIT_TEMPLATES.items():
        for scale in (extra_scales or [0.9, 1.0, 1.1]):
            th, tw = template.shape[:2]
            sh, sw = int(th * scale), int(tw * scale)
            if sh > gray.shape[0] or sw > gray.shape[1]:
                continue
            scaled = cv2.resize(template, (sw, sh))
            result = cv2.matchTemplate(gray, scaled, cv2.TM_CCOEFF_NORMED)
            for y, x in zip(*np.where(result >= TEMPLATE_THRESHOLD)):
                all_matches.append((x, digit, result[y, x], sw))

    all_matches.sort(key=lambda m: -m[2])
    digits_found = []
    for x, digit, conf, sw in all_matches:
        if not any(abs(x - ex) < sw * 0.4 for ex, _, _ in digits_found):
            digits_found.append((x, digit, conf))

    digits_found.sort(key=lambda d: d[0])
    number_str = "".join(str(d) for _, d, _ in digits_found)
    return int(number_str) if number_str else None


def _ocr_number(crop):
    """Fallback: OCR a crop to extract a number."""
    if crop.size == 0:
        return 0
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if len(crop.shape) == 3 else crop
    big = cv2.resize(gray, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
    _, thresh = cv2.threshold(big, 180, 255, cv2.THRESH_BINARY)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    padded = cv2.copyMakeBorder(thresh, 30, 30, 30, 30, cv2.BORDER_CONSTANT, value=0)
    text = pytesseract.image_to_string(
        padded, config="--psm 7 -c tessedit_char_whitelist=0123456789"
    ).strip().replace(" ", "").replace(",", "").replace(".", "")
    return int(text) if text else None


# ─── RESOURCE AND LOOT READING ───────────────────────────────

def read_resources_from_village(img):
    """Read gold and elixir from the village screen HUD (top-right corner)."""
    gx1, gy1, gx2, gy2 = GOLD_REGION
    gold = _read_number_template(img[gy1:gy2, gx1:gx2]) or 0

    ex1, ey1, ex2, ey2 = ELIXIR_REGION
    elixir = _read_number_template(img[ey1:ey2, ex1:ex2]) or 0

    return gold, elixir


def read_enemy_loot(img):
    """
    Read enemy gold and elixir from the scouting screen (top-left area).
    Scans horizontal strips to find digit rows. Early-exits after 2 numbers.
    Returns (gold, elixir).
    """
    loot_x1, loot_x2 = ENEMY_LOOT_X_RANGE
    loot_y1, loot_y2 = ENEMY_LOOT_Y_RANGE

    loot_area = img[loot_y1:loot_y2, loot_x1:loot_x2]
    loot_gray = (cv2.cvtColor(loot_area, cv2.COLOR_BGR2GRAY)
                 if len(loot_area.shape) == 3 else loot_area)

    numbers_found = []
    for y_offset in range(0, loot_y2 - loot_y1, ENEMY_LOOT_Y_STEP):
        strip = loot_gray[y_offset:y_offset + ENEMY_LOOT_STRIP_HEIGHT, :]
        if strip.size == 0:
            continue
        value = _read_number_template(strip, extra_scales=ENEMY_LOOT_SCALES, is_gray=True)
        if value is not None and value > 1000:
            abs_y = y_offset + loot_y1
            if not any(abs(abs_y - py) < ENEMY_LOOT_Y_DEDUP for py, _ in numbers_found):
                numbers_found.append((abs_y, value))
                if len(numbers_found) >= 2:
                    break

    gold = numbers_found[0][1] if numbers_found else 0
    elixir = numbers_found[1][1] if len(numbers_found) > 1 else 0
    return gold, elixir


# ─── VALIDATION ──────────────────────────────────────────────

def validate_critical_templates():
    """Verify the YOLO model is present and loads correctly. Raises on failure."""
    try:
        _get_detector()
        logger.info("YOLO detector validated successfully")
    except Exception as e:
        raise FileNotFoundError(
            f"YOLO model failed to load: {e}. "
            f"Train the model first: python training/train.py "
            f"--data datasets/full/dataset.yaml"
        ) from e


def auto_capture_template(img, button_name):
    """Legacy no-op: template auto-capture is not needed with YOLO detection."""
    return False
