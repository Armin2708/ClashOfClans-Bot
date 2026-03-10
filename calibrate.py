"""
Calibration tool — automatically detects wall positions and UI coordinates.

Usage:
    python calibrate.py walls      # Detect wall positions and update config
    python calibrate.py resources   # Find resource bar regions
    python calibrate.py buttons     # Find button positions
    python calibrate.py all         # Run all calibrations
    python calibrate.py screenshot  # Just take a screenshot and save it

Make sure you're on the village screen in CoC before running.
"""

import cv2
import numpy as np
import sys
import json
from screen import screenshot


# ─── WALL DETECTION ──────────────────────────────────────────

def detect_walls(img, debug=True):
    """
    Detect wall segments by their distinct gold/yellow color.
    Returns a list of (x, y) center coordinates for each wall.
    """
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # Gold/yellow walls — adjust these ranges if your walls are a different level/color
    # Level 7-8: golden yellow
    # Level 9-10: darker gold
    # Level 11+: lava/dark
    color_ranges = [
        # Bright gold walls
        (np.array([18, 80, 120]), np.array([35, 255, 255])),
        # Darker gold walls
        (np.array([15, 60, 100]), np.array([40, 255, 255])),
        # Orange-gold walls
        (np.array([10, 80, 130]), np.array([25, 255, 255])),
    ]

    combined_mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
    for lower, upper in color_ranges:
        mask = cv2.inRange(hsv, lower, upper)
        combined_mask = cv2.bitwise_or(combined_mask, mask)

    # Clean up noise
    kernel = np.ones((3, 3), np.uint8)
    combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, kernel, iterations=1)

    # Find contours
    contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    wall_positions = []
    # Filter by contour area — walls are small, uniform-sized squares
    areas = [cv2.contourArea(c) for c in contours if cv2.contourArea(c) > 50]
    if not areas:
        print("No wall candidates found. Try adjusting color ranges.")
        return []

    median_area = np.median(areas)
    min_area = median_area * 0.3
    max_area = median_area * 3.0

    for c in contours:
        area = cv2.contourArea(c)
        if min_area < area < max_area:
            M = cv2.moments(c)
            if M["m00"] > 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                wall_positions.append((cx, cy))

    # Remove duplicates that are too close together
    wall_positions = deduplicate(wall_positions, min_dist=20)

    # Sort: top-to-bottom, then left-to-right
    wall_positions.sort(key=lambda p: (p[1] // 30, p[0]))

    if debug:
        debug_img = img.copy()
        for (x, y) in wall_positions:
            cv2.circle(debug_img, (x, y), 8, (0, 0, 255), 2)
        cv2.imwrite("debug_walls.png", debug_img)
        print(f"Debug image saved to debug_walls.png — check that red circles are on walls")

    return wall_positions


def deduplicate(points, min_dist=20):
    """Remove points that are too close together."""
    if not points:
        return []
    filtered = [points[0]]
    for p in points[1:]:
        if all(abs(p[0] - f[0]) > min_dist or abs(p[1] - f[1]) > min_dist for f in filtered):
            filtered.append(p)
    return filtered


# ─── RESOURCE BAR DETECTION ──────────────────────────────────

def detect_resource_regions(img):
    """
    Find the resource bars (gold, elixir, dark elixir) by looking for
    their icons on the right side of the screen.
    """
    h, w = img.shape[:2]
    # Resources are in the top-right quadrant
    right_strip = img[0:h // 3, w // 2:]

    # Gold icon is a distinct gold coin color
    # Elixir icon is pink/purple
    # Dark elixir icon is dark purple/black

    hsv = cv2.cvtColor(right_strip, cv2.COLOR_BGR2HSV)

    # Gold coin — bright yellow/orange circle
    gold_mask = cv2.inRange(hsv, np.array([15, 100, 150]), np.array([35, 255, 255]))
    # Elixir — pink/magenta
    elixir_mask = cv2.inRange(hsv, np.array([140, 50, 100]), np.array([170, 255, 255]))
    # Dark elixir — dark purple
    dark_mask = cv2.inRange(hsv, np.array([120, 30, 30]), np.array([150, 200, 150]))

    results = {}
    offset_x = w // 2

    for name, mask in [("gold", gold_mask), ("elixir", elixir_mask), ("dark_elixir", dark_mask)]:
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            largest = max(contours, key=cv2.contourArea)
            x, y, cw, ch = cv2.boundingRect(largest)
            # The number region is to the LEFT of the icon
            # Estimate: digits span about 250px to the left of the icon
            icon_x = x + offset_x
            icon_y = y
            num_region = (icon_x - 300, icon_y, icon_x - 10, icon_y + ch)
            results[name] = {
                "icon": (icon_x + cw // 2, icon_y + ch // 2),
                "region": num_region
            }
            print(f"  {name}: icon at ({icon_x + cw // 2}, {icon_y + ch // 2}), "
                  f"number region: {num_region}")

    return results


# ─── BUTTON DETECTION ────────────────────────────────────────

def detect_attack_button(img):
    """Find the Attack button in the bottom-left corner."""
    h, w = img.shape[:2]
    # Attack button is in the bottom-left
    bottom_left = img[h * 3 // 4:, 0:w // 4]

    # The Attack button has a distinct orange/red background
    hsv = cv2.cvtColor(bottom_left, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array([5, 100, 100]), np.array([20, 255, 255]))

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        largest = max(contours, key=cv2.contourArea)
        M = cv2.moments(largest)
        if M["m00"] > 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"]) + h * 3 // 4
            print(f"  Attack button: ({cx}, {cy})")
            return (cx, cy)

    print("  Attack button: not found")
    return None


# ─── CONFIG WRITER ───────────────────────────────────────────

def write_wall_positions(positions):
    """Update WALL_POSITIONS in config.py with detected positions."""
    # Read current config
    with open("config.py", "r") as f:
        content = f.read()

    # Build the new wall positions block
    lines = ["WALL_POSITIONS = ["]
    for i, (x, y) in enumerate(positions):
        lines.append(f"    ({x}, {y}),")
    lines.append("]")
    new_block = "\n".join(lines)

    # Find and replace the WALL_POSITIONS section
    # Look for WALL_POSITIONS = ... up to the next blank line or next config section
    import re
    # Match from WALL_POSITIONS to the closing bracket, accounting for the helper function
    pattern = re.compile(
        r'(# ─── WALL POSITIONS[^\n]*\n)'  # header comment
        r'(.*?)'                             # everything in between
        r'(\n# ─── WALL COSTS)',             # next section
        re.DOTALL
    )

    match = pattern.search(content)
    if match:
        replacement = match.group(1) + new_block + "\n" + match.group(3)
        content = content[:match.start()] + replacement + content[match.end():]
    else:
        # Fallback: just replace the WALL_POSITIONS list
        pattern2 = re.compile(r'WALL_POSITIONS\s*=\s*[\[\(].*?[\]\)]', re.DOTALL)
        content = pattern2.sub(new_block, content)

    # Remove the helper function if it exists
    content = re.sub(
        r'def _generate_wall_grid\(.*?\n\n',
        '',
        content,
        flags=re.DOTALL
    )
    # Remove the generator variables
    content = re.sub(r'_MAIN_START_X.*?\n', '', content)
    content = re.sub(r'_MAIN_START_Y.*?\n', '', content)
    content = re.sub(r'_MAIN_SPACING_X.*?\n', '', content)
    content = re.sub(r'_MAIN_SPACING_Y.*?\n', '', content)
    content = re.sub(r'_MAIN_COLS.*?\n', '', content)
    content = re.sub(r'_MAIN_ROWS.*?\n', '', content)
    content = re.sub(r'_STRIP_START_X.*?\n', '', content)
    content = re.sub(r'_STRIP_START_Y.*?\n', '', content)
    content = re.sub(r'_STRIP_SPACING_X.*?\n', '', content)
    content = re.sub(r'_STRIP_SPACING_Y.*?\n', '', content)
    content = re.sub(r'_STRIP_COLS.*?\n', '', content)
    content = re.sub(r'_STRIP_ROWS.*?\n', '', content)

    # Clean up multiple blank lines
    content = re.sub(r'\n{3,}', '\n\n', content)

    with open("config.py", "w") as f:
        f.write(content)

    print(f"\nWrote {len(positions)} wall positions to config.py")


def update_config_value(name, value):
    """Update a single value in config.py."""
    with open("config.py", "r") as f:
        content = f.read()

    import re
    pattern = re.compile(rf'^{name}\s*=\s*.*$', re.MULTILINE)
    if pattern.search(content):
        content = pattern.sub(f"{name} = {value}", content)
    else:
        content += f"\n{name} = {value}\n"

    with open("config.py", "w") as f:
        f.write(content)
    print(f"  Updated {name} = {value}")


# ─── MAIN ────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    command = sys.argv[1].lower()

    if command == "screenshot":
        print("Taking screenshot...")
        img = screenshot()
        cv2.imwrite("calibration_screenshot.png", img)
        print(f"Saved calibration_screenshot.png ({img.shape[1]}x{img.shape[0]})")
        return

    print("Taking screenshot...")
    img = screenshot()
    cv2.imwrite("calibration_screenshot.png", img)
    print(f"Screenshot: {img.shape[1]}x{img.shape[0]}\n")

    if command in ("walls", "all"):
        print("=== DETECTING WALLS ===")
        walls = detect_walls(img)
        print(f"Found {len(walls)} wall segments")
        if walls:
            write_wall_positions(walls)
            print("Open debug_walls.png to verify the detected positions.")
            print("If walls are missed, try adjusting the HSV color ranges in calibrate.py")

    if command in ("resources", "all"):
        print("\n=== DETECTING RESOURCE BARS ===")
        resources = detect_resource_regions(img)
        if "gold" in resources:
            update_config_value("GOLD_REGION", resources["gold"]["region"])
        if "elixir" in resources:
            update_config_value("ELIXIR_REGION", resources["elixir"]["region"])
        if "dark_elixir" in resources:
            update_config_value("DARK_ELIXIR_REGION", resources["dark_elixir"]["region"])

    if command in ("buttons", "all"):
        print("\n=== DETECTING BUTTONS ===")
        attack_pos = detect_attack_button(img)
        if attack_pos:
            update_config_value("ATTACK_BUTTON", attack_pos)

    if command == "all":
        print("\n=== UPDATING RESOLUTION ===")
        update_config_value("SCREEN_WIDTH", img.shape[1])
        update_config_value("SCREEN_HEIGHT", img.shape[0])

    print("\nCalibration complete!")
    print("Run 'python calibrate.py screenshot' anytime to take a fresh screenshot.")
    print("Run tests with: python -c \"from resources import get_resources; print(get_resources())\"")


if __name__ == "__main__":
    main()
