from __future__ import annotations

import unittest
from unittest.mock import patch

from sonar import (
    CellState,
    CheckerboardHuntStrategy,
    ConfirmedShip,
    ManualEditError,
    ManualEditSession,
    SonarBoard,
    apply_manual_edits,
)


def ship(cells: tuple[tuple[int, int], ...]) -> ConfirmedShip:
    return ConfirmedShip(
        length=len(cells),
        direction="H",
        cells=cells,
        safety_area=frozenset(),
    )


class StrategyRebuildTests(unittest.TestCase):
    def test_rebuild_preserves_manual_ships_and_derives_remaining_state(self) -> None:
        board = SonarBoard(grid_size=5, submarines=(2, 3))
        states = [[CellState.UNKNOWN for _ in range(5)] for _ in range(5)]
        states[3][1] = CellState.SUNK
        states[3][2] = CellState.SUNK
        states[4][4] = CellState.MISS
        board.replace_states(states)
        strategy = CheckerboardHuntStrategy(board)

        strategy.rebuild_from_board((ship(((3, 1), (3, 2))),))
        next_cell = strategy.choose_next_cell()

        snapshot = strategy.snapshot()
        self.assertEqual(snapshot.remaining_submarines, (3,))
        self.assertEqual(len(snapshot.confirmed_ships), 1)
        self.assertIn((2, 1), snapshot.excluded_cells)
        self.assertEqual(snapshot.pending_cell, next_cell)
        self.assertEqual(board.get_state(*next_cell), CellState.SELECTED)

    def test_rebuild_also_confirms_other_uniquely_derivable_hits(self) -> None:
        board = SonarBoard(grid_size=4, submarines=(2, 2))
        states = [[CellState.UNKNOWN for _ in range(4)] for _ in range(4)]
        states[3][2] = states[3][3] = CellState.SUNK
        states[0][0] = states[0][1] = CellState.HIT
        board.replace_states(states)
        strategy = CheckerboardHuntStrategy(board)

        strategy.rebuild_from_board((ship(((3, 2), (3, 3))),))

        self.assertTrue(strategy.done)
        self.assertEqual(len(strategy.get_confirmed_ships()), 2)
        self.assertEqual(board.get_state(0, 0), CellState.SUNK)
        self.assertEqual(board.get_state(0, 1), CellState.SUNK)

    def test_rebuild_rejects_invalid_confirmed_ship_facts(self) -> None:
        cases = (
            (
                (2, 3),
                ((0, 0), (1, 1), (2, 2)),
                (ship(((0, 0), (1, 1), (2, 2))),),
                "横向或纵向",
                False,
            ),
            (
                (2,),
                ((0, 0), (0, 1), (2, 0), (2, 1)),
                (ship(((0, 0), (0, 1))), ship(((2, 0), (2, 1)))),
                "数量超过",
                False,
            ),
            (
                (2, 2),
                ((0, 0), (0, 1), (0, 2)),
                (ship(((0, 0), (0, 1))), ship(((0, 1), (0, 2)))),
                "重叠",
                False,
            ),
            (
                (2,),
                ((0, 0),),
                (ship(((0, 0), (0, 1))),),
                "MISS",
                False,
            ),
            (
                (2, 2),
                ((0, 0), (0, 1), (1, 0), (1, 1)),
                (ship(((0, 0), (0, 1))), ship(((1, 0), (1, 1)))),
                "安全间距",
                True,
            ),
        )
        for submarines, sunk, ships, error, safety in cases:
            with self.subTest(error=error):
                board = SonarBoard(grid_size=4, submarines=submarines)
                states = [
                    [CellState.UNKNOWN for _ in range(4)]
                    for _ in range(4)
                ]
                for row, col in sunk:
                    states[row][col] = CellState.SUNK
                if error == "MISS":
                    states[0][1] = CellState.MISS
                board.replace_states(states)
                strategy = CheckerboardHuntStrategy(
                    board,
                    use_safety_rule=safety,
                )
                with self.assertRaisesRegex(ValueError, error):
                    strategy.rebuild_from_board(ships)


class ManualApplyTransactionTests(unittest.TestCase):
    def test_success_updates_board_strategy_and_new_pending_cell(self) -> None:
        board = SonarBoard(grid_size=5, submarines=(2, 3))
        strategy = CheckerboardHuntStrategy(board)
        session = ManualEditSession(board)
        session.cycle_cell((2, 1))
        session.cycle_cell((2, 2))
        session.confirm_ship(((2, 1), (2, 2)))
        session.cycle_cell((4, 4))
        session.cycle_cell((4, 4))

        result = apply_manual_edits(session, board, strategy)

        self.assertEqual(board.get_state(2, 1), CellState.SUNK)
        self.assertEqual(board.get_state(4, 4), CellState.MISS)
        self.assertEqual(result.strategy_snapshot.remaining_submarines, (3,))
        self.assertIsNotNone(result.next_cell)
        self.assertEqual(strategy.pending_cell, result.next_cell)

    def test_validation_failure_keeps_formal_state_and_manual_cache(self) -> None:
        board = SonarBoard(grid_size=4, submarines=(2, 3))
        board.mark_sunk(((0, 0), (0, 1), (1, 0)))
        strategy = CheckerboardHuntStrategy(board)
        session = ManualEditSession(board)
        before = board.snapshot()

        with self.assertRaises(ManualEditError):
            apply_manual_edits(session, board, strategy)

        self.assertEqual(board.snapshot().states, before.states)
        self.assertEqual(session.states, before.states)

    def test_cancelled_old_ship_is_removed_when_facts_no_longer_confirm_it(self) -> None:
        board = SonarBoard(grid_size=4, submarines=(2,))
        states = [[CellState.UNKNOWN for _ in range(4)] for _ in range(4)]
        states[0][0] = states[0][1] = CellState.SUNK
        board.replace_states(states)
        strategy = CheckerboardHuntStrategy(board)
        strategy.rebuild_from_board((ship(((0, 0), (0, 1))),))
        session = ManualEditSession(board, strategy.get_confirmed_ships())
        session.cancel_ship_at((0, 0))
        session.cycle_cell((0, 1))

        result = apply_manual_edits(session, board, strategy)

        self.assertEqual(result.strategy_snapshot.confirmed_ships, ())
        self.assertEqual(result.strategy_snapshot.remaining_submarines, (2,))
        self.assertEqual(board.get_state(0, 0), CellState.HIT)
        self.assertEqual(board.get_state(0, 1), CellState.MISS)

    def test_rebuild_failure_rolls_back_board_and_strategy(self) -> None:
        board = SonarBoard(grid_size=4, submarines=(2,))
        strategy = CheckerboardHuntStrategy(board)
        original_pending = strategy.choose_next_cell()
        session = ManualEditSession(board, strategy.get_confirmed_ships())
        session.cycle_cell((1, 1))
        board_before = board.snapshot()
        strategy_before = strategy.snapshot()
        original_rebuild = strategy.rebuild_from_board

        def fail_after_rebuild(confirmed_ships):
            original_rebuild(confirmed_ships)
            raise RuntimeError("模拟重建失败")

        with patch.object(
            strategy,
            "rebuild_from_board",
            side_effect=fail_after_rebuild,
        ):
            with self.assertRaisesRegex(RuntimeError, "模拟重建失败"):
                apply_manual_edits(session, board, strategy)

        self.assertEqual(board.snapshot().states, board_before.states)
        self.assertEqual(strategy.snapshot(), strategy_before)
        self.assertEqual(strategy.pending_cell, original_pending)
        self.assertEqual(session.state_at((1, 1)), CellState.HIT)


if __name__ == "__main__":
    unittest.main()
