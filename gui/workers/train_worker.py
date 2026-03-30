"""Background QThread worker for YOLO model training.

Follows the same pattern as gui/bot_worker.py — signals for progress,
threading.Event for stop support.
"""

from __future__ import annotations

import shutil
import threading
from pathlib import Path

from PySide6.QtCore import QThread, Signal


class TrainWorker(QThread):
    """Runs YOLO training in a background thread."""

    progress_updated = Signal(int, int, float, float)  # epoch, total, loss, mAP
    training_finished = Signal(str)                      # path to best.pt
    error_occurred = Signal(str)

    def __init__(self, data_yaml: str, epochs: int = 50, batch: int = 16,
                 resume: bool = False, model_size: str = "n"):
        super().__init__()
        self._data_yaml = data_yaml
        self._epochs = epochs
        self._batch = batch
        self._resume = resume
        self._model_size = model_size
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def run(self):
        try:
            from ultralytics import YOLO

            # Choose starting point
            last_ckpt = Path("runs/coc/weights/last.pt")
            if self._resume and last_ckpt.exists():
                model = YOLO(str(last_ckpt))
            else:
                model = YOLO(f"yolo11{self._model_size}.pt")

            # Register progress callback
            def on_epoch_end(trainer):
                epoch = trainer.epoch + 1
                total = trainer.epochs
                loss = float(trainer.loss) if trainer.loss is not None else 0.0
                metrics = trainer.metrics or {}
                mAP = float(metrics.get("metrics/mAP50(B)", 0.0))
                self.progress_updated.emit(epoch, total, loss, mAP)

                if self._stop_event.is_set():
                    raise KeyboardInterrupt("Training stopped by user")

            model.add_callback("on_train_epoch_end", on_epoch_end)

            # Train
            model.train(
                data=self._data_yaml,
                epochs=self._epochs,
                batch=self._batch,
                imgsz=640,
                project="runs",
                name="coc",
                exist_ok=True,
                patience=20,
                verbose=False,
            )

            # Copy best weights to data/models/coc.pt
            best_pt = Path("runs/coc/weights/best.pt")
            dst = Path("data/models/coc.pt")
            dst.parent.mkdir(exist_ok=True)
            if best_pt.exists():
                shutil.copy(str(best_pt), str(dst))

            self.training_finished.emit(str(dst))

        except KeyboardInterrupt:
            self.training_finished.emit("")
        except Exception as e:
            self.error_occurred.emit(str(e))
