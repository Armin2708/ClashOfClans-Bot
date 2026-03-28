#!/usr/bin/env python3
"""
Merge all CoC training sources into one unified dataset.

Sources (all optional, combine as many as you have):
  --public    datasets/public               HuggingFace baseline (16 legacy classes)
  --roboflow  datasets/roboflow/remapped    Roboflow Universe datasets
  --labeled   datasets/labeled              Your own Roboflow-labeled screenshots

All sources are remapped to class_registry.ALL_CLASSES before merging.

IMPORTANT — labeling for level-specific classes:
  When labeling in Roboflow, use the exact class name from class_registry.py:
    cannon_7, archer_tower_12, barbarian_3, lightning_spell_5, etc.
  Level-agnostic names (cannon, archer_tower) map to legacy aliases only.

Usage:
    python training/merge_datasets.py --public datasets/public --output datasets/full
    python training/merge_datasets.py \\
        --public datasets/public \\
        --roboflow datasets/roboflow/remapped \\
        --labeled datasets/labeled \\
        --output datasets/full
"""

import shutil
import argparse
from pathlib import Path

from training.class_registry import ALL_CLASSES, CLASS_INDEX, LEGACY_ALIASES

# ── Name normalizer: maps any source class name → canonical class name ──────────
# Covers the level-agnostic names used by existing Roboflow CoC datasets
# (they label "cannon" not "cannon_7"). These map to legacy aliases where possible,
# so the data still contributes to training. Level-specific labels like "cannon_7"
# pass through directly.
_LEGACY_NAME_MAP: dict[str, str] = {
    # Public HF dataset names → legacy aliases (already in CLASS_INDEX)
    "ad":           "ad",
    "airsweeper":   "airsweeper",
    "bombtower":    "bombtower",
    "canon":        "canon",
    "cannon":       "canon",
    "clancastle":   "clancastle",
    "eagle":        "eagle",
    "inferno":      "inferno",
    "kingpad":      "kingpad",
    "mortar":       "mortar",
    "queenpad":     "queenpad",
    "rcpad":        "rcpad",
    "scattershot":  "scattershot",
    "th13":         "th13",
    "wardenpad":    "wardenpad",
    "wizztower":    "wizztower",
    "xbow":         "xbow",
    # Roboflow dataset variants → legacy aliases
    "airdefense":        "ad",
    "air_defense":       "ad",
    "air defense":       "ad",
    "air_sweeper":       "airsweeper",
    "airsweeper":        "airsweeper",
    "air sweeper":       "airsweeper",
    "bomb_tower":        "bombtower",
    "bombtower":         "bombtower",
    "bomb tower":        "bombtower",
    "cannon":            "canon",
    "clan_castle":       "clancastle",
    "clan castle":       "clancastle",
    "eagle_artillery":   "eagle",
    "eagleartillery":    "eagle",
    "eagle artillery":   "eagle",
    "inferno_tower":     "inferno",
    "infernotower":      "inferno",
    "inferno tower":     "inferno",
    "barbarian_king":    "kingpad",
    "barbarianking":     "kingpad",
    "barbarian king":    "kingpad",
    "king":              "kingpad",
    "archer_queen":      "queenpad",
    "archerqueen":       "queenpad",
    "archer queen":      "queenpad",
    "queen":             "queenpad",
    "royal_champion":    "rcpad",
    "royalchampion":     "rcpad",
    "royal champion":    "rcpad",
    "grand_warden":      "wardenpad",
    "grandwarden":       "wardenpad",
    "grand warden":      "wardenpad",
    "warden":            "wardenpad",
    "wizard_tower":      "wizztower",
    "wizardtower":       "wizztower",
    "wizard tower":      "wizztower",
    "x_bow":             "xbow",
    "x-bow":             "xbow",
    "x bow":             "xbow",
    "townhall":          "th13",
    "town_hall":         "th13",
    "town hall":         "th13",
    "th":                "th13",
    # Archer tower has no legacy alias — map to level-agnostic new class
    "archertower":       "archer_tower_1",
    "archer_tower":      "archer_tower_1",
    "archer tower":      "archer_tower_1",
    "hiddentesla":       "hidden_tesla_1",
    "hidden_tesla":      "hidden_tesla_1",
    "hidden tesla":      "hidden_tesla_1",
    "tesla":             "hidden_tesla_1",
    "giga_tesla":        "giga_tesla_1",
    "giga tesla":        "giga_tesla_1",
    "monolith":          "monolith_1",
    "ricochet_cannon":   "ricochet_cannon_1",
    "ricochet cannon":   "ricochet_cannon_1",
    "multi_archer_tower":"multi_archer_tower_1",
    "spell_tower":       "spell_tower_1",
    # Traps
    "bomb":              "bomb_trap_1",
    "bomb_trap":         "bomb_trap_1",
    "spring":            "spring_trap_1",
    "spring_trap":       "spring_trap_1",
    "airbomb":           "air_bomb_trap_1",
    "air_bomb":          "air_bomb_trap_1",
    "giant_bomb":        "giant_bomb_1",
    "giantbomb":         "giant_bomb_1",
    "seeking_air_mine":  "seeking_air_mine_1",
    "skeleton_trap":     "skeleton_trap_1",
    "tornado_trap":      "tornado_trap_1",
    # Resources
    "gold_mine":         "gold_mine_1",
    "goldmine":          "gold_mine_1",
    "gold mine":         "gold_mine_1",
    "elixir_collector":  "elixir_collector_1",
    "elixircollector":   "elixir_collector_1",
    "dark_elixir_drill": "dark_elixir_drill_1",
    "darkelixirdrill":   "dark_elixir_drill_1",
    "gold_storage":      "gold_storage_1",
    "goldstorage":       "gold_storage_1",
    "elixir_storage":    "elixir_storage_1",
    "elixirstorage":     "elixir_storage_1",
    "dark_elixir_storage":"dark_elixir_storage_1",
    # Army
    "barracks":          "barracks_1",
    "dark_barracks":     "dark_barracks_1",
    "darkbarracks":      "dark_barracks_1",
    "army_camp":         "army_camp_1",
    "armycamp":          "army_camp_1",
    "spell_factory":     "spell_factory_1",
    "spellfactory":      "spell_factory_1",
    "dark_spell_factory":"dark_spell_factory_1",
    "laboratory":        "laboratory_1",
    "lab":               "laboratory_1",
    "workshop":          "workshop_1",
    "pet_house":         "pet_house_1",
    "blacksmith":        "blacksmith_1",
    "hero_hall":         "hero_hall_1",
    "builder_hut":       "builder_hut_1",
    "builderhut":        "builder_hut_1",
    "builder":           "builder_hut_1",
}


def _resolve_class(name: str) -> int | None:
    """
    Resolve a source class name to a CLASS_INDEX entry.
    - Level-specific names (cannon_7) pass through directly.
    - Level-agnostic names (cannon) fall back via _LEGACY_NAME_MAP.
    Returns None if unresolvable (annotation will be dropped).
    """
    key = name.strip()
    # Direct match (handles level-specific names like "cannon_7")
    if key in CLASS_INDEX:
        return CLASS_INDEX[key]
    # Lowercase fallback
    lower = key.lower()
    if lower in CLASS_INDEX:
        return CLASS_INDEX[lower]
    # Legacy/alias map
    mapped = _LEGACY_NAME_MAP.get(lower)
    if mapped and mapped in CLASS_INDEX:
        return CLASS_INDEX[mapped]
    return None


def _read_yaml_classes(yaml_path: Path) -> list[str]:
    """Read the 'names' list from a YOLO data.yaml file."""
    try:
        import yaml
        with open(yaml_path) as f:
            data = yaml.safe_load(f)
        names = data.get("names", [])
        return [names[i] for i in sorted(names)] if isinstance(names, dict) else names
    except Exception:
        return []


def _copy_split(src_img: Path, src_lbl: Path, dst_img: Path, dst_lbl: Path,
                prefix: str, id_remap: dict[int, int | None]) -> int:
    """Copy images + remapped labels. Returns number of images copied."""
    if not src_img.exists():
        return 0
    dst_img.mkdir(parents=True, exist_ok=True)
    dst_lbl.mkdir(parents=True, exist_ok=True)
    count = 0
    for img_path in sorted(src_img.glob("*")):
        if img_path.suffix.lower() not in (".jpg", ".jpeg", ".png"):
            continue
        shutil.copy(img_path, dst_img / f"{prefix}_{img_path.name}")
        lbl_path = src_lbl / img_path.with_suffix(".txt").name
        dst_lbl_path = dst_lbl / f"{prefix}_{img_path.stem}.txt"
        if lbl_path.exists():
            lines = [l for l in lbl_path.read_text().strip().split("\n") if l.strip()]
            remapped = []
            for line in lines:
                parts = line.split()
                new_id = id_remap.get(int(parts[0]))
                if new_id is not None:
                    parts[0] = str(new_id)
                    remapped.append(" ".join(parts))
            dst_lbl_path.write_text("\n".join(remapped))
        else:
            dst_lbl_path.write_text("")
        count += 1
    return count


def _remap_from_names(src_names: list[str]) -> tuple[dict[int, int | None], list[str]]:
    """Build ID remap from source class names. Returns (remap, unmapped_names)."""
    remap, unmapped = {}, []
    for i, name in enumerate(src_names):
        cid = _resolve_class(name)
        remap[i] = cid
        if cid is None:
            unmapped.append(name)
    return remap, unmapped


def merge(public_dir: str | None, roboflow_dir: str | None,
          labeled_dir: str | None, output_dir: str) -> None:
    out = Path(output_dir)
    total = 0

    # ── 1. Public HuggingFace dataset ────────────────────────────────────────
    if public_dir and Path(public_dir).exists():
        pub = Path(public_dir)
        # Legacy IDs 0-15 map directly to LEGACY_ALIASES (same order)
        remap = {i: i for i in range(len(LEGACY_ALIASES))}
        print(f"\nPublic dataset ({pub}):")
        for src_split, dst_split in [("train", "train"), ("test", "train")]:
            n = _copy_split(
                pub / src_split / "images", pub / src_split / "labels",
                out / dst_split / "images", out / dst_split / "labels",
                prefix=f"pub_{src_split}", id_remap=remap,
            )
            total += n
            if n: print(f"  {src_split}: {n} images")
        n = _copy_split(
            pub / "validation" / "images", pub / "validation" / "labels",
            out / "val" / "images", out / "val" / "labels",
            prefix="pub_val", id_remap=remap,
        )
        total += n
        if n: print(f"  validation: {n} images")

    # ── 2. Roboflow Universe datasets ─────────────────────────────────────────
    if roboflow_dir and Path(roboflow_dir).exists():
        rbf = Path(roboflow_dir)
        for proj_dir in sorted(rbf.iterdir()):
            if not proj_dir.is_dir():
                continue
            yaml_files = list(proj_dir.glob("*.yaml"))
            src_names = _read_yaml_classes(yaml_files[0]) if yaml_files else []
            if src_names:
                remap, unmapped = _remap_from_names(src_names)
            else:
                # Already remapped by download_roboflow.py — identity map
                remap = {i: i for i in range(len(ALL_CLASSES))}
                unmapped = []

            print(f"\nRoboflow dataset ({proj_dir.name}):")
            if unmapped:
                print(f"  ⚠ Unmapped classes (dropped): {unmapped}")

            for src_split, dst_split in [("train", "train"), ("test", "train")]:
                n = _copy_split(
                    proj_dir / src_split / "images",
                    proj_dir / src_split / "labels",
                    out / dst_split / "images", out / dst_split / "labels",
                    prefix=f"rbf_{proj_dir.name[:8]}_{src_split[:2]}", id_remap=remap,
                )
                total += n
                if n: print(f"  {src_split}: {n} images")
            for val_name in ("valid", "validation"):
                val_dir = proj_dir / val_name
                if val_dir.exists():
                    n = _copy_split(
                        val_dir / "images", val_dir / "labels",
                        out / "val" / "images", out / "val" / "labels",
                        prefix=f"rbf_{proj_dir.name[:8]}_val", id_remap=remap,
                    )
                    total += n
                    if n: print(f"  val: {n} images")
                    break

    # ── 3. User-labeled dataset ───────────────────────────────────────────────
    if labeled_dir and Path(labeled_dir).exists():
        lab = Path(labeled_dir)
        print(f"\nLabeled dataset ({lab}):")
        yaml_files = list(lab.glob("*.yaml")) + [lab / "data.yaml"]
        yaml_files = [f for f in yaml_files if f.exists()]
        if yaml_files:
            src_names = _read_yaml_classes(yaml_files[0])
            print(f"  Source classes ({len(src_names)}): {src_names[:8]}{'...' if len(src_names) > 8 else ''}")
            remap, unmapped = _remap_from_names(src_names)
            if unmapped:
                print(f"  ⚠ Unmapped (dropped): {unmapped}")
                print(f"    Tip: use exact names from 'python training/class_registry.py --list'")
        else:
            print("  ⚠ No data.yaml found — skipping")
            return

        for src_split, dst_split in [("train", "train"), ("test", "train")]:
            n = _copy_split(
                lab / src_split / "images", lab / src_split / "labels",
                out / dst_split / "images", out / dst_split / "labels",
                prefix=f"lab_{src_split}", id_remap=remap,
            )
            total += n
            if n: print(f"  {src_split}: {n} images")
        for val_name in ("valid", "validation"):
            val_dir = lab / val_name
            if val_dir.exists():
                n = _copy_split(
                    val_dir / "images", val_dir / "labels",
                    out / "val" / "images", out / "val" / "labels",
                    prefix="lab_val", id_remap=remap,
                )
                total += n
                if n: print(f"  val: {n} images")
                break

    # ── Write dataset.yaml ────────────────────────────────────────────────────
    yaml_path = out / "dataset.yaml"
    yaml_path.write_text(
        f"# Full CoC dataset — {len(ALL_CLASSES)} classes, {total} images\n"
        f"# Auto-generated by merge_datasets.py. Do not edit manually.\n\n"
        f"path: {out.resolve()}\n"
        f"train: train/images\n"
        f"val: val/images\n\n"
        f"nc: {len(ALL_CLASSES)}\n"
        f"names: {ALL_CLASSES}\n"
    )

    print(f"\n{'='*60}")
    print(f"Merged {total} images → {out}/")
    print(f"Total classes: {len(ALL_CLASSES)}")
    print(f"Config: {yaml_path}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Merge all CoC training datasets")
    p.add_argument("--public",   default=None, help="HuggingFace dataset dir")
    p.add_argument("--roboflow", default=None, help="Roboflow remapped datasets dir")
    p.add_argument("--labeled",  default=None, help="User-labeled Roboflow export dir")
    p.add_argument("--output",   default="datasets/full")
    args = p.parse_args()
    if not any([args.public, args.roboflow, args.labeled]):
        p.error("Provide at least one of --public, --roboflow, or --labeled")
    merge(args.public, args.roboflow, args.labeled, args.output)
