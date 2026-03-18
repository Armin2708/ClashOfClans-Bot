import cv2
import numpy as np
import os
import sys
from bot.config import TEMPLATE_THRESHOLD


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller bundle."""
    if getattr(sys, '_MEIPASS', None):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


def find_template(img, template, threshold=None):
    """Find a template in the image using grayscale matching.
    Tries a few scales around 1.0 to handle slight size mismatches
    from resolution scaling.
    Returns (x, y) center or None."""
    if template is None:
        return None
    if threshold is None:
        threshold = TEMPLATE_THRESHOLD

    if len(img.shape) == 3:
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        img_gray = img

    if len(template.shape) == 3:
        tmpl_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    else:
        tmpl_gray = template

    best_val = 0
    best_loc = None
    best_shape = tmpl_gray.shape[:2]

    for scale in (1.0, 0.95, 1.05, 0.9, 1.1):
        if scale == 1.0:
            scaled = tmpl_gray
        else:
            h, w = tmpl_gray.shape[:2]
            sw, sh = max(1, int(w * scale)), max(1, int(h * scale))
            if sh > img_gray.shape[0] or sw > img_gray.shape[1]:
                continue
            scaled = cv2.resize(tmpl_gray, (sw, sh), interpolation=cv2.INTER_AREA)

        result = cv2.matchTemplate(img_gray, scaled, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        if max_val > best_val:
            best_val = max_val
            best_loc = max_loc
            best_shape = scaled.shape[:2]
        if best_val >= threshold:
            break

    if best_val >= threshold:
        h, w = best_shape
        return (best_loc[0] + w // 2, best_loc[1] + h // 2)
    return None


def find_all_templates(img, template, threshold=None, min_dist=20):
    """Find ALL occurrences of a template using grayscale matching.
    Returns list of (x, y) centers."""
    if template is None:
        return []
    if threshold is None:
        threshold = TEMPLATE_THRESHOLD

    if len(img.shape) == 3:
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        img_gray = img

    if len(template.shape) == 3:
        tmpl_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    else:
        tmpl_gray = template

    result = cv2.matchTemplate(img_gray, tmpl_gray, cv2.TM_CCOEFF_NORMED)
    locations = np.where(result >= threshold)
    h, w = tmpl_gray.shape[:2]

    points = []
    for (y, x) in zip(*locations):
        cx, cy = x + w // 2, y + h // 2
        # Deduplicate nearby detections
        if not any(abs(cx - px) < min_dist and abs(cy - py) < min_dist for px, py in points):
            points.append((cx, cy))
    return points


def load_template(path):
    """Load a template image, return None if not found."""
    resolved = resource_path(path)
    if not os.path.exists(resolved):
        return None
    return cv2.imread(resolved)


def load_template_gray(path):
    """Load a template as grayscale, return None if not found."""
    resolved = resource_path(path)
    if not os.path.exists(resolved):
        return None
    img = cv2.imread(resolved)
    if img is None:
        return None
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def save_debug(img, filename, points=None, regions=None):
    """Save a debug image with optional markers."""
    debug = img.copy()
    if points:
        for (x, y) in points:
            cv2.circle(debug, (x, y), 10, (0, 0, 255), 3)
    if regions:
        for (x1, y1, x2, y2) in regions:
            cv2.rectangle(debug, (x1, y1), (x2, y2), (0, 255, 0), 2)
    cv2.imwrite(filename, debug)
