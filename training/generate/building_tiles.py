"""
Building tile footprint definitions for Clash of Clans.

Each building occupies an NxN diamond on the isometric grid.
These values are verified against the in-game base editor.

Sprite positioning note (2.5D isometric):
  Buildings are rendered in 2.5D — the sprite shows both the top face
  and the front face of the building. This means:
  - The sprite's BOTTOM edge represents the front-bottom of the diamond
  - The sprite extends UPWARD above the diamond (showing the building height)
  - Centering should align the sprite's bottom-center with the diamond's
    bottom corner, NOT the geometric center of the diamond
  - When rendering back-to-front, sort by (tile_y + tile_x) ascending
    so nearer buildings draw on top
"""

# ── Tile size assignments ───────────────────────────────────────────

# 1x1 — walls and small traps
TILES_1x1 = [
    "wall",
    "bomb_trap",
    "spring_trap",
    "tornado_trap",
    "air_bomb_trap",
    "seeking_air_mine",
    "skeleton_trap",
]

# 2x2 — small buildings, medium traps, some defenses
TILES_2x2 = [
    "builder_hut",
    "giant_bomb",
    "giga_bomb",
    "hidden_tesla",
    "air_sweeper",
    "inferno_tower",
    "inferno_tower_single",
    "spell_tower",
    "hero_banners",
]

# 3x3 — most defenses, resource buildings, army buildings
TILES_3x3 = [
    # Defenses
    "cannon",
    "archer_tower",
    "mortar",
    "wizard_tower",
    "air_defense",
    "bomb_tower",
    "x_bow",
    "scattershot",
    "monolith",
    "firespitter",
    "multi_archer_tower",
    "ricochet_cannon",
    "revenge_tower",
    # Geared variants
    "archer_tower_geared",
    "cannon_geared",
    "mortar_geared",
    # Special defenses
    "super_wizard_tower",
    "multi_gear_tower",
    "multi_gear_tower_longrange",
    # Resources
    "gold_mine",
    "elixir_collector",
    "dark_elixir_drill",
    "dark_elixir_storage",
    "gold_storage",
    "elixir_storage",
    # Army
    "clan_castle",
    "army_camp",
    "barracks",
    "dark_barracks",
    "laboratory",
    "spell_factory",
    "dark_spell_factory",
    "pet_house",
    "blacksmith",
    # Heroes
    "hero_altars",
]

# 4x4 — large unique buildings
TILES_4x4 = [
    "town_hall",
    "eagle_artillery",
    "hero_hall",
    "workshop",
]

# Combined lookup dict
BUILDING_TILES: dict[str, int] = {}
for name in TILES_1x1:
    BUILDING_TILES[name] = 1
for name in TILES_2x2:
    BUILDING_TILES[name] = 2
for name in TILES_3x3:
    BUILDING_TILES[name] = 3
for name in TILES_4x4:
    BUILDING_TILES[name] = 4


# ── TH15 building counts ───────────────────────────────────────────
# (min, max) of each building type to place in a generated base.

TH15_COMPOSITION: dict[str, tuple[int, int]] = {
    # 4x4
    "town_hall": (1, 1),
    "eagle_artillery": (1, 1),
    "workshop": (0, 1),
    "hero_hall": (0, 1),
    # 3x3 defenses
    "cannon": (4, 7),
    "archer_tower": (5, 8),
    "mortar": (2, 4),
    "wizard_tower": (3, 5),
    "air_defense": (3, 4),
    "bomb_tower": (1, 3),
    "x_bow": (2, 4),
    "scattershot": (1, 2),
    "monolith": (0, 1),
    # 2x2 defenses
    "hidden_tesla": (3, 5),
    "inferno_tower": (2, 3),
    "air_sweeper": (1, 2),
    "spell_tower": (0, 2),
    # 3x3 resources
    "gold_mine": (4, 7),
    "elixir_collector": (4, 7),
    "dark_elixir_drill": (1, 3),
    "gold_storage": (2, 4),
    "elixir_storage": (2, 4),
    "dark_elixir_storage": (1, 1),
    # 3x3 army
    "clan_castle": (1, 1),
    "army_camp": (3, 4),
    "barracks": (1, 1),
    "dark_barracks": (0, 1),
    "laboratory": (1, 1),
    "spell_factory": (1, 1),
    "dark_spell_factory": (0, 1),
    "pet_house": (0, 1),
    "blacksmith": (0, 1),
    # 2x2
    "builder_hut": (2, 5),
    # Traps
    "giant_bomb": (2, 5),
    "bomb_trap": (3, 6),
    "spring_trap": (3, 6),
    "air_bomb_trap": (2, 5),
    "seeking_air_mine": (2, 5),
    "skeleton_trap": (2, 4),
    "tornado_trap": (0, 2),
}
