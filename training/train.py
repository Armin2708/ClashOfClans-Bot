#!/usr/bin/env python3
"""
Fine-tune YOLOv11n on a Clash of Clans dataset.

Starts from the COCO-pretrained YOLOv11n weights, fine-tunes on the
provided dataset, and copies the best checkpoint to models/coc.pt.

Usage:
    # Baseline (public buildings only, 16 classes):
    python training/train.py --data datasets/public/dataset.yaml --epochs 50

    # Full model (all classes including UI buttons):
    python training/train.py --data datasets/full/dataset.yaml --epochs 100

    # Resume from last checkpoint:
    python training/train.py --data datasets/full/dataset.yaml --resume
"""

import argparse
import shutil
from pathlib import Path


def train(
    data_yaml: str,
    epochs: int = 50,
    model_size: str = "n",
    resume: bool = False,
    batch: int = 16,
    imgsz: int = 640,
) -> None:
    from ultralytics import YOLO

    last_ckpt = Path("runs/detect/coc/weights/last.pt")
    if resume and last_ckpt.exists():
        print(f"Resuming from {last_ckpt}")
        model = YOLO(str(last_ckpt))
    else:
        base = f"yolo11{model_size}.pt"
        print(f"Starting from {base} (COCO-pretrained)")
        model = YOLO(base)

    model.train(
        data=data_yaml,
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        name="coc",
        project="runs/detect",
        patience=20,
        save=True,
        plots=True,
        exist_ok=True,
    )

    best = Path("runs/detect/coc/weights/best.pt")
    if best.exists():
        Path("models").mkdir(exist_ok=True)
        dest = Path("models/coc.pt")
        shutil.copy(best, dest)
        print(f"\nBest weights → {dest}")
    else:
        print("WARNING: best.pt not found — check runs/detect/coc/weights/")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--data", default="datasets/public/dataset.yaml")
    p.add_argument("--epochs", type=int, default=50)
    p.add_argument("--model", default="n", choices=["n", "s", "m"],
                   help="YOLOv11 size: n=nano, s=small, m=medium")
    p.add_argument("--batch", type=int, default=16)
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--resume", action="store_true")
    args = p.parse_args()
    train(args.data, args.epochs, args.model, args.resume, args.batch, args.imgsz)
