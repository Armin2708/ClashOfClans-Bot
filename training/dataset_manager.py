"""YOLO dataset I/O for the active-learning labeling pipeline.

Manages datasets/labeled/ — saves annotations from the GUI, generates
dataset.yaml, and provides stats for the labeling panel.
"""

from __future__ import annotations

import random
import shutil
from pathlib import Path

import cv2

from training.generate.class_registry import ALL_CLASSES, CLASS_INDEX

_DEFAULT_DIR = Path("datasets/labeled")


class DatasetManager:
    """Read/write YOLO label files and manage the labeled dataset."""

    def __init__(self, base_dir: Path | str = _DEFAULT_DIR):
        self.base = Path(base_dir)
        self._ensure_dirs()

    def _ensure_dirs(self):
        for split in ("train", "val"):
            (self.base / split / "images").mkdir(parents=True, exist_ok=True)
            (self.base / split / "labels").mkdir(parents=True, exist_ok=True)

    def save_annotation(self, image_name: str, image_bgr, boxes: list[dict],
                        split: str = "train"):
        """Save an annotated image and its YOLO labels.

        boxes: list of {"class_name": str, "cx": float, "cy": float,
                        "nw": float, "nh": float}
              All coordinates are normalized [0, 1].
        """
        img_dir = self.base / split / "images"
        lbl_dir = self.base / split / "labels"

        stem = Path(image_name).stem
        img_path = img_dir / f"{stem}.jpg"
        lbl_path = lbl_dir / f"{stem}.txt"

        # Save image
        cv2.imwrite(str(img_path), image_bgr, [cv2.IMWRITE_JPEG_QUALITY, 95])

        # Save labels
        lines = []
        for box in boxes:
            cls_name = box["class_name"]
            if cls_name not in CLASS_INDEX:
                continue
            cls_id = CLASS_INDEX[cls_name]
            lines.append(
                f"{cls_id} {box['cx']:.6f} {box['cy']:.6f} "
                f"{box['nw']:.6f} {box['nh']:.6f}"
            )
        lbl_path.write_text("\n".join(lines))
        return img_path, lbl_path

    def load_annotation(self, image_name: str, split: str = "train") -> list[dict]:
        """Load existing YOLO labels for an image. Returns list of box dicts."""
        stem = Path(image_name).stem
        lbl_path = self.base / split / "labels" / f"{stem}.txt"
        if not lbl_path.exists():
            return []

        boxes = []
        for line in lbl_path.read_text().strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split()
            cls_id = int(parts[0])
            if cls_id < len(ALL_CLASSES):
                boxes.append({
                    "class_name": ALL_CLASSES[cls_id],
                    "cx": float(parts[1]),
                    "cy": float(parts[2]),
                    "nw": float(parts[3]),
                    "nh": float(parts[4]),
                })
        return boxes

    def generate_yaml(self) -> Path:
        """Write dataset.yaml with classes that actually have labeled data."""
        # Scan all label files to find used class IDs
        used_ids: set[int] = set()
        for split in ("train", "val"):
            lbl_dir = self.base / split / "labels"
            for lbl_file in lbl_dir.glob("*.txt"):
                for line in lbl_file.read_text().strip().split("\n"):
                    if line.strip():
                        used_ids.add(int(line.split()[0]))

        # Always include legacy aliases (0-15) for backward compat
        for i in range(min(16, len(ALL_CLASSES))):
            used_ids.add(i)

        yaml_path = self.base / "dataset.yaml"
        yaml_path.write_text(
            f"# Labeled CoC dataset (active learning)\n\n"
            f"path: {self.base.resolve()}\n"
            f"train: train/images\n"
            f"val: val/images\n\n"
            f"nc: {len(ALL_CLASSES)}\n"
            f"names: {ALL_CLASSES}\n"
        )
        return yaml_path

    def get_stats(self) -> dict:
        """Return image/box counts per split."""
        stats = {}
        for split in ("train", "val"):
            img_dir = self.base / split / "images"
            lbl_dir = self.base / split / "labels"
            n_images = len(list(img_dir.glob("*.jpg"))) + len(list(img_dir.glob("*.png")))
            n_boxes = 0
            for lbl in lbl_dir.glob("*.txt"):
                text = lbl.read_text().strip()
                if text:
                    n_boxes += len(text.split("\n"))
            stats[split] = {"images": n_images, "boxes": n_boxes}
        return stats

    def split_val(self, ratio: float = 0.15):
        """Move a random subset of train images to val/ for validation."""
        train_imgs = list((self.base / "train" / "images").glob("*.*"))
        n_val = max(1, int(len(train_imgs) * ratio))
        val_imgs = random.sample(train_imgs, min(n_val, len(train_imgs)))

        for img_path in val_imgs:
            stem = img_path.stem
            # Move image
            dst_img = self.base / "val" / "images" / img_path.name
            shutil.move(str(img_path), str(dst_img))
            # Move label
            lbl_src = self.base / "train" / "labels" / f"{stem}.txt"
            if lbl_src.exists():
                lbl_dst = self.base / "val" / "labels" / f"{stem}.txt"
                shutil.move(str(lbl_src), str(lbl_dst))

        return len(val_imgs)
