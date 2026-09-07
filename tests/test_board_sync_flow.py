from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from flows.board_sync_flow import (
    BoardSyncError,
    apply_automatic_board_sync,
    apply_recognition_preview,
    recognize_current_board,
    validate_automatic_board_sync,
)
from flows.board_sync_state import BoardSyncState, ResumeCalibrationDecision
from sonar import CellState, CheckerboardHuntStrategy, ManualEditSession, SonarBoard
from sonar_config import GlobalBoardSyncConfig
from tests.test_board_recognition import opened, scene
from vision.board_live import LiveBoardRecognitionResult
from vision.board_recognition import recognize_board


def live_result(result, *, stable=True, disagreements=()):
    return LiveBoardRecognitionResult(
        board_result=result,
        frame_count=3,
        usable_frame_count=3,
        mean_state_agreement=1.0 if not disagreements else .98,
        disagreement_cells=tuple(disagreements),
        stable=stable,
        issues=(),
    )


class BoardSyncFlowTests(unittest.TestCase):
    def test_wrong_page_is_rejected_before_capture(self):
        from flows.sonar_page import SonarPageState
        adb = SimpleNamespace(read_screenshot=Mock())
        with patch(
            "flows.board_sync_flow.detect_sonar_page_state",
            return_value=SonarPageState.HOME,
        ):
            with self.assertRaisesRegex(BoardSyncError, "当前页面"):
                recognize_current_board(adb, object(), level=11)
        adb.read_screenshot.assert_not_called()

    def test_preview_overwrites_cache_but_not_formal_board(self):
        reference, level = scene()
        current = reference.copy()
        opened(current, level, (2, 2))
        result = recognize_board(reference, current, level_config=level)
        board = SonarBoard(5, (2, 3))
        session = ManualEditSession(board)

        apply_recognition_preview(session, live_result(result))

        self.assertEqual(session.state_at((2, 2)), CellState.MISS)
        self.assertEqual(board.get_state(2, 2), CellState.UNKNOWN)
        session.undo()
        self.assertEqual(session.state_at((2, 2)), CellState.UNKNOWN)

    def test_stale_preview_does_not_change_cache(self):
        reference, level = scene()
        result = recognize_board(reference, reference, level_config=level)
        session = ManualEditSession(SonarBoard(5, (2, 3)))
        session.cycle_cell((0, 0))
        before = session.states
        with self.assertRaisesRegex(BoardSyncError, "已变化"):
            apply_recognition_preview(session, live_result(result), expected_revision=0)
        self.assertEqual(session.states, before)

    def test_automatic_apply_rebuilds_strategy_and_can_logically_confirm(self):
        reference, level = scene(submarines=(2,))
        current = reference.copy()
        from tests.test_board_recognition import hull
        for cell in ((2, 1), (2, 2)):
            hull(current, level, [cell])
        result = recognize_board(reference, current, level_config=level)
        self.assertEqual(result.counts["HIT"], 2)
        board = SonarBoard(5, (2,))
        strategy = CheckerboardHuntStrategy(board, use_safety_rule=False)

        sync = apply_automatic_board_sync(live_result(result), board, strategy)

        self.assertEqual(board.get_state(2, 1), CellState.SUNK)
        self.assertTrue(strategy.done)
        self.assertIsNone(sync.applied.next_cell)

    def test_invalid_automatic_result_preserves_formal_state(self):
        reference, level = scene()
        result = recognize_board(reference, reference, level_config=level)
        first = replace(result.cells[0], state=CellState.HIT, confidence=.4, needs_review=True)
        result = replace(
            result,
            cells=(first, *result.cells[1:]),
            review_cells=((0, 0),),
        )
        board = SonarBoard(5, (2, 3))
        strategy = CheckerboardHuntStrategy(board)
        before = board.snapshot()

        with self.assertRaises(BoardSyncError):
            apply_automatic_board_sync(live_result(result), board, strategy)

        self.assertEqual(board.snapshot(), before)

    def test_unstable_result_is_rejected(self):
        reference, level = scene()
        result = recognize_board(reference, reference, level_config=level)
        with self.assertRaisesRegex(BoardSyncError, "稳定性"):
            validate_automatic_board_sync(live_result(result, stable=False))


class BoardSyncStateTests(unittest.TestCase):
    def test_only_successful_manual_apply_skips_one_resume(self):
        state = BoardSyncState()
        self.assertEqual(state.resume_decision(), ResumeCalibrationDecision.NONE)
        state.mark_manual_applied()
        self.assertEqual(state.resume_decision(), ResumeCalibrationDecision.NONE)
        state.mark_requested_pause()
        self.assertEqual(state.resume_decision(), ResumeCalibrationDecision.AUTO)
        state.mark_manual_applied()
        self.assertEqual(state.resume_decision(), ResumeCalibrationDecision.SKIP_MANUAL)
        state.mark_resume_succeeded()
        self.assertEqual(state.resume_decision(), ResumeCalibrationDecision.NONE)


if __name__ == "__main__":
    unittest.main()
