from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from sonar import (
    CellState,
    CheckerboardHuntStrategy,
    SonarBoard,
)


class CheckerboardHuntStrategyTests(unittest.TestCase):
    def test_fixed_hunt_order(self) -> None:
        board = SonarBoard(
            n=4,
            submarines=(2,),
        )
        strategy = CheckerboardHuntStrategy(
            board,
            hunt_parity=0,
        )

        self.assertEqual(
            strategy.hunt_order,
            (
                (0, 0),
                (0, 2),
                (1, 1),
                (1, 3),
                (2, 0),
                (2, 2),
                (3, 1),
                (3, 3),
            ),
        )

    def test_miss_continues_fixed_hunt(self) -> None:
        board = SonarBoard(
            n=4,
            submarines=(2,),
        )
        strategy = CheckerboardHuntStrategy(board)

        first = strategy.choose_next_cell()
        self.assertEqual(first, (0, 0))

        strategy.report_result(
            first,
            hit=False,
        )

        second = strategy.choose_next_cell()
        self.assertEqual(second, (0, 2))

    def test_hit_switches_to_target(self) -> None:
        board = SonarBoard(
            n=5,
            submarines=(2, 3),
        )
        strategy = CheckerboardHuntStrategy(board)

        first = strategy.choose_next_cell()
        self.assertEqual(first, (0, 0))

        strategy.report_result(
            first,
            hit=True,
        )

        # (0,0) 的“上”越界，所以下一个按固定顺序选择“下”。
        self.assertEqual(
            strategy.choose_next_cell(),
            (1, 0),
        )

    def test_aligned_hits_only_extend_line(self) -> None:
        board = SonarBoard(
            n=6,
            submarines=(3,),
        )
        strategy = CheckerboardHuntStrategy(board)

        strategy.report_result(
            (2, 2),
            hit=True,
        )
        strategy.report_result(
            (2, 3),
            hit=True,
        )

        self.assertEqual(
            strategy.choose_next_cell(),
            (2, 1),
        )

    def test_confirm_ship_and_exclude_safety_area(self) -> None:
        board = SonarBoard(
            n=6,
            submarines=(2, 3),
        )
        strategy = CheckerboardHuntStrategy(board)

        strategy.report_result(
            (2, 2),
            hit=True,
        )
        strategy.report_result(
            (2, 3),
            hit=True,
        )
        strategy.report_result(
            (2, 1),
            hit=False,
        )

        newly_confirmed = strategy.report_result(
            (2, 4),
            hit=False,
        )

        self.assertEqual(
            len(newly_confirmed),
            1,
        )
        self.assertEqual(
            newly_confirmed[0].cells,
            ((2, 2), (2, 3)),
        )
        self.assertEqual(
            board.get_state(2, 2),
            CellState.SUNK,
        )
        self.assertEqual(
            board.get_state(2, 3),
            CellState.SUNK,
        )
        self.assertIn(
            (1, 2),
            strategy.excluded_cells,
        )
        self.assertIn(
            (3, 3),
            strategy.excluded_cells,
        )
        self.assertNotIn(
            (2, 2),
            strategy.excluded_cells,
        )

    def test_full_simulated_level(self) -> None:
        board = SonarBoard(
            n=10,
            submarines=(2, 2, 3, 4, 5),
        )
        strategy = CheckerboardHuntStrategy(board)

        ships = (
            ((0, 0), (0, 1), (0, 2), (0, 3), (0, 4)),
            ((3, 6), (3, 7), (3, 8), (3, 9)),
            ((5, 0), (6, 0), (7, 0)),
            ((9, 3), (9, 4)),
            ((6, 7), (7, 7)),
        )

        occupied = {
            cell
            for ship in ships
            for cell in ship
        }

        steps = 0

        while not strategy.done:
            cell = strategy.choose_next_cell()
            self.assertIsNotNone(cell)

            strategy.report_result(
                cell,
                hit=cell in occupied,
            )

            steps += 1
            self.assertLessEqual(
                steps,
                100,
            )

        confirmed_lengths = sorted(
            ship.length
            for ship in strategy.get_confirmed_ships()
        )

        self.assertEqual(
            confirmed_lengths,
            [2, 2, 3, 4, 5],
        )


if __name__ == "__main__":
    unittest.main()
