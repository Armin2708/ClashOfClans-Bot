"""
Auto-extract template images from your reference screenshots.
Coordinates measured from pixel analysis of debug crops.

Usage:
    python extract_templates.py
"""

import cv2
import os


def crop_and_save(img, x1, y1, x2, y2, path, label=""):
    h, w = img.shape[:2]
    x1, y1 = max(0, int(x1)), max(0, int(y1))
    x2, y2 = min(w, int(x2)), min(h, int(y2))
    crop = img[y1:y2, x1:x2]
    if crop.size == 0:
        print(f"  SKIP {path} — empty crop")
        return False
    cv2.imwrite(path, crop)
    print(f"  OK   {path} ({x2 - x1}x{y2 - y1}) {label}")
    return True


def main():
    os.makedirs("templates/buttons", exist_ok=True)
    os.makedirs("templates/popups", exist_ok=True)

    # ─── VILLAGE: "Attack!" button ────────────────────────
    print("\n=== ref_village.png ===")
    img = cv2.imread("ref_village.png")
    if img is not None:
        print(f"  Resolution: {img.shape[1]}x{img.shape[0]}")
        crop_and_save(img, 10, 1260, 200, 1430,
                      "templates/buttons/attack_button.png", "(Attack!)")
    else:
        print("  NOT FOUND")

    # ─── ATTACK MENU: "Find a Match 1700" ─────────────────
    print("\n=== ref_attack_menu.png ===")
    img = cv2.imread("ref_attack_menu.png")
    if img is not None:
        print(f"  Resolution: {img.shape[1]}x{img.shape[0]}")
        crop_and_save(img, 145, 1070, 735, 1160,
                      "templates/buttons/find_match.png", "(Find a Match)")
    else:
        print("  NOT FOUND")

    # ─── ARMY: Green "Attack!" button ─────────────────────
    print("\n=== ref_army.png ===")
    img = cv2.imread("ref_army.png")
    if img is not None:
        print(f"  Resolution: {img.shape[1]}x{img.shape[0]}")
        crop_and_save(img, 2015, 1230, 2510, 1340,
                      "templates/buttons/start_battle.png", "(Army Attack!)")
    else:
        print("  NOT FOUND")

    # ─── BATTLE: "Next 1700" and "End Battle" ─────────────
    print("\n=== ref_battle.png ===")
    img = cv2.imread("ref_battle.png")
    if img is not None:
        print(f"  Resolution: {img.shape[1]}x{img.shape[0]}")
        # Next button: right quarter bottom half crop shows it at crop(340,310)-(560,430)
        # Debug image offset: x+1920, y+720
        crop_and_save(img, 2250, 1020, 2490, 1160,
                      "templates/buttons/next_base.png", "(Next 1700)")
        # End Battle: red button bottom-left
        crop_and_save(img, 30, 1075, 340, 1130,
                      "templates/buttons/end_battle.png", "(End Battle)")
    else:
        print("  NOT FOUND")

    # ─── RESULTS: "Return Home" and stars ─────────────────
    print("\n=== ref_results.png ===")
    img = cv2.imread("ref_results.png")
    if img is not None:
        print(f"  Resolution: {img.shape[1]}x{img.shape[0]}")
        crop_and_save(img, 1100, 1158, 1462, 1318,
                      "templates/buttons/return_home.png", "(Return Home)")
        crop_and_save(img, 880, 250, 1680, 600,
                      "templates/buttons/stars_screen.png", "(Victory/Stars)")
    else:
        print("  NOT FOUND")

    # ─── WALL INFO: "Upgrade" buttons ─────────────────────
    print("\n=== ref_wall_info.png ===")
    img = cv2.imread("ref_wall_info.png")
    if img is not None:
        print(f"  Resolution: {img.shape[1]}x{img.shape[0]}")
        # Bottom bar buttons. From debug_wallinfo_bottom (y offset +1080):
        # 5th button (gold Upgrade): x:1550-1790, crop y:40-310 → abs y:1120-1390
        crop_and_save(img, 1540, 1110, 1800, 1400,
                      "templates/buttons/upgrade_wall.png", "(Upgrade gold)")
        # 6th button (elixir Upgrade): x:1850-2080
        crop_and_save(img, 1840, 1110, 2100, 1400,
                      "templates/buttons/upgrade_wall_elixir.png", "(Upgrade elixir)")
    else:
        print("  NOT FOUND")

    # ─── WALL CONFIRM: "Confirm" and X close ─────────────
    print("\n=== ref_wall_confirm.png ===")
    img = cv2.imread("ref_wall_confirm.png")
    if img is not None:
        print(f"  Resolution: {img.shape[1]}x{img.shape[0]}")
        # Confirm button: green button with "5 600 000" gold cost
        # Located at x:1450-2000, y:1220-1340
        crop_and_save(img, 1450, 1220, 2000, 1340,
                      "templates/buttons/confirm_upgrade.png", "(Confirm)")
        # Red X from debug_wallconfirm_topright (x offset +1280, y offset 0):
        # crop x:860-940, y:50-140 → abs x:2140-2220, y:50-140
        crop_and_save(img, 2130, 40, 2230, 150,
                      "templates/popups/close_x.png", "(X close)")
    else:
        print("  NOT FOUND")

    print("\n=== DONE ===")
    print("\nRun: python test.py buttons")


if __name__ == "__main__":
    main()
