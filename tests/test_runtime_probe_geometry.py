"""不连接设备：验证正式单发、补帧和重启重放使用同一坐标契约。"""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import cv2
import numpy as np

from flows.auto_probe_flow import AutoProbeProgress, _complete_recognition_and_sync, _replay_recognized_hit
from flows.auto_probe_loop import _run_once_with_restart_fallback
from flows.board_geometry_flow import RuntimeBoardLocator
from flows.probe_flow import ProbeContext, prepare_probe_once
from flows.sonar_page import SonarPageState
from sonar import SonarBoard, CheckerboardHuntStrategy, CellState
from tests.test_board_recognition import scene
from tests.test_probe_stop_points import ProbePage, hit_recognition
from vision.board_geometry import BoardGeometryError, locate_board
from vision.board_debug import write_image
from vision.image_match import read_image


class RuntimeProbeGeometryTests(unittest.TestCase):
    def setup_scene(self):
        ref, level = scene()
        moved = cv2.warpAffine(ref, np.float32([[1, 0, 6], [0, 1, 5]]), ref.shape[1::-1])
        board = SonarBoard(level.grid_size, level.submarines)
        board.set_screen_quad(level.board_quad)
        locator = RuntimeBoardLocator(level)
        locator._reference = ref
        board.runtime_locator = locator
        strategy = CheckerboardHuntStrategy(board)
        cell = strategy.choose_next_cell()
        return ref, moved, level, board, strategy, cell

    def test_formal_click_uses_live_point_and_after_has_own_geometry(self):
        ref, moved, level, board, strategy, cell = self.setup_scene()
        images = iter([moved, ref])
        def take(path):
            write_image(path, next(images))
            return path
        adb = Mock(take_screenshot=take, read_image=read_image, read_screenshot=Mock(return_value=moved))
        page = ProbePage()
        page.click_point = Mock(side_effect=page.click_point)
        states = board.snapshot().states
        with (tempfile.TemporaryDirectory() as directory,
              patch('flows.probe_flow.wait_activity_detail_ready', return_value=True),
              patch('flows.probe_flow.reenter_activity_for_probe'),
              patch('flows.board_geometry_flow.detect_sonar_page_state', return_value=SonarPageState.ACTIVITY_DETAIL)):
            context = prepare_probe_once(adb, page, board, strategy, output_dir=directory)
        expected = locate_board(ref, moved, level).screen_point(level, cell)
        self.assertEqual(page.click_point.call_args.args, expected)
        self.assertEqual(context.screen_point, expected)
        self.assertNotEqual(context.screen_point, context.recognition_center)
        self.assertLess(context.after_geometry.alignment.max_shift_px, 1)
        self.assertEqual(states, board.snapshot().states)

    def test_failed_location_never_clicks_or_reports(self):
        ref, moved, level, board, strategy, cell = self.setup_scene()
        board.runtime_locator.prepare_target = Mock(side_effect=BoardGeometryError('定位失败'))
        page, adb = Mock(), Mock()
        original = board.snapshot()
        with (tempfile.TemporaryDirectory() as directory,
              patch('flows.probe_flow.wait_activity_detail_ready', return_value=True)):
            with self.assertRaises(BoardGeometryError):
                prepare_probe_once(adb, page, board, strategy, output_dir=directory)
        page.click_point.assert_not_called()
        page.click_template.assert_not_called()
        self.assertEqual(board.snapshot(), original)

    def test_recognition_and_extra_frame_use_reference_center(self):
        ref, moved, level, board, strategy, cell = self.setup_scene()
        locator = board.runtime_locator
        context = ProbeContext(cell, (999, 999), Path('before'), Path('after'),
            recognition_center=locator.reference_point(cell), runtime_locator=locator,
            before_geometry=locate_board(ref, moved, level), after_geometry=locate_board(ref, ref, level))
        adb = Mock(read_image=Mock(side_effect=[moved, ref]), read_screenshot=Mock(return_value=moved))
        progress = AutoProbeProgress()
        with (patch('flows.auto_probe_flow.classify_diamond_hit', return_value=hit_recognition()) as single,
              patch('flows.auto_probe_flow.needs_multiframe_confirmation', return_value=True),
              patch('flows.auto_probe_flow.classify_diamond_hit_multiframe', return_value=hit_recognition()) as multi):
            _complete_recognition_and_sync(adb, strategy, context, progress,
                hit_config=None, recognition_index=0, on_result_committed=None)
        self.assertEqual(single.call_args.kwargs['center'], context.recognition_center)
        self.assertEqual(multi.call_args.kwargs['center'], context.recognition_center)
        self.assertLess(np.abs(single.call_args.kwargs['before_screenshot'][100:400, 100:550].astype(float)-ref[100:400, 100:550]).mean(), 1)
        self.assertTrue(progress.result_committed)
        self.assertEqual(board.get_state(*cell), CellState.HIT)

    def test_hit_replay_relocalizes_instead_of_reusing_old_click(self):
        ref, moved, level, board, strategy, cell = self.setup_scene()
        locator = board.runtime_locator
        locator.prepare_target = Mock(return_value=(ref, object(), (456, 234)))
        context = ProbeContext(cell, (100, 100), Path('a'), Path('b'), runtime_locator=locator)
        page = Mock()
        _replay_recognized_hit(page, context, adb=object(), board=board)
        self.assertEqual(page.click_point.call_args.args, (456, 234))
        locator.prepare_target.assert_called_once()

    def test_geometry_failure_bypasses_restart_and_network_actions(self):
        with (patch('flows.auto_probe_loop.run_auto_probe_once', side_effect=BoardGeometryError('坐标不可靠')),
              patch('flows.auto_probe_loop.restart_auto_probe_once') as restart):
            network = Mock()
            with self.assertRaises(BoardGeometryError):
                _run_once_with_restart_fallback(object(), object(), network, object(), object(),
                    game=object(), hit_config=None, output_dir=None, recognition_index=0,
                    stop_event=None, on_result_committed=None)
        restart.assert_not_called()
        self.assertFalse(network.mock_calls)


if __name__ == '__main__':
    unittest.main()
