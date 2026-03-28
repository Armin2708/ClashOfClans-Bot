#!/usr/bin/env python3
"""
Merge all CoC training sources into one unified dataset.

Sources (all optional, combine as many as you have):
  --public    datasets/public          HuggingFace baseline (16 classes, 125 images)
  --roboflow  datasets/roboflow/remapped  Roboflow Universe datasets (already remapped)
  --labeled   datasets/labeled         Your own Roboflow-labeled screenshots

All sources are remapped to ALL_CLASSES before merging, so class IDs are consistent.

Usage:
    # Public + your own labels only:
    python training/merge_datasets.py \
        --public datasets/public \
        --labeled datasets/labeled \
        --output datasets/full

    # All three sources:
    python training/merge_datasets.py \
        --public  datasets/public \
        --roboflow datasets/roboflow/remapped \
        --labeled  datasets/labeled \
        --output   datasets/full
"""

import shutil
import argparse
from pathlib import Path

# ── Canonical class list (single source of truth) ──────────────────────────────
# Class ID = index in this list. Never reorder — only append.
# Keep in sync with download_roboflow.py CANONICAL_CLASSES.
ALL_CLASSES = [
    # ── Defenses (public HF dataset names — keep for model continuity) ──────
    "ad",              # Air Defense
    "airsweeper",      # Air Sweeper
    "bombtower",       # Bomb Tower
    "canon",           # Cannon
    "clancastle",      # Clan Castle
    "eagle",           # Eagle Artillery
    "inferno",         # Inferno Tower
    "kingpad",         # Barbarian King altar
    "mortar",          # Mortar
    "queenpad",        # Archer Queen altar
    "rcpad",           # Royal Champion altar
    "scattershot",     # Scattershot
    "th13",            # Town Hall (from baseline dataset)
    "wardenpad",       # Grand Warden altar
    "wizztower",       # Wizard Tower
    "xbow",            # X-Bow
    # ── Additional defenses ─────────────────────────────────────────────────
    "archer_tower",
    "hidden_tesla",
    "giga_tesla",
    "monolith",
    "ricochet_cannon",
    "multi_archer_tower",
    "spell_tower",
    # ── Traps ────────────────────────────────────────────────────────────────
    "bomb_trap",
    "spring_trap",
    "air_bomb_trap",
    "giant_bomb",
    "seeking_air_mine",
    "skeleton_trap",
    "tornado_trap",
    # ── Resources ────────────────────────────────────────────────────────────
    "gold_mine",
    "elixir_collector",
    "dark_elixir_drill",
    "gold_storage",
    "elixir_storage",
    "dark_elixir_storage",
    # ── Army buildings ───────────────────────────────────────────────────────
    "barracks",
    "dark_barracks",
    "army_camp",
    "spell_factory",
    "dark_spell_factory",
    "laboratory",
    "workshop",
    "pet_house",
    "blacksmith",
    "hero_hall",
    # ── Other structures ─────────────────────────────────────────────────────
    "town_hall",
    "builder_hut",
    # ── UI buttons ───────────────────────────────────────────────────────────
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
    # ── HUD overlays ─────────────────────────────────────────────────────────
    "hud_village",
    "hud_scouting",
    "hud_results",
    "hud_army",
    # ── Loot / troop UI ──────────────────────────────────────────────────────
    "loot_gold",
    "loot_elixir",
    "loot_gem",
    "troop_slot",
]

# ── Class name remapping for the user-labeled (Roboflow export) dataset ─────────
# Roboflow resets class IDs to 0. This maps labeled class names → ALL_CLASSES index.
# IMPORTANT: Update this to match the exact class names in datasets/labeled/data.yaml
#            after you export from Roboflow (check the names: list in that file).
LABELED_CLASS_MAP = {
    # Defenses (additional)
    "archer_tower":       "archer_tower",
    "hidden_tesla":       "hidden_tesla",
    "giga_tesla":         "giga_tesla",
    "monolith":           "monolith",
    "ricochet_cannon":    "ricochet_cannon",
    "multi_archer_tower": "multi_archer_tower",
    "spell_tower":        "spell_tower",
    # Traps
    "bomb_trap":          "bomb_trap",
    "spring_trap":        "spring_trap",
    "air_bomb_trap":      "air_bomb_trap",
    "giant_bomb":         "giant_bomb",
    "seeking_air_mine":   "seeking_air_mine",
    "skeleton_trap":      "skeleton_trap",
    "tornado_trap":       "tornado_trap",
    # Resources
    "gold_mine":          "gold_mine",
    "elixir_collector":   "elixir_collector",
    "dark_elixir_drill":  "dark_elixir_drill",
    "gold_storage":       "gold_storage",
    "elixir_storage":     "elixir_storage",
    "dark_elixir_storage":"dark_elixir_storage",
    # Army
    "barracks":           "barracks",
    "dark_barracks":      "dark_barracks",
    "army_camp":          "army_camp",
    "spell_factory":      "spell_factory",
    "dark_spell_factory": "dark_spell_factory",
    "laboratory":         "laboratory",
    "workshop":           "workshop",
    "pet_house":          "pet_house",
    "blacksmith":         "blacksmith",
    "hero_hall":          "hero_hall",
    # Structures
    "town_hall":          "town_hall",
    "builder_hut":        "builder_hut",
    # UI
    "btn_attack":         "btn_attack",
    "btn_find_match":     "btn_find_match",
    "btn_start_battle":   "btn_start_battle",
    "btn_next_base":      "btn_next_base",
    "btn_return_home":    "btn_return_home",
    "btn_end_battle":     "btn_end_battle",
    "btn_confirm":        "btn_confirm",
    "btn_close":          "btn_close",
    "btn_okay":           "btn_okay",
    "btn_later":          "btn_later",
    "hud_village":        "hud_village",
    "hud_scouting":       "hud_scouting",
    "hud_results":        "hud_results",
    "hud_army":           "hud_army",
    "loot_gold":          "loot_gold",
    "loot_elixir":        "loot_elixir",
    "loot_gem":           "loot_gem",
    "troop_slot":         "troop_slot",
}

CLASS_INDEX = {name: i for i, name in enumerate(ALL_CLASSES)}


def _read_yaml_classes(yaml_path: Path) -> list[str]:
    """Read the 'names' list from a YOLO data.yaml file."""
    try:
        import yaml
        with open(yaml_path) as f:
            data = yaml.safe_load(f)
        names = data.get("names", [])
        if isinstance(names, dict):
            return [names[i] for i in sorted(names)]
        return names
    except Exception:
        return []


def _copy_split(src_img: Path, src_lbl: Path, dst_img: Path, dst_lbl: Path,
                prefix: str, id_remap: dict[int, int | None]) -> int:
    """
    Copy images + labels, remapping class IDs via id_remap.
    Annotations with unmapped IDs are silently dropped.
    Returns number of images copied.
    """
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


def _identity_remap(n: int) -> dict[int, int | None]:
    """IDs 0..n-1 stay the same (public dataset is already canonical)."""
    return {i: i for i in range(n)}


def _build_remap_from_names(src_names: list[str],
                             name_map: dict[str, str]) -> dict[int, int | None]:
    """Map source class IDs → canonical IDs using a name→canonical_name dict."""
    remap = {}
    for i, name in enumerate(src_names):
        canonical = name_map.get(name)
        remap[i] = CLASS_INDEX.get(canonical) if canonical else None
    return remap


def merge(public_dir: str | None, roboflow_dir: str | None,
          labeled_dir: str | None, output_dir: str) -> None:
    out = Path(output_dir)

    total = 0

    # ── 1. Public HuggingFace dataset (IDs 0-15, already canonical) ──────────
    if public_dir and Path(public_dir).exists():
        pub = Path(public_dir)
        remap = _identity_remap(16)
        print(f"\nPublic dataset ({pub}):")
        for src_split, dst_split in [("train", "train"), ("test", "train")]:
            n = _copy_split(
                pub / src_split / "images", pub / src_split / "labels",
                out / dst_split / "images", out / dst_split / "labels",
                prefix=f"pub_{src_split}", id_remap=remap,
            )
            total += n
            print(f"  {src_split}: {n} images")
        n = _copy_split(
            pub / "validation" / "images", pub / "validation" / "labels",
            out / "val" / "images", out / "val" / "labels",
            prefix="pub_val", id_remap=remap,
        )
        total += n
        print(f"  validation: {n} images")

    # ── 2. Roboflow datasets (already remapped by download_roboflow.py) ───────
    if roboflow_dir and Path(roboflow_dir).exists():
        rbf = Path(roboflow_dir)
        # Each subdirectory is one project
        for proj_dir in sorted(rbf.iterdir()):
            if not proj_dir.is_dir() or proj_dir.name == "raw":
                continue
            print(f"\nRoboflow dataset ({proj_dir.name}):")
            # Already remapped to canonical IDs — use identity
            remap = _identity_remap(len(ALL_CLASSES))
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

    # ── 3. User-labeled dataset (exported from Roboflow, custom class order) ──
    if labeled_dir and Path(labeled_dir).exists():
        lab = Path(labeled_dir)
        print(f"\nLabeled dataset ({lab}):")

        # Read actual class names from Roboflow export's data.yaml
        yaml_candidates = list(lab.glob("*.yaml")) + list(lab.glob("data.yaml"))
        if yaml_candidates:
            src_names = _read_yaml_classes(yaml_candidates[0])
            print(f"  Source classes: {src_names}")
            remap = _build_remap_from_names(src_names, LABELED_CLASS_MAP)
            unmapped = [src_names[i] for i, v in remap.items() if v is None]
            if unmapped:
                print(f"  ⚠ Unmapped (skipped): {unmapped}")
                print(f"    Add them to LABELED_CLASS_MAP in this script.")
        else:
            print("  ⚠ No data.yaml found — using sequential ID offset (may be wrong!)")
            remap = {i: CLASS_INDEX.get(n) for i, n in enumerate(
                list(LABELED_CLASS_MAP.keys())
            )}

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

    # ── Write unified dataset.yaml ────────────────────────────────────────────
    yaml_path = out / "dataset.yaml"
    yaml_path.write_text(
        f"# Full CoC dataset — {len(ALL_CLASSES)} classes, {total} images\n"
        f"# Sources: HuggingFace public + Roboflow Universe + user-labeled\n\n"
        f"path: {out.resolve()}\n"
        f"train: train/images\n"
        f"val: val/images\n\n"
        f"nc: {len(ALL_CLASSES)}\n"
        f"names: {ALL_CLASSES}\n"
    )

    print(f"\n{'='*60}")
    print(f"Merged {total} images → {out}/")
    print(f"Classes: {len(ALL_CLASSES)} total")
    print(f"Config:  {yaml_path}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Merge all CoC training datasets")
    p.add_argument("--public",   default=None, help="HuggingFace public dataset dir")
    p.add_argument("--roboflow", default=None, help="Remapped Roboflow datasets dir")
    p.add_argument("--labeled",  default=None, help="User-labeled Roboflow export dir")
    p.add_argument("--output",   default="datasets/full", help="Output dir")
    args = p.parse_args()

    if not any([args.public, args.roboflow, args.labeled]):
        p.error("Provide at least one of --public, --roboflow, or --labeled")

    merge(args.public, args.roboflow, args.labeled, args.output)
