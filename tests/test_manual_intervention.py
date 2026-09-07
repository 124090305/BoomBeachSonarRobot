from __future__ import annotations

import unittest

from sonar import (
    CellState,
    ConfirmedShip,
    ManualEditError,
    ManualEditSession,
    SonarBoard,
)


class ManualEditSessionTests(unittest.TestCase):
    def make_board(self) -> SonarBoard:
        return SonarBoard(
            grid_size=4,
            submarines=(2,),
        )

    def test_cycle_edits_only_temporary_snapshot(self) -> None:
        board = self.make_board()
        session = ManualEditSession(board)

        self.assertEqual(session.cycle_cell((1, 1)), CellState.HIT)
        self.assertEqual(session.cycle_cell((1, 1)), CellState.MISS)
        self.assertEqual(session.cycle_cell((1, 1)), CellState.UNKNOWN)

        self.assertEqual(board.get_state(1, 1), CellState.UNKNOWN)
        self.assertFalse(session.changed_cells)

    def test_selected_is_unknown_in_manual_preview(self) -> None:
        board = self.make_board()
        board.select_cell(0, 2)

        session = ManualEditSession(board)

        self.assertEqual(session.state_at((0, 2)), CellState.UNKNOWN)
        self.assertEqual(session.cycle_cell((0, 2)), CellState.HIT)
        self.assertEqual(board.get_state(0, 2), CellState.SELECTED)
        self.assertIn((0, 2), session.changed_cells)

    def test_sunk_cell_is_read_only(self) -> None:
        board = self.make_board()
        board.mark_sunk(((2, 1), (2, 2)))
        session = ManualEditSession(board)

        with self.assertRaisesRegex(ManualEditError, "长按取消"):
            session.cycle_cell((2, 1))

        self.assertEqual(session.state_at((2, 1)), CellState.SUNK)
        self.assertEqual(board.get_state(2, 1), CellState.SUNK)

    def test_single_cell_undo_redo_and_new_action_clears_redo(self) -> None:
        session = ManualEditSession(self.make_board())
        session.cycle_cell((0, 0))
        self.assertTrue(session.undo())
        self.assertEqual(session.state_at((0, 0)), CellState.UNKNOWN)
        self.assertTrue(session.redo())
        self.assertEqual(session.state_at((0, 0)), CellState.HIT)
        self.assertTrue(session.undo())

        session.cycle_cell((0, 1))

        self.assertFalse(session.can_redo)
        self.assertFalse(session.redo())

    def test_confirm_ship_requires_straight_continuous_hit_cells(self) -> None:
        session = ManualEditSession(self.make_board())
        session.cycle_cell((1, 1))
        session.cycle_cell((1, 2))

        ship = session.confirm_ship(((1, 2), (1, 1)))

        self.assertEqual(ship.cells, ((1, 1), (1, 2)))
        self.assertEqual(session.state_at((1, 1)), CellState.SUNK)
        self.assertEqual(
            session.pending_confirmed_cells,
            frozenset({(1, 1), (1, 2)}),
        )

        invalid = ManualEditSession(self.make_board())
        invalid.cycle_cell((0, 0))
        invalid.cycle_cell((0, 1))
        invalid.cycle_cell((0, 1))
        with self.assertRaisesRegex(ManualEditError, "HIT"):
            invalid.confirm_ship(((0, 0), (0, 1)))

    def test_vertical_ship_can_be_confirmed_and_invalid_length_is_rejected(self) -> None:
        session = ManualEditSession(self.make_board())
        session.cycle_cell((1, 3))
        session.cycle_cell((2, 3))

        ship = session.confirm_ship(((2, 3), (1, 3)))

        self.assertEqual(ship.direction, "V")
        self.assertEqual(ship.cells, ((1, 3), (2, 3)))

        invalid = ManualEditSession(self.make_board())
        invalid.cycle_cell((0, 0))
        with self.assertRaisesRegex(ManualEditError, "长度"):
            invalid.confirm_ship(((0, 0),))

    def test_cancel_confirmed_ship_is_one_undoable_action(self) -> None:
        board = self.make_board()
        board.mark_sunk(((2, 1), (2, 2)))
        session = ManualEditSession(board)

        ship = session.cancel_ship_at((2, 2))

        self.assertEqual(ship.cells, ((2, 1), (2, 2)))
        self.assertEqual(session.state_at((2, 1)), CellState.HIT)
        self.assertEqual(
            session.pending_cancelled_cells,
            frozenset({(2, 1), (2, 2)}),
        )
        session.undo()
        self.assertEqual(session.state_at((2, 1)), CellState.SUNK)
        session.redo()
        self.assertEqual(session.state_at((2, 2)), CellState.HIT)
        self.assertEqual(board.get_state(2, 2), CellState.SUNK)

    def test_discard_changes_restores_entry_snapshot_and_history(self) -> None:
        session = ManualEditSession(self.make_board())
        session.cycle_cell((3, 3))
        session.discard_changes()

        self.assertEqual(session.state_at((3, 3)), CellState.UNKNOWN)
        self.assertFalse(session.changed_cells)
        self.assertFalse(session.can_undo)
        self.assertFalse(session.can_redo)

    def test_recognition_preview_is_one_undoable_operation(self) -> None:
        session = ManualEditSession(self.make_board())
        session.cycle_cell((3, 3))
        before = session.states
        states = [[CellState.UNKNOWN for _ in range(4)] for _ in range(4)]
        states[1][1] = states[1][2] = CellState.SUNK
        ship = ConfirmedShip(2, "H", ((1, 1), (1, 2)), frozenset())

        session.apply_recognition_preview(
            states,
            (ship,),
            review_cells=((0, 0),),
            confidences=[[0.5 for _ in range(4)] for _ in range(4)],
            reasons=[["识别" for _ in range(4)] for _ in range(4)],
            summary="一次整盘识别",
        )

        self.assertEqual(session.state_at((1, 1)), CellState.SUNK)
        self.assertEqual(session.review_cells, frozenset({(0, 0)}))
        self.assertTrue(session.undo())
        self.assertEqual(session.states, before)
        self.assertTrue(session.redo())
        self.assertEqual(session.state_at((1, 2)), CellState.SUNK)
        session.cycle_cell((0, 0))
        self.assertNotIn((0, 0), session.review_cells)


if __name__ == "__main__":
    unittest.main()
