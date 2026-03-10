# ─── SCREEN RESOLUTION ────────────────────────────────────
SCREEN_WIDTH = 2560
SCREEN_HEIGHT = 1440

# ─── ADB ─────────────────────────────────────────────────
ADB_PATH = "adb"
GAME_PACKAGE = "com.supercell.clashofclans"

# ─── THRESHOLDS ───────────────────────────────────────────
# Minimum loot on an enemy base to attack (gold OR elixir)
MIN_LOOT_TO_ATTACK = 1_000_000

# Resource storage capacity — when both are at or above this, upgrade walls
GOLD_STORAGE_FULL = 8_000_000
ELIXIR_STORAGE_FULL = 8_000_000

# ─── TIMING ───────────────────────────────────────────────
BATTLE_CHECK_INTERVAL = 5    # seconds between screenshots AFTER troops deployed
LOOP_DELAY = 3               # seconds between main loop iterations
APP_LAUNCH_WAIT = 15         # seconds to wait after launching the app
SCOUT_WAIT = 3               # seconds to wait for next base to load
BATTLE_TIMEOUT = 180         # max seconds to wait for battle to end

# ─── TEMPLATE MATCHING ───────────────────────────────────
TEMPLATE_THRESHOLD = 0.75    # default confidence threshold
SCREEN_DETECT_THRESHOLD = 0.72  # threshold for screen state detection
WALL_MATCH_THRESHOLD = 0.7  # threshold for wall template matching

# ─── BUTTON ROI REGIONS (for fast screen state detection) ─
# Each button only appears in a known area of the screen.
# Cropping to these ROIs before template matching is ~100-200x faster
# than scanning the full 2560x1440 image.
# Format: (x1, y1, x2, y2)
BUTTON_ROIS = {
    "attack_button":  (0, 1050, 500, 1440),       # bottom-left
    "find_match":     (50, 1000, 800, 1300),        # left-center
    "start_battle":   (1800, 1050, 2560, 1440),    # bottom-right
    "stars_screen":   (800, 200, 1700, 800),       # center-top
    "return_home":    (800, 900, 1700, 1400),      # center
    "next_base":      (2000, 950, 2560, 1440),     # bottom-right
    "end_battle":     (0, 1000, 500, 1440),        # bottom-left
}

# ─── RESOURCE REGIONS (pixel coordinates at 2560x1440) ───
# Village screen: gold and elixir in top-right
GOLD_REGION = (2100, 55, 2500, 105)      # x1, y1, x2, y2
ELIXIR_REGION = (2100, 180, 2500, 240)   # x1, y1, x2, y2

# Enemy scout screen: loot numbers in top-left
ENEMY_LOOT_X_RANGE = (80, 400)
ENEMY_LOOT_Y_RANGE = (150, 450)
ENEMY_LOOT_STRIP_HEIGHT = 50
ENEMY_LOOT_Y_STEP = 10
ENEMY_LOOT_Y_DEDUP = 50  # min Y distance between distinct loot lines
ENEMY_LOOT_SCALES = [0.9, 1.0, 1.2, 1.5, 2.0]

# ─── TROOP DEPLOYMENT ───────────────────────────────────
TROOP_BAR_Y_RATIO = 0.85   # troop bar Y as fraction of screen height
DEPLOY_NUM_POINTS = 15      # number of deploy points along the corner
DEPLOY_X_START = 0.1        # deploy line start X (fraction of width)
DEPLOY_X_END = 0.4          # deploy line end X (fraction of width)
DEPLOY_Y_START = 0.35       # deploy line start Y (fraction of height)
DEPLOY_Y_END = 0.10         # deploy line end Y (fraction of height)
DEPLOY_SWIPE_ROUNDS = 3     # rounds of swiping troop bar for more troops
FALLBACK_TROOP_SLOTS = 8    # number of fallback slots if detection fails
FALLBACK_TROOP_X_START = 100
FALLBACK_TROOP_X_SPACING = 80

# ─── TROOP SLOT DETECTION ───────────────────────────────
TROOP_SLOT_MIN_AREA = 1000
TROOP_SLOT_MAX_AREA = 50000
TROOP_SLOT_MIN_ASPECT = 0.5
TROOP_SLOT_MAX_ASPECT = 2.0
TROOP_SLOT_MIN_DIST = 60
TROOP_SLOT_GRAY_THRESH = 80

# ─── BATTLE SCOUTING ────────────────────────────────────
MAX_BASE_SKIPS = 30         # max bases to scout before giving up

# ─── DEPLOY SWIPE (expose top-left corner) ──────────────
DEPLOY_SWIPE_X1 = 800
DEPLOY_SWIPE_Y1 = 700
DEPLOY_SWIPE_X2 = 1600
DEPLOY_SWIPE_Y2 = 700
DEPLOY_SWIPE_DURATION = 500

# ─── WALL DETECTION ──────────────────────────────────────

# Game area bounds (exclude UI elements at edges)
# Walls should only be in the central game area
GAME_AREA = (120, 80, 2400, 1250)  # x1, y1, x2, y2

# Wall template matching scales and deduplication
WALL_SCALES = [0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.5]
WALL_DEDUP_DIST = 25       # min pixel distance between wall detections
WALL_SORT_ROW_HEIGHT = 30  # group walls into rows of this height for sorting

# Neutral tap location to deselect (top-left corner, away from UI)
EMPTY_TAP = (20, 700)
