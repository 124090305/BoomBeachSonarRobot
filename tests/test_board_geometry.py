from dataclasses import replace
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

import cv2
import numpy as np

from flows.board_geometry_flow import RuntimeBoardLocator
from flows.level_loop import create_level_state
from flows.sonar_page import SonarPageState
from sonar import SonarBoard
from sonar_config import GlobalBoardSyncConfig
from stop_control import StopRequestedError
from tests.test_board_recognition import scene, opened, hull
from vision.board_alignment import project
from vision.board_geometry import BoardGeometryError, locate_board
from vision.board_live import recognize_live_board
from vision.board_recognition import recognize_board


class BoardGeometryTests(unittest.TestCase):
    def test_mapping_reuses_existing_board_axes(self):
        ref, level = scene()
        geometry = locate_board(ref, ref, level)
        board = SonarBoard(level.grid_size, level.submarines)
        board.set_screen_quad(level.board_quad)
        for r in range(level.grid_size):
            for c in range(level.grid_size):
                self.assertEqual(geometry.screen_point(level, (r, c)), board.screen_point(r, c))

    def test_translation_scale_perspective_and_imperfect_return(self):
        ref, level = scene()
        transforms = [np.float32([[1, 0, 6], [0, 1, 5], [0, 0, 1]]),
                      np.float32([[1.02, .01, -15], [.005, 1.03, 14], [.00001, .00001, 1]])]
        for transform in transforms:
            with self.subTest(transform=transform.tolist()):
                moved = cv2.warpPerspective(ref, transform, ref.shape[1::-1], borderMode=cv2.BORDER_REFLECT)
                geometry = locate_board(ref, moved, level)
                expected = project(level.board_quad, transform)
                self.assertLess(np.linalg.norm(expected-geometry.current_quad, axis=1).max(), 3)

    def test_wrong_page_resolution_and_crop_rejected(self):
        ref, level = scene()
        for current in (np.zeros_like(ref), ref[:200], np.full_like(ref, 255)):
            with self.assertRaises(BoardGeometryError):
                locate_board(ref, current, level)

    def test_missing_outer_corner_does_not_alias_neighbor(self):
        ref, level = scene()
        cur = ref.copy()
        for cell in ((0, 4), (4, 0), (4, 4)):
            opened(cur, level, cell)
        geometry = locate_board(ref, cur, level)
        self.assertLess(np.linalg.norm(np.float32(level.board_quad)-geometry.current_quad, axis=1).max(), 2)

    def test_missing_outer_ring_is_not_a_smaller_board(self):
        ref, level = scene()
        cur = ref.copy()
        for r in range(5):
            for c in range(5):
                if r in (0, 4) or c in (0, 4):
                    opened(cur, level, (r, c))
        with self.assertRaises(BoardGeometryError):
            locate_board(ref, cur, level)

    def test_missing_entire_edge_cannot_shift_cell_number(self):
        for n in (5, 10):
            ref, level = scene(n=n)
            cur = ref.copy()
            for i in range(n):
                opened(cur, level, (n-1, i))
            with self.assertRaises(BoardGeometryError):
                locate_board(ref, cur, level)

    def test_miss_hit_sunk_survive_shifted_global_recognition(self):
        ref, level = scene()
        cur = ref.copy()
        opened(cur, level, (1, 1))
        hull(cur, level, [(2, 1), (2, 2), (2, 3)])
        transform = np.float32([[1, 0, -8], [0, 1, 25], [0, 0, 1]])
        moved = cv2.warpPerspective(cur, transform, ref.shape[1::-1], borderMode=cv2.BORDER_REFLECT)
        result = recognize_board(ref, moved, level_config=level, runtime_geometry=True)
        self.assertTrue(result.valid)
        self.assertEqual(result.counts['MISS'], 1)
        self.assertEqual(result.counts['SUNK'], 3)

    def test_debug_output(self):
        ref, level = scene()
        with tempfile.TemporaryDirectory() as output:
            locate_board(ref, ref, level, output_dir=output)
            self.assertTrue((Path(output)/'geometry.json').is_file())
            self.assertTrue((Path(output)/'coordinates.png').is_file())
        with tempfile.TemporaryDirectory() as output:
            result = recognize_board(ref, ref, level_config=level, runtime_geometry=True, output_dir=output)
            self.assertTrue(result.valid)
            self.assertTrue((Path(output)/'geometry'/'coordinates.png').is_file())

    def test_level_lifetimes_are_isolated(self):
        first, second = create_level_state(11), create_level_state(12)
        self.assertIsNot(first.board.runtime_locator, second.board.runtime_locator)
        self.assertIsNone(second.board.runtime_locator._reference)

    def test_target_obstruction_rejected(self):
        ref, level = scene()
        geometry = locate_board(ref, ref, level)
        with patch('vision.board_features.text_occlusion', return_value=np.full(ref.shape[:2], 255, np.uint8)):
            with self.assertRaises(BoardGeometryError):
                geometry.require_visible_target(ref, level, (2, 2))

    def test_stable_two_frames_publish_mapping_only(self):
        ref, level = scene()
        moved = cv2.warpAffine(ref, np.float32([[1, 0, 6], [0, 1, 5]]), ref.shape[1::-1])
        locator = RuntimeBoardLocator(level)
        locator._reference = ref
        board = SonarBoard(level.grid_size, level.submarines)
        states = board.snapshot().states
        adb = Mock(read_screenshot=Mock(return_value=moved))
        with patch('flows.board_geometry_flow.detect_sonar_page_state', return_value=SonarPageState.ACTIVITY_DETAIL):
            _, geometry, point = locator.prepare_target(adb, object(), board, (2, 2), first_image=moved)
        self.assertEqual(board.screen_point(2, 2), point)
        self.assertEqual(states, board.snapshot().states)
        self.assertEqual(adb.read_screenshot.call_count, 1)

    def test_moving_board_never_publishes_mapping(self):
        ref, level = scene()
        moved = cv2.warpAffine(ref, np.float32([[1, 0, 8], [0, 1, 5]]), ref.shape[1::-1])
        locator = RuntimeBoardLocator(level)
        locator._reference = ref
        board = SonarBoard(level.grid_size, level.submarines)
        original = board.snapshot()
        with patch('flows.board_geometry_flow.detect_sonar_page_state', return_value=SonarPageState.ACTIVITY_DETAIL):
            with self.assertRaises(BoardGeometryError):
                locator.prepare_target(Mock(read_screenshot=Mock(return_value=moved)), object(), board, (2, 2), first_image=ref)
        self.assertEqual(original, board.snapshot())

    def test_stop_before_publish(self):
        ref, level = scene()
        locator = RuntimeBoardLocator(level)
        locator._reference = ref
        stop = threading.Event()
        stop.set()
        adb = Mock()
        with self.assertRaises(StopRequestedError):
            locator.prepare_target(adb, object(), SonarBoard(5, (2,)), (2, 2), stop_event=stop)
        adb.read_screenshot.assert_not_called()

    def test_global_votes_also_require_stationary_coordinates(self):
        ref, level = scene()
        moved = cv2.warpAffine(ref, np.float32([[1, 0, 6], [0, 1, 5]]), ref.shape[1::-1])
        frames = iter([ref, moved, ref])
        result = recognize_live_board(lambda: next(frames), level_config=level, empty_reference=ref,
            live_config=GlobalBoardSyncConfig(frame_count=3, maximum_frame_count=3, frame_interval_seconds=0),
            runtime_geometry=True)
        self.assertFalse(result.stable)
        self.assertFalse(result.board_result.valid)


if __name__ == '__main__':
    unittest.main()
