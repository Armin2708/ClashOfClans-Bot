"""
Clash of Clans YOLO class registry.

Defines every detectable entity — buildings at each level, troops, spells —
and auto-generates the full ALL_CLASSES list used by the training pipeline.

Class naming convention:
  {entity}_{level}   e.g. cannon_1, cannon_21, barbarian_1, lightning_spell_1
  {entity}           level-agnostic fallback (used when level is unknown)

Adding a new building / troop / spell:
  1. Add an entry to BUILDINGS, TROOPS, or SPELLS below.
  2. Run:  python training/class_registry.py --list
  3. Retrain the model once you have labeled data for the new class.

Never remove or reorder entries — that changes class IDs and breaks saved models.
Only append.
"""

from __future__ import annotations


# ── Home Village buildings ─────────────────────────────────────────────────────
# Format: "canonical_name": max_level
# Use the lowest canonical snake_case name that is unambiguous.

BUILDINGS: dict[str, int] = {
    # ── Defenses ──────────────────────────────────────────────────────────────
    "cannon":               21,
    "archer_tower":         21,
    "mortar":               14,
    "air_defense":          12,
    "wizard_tower":         16,
    "air_sweeper":           7,
    "x_bow":                11,
    "inferno_tower":        10,
    "eagle_artillery":       6,
    "scattershot":           6,
    "bomb_tower":           11,
    "hidden_tesla":         14,
    "giga_tesla":            5,   # TH12-13 (on Town Hall)
    "giga_inferno":          5,   # TH14     (on Town Hall)
    "monolith":              4,   # TH15+
    "ricochet_cannon":       4,   # TH16+
    "multi_archer_tower":    4,   # TH16+
    "spell_tower":           4,   # TH15+
    # ── Traps ─────────────────────────────────────────────────────────────────
    "bomb_trap":            10,
    "spring_trap":           6,
    "air_bomb_trap":         9,
    "giant_bomb":            8,
    "seeking_air_mine":      5,
    "skeleton_trap":         5,
    "tornado_trap":          5,
    # ── Resources ─────────────────────────────────────────────────────────────
    "gold_mine":            15,
    "elixir_collector":     15,
    "dark_elixir_drill":     9,
    "gold_storage":         16,
    "elixir_storage":       16,
    "dark_elixir_storage":   9,
    # ── Army buildings ────────────────────────────────────────────────────────
    "barracks":             16,
    "dark_barracks":         9,
    "army_camp":            11,
    "spell_factory":         7,
    "dark_spell_factory":    5,
    "laboratory":           15,
    "workshop":              5,
    "pet_house":             4,
    "blacksmith":            4,
    "hero_hall":             4,
    # ── Special structures ────────────────────────────────────────────────────
    "town_hall":            17,
    "clan_castle":          11,
    "builder_hut":           5,
}

# ── Heroes (levels go very high — track by milestone groups or exact level) ────
# We use 5-level buckets for heroes to keep class count manageable.
# e.g. barbarian_king_1_5, barbarian_king_6_10, ...
HERO_LEVEL_BUCKET = 5
HEROES: dict[str, int] = {
    "barbarian_king":  95,
    "archer_queen":    95,
    "grand_warden":    65,
    "royal_champion":  45,
    "minion_prince":   40,
}

# ── Troops (Home Village) ──────────────────────────────────────────────────────
TROOPS: dict[str, int] = {
    # Regular
    "barbarian":        12,
    "archer":           12,
    "giant":            12,
    "goblin":           12,
    "wall_breaker":     12,
    "balloon":          12,
    "wizard":           12,
    "healer":            7,
    "dragon":           10,
    "pekka":             9,
    "baby_dragon":       9,
    "miner":             9,
    "electro_dragon":    7,
    "yeti":              5,
    "dragon_rider":      5,
    "electro_titan":     5,
    "root_rider":        5,
    "thrower":           5,
    # Dark elixir
    "minion":           12,
    "hog_rider":        12,
    "valkyrie":          9,
    "golem":             9,
    "witch":             6,
    "lava_hound":        7,
    "bowler":            6,
    "ice_golem":         5,
    "headhunter":        5,
    "apprentice_warden": 5,
    "druid":             5,
}

# ── Spells ─────────────────────────────────────────────────────────────────────
SPELLS: dict[str, int] = {
    # Regular
    "lightning_spell":     9,
    "healing_spell":       9,
    "rage_spell":          6,
    "freeze_spell":        7,
    "earthquake_spell":    5,
    "haste_spell":         5,
    "clone_spell":         6,
    "invisibility_spell":  5,
    "bat_spell":           5,
    "skeleton_spell":      6,
    "overgrowth_spell":    4,
    # Dark
    "poison_spell":        9,
    "dark_earthquake_spell": 5,
    "goblin_spell":        4,
}

# ── UI elements (no levels — these are interface buttons/HUD) ──────────────────
UI_CLASSES: list[str] = [
    # Navigation buttons
    "btn_attack",
    "btn_find_match",
    "btn_start_battle",
    "btn_next_base",
    "btn_return_home",
    "btn_end_battle",
    "btn_confirm",
    "btn_close",
    "btn_okay",
    "btn_later",
    # HUD overlays
    "hud_village",
    "hud_scouting",
    "hud_results",
    "hud_army",
    # Loot display
    "loot_gold",
    "loot_elixir",
    "loot_gem",
    "loot_dark_elixir",
    # Troop/spell deployment bar
    "troop_slot",
    "spell_slot",
    "hero_slot",
]

# ── Legacy aliases ─────────────────────────────────────────────────────────────
# Class names used in the public HuggingFace dataset (already in trained model).
# These point to the same building but use the original dataset naming.
# DO NOT REMOVE — removing changes class IDs and breaks models.
LEGACY_ALIASES: list[str] = [
    "ad",        # → air_defense
    "airsweeper",# → air_sweeper
    "bombtower", # → bomb_tower
    "canon",     # → cannon
    "clancastle",# → clan_castle
    "eagle",     # → eagle_artillery
    "inferno",   # → inferno_tower
    "kingpad",   # → barbarian_king
    "mortar",    # same
    "queenpad",  # → archer_queen
    "rcpad",     # → royal_champion
    "scattershot",# same
    "th13",      # → town_hall level 13
    "wardenpad", # → grand_warden
    "wizztower", # → wizard_tower
    "xbow",      # → x_bow
]


def _generate_building_classes() -> list[str]:
    """Generate {building}_{level} for every building at every level."""
    classes = []
    for name, max_lvl in BUILDINGS.items():
        for lvl in range(1, max_lvl + 1):
            classes.append(f"{name}_{lvl}")
    return classes


def _generate_hero_classes() -> list[str]:
    """Generate hero level-bucket classes: {hero}_{start}_{end}."""
    classes = []
    for name, max_lvl in HEROES.items():
        lvl = 1
        while lvl <= max_lvl:
            end = min(lvl + HERO_LEVEL_BUCKET - 1, max_lvl)
            classes.append(f"{name}_{lvl}_{end}")
            lvl += HERO_LEVEL_BUCKET
    return classes


def _generate_troop_classes() -> list[str]:
    """Generate {troop}_{level} for every troop at every level."""
    classes = []
    for name, max_lvl in TROOPS.items():
        for lvl in range(1, max_lvl + 1):
            classes.append(f"{name}_{lvl}")
    return classes


def _generate_spell_classes() -> list[str]:
    """Generate {spell}_{level} for every spell at every level."""
    classes = []
    for name, max_lvl in SPELLS.items():
        for lvl in range(1, max_lvl + 1):
            classes.append(f"{name}_{lvl}")
    return classes


# ── Build the full class list ──────────────────────────────────────────────────
# Order matters — class ID = index. Never reorder, only append.
ALL_CLASSES: list[str] = (
    LEGACY_ALIASES                  # IDs  0-15  (backward compat with trained model)
    + _generate_building_classes()  # IDs 16-...
    + _generate_hero_classes()
    + _generate_troop_classes()
    + _generate_spell_classes()
    + UI_CLASSES
)

# Quick lookup: name → ID
CLASS_INDEX: dict[str, int] = {name: i for i, name in enumerate(ALL_CLASSES)}

# ── Stats ──────────────────────────────────────────────────────────────────────
STATS = {
    "legacy_aliases":   len(LEGACY_ALIASES),
    "building_classes": len(_generate_building_classes()),
    "hero_classes":     len(_generate_hero_classes()),
    "troop_classes":    len(_generate_troop_classes()),
    "spell_classes":    len(_generate_spell_classes()),
    "ui_classes":       len(UI_CLASSES),
    "total":            len(ALL_CLASSES),
}


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Show CoC class registry stats")
    p.add_argument("--list", action="store_true", help="Print all class names with IDs")
    p.add_argument("--category", choices=["buildings", "heroes", "troops", "spells", "ui"],
                   help="Filter by category")
    args = p.parse_args()

    print("CoC Class Registry")
    print("=" * 50)
    for k, v in STATS.items():
        print(f"  {k:22s}: {v}")
    print()

    if args.list:
        groups = {
            "buildings": _generate_building_classes(),
            "heroes":    _generate_hero_classes(),
            "troops":    _generate_troop_classes(),
            "spells":    _generate_spell_classes(),
            "ui":        UI_CLASSES,
        }
        cats = [args.category] if args.category else list(groups.keys())
        for cat in cats:
            print(f"\n── {cat.upper()} ──")
            for name in groups[cat]:
                print(f"  [{CLASS_INDEX[name]:4d}] {name}")
