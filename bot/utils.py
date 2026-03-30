import cv2
import os
import sys


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller bundle."""
    if getattr(sys, '_MEIPASS', None):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


def writable_path(relative_path):
    """Get a writable path for saving resources at runtime.
    In a PyInstaller bundle, _MEIPASS is read-only so we use ~/.cocbot/.
    In dev mode, just use the project directory."""
    if getattr(sys, '_MEIPASS', None):
        return os.path.join(os.path.expanduser("~"), ".cocbot", relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


def load_template(path):
    """Load a template image, return None if not found.
    Checks writable path first (for auto-captured templates), then bundle/dev path."""
    writable = writable_path(path)
    if os.path.exists(writable):
        return cv2.imread(writable)
    resolved = resource_path(path)
    if not os.path.exists(resolved):
        return None
    return cv2.imread(resolved)


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
