"""
Tests for the YOLO-backed bot/vision.py public API.
All tests mock bot.vision._get_detector so no model file is needed.
"""
import numpy as np
import pytest
from unittest.mock import MagicMock, patch
from bot.state_machine import GameState


def _make_frame(h=1440, w=2560):
    return np.zeros((h, w, 3), dtype=np.uint8)


def _mock_detector(detected_classes: list[str], center: tuple[int, int] = (150, 250)):
    """Return a mock Detector whose predict() returns one detection per class."""
    from bot.detector import Detection
    x1, y1 = center[0] - 50, center[1] - 25
    x2, y2 = center[0] + 50, center[1] + 25
    dets = [Detection(cls=c, conf=0.9, x1=x1, y1=y1, x2=x2, y2=y2)
            for c in detected_classes]

    mock = MagicMock()
    mock.predict.return_value = dets
    mock.find.side_effect = lambda frame, cls: next(
        (d for d in dets if d.cls == cls), None)
    mock.find_any.side_effect = lambda frame, *classes: (
        max((d for d in dets if d.cls in classes), key=lambda d: d.conf, default=None))
    mock.find_all.side_effect = lambda frame, cls: [d for d in dets if d.cls == cls]
    return mock


class TestDetectScreenState:
    def _check(self, classes, expected_state):
        from bot.vision import detect_screen_state
        with patch("bot.vision._get_detector", return_value=_mock_detector(classes)):
            assert detect_screen_state(_make_frame()) == expected_state

    def test_results_hud(self):
        self._check(["hud_results"], GameState.RESULTS)

    def test_results_return_home_button(self):
        self._check(["btn_return_home"], GameState.RESULTS)

    def test_scouting_next_base(self):
        self._check(["btn_next_base"], GameState.SCOUTING)

    def test_scouting_end_battle_plus_loot(self):
        self._check(["btn_end_battle", "loot_gold"], GameState.SCOUTING)

    def test_scouting_end_battle_plus_elixir(self):
        self._check(["btn_end_battle", "loot_elixir"], GameState.SCOUTING)

    def test_battle_active_end_battle_no_loot(self):
        self._check(["btn_end_battle"], GameState.BATTLE_ACTIVE)

    def test_army_start_battle(self):
        self._check(["btn_start_battle"], GameState.ARMY)

    def test_attack_menu_find_match(self):
        self._check(["btn_find_match"], GameState.ATTACK_MENU)

    def test_village_attack_button(self):
        self._check(["btn_attack"], GameState.VILLAGE)

    def test_village_hud(self):
        self._check(["hud_village"], GameState.VILLAGE)

    def test_unknown_no_detections(self):
        self._check([], GameState.UNKNOWN)

    def test_results_takes_priority_over_end_battle(self):
        # If both hud_results and btn_end_battle visible, should be RESULTS
        self._check(["hud_results", "btn_end_battle"], GameState.RESULTS)


class TestFindButton:
    def test_returns_center_for_known_button(self):
        from bot.vision import find_button
        mock_d = _mock_detector(["btn_attack"], center=(300, 400))
        with patch("bot.vision._get_detector", return_value=mock_d):
            result = find_button(_make_frame(), "attack_button")
        assert result == (300, 400)

    def test_returns_none_when_button_not_detected(self):
        from bot.vision import find_button
        mock_d = _mock_detector([])
        with patch("bot.vision._get_detector", return_value=mock_d):
            result = find_button(_make_frame(), "attack_button")
        assert result is None

    def test_returns_none_for_unknown_button_name(self):
        from bot.vision import find_button
        mock_d = _mock_detector(["btn_attack"])
        with patch("bot.vision._get_detector", return_value=mock_d):
            result = find_button(_make_frame(), "totally_unknown_button")
        assert result is None

    def test_next_base_maps_to_btn_next_base(self):
        from bot.vision import find_button
        mock_d = _mock_detector(["btn_next_base"], center=(2300, 1200))
        with patch("bot.vision._get_detector", return_value=mock_d):
            result = find_button(_make_frame(), "next_base")
        assert result == (2300, 1200)


class TestFindPopup:
    def test_finds_close_x(self):
        from bot.vision import find_popup
        mock_d = _mock_detector(["btn_close"], center=(100, 100))
        with patch("bot.vision._get_detector", return_value=mock_d):
            result = find_popup(_make_frame())
        assert result == (100, 100)

    def test_finds_okay(self):
        from bot.vision import find_popup
        mock_d = _mock_detector(["btn_okay"], center=(200, 300))
        with patch("bot.vision._get_detector", return_value=mock_d):
            result = find_popup(_make_frame())
        assert result == (200, 300)

    def test_returns_none_when_no_popup(self):
        from bot.vision import find_popup
        mock_d = _mock_detector([])
        with patch("bot.vision._get_detector", return_value=mock_d):
            result = find_popup(_make_frame())
        assert result is None


class TestGetTroopSlots:
    def test_returns_centers_sorted_by_x(self):
        from bot.vision import get_troop_slots
        from bot.detector import Detection
        dets = [
            Detection("troop_slot", 0.9, 200, 1300, 250, 1350),
            Detection("troop_slot", 0.85, 100, 1300, 150, 1350),
            Detection("troop_slot", 0.8, 300, 1300, 350, 1350),
        ]
        mock_d = MagicMock()
        mock_d.find_all.return_value = dets
        with patch("bot.vision._get_detector", return_value=mock_d):
            slots = get_troop_slots(_make_frame())
        xs = [s[0] for s in slots]
        assert xs == sorted(xs)
        assert len(slots) == 3

    def test_returns_empty_when_no_slots(self):
        from bot.vision import get_troop_slots
        mock_d = MagicMock()
        mock_d.find_all.return_value = []
        with patch("bot.vision._get_detector", return_value=mock_d):
            assert get_troop_slots(_make_frame()) == []


class TestGetDeployCorner:
    def test_returns_correct_number_of_points(self):
        from bot.vision import get_deploy_corner
        import bot.config as config
        points = get_deploy_corner(_make_frame())
        assert len(points) == config.DEPLOY_NUM_POINTS

    def test_points_are_within_frame_bounds(self):
        from bot.vision import get_deploy_corner
        frame = _make_frame(h=1440, w=2560)
        for x, y in get_deploy_corner(frame):
            assert 0 <= x <= 2560
            assert 0 <= y <= 1440


class TestValidateCriticalTemplates:
    def test_passes_when_detector_loads(self):
        from bot.vision import validate_critical_templates
        mock_d = MagicMock()
        with patch("bot.vision._get_detector", return_value=mock_d):
            validate_critical_templates()  # should not raise

    def test_raises_when_detector_fails(self):
        from bot.vision import validate_critical_templates
        with patch("bot.vision._get_detector", side_effect=FileNotFoundError("model missing")):
            with pytest.raises(FileNotFoundError, match="model"):
                validate_critical_templates()


