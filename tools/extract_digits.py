"""
Extract digit templates (0-9) from a known resource number on screen.

This takes a screenshot of your village, reads the gold number area,
and saves each individual digit as a template.

You need to know your current gold amount to label the digits.

Usage:
    python extract_digits.py 13827900

The number you pass MUST match what's currently showing on screen.
"""

import cv2
import numpy as np
import sys
import os


def extract_digits(img, y1, y2, x1, x2, known_number):
    """
    Extract individual digit templates from a region containing a known number.
    Uses contour detection to find each digit, then maps to known_number.
    """
    crop = img[y1:y2, x1:x2]

    # Use HSV to find white/bright text regardless of background color
    # White text has high value and low saturation
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    # White: any hue, low saturation (<80), high value (>180)
    white_mask = cv2.inRange(hsv, np.array([0, 0, 180]), np.array([180, 80, 255]))

    # Also catch bright gray text with simple threshold as fallback
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    _, bright_mask = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)

    # Combine both masks
    thresh = cv2.bitwise_or(white_mask, bright_mask)

    # Find contours (each digit should be a separate contour)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Get bounding rects, filter by size, sort left to right
    rects = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        # Digits should be:
        #   - at least 8px tall and 4px wide
        #   - not too wide (>35px = merged digits or green bar)
        #   - not too narrow (<10px unless it's a "1")
        #   - not taller than the crop
        if h > 8 and w > 4 and w < 35 and h < (y2 - y1) and w < (x2 - x1) // 2:
            rects.append((x, y, w, h))

    rects.sort(key=lambda r: r[0])

    # Remove the digits string spaces — we just want the raw digits
    digits_str = known_number.replace(" ", "").replace(",", "")

    print(f"Found {len(rects)} contours for {len(digits_str)} digits")

    if len(rects) != len(digits_str):
        print(f"WARNING: contour count ({len(rects)}) != digit count ({len(digits_str)})")
        print("Contours found:")
        for i, (x, y, w, h) in enumerate(rects):
            print(f"  [{i}] x={x} y={y} w={w} h={h}")

        # Filter: digits should have similar height and width
        if rects:
            heights = [h for _, _, _, h in rects]
            widths = [w for _, _, w, _ in rects]
            median_h = np.median(heights)
            median_w = np.median(widths)
            rects = [(x, y, w, h) for x, y, w, h in rects
                     if h > median_h * 0.6 and w < median_w * 2.5]
            rects.sort(key=lambda r: r[0])
            print(f"After size filter: {len(rects)} contours")

    if len(rects) != len(digits_str):
        print("Still mismatched. Saving debug image...")
        debug = cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)
        for i, (x, y, w, h) in enumerate(rects):
            cv2.rectangle(debug, (x, y), (x + w, y + h), (0, 0, 255), 1)
            cv2.putText(debug, str(i), (x, y - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
        cv2.imwrite("debug_digit_contours.png", debug)
        print("Open debug_digit_contours.png to see what was found")
        return False

    # Save each digit template
    os.makedirs("data/templates/digits", exist_ok=True)
    saved = set()

    for i, ((x, y, w, h), digit_char) in enumerate(zip(rects, digits_str)):
        digit = int(digit_char)
        # Add padding around the digit
        pad = 2
        dx1 = max(0, x - pad)
        dy1 = max(0, y - pad)
        dx2 = min(crop.shape[1], x + w + pad)
        dy2 = min(crop.shape[0], y + h + pad)

        digit_img = crop[dy1:dy2, dx1:dx2]

        # Only save if we haven't saved this digit yet (use the cleanest one)
        path = f"data/templates/digits/{digit}.png"
        if digit not in saved:
            cv2.imwrite(path, digit_img)
            saved.add(digit)
            print(f"  Saved {digit_char} -> {path} ({dx2-dx1}x{dy2-dy1})")
        else:
            print(f"  Skip {digit_char} (already saved)")

    print(f"\nSaved templates for digits: {sorted(saved)}")
    missing = set(range(10)) - saved
    if missing:
        print(f"Missing digits: {sorted(missing)}")
        print("These will be extracted when they appear in a future number")

    return True


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python extract_digits.py <number>              # Extract from gold region")
        print("  python extract_digits.py <number> elixir       # Extract from elixir region")
        print("  python extract_digits.py debug                 # Save debug crops of both regions")
        return

    from bot.screen import screenshot
    img = screenshot()
    h, w = img.shape[:2]
    print(f"Screenshot: {w}x{h}")

    if sys.argv[1] == "debug":
        # Save crops of both resource regions so we can see what the bot reads
        gold_crop = img[55:115, 2000:2500]
        cv2.imwrite("debug_gold_region.png", gold_crop)
        print(f"Saved debug_gold_region.png ({gold_crop.shape[1]}x{gold_crop.shape[0]})")

        elixir_crop = img[180:240, 2000:2500]
        cv2.imwrite("debug_elixir_region.png", elixir_crop)
        print(f"Saved debug_elixir_region.png ({elixir_crop.shape[1]}x{elixir_crop.shape[0]})")
        print("\nOpen these images to check the number regions are correct")
        return

    known_number = sys.argv[1]
    region = sys.argv[2] if len(sys.argv) > 2 else "gold"

    print(f"Extracting digits for: {known_number} (from {region} region)")

    if region == "elixir":
        print("\nExtracting from elixir number region...")
        extract_digits(img, 180, 240, 2000, 2500, known_number)
    else:
        print("\nExtracting from gold number region...")
        extract_digits(img, 55, 115, 2000, 2500, known_number)


if __name__ == "__main__":
    main()
