#!/usr/bin/env python3
"""
Merge the public building dataset (16 classes) with the manually labeled
full dataset (40 classes: buildings + UI) into a unified dataset.

The public dataset uses class IDs 0-15.
The labeled dataset uses class IDs 0-39 (Roboflow resets to 0).
This script remaps labeled IDs -> 16-55 so they don't conflict.

Usage:
    python training/merge_datasets.py \
        --public datasets/public \
        --labeled datasets/labeled \
        --output datasets/full
"""

import shutil
import argparse
from pathlib import Path


PUBLIC_CLASSES = [
    "ad", "airsweeper", "bombtower", "canon", "clancastle",
    "eagle", "inferno", "kingpad", "mortar", "queenpad",
    "rcpad", "scattershot", "th13", "wardenpad", "wizztower", "xbow",
]

# Must match the class order used in Roboflow when labeling.
# Check datasets/labeled/data.yaml for the exact order Roboflow assigned.
#
# DEFENSES (not in public dataset):
#   archer_tower, hidden_tesla, giga_tesla, monolith
# RESOURCES:
#   gold_mine, elixir_collector, dark_elixir_drill
#   gold_storage, elixir_storage, dark_elixir_storage
# ARMY:
#   barracks, dark_barracks, army_camp, spell_factory,
#   dark_spell_factory, laboratory, workshop, pet_house,
#   blacksmith, hero_hall
# STRUCTURES:
#   town_hall, builder_hut
# UI BUTTONS + HUD:
#   btn_*, hud_*, loot_*, troop_slot
LABELED_CLASSES = [
    # ── Defenses not covered by public dataset ──────────────────
    "archer_tower",
    "hidden_tesla",
    "giga_tesla",
    "monolith",
    # ── Resource buildings ───────────────────────────────────────
    "gold_mine",
    "elixir_collector",
    "dark_elixir_drill",
    "gold_storage",
    "elixir_storage",
    "dark_elixir_storage",
    # ── Army buildings ───────────────────────────────────────────
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
    # ── Other structures ─────────────────────────────────────────
    "town_hall",
    "builder_hut",
    # ── UI buttons ───────────────────────────────────────────────
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
    # ── HUD overlays ─────────────────────────────────────────────
    "hud_village",
    "hud_scouting",
    "hud_results",
    "hud_army",
    # ── Loot / troop UI ──────────────────────────────────────────
    "loot_gold",
    "loot_elixir",
    "loot_gem",
    "troop_slot",
]

ALL_CLASSES = PUBLIC_CLASSES + LABELED_CLASSES


def _copy_split(src_img: Path, src_lbl: Path, dst_img: Path, dst_lbl: Path,
                prefix: str, class_offset: int) -> int:
    """Copy images and labels (with class ID remapping) to destination."""
    if not src_img.exists():
        return 0
    count = 0
    for img_path in sorted(src_img.glob("*.jpg")):
        shutil.copy(img_path, dst_img / f"{prefix}_{img_path.name}")
        lbl_path = src_lbl / img_path.with_suffix(".txt").name
        dst_lbl_path = dst_lbl / f"{prefix}_{lbl_path.name}"
        if lbl_path.exists():
            lines = [l for l in lbl_path.read_text().strip().split("\n") if l.strip()]
            remapped = []
            for line in lines:
                parts = line.split()
                parts[0] = str(int(parts[0]) + class_offset)
                remapped.append(" ".join(parts))
            dst_lbl_path.write_text("\n".join(remapped))
        else:
            dst_lbl_path.write_text("")
        count += 1
    return count


def merge(public_dir: str, labeled_dir: str, output_dir: str) -> None:
    pub = Path(public_dir)
    lab = Path(labeled_dir)
    out = Path(output_dir)

    for split in ("train", "val"):
        (out / split / "images").mkdir(parents=True, exist_ok=True)
        (out / split / "labels").mkdir(parents=True, exist_ok=True)

    total = 0

    # Public dataset: class IDs 0-15, no remapping needed
    # train split + test split both go to train (small dataset — maximize training data)
    for src_split, dst_split in [("train", "train"), ("test", "train")]:
        n = _copy_split(
            pub / src_split / "images", pub / src_split / "labels",
            out / dst_split / "images", out / dst_split / "labels",
            prefix=f"pub_{src_split}", class_offset=0,
        )
        total += n
    n = _copy_split(
        pub / "validation" / "images", pub / "validation" / "labels",
        out / "val" / "images", out / "val" / "labels",
        prefix="pub_val", class_offset=0,
    )
    total += n

    # Labeled dataset: Roboflow class IDs start at 0, remap to 16+
    labeled_offset = len(PUBLIC_CLASSES)
    for src_split, dst_split in [("train", "train"), ("test", "train")]:
        n = _copy_split(
            lab / src_split / "images", lab / src_split / "labels",
            out / dst_split / "images", out / dst_split / "labels",
            prefix=f"lab_{src_split}", class_offset=labeled_offset,
        )
        total += n
    for src_split in ("valid", "validation"):
        src_img = lab / src_split / "images"
        if src_img.exists():
            n = _copy_split(
                src_img, lab / src_split / "labels",
                out / "val" / "images", out / "val" / "labels",
                prefix="lab_val", class_offset=labeled_offset,
            )
            total += n
            break

    # Write unified dataset.yaml
    yaml_path = out / "dataset.yaml"
    yaml_path.write_text(
        f"# Full CoC dataset: public buildings (16 classes) + labeled UI (18 classes)\n\n"
        f"path: {out.resolve()}\n"
        f"train: train/images\n"
        f"val: val/images\n\n"
        f"nc: {len(ALL_CLASSES)}\n"
        f"names: {ALL_CLASSES}\n"
    )

    print(f"Merged {total} images -> {out}/")
    print(f"Classes ({len(ALL_CLASSES)}): {ALL_CLASSES[:5]}... +{len(ALL_CLASSES) - 5} more")
    print(f"Config: {yaml_path}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--public", default="datasets/public")
    p.add_argument("--labeled", default="datasets/labeled")
    p.add_argument("--output", default="datasets/full")
    args = p.parse_args()
    merge(args.public, args.labeled, args.output)
