"""
Clash of Clans — Complete YOLO Detection Class Registry
TH18 era (early 2026) — every detectable entity in the game.

STRUCTURE:
  - Home Village: defenses, traps, resources, army, special, walls
  - Heroes: all 5 heroes with level buckets
  - Troops: elixir, dark elixir, super troops, siege machines
  - Spells: elixir spells, dark spells
  - Pets: all hero pets
  - Hero Equipment: all equipment items
  - Builder Base: buildings, troops, heroes
  - Clan Capital: buildings, troops, spells
  - UI: buttons, HUD, loot, slots

CLASS NAMING CONVENTION:
  {entity}_{level}           e.g.  cannon_7,  barbarian_3,  lightning_spell_5
  {hero}_{start}_{end}       e.g.  barbarian_king_1_5,  archer_queen_96_100
  {entity}                   level-agnostic (UI elements, super troops, capital troops)

ADDING NEW CONTENT:
  1. Add entry to the relevant dict below (name: max_level or name: None for no-level)
  2. Run: python training/class_registry.py --list --category <category>
  3. Label new training data using the exact generated class names
  4. Never remove or reorder existing entries — only append (breaks model IDs)

DATA COLLECTION ROADMAP:
  Phase 1  Home Village buildings (core bot — attack/farming)
  Phase 2  Troops + spells in deployment bar (attack AI)
  Phase 3  Builder Base buildings (BB mode)
  Phase 4  Clan Capital buildings (capital raids)
  Phase 5  Hero equipment UI, pets, advanced screens
"""

from __future__ import annotations

# ══════════════════════════════════════════════════════════════════════════════
#  HOME VILLAGE — DEFENSES
# ══════════════════════════════════════════════════════════════════════════════

HV_DEFENSES: dict[str, int] = {
    "cannon":               21,
    "archer_tower":         21,
    "mortar":               18,
    "air_defense":          16,
    "wizard_tower":         17,
    "air_sweeper":           7,
    "x_bow":                12,
    "inferno_tower":        12,
    "eagle_artillery":       7,   # legacy — merged into inferno_artillery in TH17+
    "inferno_artillery":     2,   # TH17+ (replaced eagle artillery)
    "scattershot":           6,
    "bomb_tower":           13,
    "hidden_tesla":         17,
    "giga_tesla":            5,   # TH12-13 modification on Town Hall
    "giga_inferno":          5,   # TH14    modification on Town Hall
    "monolith":              4,   # TH15+
    "ricochet_cannon":       4,   # TH16+
    "multi_archer_tower":    4,   # TH16+ (merged from geared-up Archer Tower)
    "spell_tower":           4,   # TH15+
    "firespitter":           3,   # TH17+
    "multi_gear_tower":      3,   # TH16+
    "super_wizard_tower":    2,   # TH18 (speculative — wiki confirms existence)
}

# ══════════════════════════════════════════════════════════════════════════════
#  HOME VILLAGE — TRAPS
# ══════════════════════════════════════════════════════════════════════════════

HV_TRAPS: dict[str, int] = {
    "bomb_trap":            13,
    "spring_trap":          12,
    "air_bomb_trap":        12,
    "giant_bomb":           11,
    "seeking_air_mine":      7,
    "skeleton_trap":         4,
    "tornado_trap":          3,
    "giga_bomb":             3,   # TH17+
}

# ══════════════════════════════════════════════════════════════════════════════
#  HOME VILLAGE — RESOURCES
# ══════════════════════════════════════════════════════════════════════════════

HV_RESOURCES: dict[str, int] = {
    "gold_mine":            17,
    "elixir_collector":     17,
    "dark_elixir_drill":    11,
    "gold_storage":         19,
    "elixir_storage":       19,
    "dark_elixir_storage":  13,
}

# ══════════════════════════════════════════════════════════════════════════════
#  HOME VILLAGE — ARMY BUILDINGS
# ══════════════════════════════════════════════════════════════════════════════

HV_ARMY: dict[str, int] = {
    "barracks":             19,
    "dark_barracks":        12,
    "army_camp":            13,
    "spell_factory":         9,
    "dark_spell_factory":    7,
    "laboratory":           16,
    "workshop":              8,
    "pet_house":            12,
    "blacksmith":            9,
    "hero_hall":            12,
}

# ══════════════════════════════════════════════════════════════════════════════
#  HOME VILLAGE — SPECIAL / OTHER
# ══════════════════════════════════════════════════════════════════════════════

HV_SPECIAL: dict[str, int] = {
    "town_hall":            18,
    "clan_castle":          14,
    "builder_hut":           7,
    "chiefs_helper_hut":     1,
    "wall":                 19,   # Wall segments (level = visual tier)
}

# ══════════════════════════════════════════════════════════════════════════════
#  HEROES — level buckets (HERO_BUCKET_SIZE levels per class)
# ══════════════════════════════════════════════════════════════════════════════

HERO_BUCKET_SIZE = 5

HEROES: dict[str, int] = {
    "barbarian_king":   100,
    "archer_queen":     100,
    "grand_warden":      75,
    "royal_champion":    50,
    "minion_prince":     70,
}

# ══════════════════════════════════════════════════════════════════════════════
#  HOME VILLAGE TROOPS — ELIXIR
# ══════════════════════════════════════════════════════════════════════════════

HV_TROOPS_ELIXIR: dict[str, int] = {
    "barbarian":        13,
    "archer":           13,
    "giant":            13,
    "goblin":           13,
    "wall_breaker":     13,
    "balloon":          13,
    "wizard":           13,
    "healer":           13,
    "dragon":           12,
    "pekka":            13,
    "baby_dragon":      13,
    "miner":            13,
    "electro_dragon":    8,
    "yeti":             13,
    "dragon_rider":      5,
    "electro_titan":     5,
    "root_rider":        5,
    "thrower":           3,
}

# ══════════════════════════════════════════════════════════════════════════════
#  HOME VILLAGE TROOPS — DARK ELIXIR
# ══════════════════════════════════════════════════════════════════════════════

HV_TROOPS_DARK: dict[str, int] = {
    "minion":           13,
    "hog_rider":        13,
    "valkyrie":         13,
    "golem":            13,
    "witch":            13,
    "lava_hound":       13,
    "bowler":           13,
    "ice_golem":        13,
    "headhunter":       13,
    "apprentice_warden": 5,
    "druid":             5,
}

# ══════════════════════════════════════════════════════════════════════════════
#  SUPER TROOPS (Home Village — no levels, just boosted visual state)
# ══════════════════════════════════════════════════════════════════════════════

SUPER_TROOPS: list[str] = [
    "super_barbarian",
    "super_archer",
    "sneaky_goblin",
    "super_wall_breaker",
    "super_giant",
    "super_wizard",
    "super_bowler",
    "super_witch",
    "super_hog_rider",
    "super_valkyrie",
    "rocket_balloon",
    "inferno_dragon",
    "super_lava_hound",
    "super_miner",
    "super_dragon",
    "ice_hound",
]

# ══════════════════════════════════════════════════════════════════════════════
#  SIEGE MACHINES
# ══════════════════════════════════════════════════════════════════════════════

SIEGE_MACHINES: dict[str, int] = {
    "wall_wrecker":     5,
    "battle_blimp":     5,
    "stone_slammer":    5,
    "siege_barracks":   5,
    "log_launcher":     5,
    "flame_flinger":    5,
    "battle_drill":     5,
    "troop_launcher":   5,
}

# ══════════════════════════════════════════════════════════════════════════════
#  SPELLS — ELIXIR
# ══════════════════════════════════════════════════════════════════════════════

SPELLS_ELIXIR: dict[str, int] = {
    "lightning_spell":      12,
    "healing_spell":        11,
    "rage_spell":           11,
    "freeze_spell":         11,
    "jump_spell":            6,
    "clone_spell":           5,
    "invisibility_spell":   11,
    "recall_spell":          6,
    "bat_spell":             5,
    "skeleton_spell":        6,
    "overgrowth_spell":      4,
}

# ══════════════════════════════════════════════════════════════════════════════
#  SPELLS — DARK
# ══════════════════════════════════════════════════════════════════════════════

SPELLS_DARK: dict[str, int] = {
    "poison_spell":         12,
    "earthquake_spell":      5,
    "haste_spell":           5,
    "revive_spell":          4,
}

# ══════════════════════════════════════════════════════════════════════════════
#  PETS
# ══════════════════════════════════════════════════════════════════════════════

PETS: dict[str, int] = {
    "lassi":            10,
    "electro_owl":      10,
    "mighty_yak":       10,
    "unicorn":          10,
    "frosty":           10,
    "diggy":            10,
    "poison_lizard":    10,
    "phoenix":          10,
    "spirit_fox":       10,
    "angry_jelly":      10,
    "sneezy":           10,
    "greedy_raven":     10,
}

# ══════════════════════════════════════════════════════════════════════════════
#  HERO EQUIPMENT
#  Common equipment max level: 18 | Epic equipment max level: 27
# ══════════════════════════════════════════════════════════════════════════════

HERO_EQUIPMENT: dict[str, int] = {
    # Barbarian King
    "spiky_ball":           18,
    "barbarian_puppet":     18,
    "rage_vial":            18,
    "earthquake_boots":     18,
    "vampstache":           18,
    "giant_gauntlet":       27,
    "snake_bracelet":       27,
    "fireball":             27,
    # Archer Queen
    "archer_puppet":        18,
    "invisibility_vial":    18,
    "giant_arrow":          18,
    "healer_puppet":        18,
    "frozen_arrow":         27,
    "magic_mirror":         27,
    "electrobow":           27,
    # Grand Warden
    "eternal_tome":         18,
    "life_gem":             18,
    "rage_gem":             18,
    "healing_tome":         18,
    "lavaloon_puppet":      27,
    "powerful_potion":      27,
    # Royal Champion
    "royal_gem":            18,
    "seeking_shield":       18,
    "hog_rider_puppet":     18,
    "haste_vial":           18,
    "rocket_spear":         27,
    "dark_orb":             27,
    # Minion Prince
    "dark_crown":           18,
    "action_figure":        18,
    "electro_boots":        18,
    "henchmen_puppet":      18,
    "metal_pants":          27,
    "inferno_cape":         27,
}

# ══════════════════════════════════════════════════════════════════════════════
#  BUILDER BASE — BUILDINGS
# ══════════════════════════════════════════════════════════════════════════════

BB_BUILDINGS: dict[str, int] = {
    # Special
    "bb_builder_hall":      10,
    "bb_clock_tower":        8,
    "bb_gem_mine":           9,
    "bb_bob_control":        5,
    # Defenses
    "bb_double_cannon":     18,
    "bb_archer_tower":      18,
    "bb_cannon":            18,
    "bb_crusher":           18,
    "bb_guard_post":        18,
    "bb_air_bombs":         18,
    "bb_roaster":           18,
    "bb_multi_mortar":      18,
    "bb_mega_tesla":        18,
    "bb_lava_launcher":     18,
    "bb_x_bow":              5,
    "bb_giant_cannon":       5,
    # Traps
    "bb_spring_trap":        4,
    # Resources
    "bb_gold_mine":         14,
    "bb_elixir_collector":  14,
    "bb_gold_storage":      14,
    "bb_elixir_storage":    14,
    # Army
    "bb_builder_barracks":  12,
    "bb_star_laboratory":   12,
    "bb_army_camp":          1,
}

# ══════════════════════════════════════════════════════════════════════════════
#  BUILDER BASE — HEROES
# ══════════════════════════════════════════════════════════════════════════════

BB_HEROES: dict[str, int] = {
    "battle_machine":   35,
    "battle_copter":    35,
}

# ══════════════════════════════════════════════════════════════════════════════
#  BUILDER BASE — TROOPS
# ══════════════════════════════════════════════════════════════════════════════

BB_TROOPS: dict[str, int] = {
    "bb_raged_barbarian":   12,
    "bb_sneaky_archer":     12,
    "bb_boxer_giant":       12,
    "bb_bomber":            12,
    "bb_cannon_cart":       12,
    "bb_night_witch":       12,
    "bb_drop_ship":         12,
    "bb_super_pekka":       12,
    "bb_hog_glider":        12,
    "bb_electrofire_wizard":12,
    "bb_power_pekka":       12,
    "bb_minion":            12,
}

# ══════════════════════════════════════════════════════════════════════════════
#  CLAN CAPITAL — BUILDINGS
# ══════════════════════════════════════════════════════════════════════════════

CC_BUILDINGS: dict[str, int] = {
    # Core
    "cc_capital_hall":       10,
    "cc_clan_castle":         6,
    # Defenses
    "cc_cannon":             10,
    "cc_archer_tower":       10,
    "cc_air_defense":        10,
    "cc_wizard_tower":       10,
    "cc_mortar":             10,
    "cc_inferno_tower":      10,
    "cc_super_giant_post":    8,
    "cc_multi_mortar":        8,
    "cc_x_bow":               8,
    "cc_bomb_tower":          8,
    "cc_lava_launcher":       8,
    "cc_super_wizard_tower":  8,
    "cc_mega_tesla":          8,
    # Resources
    "cc_capital_gold_storage": 8,
    "cc_capital_mine":         8,
    # Traps
    "cc_giant_bomb":           8,
    "cc_air_bomb":             8,
    "cc_spring_trap":          6,
}

# ══════════════════════════════════════════════════════════════════════════════
#  CLAN CAPITAL — TROOPS (no per-level classes — all fixed visual)
# ══════════════════════════════════════════════════════════════════════════════

CC_TROOPS: list[str] = [
    "cc_super_barbarian",
    "cc_minion_horde",
    "cc_rocket_balloon",
    "cc_skeleton_barrel",
    "cc_super_miner",
    "cc_mega_sparky",
    "cc_dragon",
    "cc_pekka",
    "cc_golem",
    "cc_baby_dragon",
    "cc_hog_rider",
    "cc_lava_hound",
    "cc_electro_dragon",
    "cc_yeti",
    "cc_inferno_dragon",
]

# ══════════════════════════════════════════════════════════════════════════════
#  UI ELEMENTS (buttons, HUD, loot — no levels)
# ══════════════════════════════════════════════════════════════════════════════

UI_CLASSES: list[str] = [
    # Navigation / action buttons
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
    "btn_upgrade",
    "btn_boost",
    "btn_collect",
    "btn_visit_builder_base",
    "btn_go_home",
    # HUD / screen state overlays
    "hud_village",
    "hud_scouting",
    "hud_results",
    "hud_army",
    "hud_builder_base",
    "hud_clan_capital",
    # Loot / resource indicators
    "loot_gold",
    "loot_elixir",
    "loot_dark_elixir",
    "loot_gem",
    "loot_capital_gold",
    # Deployment bar slots
    "troop_slot",
    "spell_slot",
    "hero_slot",
    "siege_slot",
    # Misc UI elements
    "shield_icon",
    "trophy_icon",
    "star_1",
    "star_2",
    "star_3",
]

# ══════════════════════════════════════════════════════════════════════════════
#  LEGACY ALIASES (public HuggingFace dataset — keep for backward compatibility)
#  These 16 classes are already in the trained model. Never remove them.
# ══════════════════════════════════════════════════════════════════════════════

LEGACY_ALIASES: list[str] = [
    "ad",           # → air_defense
    "airsweeper",   # → air_sweeper
    "bombtower",    # → bomb_tower
    "canon",        # → cannon
    "clancastle",   # → clan_castle
    "eagle",        # → eagle_artillery
    "inferno",      # → inferno_tower
    "kingpad",      # → barbarian_king altar
    "mortar",       # same
    "queenpad",     # → archer_queen altar
    "rcpad",        # → royal_champion altar
    "scattershot",  # same
    "th13",         # → town_hall (level 13 variant)
    "wardenpad",    # → grand_warden altar
    "wizztower",    # → wizard_tower
    "xbow",         # → x_bow
]


# ══════════════════════════════════════════════════════════════════════════════
#  CLASS GENERATION
# ══════════════════════════════════════════════════════════════════════════════

def _leveled(d: dict[str, int]) -> list[str]:
    return [f"{name}_{lvl}" for name, max_lvl in d.items()
            for lvl in range(1, max_lvl + 1)]


def _bucketed(d: dict[str, int], bucket: int = HERO_BUCKET_SIZE) -> list[str]:
    classes = []
    for name, max_lvl in d.items():
        lvl = 1
        while lvl <= max_lvl:
            end = min(lvl + bucket - 1, max_lvl)
            classes.append(f"{name}_{lvl}_{end}")
            lvl += bucket
    return classes


def _equipment_leveled(d: dict[str, int]) -> list[str]:
    return [f"{name}_{lvl}" for name, max_lvl in d.items()
            for lvl in range(1, max_lvl + 1)]


# ── Full class list (class ID = index — never reorder, only append) ────────────
ALL_CLASSES: list[str] = (
    LEGACY_ALIASES                          # IDs   0-15   (backward compat)
    + _leveled(HV_DEFENSES)                 # Home Village defenses
    + _leveled(HV_TRAPS)                    # Home Village traps
    + _leveled(HV_RESOURCES)               # Home Village resources
    + _leveled(HV_ARMY)                    # Home Village army buildings
    + _leveled(HV_SPECIAL)                 # Town Hall, Clan Castle, walls
    + _bucketed(HEROES)                    # Heroes (level buckets)
    + _leveled(HV_TROOPS_ELIXIR)           # Elixir troops
    + _leveled(HV_TROOPS_DARK)             # Dark elixir troops
    + SUPER_TROOPS                         # Super troops (no levels)
    + _leveled(SIEGE_MACHINES)             # Siege machines
    + _leveled(SPELLS_ELIXIR)              # Elixir spells
    + _leveled(SPELLS_DARK)                # Dark spells
    + _leveled(PETS)                       # Pets
    + _equipment_leveled(HERO_EQUIPMENT)   # Hero equipment
    + _leveled(BB_BUILDINGS)               # Builder Base buildings
    + _bucketed(BB_HEROES)                 # Builder Base heroes
    + _leveled(BB_TROOPS)                  # Builder Base troops
    + _leveled(CC_BUILDINGS)               # Clan Capital buildings
    + CC_TROOPS                            # Clan Capital troops (no levels)
    + UI_CLASSES                           # UI buttons, HUD, slots
)

CLASS_INDEX: dict[str, int] = {name: i for i, name in enumerate(ALL_CLASSES)}

# ── Stats ───────────────────────────────────────────────────────────────────────
CATEGORY_STATS: dict[str, int] = {
    "legacy_aliases":       len(LEGACY_ALIASES),
    "hv_defenses":          len(_leveled(HV_DEFENSES)),
    "hv_traps":             len(_leveled(HV_TRAPS)),
    "hv_resources":         len(_leveled(HV_RESOURCES)),
    "hv_army_buildings":    len(_leveled(HV_ARMY)),
    "hv_special":           len(_leveled(HV_SPECIAL)),
    "heroes":               len(_bucketed(HEROES)),
    "hv_elixir_troops":     len(_leveled(HV_TROOPS_ELIXIR)),
    "hv_dark_troops":       len(_leveled(HV_TROOPS_DARK)),
    "super_troops":         len(SUPER_TROOPS),
    "siege_machines":       len(_leveled(SIEGE_MACHINES)),
    "elixir_spells":        len(_leveled(SPELLS_ELIXIR)),
    "dark_spells":          len(_leveled(SPELLS_DARK)),
    "pets":                 len(_leveled(PETS)),
    "hero_equipment":       len(_equipment_leveled(HERO_EQUIPMENT)),
    "bb_buildings":         len(_leveled(BB_BUILDINGS)),
    "bb_heroes":            len(_bucketed(BB_HEROES)),
    "bb_troops":            len(_leveled(BB_TROOPS)),
    "cc_buildings":         len(_leveled(CC_BUILDINGS)),
    "cc_troops":            len(CC_TROOPS),
    "ui_elements":          len(UI_CLASSES),
    "TOTAL":                len(ALL_CLASSES),
}


# ══════════════════════════════════════════════════════════════════════════════
#  CLI
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="CoC class registry stats and listing")
    p.add_argument("--list", action="store_true", help="Print all class names with IDs")
    p.add_argument("--category", help="Filter: hv_defenses, heroes, troops, spells, pets, "
                                      "equipment, builder_base, clan_capital, ui")
    p.add_argument("--search", help="Search for a class name (substring match)")
    args = p.parse_args()

    print("Clash of Clans — Complete YOLO Class Registry")
    print("=" * 55)
    for k, v in CATEGORY_STATS.items():
        pad = "─" * 2 if k == "TOTAL" else " "
        print(f"  {pad} {k:30s}: {v:5d}")

    if args.search:
        print(f"\nSearch results for '{args.search}':")
        for name, idx in CLASS_INDEX.items():
            if args.search.lower() in name.lower():
                print(f"  [{idx:5d}] {name}")

    elif args.list:
        cat_map = {
            "hv_defenses":   _leveled(HV_DEFENSES),
            "hv_traps":      _leveled(HV_TRAPS),
            "hv_resources":  _leveled(HV_RESOURCES),
            "hv_army":       _leveled(HV_ARMY),
            "hv_special":    _leveled(HV_SPECIAL),
            "heroes":        _bucketed(HEROES),
            "troops":        _leveled(HV_TROOPS_ELIXIR) + _leveled(HV_TROOPS_DARK),
            "super_troops":  SUPER_TROOPS,
            "siege":         _leveled(SIEGE_MACHINES),
            "spells":        _leveled(SPELLS_ELIXIR) + _leveled(SPELLS_DARK),
            "pets":          _leveled(PETS),
            "equipment":     _equipment_leveled(HERO_EQUIPMENT),
            "builder_base":  _leveled(BB_BUILDINGS) + _bucketed(BB_HEROES) + _leveled(BB_TROOPS),
            "clan_capital":  _leveled(CC_BUILDINGS) + CC_TROOPS,
            "ui":            UI_CLASSES,
        }
        cats = [args.category] if args.category and args.category in cat_map else list(cat_map)
        for cat in cats:
            print(f"\n── {cat.upper().replace('_', ' ')} ──")
            for name in cat_map[cat]:
                print(f"  [{CLASS_INDEX[name]:5d}] {name}")
