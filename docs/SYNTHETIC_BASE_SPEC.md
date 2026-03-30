# Synthetic Base Generator — Specification

## Goal

Generate realistic Clash of Clans base screenshots with perfect YOLO bounding box labels for training an object detection model. The synthetic images should look close enough to real scouting screenshots that a model trained on them transfers well to real gameplay.

## CoC Base Layout Rules

### Grid System
- Base grid: **44x44 tiles**
- Buildings snap to integer tile positions
- The view is **isometric** (2.5D) — the grid is a diamond shape rotated 45 degrees
- The buildable area is roughly the central **40x40 tiles** (edges are scenery)
- Isometric projection: screen_x = (tile_x - tile_y) * tile_half_width, screen_y = (tile_x + tile_y) * tile_half_height

### Building Tile Sizes (footprint on the grid)

| Tile Size | Buildings |
|-----------|-----------|
| **1x1** | Wall, all small traps (Bomb, Spring Trap, Tornado Trap) |
| **2x2** | Builder's Hut, Air Bomb, Seeking Air Mine, Giant Bomb, Skeleton Trap |
| **3x3** | Cannon, Archer Tower, Mortar, Wizard Tower, Air Defense, Hidden Tesla, Bomb Tower, Air Sweeper, X-Bow, Inferno Tower, Eagle Artillery, Scattershot, Monolith, Spell Tower, Firespitter, Multi-Archer Tower, Ricochet Cannon, Gold Mine, Elixir Collector, Dark Elixir Drill, Dark Elixir Storage, Blacksmith, Hero Altars (BK, AQ, GW, RC) |
| **4x4** | Town Hall, Clan Castle, Army Camp, Laboratory, Barracks, Dark Barracks, Spell Factory, Dark Spell Factory, Gold Storage, Elixir Storage, Workshop, Pet House, Hero Hall |
| **5x5** | (none in current game) |

### Building Counts at TH15 (typical scouting target)

#### Defenses
| Building | Count | Max Level |
|----------|-------|-----------|
| Cannon | 7 | 21 |
| Archer Tower | 8 | 21 |
| Mortar | 4 | 16 |
| Air Defense | 4 | 14 |
| Wizard Tower | 5 | 16 |
| Air Sweeper | 2 | 7 |
| Hidden Tesla | 5 | 15 |
| Bomb Tower | 3 | 11 |
| X-Bow | 4 | 10 |
| Inferno Tower | 3 | 8 |
| Eagle Artillery | 1 | 6 |
| Scattershot | 2 | 4 |
| Spell Tower | 2 | 2 |
| Monolith | 1 | 2 |
| Builder's Hut | 5 | 5 |
| **Total defenses** | **~56** | |

#### Resource Buildings
| Building | Count | Max Level |
|----------|-------|-----------|
| Gold Mine | 7 | 16 |
| Elixir Collector | 7 | 16 |
| Dark Elixir Drill | 3 | 10 |
| Gold Storage | 4 | 16 |
| Elixir Storage | 4 | 16 |
| Dark Elixir Storage | 1 | 10 |
| **Total resources** | **~26** | |

#### Army Buildings
| Building | Count | Max Level |
|----------|-------|-----------|
| Army Camp | 4 | 12 |
| Barracks | 1 | 17 |
| Dark Barracks | 1 | 12 |
| Laboratory | 1 | 13 |
| Spell Factory | 1 | 7 |
| Dark Spell Factory | 1 | 6 |
| Workshop | 1 | 7 |
| Clan Castle | 1 | 11 |
| Pet House | 1 | 8 |
| Hero Hall | 1 | 9 |
| Blacksmith | 1 | 8 |
| **Total army** | **~14** | |

#### Heroes (Altars)
| Hero | Count |
|------|-------|
| Barbarian King | 1 |
| Archer Queen | 1 |
| Grand Warden | 1 |
| Royal Champion | 1 |
| Minion Prince | 1 |

#### Walls
- **325 wall pieces** at TH15
- Each wall occupies 1x1 tile
- Walls form connected lines/compartments surrounding groups of buildings

#### Traps
| Trap | Count | Size |
|------|-------|------|
| Bomb | 6 | 1x1 |
| Spring Trap | 6 | 1x1 |
| Giant Bomb | 5 | 2x2 |
| Air Bomb | 5 | 2x2 |
| Seeking Air Mine | 5 | 2x2 |
| Skeleton Trap | 4 | 2x2 |
| Tornado Trap | 2 | 1x1 |

**Total buildings on a TH15 base: ~100-110** (not counting walls and traps)
**Total with walls: ~425-435 objects**

## Scouting Screen Layout

A real scouting screenshot (2560x1440) has these regions:

```
+-------------------------------------------------------+
| Player name / TH icon       Timer        Resources HUD |  <- Top HUD
|  Available Loot:                                       |
|  Gold: xxx                                             |
|  Elixir: xxx                                           |
|  DE: xxx                                               |
|                                                        |
|              +------------------------+                |
|             /    ISOMETRIC BASE       \               |
|            /     (diamond shape)       \              |
|           /   44x44 tile grid rotated   \             |
|          /        45 degrees             \            |
|         /                                 \           |
|          \                               /            |
|           \                             /             |
|            \                           /              |
|             \                         /               |
|              +------------------------+                |
|                                                        |
| [End Battle] [Boost Heroes]              [Next 1600]   |  <- Bottom buttons
+-------------------------------------------------------+
| [Troop1] [Troop2] [Troop3] ... [Hero] [Siege]        |  <- Troop bar
+-------------------------------------------------------+
```

### Key Regions (normalized coordinates for 2560x1440)
- **Base diamond area**: roughly x=[0.15, 0.85], y=[0.10, 0.80]
- **Top HUD** (loot display): y < 0.12
- **Bottom buttons**: y > 0.82
- **Troop bar**: y > 0.87
- **Next button**: x > 0.85, y > 0.82

## Sprite-to-Screen Scale

From analyzing real screenshots vs sprite pixel sizes:
- A 3x3 building (cannon, archer tower) appears as roughly **50-80px wide** in a 2560x1440 screenshot
- A 4x4 building (town hall, army camp) appears as roughly **80-130px wide**
- A 1x1 wall piece appears as roughly **15-25px wide**
- Sprites from the wiki are 2-4x larger than their in-game appearance

### Scale Factor
- Wiki sprite average for 3x3 building: ~190px wide
- In-game appearance for 3x3 building: ~65px wide
- **Scale factor: ~0.34** (sprite_px * 0.34 ≈ screen_px)
- This varies by building — use per-building scale calibration

## Generation Strategy

### Phase 1: Simple Compositing (MVP)
1. Use real base screenshots as backgrounds (buildings already present add visual noise = robustness)
2. Paste 30-60 sprites at random positions within the base diamond area
3. Scale sprites to correct game size (~0.3-0.4x of wiki sprite pixel size)
4. Apply slight rotation jitter (±2 degrees) for realism
5. Auto-generate YOLO labels from paste coordinates
6. Add brightness/contrast jitter for augmentation

### Phase 2: Grid-Aware Placement
1. Define the 44x44 isometric grid mapped to screen coordinates
2. Place buildings on valid grid positions (no overlapping tiles)
3. Ensure building spacing follows game rules (buildings can touch but not overlap)
4. Place walls in connected lines between/around building clusters
5. Leave traps scattered in gaps

### Phase 3: Realistic Base Layouts
1. Generate base layouts using compartment patterns:
   - Central core (TH + key defenses)
   - Ring layers expanding outward
   - Wall compartments of 5x5 to 13x13 tiles
2. Assign building types by strategic logic (splash damage spread, point defenses at edges)
3. Add scenery, trees, obstacles at map edges
4. Overlay the HUD from a captured screenshot

## Output Format

- Images: JPEG, 2560x1440 (or 640x640 for YOLO if preferred)
- Labels: YOLO format — `class_id center_x center_y width height` (normalized)
- Dataset split: 85% train / 15% val
- dataset.yaml with compact class index (only classes present in sprites)

## Available Assets

- **569 building sprites** (BGRA PNGs with transparency) across 55 building types
- **224 real base screenshots** for backgrounds
- **250 public labeled images** (16 classes) for additional backgrounds

## Sources

- [Clash of Clans Wiki - Buildings](https://clashofclans.fandom.com/wiki/Buildings)
- [Clash of Clans Wiki - Layouts](https://clashofclans.fandom.com/wiki/Layouts)
- [Base Design Guide](https://www.clashofclans-tools.com/Base-Design-Guide)
- [TH16 Max Levels](https://clashguideswithdusk.net/2024/11/th16-max-levels-list-clash-of-clans/)
- [Isometric Game Development](https://www.gamedeveloper.com/business/quickly-learn-to-create-isometric-games-like-clash-of-clans-or-aoe)
- [Grid Concept](http://akiyume.weebly.com/20-grid-concept.html)
