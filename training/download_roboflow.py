#!/usr/bin/env python3
"""
Download Clash of Clans datasets from Roboflow Universe.

Downloads the WalkStation dataset (35 classes, 798 images) and optionally
additional community datasets to supplement the public HuggingFace baseline.

Requires a free Roboflow account and API key:
  https://app.roboflow.com → Settings → Roboflow API

Usage:
    python training/download_roboflow.py --api-key YOUR_KEY
    python training/download_roboflow.py --api-key YOUR_KEY --output datasets/roboflow
    python training/download_roboflow.py --api-key YOUR_KEY --list    # list classes only
"""

import argparse
import json
import shutil
from pathlib import Path

# ── Roboflow datasets to download ──────────────────────────────────────────────
# Each entry: (workspace, project, version)
ROBOFLOW_DATASETS = [
    ("walkstation",   "clash-of-clan-object-detection", 1),
    ("cg-20242-g3n8u", "detection-clash-of-clans",     1),
]

# ── Canonical class names (master list shared with merge_datasets.py) ──────────
# Any class from any source dataset gets normalized to one of these names.
# See ROBOFLOW_CLASS_MAP below for the remapping.
CANONICAL_CLASSES = [
    # Defenses (public HF dataset names — keep for backward compat with trained model)
    "ad", "airsweeper", "bombtower", "canon", "clancastle",
    "eagle", "inferno", "kingpad", "mortar", "queenpad",
    "rcpad", "scattershot", "th13", "wardenpad", "wizztower", "xbow",
    # Additional defenses
    "archer_tower", "hidden_tesla", "giga_tesla", "monolith",
    "ricochet_cannon", "multi_archer_tower", "spell_tower",
    # Traps
    "bomb_trap", "spring_trap", "air_bomb_trap", "giant_bomb",
    "seeking_air_mine", "skeleton_trap", "tornado_trap",
    # Resources
    "gold_mine", "elixir_collector", "dark_elixir_drill",
    "gold_storage", "elixir_storage", "dark_elixir_storage",
    # Army
    "barracks", "dark_barracks", "army_camp", "spell_factory",
    "dark_spell_factory", "laboratory", "workshop", "pet_house",
    "blacksmith", "hero_hall",
    # Structures
    "town_hall", "builder_hut",
    # UI buttons
    "btn_attack", "btn_find_match", "btn_start_battle", "btn_next_base",
    "btn_return_home", "btn_end_battle", "btn_confirm", "btn_close",
    "btn_okay", "btn_later",
    # HUD + loot
    "hud_village", "hud_scouting", "hud_results", "hud_army",
    "loot_gold", "loot_elixir", "loot_gem", "troop_slot",
]

# ── Remapping: source class name (lowercase) → canonical name ──────────────────
# Covers naming variants across all known CoC Roboflow datasets.
ROBOFLOW_CLASS_MAP = {
    # Defenses — variants seen across datasets
    "ad":               "ad",
    "airdefense":       "ad",
    "air_defense":      "ad",
    "air defense":      "ad",
    "airsweeper":       "airsweeper",
    "air_sweeper":      "airsweeper",
    "air sweeper":      "airsweeper",
    "bombtower":        "bombtower",
    "bomb_tower":       "bombtower",
    "bomb tower":       "bombtower",
    "canon":            "canon",
    "cannon":           "canon",
    "clancastle":       "clancastle",
    "clan_castle":      "clancastle",
    "clan castle":      "clancastle",
    "eagle":            "eagle",
    "eagleartillery":   "eagle",
    "eagle_artillery":  "eagle",
    "eagle artillery":  "eagle",
    "inferno":          "inferno",
    "infernotower":     "inferno",
    "inferno_tower":    "inferno",
    "inferno tower":    "inferno",
    "kingpad":          "kingpad",
    "king":             "kingpad",
    "barbarianking":    "kingpad",
    "barbarian_king":   "kingpad",
    "barbarian king":   "kingpad",
    "mortar":           "mortar",
    "queenpad":         "queenpad",
    "queen":            "queenpad",
    "archerqueen":      "queenpad",
    "archer_queen":     "queenpad",
    "archer queen":     "queenpad",
    "rcpad":            "rcpad",
    "royalchampion":    "rcpad",
    "royal_champion":   "rcpad",
    "royal champion":   "rcpad",
    "scattershot":      "scattershot",
    "th13":             "th13",
    "townhall":         "town_hall",
    "town_hall":        "town_hall",
    "town hall":        "town_hall",
    "th":               "town_hall",
    "wardenpad":        "wardenpad",
    "warden":           "wardenpad",
    "grandwarden":      "wardenpad",
    "grand_warden":     "wardenpad",
    "grand warden":     "wardenpad",
    "wizztower":        "wizztower",
    "wizardtower":      "wizztower",
    "wizard_tower":     "wizztower",
    "wizard tower":     "wizztower",
    "xbow":             "xbow",
    "x_bow":            "xbow",
    "x-bow":            "xbow",
    "x bow":            "xbow",
    "archer_tower":     "archer_tower",
    "archertower":      "archer_tower",
    "archer tower":     "archer_tower",
    "hidden_tesla":     "hidden_tesla",
    "hiddentesla":      "hidden_tesla",
    "hidden tesla":     "hidden_tesla",
    "tesla":            "hidden_tesla",
    "giga_tesla":       "giga_tesla",
    "gigateslah":       "giga_tesla",
    "giga tesla":       "giga_tesla",
    "monolith":         "monolith",
    "ricochet_cannon":  "ricochet_cannon",
    "ricochet cannon":  "ricochet_cannon",
    "multi_archer_tower": "multi_archer_tower",
    "multi archer tower": "multi_archer_tower",
    "spell_tower":      "spell_tower",
    "spell tower":      "spell_tower",
    # Traps
    "bomb_trap":        "bomb_trap",
    "bomb":             "bomb_trap",
    "spring_trap":      "spring_trap",
    "spring trap":      "spring_trap",
    "spring":           "spring_trap",
    "air_bomb_trap":    "air_bomb_trap",
    "air bomb":         "air_bomb_trap",
    "airbomb":          "air_bomb_trap",
    "giant_bomb":       "giant_bomb",
    "giantbomb":        "giant_bomb",
    "giant bomb":       "giant_bomb",
    "seeking_air_mine": "seeking_air_mine",
    "seekingairmine":   "seeking_air_mine",
    "skeleton_trap":    "skeleton_trap",
    "skeleton trap":    "skeleton_trap",
    "tornado_trap":     "tornado_trap",
    "tornado trap":     "tornado_trap",
    # Resources
    "gold_mine":        "gold_mine",
    "goldmine":         "gold_mine",
    "gold mine":        "gold_mine",
    "elixir_collector": "elixir_collector",
    "elixircollector":  "elixir_collector",
    "elixir collector": "elixir_collector",
    "dark_elixir_drill":"dark_elixir_drill",
    "darkelixirdrill":  "dark_elixir_drill",
    "dark elixir drill":"dark_elixir_drill",
    "gold_storage":     "gold_storage",
    "goldstorage":      "gold_storage",
    "gold storage":     "gold_storage",
    "elixir_storage":   "elixir_storage",
    "elixirstorage":    "elixir_storage",
    "elixir storage":   "elixir_storage",
    "dark_elixir_storage": "dark_elixir_storage",
    "darkelixirstorage":"dark_elixir_storage",
    # Army
    "barracks":         "barracks",
    "dark_barracks":    "dark_barracks",
    "darkbarracks":     "dark_barracks",
    "dark barracks":    "dark_barracks",
    "army_camp":        "army_camp",
    "armycamp":         "army_camp",
    "army camp":        "army_camp",
    "spell_factory":    "spell_factory",
    "spellfactory":     "spell_factory",
    "spell factory":    "spell_factory",
    "dark_spell_factory": "dark_spell_factory",
    "darkspellfactory": "dark_spell_factory",
    "laboratory":       "laboratory",
    "lab":              "laboratory",
    "workshop":         "workshop",
    "pet_house":        "pet_house",
    "pethouse":         "pet_house",
    "pet house":        "pet_house",
    "blacksmith":       "blacksmith",
    "hero_hall":        "hero_hall",
    "herohall":         "hero_hall",
    "hero hall":        "hero_hall",
    # Structures
    "builder_hut":      "builder_hut",
    "builderhut":       "builder_hut",
    "builder hut":      "builder_hut",
    "builder":          "builder_hut",
}

CANONICAL_INDEX = {name: i for i, name in enumerate(CANONICAL_CLASSES)}


def normalize_class(name: str) -> str | None:
    """Map a source class name to our canonical name. Returns None if unknown."""
    return ROBOFLOW_CLASS_MAP.get(name.lower().strip())


def download_dataset(api_key: str, workspace: str, project: str, version: int,
                     output_dir: Path) -> dict:
    """Download one Roboflow dataset in YOLOv11 format. Returns class info."""
    from roboflow import Roboflow

    rf = Roboflow(api_key=api_key)
    proj = rf.workspace(workspace).project(project)
    ds = proj.version(version).download("yolov11", location=str(output_dir))
    print(f"  Downloaded to {output_dir}")

    # Read class names from data.yaml
    import yaml
    yaml_files = list(output_dir.glob("*.yaml")) + list(output_dir.glob("data.yaml"))
    if not yaml_files:
        raise FileNotFoundError(f"No data.yaml found in {output_dir}")

    with open(yaml_files[0]) as f:
        data = yaml.safe_load(f)
    return {"names": data.get("names", []), "nc": data.get("nc", 0)}


def remap_labels(src_dir: Path, dst_dir: Path, src_classes: list[str],
                 prefix: str) -> tuple[int, list[str]]:
    """
    Copy images + labels from src_dir to dst_dir, remapping class IDs
    from the source dataset's class list to our CANONICAL_CLASSES indices.

    Returns (num_images_copied, list_of_unmapped_classes).
    """
    img_src = src_dir / "images"
    lbl_src = src_dir / "labels"
    img_dst = dst_dir / "images"
    lbl_dst = dst_dir / "labels"
    img_dst.mkdir(parents=True, exist_ok=True)
    lbl_dst.mkdir(parents=True, exist_ok=True)

    # Build ID remapping: source_id → canonical_id (or None if unknown)
    id_map: dict[int, int | None] = {}
    unmapped = []
    for i, src_name in enumerate(src_classes):
        canonical = normalize_class(src_name)
        if canonical and canonical in CANONICAL_INDEX:
            id_map[i] = CANONICAL_INDEX[canonical]
        else:
            id_map[i] = None
            unmapped.append(src_name)

    count = 0
    for img_path in sorted(img_src.glob("*")):
        if img_path.suffix.lower() not in (".jpg", ".jpeg", ".png"):
            continue
        dst_img = img_dst / f"{prefix}_{img_path.name}"
        shutil.copy(img_path, dst_img)

        lbl_path = lbl_src / img_path.with_suffix(".txt").name
        dst_lbl = lbl_dst / f"{prefix}_{img_path.stem}.txt"
        if lbl_path.exists():
            lines = [l for l in lbl_path.read_text().strip().split("\n") if l.strip()]
            remapped = []
            for line in lines:
                parts = line.split()
                src_id = int(parts[0])
                canonical_id = id_map.get(src_id)
                if canonical_id is not None:
                    parts[0] = str(canonical_id)
                    remapped.append(" ".join(parts))
                # skip annotations for unmapped classes
            dst_lbl.write_text("\n".join(remapped))
        else:
            dst_lbl.write_text("")
        count += 1

    return count, unmapped


def process_all(api_key: str, output_base: Path, list_only: bool = False) -> None:
    try:
        import roboflow  # noqa: F401
    except ImportError:
        print("ERROR: roboflow package not installed. Run:")
        print("  .venv/bin/pip install roboflow")
        return

    remapped_base = output_base / "remapped"

    for workspace, project, version in ROBOFLOW_DATASETS:
        print(f"\n{'='*60}")
        print(f"Dataset: {workspace}/{project} v{version}")

        raw_dir = output_base / "raw" / project
        info = download_dataset(api_key, workspace, project, version, raw_dir)
        src_classes = info["names"]

        print(f"  Source classes ({len(src_classes)}): {src_classes}")

        if list_only:
            print("\n  Remapping preview:")
            for name in src_classes:
                canonical = normalize_class(name)
                status = f"→ {canonical}" if canonical else "⚠ UNMAPPED"
                print(f"    {name:30s} {status}")
            continue

        # Remap and copy for each split
        unmapped_all = set()
        total = 0
        for split in ("train", "valid", "test"):
            src_split = raw_dir / split
            if not src_split.exists():
                continue
            dst_split = remapped_base / project / split
            n, unmapped = remap_labels(src_split, dst_split, src_classes,
                                        prefix=f"{project[:8]}_{split[:2]}")
            total += n
            unmapped_all.update(unmapped)

        print(f"  Remapped {total} images → {remapped_base / project}/")
        if unmapped_all:
            print(f"  ⚠ Unmapped classes (skipped): {sorted(unmapped_all)}")
            print(f"    Add them to ROBOFLOW_CLASS_MAP in this script to include them.")

    if not list_only:
        # Write a combined dataset.yaml for all remapped data
        yaml_path = remapped_base / "dataset.yaml"
        yaml_path.write_text(
            f"# Remapped Roboflow CoC datasets — canonical class IDs\n\n"
            f"path: {remapped_base.resolve()}\n"
            f"train: train/images\n"
            f"val: val/images\n\n"
            f"nc: {len(CANONICAL_CLASSES)}\n"
            f"names: {CANONICAL_CLASSES}\n"
        )
        print(f"\nAll datasets remapped. Pass --roboflow {remapped_base} to merge_datasets.py")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Download CoC datasets from Roboflow Universe")
    p.add_argument("--api-key", required=True, help="Roboflow API key")
    p.add_argument("--output", default="datasets/roboflow",
                   help="Output directory (default: datasets/roboflow)")
    p.add_argument("--list", action="store_true",
                   help="List class names and remapping preview without downloading labels")
    args = p.parse_args()
    process_all(args.api_key, Path(args.output), list_only=args.list)
