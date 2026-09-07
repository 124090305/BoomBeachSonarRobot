"""实时接入的失败隔离、历史、恢复周期和停止边界回归。"""
from collections import Counter
from dataclasses import replace
from pathlib import Path
import tempfile
import threading
import tkinter as tk
import unittest
from unittest.mock import Mock, patch

from flows.board_sync_flow import (
    BoardSyncError, apply_automatic_board_sync, apply_recognition_preview,
    recognize_current_board, validate_automatic_board_sync,
)
from flows.board_sync_state import BoardSyncState, ResumeCalibrationDecision
from flows.sonar_page import SonarPageState
from sonar import CellState, CheckerboardHuntStrategy, ManualEditSession, SonarBoard
from sonar_config import GlobalBoardSyncConfig
from stop_control import StopRequestedError
from tests.test_board_recognition import scene
from tests.test_board_sync_flow import live_result
from tests import test_global_board_integration as integration
from ui.auto_loop_bridge import AutoProbeLoopBridge
from ui.gui_app import BoomBeachSonarApp
from ui.board_view import SonarBoardView, _UNKNOWN_FILL
from ui.button_state import ButtonState
from vision.board_live import recognize_live_board
from vision.board_recognition import recognize_board
from vision.board_types import RecognizedSubmarine


def with_cells(result, changes):
    cells = tuple(replace(cell, **changes.get((cell.row, cell.col), {})) for cell in result.cells)
    n = result.grid_size
    counts = Counter(cell.state.value.upper() for cell in cells)
    return replace(result, cells=cells,
                   states=tuple(tuple(cells[r*n+c].state for c in range(n)) for r in range(n)),
                   counts={key: counts[key] for key in result.counts},
                   review_cells=tuple((c.row, c.col) for c in cells if c.needs_review))


class LiveSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reference, cls.level = scene()
        cls.result = recognize_board(cls.reference, cls.reference, level_config=cls.level)

    def run_frames(self, frames, **config):
        with patch("vision.board_live.recognize_board", side_effect=frames):
            return recognize_live_board(lambda: self.reference, level_config=self.level,
                empty_reference=self.reference,
                live_config=GlobalBoardSyncConfig(frame_interval_seconds=0, **config))

    def test_stable_frames_keep_fast_three_frame_path(self):
        live = self.run_frames([self.result]*3)
        self.assertEqual(live.frame_count, 3)
        self.assertTrue(live.stable)

    def test_disagreement_adds_frames_and_remains_visible(self):
        changed = with_cells(self.result, {(2, 2): dict(state=CellState.MISS)})
        live = self.run_frames([self.result, changed, self.result, self.result, self.result])
        self.assertEqual(live.frame_count, 5)
        self.assertIn((2, 2), live.disagreement_cells)
        self.assertTrue(live.board_result.cell_at(2, 2).needs_review)
        with self.assertRaisesRegex(BoardSyncError, "分歧"):
            validate_automatic_board_sync(live)

    def test_bad_last_frame_cannot_be_hidden_by_good_majority(self):
        bad = replace(self.result, valid=False, quality="occluded")
        live = self.run_frames([self.result]*4 + [bad], frame_count=5)
        self.assertFalse(live.stable)
        self.assertFalse(live.latest_frame_usable)
        self.assertFalse(live.board_result.valid)

    def test_invalid_early_frame_gets_additional_stable_observation(self):
        bad = replace(self.result, valid=False)
        live = self.run_frames([self.result, bad, self.result, self.result])
        self.assertTrue(live.stable)
        self.assertEqual(live.frame_count, 4)

    def test_good_frame_does_not_erase_occlusion_reviews(self):
        weak = with_cells(self.result, {(0, 0): dict(confidence=.3, needs_review=True, reason="文字遮挡")})
        live = self.run_frames([weak, self.result, weak])
        cell = live.board_result.cell_at(0, 0)
        self.assertTrue(cell.needs_review)
        self.assertLess(cell.confidence, self.result.cells[0].confidence)
        self.assertIn("文字遮挡", cell.reason)

    def test_union_of_review_cells_recomputes_whole_board_validity(self):
        frames = [with_cells(self.result, {divmod(i, 5): dict(needs_review=True)
                                         for i in range(start, start+5)}) for start in (0, 5, 10)]
        live = self.run_frames(frames)
        self.assertFalse(live.board_result.valid)
        self.assertEqual(len(live.board_result.review_cells), 15)

    def test_debug_keeps_each_original_and_merged_json(self):
        with tempfile.TemporaryDirectory() as directory:
            live = recognize_live_board(lambda: self.reference, level_config=self.level,
                empty_reference=self.reference, live_config=GlobalBoardSyncConfig(frame_interval_seconds=0),
                output_dir=Path(directory))
            self.assertTrue(Path(live.board_result.debug_paths["live_result"]).is_file())
            for index in range(1, 4):
                self.assertTrue((Path(directory)/f"frame_{index:02d}"/"original.png").is_file())

    def test_same_sunk_cells_with_different_ship_partition_require_review(self):
        def ship(cells):
            return RecognizedSubmarine(tuple(cells), "H", len(cells), .9, (.9,)*(len(cells)-1), "test")
        cells = [(2, c) for c in range(4)]
        result = with_cells(self.result, {cell: dict(state=CellState.SUNK) for cell in cells})
        whole = replace(result, sunk_submarines=(ship(cells),))
        split = replace(result, sunk_submarines=(ship(cells[:2]), ship(cells[2:])))
        live = self.run_frames([whole, split, split], maximum_frame_count=3)
        self.assertEqual(len(live.board_result.sunk_submarines), 2)
        self.assertTrue(set(cells).issubset(live.disagreement_cells))
        self.assertTrue(all(live.board_result.cell_at(*cell).needs_review for cell in cells))


class SyncTransactionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        reference, level = scene()
        cls.result = recognize_board(reference, reference, level_config=level)

    def test_identical_recognition_still_adds_one_history_record(self):
        session = ManualEditSession(SonarBoard(5, (2, 3)))
        session.cycle_cell((1, 1))
        prior = session.states
        apply_recognition_preview(session, live_result(self.result))
        apply_recognition_preview(session, live_result(self.result))
        self.assertTrue(session.undo())
        self.assertEqual(session.states, self.result.states)
        self.assertTrue(session.undo())
        self.assertEqual(session.states, prior)
        self.assertTrue(session.redo())
        self.assertEqual(session.states, self.result.states)

    def test_failed_preview_adds_no_history_and_keeps_review_metadata(self):
        session = ManualEditSession(SonarBoard(5, (2, 3)))
        apply_recognition_preview(session, live_result(self.result))
        before, revision = session._current, session.revision
        with self.assertRaises(BoardSyncError):
            apply_recognition_preview(session, live_result(replace(self.result, valid=False)))
        self.assertEqual(session._current, before)
        self.assertEqual(session.revision, revision)

    def test_malformed_result_cannot_enter_preview(self):
        session = ManualEditSession(SonarBoard(5, (2, 3)))
        bad = replace(self.result, cells=self.result.cells[:-1])
        with self.assertRaisesRegex(BoardSyncError, "尺寸"):
            apply_recognition_preview(session, live_result(bad))
        self.assertFalse(session.can_undo)

    def test_sunk_cells_without_whole_ship_record_cannot_enter_preview(self):
        session = ManualEditSession(SonarBoard(5, (2, 3)))
        bad = with_cells(self.result, {(0, 0): dict(state=CellState.SUNK)})
        with self.assertRaisesRegex(BoardSyncError, "SUNK"):
            apply_recognition_preview(session, live_result(bad))
        self.assertFalse(session.can_undo)

    def test_impossible_hit_layout_never_touches_formal_board(self):
        board = SonarBoard(5, (2, 3))
        strategy = CheckerboardHuntStrategy(board)
        changes = {(r, c): dict(state=CellState.MISS) for r in range(5) for c in range(5)}
        changes[(2, 2)] = dict(state=CellState.HIT)
        bad = with_cells(self.result, changes)
        before = board.snapshot(), strategy.snapshot()
        with self.assertRaises(BoardSyncError):
            apply_automatic_board_sync(live_result(bad), board, strategy)
        self.assertEqual((board.snapshot(), strategy.snapshot()), before)

    def test_no_room_for_remaining_unseen_ships_rejected(self):
        board = SonarBoard(5, (2, 3))
        strategy = CheckerboardHuntStrategy(board)
        bad = with_cells(self.result, {(r, c): dict(state=CellState.MISS) for r in range(5) for c in range(5)})
        with self.assertRaises(BoardSyncError):
            apply_automatic_board_sync(live_result(bad), board, strategy)

    def test_conflicting_diagonal_hits_rejected_with_safety_rule(self):
        board = SonarBoard(5, (2, 3))
        strategy = CheckerboardHuntStrategy(board)
        bad = with_cells(self.result, {(1, 1): dict(state=CellState.HIT), (2, 2): dict(state=CellState.HIT)})
        with self.assertRaises(BoardSyncError):
            apply_automatic_board_sync(live_result(bad), board, strategy)

    def test_search_budget_exhaustion_preserves_formal_revision(self):
        board = SonarBoard(5, (2, 3))
        strategy = CheckerboardHuntStrategy(board)
        before = board.snapshot()
        with self.assertRaisesRegex(BoardSyncError, "超时"):
            apply_automatic_board_sync(live_result(self.result), board, strategy,
                live_config=GlobalBoardSyncConfig(feasibility_node_limit=1))
        self.assertEqual(board.snapshot(), before)

    def test_stop_during_dry_run_leaves_formal_state_unchanged(self):
        board = SonarBoard(5, (2, 3))
        strategy = CheckerboardHuntStrategy(board)
        stop = threading.Event()
        before = board.snapshot()
        with patch("flows.board_sync_flow._validate_remaining_fleet", side_effect=lambda *args: stop.set()):
            with self.assertRaises(StopRequestedError):
                apply_automatic_board_sync(live_result(self.result), board, strategy, stop_event=stop)
        self.assertEqual(board.snapshot(), before)

    def test_stop_inside_formal_write_finishes_strategy_sync(self):
        board = SonarBoard(5, (2, 3))
        strategy = CheckerboardHuntStrategy(board)
        stop = threading.Event()
        original = board.replace_states
        def write(states):
            original(states)
            stop.set()
        with patch.object(board, "replace_states", side_effect=write):
            sync = apply_automatic_board_sync(live_result(self.result), board, strategy, stop_event=stop)
        self.assertTrue(stop.is_set())
        self.assertEqual(sync.applied.next_cell, strategy.pending_cell)
        self.assertEqual(board.get_state(*strategy.pending_cell), CellState.SELECTED)

    def test_page_changed_mid_capture_rejected(self):
        reference, level = scene()
        adb = Mock(read_screenshot=Mock(return_value=reference))
        with (patch("flows.board_sync_flow.detect_sonar_page_state",
                    side_effect=[SonarPageState.ACTIVITY_DETAIL, SonarPageState.HOME]),
              patch("flows.board_sync_flow.read_image", return_value=reference),
              patch("flows.board_sync_flow.get_level_config", return_value=level),
              patch("flows.board_sync_flow.resolve_reference_path", return_value="empty.png")):
            with self.assertRaisesRegex(BoardSyncError, "页面发生变化"):
                recognize_current_board(adb, object(), level=3, live_config=GlobalBoardSyncConfig(save_debug=False))


class UiSafetyTests(unittest.TestCase):
    def setUp(self):
        self.app = integration.GlobalBoardUiTests().build_shell()

    def test_busy_guards_all_mutating_commands_and_refresh_keeps_locks(self):
        app = self.app
        app._runtime.game = Mock()
        before = app._manual_session.states
        with patch("ui.gui_app.threading.Thread", integration.HoldingThread):
            app.recognize_manual_board()
            for action in (app.recognize_manual_board, app.undo_manual_edit, app.redo_manual_edit,
                           app.apply_manual_changes, app.discard_manual_changes,
                           app._exit_manual_intervention, app.restart_game, app.restore_network,
                           app.reset_sonar_board, app.start_auto_loop, app.check_network_state):
                action()
            app._refresh_manual_button_locks()
        self.assertEqual(app._context_operation_count, 1)
        self.assertEqual(app._manual_session.states, before)
        self.assertEqual(app._weak_network_button.state, ButtonState.LOCKED)
        self.assertEqual(app._manual_intervention_button.state, ButtonState.LOCKED)

    def test_failed_thread_start_restores_controls(self):
        app = self.app
        with patch("ui.gui_app.threading.Thread", side_effect=RuntimeError("线程启动失败")), \
                patch("ui.gui_app.messagebox.showerror"):
            app.recognize_manual_board()
        self.assertEqual(app._context_operation_count, 0)
        self.assertEqual(app._manual_recognize_button.state, ButtonState.READY)

    def test_existing_context_work_blocks_recognition(self):
        self.app._context_operation_count = 1
        self.app.recognize_manual_board()
        self.assertEqual(self.app._manual_recognize_button.state, ButtonState.READY)

    def test_network_error_stays_error_after_recognition(self):
        app = self.app
        app._weak_network_button.set_error()
        with (patch("ui.gui_app.threading.Thread", integration.HoldingThread),
              patch("ui.gui_app.recognize_current_board", side_effect=RuntimeError("failed")),
              patch("ui.gui_app.messagebox.showerror")):
            app.recognize_manual_board()
            integration.HoldingThread.target()
        self.assertEqual(app._weak_network_button.state, ButtonState.ERROR)

    def test_review_confirmation_declined_does_not_mark_applied(self):
        app = self.app
        app._manual_session.apply_recognition_preview(app._manual_session.states, (), review_cells=((0, 0),))
        with patch("ui.gui_app.messagebox.askyesno", return_value=False):
            app.apply_manual_changes()
        app._auto_loop_bridge.mark_manual_applied.assert_not_called()

    def test_closing_discards_late_recognition_callback(self):
        app = self.app
        app._closing = True
        revision = app._manual_session.revision
        app._finish_manual_recognition_success(app._manual_session, revision, None)
        self.assertEqual(app._manual_session.revision, revision)

    def test_applied_review_survives_cancelling_later_temporary_edits(self):
        app = self.app
        app._auto_loop_bridge = AutoProbeLoopBridge(app._runtime)
        app._auto_loop_bridge.board_sync_state.mark_requested_pause()
        app._manual_session.cycle_cell((1, 1))
        app.apply_manual_changes()
        app._manual_session.cycle_cell((3, 3))
        app.discard_manual_changes()
        bridge = app._auto_loop_bridge
        self.assertEqual(bridge.board_sync_state.resume_decision(bridge._review_token()),
                         ResumeCalibrationDecision.SKIP_MANUAL)

    def test_failed_apply_never_sets_review_flag(self):
        app = self.app
        with (patch("ui.gui_app.apply_manual_edits", side_effect=RuntimeError("failed")),
              patch.object(app, "_show_error")):
            app.apply_manual_changes()
        app._auto_loop_bridge.mark_manual_applied.assert_not_called()


class ResumeCycleTests(unittest.TestCase):
    def test_invalidation_preserves_calibration_requirement(self):
        state = BoardSyncState()
        state.mark_requested_pause()
        state.mark_manual_applied("revision-1")
        self.assertEqual(state.resume_decision("revision-1"), ResumeCalibrationDecision.SKIP_MANUAL)
        self.assertEqual(state.resume_decision("revision-2"), ResumeCalibrationDecision.AUTO)
        state.invalidate()
        self.assertEqual(state.resume_decision("revision-1"), ResumeCalibrationDecision.AUTO)

    def test_new_pause_clears_previous_manual_review(self):
        state = BoardSyncState()
        state.mark_requested_pause()
        state.mark_manual_applied()
        state.mark_resume_succeeded()
        state.mark_requested_pause()
        self.assertEqual(state.resume_decision(), ResumeCalibrationDecision.AUTO)

    def test_stop_during_calibration_never_enters_loop(self):
        context = integration.AutoLoopCalibrationIntegrationTests().context()
        bridge = AutoProbeLoopBridge(context)
        bridge.board_sync_state.mark_requested_pause()
        def stop(*args, **kwargs):
            bridge.stop_event.set()
            return object()
        with (patch("ui.auto_loop_bridge.recognize_current_board", side_effect=stop),
              patch("ui.auto_loop_bridge.apply_automatic_board_sync") as apply,
              patch("ui.auto_loop_bridge.run_multi_level_loop") as loop):
            bridge._worker()
        apply.assert_not_called()
        loop.assert_not_called()
        context.network.restore_network.assert_not_called()
        self.assertEqual(bridge.board_sync_state.resume_decision(), ResumeCalibrationDecision.AUTO)

    def test_exception_exit_requires_calibration_next_time(self):
        context = integration.AutoLoopCalibrationIntegrationTests().context()
        bridge = AutoProbeLoopBridge(context)
        with patch("ui.auto_loop_bridge.run_multi_level_loop", side_effect=RuntimeError("failed")):
            bridge._worker()
        self.assertEqual(bridge.board_sync_state.resume_decision(), ResumeCalibrationDecision.AUTO)


class BoardPreviewWidgetTests(unittest.TestCase):
    def test_actual_app_recognition_history_and_apply_use_same_session(self):
        reference, level = scene()
        recognition = live_result(recognize_board(reference, reference, level_config=level))
        app = None
        with (patch.object(BoomBeachSonarApp, "_refresh_network_buttons_async"),
              patch("ui.gui_app.recognize_current_board", return_value=recognition),
              patch("ui.gui_app.messagebox.showwarning")):
            try:
                app = BoomBeachSonarApp()
                app.withdraw()
                app.change_level(3)
                app._enter_manual_intervention()
                board_before = app.sonar_board.snapshot()
                with patch("ui.gui_app.threading.Thread", integration.HoldingThread):
                    app.recognize_manual_board()
                    self.assertEqual(app._manual_recognize_button.button.cget("relief"), "sunken")
                    app.update()
                    integration.HoldingThread.target()
                app._drain_ui_callbacks()
                self.assertEqual(app.sonar_board.snapshot(), board_before)
                self.assertTrue(app._manual_session.can_undo)
                app.undo_manual_edit()
                self.assertTrue(app._manual_session.can_redo)
                app.redo_manual_edit()
                app.apply_manual_changes()
                self.assertFalse(app._manual_session.can_undo)
                self.assertFalse(app._auto_loop_bridge.running)
            except tk.TclError as exc:
                if app is None:
                    self.skipTest(str(exc))
                raise
            finally:
                if app is not None:
                    app._cancel_regular_after_callbacks()
                    app.board_view.shutdown()
                    app.scroll_container.shutdown()
                    from logger import detach_log_handler
                    detach_log_handler(app._log_handler)
                    app.destroy()

    def test_manual_preview_ignores_old_strategy_exclusions(self):
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(str(exc))
        root.withdraw()
        view = None
        try:
            board = SonarBoard(5, (2, 3))
            strategy = CheckerboardHuntStrategy(board)
            strategy.report_result((0, 0), True)
            strategy.report_result((0, 1), True)
            strategy.report_result((0, 2), False)
            self.assertIn((1, 1), strategy.excluded_cells)
            view = SonarBoardView(root, board, strategy)
            session = ManualEditSession(board, strategy.get_confirmed_ships())
            session.apply_recognition_preview([[CellState.UNKNOWN]*5 for _ in range(5)], ())
            view.set_manual_session(session)
            view.refresh()
            self.assertIn("人工待应用", view.strategy_var.get())
            self.assertNotIn("已排除", view.strategy_var.get())
            self.assertEqual(view.canvas.itemcget(view._cell_items[(1, 1)], "fill"), _UNKNOWN_FILL)
        finally:
            if view:
                view.shutdown()
            root.destroy()


if __name__ == "__main__":
    unittest.main()
