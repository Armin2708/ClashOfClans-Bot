# Clash of Clans Bot — Setup Guide

## 1. Install BlueStacks 5

1. Download BlueStacks 5 from bluestacks.com
2. Install and launch it
3. Sign in with a Google account
4. Open the Play Store inside BlueStacks → search "Clash of Clans" → install
5. Launch CoC once manually to make sure it runs

## 2. Enable ADB in BlueStacks

1. Click the gear icon (Settings) in BlueStacks
2. Go to **Advanced**
3. Toggle **Android Debug Bridge (ADB)** to ON
4. Note the port shown (usually `5555` or `5585`)

## 3. Install System Dependencies

```bash
# ADB (talks to the emulator)
brew install android-platform-tools

# Tesseract OCR (reads text from screenshots)
brew install tesseract

# Verify both installed
adb version
tesseract --version
```

## 4. Connect ADB to BlueStacks

```bash
adb connect localhost:5555
adb devices
```

You should see `localhost:5555  device`. If it fails, try port `5585` or check BlueStacks Settings → Advanced for the correct port.

## 5. Install Python Dependencies

```bash
cd ~/Desktop/clashofclans
pip install -r requirements.txt
```

## 6. Check Your Emulator Resolution

```bash
adb shell wm size
```

Update `SCREEN_WIDTH` and `SCREEN_HEIGHT` in `config.py` to match.

## 7. Capture Reference Screenshots

Open CoC in BlueStacks and take screenshots from each game state. You need to be in that state first (e.g. open the attack menu before screenshotting it).

```bash
cd ~/Desktop/clashofclans

# Village screen (with gold/elixir visible at top)
adb exec-out screencap -p > ref_village.png

# Attack menu (tap the Attack button first)
adb exec-out screencap -p > ref_attack_menu.png

# Army screen (tap "Find a Match" to get here)
adb exec-out screencap -p > ref_army.png

# During a battle (start one manually)
adb exec-out screencap -p > ref_battle.png

# Results/stars screen (after a battle ends)
adb exec-out screencap -p > ref_results.png

# Wall info screen (tap a wall in your village — shows the upgrade button)
adb exec-out screencap -p > ref_wall_info.png

# Wall confirm screen (tap the upgrade button — shows cost and confirm)
adb exec-out screencap -p > ref_wall_confirm.png

# Any popup that appears (clan messages, trader, events, etc.)
adb exec-out screencap -p > ref_popup.png
```

## 8. Create Template Images

Open each reference screenshot in an image editor (Preview, GIMP, Photoshop) and crop out the following elements. Save each crop tightly around the element — no extra space.

### From `ref_village.png`:
| Crop | Save to |
|------|---------|
| Each digit (0-9) from the gold/elixir numbers at the top | `templates/digits/0.png` through `9.png` |
| The "Attack!" button (bottom of screen) | `templates/buttons/attack_button.png` |
| The gem icon (small gem next to resource costs) | `templates/buttons/gem_cost.png` |

### From `ref_attack_menu.png`:
| Crop | Save to |
|------|---------|
| The "Find a Match" button | `templates/buttons/find_match.png` |

### From `ref_army.png`:
| Crop | Save to |
|------|---------|
| The "Start Battle" button | `templates/buttons/start_battle.png` |

### From `ref_battle.png` (scouting an enemy base):
| Crop | Save to |
|------|---------|
| The enemy Town Hall building | `templates/townhall/th_X.png` (X = TH level, e.g. `th_10.png`) |
| The "Next" button (skip to next base) | `templates/buttons/next_base.png` |

### From `ref_results.png`:
| Crop | Save to |
|------|---------|
| The stars overlay / results banner | `templates/buttons/stars_screen.png` |
| The "Return Home" button | `templates/buttons/return_home.png` |

### From `ref_wall_info.png` (after tapping a wall):
| Crop | Save to |
|------|---------|
| The upgrade button (hammer icon) | `templates/buttons/upgrade_wall.png` |

### From `ref_wall_confirm.png` (after tapping the upgrade button):
| Crop | Save to |
|------|---------|
| The confirm upgrade button | `templates/buttons/confirm_upgrade.png` |
| The gem icon (if visible next to the cost) | `templates/buttons/gem_cost.png` |

### From `ref_popup.png` (capture each popup type you see):
| Crop | Save to |
|------|---------|
| X / close button | `templates/popups/close_x.png` |
| "Okay" button | `templates/popups/okay_button.png` |
| "Later" button | `templates/popups/later_button.png` |

## 9. Auto-Calibrate with `calibrate.py`

Instead of manually finding coordinates, use the calibration tool. Make sure CoC is open on your village screen, then:

```bash
cd ~/Desktop/clashofclans

# Calibrate everything at once (walls, resources, buttons, resolution)
python calibrate.py all
```

This will:
- Take a screenshot from the emulator
- Detect all wall positions by color and write them to `config.py`
- Find the resource bar regions and update `config.py`
- Find the Attack button position and update `config.py`
- Save `debug_walls.png` — **open this to verify** the red circles are on your walls

You can also run each step individually:
```bash
python calibrate.py walls       # Detect walls only
python calibrate.py resources   # Detect resource bars only
python calibrate.py buttons     # Detect button positions only
python calibrate.py screenshot  # Just save a screenshot for inspection
```

If the wall detection misses walls or picks up non-walls, adjust the HSV color ranges in `calibrate.py` for your wall level.

**Still manual** (calibrate.py doesn't detect these — set them in `config.py`):
- `FIND_MATCH_BUTTON` — center of "Find a Match" in the attack menu
- `START_BATTLE_BUTTON` — center of "Start Battle" on the army screen
- `TROOP_BAR_REGION` — the troop bar at the bottom during battle

To find these, take screenshots from those screens and open them in an image editor:
```bash
# Open attack menu in CoC first, then:
python calibrate.py screenshot
# Open calibration_screenshot.png and note the button coordinates
```

## 10. Test Each Module

Run these one at a time to verify each piece works:

```bash
cd ~/Desktop/clashofclans

# Test screenshot capture
python -c "from screen import screenshot; import cv2; img = screenshot(); cv2.imwrite('test.png', img); print('OK')"

# Test a tap (taps center of screen)
python -c "from screen import tap; tap(960, 540); print('OK')"

# Test resource reading (must be on village screen in CoC)
python -c "from resources import get_resources; print(get_resources())"
```

## 12. Run the Bot

```bash
python main.py
```

The bot will loop: check resources → upgrade walls if affordable → attack if not → repeat.

## Battle Flow

```
Village → Attack button → Find a Match → Army Screen → Start Battle → Clouds → Battle → Stars → Return Home → Village
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `adb devices` shows nothing | Enable ADB in BlueStacks settings, restart emulator |
| Screenshot is all black | Wrong ADB port — try `adb connect localhost:5585` |
| OCR reads wrong numbers | Recalibrate `GOLD_REGION`/`ELIXIR_REGION`, or use digit templates instead |
| Bot taps wrong locations | Resolution mismatch — run `adb shell wm size` and update `config.py` |
| Game disconnects during idle | Supercell timeout — bot's regular actions should keep it alive |
| Popups block the bot | Screenshot the popup, crop the dismiss button, add to `templates/popups/` |
| Gems get spent accidentally | Make gem template more precise, increase `MIN_GOLD_FOR_WALLS` |
| Troops deploy in wrong spot | Add more TH templates at different scales, or lower detection threshold |

## Safety Notes

- The bot checks for gem costs **twice** before confirming any wall upgrade
- Set `MIN_GOLD_FOR_WALLS` high enough that you're clearly able to afford upgrades
- For testing, do a dry run: watch the bot for a full loop before leaving it unattended
