#!/usr/bin/env python3
"""
Download the public Clash of Clans dataset from HuggingFace and convert
from COCO JSON format to YOLOv11 TXT format.

Source: keremberke/clash-of-clans-object-detection (CC BY 4.0, 125 images)
16 classes: buildings and defensive structures.

Usage:
    python training/download_dataset.py
    python training/download_dataset.py --output datasets/public
"""

import argparse
from pathlib import Path


# Class list from the HuggingFace dataset (index = YOLO class ID)
PUBLIC_CLASSES = [
    "ad", "airsweeper", "bombtower", "canon", "clancastle",
    "eagle", "inferno", "kingpad", "mortar", "queenpad",
    "rcpad", "scattershot", "th13", "wardenpad", "wizztower", "xbow",
]


def download_and_convert(output_dir: str = "datasets/public") -> None:
    from datasets import load_dataset

    output = Path(output_dir)
    for split in ("train", "validation", "test"):
        (output / split / "images").mkdir(parents=True, exist_ok=True)
        (output / split / "labels").mkdir(parents=True, exist_ok=True)

    print("Downloading from HuggingFace (keremberke/clash-of-clans-object-detection)...")
    ds = load_dataset("keremberke/clash-of-clans-object-detection", name="full")

    split_map = {"train": "train", "validation": "validation", "test": "test"}
    for hf_split, out_split in split_map.items():
        split_data = ds[hf_split]
        print(f"  Converting {hf_split} ({len(split_data)} images)...")

        for idx, example in enumerate(split_data):
            img = example["image"]  # PIL Image
            w, h = img.size

            img_path = output / out_split / "images" / f"{idx:05d}.jpg"
            img.save(str(img_path), quality=95)

            annotations = example["objects"]
            lines = []
            for bbox, cat_id in zip(annotations["bbox"], annotations["category"]):
                # COCO bbox: [x_topleft, y_topleft, width, height] in pixels
                bx, by, bw, bh = bbox
                cx = (bx + bw / 2) / w
                cy = (by + bh / 2) / h
                nw = bw / w
                nh = bh / h
                lines.append(f"{cat_id} {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}")

            lbl_path = output / out_split / "labels" / f"{idx:05d}.txt"
            lbl_path.write_text("\n".join(lines))

    # Write dataset.yaml for training
    yaml_path = output / "dataset.yaml"
    yaml_path.write_text(
        f"# Public CoC baseline dataset (buildings + defenses only)\n"
        f"# Source: keremberke/clash-of-clans-object-detection (HuggingFace, CC BY 4.0)\n\n"
        f"path: {output.resolve()}\n"
        f"train: train/images\n"
        f"val: validation/images\n"
        f"test: test/images\n\n"
        f"nc: {len(PUBLIC_CLASSES)}\n"
        f"names: {PUBLIC_CLASSES}\n"
    )

    total = sum(len(ds[s]) for s in split_map)
    print(f"\nDataset ready at {output}/")
    print(f"  Total: {total} images, {len(PUBLIC_CLASSES)} classes")
    print(f"  Classes: {PUBLIC_CLASSES}")
    print(f"  Config:  {yaml_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download public CoC YOLO dataset")
    parser.add_argument("--output", default="datasets/public",
                        help="Output directory (default: datasets/public)")
    args = parser.parse_args()
    download_and_convert(args.output)
