#!/usr/bin/env python3
"""
Scrape Clash of Clans building/troop/hero/spell images from the Fandom wiki.

Uses the MediaWiki API to list images on each building page, filters to
level-specific sprites, and downloads them into organized folders.

Output structure:
    data/sprites/
        cannon/
            cannon_1.png
            cannon_2.png
            ...
        archer_tower/
            archer_tower_1.png
            ...

Usage:
    python training/scrape_wiki.py
    python training/scrape_wiki.py --category defenses
    python training/scrape_wiki.py --category all --output data/sprites
    python training/scrape_wiki.py --dry-run          # show what would be downloaded
"""

from __future__ import annotations

import argparse
import re
import time
from pathlib import Path

import requests

API = "https://clashofclans.fandom.com/api.php"
HEADERS = {
    "User-Agent": "ClashOfClansBot/1.0 (training data collection; "
                  "github.com/Armin2708/ClashOfClans-Bot)"
}
REQUEST_DELAY = 1.0  # seconds between API requests (be nice to the wiki)
MAX_RETRIES = 3


# ── Building registry ────────────────────────────────────────────────
# Maps our internal name → (wiki_page, wiki_image_prefix, max_level)
#
# wiki_image_prefix: the prefix used in image filenames on the wiki,
#   e.g. "Cannon" for Cannon1.png, "Archer_Tower" for Archer_Tower1.png

BUILDINGS: dict[str, dict] = {
    # ── Defenses ──
    "cannon":              {"page": "Cannon/Home_Village",          "prefix": "Cannon",              "max": 21},
    "archer_tower":        {"page": "Archer_Tower/Home_Village",    "prefix": "Archer_Tower",        "max": 21},
    "mortar":              {"page": "Mortar",                       "prefix": "Mortar",              "max": 18},
    "air_defense":         {"page": "Air_Defense/Home_Village",     "prefix": "Air_Defense",         "max": 16},
    "wizard_tower":        {"page": "Wizard_Tower",                 "prefix": "Wizard_Tower",        "max": 17},
    "air_sweeper":         {"page": "Air_Sweeper",                  "prefix": "Air_Sweeper",         "max": 7},
    "x_bow":               {"page": "X-Bow/Home_Village",           "prefix": "X-Bow",              "max": 12, "suffix": "_Ground"},
    "inferno_tower":       {"page": "Inferno_Tower/Home_Village",   "prefix": "Inferno_Tower",       "max": 12, "suffix": "_Multi"},
    "eagle_artillery":     {"page": "Eagle_Artillery",              "prefix": "Eagle_Artillery",     "max": 7},
    "scattershot":         {"page": "Scattershot",                  "prefix": "Scattershot",         "max": 6},
    "bomb_tower":          {"page": "Bomb_Tower/Home_Village",      "prefix": "Bomb_Tower",          "max": 13},
    "hidden_tesla":        {"page": "Hidden_Tesla/Home_Village",    "prefix": "Hidden_Tesla",        "max": 17},
    "monolith":            {"page": "Monolith",                     "prefix": "Monolith",            "max": 4},
    "ricochet_cannon":     {"page": "Ricochet_Cannon",              "prefix": "Ricochet_Cannon",     "max": 4},
    "multi_archer_tower":  {"page": "Multi-Archer_Tower",           "prefix": "Multi-Archer_Tower",  "max": 4},
    "spell_tower":         {"page": "Spell_Tower",                  "prefix": "Spell_Tower",         "max": 4, "suffix": "_Rage"},
    "firespitter":         {"page": "Firespitter",                  "prefix": "Firespitter",         "max": 3},
    "multi_gear_tower":    {"page": "Multi-Gear_Tower",             "prefix": "Multi-Gear_Tower",    "max": 3, "suffix": "_FastAttack"},
    # ── Traps ──
    "bomb_trap":           {"page": "Bomb",                         "prefix": "Bomb",                "max": 13},
    "spring_trap":         {"page": "Spring_Trap/Home_Village",     "prefix": "Spring_Trap",         "max": 12},
    "air_bomb_trap":       {"page": "Air_Bomb",                     "prefix": "Air_Bomb",            "max": 12},
    "giant_bomb":          {"page": "Giant_Bomb",                   "prefix": "Giant_Bomb",          "max": 11},
    "seeking_air_mine":    {"page": "Seeking_Air_Mine",             "prefix": "Seeking_Air_Mine",    "max": 7},
    "skeleton_trap":       {"page": "Skeleton_Trap",                "prefix": "Skeleton_Trap",       "max": 4},
    "tornado_trap":        {"page": "Tornado_Trap",                 "prefix": "Tornado_Trap",        "max": 3},
    # ── Resources ──
    "gold_mine":           {"page": "Gold_Mine/Home_Village",       "prefix": "Gold_Mine",           "max": 17},
    "elixir_collector":    {"page": "Elixir_Collector/Home_Village","prefix": "Elixir_Collector",    "max": 17},
    "dark_elixir_drill":   {"page": "Dark_Elixir_Drill",           "prefix": "Dark_Elixir_Drill",   "max": 11},
    "gold_storage":        {"page": "Gold_Storage/Home_Village",    "prefix": "Gold_Storage",        "max": 19},
    "elixir_storage":      {"page": "Elixir_Storage/Home_Village",  "prefix": "Elixir_Storage",      "max": 19},
    "dark_elixir_storage": {"page": "Dark_Elixir_Storage",          "prefix": "Dark_Elixir_Storage", "max": 12},
    # ── Army Buildings ──
    "barracks":            {"page": "Barracks",                     "prefix": "Barracks",            "max": 19},
    "dark_barracks":       {"page": "Dark_Barracks",                "prefix": "Dark_Barracks",       "max": 12},
    "army_camp":           {"page": "Army_Camp/Home_Village",       "prefix": "Army_Camp",           "max": 13},
    "spell_factory":       {"page": "Spell_Factory",                "prefix": "Spell_Factory",       "max": 9},
    "dark_spell_factory":  {"page": "Dark_Spell_Factory",           "prefix": "Dark_Spell_Factory",  "max": 7},
    "laboratory":          {"page": "Laboratory",                   "prefix": "Laboratory",          "max": 16},
    "workshop":            {"page": "Workshop",                     "prefix": "Workshop",            "max": 8},
    "pet_house":           {"page": "Pet_House",                    "prefix": "Pet_House",           "max": 12},
    "blacksmith":          {"page": "Blacksmith",                   "prefix": "Blacksmith",          "max": 9},
    "hero_hall":           {"page": "Hero_Hall",                    "prefix": "Hero_Hall",           "max": 11},
    # ── Special ──
    "town_hall":           {"page": "Town_Hall",                    "prefix": "Town_Hall",           "max": 18},
    "clan_castle":         {"page": "Clan_Castle",                  "prefix": "Clan_Castle",         "max": 14},
    "builder_hut":         {"page": "Builder's_Hut",                "prefix": "Builders_Hut",        "max": 7},
    "wall":                {"page": "Wall/Home_Village",            "prefix": "Wall",                "max": 18},
}

# Category groupings for --category filter
CATEGORIES: dict[str, list[str]] = {
    "defenses": [k for k in BUILDINGS if k in {
        "cannon", "archer_tower", "mortar", "air_defense", "wizard_tower",
        "air_sweeper", "x_bow", "inferno_tower", "eagle_artillery",
        "scattershot", "bomb_tower", "hidden_tesla", "monolith",
        "ricochet_cannon", "multi_archer_tower", "spell_tower",
        "firespitter", "multi_gear_tower",
    }],
    "traps": [k for k in BUILDINGS if k.endswith("_trap") or k in {
        "bomb_trap", "giant_bomb", "seeking_air_mine",
    }],
    "resources": [k for k in BUILDINGS if any(
        x in k for x in ("mine", "collector", "drill", "storage"))],
    "army": [k for k in BUILDINGS if k in {
        "barracks", "dark_barracks", "army_camp", "spell_factory",
        "dark_spell_factory", "laboratory", "workshop", "pet_house",
        "blacksmith", "hero_hall",
    }],
    "special": ["town_hall", "clan_castle", "builder_hut", "wall"],
}
CATEGORIES["all"] = list(BUILDINGS.keys())


# ── API helpers ──────────────────────────────────────────────────────

def _api_get(params: dict) -> dict:
    """Make a MediaWiki API request with rate limiting and retries."""
    params["format"] = "json"
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.get(API, params=params, headers=HEADERS, timeout=20)
            r.raise_for_status()
            time.sleep(REQUEST_DELAY)
            return r.json()
        except requests.RequestException as e:
            if attempt < MAX_RETRIES:
                wait = REQUEST_DELAY * attempt * 3
                print(f"    Retry {attempt}/{MAX_RETRIES} after {wait:.0f}s ({e})")
                time.sleep(wait)
            else:
                raise


def get_page_images(page: str) -> list[str]:
    """Return all image filenames listed on a wiki page."""
    data = _api_get({"action": "parse", "page": page, "prop": "images"})
    if "parse" not in data:
        return []
    return data["parse"].get("images", [])


def get_image_url(filename: str) -> str | None:
    """Get the direct download URL for a wiki image file."""
    data = _api_get({
        "action": "query",
        "titles": f"File:{filename}",
        "prop": "imageinfo",
        "iiprop": "url",
    })
    pages = data.get("query", {}).get("pages", {})
    for info in pages.values():
        if "imageinfo" in info:
            return info["imageinfo"][0]["url"]
    return None


def download_image(url: str, dest: Path) -> bool:
    """Download an image file. Returns True on success."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        dest.write_bytes(r.content)
        time.sleep(REQUEST_DELAY)
        return True
    except Exception as e:
        print(f"    FAILED: {e}")
        return False


# ── Image filtering ──────────────────────────────────────────────────

def find_level_images(all_images: list[str], prefix: str, max_level: int,
                      suffix: str = "") -> dict[int, str]:
    """Find the best image filename for each level.

    Tries exact match first ({Prefix}{Level}{Suffix}.png), then falls
    back to {Prefix}{Level}.png without suffix.
    """
    found: dict[int, str] = {}

    for level in range(1, max_level + 1):
        # Try with suffix first (e.g. X-Bow3_Ground.png)
        candidates = []
        if suffix:
            candidates.append(f"{prefix}{level}{suffix}.png")
        candidates.append(f"{prefix}{level}.png")

        for candidate in candidates:
            if candidate in all_images:
                found[level] = candidate
                break

    return found


# ── Main scraping logic ─────────────────────────────────────────────

def scrape_building(name: str, info: dict, output_dir: Path,
                    dry_run: bool = False) -> int:
    """Scrape all level images for one building. Returns download count."""
    page = info["page"]
    prefix = info["prefix"]
    max_level = info["max"]
    suffix = info.get("suffix", "")

    print(f"\n{'─'*50}")
    print(f"  {name} (levels 1-{max_level})")
    print(f"  Wiki page: {page}")

    # Get all images on the page
    all_images = get_page_images(page)
    if not all_images:
        print(f"  WARNING: No images found on page '{page}'")
        return 0

    # Find level-specific images
    level_images = find_level_images(all_images, prefix, max_level, suffix)
    print(f"  Found {len(level_images)}/{max_level} level images")

    if dry_run:
        for lvl, fname in sorted(level_images.items()):
            print(f"    Level {lvl}: {fname}")
        missing = set(range(1, max_level + 1)) - set(level_images.keys())
        if missing:
            print(f"    MISSING levels: {sorted(missing)}")
        return len(level_images)

    # Create output directory
    building_dir = output_dir / name
    building_dir.mkdir(parents=True, exist_ok=True)

    downloaded = 0
    for level, filename in sorted(level_images.items()):
        dest = building_dir / f"{name}_{level}.png"
        if dest.exists():
            print(f"    Level {level}: already exists, skipping")
            downloaded += 1
            continue

        url = get_image_url(filename)
        if not url:
            print(f"    Level {level}: could not resolve URL for {filename}")
            continue

        print(f"    Level {level}: downloading {filename}...")
        if download_image(url, dest):
            downloaded += 1

    missing = set(range(1, max_level + 1)) - set(level_images.keys())
    if missing:
        print(f"  MISSING levels (not on wiki): {sorted(missing)}")

    return downloaded


def scrape_all(category: str = "all", output_dir: str = "data/sprites",
               dry_run: bool = False):
    """Scrape building images for a category."""
    out = Path(output_dir)
    if not dry_run:
        out.mkdir(parents=True, exist_ok=True)

    building_names = CATEGORIES.get(category, CATEGORIES["all"])
    total_buildings = len(building_names)
    total_downloaded = 0
    total_expected = 0

    print(f"Scraping {total_buildings} buildings (category: {category})")
    print(f"Output: {out.resolve()}")
    if dry_run:
        print("DRY RUN — no files will be downloaded\n")

    for i, name in enumerate(building_names, 1):
        info = BUILDINGS[name]
        total_expected += info["max"]
        print(f"\n[{i}/{total_buildings}] ", end="")
        count = scrape_building(name, info, out, dry_run)
        total_downloaded += count

    print(f"\n{'='*50}")
    print(f"DONE: {total_downloaded}/{total_expected} images "
          f"({'would download' if dry_run else 'downloaded'})")
    print(f"Buildings: {total_buildings}")
    print(f"Output: {out.resolve()}")

    if not dry_run:
        # Write a summary file
        summary = out / "README.txt"
        summary.write_text(
            f"Clash of Clans building images scraped from clashofclans.fandom.com\n"
            f"Category: {category}\n"
            f"Buildings: {total_buildings}\n"
            f"Images: {total_downloaded}\n\n"
            f"Structure: {{building_name}}/{{building_name}}_{{level}}.png\n"
            f"Example: cannon/cannon_1.png\n"
        )


if __name__ == "__main__":
    p = argparse.ArgumentParser(
        description="Scrape CoC building images from the Fandom wiki")
    p.add_argument("--category", default="all",
                   choices=list(CATEGORIES.keys()),
                   help="Building category to scrape (default: all)")
    p.add_argument("--output", default="data/sprites",
                   help="Output directory (default: data/sprites)")
    p.add_argument("--dry-run", action="store_true",
                   help="Show what would be downloaded without downloading")
    args = p.parse_args()

    scrape_all(args.category, args.output, args.dry_run)
