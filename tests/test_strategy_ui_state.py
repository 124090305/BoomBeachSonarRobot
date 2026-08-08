from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from sonar import (
    CheckerboardHuntStrategy,
    SonarBoard,
)


class StrategyUiStateTests(unittest.TestCase):
    def test_snapshot_tracks_next_cell_and_mode(self) -> None:
        board = SonarBoard(
            n=5,
            submarines=(2, 3),
        )
        strategy = CheckerboardHuntStrategy(board)

        initial = strategy.snapshot()
        self.assertEqual(initial.mode, "HUNT")
        self.assertIsNone(initial.pending_cell)

        first = strategy.choose_next_cell()
        selected = strategy.snapshot()

        self.assertEqual(first, (0, 0))
        self.assertEqual(selected.pending_cell, (0, 0))
        self.assertEqual(selected.mode, "HUNT")

        strategy.report_result(
            first,
            hit=True,
        )

        target = strategy.choose_next_cell()
        target_snapshot = strategy.snapshot()

        self.assertEqual(target, (1, 0))
        self.assertEqual(target_snapshot.mode, "TARGET")
        self.assertEqual(target_snapshot.pending_cell, (1, 0))

    def test_snapshot_tracks_confirmed_ship_and_excluded_cells(self) -> None:
        board = SonarBoard(
            n=5,
            submarines=(2,),
        )
        strategy = CheckerboardHuntStrategy(board)

        first = strategy.choose_next_cell()
        strategy.report_result(
            first,
            hit=True,
        )

        second = strategy.choose_next_cell()
        self.assertEqual(second, (1, 0))
        strategy.report_result(
            second,
            hit=False,
        )

        third = strategy.choose_next_cell()
        self.assertEqual(third, (0, 1))
        strategy.report_result(
            third,
            hit=True,
        )

        snapshot = strategy.snapshot()

        self.assertEqual(snapshot.mode, "DONE")
        self.assertEqual(snapshot.remaining_submarines, ())
        self.assertEqual(len(snapshot.confirmed_ships), 1)
        self.assertEqual(
            snapshot.confirmed_ships[0].cells,
            ((0, 0), (0, 1)),
        )
        self.assertIn(
            (1, 1),
            snapshot.excluded_cells,
        )
        self.assertIsNone(snapshot.calculation_progress)
        self.assertEqual(snapshot.calculation_status, "")


if __name__ == "__main__":
    unittest.main()
