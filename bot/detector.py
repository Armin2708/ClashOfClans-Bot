"""
YOLO-based game element detector.

Wraps Ultralytics YOLOv11 inference with a minimal interface:
  Detector.predict(frame)  → list[Detection]
  Detector.find(frame, cls)  → Detection | None
  Detector.find_any(frame, *classes)  → Detection | None
  Detector.find_all(frame, cls)  → list[Detection]
"""

import logging
import numpy as np
from dataclasses import dataclass

logger = logging.getLogger("coc.detector")

# Imported at module level so tests can patch it cleanly
from ultralytics import YOLO


@dataclass
class Detection:
    cls: str
    conf: float
    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def center(self) -> tuple[int, int]:
        return ((self.x1 + self.x2) // 2, (self.y1 + self.y2) // 2)

    @property
    def area(self) -> int:
        return (self.x2 - self.x1) * (self.y2 - self.y1)

    @property
    def bbox(self) -> tuple[int, int, int, int]:
        return (self.x1, self.y1, self.x2, self.y2)


class Detector:
    """Load a YOLOv11 model and run inference on game screenshots."""

    def __init__(self, model_path: str, confidence: float = 0.45):
        logger.info("Loading YOLO model from %s", model_path)
        self._model = YOLO(model_path)
        self._confidence = confidence
        logger.info(
            "Model loaded — %d classes, first 5: %s",
            len(self._model.names),
            list(self._model.names.values())[:5],
        )

    def predict(self, frame: np.ndarray) -> list[Detection]:
        """Run inference on a BGR frame. Returns all detections above confidence."""
        results = self._model(frame, conf=self._confidence, verbose=False)
        detections: list[Detection] = []
        for r in results:
            if r.boxes is None:
                continue
            names = r.names
            for box in r.boxes:
                cls_id = int(box.cls[0])
                detections.append(Detection(
                    cls=names[cls_id],
                    conf=float(box.conf[0]),
                    x1=int(box.xyxy[0][0]),
                    y1=int(box.xyxy[0][1]),
                    x2=int(box.xyxy[0][2]),
                    y2=int(box.xyxy[0][3]),
                ))
        return detections

    def find(self, frame: np.ndarray, cls: str) -> "Detection | None":
        """Return the highest-confidence detection of a given class, or None."""
        matches = [d for d in self.predict(frame) if d.cls == cls]
        return max(matches, key=lambda d: d.conf) if matches else None

    def find_any(self, frame: np.ndarray, *classes: str) -> "Detection | None":
        """Return the highest-confidence detection among multiple classes."""
        matches = [d for d in self.predict(frame) if d.cls in classes]
        return max(matches, key=lambda d: d.conf) if matches else None

    def find_all(self, frame: np.ndarray, cls: str) -> list[Detection]:
        """Return all detections of a given class."""
        return [d for d in self.predict(frame) if d.cls == cls]
