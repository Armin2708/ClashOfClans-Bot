"""Unit tests for bot/detector.py — mocks YOLO so no model file is needed."""
import numpy as np
import pytest
from unittest.mock import MagicMock, patch


def _make_frame(h=1440, w=2560):
    return np.zeros((h, w, 3), dtype=np.uint8)


def _mock_yolo_result(cls_id: int, cls_name: str, conf: float, xyxy: list):
    """Build a minimal mock YOLO result object."""
    mock_box = MagicMock()
    mock_box.cls = [cls_id]
    mock_box.conf = [conf]
    mock_box.xyxy = [np.array(xyxy, dtype=float)]

    mock_result = MagicMock()
    mock_result.boxes = [mock_box]
    mock_result.names = {cls_id: cls_name}
    return mock_result


class TestDetection:
    def test_center_midpoint(self):
        from bot.detector import Detection
        d = Detection(cls="btn_attack", conf=0.9, x1=100, y1=200, x2=200, y2=300)
        assert d.center == (150, 250)

    def test_area(self):
        from bot.detector import Detection
        d = Detection(cls="btn_attack", conf=0.9, x1=0, y1=0, x2=100, y2=50)
        assert d.area == 5000

    def test_bbox_tuple(self):
        from bot.detector import Detection
        d = Detection(cls="x", conf=0.5, x1=10, y1=20, x2=30, y2=40)
        assert d.bbox == (10, 20, 30, 40)


class TestDetectorPredict:
    def test_predict_returns_detection(self):
        from bot.detector import Detector, Detection

        mock_result = _mock_yolo_result(0, "btn_attack", 0.9, [100, 200, 200, 300])
        mock_model = MagicMock(return_value=[mock_result])
        mock_model.names = {0: "btn_attack"}

        with patch("bot.detector.YOLO", return_value=mock_model):
            detector = Detector("fake.pt", confidence=0.5)

        dets = detector.predict(_make_frame())
        assert len(dets) == 1
        assert dets[0].cls == "btn_attack"
        assert dets[0].conf == pytest.approx(0.9)
        assert dets[0].x1 == 100
        assert dets[0].y2 == 300

    def test_predict_empty_result(self):
        from bot.detector import Detector

        mock_result = MagicMock()
        mock_result.boxes = []
        mock_result.names = {}
        mock_model = MagicMock(return_value=[mock_result])

        with patch("bot.detector.YOLO", return_value=mock_model):
            detector = Detector("fake.pt")

        assert detector.predict(_make_frame()) == []

    def test_predict_multiple_detections(self):
        from bot.detector import Detector

        mock_result_combined = MagicMock()
        box1 = MagicMock()
        box1.cls = [0]; box1.conf = [0.9]; box1.xyxy = [np.array([0, 0, 100, 50])]
        box2 = MagicMock()
        box2.cls = [1]; box2.conf = [0.8]; box2.xyxy = [np.array([200, 200, 300, 250])]
        mock_result_combined.boxes = [box1, box2]
        mock_result_combined.names = {0: "btn_attack", 1: "btn_next_base"}
        mock_model = MagicMock(return_value=[mock_result_combined])

        with patch("bot.detector.YOLO", return_value=mock_model):
            detector = Detector("fake.pt")

        dets = detector.predict(_make_frame())
        assert len(dets) == 2
        assert {d.cls for d in dets} == {"btn_attack", "btn_next_base"}


class TestDetectorFind:
    def test_find_returns_highest_confidence(self):
        from bot.detector import Detector, Detection
        detector = Detector.__new__(Detector)
        detector._confidence = 0.5
        det_low = Detection("btn_attack", 0.6, 0, 0, 10, 10)
        det_high = Detection("btn_attack", 0.9, 50, 50, 60, 60)
        det_other = Detection("btn_next_base", 0.95, 100, 100, 110, 110)

        with patch.object(detector, "predict", return_value=[det_low, det_high, det_other]):
            result = detector.find(_make_frame(), "btn_attack")

        assert result is det_high

    def test_find_returns_none_when_absent(self):
        from bot.detector import Detector, Detection
        detector = Detector.__new__(Detector)
        det = Detection("btn_attack", 0.9, 0, 0, 10, 10)

        with patch.object(detector, "predict", return_value=[det]):
            result = detector.find(_make_frame(), "btn_next_base")

        assert result is None

    def test_find_any_returns_first_match(self):
        from bot.detector import Detector, Detection
        detector = Detector.__new__(Detector)
        det1 = Detection("btn_okay", 0.8, 0, 0, 10, 10)
        det2 = Detection("btn_close", 0.85, 50, 50, 60, 60)

        with patch.object(detector, "predict", return_value=[det1, det2]):
            result = detector.find_any(_make_frame(), "btn_close", "btn_okay", "btn_later")

        # Should return highest-conf among the matching classes
        assert result is det2

    def test_find_all_filters_by_class(self):
        from bot.detector import Detector, Detection
        detector = Detector.__new__(Detector)
        dets = [
            Detection("troop_slot", 0.9, 0, 0, 50, 50),
            Detection("troop_slot", 0.85, 60, 0, 110, 50),
            Detection("btn_attack", 0.9, 200, 200, 250, 250),
        ]

        with patch.object(detector, "predict", return_value=dets):
            result = detector.find_all(_make_frame(), "troop_slot")

        assert len(result) == 2
        assert all(d.cls == "troop_slot" for d in result)
