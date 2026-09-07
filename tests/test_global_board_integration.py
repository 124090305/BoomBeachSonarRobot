from __future__ import annotations

import queue
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from flows.board_sync_flow import BoardSyncApplyResult
from sonar import CellState, CheckerboardHuntStrategy, ManualEditSession, SonarBoard
from tests.test_board_recognition import opened, scene
from tests.test_board_sync_flow import live_result
from tests.test_button_state import FakeButton, FakeVar, toggle_labels
from ui.auto_loop_bridge import AutoProbeLoopBridge
from ui.button_state import ButtonLabels, ButtonState, StatefulButton
from ui.gui_app import BoomBeachSonarApp
from vision.board_recognition import recognize_board


class HoldingThread:
    target = None

    def __init__(self, *, target, name=None, daemon=True):
        HoldingThread.target = target

    def start(self):
        pass


class GlobalBoardUiTests(unittest.TestCase):
    def build_shell(self):
        app = object.__new__(BoomBeachSonarApp)
        board = SonarBoard(5, (2, 3))
        strategy = CheckerboardHuntStrategy(board)
        app._runtime = SimpleNamespace(
            adb=object(), page=object(), current_level=3,
            control_lock=threading.Lock(), board=board, strategy=strategy,
        )
        app.sonar_board = board
        app.sonar_strategy = strategy
        app._manual_session = ManualEditSession(board)
        app._auto_loop_bridge = SimpleNamespace(running=False, mark_manual_applied=Mock())
        app._closing = False
        app._context_operation_count = 0
        app._queue_ui_callback = lambda callback: callback()
        app._write_log = Mock()
        app.status_var = FakeVar()
        app.board_view = Mock()
        app.level_selector = SimpleNamespace(set_enabled=Mock())
        app._manual_intervention_button = StatefulButton(FakeButton(), toggle_labels(), is_toggle=True)
        app._manual_intervention_button.complete_toggle(True)
        app._restart_button = StatefulButton(FakeButton(), toggle_labels(), is_toggle=False)
        app._weak_network_button = StatefulButton(FakeButton(), toggle_labels(), is_toggle=True)
        app._reject_network_button = StatefulButton(FakeButton(), toggle_labels(), is_toggle=True)
        app._auto_loop_button = StatefulButton(FakeButton(), toggle_labels(), is_toggle=True)
        app._manual_recognize_button = StatefulButton(
            FakeButton(),
            ButtonLabels("识别", "识别", "识别中", "识别中", "锁定", "失败"),
            is_toggle=False,
        )
        app._manual_undo_button = FakeButton()
        app._manual_redo_button = FakeButton()
        app._manual_discard_button = FakeButton()
        app._manual_apply_button = FakeButton()
        app._restore_network_button = FakeButton()
        return app

    def recognition(self):
        reference, level = scene()
        current = reference.copy()
        opened(current, level, (2, 2))
        return live_result(recognize_board(reference, current, level_config=level))

    def test_recognition_busy_locks_and_success_updates_only_manual_cache(self):
        app = self.build_shell()
        recognition = self.recognition()
        before_formal = app.sonar_board.snapshot()
        with (
            patch("ui.gui_app.threading.Thread", HoldingThread),
            patch("ui.gui_app.recognize_current_board", return_value=recognition),
            patch("ui.gui_app.messagebox.showwarning"),
        ):
            app.recognize_manual_board()
            self.assertEqual(app._manual_recognize_button.state, ButtonState.BUSY)
            self.assertEqual(app._manual_intervention_button.state, ButtonState.LOCKED)
            self.assertEqual(app._manual_apply_button.options["ttk_state"], ("disabled",))
            self.assertFalse(app.board_view.set_manual_edit_enabled.call_args.args[0])
            HoldingThread.target()

        self.assertEqual(app._manual_session.state_at((2, 2)), CellState.MISS)
        self.assertEqual(app.sonar_board.snapshot(), before_formal)
        self.assertTrue(app._manual_session.can_undo)
        self.assertEqual(app._manual_recognize_button.state, ButtonState.READY)
        app.board_view.set_manual_edit_enabled.assert_called_with(True)

    def test_recognition_failure_preserves_manual_cache_and_restores_controls(self):
        app = self.build_shell()
        app._manual_session.cycle_cell((1, 1))
        before = app._manual_session.states
        with (
            patch("ui.gui_app.threading.Thread", HoldingThread),
            patch("ui.gui_app.recognize_current_board", side_effect=RuntimeError("页面错误")),
            patch("ui.gui_app.messagebox.showerror") as show_error,
        ):
            app.recognize_manual_board()
            HoldingThread.target()

        self.assertEqual(app._manual_session.states, before)
        self.assertEqual(app._manual_recognize_button.state, ButtonState.READY)
        self.assertEqual(app._manual_apply_button.options["ttk_state"], ("!disabled",))
        show_error.assert_called_once()

    def test_only_successful_apply_marks_manual_review(self):
        app = self.build_shell()
        marker = app._auto_loop_bridge.mark_manual_applied
        app._manual_session.cycle_cell((1, 1))
        app.discard_manual_changes()
        marker.assert_not_called()

        app._manual_session.cycle_cell((1, 1))
        app.apply_manual_changes()

        marker.assert_called_once_with()
        self.assertEqual(app.sonar_board.get_state(1, 1), CellState.HIT)


class AutoLoopCalibrationIntegrationTests(unittest.TestCase):
    def context(self):
        network = Mock()
        return SimpleNamespace(
            adb=object(), page=object(), network=network, game=object(),
            board=object(), strategy=object(), current_level=11,
            control_lock=threading.Lock(),
        )

    def test_resume_without_manual_apply_runs_calibration_before_loop(self):
        context = self.context()
        bridge = AutoProbeLoopBridge(context)
        bridge.board_sync_state.mark_requested_pause()
        recognition = object()
        applied = SimpleNamespace(next_cell=(1, 1))
        sync = BoardSyncApplyResult(recognition=recognition, applied=applied)
        summary = SimpleNamespace(stop_reason="max_levels")
        calls = []
        with (
            patch("ui.auto_loop_bridge.recognize_current_board", side_effect=lambda *a, **k: calls.append("recognize") or recognition),
            patch("ui.auto_loop_bridge.apply_automatic_board_sync", side_effect=lambda *a, **k: calls.append("apply") or sync),
            patch("ui.auto_loop_bridge.run_multi_level_loop", side_effect=lambda **k: calls.append("loop") or summary),
        ):
            bridge._worker()

        self.assertEqual(calls, ["recognize", "apply", "loop"])
        self.assertEqual(bridge.events.get_nowait()[0], "calibrating")
        self.assertEqual(bridge.events.get_nowait()[0], "calibration")
        self.assertEqual(bridge.board_sync_state.resume_decision().value, "none")

    def test_successful_manual_apply_skips_exactly_one_resume_calibration(self):
        context = self.context()
        bridge = AutoProbeLoopBridge(context)
        bridge.board_sync_state.mark_requested_pause()
        bridge.mark_manual_applied()
        summary = SimpleNamespace(stop_reason="max_levels")
        with (
            patch("ui.auto_loop_bridge.recognize_current_board") as recognize,
            patch("ui.auto_loop_bridge.run_multi_level_loop", return_value=summary),
        ):
            bridge._worker()
        recognize.assert_not_called()
        self.assertEqual(bridge.events.get_nowait()[0], "calibration_skipped")
        self.assertEqual(bridge.board_sync_state.resume_decision().value, "none")

    def test_calibration_failure_stops_before_loop_and_keeps_resume_pending(self):
        context = self.context()
        bridge = AutoProbeLoopBridge(context)
        bridge.board_sync_state.mark_requested_pause()
        with (
            patch("ui.auto_loop_bridge.recognize_current_board", side_effect=RuntimeError("质量不足")),
            patch("ui.auto_loop_bridge.run_multi_level_loop") as loop,
        ):
            bridge._worker()
        loop.assert_not_called()
        self.assertEqual(bridge.events.get_nowait()[0], "calibrating")
        self.assertEqual(bridge.events.get_nowait()[0], "error")
        self.assertEqual(bridge.board_sync_state.resume_decision().value, "auto")


if __name__ == "__main__":
    unittest.main()
