from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

import cv2
import numpy as np

from flows.board_drag_trial import BoardDragTrialError, BoardDragTrialConfig, measure_translation, plan_board_drag, run_board_drag_trial
from flows.sonar_page import SonarPageState
from stop_control import StopRequestedError
from tests.test_board_recognition import scene


class BoardDragTrialTests(unittest.TestCase):
    def setUp(self):
        self.image, level = scene()
        self.level = replace(level, empty_reference_path=Path("empty.png"))
        self.cfg = BoardDragTrialConfig(settle_seconds=0)

    def test_plan_is_outside_board_and_keeps_bottom_visible(self):
        plan = plan_board_drag(self.image, self.level, self.cfg)
        self.assertGreater(plan.start[0]-plan.corridor_radius, max(p[0] for p in self.level.board_quad))
        dy = plan.end[1]-plan.start[1]
        self.assertGreaterEqual(dy, self.cfg.minimum_displacement_px)
        self.assertLess(max(p[1] for p in self.level.board_quad)+dy, self.image.shape[0])

    def test_insufficient_bottom_space_rejected(self):
        level = replace(self.level, board_quad=tuple((x, y+50) for x, y in self.level.board_quad))
        with self.assertRaises(BoardDragTrialError):
            plan_board_drag(self.image, level, self.cfg)

    def test_non_water_corridor_rejected(self):
        image = self.image.copy()
        image[:, 560:] = 0
        with self.assertRaises(BoardDragTrialError):
            plan_board_drag(image, self.level, self.cfg)

    def test_translation_is_measured_and_formally_verified(self):
        shifted = cv2.warpAffine(self.image, np.float32([[1, 0, 0], [0, 1, 40]]), self.image.shape[1::-1])
        result = measure_translation(self.image, shifted, self.level, self.cfg)
        self.assertAlmostEqual(result["dy"], 40, delta=2)
        self.assertAlmostEqual(result["dx"], 0, delta=2)

    def test_static_board_has_zero_motion(self):
        result = measure_translation(self.image, self.image, self.level, self.cfg)
        self.assertAlmostEqual(result["dy"], 0, delta=.1)

    def test_blank_frame_cannot_verify_motion(self):
        with self.assertRaises(BoardDragTrialError):
            measure_translation(self.image, np.zeros_like(self.image), self.level, self.cfg)

    def trial(self, execute=False, measurements=None, stop=None, page_state=SonarPageState.ACTIVITY_DETAIL):
        adb = Mock(read_screenshot=Mock(return_value=self.image))
        page = Mock()
        if stop is not None:
            page.swipe.side_effect = lambda *a, **k: stop.set()
        with (tempfile.TemporaryDirectory() as directory,
              patch("flows.board_drag_trial.read_image", return_value=self.image),
              patch("flows.board_drag_trial.detect_sonar_page_state", return_value=page_state),
              patch("flows.board_drag_trial.measure_translation", side_effect=measurements) as measure):
            try:
                result = run_board_drag_trial(adb, page, self.level, Path(directory)/"trial",
                    execute=execute, cfg=self.cfg, stop_event=stop)
                return result, page
            finally:
                self.page = page

    def test_dry_run_never_sends_gesture(self):
        result, page = self.trial()
        self.assertFalse(result["executed"])
        page.swipe.assert_not_called()

    def test_wrong_page_never_sends_gesture(self):
        with self.assertRaises(BoardDragTrialError):
            self.trial(execute=True, page_state=SonarPageState.HOME)
        self.page.swipe.assert_not_called()

    def test_no_effect_does_not_send_reverse_gesture(self):
        result, page = self.trial(True, [{"dx": 0, "dy": 0}])
        self.assertTrue(result["restored"])
        self.assertEqual(page.swipe.call_count, 1)

    def test_motion_followed_by_verified_return(self):
        result, page = self.trial(True, [{"dx": 0, "dy": 40}]*2 + [{"dx": 0, "dy": 0}])
        self.assertTrue(result["restored"])
        self.assertEqual(page.swipe.call_count, 2)

    def test_failed_return_blocks_completion(self):
        with self.assertRaisesRegex(BoardDragTrialError, "恢复原位"):
            self.trial(True, [{"dx": 0, "dy": 40}]*3)

    def test_stop_during_gesture_still_verifies_return(self):
        stop = threading.Event()
        with self.assertRaises(StopRequestedError):
            self.trial(True, [{"dx": 0, "dy": 40}]*2 + [{"dx": 0, "dy": 0}], stop)
        self.assertEqual(self.page.swipe.call_count, 2)


if __name__ == "__main__":
    unittest.main()
